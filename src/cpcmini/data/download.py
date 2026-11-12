"""Descarga de los archivos anuales del OCP Data Registry con verificación de integridad."""

from __future__ import annotations

import gzip
import hashlib
import json
import shutil
import urllib.request
from pathlib import Path

from cpcmini.config import SourceConfig

USER_AGENT = "cpcmini-dataset-builder/0.1"
ALLOWED_HOST = "https://data.open-contracting.org/"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download_year(cfg: SourceConfig, year: int, dest_dir: Path, force: bool = False) -> Path:
    url = cfg.url_template.format(year=year)
    if not url.startswith(ALLOWED_HOST):
        raise ValueError("La URL de origen debe ser del OCP Data Registry")
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / f"{year}.jsonl.gz"
    if target.exists() and not force:
        return target
    tmp = target.with_suffix(".part")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310
    with urllib.request.urlopen(request, timeout=120) as response, tmp.open("wb") as fh:  # noqa: S310
        shutil.copyfileobj(response, fh, length=1 << 20)
    with gzip.open(tmp, "rt", encoding="utf-8") as check:  # el archivo debe ser gzip+JSON válido
        json.loads(check.readline())
    tmp.replace(target)
    return target


def write_checksums(dest_dir: Path, years: list[int]) -> Path:
    sums = {
        str(y): sha256_of(dest_dir / f"{y}.jsonl.gz")
        for y in years
        if (dest_dir / f"{y}.jsonl.gz").exists()
    }
    out = dest_dir / "SHA256SUMS.json"
    out.write_text(json.dumps(sums, indent=2), encoding="utf-8")
    return out
