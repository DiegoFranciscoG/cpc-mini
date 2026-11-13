"""Muestra minimizada (sin partes ni datos personales) y descarga verificada, sin red."""

from __future__ import annotations

import gzip
import io
import json
from pathlib import Path

import pytest

from cpcmini.data import download as dl
from cpcmini.data.sample import build_sample, keep, minimize_record
from tests.conftest import make_records, write_raw


def test_minimize_record_drops_parties_and_amounts():
    record = {
        "ocid": "ocds-x",
        "date": "2024-01-01",
        "parties": [{"name": "Persona"}],
        "buyer": {"name": "Entidad"},
        "tender": {
            "procurementMethodDetails": "Subasta",
            "mainProcurementCategory": "goods",
            "value": {"amount": 10},
            "items": [
                {
                    "id": "1",
                    "description": "papel",
                    "classification": {"id": "1", "scheme": "CPC"},
                    "unit": {"value": {"amount": 3}},
                }
            ],
        },
        "awards": [{"suppliers": [{"name": "Proveedor"}], "items": []}],
    }
    small = minimize_record(record)
    text = json.dumps(small)
    assert "Persona" not in text and "Proveedor" not in text and "amount" not in text
    assert small["tender"]["items"][0]["description"] == "papel"


def test_keep_is_deterministic():
    assert keep("ocds-a", 3, 1) == keep("ocds-a", 3, 1)
    assert sum(keep(f"ocds-{i}", 10, 7) for i in range(1000)) in range(60, 140)


def test_build_sample_excludes_personal_data(settings, tmp_path):
    raw = write_raw(tmp_path / "raw", make_records([2024], per_year=120))
    source = settings.data.source.model_copy(update={"years": [2024], "raw_dir": str(raw)})
    cfg = settings.data.model_copy(update={"source": source})
    counts = build_sample(cfg, tmp_path / "out", rate=1, seed=1)
    with gzip.open(tmp_path / "out" / "2024.jsonl.gz", "rt", encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    assert counts[2024] == len(lines) < 120  # los procesos con teléfono se descartan
    assert not any("0991234567" in line for line in lines)


class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_download_year_validates_and_writes_checksums(settings, tmp_path, monkeypatch):
    payload = io.BytesIO()
    with gzip.open(payload, "wt", encoding="utf-8") as gz:
        gz.write(json.dumps({"ocid": "x"}) + "\n")
    monkeypatch.setattr(
        dl.urllib.request, "urlopen", lambda *a, **k: _FakeResponse(payload.getvalue())
    )
    target = dl.download_year(settings.data.source, 2024, tmp_path)
    assert target.exists()
    assert dl.download_year(settings.data.source, 2024, tmp_path) == target  # no vuelve a bajar
    sums = json.loads(dl.write_checksums(tmp_path, [2024, 2025]).read_text())
    assert list(sums) == ["2024"] and len(sums["2024"]) == 64


def test_download_rejects_foreign_hosts(settings, tmp_path):
    evil = settings.data.source.model_copy(update={"url_template": "https://example.com/{year}.gz"})
    with pytest.raises(ValueError, match="OCP Data Registry"):
        dl.download_year(evil, 2024, tmp_path)


def test_download_rejects_corrupt_files(settings, tmp_path, monkeypatch):
    monkeypatch.setattr(dl.urllib.request, "urlopen", lambda *a, **k: _FakeResponse(b"no es gzip"))
    with pytest.raises(gzip.BadGzipFile):
        dl.download_year(settings.data.source, 2023, tmp_path, force=True)
    assert not Path(tmp_path / "2023.jsonl.gz").exists()
    assert not Path(tmp_path / "2023.jsonl.part").exists()  # no deja archivos a medias
