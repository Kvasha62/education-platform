from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class AssessmentResult:
    id: UUID
    attempt_id: UUID

    @classmethod
    def create(cls, attempt_id: UUID) -> "AssessmentResult":
        return cls(uuid4(), attempt_id)
