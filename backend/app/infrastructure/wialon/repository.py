"""Implementación del puerto sobre el gateway de Wialon (patrón Adapter)."""

from typing import Any

from app.infrastructure.wialon.client import WialonClient

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
