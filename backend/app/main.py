"""Composición de la aplicación. Este archivo arma, no decide."""

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.http_security import RateLimitMiddleware, SecurityHeadersMiddleware
from app.core.logging import configurar_logging, get_logger
from app.core.problem import registrar_manejadores
from app.infrastructure.wialon.client import close_wialon_client

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = get_settings()
    logger.info("arranque", env=settings.app_env, debug=settings.app_debug)
    yield
    await close_wialon_client()
    logger.info("apagado")


def create_app() -> FastAPI:
    settings = get_settings()
    settings.assert_production_ready()
    configurar_logging(nivel=settings.log_level, salida_json=settings.is_production)

    app = FastAPI(
        title=settings.app_name,
        description="API de monitoreo de flota conectada a Wialon.",
        version="0.1.0",
        docs_url=settings.docs_url,
        redoc_url=None,
        openapi_url=settings.openapi_url,
        lifespan=lifespan,
    )

    # CORS restringido a los orígenes declarados (SEG-01, DEP-03)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
    )

    # El orden importa: en Starlette el último middleware añadido es el más
    # externo. Se declaran de adentro hacia afuera para que las cabeceras de
    # seguridad envuelvan incluso al 429 del limitador, y para que el limitador
    # ya tenga disponible el trace_id cuando rechaza una petición.
    if settings.rate_limit_enabled:
        app.add_middleware(
            RateLimitMiddleware,
            limite_general=settings.rate_limit_per_minute,
            limite_login=settings.rate_limit_login_per_minute,
        )

    @app.middleware("http")
    async def trace_id_middleware(request: Request, call_next):
        """Un identificador por petición, para correlacionar logs y errores."""
        trace_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        request.state.trace_id = trace_id
        response = await call_next(request)
        response.headers["X-Request-Id"] = trace_id
        return response

    # Añadido al final: queda como el middleware más externo (SEG-05).
    app.add_middleware(SecurityHeadersMiddleware, es_produccion=settings.is_production)

    registrar_manejadores(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
