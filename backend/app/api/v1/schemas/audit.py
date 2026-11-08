"""DTOs del registro de auditoría (RF-26)."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.infrastructure.db.models import AuditLog


class AuditEntry(BaseModel):
    id: uuid.UUID
    action: str
    user_email: str | None
    entity_type: str | None
    entity_id: str | None
    success: bool
    detail: dict | None
    ip_address: str | None
    created_at: datetime

    @classmethod
    def from_domain(cls, a: AuditLog) -> "AuditEntry":
        return cls(
            id=a.id,
            action=a.action,
            user_email=a.user_email,
            entity_type=a.entity_type,
            entity_id=a.entity_id,
            success=a.success,
            detail=a.detail,
            ip_address=a.ip_address,
            created_at=a.created_at,
        )
