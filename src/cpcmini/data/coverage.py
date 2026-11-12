"""Fase de verificación: cuánto de los datos del SERCOP sirve para entrenar (cobertura por año).

Se calcula sobre los Parquet intermedios (una fila por ítem tal como viene en OCDS).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import polars as pl

from cpcmini.data.dataset import keep_mask

LONG_TAIL_THRESHOLDS = (1, 5, 20, 100)


def coverage_by_year(items: pl.DataFrame) -> pl.DataFrame:
    usable = keep_mask()
    return (
        items.group_by("year")
        .agg(
            items=pl.len(),
            with_description=(pl.col("description") != "").sum(),
            with_classification=(pl.col("cpc_raw") != "").sum(),
            usable_code=pl.col("code").is_not_null().sum(),
            zero_restored=pl.col("zero_restored").sum(),
            informative=(pl.col("code").is_not_null() & pl.col("informative")).sum(),
            label_copy=(pl.col("code").is_not_null() & pl.col("label_copy")).sum(),
            pii=(pl.col("pii") != "").sum(),
            usable=usable.sum(),
            codes9=pl.col("code").filter(usable).str.slice(0, 9).n_unique(),
            codes5=pl.col("code").filter(usable).str.slice(0, 5).n_unique(),
            award_items=(pl.col("source") == "award").sum(),
        )
        .with_columns(
            pct_description=(100 * pl.col("with_description") / pl.col("items")).round(2),
            pct_classification=(100 * pl.col("with_classification") / pl.col("items")).round(2),
            pct_usable=(100 * pl.col("usable") / pl.col("items")).round(2),
            pct_label_copy=(100 * pl.col("label_copy") / pl.col("items")).round(2),
        )
        .sort("year")
    )


def code_lengths(items: pl.DataFrame) -> dict[str, int]:
    lengths = (
        items.filter(pl.col("code").is_not_null())
        .group_by(pl.col("code").str.len_chars().alias("digits"))
        .len()
        .sort("digits")
    )
    return {str(d): int(n) for d, n in lengths.iter_rows()}


def long_tail(train: pl.DataFrame) -> dict[str, int]:
    counts = train.group_by("code9").len()["len"]
    out = {f"codes_le_{t}": int((counts <= t).sum()) for t in LONG_TAIL_THRESHOLDS}
    out["codes_total"] = int(counts.len())
    return out


def coverage_report(
    interim_dir: str | Path, years: list[int], train: pl.DataFrame | None = None
) -> dict[str, Any]:
    files = [Path(interim_dir) / f"items_{y}.parquet" for y in years]
    items = pl.read_parquet([f for f in files if f.exists()])
    report: dict[str, Any] = {
        "by_year": coverage_by_year(items).to_dicts(),
        "code_lengths": code_lengths(items),
    }
    if train is not None:
        report["long_tail_train"] = long_tail(train)
    return report


def write_report(report: dict[str, Any], out_json: str | Path) -> Path:
    out = Path(out_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
