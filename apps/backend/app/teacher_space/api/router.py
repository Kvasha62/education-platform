"""Authenticated, owner-scoped Teacher Space endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.identity.api.dependencies import get_current_identity, require_trusted_origin
from app.identity.domain.models import Identity
from app.teacher_space.api.dependencies import get_teacher_space_service
from app.teacher_space.api.schemas import (
    CreateTeacherSpaceRequest,
    TeacherSpaceResponse,
    UpdateTeacherSpaceRequest,
)
from app.teacher_space.application.errors import TeacherSpaceNotFoundError
from app.teacher_space.application.services import TeacherSpaceService
from app.teacher_space.domain.models import (
    InvalidTeacherSpaceTransitionError,
    TeacherSpaceDisabledError,
)

router = APIRouter(prefix="/api/v1/teacher-spaces", tags=["teacher-spaces"])

CurrentIdentity = Annotated[Identity, Depends(get_current_identity)]
TeacherSpaces = Annotated[TeacherSpaceService, Depends(get_teacher_space_service)]


def not_found(error: TeacherSpaceNotFoundError) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, "Teacher Space not found")


@router.post(
    "",
    response_model=TeacherSpaceResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_trusted_origin)],
)
def create_teacher_space(
    payload: CreateTeacherSpaceRequest,
    identity: CurrentIdentity,
    service: TeacherSpaces,
) -> TeacherSpaceResponse:
    teacher_space = service.create(identity.id, payload.name)
    return TeacherSpaceResponse.from_teacher_space(teacher_space)


@router.get("", response_model=list[TeacherSpaceResponse])
def list_teacher_spaces(
    identity: CurrentIdentity,
    service: TeacherSpaces,
) -> list[TeacherSpaceResponse]:
    return [
        TeacherSpaceResponse.from_teacher_space(item)
        for item in service.list_owned(identity.id)
    ]


@router.get("/{teacher_space_id}", response_model=TeacherSpaceResponse)
def get_teacher_space(
    teacher_space_id: UUID,
    identity: CurrentIdentity,
    service: TeacherSpaces,
) -> TeacherSpaceResponse:
    try:
        teacher_space = service.get_owned(teacher_space_id, identity.id)
    except TeacherSpaceNotFoundError as error:
        raise not_found(error) from error
    return TeacherSpaceResponse.from_teacher_space(teacher_space)


@router.patch(
    "/{teacher_space_id}",
    response_model=TeacherSpaceResponse,
    dependencies=[Depends(require_trusted_origin)],
)
def update_teacher_space(
    teacher_space_id: UUID,
    payload: UpdateTeacherSpaceRequest,
    identity: CurrentIdentity,
    service: TeacherSpaces,
) -> TeacherSpaceResponse:
    try:
        teacher_space = service.rename(teacher_space_id, identity.id, payload.name)
    except TeacherSpaceNotFoundError as error:
        raise not_found(error) from error
    except TeacherSpaceDisabledError as error:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Disabled Teacher Space is read-only"
        ) from error
    return TeacherSpaceResponse.from_teacher_space(teacher_space)


@router.post(
    "/{teacher_space_id}/disable",
    response_model=TeacherSpaceResponse,
    dependencies=[Depends(require_trusted_origin)],
)
def disable_teacher_space(
    teacher_space_id: UUID,
    identity: CurrentIdentity,
    service: TeacherSpaces,
) -> TeacherSpaceResponse:
    try:
        teacher_space = service.disable(teacher_space_id, identity.id)
    except TeacherSpaceNotFoundError as error:
        raise not_found(error) from error
    except InvalidTeacherSpaceTransitionError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, "Teacher Space is already disabled") from error
    return TeacherSpaceResponse.from_teacher_space(teacher_space)
