from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.content.public import ContentReference, ContentStatus, ContentType


class AttachActivityContentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_id: UUID


class ActivityContentLinkResponse(BaseModel):
    activity_id: UUID
    content_id: UUID


class ActivityContentReferenceResponse(BaseModel):
    id: UUID
    type: ContentType | None
    status: ContentStatus | None
    available_for_student: bool

    @classmethod
    def from_reference(
        cls,
        content_id: UUID,
        reference: ContentReference | None,
    ) -> "ActivityContentReferenceResponse":
        if reference is None:
            return cls(
                id=content_id,
                type=None,
                status=None,
                available_for_student=False,
            )
        return cls(
            id=reference.id,
            type=reference.type,
            status=reference.status,
            available_for_student=reference.available_for_student,
        )
