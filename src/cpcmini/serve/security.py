"""Middlewares de seguridad: límite de solicitudes, tamaño de cuerpo y cabeceras."""

from __future__ import annotations

import threading
import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")
API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
DOCS_CSP = (
    "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; img-src 'self' data: "
    "https://fastapi.tiangolo.com; frame-ancestors 'none'; base-uri 'none'"
)


class TokenBucket:
    """Ventana deslizante simple por cliente (memoria del proceso; suficiente para una instancia)."""

    def __init__(self, per_minute: int, clock: Callable[[], float] = time.monotonic) -> None:
        self.capacity = float(per_minute)
        self.rate = per_minute / 60.0
        self.clock = clock
        self._state: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = self.clock()
        with self._lock:
            tokens, last = self._state.get(key, (self.capacity, now))
            tokens = min(self.capacity, tokens + (now - last) * self.rate)
            if tokens < 1.0:
                self._state[key] = (tokens, now)
                return False
            self._state[key] = (tokens - 1.0, now)
            if len(self._state) > 50_000:  # evita crecimiento sin límite
                self._state.clear()
            return True


def client_key(request: Request, trust_proxy: bool) -> str:
    if trust_proxy:
        real = request.headers.get("x-real-ip")
        if real:
            return real.strip()
    return request.client.host if request.client else "desconocido"


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, bucket: TokenBucket, trust_proxy: bool) -> None:
        super().__init__(app)
        self.bucket = bucket
        self.trust_proxy = trust_proxy

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        limited = request.url.path.startswith("/api/") and request.url.path != "/api/v1/health"
        if limited and not self.bucket.allow(client_key(request, self.trust_proxy)):
            return JSONResponse(
                {"detail": "Demasiadas solicitudes; intenta en un minuto."},
                status_code=429,
                headers={"Retry-After": "60"},
            )
        return await call_next(request)


class BodySizeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        length = request.headers.get("content-length")
        if length is not None and (not length.isdigit() or int(length) > self.max_bytes):
            return JSONResponse(
                {"detail": "Cuerpo de la solicitud demasiado grande."}, status_code=413
            )
        if request.method in ("POST", "PUT", "PATCH") and length is None:
            body = await request.body()
            if len(body) > self.max_bytes:
                return JSONResponse(
                    {"detail": "Cuerpo de la solicitud demasiado grande."}, status_code=413
                )
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        docs = request.url.path.startswith(DOCS_PATHS)
        response.headers["Content-Security-Policy"] = DOCS_CSP if docs else API_CSP
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response
