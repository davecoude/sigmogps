"""Logging estructurado sin datos sensibles (ARQ-07, SEG-02, SEG-09)."""

import logging
import sys

import structlog

CLAVES_SENSIBLES = {
    "password",
    "passwd",
    "secret",
    "secret_key",
    "token",
    "access_token",
    "refresh_token",
    "wialon_token",
    "authorization",
    "cookie",
    "set-cookie",
    "sid",
    "eid",
}


def redactar(_logger, _nombre_metodo, event_dict: dict) -> dict:
    """Sustituye cualquier valor cuya clave sea sensible. Última línea de defensa."""
    for clave in list(event_dict):
        if clave.lower() in CLAVES_SENSIBLES:
            event_dict[clave] = "[redactado]"
    return event_dict


def configurar_logging(nivel: str = "INFO", salida_json: bool = True) -> None:
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, nivel.upper(), logging.INFO),
    )

    procesadores = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        redactar,
    ]
    procesadores.append(
        structlog.processors.JSONRenderer()
        if salida_json
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    structlog.configure(
        processors=procesadores,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(nombre: str = "sigmogps"):
    return structlog.get_logger(nombre)
