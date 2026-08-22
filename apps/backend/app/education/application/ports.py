"""Education application-owned persistence interfaces."""

from typing import Protocol
from uuid import UUID

from app.education.domain.models import EducationalEnvironment


class EnvironmentRepository(Protocol):
    def add(self, environment: EducationalEnvironment) -> EducationalEnvironment: ...
    def get_by_teacher_space(self, teacher_space_id: UUID) -> EducationalEnvironment | None: ...
    def update(self, environment: EducationalEnvironment) -> EducationalEnvironment: ...
