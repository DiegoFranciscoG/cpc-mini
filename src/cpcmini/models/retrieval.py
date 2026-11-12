"""Escalón 4: recuperación por vecinos más cercanos con voto ponderado.

No aprende parámetros por clase: un código nuevo se puede sugerir con sólo agregar ejemplos al
índice, sin reentrenar. La representación es pluggable (TF-IDF por defecto; embeddings densos en
el cuaderno de Kaggle).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
import scipy.sparse as sp
from sklearn.pipeline import FeatureUnion

from cpcmini.config import RetrievalConfig
from cpcmini.features.text import build_vectorizer, transform
from cpcmini.models.base import CandidateSet


def vote(
    neighbor_codes: Sequence[str], sims: npt.NDArray[np.float64], power: float, k: int
) -> tuple[list[str], npt.NDArray[np.float64]]:
    """Suma ``sim**power`` por código y normaliza a probabilidades (orden desc, empate por código)."""
    totals: dict[str, float] = defaultdict(float)
    for code, sim in zip(neighbor_codes, sims.tolist(), strict=True):
        totals[code] += sim**power
    if not totals:
        return [], np.array([], dtype=np.float64)
    ranked = sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))[:k]
    mass = sum(totals.values())
    return [c for c, _ in ranked], np.array([v / mass for _, v in ranked], dtype=np.float64)


@dataclass
class KnnRetrieval:
    cfg: RetrievalConfig
    name: str = "tfidf_knn"
    vectorizer: FeatureUnion | None = None
    index: sp.csr_matrix | None = None
    labels: npt.NDArray[np.str_] | None = None

    def fit(self, texts: Sequence[str], codes: Sequence[str]) -> KnnRetrieval:
        cfg = self.cfg
        self.vectorizer = build_vectorizer(
            cfg.char_ngram_range,
            cfg.word_ngram_range,
            cfg.max_features_char,
            cfg.max_features_word,
            cfg.min_df,
            cfg.max_df,
        )
        self.vectorizer.fit(list(texts))
        self.index = transform(self.vectorizer, texts).T.tocsr()
        self.labels = np.asarray(codes, dtype=str)
        return self

    def neighbors(
        self, texts: Sequence[str]
    ) -> list[tuple[npt.NDArray[np.int64], npt.NDArray[np.float64]]]:
        if self.vectorizer is None or self.index is None:
            raise RuntimeError("El índice no está construido")
        out: list[tuple[npt.NDArray[np.int64], npt.NDArray[np.float64]]] = []
        k, floor = self.cfg.k, self.cfg.min_similarity
        for start in range(0, len(texts), self.cfg.batch_size):
            q = transform(self.vectorizer, texts[start : start + self.cfg.batch_size])
            sims = (q @ self.index).tocsr()
            for row in range(sims.shape[0]):
                lo, hi = sims.indptr[row], sims.indptr[row + 1]
                cols, vals = sims.indices[lo:hi], sims.data[lo:hi].astype(np.float64)
                keep = vals >= floor
                cols, vals = cols[keep], vals[keep]
                if vals.size > k:
                    part = np.argpartition(-vals, k - 1)[:k]
                    cols, vals = cols[part], vals[part]
                order = np.lexsort((cols, -vals))
                out.append((cols[order].astype(np.int64), vals[order]))
        return out

    def predict_candidates(self, texts: Sequence[str], k: int) -> CandidateSet:
        assert self.labels is not None or not texts
        codes: list[list[str]] = []
        probs: list[npt.NDArray[np.float64]] = []
        for cols, sims in self.neighbors(texts):
            assert self.labels is not None
            c, p = vote(self.labels[cols].tolist(), sims, self.cfg.power, k)
            codes.append(c)
            probs.append(p)
        return CandidateSet(codes, probs)

    def nbytes(self) -> int:
        if self.index is None:
            return 0
        return int(self.index.data.nbytes + self.index.indices.nbytes + self.index.indptr.nbytes)
