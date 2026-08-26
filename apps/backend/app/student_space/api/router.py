from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.identity.api.dependencies import get_current_identity, require_trusted_origin
from app.identity.domain.models import Identity
from app.learning.api.dependencies import (
    get_activity_progress_service,
    get_enrollment_service,
    get_student_enrollment_reader,
)
from app.learning.application.enrollment_read import StudentEnrollmentReader
from app.learning.application.progress import (
    ActivityProgressService,
    ProgressActivityNotFoundError,
    ProgressEnrollmentRequiredError,
    ProgressNotStartedError,
)
from app.learning.application.services import EnrollmentCourseNotFoundError, EnrollmentService
from app.student_space.api.dependencies import (
    get_student_course_service,
    get_student_published_course_list_service,
)
from app.student_space.api.schemas import (
    ActivityProgressResponse,
    EnrollmentReferenceResponse,
    EnrollmentResponse,
    PublishedCourseListResponse,
    PublishedCourseSummaryResponse,
    StudentCourseResponse,
    StudentEnrollmentListResponse,
)
from app.student_space.application.services import (
    StudentContentUnavailableError,
    StudentCourseNotFoundError,
    StudentCourseService,
    StudentPublishedCourseListService,
)

router = APIRouter(prefix="/api/v1/student", tags=["student-courses"])
CurrentIdentity = Annotated[Identity, Depends(get_current_identity)]
StudentCourses = Annotated[StudentCourseService, Depends(get_student_course_service)]
PublishedCourseLists = Annotated[
    StudentPublishedCourseListService, Depends(get_student_published_course_list_service)
]
Enrollments = Annotated[EnrollmentService, Depends(get_enrollment_service)]
ActivityProgresses = Annotated[ActivityProgressService, Depends(get_activity_progress_service)]
StudentEnrollments = Annotated[StudentEnrollmentReader, Depends(get_student_enrollment_reader)]


@router.get("/courses", response_model=PublishedCourseListResponse)
def list_published_courses(
    _identity: CurrentIdentity,
    courses: PublishedCourseLists,
) -> PublishedCourseListResponse:
    return PublishedCourseListResponse(
        items=[
            PublishedCourseSummaryResponse.from_summary(item)
            for item in courses.list_published()
        ]
    )


@router.get("/courses/{course_id}", response_model=StudentCourseResponse)
def get_published_course(
    course_id: UUID,
    _identity: CurrentIdentity,
    courses: StudentCourses,
) -> StudentCourseResponse:
    try:
        course = courses.get_published(course_id)
    except StudentCourseNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found") from error
    except StudentContentUnavailableError as error:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Content lookup unavailable",
        ) from error
    return StudentCourseResponse.from_course(course)


@router.post(
    "/courses/{course_id}/enrollment",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_200_OK: {"model": EnrollmentResponse}},
    dependencies=[Depends(require_trusted_origin)],
)
def enroll_in_course(
    course_id: UUID,
    identity: CurrentIdentity,
    enrollments: Enrollments,
    response: Response,
) -> EnrollmentResponse:
    try:
        result = enrollments.enroll(identity.id, course_id)
    except EnrollmentCourseNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found") from error
    if not result.created:
        response.status_code = status.HTTP_200_OK
    return EnrollmentResponse.from_enrollment(result.enrollment)


@router.get("/enrollments", response_model=StudentEnrollmentListResponse)
def list_enrollments(
    identity: CurrentIdentity,
    enrollments: StudentEnrollments,
) -> StudentEnrollmentListResponse:
    return StudentEnrollmentListResponse(
        items=[
            EnrollmentReferenceResponse.from_reference(item)
            for item in enrollments.list_for_student(identity.id)
        ]
    )


def _progress_or_error(action):
    try:
        return action()
    except (ProgressActivityNotFoundError, ProgressEnrollmentRequiredError) as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Activity not found") from error
    except ProgressNotStartedError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, "Progress has not started") from error


@router.post(
    "/activities/{activity_id}/progress/start",
    response_model=ActivityProgressResponse,
    dependencies=[Depends(require_trusted_origin)],
)
def start_activity_progress(
    activity_id: UUID, identity: CurrentIdentity, progress: ActivityProgresses
) -> ActivityProgressResponse:
    return ActivityProgressResponse.from_reference(
        _progress_or_error(lambda: progress.start(identity.id, activity_id))
    )


@router.post(
    "/activities/{activity_id}/progress/complete",
    response_model=ActivityProgressResponse,
    dependencies=[Depends(require_trusted_origin)],
)
def complete_activity_progress(
    activity_id: UUID, identity: CurrentIdentity, progress: ActivityProgresses
) -> ActivityProgressResponse:
    return ActivityProgressResponse.from_reference(
        _progress_or_error(lambda: progress.complete(identity.id, activity_id))
    )


@router.get("/activities/{activity_id}/progress", response_model=ActivityProgressResponse)
def get_activity_progress(
    activity_id: UUID, identity: CurrentIdentity, progress: ActivityProgresses
) -> ActivityProgressResponse:
    reference = _progress_or_error(
        lambda: progress.get_for_student_activity(identity.id, activity_id)
    )
    if reference is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Progress not found")
    return ActivityProgressResponse.from_reference(reference)
