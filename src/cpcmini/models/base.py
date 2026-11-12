"""Contrato común de los modelos de la escalera (mismo protocolo de evaluación para todos)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np
import numpy.typing as npt


@dataclass(frozen=True, slots=True)
class Candidate:
    code: str
    score: float


@dataclass
class CandidateSet:
    """Candidatos por ítem: códigos de 9 dígitos y probabilidades (filas ordenadas desc)."""

    codes: list[list[str]]
    probs: list[npt.NDArray[np.float64]]

    def __len__(self) -> int:
        return len(self.codes)

    def top1(self) -> tuple[list[str], npt.NDArray[np.float64]]:
        codes = [c[0] if c else "" for c in self.codes]
        conf = np.array([p[0] if len(p) else 0.0 for p in self.probs], dtype=np.float64)
        return codes, conf

    def subset(self, idx: Sequence[int] | npt.NDArray[np.int64]) -> CandidateSet:
        return CandidateSet([self.codes[i] for i in idx], [self.probs[i] for i in idx])


@runtime_checkable
class CodeClassifier(Protocol):
    """Un modelo recibe descripciones YA normalizadas y devuelve candidatos de 9 dígitos."""

    name: str

    def fit(self, texts: Sequence[str], codes: Sequence[str]) -> CodeClassifier: ...

    def predict_candidates(self, texts: Sequence[str], k: int) -> CandidateSet: ...


def softmax_rows(scores: npt.NDArray[np.floating]) -> npt.NDArray[np.float64]:
    shifted = scores - scores.max(axis=1, keepdims=True)
    expd = np.exp(shifted.astype(np.float64))
    out: npt.NDArray[np.float64] = expd / expd.sum(axis=1, keepdims=True)
    return out


def topk_from_scores(
    labels: npt.NDArray[np.str_], scores: npt.NDArray[np.float64], k: int
) -> tuple[list[list[str]], list[npt.NDArray[np.float64]]]:
    """Top-k por fila de una matriz densa de probabilidades."""
    k = min(k, scores.shape[1])
    part = np.argpartition(-scores, k - 1, axis=1)[:, :k]
    codes: list[list[str]] = []
    probs: list[npt.NDArray[np.float64]] = []
    for row, cols in enumerate(part):
        order = cols[np.argsort(-scores[row, cols], kind="stable")]
        codes.append([str(c) for c in labels[order]])
        probs.append(scores[row, order].astype(np.float64))
    return codes, probs
