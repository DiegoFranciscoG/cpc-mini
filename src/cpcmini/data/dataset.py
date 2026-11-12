"""Construcción del dataset: exclusiones, división por tiempo, deduplicación y control de fuga.

Pruebas asociadas: T-01 (conteos), T-02 (sin duplicados entre divisiones), T-03 (tiempo),
T-04 (sin datos personales).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl

from cpcmini.config import DataConfig

SPLITS = ("train", "val", "test")
OUTPUT_COLUMNS = [
    "desc_norm",
    "description",
    "signature",
    "code9",
    "code5",
    "code",
    "n_items",
    "code_agreement",
    "label_copy",
    "category",
    "method",
    "process_kind",
    "year_min",
    "year_max",
    "split",
]


@dataclass
class YearCounts:
    year: int
    raw_items: int
    excluded_no_code: int
    excluded_generic: int
    excluded_pii: int
    kept: int


@dataclass
class SplitCounts:
    split: str
    items: int
    unique_descriptions: int
    removed_leakage_exact: int
    removed_leakage_signature: int
    rows: int
    codes9: int
    codes5: int
    label_copy_rows: int


@dataclass
class Manifest:
    created_at: str
    dataset_hash: str
    config_hash: str
    source_license: str
    attribution: str
    years: list[YearCounts] = field(default_factory=list)
    splits: list[SplitCounts] = field(default_factory=list)
    pii_types_excluded: dict[str, int] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)


def load_interim(interim_dir: str | Path, years: list[int]) -> pl.LazyFrame:
    files = [Path(interim_dir) / f"items_{y}.parquet" for y in years]
    files = [f for f in files if f.exists()]
    if not files:
        raise FileNotFoundError(f"No hay archivos intermedios en {interim_dir}; ejecuta la ingesta")
    return pl.scan_parquet(files)


def year_counts(items: pl.DataFrame) -> list[YearCounts]:
    agg = (
        items.group_by("year")
        .agg(
            raw_items=pl.len(),
            excluded_no_code=pl.col("code").is_null().sum(),
            excluded_generic=(pl.col("code").is_not_null() & ~pl.col("informative")).sum(),
            excluded_pii=(
                pl.col("code").is_not_null() & pl.col("informative") & (pl.col("pii") != "")
            ).sum(),
        )
        .sort("year")
    )
    out = []
    for r in agg.iter_rows(named=True):
        kept = r["raw_items"] - r["excluded_no_code"] - r["excluded_generic"] - r["excluded_pii"]
        out.append(YearCounts(kept=kept, **r))
    return out


def keep_mask() -> pl.Expr:
    return pl.col("code").is_not_null() & pl.col("informative") & (pl.col("pii") == "")


def with_process_kind(items: pl.DataFrame) -> pl.DataFrame:
    """Tipo de proceso del ítem: único, multi-ítem con un solo código (código del proceso) o mixto."""
    code9 = pl.col("code").str.slice(0, 9)
    proc = items.group_by("ocid").agg(proc_items=pl.len(), proc_codes=code9.n_unique())
    return (
        items.join(proc, on="ocid", how="left")
        .with_columns(
            process_kind=pl.when(pl.col("proc_items") == 1)
            .then(pl.lit("unico"))
            .when(pl.col("proc_codes") == 1)
            .then(pl.lit("multi_un_codigo"))
            .otherwise(pl.lit("multi_varios_codigos"))
        )
        .drop("proc_items", "proc_codes")
    )


def aggregate_split(items: pl.DataFrame) -> pl.DataFrame:
    """Una fila por descripción normalizada con el código de 9 dígitos mayoritario."""
    items = items.with_columns(code9=pl.col("code").str.slice(0, 9))
    pairs = items.group_by(["desc_norm", "code9"]).agg(
        n=pl.len(),
        code=pl.col("code").mode().sort().first(),
    )
    best = (
        pairs.sort(["desc_norm", "n", "code9"], descending=[False, True, False])
        .group_by("desc_norm", maintain_order=True)
        .first()
    )
    per_desc = items.group_by("desc_norm").agg(
        n_items=pl.len(),
        description=pl.col("description").mode().sort().first(),
        signature=pl.col("signature").first(),
        label_copy=pl.col("label_copy").any(),
        category=pl.col("category").mode().sort().first(),
        method=pl.col("method").mode().sort().first(),
        process_kind=pl.col("process_kind").mode().sort().first(),
        year_min=pl.col("year").min(),
        year_max=pl.col("year").max(),
    )
    return (
        per_desc.join(best, on="desc_norm", how="inner")
        .with_columns(
            code_agreement=(pl.col("n") / pl.col("n_items")).round(4),
            code5=pl.col("code9").str.slice(0, 5),
        )
        .drop("n")
        .sort("desc_norm")
    )


def remove_leakage(
    frame: pl.DataFrame, seen_desc: set[str], seen_sig: set[str], use_signature: bool
) -> tuple[pl.DataFrame, int, int]:
    exact = frame["desc_norm"].is_in(list(seen_desc))
    n_exact = int(exact.sum())
    frame = frame.filter(~exact)
    n_sig = 0
    if use_signature:
        sig = frame["signature"].is_in(list(seen_sig))
        n_sig = int(sig.sum())
        frame = frame.filter(~sig)
    return frame, n_exact, n_sig


def content_hash(frames: dict[str, pl.DataFrame]) -> str:
    """Hash estable del contenido (independiente de metadatos del archivo Parquet)."""
    h = hashlib.sha256()
    for name in SPLITS:
        df = frames[name].select("desc_norm", "code9").sort("desc_norm")
        h.update(name.encode())
        for d, c in df.iter_rows():
            h.update(f"{d}\t{c}\n".encode())
    return h.hexdigest()


def config_hash(cfg: DataConfig) -> str:
    return hashlib.sha256(cfg.model_dump_json().encode()).hexdigest()[:16]


def build_catalog(kept: pl.DataFrame) -> pl.DataFrame:
    """Catálogo de códigos de 9 dígitos con su etiqueta oficial más frecuente en los datos."""
    items = kept.with_columns(
        code9=pl.col("code").str.slice(0, 9), exact=pl.col("code").str.len_chars() == 9
    )
    labels = (
        items.filter(pl.col("cpc_label") != "")
        .group_by(["code9", "cpc_label"])
        .agg(n=pl.len(), exact=pl.col("exact").any())
        .sort(["code9", "exact", "n", "cpc_label"], descending=[False, True, True, False])
        .group_by("code9", maintain_order=True)
        .first()
        .select("code9", label="cpc_label")
    )
    stats = items.group_by("code9").agg(
        n_items=pl.len(), first_year=pl.col("year").min(), last_year=pl.col("year").max()
    )
    return (
        stats.join(labels, on="code9", how="left")
        .with_columns(code5=pl.col("code9").str.slice(0, 5), label=pl.col("label").fill_null(""))
        .sort("code9")
    )


def build_dataset(
    cfg: DataConfig, interim_dir: str | Path | None = None, out_dir: str | Path | None = None
) -> Manifest:
    interim = interim_dir or cfg.paths.interim_dir
    out = Path(out_dir or cfg.paths.processed_dir)
    out.mkdir(parents=True, exist_ok=True)
    items = load_interim(interim, cfg.source.years).collect()
    years = year_counts(items)
    pii_types = (
        items.filter(pl.col("code").is_not_null() & pl.col("informative") & (pl.col("pii") != ""))
        .select(pl.col("pii").str.split(",").explode())
        .group_by("pii")
        .len()
    )
    kept = with_process_kind(items.filter(keep_mask())).with_columns(
        split=pl.col("year").map_elements(cfg.split.split_of, return_dtype=pl.String)
    )
    kept = kept.filter(pl.col("split").is_not_null())
    frames: dict[str, pl.DataFrame] = {}
    counts: list[SplitCounts] = []
    seen_desc: set[str] = set()
    seen_sig: set[str] = set()
    for name in SPLITS:
        part = kept.filter(pl.col("split") == name)
        agg = aggregate_split(part)
        unique = agg.height
        agg, n_exact, n_sig = remove_leakage(
            agg, seen_desc, seen_sig, cfg.dedup.use_token_signature
        )
        agg = agg.with_columns(split=pl.lit(name)).select(OUTPUT_COLUMNS)
        frames[name] = agg
        seen_desc.update(agg["desc_norm"].to_list())
        seen_sig.update(agg["signature"].to_list())
        counts.append(
            SplitCounts(
                split=name,
                items=part.height,
                unique_descriptions=unique,
                removed_leakage_exact=n_exact,
                removed_leakage_signature=n_sig,
                rows=agg.height,
                codes9=agg["code9"].n_unique(),
                codes5=agg["code5"].n_unique(),
                label_copy_rows=int(agg["label_copy"].sum()),
            )
        )
        agg.write_parquet(out / f"{name}.parquet", compression="zstd")
    build_catalog(kept).write_parquet(out / "catalog.parquet", compression="zstd")
    manifest = Manifest(
        created_at=datetime.now(UTC).isoformat(timespec="seconds"),
        dataset_hash=content_hash(frames),
        config_hash=config_hash(cfg),
        source_license=cfg.source.license,
        attribution=cfg.source.attribution,
        years=years,
        splits=counts,
        pii_types_excluded={str(r[0]): int(r[1]) for r in pii_types.iter_rows()},
    )
    (out / "manifest.json").write_text(manifest.to_json(), encoding="utf-8")
    return manifest


def read_split(processed_dir: str | Path, name: str) -> pl.DataFrame:
    return pl.read_parquet(Path(processed_dir) / f"{name}.parquet")


def read_manifest(processed_dir: str | Path) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads((Path(processed_dir) / "manifest.json").read_text("utf-8"))
    return loaded
