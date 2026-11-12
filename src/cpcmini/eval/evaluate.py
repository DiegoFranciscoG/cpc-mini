"""Aplica el protocolo de evaluación a los candidatos de cualquier escalón."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import numpy.typing as npt

from cpcmini.config import EvalConfig
from cpcmini.eval.metrics import (
    bootstrap,
    by_frequency,
    coverage_at_precision,
    expected_calibration_error,
    hits_at_k,
    level_view,
    macro_f1,
)
from cpcmini.models.base import CandidateSet
from cpcmini.models.calibration import selective

LEVELS = (5, 9)


def level_metrics(
    cands: CandidateSet,
    truth: Sequence[str],
    level: int,
    cfg: EvalConfig,
    seed: int,
    with_ci: bool = True,
) -> dict[str, Any]:
    ranked, conf = level_view(cands, level)
    top1 = hits_at_k(ranked, truth, level, 1)
    top3 = hits_at_k(ranked, truth, level, 3)
    pred = [r[0] if r else "" for r in ranked]
    gold = [t[:level] for t in truth]
    n = len(truth)
    out: dict[str, Any] = {"n": n}
    if with_ci:
        out["top1"] = bootstrap(
            lambda i: float(top1[i].mean()), n, cfg.bootstrap_samples, cfg.bootstrap_alpha, seed
        ).as_dict()
        out["top3"] = bootstrap(
            lambda i: float(top3[i].mean()), n, cfg.bootstrap_samples, cfg.bootstrap_alpha, seed + 1
        ).as_dict()
        out["macro_f1"] = bootstrap(
            lambda i: macro_f1([pred[j] for j in i], [gold[j] for j in i]),
            n,
            cfg.bootstrap_samples_f1,
            cfg.bootstrap_alpha,
            seed + 2,
        ).as_dict()
    else:
        out["top1"] = round(float(top1.mean()), 4) if n else 0.0
        out["top3"] = round(float(top3.mean()), 4) if n else 0.0
        out["macro_f1"] = round(macro_f1(pred, gold), 4) if n else 0.0
    out["ece"] = round(expected_calibration_error(conf, top1, cfg.ece_bins), 4)
    out["coverage_at_target"] = round(coverage_at_precision(conf, top1, cfg.target_precision), 4)
    return out


def evaluate_candidates(
    cands: CandidateSet,
    truth: Sequence[str],
    train_counts: Mapping[str, int],
    cfg: EvalConfig,
    threshold: float,
    seed: int,
    subsets: Mapping[str, npt.NDArray[np.bool_]] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        f"level_{lv}": level_metrics(cands, truth, lv, cfg, seed) for lv in LEVELS
    }
    ranked9, conf9 = level_view(cands, 9)
    top1_9 = hits_at_k(ranked9, truth, 9, 1)
    coverage, precision = selective(conf9, top1_9, threshold)
    result["abstention"] = {
        "threshold": round(threshold, 4),
        "coverage": round(coverage, 4),
        "answered_top1": round(precision, 4),
        "target": cfg.target_precision,
    }
    result["by_train_frequency"] = by_frequency(top1_9, truth, train_counts, cfg.frequency_buckets)
    result["subsets"] = {}
    for name, mask in (subsets or {}).items():
        idx = np.flatnonzero(mask)
        if idx.size == 0:
            continue
        sub = cands.subset(idx)
        sub_truth = [truth[int(i)] for i in idx]
        result["subsets"][name] = {
            f"level_{lv}": level_metrics(sub, sub_truth, lv, cfg, seed, with_ci=False)
            for lv in LEVELS
        }
    return result
