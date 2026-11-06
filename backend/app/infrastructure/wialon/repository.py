"""Implementación del puerto sobre el gateway de Wialon (patrón Adapter)."""

from typing import Any

from app.infrastructure.wialon.client import WialonClient
from app.domain.exceptions import ExternalServiceError

# 1 (base) + 8 (campos personalizados) + 1024 (última posición)
FLAGS_UNIDAD = 1033
# 1 (base) + 256 (conductores del recurso)
FLAGS_RECURSO_CONDUCTORES = 257


class WialonFleetRepository:
    def __init__(self, client: WialonClient) -> None:
        self._client = client

    async def list_units(self) -> list[dict[str, Any]]:
        datos = await self._client.call(
            "core/search_items",
            {
                "spec": {
                    "itemsType": "avl_unit",
                    "propName": "sys_name",
                    "propValueMask": "*",
                    "sortType": "sys_name",
                },
                "force": 1,
                "flags": FLAGS_UNIDAD,
                "from": 0,
                "to": 0,
            },
        )
        return datos.get("items") or []

    async def get_unit(self, unit_id: int) -> dict[str, Any] | None:
        datos = await self._client.call(
            "core/search_item", {"id": unit_id, "flags": FLAGS_UNIDAD}
        )
        return datos.get("item")

    async def list_drivers(self, resource_id: int) -> list[dict[str, Any]]:
        datos = await self._client.call(
            "core/search_item", {"id": resource_id, "flags": FLAGS_RECURSO_CONDUCTORES}
        )
        item = datos.get("item") or {}
        return list((item.get("drvrs") or {}).values())

    # ───────────────────────── escrituras ─────────────────────────

    async def get_driver(self, resource_id: int, driver_id: int) -> dict[str, Any] | None:
        """Lee un conductor completo. Base del patrón leer-mezclar-escribir."""
        for bruto in await self.list_drivers(resource_id):
            if int(bruto.get("id", -1)) == driver_id:
                return bruto
        return None

    async def save_driver(self, resource_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        """Crea o actualiza. `payload` DEBE traer el objeto completo.

        Wialon trata la actualización como reemplazo: lo que no mandas, se
        pierde. El servicio arma el objeto completo antes de llamar aquí.
        """
        datos = await self._client.call(
            "resource/update_driver",
            {"itemId": resource_id, **payload},
            usar_cache=False,
        )
        # Respuesta: [id, objeto]
        if isinstance(datos, list) and len(datos) == 2 and datos[1]:
            return datos[1]
        raise ExternalServiceError("Wialon no devolvió el conductor guardado")

    async def delete_driver(self, resource_id: int, driver_id: int) -> None:
        await self._client.call(
            "resource/update_driver",
            {"itemId": resource_id, "id": driver_id, "callMode": "delete"},
            usar_cache=False,
        )

    async def bind_driver(
        self, resource_id: int, *, unit_id: int, driver_id: int, bind: bool
    ) -> None:
        await self._client.call(
            "resource/bind_unit_driver",
            {
                "resourceId": resource_id,
                "unitId": unit_id,
                "driverId": driver_id,
                "time": 0,
                "mode": 1 if bind else 0,
            },
            usar_cache=False,
        )
