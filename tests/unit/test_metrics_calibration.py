"""Métricas del protocolo y calibración/abstención (T-08)."""

import numpy as np
import pytest

from cpcmini.eval.metrics import (
    bootstrap,
    bucket_of,
    by_frequency,
    coverage_at_precision,
    expected_calibration_error,
    hits_at_k,
    level_view,
    macro_f1,
)
from cpcmini.models.base import CandidateSet
from cpcmini.models.calibration import (
    apply_temperature,
    calibrate,
    choose_threshold,
    fit_temperature,
    nll,
    selective,
)


def cs(rows):
    return CandidateSet(
        [[c for c, _ in r] for r in rows], [np.array([p for _, p in r]) for r in rows]
    )


def test_level_view_aggregates_by_prefix():
    cands = cs([[("111110001", 0.4), ("222220001", 0.35), ("111110002", 0.25)]])
    ranked9, conf9 = level_view(cands, 9)
    ranked5, conf5 = level_view(cands, 5)
    assert ranked9[0][0] == "111110001" and conf9[0] == pytest.approx(0.4)
    assert ranked5[0] == ["11111", "22222"] and conf5[0] == pytest.approx(0.65)


def test_hits_at_k_and_macro_f1():
    ranked = [["a1", "b1"], ["b1", "a1"], ["c1"]]
    truth = ["a1", "a1", "d1"]
    assert hits_at_k(ranked, truth, 2, 1).tolist() == [True, False, False]
    assert hits_at_k(ranked, truth, 2, 2).tolist() == [True, True, False]
    assert macro_f1(["a", "b", "a"], ["a", "a", "a"]) == pytest.approx(0.8)
    assert macro_f1(["x"], ["x"]) == 1.0


def test_ece_and_coverage():
    conf = np.array([0.9, 0.9, 0.2, 0.2])
    correct = np.array([True, True, False, False])
    assert expected_calibration_error(conf, correct, 10) == pytest.approx(0.15)
    assert coverage_at_precision(conf, correct, 0.9) == pytest.approx(0.5)
    assert coverage_at_precision(np.array([]), np.array([], dtype=bool), 0.9) == 0.0
    assert expected_calibration_error(np.array([]), np.array([], dtype=bool), 10) == 0.0


def test_frequency_buckets():
    assert bucket_of(3, [5, 20]) == "1-5"
    assert bucket_of(7, [5, 20]) == "6-20"
    assert bucket_of(70, [5, 20]) == "21+"
    out = by_frequency(np.array([True, False, True]), ["a", "b", "z"], {"a": 1, "b": 30}, [5, 20])
    assert out["0 (no visto)"]["n"] == 1 and out["1-5"]["top1"] == 1.0 and out["21+"]["top1"] == 0.0


def test_bootstrap_is_deterministic_and_contains_value():
    data = np.array([1, 0, 1, 1, 0, 1, 1, 1])
    a = bootstrap(lambda i: float(data[i].mean()), len(data), 200, 0.05, 1)
    b = bootstrap(lambda i: float(data[i].mean()), len(data), 200, 0.05, 1)
    assert a == b and a.low <= a.value <= a.high
    assert bootstrap(lambda i: 0.0, 0, 10, 0.05, 1).value == 0.0


def test_temperature_keeps_ranking_and_residual():
    p = np.array([0.5, 0.3, 0.1])  # 0.1 de masa residual
    for t in (0.5, 1.0, 2.0):
        cal = apply_temperature(p, t)
        assert np.all(np.diff(cal) <= 0) and cal.sum() <= 1.0 + 1e-9
    assert apply_temperature(p, 1.0) == pytest.approx(p)
    assert apply_temperature(np.array([]), 2.0).size == 0


def test_fit_temperature_reduces_nll_on_overconfident_model():
    rng = np.random.default_rng(0)
    rows, truth = [], []
    for _ in range(400):
        ok = rng.random() < 0.5
        rows.append([("aaaaaaaaa", 0.97), ("bbbbbbbbb", 0.02)])
        truth.append("aaaaaaaaa" if ok else "bbbbbbbbb")
    cands = cs(rows)
    t = fit_temperature(cands, truth)
    assert t > 1.0
    assert nll(cands, truth, t) < nll(cands, truth, 1.0)
    assert calibrate(cands, t).probs[0][0] < 0.97


def test_t08_threshold_reaches_target_on_validation():
    rng = np.random.default_rng(42)
    conf = rng.random(2000)
    correct = rng.random(2000) < conf  # bien calibrado por construcción
    th = choose_threshold(conf, correct, 0.9)
    coverage, precision = selective(conf, correct, th.value)
    assert precision >= 0.9 and coverage == pytest.approx(th.coverage)
    assert 0.0 < th.coverage < 1.0


def test_threshold_abstains_always_when_target_unreachable():
    th = choose_threshold(np.array([0.9, 0.8]), np.array([False, False]), 0.9)
    assert th.value > 1.0 and th.coverage == 0.0
    assert selective(np.array([0.9]), np.array([True]), th.value) == (0.0, 0.0)
    assert choose_threshold(np.array([]), np.array([], dtype=bool), 0.9).coverage == 0.0
