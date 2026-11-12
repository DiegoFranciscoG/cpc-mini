"""Integración del flujo completo sobre datos ficticios: T-06, T-07, T-08, T-10 y T-12."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from cpcmini.cli import app
from cpcmini.config import Settings
from cpcmini.eval.report import load_metrics, render, select_winner
from cpcmini.models.registry import load_meta, load_model
from cpcmini.pipeline import cap_per_class, train_and_evaluate

pytestmark = pytest.mark.slow

SMALL_MODELS = {
    "linear": {"max_features_char": 5000, "max_features_word": 2000, "min_df": 1, "max_iter": 30},
    "retrieval": {"max_features_char": 5000, "max_features_word": 2000, "min_df": 1, "max_df": 0.5},
}


def _settings(settings: Settings, ws: dict[str, Any], artifacts: Path) -> Settings:
    models = settings.models.model_copy(
        update={
            "artifacts_dir": str(artifacts),
            "linear": settings.models.linear.model_copy(update=SMALL_MODELS["linear"]),
            "retrieval": settings.models.retrieval.model_copy(update=SMALL_MODELS["retrieval"]),
        }
    )
    ev = settings.eval.model_copy(
        update={"bootstrap_samples": 100, "bootstrap_samples_f1": 20, "latency_samples": 30}
    )
    return settings.model_copy(update={"data": ws["data_cfg"], "models": models, "eval": ev})


@pytest.fixture(scope="module")
def trained(synthetic_workspace, settings, tmp_path_factory):
    out = tmp_path_factory.mktemp("trained")
    s = _settings(settings, synthetic_workspace, out / "artifacts")
    processed = synthetic_workspace["data_cfg"].paths.processed_dir
    results = {
        name: train_and_evaluate(name, s, processed, out / "artifacts", out / "reports")
        for name in ("tfidf_logreg", "tfidf_knn")
    }
    return {"settings": s, "dir": out, "results": results, "processed": processed}


def test_metrics_structure_and_learning(trained):
    m = trained["results"]["tfidf_logreg"]
    for split in ("validation", "test"):
        for level in ("level_5", "level_9"):
            block = m[split][level]
            assert (
                0.0
                <= block["top1"]["low"]
                <= block["top1"]["value"]
                <= block["top1"]["high"]
                <= 1.0
            )
            assert block["top3"]["value"] >= block["top1"]["value"]
    # los datos ficticios son separables: el modelo debe aprender bastante más que el azar
    assert m["test"]["level_5"]["top1"]["value"] > 0.5
    assert "texto_libre" in m["test"]["subsets"]


def test_t06_reproducible_with_same_seed(trained):
    s = trained["settings"]
    again = train_and_evaluate(
        "tfidf_logreg",
        s,
        trained["processed"],
        trained["dir"] / "again",
        trained["dir"] / "again_reports",
    )
    first = trained["results"]["tfidf_logreg"]["test"]["level_9"]["top1"]["value"]
    second = again["test"]["level_9"]["top1"]["value"]
    assert abs(first - second) <= s.eval.reproducibility_tolerance
    assert again["dataset_hash"] == trained["results"]["tfidf_logreg"]["dataset_hash"]


def test_t07_quantized_loses_less_than_two_points(trained):
    q = trained["results"]["tfidf_logreg"]["quantization"]
    assert q["drop"] < trained["settings"].eval.quantization_max_drop
    assert q["int8_weights_mb"] < q["float32_weights_mb"]
    assert (trained["dir"] / "artifacts" / "tfidf_logreg_int8" / "model.joblib").exists()


def test_t08_threshold_meets_target_on_validation(trained):
    target = trained["settings"].eval.target_precision
    for result in trained["results"].values():
        abst = result["validation"]["abstention"]
        assert abst["coverage"] == 0.0 or abst["answered_top1"] >= target


def test_t10_latency_under_budget(trained):
    budget = trained["settings"].eval.latency_budget_ms
    for result in trained["results"].values():
        assert result["latency_cpu"]["p95_ms"] < budget


def test_artifacts_roundtrip_and_report(trained):
    folder = trained["dir"] / "artifacts" / "tfidf_logreg"
    model = load_model(folder)
    meta = load_meta(folder)
    assert meta.dataset_hash == trained["results"]["tfidf_logreg"]["dataset_hash"]
    assert model.predict_candidates(["paracetamol 500 mg tableta"], 3).codes[0]
    metrics = load_metrics(trained["dir"] / "reports")
    assert set(metrics) == {"tfidf_logreg", "tfidf_knn"}
    assert select_winner(metrics) in metrics
    text = render(metrics, {"dataset_hash": meta.dataset_hash})
    assert "Ganador (elegido en validación)" in text and "pendiente" in text
    with pytest.raises(FileNotFoundError):
        load_model(trained["dir"] / "nada")


def test_cap_per_class_keeps_most_frequent(synthetic_workspace):
    import polars as pl

    frame = pl.DataFrame(
        {
            "code9": ["a"] * 5 + ["b"],
            "n_items": [1, 9, 3, 7, 5, 1],
            "desc_norm": ["d1", "d2", "d3", "d4", "d5", "d6"],
        }
    )
    out = cap_per_class(frame, 2)
    assert sorted(out["desc_norm"].to_list()) == ["d2", "d4", "d6"]


def test_unknown_model_name(settings):
    from cpcmini.pipeline import build_model

    with pytest.raises(ValueError, match="desconocido"):
        build_model("gpt", settings)


def test_t12_rebuild_from_scratch_in_clean_folder(synthetic_workspace, tmp_path, monkeypatch):
    """La orden ``cpcmini rebuild`` reconstruye todo desde los JSONL.gz en una carpeta vacía."""
    raw_dir = Path(synthetic_workspace["data_cfg"].source.raw_dir)
    override = {
        "data": {
            "source": {
                "raw_dir": str(raw_dir),
                "years": synthetic_workspace["data_cfg"].source.years,
            },
            "paths": {
                "interim_dir": str(tmp_path / "interim"),
                "processed_dir": str(tmp_path / "processed"),
                "manifest": str(tmp_path / "processed" / "manifest.json"),
            },
        },
        "models": {"artifacts_dir": str(tmp_path / "artifacts"), **SMALL_MODELS},
        "eval": {"bootstrap_samples": 50, "bootstrap_samples_f1": 10, "latency_samples": 10},
    }
    override_path = tmp_path / "override.yaml"
    override_path.write_text(yaml.safe_dump(override), encoding="utf-8")
    db = tmp_path / "cpcmini.db"
    monkeypatch.setenv("CPCMINI_DATABASE_URL", f"sqlite:///{db.as_posix()}")
    root = Path(__file__).resolve().parents[2]
    monkeypatch.chdir(root)
    result = CliRunner().invoke(
        app,
        [
            "rebuild",
            "--override",
            str(override_path),
            "--reports",
            str(tmp_path / "reports"),
            "--models",
            "tfidf_logreg",
        ],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "artifacts" / "serving" / "model.joblib").exists()
    assert (tmp_path / "reports" / "resultados.md").exists()
    assert (
        json.loads((tmp_path / "reports" / "ganador.json").read_text())["model"] == "tfidf_logreg"
    )
    assert db.exists()
    predicted = CliRunner().invoke(
        app,
        [
            "predecir",
            "paracetamol 500 mg tabletas",
            "--override",
            str(override_path),
            "--model-dir",
            str(tmp_path / "artifacts" / "serving"),
        ],
    )
    assert predicted.exit_code == 0 and "%" in predicted.output
    empty = CliRunner().invoke(
        app,
        [
            "predecir",
            "ver pliegos",
            "--override",
            str(override_path),
            "--model-dir",
            str(tmp_path / "artifacts" / "serving"),
        ],
    )
    assert empty.exit_code == 0 and "no sé" in empty.output
