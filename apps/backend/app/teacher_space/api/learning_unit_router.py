"""Teacher Space owner-facing Learning Unit endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.education.api.dependencies import (
    get_course_service,
    get_environment_service,
    get_learning_unit_service,
    get_section_service,
)
from app.education.api.learning_unit_schemas import (
    CreateLearningUnitRequest,
    LearningUnitResponse,
    UpdateLearningUnitRequest,
)
from app.education.application.errors import LearningUnitNotFoundError, SectionNotFoundError
from app.education.application.services import (
    CourseService,
    EducationalEnvironmentService,
    LearningUnitService,
    SectionService,
)
from app.education.domain.models import Section
from app.identity.api.dependencies import get_current_identity, require_trusted_origin
from app.identity.domain.models import Identity
from app.teacher_space.api.dependencies import get_teacher_space_service
from app.teacher_space.api.environment_router import require_writable
from app.teacher_space.api.section_router import resolve_course
from app.teacher_space.application.services import TeacherSpaceService
from app.teacher_space.domain.models import TeacherSpace

router = APIRouter(
    prefix=(
        "/api/v1/teacher-spaces/{teacher_space_id}/environment/courses/{course_id}"
        "/sections/{section_id}/units"
    ),
    tags=["learning-units"],
)

CurrentIdentity = Annotated[Identity, Depends(get_current_identity)]
TeacherSpaces = Annotated[TeacherSpaceService, Depends(get_teacher_space_service)]
Environments = Annotated[EducationalEnvironmentService, Depends(get_environment_service)]
Courses = Annotated[CourseService, Depends(get_course_service)]
Sections = Annotated[SectionService, Depends(get_section_service)]
Units = Annotated[LearningUnitService, Depends(get_learning_unit_service)]


def resolve_section(
    teacher_space_id: UUID,
    course_id: UUID,
    section_id: UUID,
    identity: Identity,
    teacher_spaces: TeacherSpaceService,
    environments: EducationalEnvironmentService,
    courses: CourseService,
    sections: SectionService,
) -> tuple[Section, TeacherSpace]:
    course, teacher_space = resolve_course(
        teacher_space_id, course_id, identity, teacher_spaces, environments, courses
    )
    try:
        section = sections.get(section_id, course.id)
    except SectionNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Section not found") from error
    return section, teacher_space


def unit_not_found(error: LearningUnitNotFoundError) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, "Learning Unit not found")


@router.post(
    "",
    response_model=LearningUnitResponse,
    status_code=201,
    dependencies=[Depends(require_trusted_origin)],
)
def create_unit(
    teacher_space_id: UUID,
    course_id: UUID,
    section_id: UUID,
    payload: CreateLearningUnitRequest,
    identity: CurrentIdentity,
    teacher_spaces: TeacherSpaces,
    environments: Environments,
    courses: Courses,
    sections: Sections,
    units: Units,
) -> LearningUnitResponse:
    section, teacher_space = resolve_section(
        teacher_space_id,
        course_id,
        section_id,
        identity,
        teacher_spaces,
        environments,
        courses,
        sections,
    )
    require_writable(teacher_space)
    try:
        unit = units.create(section.id, payload.title, payload.position)
    except SectionNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Section not found") from error
    return LearningUnitResponse.from_unit(unit)


@router.get("", response_model=list[LearningUnitResponse])
def list_units(
    teacher_space_id: UUID,
    course_id: UUID,
    section_id: UUID,
    identity: CurrentIdentity,
    teacher_spaces: TeacherSpaces,
    environments: Environments,
    courses: Courses,
    sections: Sections,
    units: Units,
) -> list[LearningUnitResponse]:
    section, _ = resolve_section(
        teacher_space_id,
        course_id,
        section_id,
        identity,
        teacher_spaces,
        environments,
        courses,
        sections,
    )
    return [LearningUnitResponse.from_unit(unit) for unit in units.list(section.id)]


@router.get("/{unit_id}", response_model=LearningUnitResponse)
def get_unit(
    teacher_space_id: UUID,
    course_id: UUID,
    section_id: UUID,
    unit_id: UUID,
    identity: CurrentIdentity,
    teacher_spaces: TeacherSpaces,
    environments: Environments,
    courses: Courses,
    sections: Sections,
    units: Units,
) -> LearningUnitResponse:
    section, _ = resolve_section(
        teacher_space_id,
        course_id,
        section_id,
        identity,
        teacher_spaces,
        environments,
        courses,
        sections,
    )
    try:
        unit = units.get(unit_id, section.id)
    except LearningUnitNotFoundError as error:
        raise unit_not_found(error) from error
    return LearningUnitResponse.from_unit(unit)


@router.patch(
    "/{unit_id}",
    response_model=LearningUnitResponse,
    dependencies=[Depends(require_trusted_origin)],
)
def update_unit(
    teacher_space_id: UUID,
    course_id: UUID,
    section_id: UUID,
    unit_id: UUID,
    payload: UpdateLearningUnitRequest,
    identity: CurrentIdentity,
    teacher_spaces: TeacherSpaces,
    environments: Environments,
    courses: Courses,
    sections: Sections,
    units: Units,
) -> LearningUnitResponse:
    section, teacher_space = resolve_section(
        teacher_space_id,
        course_id,
        section_id,
        identity,
        teacher_spaces,
        environments,
        courses,
        sections,
    )
    require_writable(teacher_space)
    try:
        unit = units.update(unit_id, section.id, title=payload.title, position=payload.position)
    except LearningUnitNotFoundError as error:
        raise unit_not_found(error) from error
    return LearningUnitResponse.from_unit(unit)


@router.delete(
    "/{unit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_trusted_origin)],
)
def delete_unit(
    teacher_space_id: UUID,
    course_id: UUID,
    section_id: UUID,
    unit_id: UUID,
    identity: CurrentIdentity,
    teacher_spaces: TeacherSpaces,
    environments: Environments,
    courses: Courses,
    sections: Sections,
    units: Units,
) -> Response:
    section, teacher_space = resolve_section(
        teacher_space_id,
        course_id,
        section_id,
        identity,
        teacher_spaces,
        environments,
        courses,
        sections,
    )
    require_writable(teacher_space)
    try:
        units.delete(unit_id, section.id)
    except LearningUnitNotFoundError as error:
        raise unit_not_found(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
