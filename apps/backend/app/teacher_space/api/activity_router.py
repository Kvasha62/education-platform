"""Teacher Space owner-facing Activity endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.assessment.application.definition_lookup import AssessmentDefinitionIdLookup
from app.education.api.activity_schemas import (
    ActivityResponse,
    CreateActivityRequest,
    UpdateActivityRequest,
)
from app.education.api.dependencies import (
    get_activity_service,
    get_course_service,
    get_environment_service,
    get_learning_unit_service,
    get_section_service,
)
from app.education.application.errors import ActivityNotFoundError, LearningUnitNotFoundError
from app.education.application.services import (
    ActivityService,
    CourseService,
    EducationalEnvironmentService,
    LearningUnitService,
    SectionService,
)
from app.education.domain.models import Activity, Course, CourseImmutableError, LearningUnit
from app.identity.api.dependencies import get_current_identity, require_trusted_origin
from app.identity.domain.models import Identity
from app.teacher_space.api.course_router import course_immutable
from app.teacher_space.api.dependencies import (
    get_teacher_activity_assessment_lookup,
    get_teacher_space_service,
)
from app.teacher_space.api.environment_router import require_writable
from app.teacher_space.api.learning_unit_router import resolve_section
from app.teacher_space.application.services import TeacherSpaceService
from app.teacher_space.domain.models import TeacherSpace

router = APIRouter(
    prefix=(
        "/api/v1/teacher-spaces/{teacher_space_id}/environment/courses/{course_id}"
        "/sections/{section_id}/units/{unit_id}/activities"
    ),
    tags=["activities"],
)
CurrentIdentity = Annotated[Identity, Depends(get_current_identity)]
TeacherSpaces = Annotated[TeacherSpaceService, Depends(get_teacher_space_service)]
Environments = Annotated[EducationalEnvironmentService, Depends(get_environment_service)]
Courses = Annotated[CourseService, Depends(get_course_service)]
Sections = Annotated[SectionService, Depends(get_section_service)]
Units = Annotated[LearningUnitService, Depends(get_learning_unit_service)]
Activities = Annotated[ActivityService, Depends(get_activity_service)]
Assessments = Annotated[
    AssessmentDefinitionIdLookup,
    Depends(get_teacher_activity_assessment_lookup),
]


def activity_response(
    activity: Activity,
    assessments: AssessmentDefinitionIdLookup,
) -> ActivityResponse:
    return ActivityResponse.from_activity(
        activity,
        assessments.get_id_for_activity(activity.id),
    )


def resolve_unit(
    teacher_space_id: UUID,
    course_id: UUID,
    section_id: UUID,
    unit_id: UUID,
    identity: Identity,
    teacher_spaces: TeacherSpaceService,
    environments: EducationalEnvironmentService,
    courses: CourseService,
    sections: SectionService,
    units: LearningUnitService,
) -> tuple[LearningUnit, Course, TeacherSpace]:
    section, course, teacher_space = resolve_section(
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
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Learning Unit not found") from error
    return unit, course, teacher_space


def not_found(error: ActivityNotFoundError) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, "Activity not found")


@router.post(
    "",
    response_model=ActivityResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_trusted_origin)],
)
def create_activity(
    teacher_space_id: UUID,
    course_id: UUID,
    section_id: UUID,
    unit_id: UUID,
    payload: CreateActivityRequest,
    identity: CurrentIdentity,
    teacher_spaces: TeacherSpaces,
    environments: Environments,
    courses: Courses,
    sections: Sections,
    units: Units,
    activities: Activities,
    assessments: Assessments,
) -> ActivityResponse:
    unit, course, teacher_space = resolve_unit(
        teacher_space_id,
        course_id,
        section_id,
        unit_id,
        identity,
        teacher_spaces,
        environments,
        courses,
        sections,
        units,
    )
    require_writable(teacher_space)
    try:
        activity = activities.create(
            unit.id,
            course,
            payload.title,
            payload.type,
            payload.position,
        )
    except LearningUnitNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Learning Unit not found") from error
    except CourseImmutableError as error:
        raise course_immutable(error) from error
    return activity_response(activity, assessments)


@router.get("", response_model=list[ActivityResponse])
def list_activities(
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
    activities: Activities,
    assessments: Assessments,
) -> list[ActivityResponse]:
    unit, _, _ = resolve_unit(
        teacher_space_id,
        course_id,
        section_id,
        unit_id,
        identity,
        teacher_spaces,
        environments,
        courses,
        sections,
        units,
    )
    return [activity_response(item, assessments) for item in activities.list(unit.id)]


@router.get("/{activity_id}", response_model=ActivityResponse)
def get_activity(
    teacher_space_id: UUID,
    course_id: UUID,
    section_id: UUID,
    unit_id: UUID,
    activity_id: UUID,
    identity: CurrentIdentity,
    teacher_spaces: TeacherSpaces,
    environments: Environments,
    courses: Courses,
    sections: Sections,
    units: Units,
    activities: Activities,
    assessments: Assessments,
) -> ActivityResponse:
    unit, _, _ = resolve_unit(
        teacher_space_id,
        course_id,
        section_id,
        unit_id,
        identity,
        teacher_spaces,
        environments,
        courses,
        sections,
        units,
    )
    try:
        activity = activities.get(activity_id, unit.id)
    except ActivityNotFoundError as error:
        raise not_found(error) from error
    return activity_response(activity, assessments)


@router.patch(
    "/{activity_id}",
    response_model=ActivityResponse,
    dependencies=[Depends(require_trusted_origin)],
)
def update_activity(
    teacher_space_id: UUID,
    course_id: UUID,
    section_id: UUID,
    unit_id: UUID,
    activity_id: UUID,
    payload: UpdateActivityRequest,
    identity: CurrentIdentity,
    teacher_spaces: TeacherSpaces,
    environments: Environments,
    courses: Courses,
    sections: Sections,
    units: Units,
    activities: Activities,
    assessments: Assessments,
) -> ActivityResponse:
    unit, course, teacher_space = resolve_unit(
        teacher_space_id,
        course_id,
        section_id,
        unit_id,
        identity,
        teacher_spaces,
        environments,
        courses,
        sections,
        units,
    )
    try:
        activities.get(activity_id, unit.id)
    except ActivityNotFoundError as error:
        raise not_found(error) from error
    require_writable(teacher_space)
    try:
        activity = activities.update(
            activity_id,
            unit.id,
            course,
            title=payload.title,
            position=payload.position,
        )
    except ActivityNotFoundError as error:
        raise not_found(error) from error
    except CourseImmutableError as error:
        raise course_immutable(error) from error
    return activity_response(activity, assessments)


@router.delete(
    "/{activity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_trusted_origin)],
)
def delete_activity(
    teacher_space_id: UUID,
    course_id: UUID,
    section_id: UUID,
    unit_id: UUID,
    activity_id: UUID,
    identity: CurrentIdentity,
    teacher_spaces: TeacherSpaces,
    environments: Environments,
    courses: Courses,
    sections: Sections,
    units: Units,
    activities: Activities,
) -> Response:
    unit, course, teacher_space = resolve_unit(
        teacher_space_id,
        course_id,
        section_id,
        unit_id,
        identity,
        teacher_spaces,
        environments,
        courses,
        sections,
        units,
    )
    try:
        activities.get(activity_id, unit.id)
    except ActivityNotFoundError as error:
        raise not_found(error) from error
    require_writable(teacher_space)
    try:
        activities.delete(activity_id, unit.id, course)
    except ActivityNotFoundError as error:
        raise not_found(error) from error
    except CourseImmutableError as error:
        raise course_immutable(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
