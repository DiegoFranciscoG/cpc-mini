# syntax=docker/dockerfile:1
# API de CPC-mini. Etapa de construcción: dependencias y modelo de demostración (entrenado con la
# muestra pública versionada). Imagen final sin herramientas de compilación, con usuario sin privilegios.

FROM ghcr.io/astral-sh/uv:0.13.8 AS uv

FROM python:3.13.18-slim AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable
COPY configs ./configs
COPY sample_data ./sample_data
COPY alembic.ini ./
COPY migrations ./migrations
ENV PATH="/opt/venv/bin:$PATH" CPCMINI_DATABASE_URL="sqlite:////app/data/cpcmini.db"
RUN mkdir -p data \
 && cpcmini rebuild --override configs/sample.yaml --models tfidf_knn,tfidf_logreg --reports build/sample/reports \
 && cp -r build/sample/artifacts/serving /app/serving

FROM python:3.13.18-slim AS runtime
LABEL org.opencontainers.image.title="cpc-mini-api" \
      org.opencontainers.image.description="API que sugiere códigos CPC para compras públicas de Ecuador" \
      org.opencontainers.image.licenses="MIT"
ENV PATH="/opt/venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
# Parches de seguridad del sistema y sin pip (la app usa el entorno de uv; pip trae dependencias vendorizadas).
RUN apt-get update \
 && apt-get upgrade -y \
 && rm -rf /var/lib/apt/lists/* \
 && python -m pip uninstall -y pip \
 && groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --no-create-home app
WORKDIR /app
COPY --from=build /opt/venv /opt/venv
COPY --chown=app:app configs ./configs
COPY --chown=app:app alembic.ini ./
COPY --chown=app:app migrations ./migrations
COPY --from=build --chown=app:app /app/serving ./artifacts/serving
COPY --from=build --chown=app:app /app/data/cpcmini.db ./data/cpcmini.db
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=4).status == 200 else 1)"]
CMD ["uvicorn", "cpcmini.serve.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--proxy-headers", "--forwarded-allow-ips", "*"]
