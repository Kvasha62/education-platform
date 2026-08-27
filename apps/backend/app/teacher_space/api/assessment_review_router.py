"""Teacher-facing Assessment Review HTTP surface."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.assessment.application.attempts import (
    AssessmentAttemptNotFoundError,
    AssessmentAttemptResultMissingError,
)
from app.assessment.application.results import (
    AssessmentResultAlreadyExistsError,
    AssessmentResultNotFoundError,
)
from app.assessment.domain.attempts import AssessmentAttemptImmutableError, AssessmentAttemptStatus
from app.assessment.domain.results import (
    InvalidAssessmentResultFeedbackError,
    InvalidAssessmentResultMaxScoreError,
    InvalidAssessmentResultScoreError,
)
from app.identity.api.dependencies import get_current_identity, require_trusted_origin
from app.identity.domain.models import Identity
from app.teacher_space.api.assessment_review_schemas import (
    AssessmentResultResponse,
    CorrectAssessmentRequest,
    ReviewAssessmentRequest,
    TeacherAssessmentAttemptDetailResponse,
    TeacherAssessmentAttemptItemResponse,
    TeacherAssessmentAttemptPageResponse,
    TeacherAssessmentAttemptStatusFilter,
)
from app.teacher_space.api.dependencies import get_teacher_assessment_review_service
from app.teacher_space.application.assessment_results import (
    TeacherAssessmentReviewAuthorizationError,
    TeacherAssessmentReviewConflictError,
    TeacherAssessmentReviewNotFoundError,
    TeacherAssessmentReviewService,
)

router = APIRouter(
    prefix=(
        "/api/v1/teacher-spaces/{teacher_space_id}/activities/{activity_id}"
        "/assessment-attempts"
    ),
    tags=["teacher-assessment"],
)

CurrentIdentity = Annotated[Identity, Depends(get_current_identity)]
Reviews = Annotated[TeacherAssessmentReviewService, Depends(get_teacher_assessment_review_service)]

READ_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required"},
    status.HTTP_403_FORBIDDEN: {"description": "Assessment access denied"},
    status.HTTP_404_NOT_FOUND: {"description": "Assessment resource not found"},
    status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "Invalid request or query"},
    status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"},
}
MUTATION_ERROR_RESPONSES = {
    **READ_ERROR_RESPONSES,
    status.HTTP_409_CONFLICT: {"description": "Invalid Assessment lifecycle state"},
}


def _or_error(action):
    try:
        return action()
    except (
        TeacherAssessmentReviewNotFoundError,
        AssessmentAttemptNotFoundError,
        AssessmentResultNotFoundError,
    ) as error:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Assessment resource not found",
        ) from error
    except TeacherAssessmentReviewAuthorizationError as error:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Assessment access denied",
        ) from error
    except (
        TeacherAssessmentReviewConflictError,
        AssessmentAttemptImmutableError,
        AssessmentResultAlreadyExistsError,
    ) as error:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Invalid assessment state",
        ) from error
    except (
        InvalidAssessmentResultScoreError,
        InvalidAssessmentResultMaxScoreError,
        InvalidAssessmentResultFeedbackError,
    ) as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Invalid score or feedback",
        ) from error
    except AssessmentAttemptResultMissingError as error:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Internal Server Error",
        ) from error


@router.get(
    "",
    response_model=TeacherAssessmentAttemptPageResponse,
    responses=READ_ERROR_RESPONSES,
)
def list_assessment_attempts(
    teacher_space_id: UUID,
    activity_id: UUID,
    identity: CurrentIdentity,
    reviews: Reviews,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: Annotated[
        TeacherAssessmentAttemptStatusFilter | None, Query(alias="status")
    ] = None,
) -> TeacherAssessmentAttemptPageResponse:
    result = _or_error(
        lambda: reviews.list_attempts(
            identity.id,
            teacher_space_id,
            activity_id,
            status=(
                None
                if status_filter is None
                else AssessmentAttemptStatus(status_filter.value)
            ),
            page=page,
            page_size=page_size,
        )
    )
    return TeacherAssessmentAttemptPageResponse(
        items=[
            TeacherAssessmentAttemptItemResponse.from_detail(item, activity_id)
            for item in result.items
        ],
        page=page,
        page_size=page_size,
        has_next=result.has_next,
    )


@router.get(
    "/{attempt_id}",
    response_model=TeacherAssessmentAttemptDetailResponse,
    responses=READ_ERROR_RESPONSES,
)
def get_assessment_attempt(
    teacher_space_id: UUID,
    activity_id: UUID,
    attempt_id: UUID,
    identity: CurrentIdentity,
    reviews: Reviews,
) -> TeacherAssessmentAttemptDetailResponse:
    detail = _or_error(
        lambda: reviews.get_attempt(
            identity.id,
            teacher_space_id,
            activity_id,
            attempt_id,
        )
    )
    return TeacherAssessmentAttemptDetailResponse.from_detail(detail, activity_id)


@router.post(
    "/{attempt_id}/review",
    response_model=AssessmentResultResponse,
    responses=MUTATION_ERROR_RESPONSES,
    dependencies=[Depends(require_trusted_origin)],
)
def review_assessment_attempt(
    teacher_space_id: UUID,
    activity_id: UUID,
    attempt_id: UUID,
    payload: ReviewAssessmentRequest,
    identity: CurrentIdentity,
    reviews: Reviews,
) -> AssessmentResultResponse:
    result = _or_error(
        lambda: reviews.review(
            identity.id,
            teacher_space_id,
            activity_id,
            attempt_id,
            payload.score,
            payload.max_score,
            payload.feedback,
        )
    )
    return AssessmentResultResponse.from_result(result)


@router.post(
    "/{attempt_id}/correction",
    response_model=AssessmentResultResponse,
    responses=MUTATION_ERROR_RESPONSES,
    dependencies=[Depends(require_trusted_origin)],
)
def correct_assessment_attempt(
    teacher_space_id: UUID,
    activity_id: UUID,
    attempt_id: UUID,
    payload: CorrectAssessmentRequest,
    identity: CurrentIdentity,
    reviews: Reviews,
) -> AssessmentResultResponse:
    result = _or_error(
        lambda: reviews.correct(
            identity.id,
            teacher_space_id,
            activity_id,
            attempt_id,
            payload.result_id,
            payload.score,
            payload.feedback,
        )
    )
    return AssessmentResultResponse.from_result(result)
