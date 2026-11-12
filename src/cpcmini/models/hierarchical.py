"""Escalón 1: TF-IDF + modelo lineal jerárquico (grupo 3 → subclase 5 → código 9 dígitos).

Cada nodo del árbol de prefijos tiene un clasificador local (regresión logística por SGD o SVM
lineal con liblinear) entrenado sólo con los documentos de su rama y sólo con las columnas que
aparecen en ella; así el modelo completo cabe en memoria de una laptop. La predicción usa búsqueda en
haz (beam) para no arrastrar un error temprano: se conservan las ``beam_width`` ramas más probables
en cada nivel.
"""

from __future__ import annotations

import warnings
from collections.abc import Sequence
from dataclasses import dataclass, field
from itertools import pairwise

import numpy as np
import numpy.typing as npt
import scipy.sparse as sp
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import FeatureUnion
from sklearn.svm import LinearSVC

from cpcmini.config import LinearConfig
from cpcmini.features.text import build_vectorizer, transform
from cpcmini.models.base import CandidateSet, softmax_rows

LOG_FLOOR = 1e-12


@dataclass
class LocalModel:
    """Clasificador de un nodo. ``cols is None`` significa un único hijo (probabilidad 1)."""

    classes: npt.NDArray[np.str_]
    cols: npt.NDArray[np.int32] | None = None
    weight: npt.NDArray[np.float32] | npt.NDArray[np.int8] | None = None
    bias: npt.NDArray[np.float32] | None = None
    scale: npt.NDArray[np.float32] | None = None
    margin_scale: float = 1.0

    def dense_weight(self) -> npt.NDArray[np.float32]:
        assert self.weight is not None
        if self.scale is None:
            return self.weight.astype(np.float32, copy=False)
        out: npt.NDArray[np.float32] = self.weight.astype(np.float32) * self.scale[:, None]
        return out

    def proba(self, x: sp.csr_matrix) -> npt.NDArray[np.float64]:
        if self.cols is None:
            return np.ones((x.shape[0], 1), dtype=np.float64)
        assert self.bias is not None
        sub = x[:, self.cols]
        scores = np.asarray(sub @ self.dense_weight().T) + self.bias
        return softmax_rows(scores * self.margin_scale)

    def nbytes(self) -> int:
        total = 0
        for arr in (self.cols, self.weight, self.bias, self.scale):
            if arr is not None:
                total += int(arr.nbytes)
        return total


@dataclass
class HierarchicalLinear:
    cfg: LinearConfig
    seed: int = 0
    name: str = "tfidf_linear"
    vectorizer: FeatureUnion | None = None
    nodes: dict[str, LocalModel] = field(default_factory=dict)

    # ------------------------------------------------------------------ entrenamiento
    def fit(self, texts: Sequence[str], codes: Sequence[str]) -> HierarchicalLinear:
        cfg = self.cfg
        self.vectorizer = build_vectorizer(
            cfg.char_ngram_range,
            cfg.word_ngram_range,
            cfg.max_features_char,
            cfg.max_features_word,
            cfg.min_df,
        )
        self.vectorizer.fit(list(texts))
        x = transform(self.vectorizer, texts)
        codes_arr = np.asarray(codes, dtype=str)
        levels = list(cfg.hierarchy_levels)
        parents = [0, *levels[:-1]]
        self.nodes = {}
        for parent_len, child_len in zip(parents, levels, strict=True):
            parent_keys = np.array([c[:parent_len] for c in codes_arr])
            child_keys = np.array([c[:child_len] for c in codes_arr])
            order = np.argsort(parent_keys, kind="stable")
            sorted_keys = parent_keys[order]
            bounds = np.flatnonzero(np.r_[True, sorted_keys[1:] != sorted_keys[:-1], True])
            for start, end in pairwise(bounds):
                rows = order[start:end]
                key = str(sorted_keys[start])
                self.nodes[key] = self._fit_node(x[rows], child_keys[rows])
        return self

    def _fit_node(self, x: sp.csr_matrix, y: npt.NDArray[np.str_]) -> LocalModel:
        classes = np.unique(y)
        if len(classes) == 1:
            return LocalModel(classes=classes)
        cfg = self.cfg
        df = np.asarray((x > 0).sum(axis=0)).ravel()
        cols = np.flatnonzero(df >= cfg.local_min_df).astype(np.int32)
        if cols.size == 0:
            cols = np.flatnonzero(df > 0).astype(np.int32)
        sub = x[:, cols]
        with warnings.catch_warnings():
            # Con max_iter acotado, muchos nodos pequeños no «convergen» del todo; el efecto real
            # se mide en validación, no en el aviso.
            warnings.simplefilter("ignore", ConvergenceWarning)
            if cfg.loss == "hinge":
                svm = LinearSVC(
                    C=cfg.C, max_iter=cfg.svm_max_iter, tol=cfg.tol, random_state=self.seed
                )
                svm.fit(sub, y)
                weight, bias, fitted = svm.coef_, svm.intercept_, svm.classes_
                margin = cfg.svm_softmax_scale
            else:
                # Regresión logística entrenada con SGD (OvR): escala a cientos de miles de filas.
                lr = SGDClassifier(
                    loss="log_loss",
                    alpha=cfg.alpha,
                    max_iter=cfg.max_iter,
                    tol=cfg.tol,
                    random_state=self.seed,
                    n_jobs=cfg.n_jobs,
                )
                lr.fit(sub, y)
                weight, bias, fitted = lr.coef_, lr.intercept_, lr.classes_
                margin = 1.0
        weight = np.asarray(weight, dtype=np.float32)
        bias = np.asarray(bias, dtype=np.float32)
        if weight.shape[0] == 1:  # binario: softmax([-z/2, z/2]) == [sigmoid(-z), sigmoid(z)]
            weight = np.vstack([-weight / 2, weight / 2])
            bias = np.array([-bias[0] / 2, bias[0] / 2], dtype=np.float32)
        return LocalModel(
            classes=np.asarray(fitted, dtype=str),
            cols=cols,
            weight=weight,
            bias=bias,
            margin_scale=margin,
        )

    # ------------------------------------------------------------------ predicción
    def predict_candidates(self, texts: Sequence[str], k: int) -> CandidateSet:
        if self.vectorizer is None:
            raise RuntimeError("El modelo no está entrenado")
        x = transform(self.vectorizer, texts)
        n = x.shape[0]
        beam = self.cfg.beam_width
        q = np.arange(n)
        pref = np.array([""] * n, dtype=object)
        logp = np.zeros(n, dtype=np.float64)
        for _ in self.cfg.hierarchy_levels:
            q, pref, logp = self._expand(x, q, pref, logp, beam)
            q, pref, logp = _keep_top_per_query(q, pref, logp, beam)
        return _to_candidates(n, q, pref, logp, k)

    def _expand(
        self,
        x: sp.csr_matrix,
        q: npt.NDArray[np.int64],
        pref: npt.NDArray[np.object_],
        logp: npt.NDArray[np.float64],
        beam: int,
    ) -> tuple[npt.NDArray[np.int64], npt.NDArray[np.object_], npt.NDArray[np.float64]]:
        out_q: list[npt.NDArray[np.int64]] = []
        out_p: list[npt.NDArray[np.object_]] = []
        out_l: list[npt.NDArray[np.float64]] = []
        order = np.argsort(pref.astype(str), kind="stable")
        keys = pref[order]
        bounds = np.flatnonzero(np.r_[True, keys[1:] != keys[:-1], True])
        for start, end in pairwise(bounds):
            idx = order[start:end]
            node = self.nodes.get(str(keys[start]))
            if node is None:
                continue
            probs = node.proba(x[q[idx]])
            kk = min(beam, probs.shape[1])
            top = np.argpartition(-probs, kk - 1, axis=1)[:, :kk]
            rows = np.repeat(np.arange(len(idx)), kk)
            cols = top.ravel()
            out_q.append(q[idx][rows])
            out_p.append(node.classes[cols].astype(object))
            out_l.append(logp[idx][rows] + np.log(np.maximum(probs[rows, cols], LOG_FLOOR)))
        if not out_q:
            empty = np.array([], dtype=np.int64)
            return empty, np.array([], dtype=object), np.array([], dtype=np.float64)
        return np.concatenate(out_q), np.concatenate(out_p), np.concatenate(out_l)

    def nbytes(self) -> int:
        return sum(node.nbytes() for node in self.nodes.values())


def _keep_top_per_query(
    q: npt.NDArray[np.int64],
    pref: npt.NDArray[np.object_],
    logp: npt.NDArray[np.float64],
    beam: int,
) -> tuple[npt.NDArray[np.int64], npt.NDArray[np.object_], npt.NDArray[np.float64]]:
    if q.size == 0:
        return q, pref, logp
    order = np.lexsort((pref.astype(str), -logp, q))
    q, pref, logp = q[order], pref[order], logp[order]
    starts = np.flatnonzero(np.r_[True, q[1:] != q[:-1]])
    lengths = np.diff(np.r_[starts, q.size])
    rank = np.arange(q.size) - np.repeat(starts, lengths)
    keep = rank < beam
    return q[keep], pref[keep], logp[keep]


def _to_candidates(
    n: int,
    q: npt.NDArray[np.int64],
    pref: npt.NDArray[np.object_],
    logp: npt.NDArray[np.float64],
    k: int,
) -> CandidateSet:
    codes: list[list[str]] = [[] for _ in range(n)]
    probs: list[list[float]] = [[] for _ in range(n)]
    for qi, p, lp in zip(q.tolist(), pref.tolist(), logp.tolist(), strict=True):
        if len(codes[qi]) < k:
            codes[qi].append(str(p))
            probs[qi].append(float(np.exp(lp)))
    return CandidateSet(codes, [np.asarray(p, dtype=np.float64) for p in probs])
