"""Protocolo de evaluación común: exactitud top-k por nivel, F1 macro, ECE, cobertura a
confianza fija, rendimiento por frecuencia de clase e intervalos por bootstrap."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
from sklearn.metrics import f1_score

from cpcmini.models.base import CandidateSet


def level_view(cands: CandidateSet, level: int) -> tuple[list[list[str]], npt.NDArray[np.float64]]:
    ranked: list[list[str]] = []
    conf = np.zeros(len(cands), dtype=np.float64)
    for i, (codes, probs) in enumerate(zip(cands.codes, cands.probs, strict=True)):
        agg: dict[str, float] = defaultdict(float)
        for code, p in zip(codes, probs.tolist(), strict=True):
            agg[code[:level]] += p
        order = sorted(agg.items(), key=lambda kv: (-kv[1], kv[0]))
        ranked.append([c for c, _ in order])
        conf[i] = order[0][1] if order else 0.0
    return ranked, conf


def hits_at_k(
    ranked: Sequence[Sequence[str]], truth: Sequence[str], level: int, k: int
) -> npt.NDArray[np.bool_]:
    return np.array([t[:level] in r[:k] for r, t in zip(ranked, truth, strict=True)], dtype=bool)


def macro_f1(pred: Sequence[str], truth: Sequence[str]) -> float:
    """F1 macro sobre las clases presentes en la verdad (no premia predecir clases inexistentes)."""
    labels = sorted(set(truth))
    return float(f1_score(list(truth), list(pred), labels=labels, average="macro", zero_division=0))


def expected_calibration_error(
    conf: npt.NDArray[np.float64], correct: npt.NDArray[np.bool_], bins: int
) -> float:
    if conf.size == 0:
        return 0.0
    edges = np.linspace(0.0, 1.0, bins + 1)
    idx = np.clip(np.digitize(conf, edges[1:-1], right=True), 0, bins - 1)
    ece = 0.0
    for b in range(bins):
        mask = idx == b
        if mask.any():
            ece += mask.mean() * abs(float(correct[mask].mean()) - float(conf[mask].mean()))
    return float(ece)


def coverage_at_precision(
    conf: npt.NDArray[np.float64], correct: npt.NDArray[np.bool_], target: float
) -> float:
    """Mayor fracción de ítems respondible con exactitud ≥ target (umbral óptimo en el mismo set)."""
    if conf.size == 0:
        return 0.0
    order = np.argsort(-conf, kind="stable")
    precision = np.cumsum(correct[order]) / np.arange(1, conf.size + 1)
    sorted_conf = conf[order]
    last_of_tie = np.r_[sorted_conf[1:] != sorted_conf[:-1], True]
    ok = np.flatnonzero((precision >= target) & last_of_tie)
    return float((ok[-1] + 1) / conf.size) if ok.size else 0.0


def bucket_of(count: int, edges: Sequence[int]) -> str:
    lower = 1
    for edge in edges:
        if count <= edge:
            return f"{lower}-{edge}"
        lower = edge + 1
    return f"{lower}+"


def by_frequency(
    correct: npt.NDArray[np.bool_],
    truth: Sequence[str],
    train_counts: Mapping[str, int],
    edges: Sequence[int],
) -> dict[str, dict[str, float]]:
    """Exactitud top-1 por grupo de frecuencia del código verdadero en entrenamiento (0 = nunca visto)."""
    groups: dict[str, list[bool]] = defaultdict(list)
    for ok, t in zip(correct.tolist(), truth, strict=True):
        n = train_counts.get(t, 0)
        groups["0 (no visto)" if n == 0 else bucket_of(n, edges)].append(ok)
    return {g: {"n": float(len(v)), "top1": float(np.mean(v))} for g, v in sorted(groups.items())}


@dataclass(frozen=True)
class Interval:
    value: float
    low: float
    high: float

    def as_dict(self) -> dict[str, float]:
        return {
            "value": round(self.value, 4),
            "low": round(self.low, 4),
            "high": round(self.high, 4),
        }


def bootstrap(
    stat: Callable[[npt.NDArray[np.int64]], float], n: int, samples: int, alpha: float, seed: int
) -> Interval:
    """Intervalo percentil por bootstrap no paramétrico (remuestreo de ítems con reemplazo)."""
    rng = np.random.default_rng(seed)
    full = stat(np.arange(n))
    if n == 0:
        return Interval(full, full, full)
    values = np.array([stat(rng.integers(0, n, n)) for _ in range(samples)])
    low, high = np.quantile(values, [alpha / 2, 1 - alpha / 2])
    return Interval(full, float(low), float(high))
