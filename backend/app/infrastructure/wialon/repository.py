"""Implementación del puerto sobre el gateway de Wialon (patrón Adapter)."""

from typing import Any

from app.infrastructure.wialon.client import WialonClient
from app.domain.exceptions import ExternalServiceError
import time

# 1 (base) + 8 (campos personalizados) + 1024 (última posición)
FLAGS_UNIDAD = 1033
# 1 (base) + 256 (conductores del recurso)
FLAGS_RECURSO_CONDUCTORES = 257
# 1 (base) + 0x200000 (pasajeros del recurso)
# Ojo: 0x100000 son grupos de geocercas, no tags. Confundirlos devuelve una
# respuesta válida y vacía, indistinguible de «no hay pasajeros».
FLAGS_RECURSO_TAGS = 2097153


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

		    # ───────────────────────── pasajeros (tags) ─────────────────────────

    async def list_tags(self, resource_id: int) -> list[dict[str, Any]]:
        datos = await self._client.call(
            "core/search_item", {"id": resource_id, "flags": FLAGS_RECURSO_TAGS}
        )
        item = datos.get("item") or {}
        return list((item.get("tags") or {}).values())

    async def get_tag(self, resource_id: int, tag_id: int) -> dict[str, Any] | None:
        for bruto in await self.list_tags(resource_id):
            if int(bruto.get("id", -1)) == tag_id:
                return bruto
        return None

    async def save_tag(self, resource_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        """Crea o actualiza. `payload` DEBE traer el objeto completo.

        La documentación de Wialon es explícita: si se omite `jp`, los campos
        personalizados se borran. El servicio arma el objeto completo antes.
        """
        datos = await self._client.call(
            "resource/update_tag", {"itemId": resource_id, **payload}, usar_cache=False
        )
        if isinstance(datos, list) and len(datos) == 2 and datos[1]:
            return datos[1]
        raise ExternalServiceError("Wialon no devolvió el pasajero guardado")

    async def delete_tag(self, resource_id: int, tag_id: int) -> None:
        await self._client.call(
            "resource/update_tag",
            {"itemId": resource_id, "id": tag_id, "callMode": "delete"},
            usar_cache=False,
        )

    async def bind_tag(
        self, resource_id: int, *, unit_id: int, tag_id: int, bind: bool
    ) -> None:
        await self._client.call(
            "resource/bind_unit_tag",
            {
                "resourceId": resource_id,
                "unitId": unit_id,
                "tagId": tag_id,
                "time": 0,
                "mode": 1 if bind else 0,
            },
            usar_cache=False,
        )

    async def tag_bindings(self, resource_id: int) -> dict[int, int]:
        """Unidad asignada a cada pasajero, o nada si no tiene.

        El servicio devuelve el histórico de eventos por etiqueta, no el estado
        actual: hay que quedarse con el último de cada una. En un evento de
        asignación `u` trae la unidad; en uno de retiro, `u` viene en 0.
        """
        ahora = int(time.time())
        datos = await self._client.call(
            "resource/get_tag_bindings",
            {
                "resourceId": resource_id,
                "unitId": 0,  # todas
                "tagId": 0,  # todos
                "timeFrom": ahora - 60 * 60 * 24 * 90,
                "timeTo": ahora + 3600,
            },
        )
        actual: dict[int, int] = {}
        for clave, eventos in (datos or {}).items():
            try:
                tag_id = int(clave)
            except (TypeError, ValueError):
                continue
            if not eventos:
                continue
            ultimo = max(eventos, key=lambda e: int(e.get("t") or 0))
            unidad = int(ultimo.get("u") or 0)
            if unidad:
                actual[tag_id] = unidad
        return actual
