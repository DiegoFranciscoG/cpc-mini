"""Ingesta en flujo: un archivo JSONL.gz por año → un Parquet intermedio con banderas por ítem."""

from __future__ import annotations

from collections.abc import Iterable
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import polars as pl

from cpcmini.config import DataConfig
from cpcmini.data.codes import clean_code, digits_of
from cpcmini.data.normalize import TextNormalizer, clean_display
from cpcmini.data.ocds import RawItem, iter_items
from cpcmini.data.pii import PiiDetector

INTERIM_SCHEMA: dict[str, Any] = {
    "item_uid": pl.String,
    "ocid": pl.String,
    "year": pl.Int32,
    "source": pl.String,
    "description": pl.String,
    "desc_norm": pl.String,
    "signature": pl.String,
    "cpc_raw": pl.String,
    "code": pl.String,
    "cpc_label": pl.String,
    "label_norm": pl.String,
    "method": pl.String,
    "category": pl.String,
    "informative": pl.Boolean,
    "label_copy": pl.Boolean,
    "pii": pl.String,
    "zero_restored": pl.Boolean,
}


def item_row(
    it: RawItem, norm: TextNormalizer, pii: PiiDetector, cfg: DataConfig
) -> dict[str, Any]:
    desc_norm = norm.normalize(it.description)
    label_norm = norm.normalize(it.cpc_label)
    code = clean_code(it.cpc_raw, it.additional_code, cfg.codes)
    if it.cpc_scheme and it.cpc_scheme != cfg.items.classification_scheme:
        code = None
    raw = digits_of(it.cpc_raw)
    return {
        "item_uid": it.item_uid,
        "ocid": it.ocid,
        "year": it.year,
        "source": it.source,
        "description": clean_display(it.description),
        "desc_norm": desc_norm,
        "signature": norm.signature(desc_norm),
        "cpc_raw": it.cpc_raw,
        "code": code,
        "cpc_label": clean_display(it.cpc_label),
        "label_norm": label_norm,
        "method": it.method,
        "category": it.category,
        "informative": norm.is_informative(desc_norm),
        "label_copy": bool(desc_norm) and desc_norm == label_norm,
        "pii": ",".join(pii.findings(it.description)),
        "zero_restored": code is not None and code.startswith("0") and not raw.startswith("0"),
    }


def rows_to_frame(rows: Iterable[dict[str, Any]]) -> pl.DataFrame:
    return pl.DataFrame(list(rows), schema=INTERIM_SCHEMA)


def ingest_file(path: Path, out_path: Path, cfg: DataConfig, chunk_size: int = 200_000) -> int:
    """Convierte un año a Parquet por bloques para no cargar todo en memoria."""
    norm = TextNormalizer(cfg.text)
    pii = PiiDetector(cfg.pii)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    frames: list[pl.DataFrame] = []
    buffer: list[dict[str, Any]] = []
    total = 0
    for it in iter_items(path, cfg.items):
        buffer.append(item_row(it, norm, pii, cfg))
        if len(buffer) >= chunk_size:
            frames.append(rows_to_frame(buffer))
            total += len(buffer)
            buffer = []
    if buffer or not frames:
        frames.append(rows_to_frame(buffer))
        total += len(buffer)
    pl.concat(frames).write_parquet(out_path, compression="zstd")
    return total


def _ingest_year(args: tuple[int, str, str, DataConfig]) -> tuple[int, int]:
    year, raw_dir, interim_dir, cfg = args
    src = Path(raw_dir) / f"{year}.jsonl.gz"
    dst = Path(interim_dir) / f"items_{year}.parquet"
    return year, ingest_file(src, dst, cfg)


def ingest_years(
    cfg: DataConfig, years: list[int] | None = None, workers: int = 4, raw_dir: str | None = None
) -> dict[int, int]:
    todo = years or cfg.source.years
    raw = raw_dir or cfg.source.raw_dir
    jobs = [
        (y, raw, cfg.paths.interim_dir, cfg) for y in todo if (Path(raw) / f"{y}.jsonl.gz").exists()
    ]
    if workers <= 1:
        return dict(_ingest_year(j) for j in jobs)
    with ProcessPoolExecutor(workers) as pool:
        return dict(pool.map(_ingest_year, jobs))
