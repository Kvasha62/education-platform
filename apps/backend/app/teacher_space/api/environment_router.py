"""Teacher Space owner-facing Educational Environment endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.education.api.dependencies import get_environment_service
from app.education.api.schemas import (
    CreateEnvironmentRequest,
    EnvironmentResponse,
    UpdateEnvironmentRequest,
)
from app.education.application.errors import (
    EnvironmentAlreadyExistsError,
    EnvironmentNotFoundError,
)
from app.education.application.services import EducationalEnvironmentService
from app.identity.api.dependencies import get_current_identity, require_trusted_origin
from app.identity.domain.models import Identity
from app.teacher_space.api.dependencies import get_teacher_space_service
from app.teacher_space.application.errors import TeacherSpaceNotFoundError
from app.teacher_space.application.services import TeacherSpaceService
from app.teacher_space.domain.models import TeacherSpace, TeacherSpaceStatus

router = APIRouter(
    prefix="/api/v1/teacher-spaces/{teacher_space_id}/environment",
    tags=["educational-environments"],
)

CurrentIdentity = Annotated[Identity, Depends(get_current_identity)]
TeacherSpaces = Annotated[TeacherSpaceService, Depends(get_teacher_space_service)]
Environments = Annotated[
    EducationalEnvironmentService, Depends(get_environment_service)
]


def resolve_owned_teacher_space(
    teacher_space_id: UUID,
    owner_user_id: UUID,
    service: TeacherSpaceService,
) -> TeacherSpace:
    try:
        return service.get_owned(teacher_space_id, owner_user_id)
    except TeacherSpaceNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Teacher Space not found") from error


def require_writable(teacher_space: TeacherSpace) -> None:
    if teacher_space.status is TeacherSpaceStatus.DISABLED:
        raise HTTPException(status.HTTP_409_CONFLICT, "Disabled Teacher Space is read-only")


@router.post(
    "",
    response_model=EnvironmentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_trusted_origin)],
)
def create_environment(
    teacher_space_id: UUID,
    payload: CreateEnvironmentRequest,
    identity: CurrentIdentity,
    teacher_spaces: TeacherSpaces,
    environments: Environments,
) -> EnvironmentResponse:
    teacher_space = resolve_owned_teacher_space(teacher_space_id, identity.id, teacher_spaces)
    require_writable(teacher_space)
    try:
        environment = environments.create(teacher_space.id, payload.name)
    except EnvironmentAlreadyExistsError as error:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Educational Environment already exists",
        ) from error
    return EnvironmentResponse.from_environment(environment)


@router.get("", response_model=EnvironmentResponse)
def get_environment(
    teacher_space_id: UUID,
    identity: CurrentIdentity,
    teacher_spaces: TeacherSpaces,
    environments: Environments,
) -> EnvironmentResponse:
    teacher_space = resolve_owned_teacher_space(teacher_space_id, identity.id, teacher_spaces)
    try:
        environment = environments.get(teacher_space.id)
    except EnvironmentNotFoundError as error:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Educational Environment not found"
        ) from error
    return EnvironmentResponse.from_environment(environment)


@router.patch(
    "",
    response_model=EnvironmentResponse,
    dependencies=[Depends(require_trusted_origin)],
)
def update_environment(
    teacher_space_id: UUID,
    payload: UpdateEnvironmentRequest,
    identity: CurrentIdentity,
    teacher_spaces: TeacherSpaces,
    environments: Environments,
) -> EnvironmentResponse:
    teacher_space = resolve_owned_teacher_space(teacher_space_id, identity.id, teacher_spaces)
    require_writable(teacher_space)
    try:
        environment = environments.rename(teacher_space.id, payload.name)
    except EnvironmentNotFoundError as error:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Educational Environment not found"
        ) from error
    return EnvironmentResponse.from_environment(environment)
