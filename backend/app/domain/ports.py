"""Puertos: lo que el dominio necesita, sin decir quién lo provee.

Son `Protocol`, no clases base: la implementación no tiene que heredar nada y
un doble de prueba es cualquier objeto con los mismos métodos.
"""

from typing import Any, Protocol


class FleetProvider(Protocol):
    """Fuente de datos de flota. Hoy Wialon; mañana cualquier otra."""

    async def list_units(self) -> list[dict[str, Any]]: ...

    async def get_unit(self, unit_id: int) -> dict[str, Any] | None: ...

    async def list_drivers(self, resource_id: int) -> list[dict[str, Any]]: ...
