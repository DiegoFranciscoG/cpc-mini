"""Lectura en flujo de los archivos JSONL.gz de OCDS (un proceso de contratación por línea)."""

from __future__ import annotations

import gzip
import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cpcmini.config import ItemsConfig

METHOD_MAX_CHARS = 80


@dataclass(frozen=True, slots=True)
class RawItem:
    """Un ítem tal como viene en OCDS, con el contexto mínimo del proceso (sin datos de partes)."""

    item_uid: str
    ocid: str
    year: int
    source: str
    description: str
    cpc_raw: str
    cpc_label: str
    cpc_scheme: str
    additional_code: str
    method: str
    category: str


def iter_records(path: str | Path) -> Iterator[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def _method_family(details: str | None) -> str:
    """Familia del procedimiento (el texto del catálogo electrónico trae el convenio completo)."""
    if not details:
        return ""
    family = details.split(" - ")[0].strip()
    return family[:METHOD_MAX_CHARS]


def _to_item(
    record: dict[str, Any], source: str, group: int, idx: int, it: dict[str, Any], year: int
) -> RawItem:
    cls = it.get("classification") or {}
    additional = it.get("additionalClassifications") or []
    tender = record.get("tender") or {}
    ocid = str(record.get("ocid") or "")
    return RawItem(
        item_uid=f"{ocid}#{source[0]}{group}#{idx}",
        ocid=ocid,
        year=year,
        source=source,
        description=str(it.get("description") or "").strip(),
        cpc_raw=str(cls.get("id") or "").strip(),
        cpc_label=str(cls.get("description") or "").strip(),
        cpc_scheme=str(cls.get("scheme") or ""),
        additional_code=str(additional[0].get("id") or "") if additional else "",
        method=_method_family(tender.get("procurementMethodDetails")),
        category=str(tender.get("mainProcurementCategory") or ""),
    )


def record_year(record: dict[str, Any]) -> int | None:
    date = str(record.get("date") or "")
    return int(date[:4]) if date[:4].isdigit() else None


def items_of_record(record: dict[str, Any], cfg: ItemsConfig) -> list[RawItem]:
    """Ítems de adjudicación; si no hay, los de la licitación (configurable)."""
    year = record_year(record)
    if year is None:
        return []
    out: list[RawItem] = []
    if cfg.primary_source == "award":
        for g, award in enumerate(record.get("awards") or []):
            for i, it in enumerate(award.get("items") or []):
                out.append(_to_item(record, "award", g, i, it, year))
    if not out and cfg.fallback_source == "tender":
        tender = record.get("tender") or {}
        for i, it in enumerate(tender.get("items") or []):
            out.append(_to_item(record, "tender", 0, i, it, year))
    return out


def iter_items(path: str | Path, cfg: ItemsConfig) -> Iterator[RawItem]:
    for record in iter_records(path):
        yield from items_of_record(record, cfg)
