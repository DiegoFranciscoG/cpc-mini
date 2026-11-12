"""Escalón 2: codificador multilingüe (mmBERT-small) ajustado de forma jerárquica.

Se entrenan dos cabezas de clasificación sobre el mismo modelo base: subclase (5 dígitos) y código
(9 dígitos). En inferencia se combinan con ``HierarchyLabels.combine`` para que el código fino
respete la rama elegida. Requiere ``uv sync --extra gpu``; está pensado para Kaggle (GPU T4/P100),
pero funciona en CPU con modelos diminutos (prueba de humo).
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from cpcmini.config import EncoderConfig
from cpcmini.models.base import CandidateSet
from cpcmini.models.labels import HierarchyLabels

LEVELS = (5, 9)


def train_encoder(
    texts: Sequence[str],
    codes: Sequence[str],
    cfg: EncoderConfig,
    out_dir: str | Path,
    seed: int,
    base_model: Any = None,
    tokenizer: Any = None,
) -> Path:
    """Ajusta una cabeza por nivel y guarda modelos, tokenizador y etiquetas en ``out_dir``."""
    import torch
    from datasets import Dataset
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        Trainer,
        TrainingArguments,
        set_seed,
    )

    set_seed(seed)
    out = Path(out_dir)
    labels = HierarchyLabels.from_codes(codes)
    tok = tokenizer or AutoTokenizer.from_pretrained(cfg.base_model)
    for level in LEVELS:
        names = labels.codes5 if level == 5 else labels.codes9
        index = {c: i for i, c in enumerate(names)}
        y = [index[c[:level]] for c in codes]
        if base_model is not None:
            model = base_model(len(names))
        else:
            model = AutoModelForSequenceClassification.from_pretrained(
                cfg.base_model, num_labels=len(names)
            )
        data = Dataset.from_dict({"text": list(texts), "label": y}).map(
            lambda b: tok(
                b["text"], truncation=True, max_length=cfg.max_length, padding="max_length"
            ),
            batched=True,
        )
        args = TrainingArguments(
            output_dir=str(out / f"tmp_level{level}"),
            per_device_train_batch_size=cfg.batch_size,
            learning_rate=cfg.learning_rate,
            num_train_epochs=cfg.epochs,
            weight_decay=cfg.weight_decay,
            warmup_ratio=cfg.warmup_ratio,
            fp16=torch.cuda.is_available(),
            seed=seed,
            data_seed=seed,
            report_to=[],
            save_strategy="no",
            logging_steps=50,
        )
        Trainer(model=model, args=args, train_dataset=data).train()
        model.save_pretrained(out / f"level{level}")
    tok.save_pretrained(out / "tokenizer")
    (out / "labels.json").write_text(json.dumps({"codes9": labels.codes9}), encoding="utf-8")
    return out


@dataclass
class EncoderClassifier:
    """Inferencia del codificador jerárquico (PyTorch u ONNX Runtime según se exporte)."""

    directory: Path
    max_length: int = 64
    batch_size: int = 128
    name: str = "mmbert_small"

    def __post_init__(self) -> None:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        raw = json.loads((self.directory / "labels.json").read_text(encoding="utf-8"))
        self.labels = HierarchyLabels.from_codes(raw["codes9"])
        self.tokenizer = AutoTokenizer.from_pretrained(self.directory / "tokenizer")
        self.models = {
            lv: AutoModelForSequenceClassification.from_pretrained(self.directory / f"level{lv}")
            for lv in LEVELS
        }
        for model in self.models.values():
            model.eval()

    def fit(self, texts: Sequence[str], codes: Sequence[str]) -> EncoderClassifier:
        raise NotImplementedError("Entrena con train_encoder (cuaderno de Kaggle)")

    def predict_candidates(self, texts: Sequence[str], k: int) -> CandidateSet:
        import torch

        rows: list[np.ndarray] = []
        for start in range(0, len(texts), self.batch_size):
            batch = self.tokenizer(
                list(texts[start : start + self.batch_size]),
                truncation=True,
                max_length=self.max_length,
                padding=True,
                return_tensors="pt",
            )
            with torch.no_grad():
                p5 = (
                    torch.softmax(self.models[5](**batch).logits, dim=-1).numpy().astype(np.float64)
                )
                p9 = (
                    torch.softmax(self.models[9](**batch).logits, dim=-1).numpy().astype(np.float64)
                )
            rows.append(self.labels.combine(p5, p9))
        probs = np.vstack(rows) if rows else np.zeros((0, len(self.labels.codes9)))
        return self.labels.to_candidates(probs, k)
