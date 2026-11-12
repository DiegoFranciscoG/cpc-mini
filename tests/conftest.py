"""Fixtures compartidas. Los registros OCDS de prueba son FICTICIOS (descripciones inventadas)."""

from __future__ import annotations

import gzip
import json
import random
from pathlib import Path
from typing import Any

import pytest

from cpcmini.config import Settings, load_settings

ROOT = Path(__file__).resolve().parents[1]

# Familias ficticias de productos: (código de 9 dígitos, etiqueta, plantillas de descripción).
FAMILIES: list[tuple[str, str, list[str]]] = [
    (
        "352600111",
        "PARACETAMOL SOLIDO ORAL",
        [
            "paracetamol {n} mg tabletas",
            "acetaminofen {n}mg tab caja",
            "PARACETAMOL {n} MG COMPRIMIDOS",
        ],
    ),
    (
        "352600112",
        "IBUPROFENO SOLIDO ORAL",
        [
            "ibuprofeno {n} mg tabletas",
            "IBUPROFENO {n}MG CAPS",
            "ibuprofeno de {n} mg en comprimidos",
        ],
    ),
    (
        "321290418",
        "RESMA DE PAPEL BOND A4",
        [
            "resma papel bond a4 {n} gr",
            "papel bond A4 de {n} g resma",
            "RESMA DE PAPEL BOND {n} GRAMOS",
        ],
    ),
    (
        "321290419",
        "RESMA DE PAPEL BOND INEN",
        ["papel bond inen {n} g", "resma inen de {n} gramos", "PAPEL BOND TAMAÑO INEN {n} GR"],
    ),
    (
        "853300012",
        "SERVICIOS DE LIMPIEZA DE EDIFICIOS",
        [
            "servicio de limpieza de oficinas {n} m2",
            "limpieza de edificio administrativo bloque {n}",
            "LIMPIEZA INTEGRAL DE INSTALACIONES SECTOR {n}",
        ],
    ),
    (
        "853300011",
        "LIMPIEZA DE VIVIENDAS",
        [
            "limpieza de viviendas sector {n}",
            "aseo de casas barrio {n}",
            "LIMPIEZA DOMICILIARIA ZONA {n}",
        ],
    ),
    (
        "542510012",
        "CONSTRUCCION DE REDES URBANAS DE ALCANTARILLADO",
        [
            "construccion de alcantarillado sanitario etapa {n}",
            "red de alcantarillado pluvial tramo {n}",
            "ALCANTARILLADO COMBINADO SECTOR {n}",
        ],
    ),
    (
        "431510128",
        "REPUESTOS PARA MOTOR DIESEL",
        [
            "filtro de combustible motor diesel {n}",
            "repuestos motor diesel modelo {n}",
            "KIT DE EMPAQUES MOTOR DIESEL {n}",
        ],
    ),
    (
        "013492912",
        "CANASTA DE FRUTAS",
        [
            "canasta de frutas surtidas {n} kg",
            "frutas de temporada {n} kilos",
            "CANASTA FRUTAL {n} KG",
        ],
    ),
    (
        "452300034",
        "TERMINALES",
        ["computadora de escritorio core {n}", "laptop {n} gb ram", "COMPUTADOR PORTATIL {n} GB"],
    ),
]


def _item(code: str, label: str, desc: str, idx: int) -> dict[str, Any]:
    raw = code.lstrip("0") if code.startswith("0") else code  # el cero inicial se pierde en OCDS
    extra = f"{code[:5]}.{code[5:7]}.{code[7]}"
    return {
        "id": str(idx),
        "description": desc,
        "classification": {"id": raw, "scheme": "CPC", "description": label},
        "additionalClassifications": [{"id": extra, "scheme": "CPC"}],
    }


def make_records(years: list[int], per_year: int, seed: int = 7) -> dict[int, list[dict[str, Any]]]:
    rng = random.Random(seed)
    out: dict[int, list[dict[str, Any]]] = {}
    for year in years:
        records = []
        for r in range(per_year):
            code, label, templates = FAMILIES[rng.randrange(len(FAMILIES))]
            n = rng.choice([25, 50, 75, 100, 250, 500, 1000]) + (year % 7)
            desc = rng.choice(templates).format(n=n)
            items = [_item(code, label, desc, 0)]
            if r % 9 == 0:
                items.append(_item(code, label, "VER ESPECIFICACIONES TECNICAS EN LOS PLIEGOS", 1))
            if r % 50 == 0:
                items.append(_item(code, label, f"contacto 0991234567 {desc}", 2))
            if r % 13 == 0:
                items.append(_item(code, label, label, 3))
            record = {
                "ocid": f"ocds-test-{year}-{r}",
                "date": f"{year}-03-01T10:00:00-05:00",
                "tender": {
                    "procurementMethodDetails": "Subasta Inversa Electrónica",
                    "mainProcurementCategory": "goods",
                    "items": [],
                },
                "awards": [{"items": items}],
            }
            if r % 17 == 0:
                record["awards"] = []
                record["tender"]["items"] = items[:1]
            if r % 23 == 0:
                record["awards"][0:0] = (
                    [{"items": [{"id": "x", "description": "sin codigo", "classification": {}}]}]
                    if record["awards"]
                    else []
                )
            records.append(record)
        out[year] = records
    return out


def write_raw(dest: Path, records: dict[int, list[dict[str, Any]]]) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    for year, recs in records.items():
        with gzip.open(dest / f"{year}.jsonl.gz", "wt", encoding="utf-8") as fh:
            for rec in recs:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return dest


@pytest.fixture(scope="session")
def settings() -> Settings:
    return load_settings(ROOT / "configs")


@pytest.fixture(scope="session")
def synthetic_workspace(
    tmp_path_factory: pytest.TempPathFactory, settings: Settings
) -> dict[str, Any]:
    """Raw ficticio → ingesta → dataset, en una carpeta temporal (compartido entre pruebas)."""
    from cpcmini.data.dataset import build_dataset
    from cpcmini.data.ingest import ingest_years

    base = tmp_path_factory.mktemp("ws")
    years = [2021, 2022, 2023, 2024, 2025, 2026]
    records = make_records(years, per_year=160)
    write_raw(base / "raw", records)
    paths = settings.data.paths.model_copy(
        update={
            "interim_dir": str(base / "interim"),
            "processed_dir": str(base / "processed"),
            "manifest": str(base / "processed" / "manifest.json"),
        }
    )
    source = settings.data.source.model_copy(update={"years": years, "raw_dir": str(base / "raw")})
    data_cfg = settings.data.model_copy(update={"paths": paths, "source": source})
    counts = ingest_years(data_cfg, workers=1)
    manifest = build_dataset(data_cfg)
    return {
        "base": base,
        "data_cfg": data_cfg,
        "records": records,
        "ingested": counts,
        "manifest": manifest,
    }
