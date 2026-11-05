"""Códigos de error de la API remota de Wialon, traducidos a excepciones propias (INT-05)."""

from app.domain.exceptions import (
    AuthenticationError,
    ConflictError,
    DomainError,
    ExternalServiceError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)


class WialonSessionExpired(ExternalServiceError):
    """La sesión murió. El cliente reintenta tras renovarla; no sale al usuario."""

    title = "Sesión de Wialon expirada"


# Fuente: https://help.wialon.com/en/api/user-guide/api-reference/error-codes
CODIGOS: dict[int, tuple[type[DomainError], str]] = {
    1: (WialonSessionExpired, "Sesión inválida"),
    2: (ExternalServiceError, "Servicio de Wialon inexistente"),
    3: (ExternalServiceError, "Wialon devolvió un resultado inválido"),
    4: (ValidationError, "Parámetros inválidos para Wialon"),
    5: (ExternalServiceError, "Wialon no pudo ejecutar la solicitud"),
    6: (ExternalServiceError, "Error desconocido de Wialon"),
    7: (PermissionDeniedError, "La cuenta no tiene acceso a este recurso en Wialon"),
    8: (AuthenticationError, "Credenciales de Wialon inválidas"),
    9: (ExternalServiceError, "El servidor de autorización de Wialon no responde"),
    1001: (NotFoundError, "No hay mensajes en el intervalo seleccionado"),
    1002: (ConflictError, "Ya existe un elemento con esa propiedad única"),
    1003: (ExternalServiceError, "Wialon solo acepta una solicitud a la vez"),
    1004: (ExternalServiceError, "Se excedió el límite de mensajes"),
    1005: (ExternalServiceError, "La solicitud excedió el tiempo límite en Wialon"),
    1011: (WialonSessionExpired, "La sesión expiró o cambió la IP"),
}


def traducir(codigo: int, *, servicio: str) -> DomainError:
    clase, mensaje = CODIGOS.get(
        codigo, (ExternalServiceError, f"Error {codigo} de Wialon")
    )
    return clase(mensaje, servicio=servicio, codigo_wialon=codigo)
