"""Cabeceras de seguridad y limitador de peticiones (SEG-05, SEG-06).

Este módulo decide; `main.py` solo lo monta.
"""

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger
from app.core.problem import problem_response

logger = get_logger(__name__)

# El API responde JSON, nunca HTML. Por eso la política puede ser la más
# restrictiva que existe: no se permite cargar nada. Si un día una respuesta
# intentara ejecutar un script, el navegador lo bloquearía.
CSP_API = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"

# Swagger carga su JS y su CSS desde un CDN, así que en desarrollo la ruta de
# documentación necesita una política propia. En producción no existe (SEG-05).
CSP_DOCS = (
    "default-src 'none'; "
    "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "img-src 'self' https://fastapi.tiangolo.com data:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; base-uri 'none'"
)

RUTAS_DOCS = ("/docs", "/redoc", "/openapi.json")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Añade las cabeceras de seguridad a toda respuesta, incluidos los errores."""

    def __init__(self, app, *, es_produccion: bool) -> None:
        super().__init__(app)
        self._es_produccion = es_produccion

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        es_docs = any(request.url.path.startswith(r) for r in RUTAS_DOCS)
        response.headers["Content-Security-Policy"] = CSP_DOCS if es_docs else CSP_API

        # Impide que el navegador adivine el tipo de contenido y ejecute como
        # script algo que declaramos como JSON.
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Sin referente: las URLs del API llevan identificadores que no deben
        # viajar a terceros en la cabecera Referer.
        response.headers["Referrer-Policy"] = "no-referrer"

        # El API no se embebe en ningún marco. X-Frame-Options es redundante con
        # frame-ancestors, pero navegadores viejos solo entienden la primera.
        response.headers["X-Frame-Options"] = "DENY"

        response.headers["Permissions-Policy"] = (
            "geolocation=(), camera=(), microphone=(), payment=(), usb=()"
        )
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"

        # Las respuestas llevan datos de sesión: no deben quedar en el caché
        # del navegador ni en un proxy intermedio.
        if not es_docs:
            response.headers["Cache-Control"] = "no-store"

        # HSTS solo en producción: en local no hay HTTPS y fijarlo rompería el
        # acceso a localhost durante el plazo declarado.
        if self._es_produccion:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        return response


def ip_del_cliente(request: Request) -> str:
    """IP real detrás del proxy.

    Render y Vercel fijan `X-Forwarded-For`. La cabecera es falsificable si
    alguien llega al servicio sin pasar por el proxy, y por eso el limitador no
    es el control principal contra fuerza bruta: el bloqueo por usuario de
    `auth_service` sí lo es. Aquí solo se amortigua el volumen.
    """
    reenviado = request.headers.get("X-Forwarded-For")
    if reenviado:
        return reenviado.split(",")[0].strip()
    return request.client.host if request.client else "desconocido"


class VentanaDeslizante:
    """Cuenta peticiones por clave en una ventana de 60 segundos.

    En memoria del proceso: con más de una instancia cada una tendría su propio
    contador. Está declarado como limitación en el README. La alternativa
    (Redis) no existe en el plan gratuito.
    """

    VENTANA = 60.0

    def __init__(self) -> None:
        self._marcas: dict[str, deque[float]] = defaultdict(deque)

    def permitir(self, clave: str, limite: int) -> tuple[bool, int]:
        """Devuelve (permitido, segundos hasta que se libere un hueco)."""
        ahora = time.monotonic()
        marcas = self._marcas[clave]

        while marcas and ahora - marcas[0] > self.VENTANA:
            marcas.popleft()

        if len(marcas) >= limite:
            # Con límite cero la cola está vacía y no hay marca de la cual
            # derivar la espera: se informa la ventana completa.
            espera = (
                int(self.VENTANA - (ahora - marcas[0])) + 1 if marcas else int(self.VENTANA)
            )
            return False, espera

        marcas.append(ahora)
        return True, 0

    def limpiar(self) -> None:
        """Solo para las pruebas: reinicia los contadores."""
        self._marcas.clear()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Dos cubos por IP: uno general y uno más estrecho para el ingreso."""

    def __init__(
        self,
        app,
        *,
        limite_general: int,
        limite_login: int,
        rutas_estrechas: tuple[str, ...] = ("/auth/login",),
    ) -> None:
        super().__init__(app)
        self._limite_general = limite_general
        self._limite_login = limite_login
        self._rutas_estrechas = rutas_estrechas
        self.ventana = VentanaDeslizante()

    async def dispatch(self, request: Request, call_next) -> Response:
        ip = ip_del_cliente(request)
        es_estrecha = any(request.url.path.endswith(r) for r in self._rutas_estrechas)

        if es_estrecha:
            permitido, espera = self.ventana.permitir(f"login:{ip}", self._limite_login)
        else:
            permitido, espera = self.ventana.permitir(f"api:{ip}", self._limite_general)

        if not permitido:
            logger.warning(
                "rate_limit_excedido",
                ruta=request.url.path,
                metodo=request.method,
                estrecha=es_estrecha,
            )
            respuesta = problem_response(
                status=429,
                title="Demasiadas peticiones",
                detail=f"Espera {espera} segundos antes de volver a intentar.",
                instance=request.url.path,
                trace_id=getattr(request.state, "trace_id", "sin-trace"),
            )
            respuesta.headers["Retry-After"] = str(espera)
            return respuesta

        return await call_next(request)
