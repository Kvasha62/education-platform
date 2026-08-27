from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.assessment.application.attempts import (
    AssessmentAttemptDefinitionArchivedError,
    AssessmentAttemptDefinitionNotFoundError,
    AssessmentAttemptResultMissingError,
)
from app.assessment.domain.attempts import (
    AssessmentAttemptImmutableError,
    AssessmentSubmissionRequiredError,
)
from app.identity.api.dependencies import get_current_identity, require_trusted_origin
from app.identity.domain.models import Identity
from app.learning.api.dependencies import (
    get_activity_progress_service,
    get_enrollment_service,
    get_student_enrollment_reader,
)
from app.learning.application.course_progress import (
    CourseProgressNotFoundError,
    CourseProgressReader,
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
    get_student_assessment_attempt_service,
    get_student_course_progress_reader,
    get_student_course_service,
    get_student_dashboard_reader,
    get_student_published_content_body_service,
    get_student_published_course_list_service,
)
from app.student_space.api.schemas import (
    ActivityProgressResponse,
    AssessmentAttemptResponse,
    CourseProgressResponse,
    CreateAssessmentAttemptRequest,
    EnrollmentReferenceResponse,
    EnrollmentResponse,
    PublishedCourseListResponse,
    PublishedCourseSummaryResponse,
    ReplaceAssessmentAttemptRequest,
    StudentCourseResponse,
    StudentDashboardResponse,
    StudentEnrollmentListResponse,
    StudentPublishedContentBodyResponse,
)
from app.student_space.application.assessment_attempts import (
    AssessmentAttemptAuthorizationError,
    AssessmentAttemptMutationForbiddenError,
    StudentAssessmentAttemptService,
)
from app.student_space.application.dashboard import StudentDashboardReader
from app.student_space.application.services import (
    StudentContentUnavailableError,
    StudentCourseNotFoundError,
    StudentCourseService,
    StudentPublishedContentBodyNotFoundError,
    StudentPublishedContentBodyService,
    StudentPublishedCourseListService,
)

router = APIRouter(prefix="/api/v1/student", tags=["student-courses"])
CurrentIdentity = Annotated[Identity, Depends(get_current_identity)]
StudentCourses = Annotated[StudentCourseService, Depends(get_student_course_service)]
StudentCourseProgresses = Annotated[
    CourseProgressReader,
    Depends(get_student_course_progress_reader),
]
StudentDashboards = Annotated[StudentDashboardReader, Depends(get_student_dashboard_reader)]
StudentContentBodies = Annotated[
    StudentPublishedContentBodyService, Depends(get_student_published_content_body_service)
]
PublishedCourseLists = Annotated[
    StudentPublishedCourseListService,
    Depends(get_student_published_course_list_service),
]
Enrollments = Annotated[EnrollmentService, Depends(get_enrollment_service)]
ActivityProgresses = Annotated[ActivityProgressService, Depends(get_activity_progress_service)]
StudentEnrollments = Annotated[StudentEnrollmentReader, Depends(get_student_enrollment_reader)]
StudentAssessmentAttempts = Annotated[
    StudentAssessmentAttemptService,
    Depends(get_student_assessment_attempt_service),
]


ASSESSMENT_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required"},
    status.HTTP_403_FORBIDDEN: {"description": "Assessment access denied"},
    status.HTTP_404_NOT_FOUND: {"description": "Assessment Attempt not found"},
    status.HTTP_409_CONFLICT: {"description": "Invalid Assessment state"},
    status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "Invalid request or submission"},
    status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"},
}
ASSESSMENT_DETAIL_ERROR_RESPONSES = {
    code: response
    for code, response in ASSESSMENT_ERROR_RESPONSES.items()
    if code != status.HTTP_409_CONFLICT
}


def _assessment_attempt_or_error(action):
    try:
        return action()
    except (
        AssessmentAttemptAuthorizationError,
        AssessmentAttemptDefinitionNotFoundError,
    ) as error:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Assessment Attempt not found",
        ) from error
    except AssessmentAttemptMutationForbiddenError as error:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Assessment access denied",
        ) from error
    except AssessmentAttemptDefinitionArchivedError as error:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Assessment Definition is archived",
        ) from error
    except AssessmentSubmissionRequiredError as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Submission is required",
        ) from error
    except AssessmentAttemptImmutableError as error:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Assessment Attempt is immutable",
        ) from error
    except AssessmentAttemptResultMissingError as error:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Internal Server Error",
        ) from error


@router.post(
    "/activities/{activity_id}/assessment-definitions/{definition_id}/attempts",
    response_model=AssessmentAttemptResponse,
    status_code=status.HTTP_201_CREATED,
    responses=ASSESSMENT_ERROR_RESPONSES,
    dependencies=[Depends(require_trusted_origin)],
    tags=["student-assessment"],
)
def create_assessment_attempt(
    activity_id: UUID,
    definition_id: UUID,
    payload: CreateAssessmentAttemptRequest,
    identity: CurrentIdentity,
    attempts: StudentAssessmentAttempts,
) -> AssessmentAttemptResponse:
    detail = _assessment_attempt_or_error(
        lambda: attempts.create(
            identity.id,
            activity_id,
            definition_id,
            payload.submission,
        )
    )
    return AssessmentAttemptResponse.from_detail(detail)


@router.put(
    "/assessment-attempts/{attempt_id}",
    response_model=AssessmentAttemptResponse,
    responses=ASSESSMENT_ERROR_RESPONSES,
    dependencies=[Depends(require_trusted_origin)],
    tags=["student-assessment"],
)
def replace_assessment_attempt_submission(
    attempt_id: UUID,
    payload: ReplaceAssessmentAttemptRequest,
    identity: CurrentIdentity,
    attempts: StudentAssessmentAttempts,
) -> AssessmentAttemptResponse:
    detail = _assessment_attempt_or_error(
        lambda: attempts.update_submission(
            identity.id,
            attempt_id,
            payload.submission,
        )
    )
    return AssessmentAttemptResponse.from_detail(detail)


@router.post(
    "/assessment-attempts/{attempt_id}/submit",
    response_model=AssessmentAttemptResponse,
    responses=ASSESSMENT_ERROR_RESPONSES,
    dependencies=[Depends(require_trusted_origin)],
    tags=["student-assessment"],
)
def submit_assessment_attempt(
    attempt_id: UUID,
    identity: CurrentIdentity,
    attempts: StudentAssessmentAttempts,
) -> AssessmentAttemptResponse:
    detail = _assessment_attempt_or_error(
        lambda: attempts.submit(identity.id, attempt_id)
    )
    return AssessmentAttemptResponse.from_detail(detail)


@router.get(
    "/assessment-attempts/{attempt_id}",
    response_model=AssessmentAttemptResponse,
    responses=ASSESSMENT_DETAIL_ERROR_RESPONSES,
    tags=["student-assessment"],
)
def get_assessment_attempt(
    attempt_id: UUID,
    identity: CurrentIdentity,
    attempts: StudentAssessmentAttempts,
) -> AssessmentAttemptResponse:
    detail = _assessment_attempt_or_error(
        lambda: attempts.get(identity.id, attempt_id)
    )
    return AssessmentAttemptResponse.from_detail(detail)


@router.get("/dashboard", response_model=StudentDashboardResponse)
def get_student_dashboard(
    identity: CurrentIdentity,
    dashboard: StudentDashboards,
) -> StudentDashboardResponse:
    """Return enrolled published Courses and the latest visible IN_PROGRESS Activity.

    Recent Learning and Progress Overview are intentionally excluded from the MVP contract.
    The endpoint is an unpaginated aggregate composed through Education and Learning readers.
    Contract versioning is provided by the existing `/api/v1` prefix; no body version field is used.
    """
    return StudentDashboardResponse.from_dashboard(
        dashboard.get_dashboard(identity.id)
    )


@router.get(
    "/contents/{content_id}/body",
    response_model=StudentPublishedContentBodyResponse,
)
def get_published_content_body(
    content_id: UUID,
    _identity: CurrentIdentity,
    content: StudentContentBodies,
) -> StudentPublishedContentBodyResponse:
    try:
        reference = content.get_published_body(content_id)
    except StudentPublishedContentBodyNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Content not found") from error
    except StudentContentUnavailableError as error:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Content lookup unavailable",
        ) from error
    return StudentPublishedContentBodyResponse.from_reference(reference)


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


@router.get(
    "/courses/{course_id}/progress",
    response_model=CourseProgressResponse,
)
def get_course_progress(
    course_id: UUID,
    identity: CurrentIdentity,
    progress: StudentCourseProgresses,
) -> CourseProgressResponse:
    try:
        result = progress.get_for_student(identity.id, course_id)
    except CourseProgressNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found") from error
    return CourseProgressResponse.from_progress(result)


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
