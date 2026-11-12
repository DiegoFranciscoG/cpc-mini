"""Orquestación: entrenar → calibrar en validación → elegir umbral → evaluar en prueba → guardar."""

from __future__ import annotations

import json
import time
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from cpcmini.config import Settings
from cpcmini.data.dataset import read_manifest, read_split
from cpcmini.eval.evaluate import evaluate_candidates
from cpcmini.eval.metrics import hits_at_k, level_view
from cpcmini.models import registry
from cpcmini.models.base import CandidateSet, CodeClassifier
from cpcmini.models.calibration import calibrate, choose_threshold, fit_temperature
from cpcmini.models.hierarchical import HierarchicalLinear
from cpcmini.models.quantize import quantize_model
from cpcmini.models.retrieval import KnnRetrieval

CANDIDATES_FOR_EVAL = 20
MODEL_FAMILIES = {
    "tfidf_logreg": "1. Base: TF-IDF + regresión logística jerárquica",
    "tfidf_svm": "1. Base: TF-IDF + SVM lineal jerárquico",
    "tfidf_knn": "4. Recuperación: vecinos TF-IDF + voto ponderado",
}


def build_model(name: str, settings: Settings) -> CodeClassifier:
    m = settings.models
    if name == "tfidf_logreg":
        return HierarchicalLinear(
            m.linear.model_copy(update={"loss": "log_loss"}), seed=m.seed, name=name
        )
    if name == "tfidf_svm":
        return HierarchicalLinear(
            m.linear.model_copy(update={"loss": "hinge"}), seed=m.seed, name=name
        )
    if name == "tfidf_knn":
        return KnnRetrieval(m.retrieval, name=name)
    raise ValueError(f"Modelo desconocido: {name}. Opciones: {sorted(MODEL_FAMILIES)}")


def cap_per_class(frame: pl.DataFrame, max_per_class: int) -> pl.DataFrame:
    """Hasta ``max_per_class`` descripciones por código (prioriza las más frecuentes; determinista)."""
    return (
        frame.sort(["code9", "n_items", "desc_norm"], descending=[False, True, False])
        .with_columns(rank=pl.int_range(pl.len()).over("code9"))
        .filter(pl.col("rank") < max_per_class)
        .drop("rank")
        .sort("desc_norm")
    )


def subsets_of(frame: pl.DataFrame) -> dict[str, np.ndarray]:
    out = {"texto_libre": (~frame["label_copy"]).to_numpy()}
    for kind in sorted(frame["process_kind"].unique().to_list()):
        out[f"proceso_{kind}"] = (frame["process_kind"] == kind).to_numpy()
    for year in sorted(frame["year_min"].unique().to_list()):
        out[f"anio_{year}"] = (frame["year_min"] == year).to_numpy()
    return out


def measure_latency(model: CodeClassifier, texts: list[str], k: int) -> dict[str, float]:
    times = []
    model.predict_candidates(texts[:1], k)  # calentamiento
    for text in texts:
        start = time.perf_counter()
        model.predict_candidates([text], k)
        times.append((time.perf_counter() - start) * 1000)
    arr = np.array(times)
    return {
        "p50_ms": round(float(np.median(arr)), 2),
        "p95_ms": round(float(np.quantile(arr, 0.95)), 2),
        "n": float(arr.size),
    }


def top1_at_9(cands: CandidateSet, truth: list[str]) -> float:
    ranked, _ = level_view(cands, 9)
    return float(hits_at_k(ranked, truth, 9, 1).mean())


def train_and_evaluate(
    name: str,
    settings: Settings,
    processed_dir: str | Path,
    artifacts_dir: str | Path,
    reports_dir: str | Path,
) -> dict[str, Any]:
    ev, mcfg = settings.eval, settings.models
    train = read_split(processed_dir, "train")
    val = read_split(processed_dir, "val")
    test = read_split(processed_dir, "test")
    manifest = read_manifest(processed_dir)
    capped = cap_per_class(train, mcfg.linear.max_per_class)
    train_counts = Counter(train["code9"].to_list())

    model = build_model(name, settings)
    start = time.perf_counter()
    model.fit(capped["desc_norm"].to_list(), capped["code9"].to_list())
    train_seconds = time.perf_counter() - start

    val_truth, test_truth = val["code9"].to_list(), test["code9"].to_list()
    val_raw = model.predict_candidates(val["desc_norm"].to_list(), CANDIDATES_FOR_EVAL)
    temperature = fit_temperature(val_raw, val_truth)
    val_cands = calibrate(val_raw, temperature)
    ranked, conf = level_view(val_cands, 9)
    threshold = choose_threshold(conf, hits_at_k(ranked, val_truth, 9, 1), ev.target_precision)
    test_raw = model.predict_candidates(test["desc_norm"].to_list(), CANDIDATES_FOR_EVAL)
    test_cands = calibrate(test_raw, temperature)

    metrics: dict[str, Any] = {
        "model": name,
        "family": MODEL_FAMILIES[name],
        "dataset_hash": manifest["dataset_hash"],
        "train_rows": capped.height,
        "train_seconds": round(train_seconds, 1),
        "temperature": round(temperature, 4),
        "validation": evaluate_candidates(
            val_cands, val_truth, train_counts, ev, threshold.value, mcfg.seed, subsets_of(val)
        ),
        "test": evaluate_candidates(
            test_cands, test_truth, train_counts, ev, threshold.value, mcfg.seed, subsets_of(test)
        ),
    }
    sample = (
        test["desc_norm"].sample(n=min(ev.latency_samples, test.height), seed=mcfg.seed).to_list()
    )
    metrics["latency_cpu"] = measure_latency(model, sample, mcfg.top_k)

    out_dir = Path(artifacts_dir) / name
    meta = registry.ModelMeta(
        name=name,
        family=MODEL_FAMILIES[name],
        temperature=temperature,
        threshold=threshold.value,
        dataset_hash=manifest["dataset_hash"],
        trained_at=datetime.now(UTC).isoformat(timespec="seconds"),
        train_rows=capped.height,
        train_seconds=round(train_seconds, 1),
        size_bytes=0,
        seed=mcfg.seed,
        config=json.loads(settings.models.model_dump_json()),
    )
    registry.save(model, meta, out_dir)
    meta.size_bytes = (out_dir / registry.MODEL_FILE).stat().st_size
    metrics["size_mb"] = round(meta.size_bytes / 1e6, 2)

    if isinstance(model, HierarchicalLinear):
        metrics["quantization"] = _quantized_report(
            model, meta, val, test, temperature, Path(artifacts_dir), metrics
        )
    meta.metrics = {k: metrics[k] for k in ("test", "latency_cpu", "size_mb")}
    registry.write_meta(meta, out_dir)
    _write_report(metrics, Path(reports_dir))
    _log_mlflow(metrics, meta)
    return metrics


def _quantized_report(
    model: HierarchicalLinear,
    meta: registry.ModelMeta,
    val: pl.DataFrame,
    test: pl.DataFrame,
    temperature: float,
    artifacts: Path,
    metrics: dict[str, Any],
) -> dict[str, Any]:
    q = quantize_model(model)
    test_truth = test["code9"].to_list()
    q_test = calibrate(
        q.predict_candidates(test["desc_norm"].to_list(), CANDIDATES_FOR_EVAL), temperature
    )
    float_top1 = metrics["test"]["level_9"]["top1"]["value"]
    int8_top1 = top1_at_9(q_test, test_truth)
    q_meta = registry.ModelMeta(**{**asdict(meta), "name": q.name, "config": meta.config})
    q_dir = artifacts / q.name
    registry.save(q, q_meta, q_dir)
    q_meta.size_bytes = (q_dir / registry.MODEL_FILE).stat().st_size
    sample = test["desc_norm"].sample(n=min(200, test.height), seed=meta.seed).to_list()
    report = {
        "float32_top1_9": round(float_top1, 4),
        "int8_top1_9": round(int8_top1, 4),
        "drop": round(float_top1 - int8_top1, 4),
        "float32_weights_mb": round(model.nbytes() / 1e6, 2),
        "int8_weights_mb": round(q.nbytes() / 1e6, 2),
        "int8_file_mb": round(q_meta.size_bytes / 1e6, 2),
        "int8_latency_cpu": measure_latency(q, sample, 3),
    }
    q_meta.metrics = {"quantization": report}
    registry.write_meta(q_meta, q_dir)
    return report


def _write_report(metrics: dict[str, Any], reports_dir: Path) -> None:
    out = reports_dir / "metrics"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{metrics['model']}.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _log_mlflow(metrics: dict[str, Any], meta: registry.ModelMeta) -> None:
    """Registro opcional en MLflow local (``uv sync --extra tracking``)."""
    try:
        import mlflow
    except ImportError:
        return
    mlflow.set_tracking_uri("file:./mlruns")
    mlflow.set_experiment("cpc-mini")
    with mlflow.start_run(run_name=meta.name):
        mlflow.log_params(
            {
                "model": meta.name,
                "seed": meta.seed,
                "dataset_hash": meta.dataset_hash,
                "temperature": meta.temperature,
                "threshold": meta.threshold,
            }
        )
        test = metrics["test"]
        for level in ("level_5", "level_9"):
            for key in ("top1", "top3", "macro_f1"):
                mlflow.log_metric(f"test_{level}_{key}", test[level][key]["value"])
            mlflow.log_metric(f"test_{level}_ece", test[level]["ece"])
        mlflow.log_metric("latency_p50_ms", metrics["latency_cpu"]["p50_ms"])
