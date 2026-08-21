"""Identity domain models without framework or persistence dependencies."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class IdentityStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


@dataclass(frozen=True, slots=True)
class Identity:
    id: UUID
    email: str
    password_hash: str
    status: IdentityStatus
    created_at: datetime
    updated_at: datetime
