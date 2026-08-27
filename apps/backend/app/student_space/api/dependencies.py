from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.assessment.application.definition_lookup import AssessmentDefinitionIdLookup
from app.assessment.composition import (
    get_assessment_attempt_detail_service,
    get_assessment_attempt_service,
    get_assessment_definition_id_lookup,
)
from app.core.database import get_db
from app.education.application.published_course_list import (
    PublishedCourseListReader,
)
from app.education.application.student_content_body import StudentPublishedContentBodyReader
from app.education.application.student_course import PublishedCourseReader
from app.education.composition import (
    get_published_activity_lookup,
    get_published_course_list_reader,
    get_published_course_reader,
    get_student_published_content_body_reader,
)
from app.learning.api.dependencies import (
    get_continue_learning_reader,
    get_course_progress_reader,
    get_enrollment_verifier,
    get_student_enrollment_reader,
)
from app.learning.application.course_progress import CourseProgressReader
from app.learning.application.dashboard import ContinueLearningReader
from app.learning.application.enrollment_read import StudentEnrollmentReader
from app.student_space.application.assessment_attempts import StudentAssessmentAttemptService
from app.student_space.application.dashboard import StudentDashboardReader, StudentDashboardService
from app.student_space.application.services import (
    StudentCourseService,
    StudentPublishedContentBodyService,
    StudentPublishedCourseListService,
)


def get_student_assessment_attempt_service(
    db: Annotated[Session, Depends(get_db)],
) -> StudentAssessmentAttemptService:
    return StudentAssessmentAttemptService(
        get_published_activity_lookup(db),
        get_enrollment_verifier(db),
        get_assessment_attempt_service(db),
        get_assessment_attempt_detail_service(db),
    )


def get_student_course_service(
    courses: Annotated[PublishedCourseReader, Depends(get_published_course_reader)],
    assessments: Annotated[
        AssessmentDefinitionIdLookup,
        Depends(get_assessment_definition_id_lookup),
    ],
) -> StudentCourseService:
    return StudentCourseService(courses, assessments)


def get_student_published_course_list_service(
    courses: Annotated[
        PublishedCourseListReader, Depends(get_published_course_list_reader)
    ],
) -> StudentPublishedCourseListService:
    return StudentPublishedCourseListService(courses)


def get_student_published_content_body_service(
    content: Annotated[
        StudentPublishedContentBodyReader,
        Depends(get_student_published_content_body_reader),
    ],
) -> StudentPublishedContentBodyService:
    return StudentPublishedContentBodyService(content)


def get_student_course_progress_reader(
    progress: Annotated[CourseProgressReader, Depends(get_course_progress_reader)],
) -> CourseProgressReader:
    return progress


def get_student_dashboard_reader(
    enrollments: Annotated[
        StudentEnrollmentReader, Depends(get_student_enrollment_reader)
    ],
    courses: Annotated[
        PublishedCourseListReader, Depends(get_published_course_list_reader)
    ],
    continue_learning: Annotated[
        ContinueLearningReader, Depends(get_continue_learning_reader)
    ],
) -> StudentDashboardReader:
    return StudentDashboardService(enrollments, courses, continue_learning)
