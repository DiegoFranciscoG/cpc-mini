"""Escalón 3: Qwen3-0.6B-Base con LoRA y salida restringida al catálogo (adaptador Hugging Face).

En Kaggle se usa Unsloth si está instalado y hay GPU; si no, PEFT estándar (sirve para la prueba
de humo en CPU con un modelo diminuto). La decodificación siempre pasa por ``CodeTrie``: el modelo
no puede devolver un código que no exista en el catálogo de entrenamiento (T-05).
"""

from __future__ import annotations

import importlib.util
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from cpcmini.config import GenerativeConfig
from cpcmini.models.base import CandidateSet
from cpcmini.models.constrained import CodeTrie, constrained_beam


def format_example(cfg: GenerativeConfig, description: str, code: str | None = None) -> str:
    prompt = cfg.prompt_template.format(description=description)
    return prompt if code is None else f"{prompt} {code}"


def _encode_value(tokenizer: Any, value: str) -> list[int]:
    ids: list[int] = tokenizer(" " + value, add_special_tokens=False)["input_ids"]
    return ids


def train_lora(
    texts: Sequence[str],
    codes: Sequence[str],
    cfg: GenerativeConfig,
    out_dir: str | Path,
    seed: int,
    model: Any = None,
    tokenizer: Any = None,
) -> Path:
    import torch
    from datasets import Dataset
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        DataCollatorForLanguageModeling,
        Trainer,
        TrainingArguments,
        set_seed,
    )

    set_seed(seed)
    use_unsloth = importlib.util.find_spec("unsloth") is not None and torch.cuda.is_available()
    if model is None and use_unsloth:
        from unsloth import FastLanguageModel

        model, tokenizer = FastLanguageModel.from_pretrained(
            cfg.base_model, max_seq_length=cfg.max_seq_length
        )
        model = FastLanguageModel.get_peft_model(
            model,
            r=cfg.lora_r,
            lora_alpha=cfg.lora_alpha,
            lora_dropout=cfg.lora_dropout,
            random_state=seed,
        )
    else:
        from peft import LoraConfig, get_peft_model

        tokenizer = tokenizer or AutoTokenizer.from_pretrained(cfg.base_model)
        model = model or AutoModelForCausalLM.from_pretrained(cfg.base_model)
        lora = LoraConfig(
            r=cfg.lora_r,
            lora_alpha=cfg.lora_alpha,
            lora_dropout=cfg.lora_dropout,
            task_type="CAUSAL_LM",
            target_modules="all-linear",
        )
        model = get_peft_model(model, lora)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    eos = tokenizer.eos_token or ""
    data = Dataset.from_dict(
        {"text": [format_example(cfg, t, c) + eos for t, c in zip(texts, codes, strict=True)]}
    )
    data = data.map(
        lambda b: tokenizer(b["text"], truncation=True, max_length=cfg.max_seq_length),
        batched=True,
        remove_columns=["text"],
    )
    args = TrainingArguments(
        output_dir=str(Path(out_dir) / "tmp"),
        per_device_train_batch_size=cfg.batch_size,
        learning_rate=cfg.learning_rate,
        num_train_epochs=cfg.epochs,
        seed=seed,
        data_seed=seed,
        fp16=torch.cuda.is_available(),
        report_to=[],
        save_strategy="no",
        logging_steps=50,
    )
    collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)
    Trainer(model=model, args=args, train_dataset=data, data_collator=collator).train()
    model.save_pretrained(Path(out_dir) / "adapter")
    tokenizer.save_pretrained(Path(out_dir) / "adapter")
    return Path(out_dir)


@dataclass
class GenerativeClassifier:
    """Genera el código con búsqueda en haz restringida al catálogo (o "no sé")."""

    model: Any
    tokenizer: Any
    cfg: GenerativeConfig
    catalog: Sequence[str]
    abstain_label: str = "no sé"
    beams: int = 5
    name: str = "qwen3_lora"
    trie: CodeTrie = field(init=False)

    def __post_init__(self) -> None:
        eos = int(self.tokenizer.eos_token_id)
        values = [*self.catalog, self.abstain_label]
        self.trie = CodeTrie.build(values, lambda v: _encode_value(self.tokenizer, v), eos)
        self.max_steps = max(len(_encode_value(self.tokenizer, v)) for v in values) + 1

    def fit(self, texts: Sequence[str], codes: Sequence[str]) -> GenerativeClassifier:
        raise NotImplementedError("Entrena con train_lora (cuaderno de Kaggle)")

    def _scorer(self, prompt_ids: list[int]) -> Any:
        import torch

        def score(prefix: Sequence[int]) -> np.ndarray:
            ids = torch.tensor([prompt_ids + list(prefix)])
            with torch.no_grad():
                logits = self.model(input_ids=ids).logits[0, -1]
            out: np.ndarray = np.asarray(logits.float().numpy(), dtype=np.float64)
            return out

        return score

    def predict_candidates(self, texts: Sequence[str], k: int) -> CandidateSet:
        codes: list[list[str]] = []
        probs: list[np.ndarray] = []
        for text in texts:
            prompt_ids = self.tokenizer(format_example(self.cfg, text), add_special_tokens=False)[
                "input_ids"
            ]
            ranked = constrained_beam(
                self._scorer(prompt_ids), self.trie, max(self.beams, k), self.max_steps
            )
            valid = [(v, lp) for v, lp in ranked if v != self.abstain_label][:k]
            codes.append([v for v, _ in valid])
            probs.append(np.exp(np.array([lp for _, lp in valid], dtype=np.float64)))
        return CandidateSet(codes, probs)
