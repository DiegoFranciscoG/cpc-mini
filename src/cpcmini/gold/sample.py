"""Conjunto de oro: muestreo estratificado de prueba y reglas de revisión manual."""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from cpcmini.eval.metrics import bucket_of

GOLD_COLUMNS = ["desc_norm", "description", "original_code9", "stratum"]
REVIEWED_COLUMNS = [*GOLD_COLUMNS, "status", "gold_code9", "notes"]


def stratum_of(code9: str, train_counts: Mapping[str, int], edges: Sequence[int]) -> str:
    n = train_counts.get(code9, 0)
    return "0 (no visto)" if n == 0 else bucket_of(n, edges)


def stratified_sample(
    test: pl.DataFrame, train_counts: Mapping[str, int], n: int, edges: Sequence[int], seed: int
) -> pl.DataFrame:
    """Reparto igual entre estratos de frecuencia; si un estrato no alcanza, el resto se reparte.

    Sólo texto libre (se excluyen descripciones idénticas a la etiqueta del catálogo).
    """
    pool = test.filter(~pl.col("label_copy")).with_columns(
        stratum=pl.col("code9").map_elements(
            lambda c: stratum_of(c, train_counts, edges), return_dtype=pl.String
        )
    )
    strata = sorted(pool["stratum"].unique().to_list())
    if not strata:
        return pool.head(0).select(["desc_norm", "description", "code9", "stratum"])
    shuffled = pool.sample(fraction=1.0, shuffle=True, seed=seed)
    quota = {s: n // len(strata) for s in strata}
    for s in strata[: n - sum(quota.values())]:
        quota[s] += 1
    taken: dict[str, int] = {}
    for s in strata:
        available = shuffled.filter(pl.col("stratum") == s).height
        taken[s] = min(quota[s], available)
    missing = n - sum(taken.values())
    for s in strata:
        if missing <= 0:
            break
        extra = min(missing, shuffled.filter(pl.col("stratum") == s).height - taken[s])
        taken[s] += extra
        missing -= extra
    parts = [shuffled.filter(pl.col("stratum") == s).head(taken[s]) for s in strata]
    return (
        pl.concat(parts)
        .select(["desc_norm", "description", "code9", "stratum"])
        .sort(["stratum", "desc_norm"])
    )


def write_candidates(frame: pl.DataFrame, path: str | Path) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    frame.rename({"code9": "original_code9"}).select(GOLD_COLUMNS).write_csv(out)


@dataclass(frozen=True)
class ReviewDecision:
    status: str
    gold_code9: str | None
    error: str | None = None


def decide(answer: str, original_code9: str, catalog: set[str] | frozenset[str]) -> ReviewDecision:
    """Interpreta la respuesta del revisor: ``c`` confirma, ``d`` descarta, 9 dígitos corrige."""
    text = answer.strip().lower()
    if text == "c":
        return ReviewDecision("confirmed", original_code9)
    if text == "d":
        return ReviewDecision("discarded", None)
    if len(text) == 9 and text.isdigit():
        if text not in catalog:
            return ReviewDecision("pending", None, f"El código {text} no existe en el catálogo")
        status = "confirmed" if text == original_code9 else "corrected"
        return ReviewDecision(status, text)
    return ReviewDecision(
        "pending", None, "Responde c (confirmar), d (descartar) o un código de 9 dígitos"
    )


def read_reviewed(path: str | Path) -> list[dict[str, str]]:
    p = Path(path)
    if not p.is_file():
        return []
    with p.open(encoding="utf-8", newline="") as fh:
        return [r for r in csv.DictReader(fh) if r.get("status") in ("confirmed", "corrected")]
