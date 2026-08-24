"""Teacher Space owner-facing Section endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.education.api.dependencies import (
    get_course_service,
    get_environment_service,
    get_section_service,
)
from app.education.api.section_schemas import (
    CreateSectionRequest,
    SectionResponse,
    UpdateSectionRequest,
)
from app.education.application.errors import CourseNotFoundError, SectionNotFoundError
from app.education.application.services import (
    CourseService,
    EducationalEnvironmentService,
    SectionService,
)
from app.education.domain.models import Course, CourseImmutableError
from app.identity.api.dependencies import get_current_identity, require_trusted_origin
from app.identity.domain.models import Identity
from app.teacher_space.api.course_router import course_immutable, resolve_environment
from app.teacher_space.api.dependencies import get_teacher_space_service
from app.teacher_space.api.environment_router import require_writable
from app.teacher_space.application.services import TeacherSpaceService
from app.teacher_space.domain.models import TeacherSpace

router = APIRouter(
    prefix=("/api/v1/teacher-spaces/{teacher_space_id}/environment/courses/{course_id}/sections"),
    tags=["sections"],
)

CurrentIdentity = Annotated[Identity, Depends(get_current_identity)]
TeacherSpaces = Annotated[TeacherSpaceService, Depends(get_teacher_space_service)]
Environments = Annotated[EducationalEnvironmentService, Depends(get_environment_service)]
Courses = Annotated[CourseService, Depends(get_course_service)]
Sections = Annotated[SectionService, Depends(get_section_service)]


def resolve_course(
    teacher_space_id: UUID,
    course_id: UUID,
    identity: Identity,
    teacher_spaces: TeacherSpaceService,
    environments: EducationalEnvironmentService,
    courses: CourseService,
) -> tuple[Course, TeacherSpace]:
    environment, teacher_space = resolve_environment(
        teacher_space_id, identity, teacher_spaces, environments
    )
    try:
        course = courses.get(course_id, environment.id)
    except CourseNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found") from error
    return course, teacher_space


def section_not_found(error: SectionNotFoundError) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, "Section not found")


@router.post(
    "",
    response_model=SectionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_trusted_origin)],
)
def create_section(
    teacher_space_id: UUID,
    course_id: UUID,
    payload: CreateSectionRequest,
    identity: CurrentIdentity,
    teacher_spaces: TeacherSpaces,
    environments: Environments,
    courses: Courses,
    sections: Sections,
) -> SectionResponse:
    course, teacher_space = resolve_course(
        teacher_space_id, course_id, identity, teacher_spaces, environments, courses
    )
    require_writable(teacher_space)
    try:
        section = sections.create(course, payload.title, payload.position)
    except CourseNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found") from error
    except CourseImmutableError as error:
        raise course_immutable(error) from error
    return SectionResponse.from_section(section)


@router.get("", response_model=list[SectionResponse])
def list_sections(
    teacher_space_id: UUID,
    course_id: UUID,
    identity: CurrentIdentity,
    teacher_spaces: TeacherSpaces,
    environments: Environments,
    courses: Courses,
    sections: Sections,
) -> list[SectionResponse]:
    course, _ = resolve_course(
        teacher_space_id, course_id, identity, teacher_spaces, environments, courses
    )
    return [SectionResponse.from_section(section) for section in sections.list(course.id)]


@router.get("/{section_id}", response_model=SectionResponse)
def get_section(
    teacher_space_id: UUID,
    course_id: UUID,
    section_id: UUID,
    identity: CurrentIdentity,
    teacher_spaces: TeacherSpaces,
    environments: Environments,
    courses: Courses,
    sections: Sections,
) -> SectionResponse:
    course, _ = resolve_course(
        teacher_space_id, course_id, identity, teacher_spaces, environments, courses
    )
    try:
        section = sections.get(section_id, course.id)
    except SectionNotFoundError as error:
        raise section_not_found(error) from error
    return SectionResponse.from_section(section)


@router.patch(
    "/{section_id}",
    response_model=SectionResponse,
    dependencies=[Depends(require_trusted_origin)],
)
def update_section(
    teacher_space_id: UUID,
    course_id: UUID,
    section_id: UUID,
    payload: UpdateSectionRequest,
    identity: CurrentIdentity,
    teacher_spaces: TeacherSpaces,
    environments: Environments,
    courses: Courses,
    sections: Sections,
) -> SectionResponse:
    course, teacher_space = resolve_course(
        teacher_space_id, course_id, identity, teacher_spaces, environments, courses
    )
    try:
        sections.get(section_id, course.id)
    except SectionNotFoundError as error:
        raise section_not_found(error) from error
    require_writable(teacher_space)
    try:
        section = sections.update(
            section_id,
            course,
            title=payload.title,
            position=payload.position,
        )
    except SectionNotFoundError as error:
        raise section_not_found(error) from error
    except CourseImmutableError as error:
        raise course_immutable(error) from error
    return SectionResponse.from_section(section)


@router.delete(
    "/{section_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_trusted_origin)],
)
def delete_section(
    teacher_space_id: UUID,
    course_id: UUID,
    section_id: UUID,
    identity: CurrentIdentity,
    teacher_spaces: TeacherSpaces,
    environments: Environments,
    courses: Courses,
    sections: Sections,
) -> Response:
    course, teacher_space = resolve_course(
        teacher_space_id, course_id, identity, teacher_spaces, environments, courses
    )
    try:
        sections.get(section_id, course.id)
    except SectionNotFoundError as error:
        raise section_not_found(error) from error
    require_writable(teacher_space)
    try:
        sections.delete(section_id, course)
    except SectionNotFoundError as error:
        raise section_not_found(error) from error
    except CourseImmutableError as error:
        raise course_immutable(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
