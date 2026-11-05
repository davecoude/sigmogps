"""Contrato de paginación, uniforme en todo el API (ARQ-04)."""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PageMeta(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int


class PagedResponse(BaseModel, Generic[T]):
    items: list[T]
    meta: PageMeta
