"""Conjunto de oro, límite de solicitudes, configuración."""

from pathlib import Path

import numpy as np
import polars as pl
import pytest
from pydantic import ValidationError

from cpcmini.config import load_settings
from cpcmini.gold.sample import (
    decide,
    gold_metrics,
    read_reviewed,
    stratified_sample,
    stratum_of,
    write_candidates,
)
from cpcmini.models.base import CandidateSet
from cpcmini.serve.security import TokenBucket
from cpcmini.serve.settings import ApiSettings


def test_stratified_sample_quota_and_exclusions():
    codes = [f"{i:09d}" for i in range(60)]
    test = pl.DataFrame(
        {
            "desc_norm": [f"d{i}" for i in range(60)],
            "description": [f"D{i}" for i in range(60)],
            "code9": codes,
            "label_copy": [i % 10 == 0 for i in range(60)],
        }
    )
    counts = {c: (i % 4) * 30 for i, c in enumerate(codes)}  # 0, 30, 60, 90 → 3 estratos
    sample = stratified_sample(test, counts, 12, [5, 20, 100], seed=1)
    assert sample.height == 12
    assert not set(sample["desc_norm"].to_list()) & {f"d{i}" for i in range(0, 60, 10)}
    assert len(set(sample["stratum"].to_list())) == 2  # "0 (no visto)" y "21-100"
    again = stratified_sample(test, counts, 12, [5, 20, 100], seed=1)
    assert again.equals(sample)
    assert stratum_of("x", {}, [5]) == "0 (no visto)"


def test_sample_fills_from_other_strata_when_short():
    test = pl.DataFrame(
        {
            "desc_norm": ["a", "b", "c"],
            "description": ["a", "b", "c"],
            "code9": ["111111111", "222222222", "222222222"],
            "label_copy": [False] * 3,
        }
    )
    out = stratified_sample(test, {"222222222": 50}, 3, [5, 20, 100], seed=0)
    assert out.height == 3


def test_write_and_read_gold(tmp_path: Path):
    frame = pl.DataFrame(
        {"desc_norm": ["a"], "description": ["A"], "code9": ["111111111"], "stratum": ["1-5"]}
    )
    write_candidates(frame, tmp_path / "g.csv")
    assert (
        (tmp_path / "g.csv")
        .read_text(encoding="utf-8")
        .startswith("desc_norm,description,original_code9")
    )
    (tmp_path / "r.csv").write_text(
        "desc_norm,description,original_code9,stratum,status,gold_code9,notes\n"
        "a,A,111111111,1-5,confirmed,111111111,\nb,B,1,1-5,pending,,\n",
        encoding="utf-8",
    )
    assert len(read_reviewed(tmp_path / "r.csv")) == 1
    assert read_reviewed(tmp_path / "missing.csv") == []


def test_review_decisions():
    catalog = frozenset({"111111111", "222222222"})
    assert decide("c", "111111111", catalog).status == "confirmed"
    assert decide("D", "111111111", catalog).status == "discarded"
    assert decide("222222222", "111111111", catalog).status == "corrected"
    assert decide("111111111", "111111111", catalog).status == "confirmed"
    assert decide("333333333", "111111111", catalog).error
    assert decide("hola", "111111111", catalog).error


def test_token_bucket_refills():
    now = [0.0]
    bucket = TokenBucket(per_minute=2, clock=lambda: now[0])
    assert bucket.allow("ip") and bucket.allow("ip")
    assert not bucket.allow("ip")
    assert bucket.allow("otra-ip")
    now[0] += 30.0
    assert bucket.allow("ip")


def test_api_settings_require_explicit_origins(monkeypatch):
    monkeypatch.delenv("CPCMINI_CORS_ALLOWED_ORIGINS", raising=False)
    with pytest.raises(ValidationError):
        ApiSettings(database_url="sqlite://", model_dir="x")  # falta CORS: no arranca
    with pytest.raises(ValidationError):
        ApiSettings(database_url="sqlite://", model_dir="x", cors_allowed_origins="*")
    ok = ApiSettings(
        database_url="sqlite://",
        model_dir="x",
        cors_allowed_origins="http://localhost:8080, http://127.0.0.1:8080",
    )
    assert ok.origins() == ["http://localhost:8080", "http://127.0.0.1:8080"]


def test_settings_override(tmp_path: Path):
    root = Path(__file__).resolve().parents[2] / "configs"
    override = tmp_path / "o.yaml"
    override.write_text("models:\n  top_k: 5\n", encoding="utf-8")
    s = load_settings(root, override)
    assert s.models.top_k == 5 and s.data.split.split_of(2023) == "train"
    assert s.data.split.split_of(2024) == "val" and s.data.split.split_of(2026) == "test"
    assert s.data.split.split_of(2030) is None
    bad = tmp_path / "bad.yaml"
    bad.write_text("- lista\n", encoding="utf-8")
    with pytest.raises(ValueError, match="mapa YAML"):
        load_settings(root, bad)


def test_gold_metrics():
    cands = CandidateSet(
        [["111110001", "222220001"], ["333330001"]],
        [np.array([0.6, 0.3]), np.array([0.9])],
    )
    rows = [
        {"gold_code9": "222220001", "original_code9": "111110001"},
        {"gold_code9": "333330001", "original_code9": "333330001"},
    ]
    out = gold_metrics(cands, rows)
    assert out["level_9_top1"] == 0.5
    assert out["level_9_top3"] == 1.0
    assert out["original_label_correct"] == 0.5
    assert gold_metrics(cands, []) == {"n": 0.0}
