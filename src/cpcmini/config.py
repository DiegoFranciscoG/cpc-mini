"""Carga tipada de los archivos de configuración versionados en ``configs/``."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SourceConfig(_Frozen):
    url_template: str
    publication: int
    license: str
    license_url: str
    attribution: str
    years: list[int]
    raw_dir: str


class ItemsConfig(_Frozen):
    primary_source: str
    fallback_source: str
    classification_scheme: str


class CodesConfig(_Frozen):
    levels: list[int]
    min_digits: int
    max_digits: int
    restore_leading_zero: bool


class TextConfig(_Frozen):
    min_chars: int
    min_alpha_tokens: int
    max_chars: int
    generic_patterns: list[str]
    units: dict[str, list[str]]
    abbreviations: dict[str, str]
    strip_prefixes: list[str]


class PiiConfig(_Frozen):
    cedula_provinces_max: int
    cedula_extra_provinces: list[int]
    email_regex: str
    phone_regexes: list[str]


class SplitConfig(_Frozen):
    train_max_year: int
    val_years: list[int]
    test_years: list[int]

    def split_of(self, year: int) -> str | None:
        if year <= self.train_max_year:
            return "train"
        if year in self.val_years:
            return "val"
        if year in self.test_years:
            return "test"
        return None


class DedupConfig(_Frozen):
    use_token_signature: bool


class PathsConfig(_Frozen):
    interim_dir: str
    processed_dir: str
    manifest: str


class DataConfig(_Frozen):
    source: SourceConfig
    items: ItemsConfig
    codes: CodesConfig
    text: TextConfig
    pii: PiiConfig
    split: SplitConfig
    dedup: DedupConfig
    paths: PathsConfig


class LinearConfig(_Frozen):
    loss: str
    C: float
    alpha: float
    n_jobs: int
    max_iter: int
    svm_max_iter: int
    tol: float
    char_ngram_range: tuple[int, int]
    word_ngram_range: tuple[int, int]
    max_features_char: int
    max_features_word: int
    min_df: int
    local_min_df: int
    max_per_class: int
    hierarchy_levels: list[int]
    beam_width: int
    svm_softmax_scale: float


class RetrievalConfig(_Frozen):
    k: int
    power: float
    min_similarity: float
    batch_size: int
    char_ngram_range: tuple[int, int]
    word_ngram_range: tuple[int, int]
    max_features_char: int
    max_features_word: int
    min_df: int
    max_df: float


class EncoderConfig(_Frozen):
    base_model: str
    max_length: int
    epochs: float
    learning_rate: float
    batch_size: int
    weight_decay: float
    warmup_ratio: float


class GenerativeConfig(_Frozen):
    base_model: str
    lora_r: int
    lora_alpha: int
    lora_dropout: float
    max_seq_length: int
    epochs: float
    learning_rate: float
    batch_size: int
    prompt_template: str


class ModelsConfig(_Frozen):
    seed: int
    top_k: int
    linear: LinearConfig
    retrieval: RetrievalConfig
    encoder: EncoderConfig
    generative: GenerativeConfig
    artifacts_dir: str


class EvalConfig(_Frozen):
    target_precision: float
    bootstrap_samples: int
    bootstrap_samples_f1: int
    bootstrap_alpha: float
    ece_bins: int
    frequency_buckets: list[int]
    quantization_max_drop: float
    latency_budget_ms: float
    reproducibility_tolerance: float
    latency_samples: int
    abstain_label: str = Field(default="no sé")


class Settings(_Frozen):
    data: DataConfig
    models: ModelsConfig
    eval: EvalConfig


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        loaded = yaml.safe_load(fh)
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} no contiene un mapa YAML")
    return loaded


def load_settings(
    config_dir: str | Path = "configs", overrides: str | Path | None = None
) -> Settings:
    """Lee ``data.yaml``, ``models.yaml`` y ``eval.yaml``; ``overrides`` reemplaza secciones."""
    base = Path(config_dir)
    raw: dict[str, Any] = {
        "data": _read_yaml(base / "data.yaml"),
        "models": _read_yaml(base / "models.yaml"),
        "eval": _read_yaml(base / "eval.yaml"),
    }
    if overrides is not None:
        _deep_update(raw, _read_yaml(Path(overrides)))
    return Settings.model_validate(raw)


def _deep_update(target: dict[str, Any], patch: dict[str, Any]) -> None:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
        else:
            target[key] = value
