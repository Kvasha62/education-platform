"""Teacher-facing HTTP surface for Activity / Content associations."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.education.api.dependencies import (
    get_activity_service,
    get_course_service,
    get_environment_service,
    get_learning_unit_service,
    get_section_service,
)
from app.education.application.content_links import ActivityContentService
from app.education.application.errors import (
    ActivityNotFoundError,
    LinkedContentNotFoundError,
    LinkedContentUnavailableError,
)
from app.education.application.services import (
    ActivityService,
    CourseService,
    EducationalEnvironmentService,
    LearningUnitService,
    SectionService,
)
from app.education.composition import get_activity_content_service
from app.education.domain.models import Activity
from app.identity.api.dependencies import get_current_identity, require_trusted_origin
from app.identity.domain.models import Identity
from app.teacher_space.api.activity_content_schemas import (
    ActivityContentLinkResponse,
    ActivityContentReferenceResponse,
    AttachActivityContentRequest,
)
from app.teacher_space.api.activity_router import resolve_unit
from app.teacher_space.api.dependencies import get_teacher_space_service
from app.teacher_space.api.environment_router import require_writable
from app.teacher_space.application.services import TeacherSpaceService
from app.teacher_space.domain.models import TeacherSpace

router = APIRouter(
    prefix=(
        "/api/v1/teacher-spaces/{teacher_space_id}/environment/courses/{course_id}"
        "/sections/{section_id}/units/{unit_id}/activities/{activity_id}/contents"
    ),
    tags=["activity-content"],
)

CurrentIdentity = Annotated[Identity, Depends(get_current_identity)]
TeacherSpaces = Annotated[TeacherSpaceService, Depends(get_teacher_space_service)]
Environments = Annotated[EducationalEnvironmentService, Depends(get_environment_service)]
Courses = Annotated[CourseService, Depends(get_course_service)]
Sections = Annotated[SectionService, Depends(get_section_service)]
Units = Annotated[LearningUnitService, Depends(get_learning_unit_service)]
Activities = Annotated[ActivityService, Depends(get_activity_service)]
ActivityContents = Annotated[
    ActivityContentService,
    Depends(get_activity_content_service),
]


def dependency_unavailable(error: LinkedContentUnavailableError) -> HTTPException:
    return HTTPException(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "Content lookup unavailable",
    )


def resolve_scoped_activity(
    teacher_space_id: UUID,
    course_id: UUID,
    section_id: UUID,
    unit_id: UUID,
    activity_id: UUID,
    identity: Identity,
    teacher_spaces: TeacherSpaceService,
    environments: EducationalEnvironmentService,
    courses: CourseService,
    sections: SectionService,
    units: LearningUnitService,
    activities: ActivityService,
) -> tuple[Activity, TeacherSpace]:
    unit, teacher_space = resolve_unit(
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
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Activity not found") from error
    return activity, teacher_space


@router.post(
    "",
    response_model=ActivityContentLinkResponse,
    dependencies=[Depends(require_trusted_origin)],
)
def attach_content(
    teacher_space_id: UUID,
    course_id: UUID,
    section_id: UUID,
    unit_id: UUID,
    activity_id: UUID,
    payload: AttachActivityContentRequest,
    identity: CurrentIdentity,
    teacher_spaces: TeacherSpaces,
    environments: Environments,
    courses: Courses,
    sections: Sections,
    units: Units,
    activities: Activities,
    activity_contents: ActivityContents,
) -> ActivityContentLinkResponse:
    activity, teacher_space = resolve_scoped_activity(
        teacher_space_id,
        course_id,
        section_id,
        unit_id,
        activity_id,
        identity,
        teacher_spaces,
        environments,
        courses,
        sections,
        units,
        activities,
    )
    require_writable(teacher_space)
    try:
        link = activity_contents.attach(activity.id, unit_id, payload.content_id, identity.id)
    except LinkedContentNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Content not found") from error
    except LinkedContentUnavailableError as error:
        raise dependency_unavailable(error) from error
    return ActivityContentLinkResponse(
        activity_id=link.activity_id,
        content_id=link.content_id,
    )


@router.get("", response_model=list[ActivityContentReferenceResponse])
def list_content(
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
    activity_contents: ActivityContents,
) -> list[ActivityContentReferenceResponse]:
    activity, _ = resolve_scoped_activity(
        teacher_space_id,
        course_id,
        section_id,
        unit_id,
        activity_id,
        identity,
        teacher_spaces,
        environments,
        courses,
        sections,
        units,
        activities,
    )
    try:
        resolved = activity_contents.resolve_for_activity(activity.id, unit_id, identity.id)
    except LinkedContentUnavailableError as error:
        raise dependency_unavailable(error) from error
    return [ActivityContentReferenceResponse.from_resolved(item) for item in resolved]


@router.delete(
    "/{content_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_trusted_origin)],
)
def detach_content(
    teacher_space_id: UUID,
    course_id: UUID,
    section_id: UUID,
    unit_id: UUID,
    activity_id: UUID,
    content_id: UUID,
    identity: CurrentIdentity,
    teacher_spaces: TeacherSpaces,
    environments: Environments,
    courses: Courses,
    sections: Sections,
    units: Units,
    activities: Activities,
    activity_contents: ActivityContents,
) -> Response:
    activity, teacher_space = resolve_scoped_activity(
        teacher_space_id,
        course_id,
        section_id,
        unit_id,
        activity_id,
        identity,
        teacher_spaces,
        environments,
        courses,
        sections,
        units,
        activities,
    )
    require_writable(teacher_space)
    activity_contents.detach(activity.id, unit_id, content_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
