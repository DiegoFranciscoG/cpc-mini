"""API REST de CPC-mini (FastAPI). Sólo lectura: no guarda las descripciones que recibe."""

import logging
import time
from collections.abc import Awaitable, Callable, Iterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Path, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, sessionmaker
from starlette.responses import Response

from cpcmini import __version__
from cpcmini.config import Settings, load_settings
from cpcmini.db.repository import CatalogRepository, make_engine, make_session_factory
from cpcmini.models.registry import load_meta, load_model
from cpcmini.serve.schemas import (
    BatchOut,
    BatchRequest,
    CodeOut,
    HealthOut,
    ModelInfoOut,
    PredictionOut,
    PredictionRequest,
    SubsetOut,
)
from cpcmini.serve.security import (
    BodySizeMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    TokenBucket,
)
from cpcmini.serve.service import INTENDED_USE, NOT_INTENDED_USE, Predictor
from cpcmini.serve.settings import ApiSettings

log = logging.getLogger("cpcmini.api")
CODE_PATTERN = r"^\d{9}$"


@dataclass
class AppState:
    settings: Settings
    predictor: Predictor
    sessions: sessionmaker[Session]


def build_state(api: ApiSettings) -> AppState:
    settings = load_settings(api.config_dir)
    model = load_model(api.model_dir)
    meta = load_meta(api.model_dir)
    sessions = make_session_factory(make_engine(api.database_url))
    return AppState(settings, Predictor.build(model, meta, settings), sessions)


def create_app(api: ApiSettings | None = None, state: AppState | None = None) -> FastAPI:
    api = api or ApiSettings()  # type: ignore[call-arg]  # pydantic-settings lee el entorno
    holder: dict[str, AppState] = {}

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> Any:
        holder["state"] = state or build_state(api)
        yield
        holder.clear()

    app = FastAPI(
        title="CPC-mini API",
        version=__version__,
        description=(
            "Sugiere códigos CPC para descripciones de compras públicas de Ecuador. "
            "Datos: SERCOP vía OCP Data Registry, CC BY 3.0 EC. No es un servicio oficial."
        ),
        docs_url="/docs" if api.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if api.docs_enabled else None,
        lifespan=lifespan,
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=api.origins(),
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        allow_credentials=False,
        max_age=600,
    )
    app.add_middleware(BodySizeMiddleware, max_bytes=api.max_body_bytes)
    app.add_middleware(
        RateLimitMiddleware,
        bucket=TokenBucket(api.rate_limit_per_minute),
        trust_proxy=api.trust_proxy_headers,
    )

    @app.middleware("http")
    async def access_log(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        # Nunca se registra el cuerpo (la descripción del usuario): minimización de datos.
        log.info(
            "%s %s %s %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            (time.perf_counter() - start) * 1000,
        )
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"campo": ".".join(str(p) for p in e.get("loc", [])[1:]), "mensaje": e.get("msg", "")}
            for e in exc.errors()
        ]
        return JSONResponse({"detail": "Solicitud inválida", "errores": errors}, status_code=422)

    @app.exception_handler(Exception)
    async def unexpected(_: Request, exc: Exception) -> JSONResponse:
        log.error("Error no controlado: %s", type(exc).__name__)
        return JSONResponse(
            {"detail": "Error interno. Intenta de nuevo más tarde."}, status_code=500
        )

    def get_state() -> AppState:
        return holder["state"]

    def get_catalog(st: Annotated[AppState, Depends(get_state)]) -> Iterator[CatalogRepository]:
        with st.sessions() as session:
            yield CatalogRepository(session)

    StateDep = Annotated[AppState, Depends(get_state)]  # noqa: N806 - alias de tipo
    CatalogDep = Annotated[CatalogRepository, Depends(get_catalog)]  # noqa: N806 - alias de tipo

    @app.get("/api/v1/health", response_model=HealthOut, tags=["salud"])
    def health(st: StateDep, catalog: CatalogDep) -> HealthOut:
        return HealthOut(
            status="ok", model_loaded=st.predictor is not None, catalog_codes=catalog.count()
        )

    @app.get("/api/v1/model", response_model=ModelInfoOut, tags=["modelo"])
    def model_info(st: StateDep) -> ModelInfoOut:
        meta, src = st.predictor.meta, st.settings.data.source
        test = meta.metrics.get("test", {})
        flat: dict[str, float] = {}
        intervals: dict[str, tuple[float, float]] = {}
        for level in ("level_5", "level_9"):
            for key in ("top1", "top3", "macro_f1"):
                value = test.get(level, {}).get(key)
                if isinstance(value, dict):
                    flat[f"{level}_{key}"] = float(value["value"])
                    if "low" in value and "high" in value:
                        intervals[f"{level}_{key}"] = (float(value["low"]), float(value["high"]))
        subsets = {
            name: SubsetOut(
                n=int(block["level_9"]["n"]),
                top1=float(block["level_9"]["top1"]),
                top3=float(block["level_9"]["top3"]),
            )
            for name, block in test.get("subsets", {}).items()
        }
        latency = meta.metrics.get("latency_cpu", {}).get("p50_ms")
        size = meta.metrics.get("size_mb")
        abst = test.get("abstention", {})
        if abst:
            flat["coverage_at_threshold"] = float(abst.get("coverage", 0.0))
            flat["answered_top1"] = float(abst.get("answered_top1", 0.0))
        return ModelInfoOut(
            name=meta.name,
            family=meta.family,
            dataset_hash=meta.dataset_hash,
            trained_at=meta.trained_at,
            threshold=meta.threshold,
            target_precision=st.settings.eval.target_precision,
            metrics=flat,
            intervals=intervals,
            subsets=subsets,
            latency_ms_p50=float(latency) if latency is not None else None,
            size_mb=float(size) if size is not None else None,
            data_attribution=src.attribution,
            data_license=src.license,
            data_license_url=src.license_url,
            intended_use=INTENDED_USE,
            not_intended_use=NOT_INTENDED_USE,
        )

    @app.post("/api/v1/predictions", response_model=PredictionOut, tags=["predicción"])
    def predict(body: PredictionRequest, st: StateDep, catalog: CatalogDep) -> PredictionOut:
        return st.predictor.predict([body.description], catalog)[0]

    @app.post("/api/v1/predictions/batch", response_model=BatchOut, tags=["predicción"])
    def predict_batch(body: BatchRequest, st: StateDep, catalog: CatalogDep) -> BatchOut:
        return BatchOut(results=st.predictor.predict(body.descriptions, catalog))

    @app.get("/api/v1/codes/{code9}", response_model=CodeOut, tags=["catálogo"])
    def get_code(code9: Annotated[str, Path(pattern=CODE_PATTERN)], catalog: CatalogDep) -> CodeOut:
        entry = catalog.get(code9)
        if entry is None:
            raise HTTPException(status_code=404, detail="Código no encontrado en el catálogo")
        return CodeOut(**entry.__dict__)

    @app.get("/api/v1/codes", response_model=list[CodeOut], tags=["catálogo"])
    def search_codes(
        catalog: CatalogDep,
        q: Annotated[str, Query(min_length=2, max_length=60)],
        limit: Annotated[int, Query(ge=1, le=50)] = 20,
    ) -> list[CodeOut]:
        return [CodeOut(**e.__dict__) for e in catalog.search(q, limit)]

    return app
