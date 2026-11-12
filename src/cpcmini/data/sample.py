"""Muestra mínima de OCDS para CI, la demo en Docker y la prueba de reconstrucción (T-12).

Sólo conserva los campos que usa el flujo (sin partes, compradores ni proveedores: minimización) y
descarta procesos cuyas descripciones tengan patrones de datos personales.
"""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
from typing import Any

from cpcmini.config import DataConfig
from cpcmini.data.ocds import iter_records
from cpcmini.data.pii import PiiDetector

MAX_ITEMS_PER_RECORD = 40


def _min_item(it: dict[str, Any]) -> dict[str, Any]:
    cls = it.get("classification") or {}
    out: dict[str, Any] = {
        "id": it.get("id"),
        "description": it.get("description"),
        "classification": {"id": cls.get("id"), "scheme": cls.get("scheme"),
                           "description": cls.get("description")},
    }
    extra = it.get("additionalClassifications") or []
    if extra:
        out["additionalClassifications"] = [{"id": extra[0].get("id"), "scheme": extra[0].get("scheme")}]
    return out


def minimize_record(record: dict[str, Any]) -> dict[str, Any]:
    tender = record.get("tender") or {}
    return {
        "ocid": record.get("ocid"),
        "date": record.get("date"),
        "tender": {
            "procurementMethodDetails": tender.get("procurementMethodDetails"),
            "mainProcurementCategory": tender.get("mainProcurementCategory"),
            "items": [_min_item(i) for i in (tender.get("items") or [])[:MAX_ITEMS_PER_RECORD]],
        },
        "awards": [{"items": [_min_item(i) for i in (a.get("items") or [])[:MAX_ITEMS_PER_RECORD]]}
                   for a in (record.get("awards") or [])],
    }


def keep(ocid: str, rate: int, seed: int) -> bool:
    digest = hashlib.sha256(f"{seed}:{ocid}".encode()).digest()
    return int.from_bytes(digest[:4], "big") % rate == 0


def build_sample(cfg: DataConfig, out_dir: str | Path, rate: int, seed: int,
                 raw_dir: str | None = None) -> dict[int, int]:
    """Toma ~1 de cada ``rate`` procesos por año (selección determinista por hash del ocid)."""
    pii = PiiDetector(cfg.pii)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    counts: dict[int, int] = {}
    for year in cfg.source.years:
        src = Path(raw_dir or cfg.source.raw_dir) / f"{year}.jsonl.gz"
        if not src.exists():
            continue
        n = 0
        with gzip.open(out / f"{year}.jsonl.gz", "wt", encoding="utf-8", compresslevel=9) as fh:
            for record in iter_records(src):
                if not keep(str(record.get("ocid")), rate, seed):
                    continue
                small = minimize_record(record)
                texts = [i.get("description") for a in small["awards"] for i in a["items"]]
                texts += [i.get("description") for i in small["tender"]["items"]]
                if any(pii.has_pii(t) for t in texts if t):
                    continue
                fh.write(json.dumps(small, ensure_ascii=False) + "\n")
                n += 1
        counts[year] = n
    return counts
