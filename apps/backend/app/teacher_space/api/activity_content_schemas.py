from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.education.application.content_links import (
    ContentStatusValue,
    ContentTypeValue,
    ResolvedActivityContent,
)


class AttachActivityContentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_id: UUID


class ActivityContentLinkResponse(BaseModel):
    activity_id: UUID
    content_id: UUID


class ActivityContentReferenceResponse(BaseModel):
    id: UUID
    type: ContentTypeValue | None
    status: ContentStatusValue | None
    available_for_student: bool

    @classmethod
    def from_resolved(
        cls,
        resolved: ResolvedActivityContent,
    ) -> "ActivityContentReferenceResponse":
        return cls(
            id=resolved.link.content_id,
            type=resolved.type,
            status=resolved.status,
            available_for_student=resolved.available_for_student,
        )
