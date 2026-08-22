"""Teacher Space owner-facing Course endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.education.api.course_schemas import (
    CourseResponse,
    CreateCourseRequest,
    UpdateCourseRequest,
)
from app.education.api.dependencies import get_course_service, get_environment_service
from app.education.application.errors import CourseNotFoundError, EnvironmentNotFoundError
from app.education.application.services import CourseService, EducationalEnvironmentService
from app.education.domain.models import EducationalEnvironment
from app.identity.api.dependencies import get_current_identity, require_trusted_origin
from app.identity.domain.models import Identity
from app.teacher_space.api.dependencies import get_teacher_space_service
from app.teacher_space.api.environment_router import (
    require_writable,
    resolve_owned_teacher_space,
)
from app.teacher_space.application.services import TeacherSpaceService
from app.teacher_space.domain.models import TeacherSpace

router = APIRouter(
    prefix="/api/v1/teacher-spaces/{teacher_space_id}/environment/courses",
    tags=["courses"],
)

CurrentIdentity = Annotated[Identity, Depends(get_current_identity)]
TeacherSpaces = Annotated[TeacherSpaceService, Depends(get_teacher_space_service)]
Environments = Annotated[
    EducationalEnvironmentService, Depends(get_environment_service)
]
Courses = Annotated[CourseService, Depends(get_course_service)]


def resolve_environment(
    teacher_space_id: UUID,
    identity: Identity,
    teacher_spaces: TeacherSpaceService,
    environments: EducationalEnvironmentService,
) -> tuple[EducationalEnvironment, TeacherSpace]:
    teacher_space = resolve_owned_teacher_space(teacher_space_id, identity.id, teacher_spaces)
    try:
        environment = environments.get(teacher_space.id)
    except EnvironmentNotFoundError as error:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Educational Environment not found"
        ) from error
    return environment, teacher_space


def course_not_found(error: CourseNotFoundError) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, "Course not found")


@router.post(
    "",
    response_model=CourseResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_trusted_origin)],
)
def create_course(
    teacher_space_id: UUID,
    payload: CreateCourseRequest,
    identity: CurrentIdentity,
    teacher_spaces: TeacherSpaces,
    environments: Environments,
    courses: Courses,
) -> CourseResponse:
    environment, teacher_space = resolve_environment(
        teacher_space_id, identity, teacher_spaces, environments
    )
    require_writable(teacher_space)
    return CourseResponse.from_course(courses.create(environment.id, payload.title))


@router.get("", response_model=list[CourseResponse])
def list_courses(
    teacher_space_id: UUID,
    identity: CurrentIdentity,
    teacher_spaces: TeacherSpaces,
    environments: Environments,
    courses: Courses,
) -> list[CourseResponse]:
    environment, _ = resolve_environment(
        teacher_space_id, identity, teacher_spaces, environments
    )
    return [CourseResponse.from_course(course) for course in courses.list(environment.id)]


@router.get("/{course_id}", response_model=CourseResponse)
def get_course(
    teacher_space_id: UUID,
    course_id: UUID,
    identity: CurrentIdentity,
    teacher_spaces: TeacherSpaces,
    environments: Environments,
    courses: Courses,
) -> CourseResponse:
    environment, _ = resolve_environment(
        teacher_space_id, identity, teacher_spaces, environments
    )
    try:
        course = courses.get(course_id, environment.id)
    except CourseNotFoundError as error:
        raise course_not_found(error) from error
    return CourseResponse.from_course(course)


@router.patch(
    "/{course_id}",
    response_model=CourseResponse,
    dependencies=[Depends(require_trusted_origin)],
)
def update_course(
    teacher_space_id: UUID,
    course_id: UUID,
    payload: UpdateCourseRequest,
    identity: CurrentIdentity,
    teacher_spaces: TeacherSpaces,
    environments: Environments,
    courses: Courses,
) -> CourseResponse:
    environment, teacher_space = resolve_environment(
        teacher_space_id, identity, teacher_spaces, environments
    )
    require_writable(teacher_space)
    try:
        course = courses.rename(course_id, environment.id, payload.title)
    except CourseNotFoundError as error:
        raise course_not_found(error) from error
    return CourseResponse.from_course(course)
