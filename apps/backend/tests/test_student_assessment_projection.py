from typing import cast
from uuid import uuid4

from app.assessment.application.definition_lookup import AssessmentDefinitionIdLookup
from app.education.application.student_course import (
    PublishedCourseReader,
    StudentActivity,
    StudentCourse,
    StudentLearningUnit,
    StudentSection,
)
from app.student_space.api.schemas import StudentCourseResponse
from app.student_space.application.services import StudentCourseService


class Courses:
    def __init__(self, course):
        self.course = course

    def get_published(self, course_id):
        return self.course


class Assessments:
    def __init__(self, activity_id, definition_id):
        self.activity_id = activity_id
        self.definition_id = definition_id

    def get_id_for_activity(self, activity_id):
        return self.definition_id if activity_id == self.activity_id else None


def test_student_activity_projection_exposes_nullable_assessment_definition_id():
    assessed_activity_id = uuid4()
    plain_activity_id = uuid4()
    definition_id = uuid4()
    course = StudentCourse(
        id=uuid4(),
        title="Course",
        sections=[
            StudentSection(
                id=uuid4(),
                title="Section",
                position=0,
                units=[
                    StudentLearningUnit(
                        id=uuid4(),
                        title="Unit",
                        position=0,
                        activities=[
                            StudentActivity(
                                id=assessed_activity_id,
                                title="Assessment",
                                type="homework",
                                position=0,
                                contents=[],
                            ),
                            StudentActivity(
                                id=plain_activity_id,
                                title="Reading",
                                type="lecture",
                                position=1,
                                contents=[],
                            ),
                        ],
                    )
                ],
            )
        ],
    )
    view = StudentCourseService(
        cast(PublishedCourseReader, Courses(course)),
        cast(
            AssessmentDefinitionIdLookup,
            Assessments(assessed_activity_id, definition_id),
        ),
    ).get_published(course.id)

    activities = StudentCourseResponse.from_course(view).model_dump()["sections"][0][
        "units"
    ][0]["activities"]
    assert activities[0]["assessment_definition_id"] == definition_id
    assert activities[1]["assessment_definition_id"] is None
