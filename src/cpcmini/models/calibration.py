"""Calibración por temperatura y umbral de abstención (pruebas T-08)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from cpcmini.models.base import CandidateSet

EPS = 1e-12
TEMPERATURE_GRID = np.exp(np.linspace(np.log(0.2), np.log(5.0), 81))


def apply_temperature(
    probs: npt.NDArray[np.float64], temperature: float
) -> npt.NDArray[np.float64]:
    """Escala ``p**(1/T)`` incluyendo la masa residual (lo que el modelo no asignó a candidatos)."""
    if probs.size == 0:
        return probs
    residual = max(0.0, 1.0 - float(probs.sum()))
    powered = np.power(np.maximum(probs, EPS), 1.0 / temperature)
    rest = residual ** (1.0 / temperature) if residual > 0 else 0.0
    out: npt.NDArray[np.float64] = powered / (powered.sum() + rest)
    return out


def calibrate(cands: CandidateSet, temperature: float) -> CandidateSet:
    return CandidateSet(list(cands.codes), [apply_temperature(p, temperature) for p in cands.probs])


def nll(cands: CandidateSet, truth: Sequence[str], temperature: float) -> float:
    total = 0.0
    for codes, probs, true in zip(cands.codes, cands.probs, truth, strict=True):
        cal = apply_temperature(probs, temperature)
        p = float(cal[codes.index(true)]) if true in codes else max(EPS, 1.0 - float(cal.sum()))
        total -= np.log(max(p, EPS))
    return total / max(1, len(truth))


def fit_temperature(cands: CandidateSet, truth: Sequence[str]) -> float:
    """Temperatura que minimiza la log-verosimilitud negativa en validación (búsqueda en grilla)."""
    losses = [nll(cands, truth, float(t)) for t in TEMPERATURE_GRID]
    return float(TEMPERATURE_GRID[int(np.argmin(losses))])


@dataclass(frozen=True)
class Threshold:
    value: float
    coverage: float
    precision: float


def choose_threshold(
    conf: npt.NDArray[np.float64], correct: npt.NDArray[np.bool_], target: float
) -> Threshold:
    """Umbral mínimo cuya exactitud sobre lo respondido alcanza ``target`` con máxima cobertura.

    Si ningún umbral alcanza el objetivo, el modelo se abstiene siempre (umbral > 1).
    """
    if conf.size == 0:
        return Threshold(1.01, 0.0, 0.0)
    order = np.argsort(-conf, kind="stable")
    hits = np.cumsum(correct[order].astype(np.float64))
    answered = np.arange(1, conf.size + 1, dtype=np.float64)
    precision = hits / answered
    sorted_conf = conf[order]
    # sólo se puede cortar donde cambia la confianza (empates entran o salen juntos)
    last_of_tie = np.r_[sorted_conf[1:] != sorted_conf[:-1], True]
    ok = np.flatnonzero((precision >= target) & last_of_tie)
    if ok.size == 0:
        return Threshold(1.01, 0.0, 0.0)
    cut = int(ok[-1])
    return Threshold(float(sorted_conf[cut]), float((cut + 1) / conf.size), float(precision[cut]))


def selective(
    conf: npt.NDArray[np.float64], correct: npt.NDArray[np.bool_], threshold: float
) -> tuple[float, float]:
    """Cobertura y exactitud de lo respondido con un umbral fijo."""
    answered = conf >= threshold
    if not answered.any():
        return 0.0, 0.0
    return float(answered.mean()), float(correct[answered].mean())
