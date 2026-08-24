from typing import Annotated

from fastapi import Depends

from app.education.application.student_course import PublishedCourseReader
from app.education.composition import get_published_course_reader
from app.student_space.application.services import StudentCourseService


def get_student_course_service(
    courses: Annotated[PublishedCourseReader, Depends(get_published_course_reader)],
) -> StudentCourseService:
    return StudentCourseService(courses)
