"""Education-owned Activity / Content association."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ActivityContentLink:
    activity_id: UUID
    content_id: UUID
