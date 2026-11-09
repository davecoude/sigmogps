"""Casos de uso de vehículos (RF-10 a RF-13).

Nota de diseño: Wialon pagina con `from`/`to`, pero no sabe filtrar por el
estado derivado ni buscar dentro de un campo personalizado, que es donde vive
la placa. Por eso se trae el conjunto completo una vez por ventana de caché y
el filtrado y la paginación ocurren aquí. Con 65 unidades es más barato que
una consulta por página; el enfoque deja de servir por encima de unas pocas
miles y queda documentado como límite conocido.
"""

import asyncio

from app.core.logging import get_logger
from app.domain.exceptions import NotFoundError, ValidationError
from app.domain.models import Vehicle, VehicleStatus
from app.domain.pagination import Page, paginar
from app.domain.ports import FleetProvider
from app.infrastructure.wialon.mappers import (
    map_custom_fields,
    map_driver,
    map_vehicle,
    normalizar_nombre_campo,
)

logger = get_logger(__name__)

LARGO_MAXIMO_NOMBRE = 60
LARGO_MAXIMO_VALOR = 255


class VehicleService:
    # Wialon tarda en exponer una escritura (medido en ~2,3 s para vínculos).
    # Se confirma antes de responder, igual que en el vínculo de conductores.
    _ESPERA_PROPAGACION = 4.0
    _INTERVALO_SONDEO = 0.4

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

        return paginar(vehiculos, page=page, page_size=page_size)

    async def get_vehicle(self, vehicle_id: int) -> Vehicle | None:
        for v in await self._vehiculos_con_conductor():
            if v.id == vehicle_id:
                return v
        return None

    # ───────── campos personalizados (RF-19, RF-20) ─────────

    async def replace_custom_fields(
        self, vehicle_id: int, campos: dict[str, str]
    ) -> Vehicle:
        """Reemplaza el conjunto completo de campos personalizados.

        Semántica de conjunto completo, igual que en pasajeros (RF-27): lo que
        no viene en `campos` se elimina. Enviar un subconjunto borraría el
        resto, así que el contrato es explícito y la operación es idempotente.

        Wialon expone un campo por llamada y no tiene operación por lote, así
        que se calcula la diferencia contra el estado actual: solo se escribe
        lo que cambió. Con quince campos y un valor editado eso es una llamada
        en vez de quince.

        Los nombres existentes se preservan tal cual los tiene el cliente. Si
        el nombre entrante coincide salvo acento o caja —los datos reales traen
        LINEA y LÍNEA, COLOR y COLORE—, se actualiza el valor sin renombrar el
        campo: renombrarlo en silencio sería corromper el dato del cliente.
        """
        limpios = self._validar_campos(campos)

        bruto = await self._provider.get_unit(vehicle_id)
        if bruto is None:
            raise NotFoundError("El vehículo no existe o no es visible para esta cuenta.")

        actuales = map_custom_fields(bruto.get("flds"))
        por_nombre = {normalizar_nombre_campo(c.name): c for c in actuales}
        entrantes = {normalizar_nombre_campo(n): (n, v) for n, v in limpios.items()}

        creados = actualizados = eliminados = 0

        for clave, (nombre, valor) in entrantes.items():
            existente = por_nombre.get(clave)
            if existente is None:
                await self._provider.create_unit_custom_field(
                    vehicle_id, name=nombre, value=valor
                )
                creados += 1
            elif existente.value != valor:
                # Se reenvía el nombre original, no el que llegó.
                await self._provider.update_unit_custom_field(
                    vehicle_id,
                    field_id=existente.id,
                    name=existente.name,
                    value=valor,
                )
                actualizados += 1

        for clave, existente in por_nombre.items():
            if clave not in entrantes:
                await self._provider.delete_unit_custom_field(vehicle_id, existente.id)
                eliminados += 1

        logger.info(
            "campos_personalizados_reemplazados",
            unidad=vehicle_id,
            creados=creados,
            actualizados=actualizados,
            eliminados=eliminados,
        )

        if creados or actualizados or eliminados:
            await self._esperar_propagacion(vehicle_id, entrantes)

        vehiculo = await self.get_vehicle(vehicle_id)
        if vehiculo is None:
            raise NotFoundError("El vehículo dejó de ser visible después de guardar.")
        return vehiculo

    def _validar_campos(self, campos: dict[str, str]) -> dict[str, str]:
        """Nombres no vacíos, sin duplicados ni siquiera por acento o caja."""
        limpios: dict[str, str] = {}
        vistos: dict[str, str] = {}

        for nombre_bruto, valor_bruto in campos.items():
            nombre = (nombre_bruto or "").strip()
            if not nombre:
                raise ValidationError("Hay un campo sin nombre.")
            if len(nombre) > LARGO_MAXIMO_NOMBRE:
                raise ValidationError(
                    f"El nombre «{nombre[:20]}…» supera {LARGO_MAXIMO_NOMBRE} caracteres."
                )

            valor = str(valor_bruto or "").strip()
            if len(valor) > LARGO_MAXIMO_VALOR:
                raise ValidationError(
                    f"El valor de «{nombre}» supera {LARGO_MAXIMO_VALOR} caracteres."
                )

            clave = normalizar_nombre_campo(nombre)
            if clave in vistos:
                raise ValidationError(
                    f"«{nombre}» y «{vistos[clave]}» son el mismo campo para Wialon."
                )
            vistos[clave] = nombre
            limpios[nombre] = valor

        return limpios

    async def _esperar_propagacion(
        self, vehicle_id: int, esperados: dict[str, tuple[str, str]]
    ) -> bool:
        """Sondea hasta que Wialon exponga el conjunto escrito.

        Que la respuesta sea `200` debe significar que el cambio ya es visible.
        Si no se confirma dentro del límite se registra y se continúa: el dato
        quedó escrito, solo no se pudo verificar a tiempo.
        """
        objetivo = {clave: valor for clave, (_, valor) in esperados.items()}
        limite = asyncio.get_running_loop().time() + self._ESPERA_PROPAGACION

        while asyncio.get_running_loop().time() < limite:
            bruto = await self._provider.get_unit(vehicle_id)
            actuales = map_custom_fields((bruto or {}).get("flds"))
            visto = {normalizar_nombre_campo(c.name): c.value for c in actuales}
            if visto == objetivo:
                return True
            await asyncio.sleep(self._INTERVALO_SONDEO)

        logger.warning("campos_personalizados_sin_confirmar", unidad=vehicle_id)
        return False

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
