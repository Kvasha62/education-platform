from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.identity.api.dependencies import get_current_identity
from app.identity.domain.models import Identity
from app.student_space.api.dependencies import get_student_course_service
from app.student_space.api.schemas import StudentCourseResponse
from app.student_space.application.services import (
    StudentContentUnavailableError,
    StudentCourseNotFoundError,
    StudentCourseService,
)

router = APIRouter(prefix="/api/v1/student", tags=["student-courses"])
CurrentIdentity = Annotated[Identity, Depends(get_current_identity)]
StudentCourses = Annotated[StudentCourseService, Depends(get_student_course_service)]


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
