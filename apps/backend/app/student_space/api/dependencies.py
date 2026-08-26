from typing import Annotated

from fastapi import Depends

from app.education.application.published_course_list import PublishedCourseListReader
from app.education.application.student_course import PublishedCourseReader
from app.education.composition import (
    get_published_course_list_reader,
    get_published_course_reader,
)
from app.student_space.application.services import (
    StudentCourseService,
    StudentPublishedCourseListService,
)


def get_student_course_service(
    courses: Annotated[PublishedCourseReader, Depends(get_published_course_reader)],
) -> StudentCourseService:
    return StudentCourseService(courses)


def get_student_published_course_list_service(
    courses: Annotated[
        PublishedCourseListReader, Depends(get_published_course_list_reader)
    ],
) -> StudentPublishedCourseListService:
    return StudentPublishedCourseListService(courses)
