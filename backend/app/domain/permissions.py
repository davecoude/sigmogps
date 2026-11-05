"""Catálogo de permisos y matriz de roles (sección 5.3).

Única fuente de verdad: el seed la escribe en la base, la API la aplica y el
frontend construye su menú con lo que devuelve /me. Agregar un permiso aquí y
correr el seed es todo lo que hace falta para extender el sistema.
"""

from enum import StrEnum


class Permission(StrEnum):
    VEHICLES_READ = "vehicles:read"
    VEHICLES_WRITE = "vehicles:write"
    DRIVERS_READ = "drivers:read"
    DRIVERS_WRITE = "drivers:write"
    PASSENGERS_READ = "passengers:read"
    PASSENGERS_WRITE = "passengers:write"
    BINDINGS_WRITE = "bindings:write"
    HISTORY_READ = "history:read"
    EXPORT_CSV = "export:csv"
    USERS_MANAGE = "users:manage"
    AUDIT_READ = "audit:read"


class RoleName(StrEnum):
    ADMIN = "Admin"
    OPERATOR = "Operador"
    VIEWER = "Visualizador"


PERMISSION_DESCRIPTIONS: dict[Permission, str] = {
    Permission.VEHICLES_READ: "Ver vehículos, mapa y detalle",
    Permission.VEHICLES_WRITE: "Editar campos personalizados de vehículos",
    Permission.DRIVERS_READ: "Ver conductores",
    Permission.DRIVERS_WRITE: "Crear, editar y eliminar conductores",
    Permission.PASSENGERS_READ: "Ver pasajeros",
    Permission.PASSENGERS_WRITE: "Crear, editar y eliminar pasajeros",
    Permission.BINDINGS_WRITE: "Vincular y desvincular conductores y pasajeros",
    Permission.HISTORY_READ: "Ver historial de recorridos",
    Permission.EXPORT_CSV: "Exportar datos a CSV",
    Permission.USERS_MANAGE: "Gestionar usuarios y roles",
    Permission.AUDIT_READ: "Ver el registro de auditoría",
}

ROLE_DESCRIPTIONS: dict[RoleName, str] = {
    RoleName.ADMIN: "Control total, incluidos usuarios y auditoría",
    RoleName.OPERATOR: "Opera la flota: lee todo y edita conductores, pasajeros y vínculos",
    RoleName.VIEWER: "Solo consulta",
}

_READ_ONLY = frozenset(
    {
        Permission.VEHICLES_READ,
        Permission.DRIVERS_READ,
        Permission.PASSENGERS_READ,
        Permission.HISTORY_READ,
    }
)

ROLE_PERMISSIONS: dict[RoleName, frozenset[Permission]] = {
    RoleName.ADMIN: frozenset(Permission),
    RoleName.OPERATOR: _READ_ONLY
    | {
        Permission.VEHICLES_WRITE,
        Permission.DRIVERS_WRITE,
        Permission.PASSENGERS_WRITE,
        Permission.BINDINGS_WRITE,
        Permission.EXPORT_CSV,
    },
    RoleName.VIEWER: _READ_ONLY,
}
