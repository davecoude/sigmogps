"""Errores de negocio. No conocen HTTP ni FastAPI: la capa de API los traduce."""


class DomainError(Exception):
    """Raíz de todos los errores de negocio."""

    title = "Error de dominio"
    status_code = 400

    def __init__(self, detail: str = "", **context: object) -> None:
        self.detail = detail or self.title
        self.context = context
        super().__init__(self.detail)


class NotFoundError(DomainError):
    title = "Recurso no encontrado"
    status_code = 404


class ConflictError(DomainError):
    title = "Conflicto con el estado actual"
    status_code = 409


class ValidationError(DomainError):
    title = "Datos inválidos"
    status_code = 422


class PermissionDeniedError(DomainError):
    title = "Permiso denegado"
    status_code = 403


class AuthenticationError(DomainError):
    title = "No autenticado"
    status_code = 401


class ExternalServiceError(DomainError):
    """Wialon respondió mal, tarde o no respondió."""

    title = "Servicio externo no disponible"
    status_code = 502
