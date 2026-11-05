"""Formato de error uniforme RFC 7807 Problem Details (ARQ-04, SEG-10)."""

import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger
from app.domain.exceptions import DomainError

logger = get_logger(__name__)

CONTENT_TYPE = "application/problem+json"


def problem_response(
    *,
    status: int,
    title: str,
    detail: str,
    instance: str,
    trace_id: str,
    errors: list[dict] | None = None,
) -> JSONResponse:
    cuerpo: dict = {
        "type": f"https://sigmogps.app/errors/{status}",
        "title": title,
        "status": status,
        "detail": detail,
        "instance": instance,
        "trace_id": trace_id,
    }
    if errors:
        cuerpo["errors"] = errors
    return JSONResponse(status_code=status, content=cuerpo, media_type=CONTENT_TYPE)


def _trace_id(request: Request) -> str:
    return getattr(request.state, "trace_id", str(uuid.uuid4()))


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain(request: Request, exc: DomainError):
        trace_id = _trace_id(request)
        logger.warning(
            "error_dominio",
            tipo=exc.__class__.__name__,
            detalle=exc.detail,
            ruta=request.url.path,
            trace_id=trace_id,
            **exc.context,
        )
        return problem_response(
            status=exc.status_code,
            title=exc.title,
            detail=exc.detail,
            instance=request.url.path,
            trace_id=trace_id,
        )

    @app.exception_handler(RequestValidationError)
    async def _validacion(request: Request, exc: RequestValidationError):
        errores = [
            {
                "campo": ".".join(str(p) for p in e["loc"][1:]) or "cuerpo",
                "mensaje": e["msg"],
            }
            for e in exc.errors()
        ]
        return problem_response(
            status=422,
            title="Datos inválidos",
            detail="Revisa los campos marcados.",
            instance=request.url.path,
            trace_id=_trace_id(request),
            errors=errores,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        return problem_response(
            status=exc.status_code,
            title=str(exc.detail),
            detail=str(exc.detail),
            instance=request.url.path,
            trace_id=_trace_id(request),
        )

    @app.exception_handler(Exception)
    async def _no_controlado(request: Request, exc: Exception):
        """Nunca expone el stack trace al cliente (SEG-10)."""
        trace_id = _trace_id(request)
        logger.exception(
            "error_no_controlado",
            ruta=request.url.path,
            metodo=request.method,
            trace_id=trace_id,
        )
        return problem_response(
            status=500,
            title="Error interno",
            detail="Ocurrió un error inesperado. Usa el trace_id para reportarlo.",
            instance=request.url.path,
            trace_id=trace_id,
        )
