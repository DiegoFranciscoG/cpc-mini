"""Guardado y carga de artefactos de modelo (joblib + metadatos JSON).

Los artefactos los produce este mismo flujo; nunca se cargan archivos de terceros con joblib.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import joblib

from cpcmini.models.base import CodeClassifier

MODEL_FILE = "model.joblib"
META_FILE = "meta.json"


@dataclass
class ModelMeta:
    name: str
    family: str
    temperature: float
    threshold: float
    dataset_hash: str
    trained_at: str
    train_rows: int
    train_seconds: float
    size_bytes: int
    seed: int
    config: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)


def save(model: CodeClassifier, meta: ModelMeta, directory: str | Path) -> Path:
    out = Path(directory)
    out.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, out / MODEL_FILE, compress=3)
    write_meta(meta, out)
    return out


def write_meta(meta: ModelMeta, directory: str | Path) -> None:
    path = Path(directory) / META_FILE
    path.write_text(json.dumps(asdict(meta), ensure_ascii=False, indent=2), encoding="utf-8")


def load_meta(directory: str | Path) -> ModelMeta:
    raw = json.loads((Path(directory) / META_FILE).read_text(encoding="utf-8"))
    return ModelMeta(**raw)


def load_model(directory: str | Path) -> CodeClassifier:
    path = Path(directory) / MODEL_FILE
    if not path.is_file():
        raise FileNotFoundError(f"No existe el artefacto {path}")
    model: CodeClassifier = joblib.load(path)
    return model
