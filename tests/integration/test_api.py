"""API: endpoints, validación, seguridad (CORS, cabeceras, límites) y migraciones."""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from cpcmini.db.repository import CatalogRepository, make_engine, make_session_factory
from cpcmini.models.hierarchical import HierarchicalLinear
from cpcmini.models.registry import ModelMeta
from cpcmini.serve.api import AppState, create_app
from cpcmini.serve.service import Predictor
from cpcmini.serve.settings import ApiSettings

ROOT = Path(__file__).resolve().parents[2]
ORIGIN = "http://localhost:8080"
TEXTS = [
    "paracetamol 500 mg tableta",
    "ibuprofeno 400 mg tableta",
    "resma papel bond a4 75 g",
    "limpieza de oficinas",
    "paracetamol jarabe 120 ml",
    "ibuprofeno 600 mg capsula",
]
CODES = ["352600111", "352600112", "321290418", "853300012", "352600111", "352600112"]


def _migrate(url: str) -> None:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.attributes["database_url"] = url
    command.upgrade(cfg, "head")


@pytest.fixture
def db_url(tmp_path):
    url = f"sqlite:///{(tmp_path / 'api.db').as_posix()}"
    _migrate(url)
    sessions = make_session_factory(make_engine(url))
    with sessions() as session:
        CatalogRepository(session).replace_all(
            [
                {
                    "code9": c,
                    "code5": c[:5],
                    "label": f"ETIQUETA {c}",
                    "n_items": 10 + i,
                    "first_year": 2015,
                    "last_year": 2026,
                }
                for i, c in enumerate(sorted(set(CODES)))
            ]
        )
    return url


def _client(settings, db_url, rate=100, threshold=0.0):
    cfg = settings.models.linear.model_copy(
        update={"max_features_char": 2000, "max_features_word": 500, "min_df": 1, "max_iter": 30}
    )
    model = HierarchicalLinear(cfg, seed=1).fit(TEXTS, CODES)
    meta = ModelMeta(
        name="tfidf_logreg",
        family="1. Base",
        temperature=1.0,
        threshold=threshold,
        dataset_hash="abc",
        trained_at="2026-11-12T00:00:00+00:00",
        train_rows=6,
        train_seconds=0.1,
        size_bytes=1,
        seed=1,
        metrics={
            "latency_cpu": {"p50_ms": 4.2},
            "size_mb": 12.5,
            "test": {
                "subsets": {"proceso_unico": {"level_9": {"n": 10, "top1": 0.4, "top3": 0.6}}},
                "level_9": {
                    "top1": {"value": 0.5},
                    "top3": {"value": 0.7},
                    "macro_f1": {"value": 0.3},
                },
                "abstention": {"coverage": 0.4, "answered_top1": 0.9},
            },
        },
    )
    state = AppState(
        settings, Predictor.build(model, meta, settings), make_session_factory(make_engine(db_url))
    )
    api = ApiSettings(
        database_url=db_url,
        model_dir="unused",
        cors_allowed_origins=ORIGIN,
        rate_limit_per_minute=rate,
        max_body_bytes=2048,
    )
    return TestClient(create_app(api, state))


def test_health_model_and_prediction(settings, db_url):
    with _client(settings, db_url) as client:
        health = client.get("/api/v1/health").json()
        assert health == {"status": "ok", "model_loaded": True, "catalog_codes": 4}
        info = client.get("/api/v1/model").json()
        assert "SERCOP" in info["data_attribution"] and info["data_license"] == "CC BY 3.0 EC"
        assert info["metrics"]["level_9_top1"] == 0.5
        assert info["intervals"] == {}
        assert info["subsets"]["proceso_unico"] == {"n": 10, "top1": 0.4, "top3": 0.6}
        assert info["latency_ms_p50"] == 4.2
        assert info["size_mb"] == 12.5
        res = client.post("/api/v1/predictions", json={"description": "  Paracetamol 500MG tab  "})
        assert res.status_code == 200
        body = res.json()
        assert body["description"] == "Paracetamol 500MG tab"
        assert body["candidates"][0]["code9"] == "352600111"
        assert body["candidates"][0]["label"] == "ETIQUETA 352600111"
        assert len(body["candidates"]) <= 3 and not body["abstained"]


def test_abstention_and_uninformative(settings, db_url):
    with _client(settings, db_url, threshold=1.01) as client:
        body = client.post("/api/v1/predictions", json={"description": "paracetamol 500 mg"}).json()
        assert body["abstained"] and body["message"].startswith("No sé")
        empty = client.post("/api/v1/predictions", json={"description": "ver pliegos"}).json()
        assert empty["abstained"] and empty["candidates"] == []


def test_batch_and_validation(settings, db_url):
    with _client(settings, db_url) as client:
        ok = client.post(
            "/api/v1/predictions/batch", json={"descriptions": ["paracetamol", "resma papel"]}
        )
        assert ok.status_code == 200 and len(ok.json()["results"]) == 2
        for bad in (
            {"description": "a"},
            {"description": "x" * 501},
            {"descripcion": "hola"},
            {"description": "ok ok", "extra": 1},
        ):
            res = client.post("/api/v1/predictions", json=bad)
            assert res.status_code == 422 and res.json()["detail"] == "Solicitud inválida"
        assert (
            client.post("/api/v1/predictions/batch", json={"descriptions": []}).status_code == 422
        )
        assert (
            client.post("/api/v1/predictions/batch", json={"descriptions": ["ok"] * 51}).status_code
            == 422
        )


def test_catalog_endpoints(settings, db_url):
    with _client(settings, db_url) as client:
        assert client.get("/api/v1/codes/352600111").json()["label"] == "ETIQUETA 352600111"
        assert client.get("/api/v1/codes/999999999").status_code == 404
        assert client.get("/api/v1/codes/12ab").status_code == 422
        found = client.get("/api/v1/codes", params={"q": "3526"}).json()
        assert [c["code9"] for c in found] == ["352600112", "352600111"]
        assert (
            client.get("/api/v1/codes", params={"q": "etiqueta 8533"}).json()[0]["code9"]
            == "853300012"
        )
        assert client.get("/api/v1/codes", params={"q": "100%_"}).json() == []


def test_security_headers_cors_and_limits(settings, db_url):
    with _client(settings, db_url, rate=3) as client:
        res = client.get("/api/v1/model", headers={"Origin": ORIGIN})
        assert res.headers["access-control-allow-origin"] == ORIGIN
        assert res.headers["x-content-type-options"] == "nosniff"
        assert res.headers["x-frame-options"] == "DENY"
        assert "default-src 'none'" in res.headers["content-security-policy"]
        assert res.headers["cache-control"] == "no-store"
        evil = client.get("/api/v1/model", headers={"Origin": "https://evil.example"})
        assert "access-control-allow-origin" not in evil.headers
        big = client.post(
            "/api/v1/predictions",
            content=b'{"description":"' + b"a" * 4000 + b'"}',
            headers={"Content-Type": "application/json"},
        )
        assert big.status_code == 413
        statuses = [client.get("/api/v1/model").status_code for _ in range(5)]
        assert 429 in statuses
        assert client.get("/api/v1/health").status_code == 200  # la salud no se limita
        docs = client.get("/docs")
        assert (
            docs.status_code == 200
            and "cdn.jsdelivr.net" in docs.headers["content-security-policy"]
        )


def test_errors_do_not_leak_internals(settings, db_url):
    with _client(settings, db_url) as client:
        client.app.state.boom = True

        @client.app.get("/api/v1/boom")
        def boom() -> None:
            raise RuntimeError("secreto interno")

        res = TestClient(client.app, raise_server_exceptions=False).get("/api/v1/boom")
        assert res.status_code == 500
        assert "secreto" not in res.text and "Traceback" not in res.text


def test_migrations_up_and_down(tmp_path):
    url = f"sqlite:///{(tmp_path / 'm.db').as_posix()}"
    _migrate(url)
    engine = make_engine(url)
    assert {"cpc_code", "dataset_version", "gold_item"} <= set(inspect(engine).get_table_names())
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.attributes["database_url"] = url
    command.downgrade(cfg, "base")
    assert "cpc_code" not in inspect(engine).get_table_names()


def test_catalog_constraints(db_url):
    from sqlalchemy.exc import IntegrityError

    sessions = make_session_factory(make_engine(db_url))
    with sessions() as session, pytest.raises(IntegrityError):
        CatalogRepository(session).replace_all(
            [
                {
                    "code9": "12345678X",
                    "code5": "12345",
                    "label": "",
                    "n_items": 1,
                    "first_year": 2020,
                    "last_year": 2020,
                }
            ]
        )


def test_gold_repository_flow(db_url):
    from cpcmini.db.repository import DatasetVersionRepository, GoldRepository

    sessions = make_session_factory(make_engine(db_url))
    with sessions() as session:
        version = DatasetVersionRepository(session).get_or_create(
            "h" * 64, "c" * 16, {"train": 1, "val": 1, "test": 1}, "CC BY 3.0 EC"
        )
        same = DatasetVersionRepository(session).get_or_create(
            "h" * 64, "c" * 16, {"train": 1, "val": 1, "test": 1}, "CC BY 3.0 EC"
        )
        assert same.id == version.id
        gold = GoldRepository(session)
        rows = [
            {"desc_norm": "a", "description": "A", "original_code9": "352600111", "stratum": "1-5"},
            {
                "desc_norm": "b",
                "description": "B",
                "original_code9": "352600112",
                "stratum": "6-20",
            },
        ]
        assert gold.add_candidates(version.id, rows) == 2
        assert gold.add_candidates(version.id, rows) == 0
        first = gold.pending(version.id)[0]
        gold.review(first, "corrected", "352600112", "DG", "dosis")
        assert [g.desc_norm for g in gold.reviewed(version.id)] == ["a"]
        assert len(gold.all(version.id)) == 2
