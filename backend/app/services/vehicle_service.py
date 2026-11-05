"""Casos de uso de vehículos (RF-10 a RF-13).

Nota de diseño: Wialon pagina con `from`/`to`, pero no sabe filtrar por el
estado derivado ni buscar dentro de un campo personalizado, que es donde vive
la placa. Por eso se trae el conjunto completo una vez por ventana de caché y
el filtrado y la paginación ocurren aquí. Con 65 unidades es más barato que
una consulta por página; el enfoque deja de servir por encima de unas pocas
miles y queda documentado como límite conocido.
"""

from dataclasses import dataclass

from app.domain.models import Vehicle, VehicleStatus
from app.domain.ports import FleetProvider
from app.infrastructure.wialon.mappers import map_driver, map_vehicle


@dataclass(frozen=True, slots=True)
class Page[T]:
    items: list[T]
    total: int
    page: int
    page_size: int

    @property
    def pages(self) -> int:
        return max(1, -(-self.total // self.page_size))


class VehicleService:
    def __init__(self, provider: FleetProvider, *, resource_id: int) -> None:
        self._provider = provider
        self._resource_id = resource_id

    async def _vehiculos_con_conductor(self) -> list[Vehicle]:
        crudos = await self._provider.list_units()
        vehiculos = [map_vehicle(c) for c in crudos if c]

        # Una sola lectura de conductores indexada por unidad vinculada (RF-13),
        # en vez de una consulta por vehículo.
        conductores = await self._provider.list_drivers(self._resource_id)
        por_unidad = {}
        for bruto in conductores:
            conductor = map_driver(bruto, resource_id=self._resource_id)
            if conductor.bound_unit_id:
                por_unidad[conductor.bound_unit_id] = conductor

        salida: list[Vehicle] = []
        for v in vehiculos:
            conductor = por_unidad.get(v.id)
            if conductor is None:
                salida.append(v)
            else:
                salida.append(
                    Vehicle(
                        id=v.id,
                        name=v.name,
                        plate=v.plate,
                        status=v.status,
                        position=v.position,
                        custom_fields=v.custom_fields,
                        driver_id=conductor.id,
                        driver_name=conductor.name or None,
                    )
                )
        return salida

    async def list_vehicles(
        self,
        *,
        search: str | None = None,
        status: VehicleStatus | None = None,
        only_without_driver: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> Page[Vehicle]:
        vehiculos = await self._vehiculos_con_conductor()

        if search:
            aguja = search.strip().lower()
            vehiculos = [
                v
                for v in vehiculos
                if aguja in v.name.lower()
                or (v.plate and aguja in v.plate.lower())
                or (v.driver_name and aguja in v.driver_name.lower())
            ]

        if status is not None:
            vehiculos = [v for v in vehiculos if v.status is status]

        if only_without_driver:
            vehiculos = [v for v in vehiculos if v.driver_id is None]

        # Orden estable: primero lo que exige atención, luego por nombre visible.
        prioridad = {
            VehicleStatus.OFFLINE: 0,
            VehicleStatus.MOVING: 1,
            VehicleStatus.STOPPED: 2,
        }
        vehiculos.sort(key=lambda v: (prioridad[v.status], v.display_name.lower()))

        total = len(vehiculos)
        inicio = (page - 1) * page_size
        return Page(
            items=vehiculos[inicio : inicio + page_size],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_vehicle(self, vehicle_id: int) -> Vehicle | None:
        for v in await self._vehiculos_con_conductor():
            if v.id == vehicle_id:
                return v
        return None

    async def summary(self) -> dict[str, int]:
        """KPIs del tablero (RF-23)."""
        vehiculos = await self._vehiculos_con_conductor()
        return {
            "total": len(vehiculos),
            "en_movimiento": sum(1 for v in vehiculos if v.status is VehicleStatus.MOVING),
            "detenidos": sum(1 for v in vehiculos if v.status is VehicleStatus.STOPPED),
            "sin_senal": sum(1 for v in vehiculos if v.status is VehicleStatus.OFFLINE),
            "con_conductor": sum(1 for v in vehiculos if v.driver_id is not None),
            "sin_conductor": sum(1 for v in vehiculos if v.driver_id is None),
        }
