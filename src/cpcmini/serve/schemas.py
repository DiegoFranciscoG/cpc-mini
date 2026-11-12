"""DTOs de la API con validación (Pydantic)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

DESCRIPTION_MIN = 3
DESCRIPTION_MAX = 500
BATCH_MAX = 50


class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str = Field(
        min_length=DESCRIPTION_MIN,
        max_length=DESCRIPTION_MAX,
        examples=["Paracetamol 500 mg tabletas caja x 100"],
    )

    @field_validator("description")
    @classmethod
    def _strip(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < DESCRIPTION_MIN:
            raise ValueError(f"La descripción debe tener al menos {DESCRIPTION_MIN} caracteres")
        return cleaned


class BatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    descriptions: list[str] = Field(min_length=1, max_length=BATCH_MAX)

    @field_validator("descriptions")
    @classmethod
    def _each(cls, values: list[str]) -> list[str]:
        cleaned = [" ".join(v.split()) for v in values]
        if any(not DESCRIPTION_MIN <= len(v) <= DESCRIPTION_MAX for v in cleaned):
            raise ValueError(
                f"Cada descripción debe tener entre {DESCRIPTION_MIN} y {DESCRIPTION_MAX} caracteres"
            )
        return cleaned


class CandidateOut(BaseModel):
    code9: str
    code5: str
    label: str
    confidence: float = Field(ge=0.0, le=1.0)


class PredictionOut(BaseModel):
    description: str
    abstained: bool
    message: str
    threshold: float
    candidates: list[CandidateOut]
    model: str
    latency_ms: float


class BatchOut(BaseModel):
    results: list[PredictionOut]


class CodeOut(BaseModel):
    code9: str
    code5: str
    label: str
    n_items: int


class SubsetOut(BaseModel):
    n: int
    top1: float
    top3: float


class ModelInfoOut(BaseModel):
    name: str
    family: str
    dataset_hash: str
    trained_at: str
    threshold: float
    target_precision: float
    metrics: dict[str, float]
    intervals: dict[str, tuple[float, float]]
    subsets: dict[str, SubsetOut]
    latency_ms_p50: float | None
    size_mb: float | None
    data_attribution: str
    data_license: str
    data_license_url: str
    intended_use: str
    not_intended_use: str


class HealthOut(BaseModel):
    status: str
    model_loaded: bool
    catalog_codes: int
