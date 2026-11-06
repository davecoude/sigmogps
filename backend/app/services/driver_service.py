"""Casos de uso de conductores (RF-16, RF-17, RF-18).

La regla que gobierna este módulo: Wialon trata `resource/update_driver` como
un reemplazo, no como un parche. Editar el nombre sin reenviar `jp` borra los
campos personalizados del conductor. Por eso toda escritura pasa por
leer-mezclar-escribir y nunca se construye el objeto desde cero.
"""

from dataclasses import dataclass

from app.domain.exceptions import ConflictError, NotFoundError, ValidationError
from app.domain.models import Driver
from app.infrastructure.wialon.mappers import map_driver
from app.infrastructure.wialon.repository import WialonFleetRepository


@dataclass(frozen=True, slots=True)
class DriverInput:
    name: str
    code: str | None = None
    phone: str | None = None
    description: str | None = None
    custom_fields: dict[str, str] | None = None


class DriverService:
    def __init__(self, repo: WialonFleetRepository, *, resource_id: int) -> None:
        self._repo = repo
        self._resource_id = resource_id

    # ───────────────────────── lectura ─────────────────────────

    async def list_drivers(self, *, search: str | None = None) -> list[Driver]:
        crudos = await self._repo.list_drivers(self._resource_id)
        conductores = [map_driver(c, resource_id=self._resource_id) for c in crudos]

        if search:
            aguja = search.strip().lower()
            conductores = [
                d
                for d in conductores
                if aguja in d.name.lower()
                or (d.code and aguja in d.code.lower())
                or (d.phone and aguja in d.phone.lower())
            ]

        conductores.sort(key=lambda d: d.name.lower())
        return conductores

    async def get_driver(self, driver_id: int) -> Driver:
        bruto = await self._repo.get_driver(self._resource_id, driver_id)
        if bruto is None:
            raise NotFoundError("El conductor no existe.")
        return map_driver(bruto, resource_id=self._resource_id)

    # ───────────────────────── escritura ─────────────────────────

    def _validar(self, datos: DriverInput) -> None:
        if not datos.name or not datos.name.strip():
            raise ValidationError("El nombre es obligatorio.")
        if len(datos.name.strip()) > 120:
            raise ValidationError("El nombre no puede superar los 120 caracteres.")
        if datos.phone and not datos.phone.strip().lstrip("+").replace(" ", "").isdigit():
            raise ValidationError("El teléfono solo admite dígitos y un + inicial.")

    async def _codigo_duplicado(self, codigo: str, *, excepto: int | None = None) -> bool:
        if not codigo.strip():
            return False
        objetivo = codigo.strip().lower()
        for d in await self.list_drivers():
            if d.id != excepto and d.code and d.code.lower() == objetivo:
                return True
        return False

    async def create_driver(self, datos: DriverInput) -> Driver:
        self._validar(datos)
        if datos.code and await self._codigo_duplicado(datos.code):
            raise ConflictError(f"Ya existe un conductor con el código {datos.code}.")

        guardado = await self._repo.save_driver(
            self._resource_id,
            {
                "id": 0,
                "callMode": "create",
                "n": datos.name.strip(),
                "c": (datos.code or "").strip(),
                "ds": (datos.description or "").strip(),
                "p": (datos.phone or "").strip(),
                "f": 0,
                "pwd": "",
                "jp": datos.custom_fields or {},
            },
        )
        return map_driver(guardado, resource_id=self._resource_id)

    async def update_driver(self, driver_id: int, datos: DriverInput) -> Driver:
        self._validar(datos)

        # Leer. Sin esto, los campos que no vengan en el formulario se pierden.
        actual = await self._repo.get_driver(self._resource_id, driver_id)
        if actual is None:
            raise NotFoundError("El conductor no existe.")

        if datos.code and await self._codigo_duplicado(datos.code, excepto=driver_id):
            raise ConflictError(f"Ya existe un conductor con el código {datos.code}.")

        # Mezclar: lo que el formulario no toca conserva su valor actual.
        campos = (
            datos.custom_fields
            if datos.custom_fields is not None
            else {k: str(v) for k, v in (actual.get("jp") or {}).items()}
        )

        guardado = await self._repo.save_driver(
            self._resource_id,
            {
                "id": driver_id,
                "callMode": "update",
                "n": datos.name.strip(),
                "c": (datos.code or "").strip(),
                "ds": (datos.description or "").strip(),
                "p": (datos.phone or "").strip(),
                "f": int(actual.get("f") or 0),
                "pwd": str(actual.get("pwd") or ""),
                "jp": campos,
            },
        )
        return map_driver(guardado, resource_id=self._resource_id)

    async def delete_driver(self, driver_id: int) -> None:
        if await self._repo.get_driver(self._resource_id, driver_id) is None:
            raise NotFoundError("El conductor no existe.")
        await self._repo.delete_driver(self._resource_id, driver_id)

    # ───────────────────────── vínculos ─────────────────────────

    async def bind(self, *, driver_id: int, unit_id: int) -> None:
        conductor = await self.get_driver(driver_id)
        if conductor.bound_unit_id == unit_id:
            raise ConflictError("El conductor ya está vinculado a ese vehículo.")
        await self._repo.bind_driver(
            self._resource_id, unit_id=unit_id, driver_id=driver_id, bind=True
        )

    async def unbind(self, *, driver_id: int, unit_id: int) -> None:
        await self._repo.bind_driver(
            self._resource_id, unit_id=unit_id, driver_id=driver_id, bind=False
        )
