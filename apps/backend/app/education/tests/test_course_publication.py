from typing import Any
from uuid import uuid4

import pytest

from app.education.application.course_publication import CoursePublicationService
from app.education.application.errors import CourseNotReadyForPublicationError
from app.education.application.publication_readiness import is_ready_for_publication
from app.education.application.services import (
    ActivityService,
    CourseService,
    LearningUnitService,
    SectionService,
)
from app.education.domain.models import (
    ActivityType,
    CourseStatus,
    InvalidCourseTransitionError,
)


class MemoryCourseRepository:
    def __init__(self) -> None:
        self.items: dict[Any, Any] = {}

    def add(self, course):
        self.items[course.id] = course
        return course

    def list_by_environment(self, environment_id):
        return [
            course
            for course in self.items.values()
            if course.educational_environment_id == environment_id
        ]

    def get_by_id(self, course_id):
        return self.items.get(course_id)

    def get_in_environment(self, course_id, environment_id):
        course = self.items.get(course_id)
        return course if course and course.educational_environment_id == environment_id else None

    def update(self, course):
        self.items[course.id] = course
        return course


class MemorySectionRepository:
    def __init__(self) -> None:
        self.items: dict[Any, Any] = {}

    def add(self, section):
        self.items[section.id] = section
        return section

    def list_by_course(self, course_id):
        return [item for item in self.items.values() if item.course_id == course_id]

    def get_in_course(self, section_id, course_id):
        section = self.items.get(section_id)
        return section if section and section.course_id == course_id else None

    def update(self, section):
        self.items[section.id] = section
        return section

    def delete(self, section):
        self.items.pop(section.id, None)


class MemoryLearningUnitRepository:
    def __init__(self) -> None:
        self.items: dict[Any, Any] = {}

    def add(self, unit):
        self.items[unit.id] = unit
        return unit

    def list_by_section(self, section_id):
        return [item for item in self.items.values() if item.section_id == section_id]

    def get_in_section(self, unit_id, section_id):
        unit = self.items.get(unit_id)
        return unit if unit and unit.section_id == section_id else None

    def update(self, unit):
        self.items[unit.id] = unit
        return unit

    def delete(self, unit):
        self.items.pop(unit.id, None)


class MemoryActivityRepository:
    def __init__(self) -> None:
        self.items: dict[Any, Any] = {}

    def add(self, activity):
        self.items[activity.id] = activity
        return activity

    def list_by_unit(self, unit_id):
        return [item for item in self.items.values() if item.learning_unit_id == unit_id]

    def get_in_unit(self, activity_id, unit_id):
        activity = self.items.get(activity_id)
        return activity if activity and activity.learning_unit_id == unit_id else None

    def update(self, activity):
        self.items[activity.id] = activity
        return activity

    def delete(self, activity):
        self.items.pop(activity.id, None)


@pytest.fixture
def publication() -> CoursePublicationService:
    return CoursePublicationService(
        CourseService(MemoryCourseRepository()),
        SectionService(MemorySectionRepository()),
        LearningUnitService(MemoryLearningUnitRepository()),
        ActivityService(MemoryActivityRepository()),
    )


def create_structure(
    publication: CoursePublicationService,
    course_id,
    environment_id,
    sections: int = 1,
    units_per_section: int = 1,
    activities_per_unit: int = 1,
) -> None:
    course = publication.courses.get(course_id, environment_id)
    for section_index in range(sections):
        section = publication.sections.create(
            course, f"Section {section_index}", section_index
        )
        for unit_index in range(units_per_section):
            unit = publication.units.create(
                section.id, course, f"Unit {unit_index}", unit_index
            )
            for activity_index in range(activities_per_unit):
                publication.activities.create(
                    unit.id,
                    course,
                    f"Activity {activity_index}",
                    ActivityType.LECTURE,
                    activity_index,
                )


def test_ready_course_publishes_successfully(publication: CoursePublicationService) -> None:
    environment_id = uuid4()
    course = publication.courses.create(environment_id, "Course")
    create_structure(publication, course.id, environment_id)

    published = publication.publish(course.id, environment_id)

    assert published.status is CourseStatus.PUBLISHED


def test_course_without_sections_is_not_ready(publication: CoursePublicationService) -> None:
    environment_id = uuid4()
    course = publication.courses.create(environment_id, "Course")

    with pytest.raises(CourseNotReadyForPublicationError):
        publication.publish(course.id, environment_id)

    assert publication.courses.get(course.id, environment_id).status is CourseStatus.DRAFT


def test_section_without_learning_units_is_not_ready(
    publication: CoursePublicationService,
) -> None:
    environment_id = uuid4()
    course = publication.courses.create(environment_id, "Course")
    create_structure(publication, course.id, environment_id, units_per_section=0)

    with pytest.raises(CourseNotReadyForPublicationError):
        publication.publish(course.id, environment_id)

    assert publication.courses.get(course.id, environment_id).status is CourseStatus.DRAFT


def test_learning_unit_without_activities_is_not_ready(
    publication: CoursePublicationService,
) -> None:
    environment_id = uuid4()
    course = publication.courses.create(environment_id, "Course")
    create_structure(publication, course.id, environment_id, activities_per_unit=0)

    with pytest.raises(CourseNotReadyForPublicationError):
        publication.publish(course.id, environment_id)

    assert publication.courses.get(course.id, environment_id).status is CourseStatus.DRAFT


def test_partially_ready_hierarchy_is_not_ready(
    publication: CoursePublicationService,
) -> None:
    environment_id = uuid4()
    course = publication.courses.create(environment_id, "Course")
    create_structure(publication, course.id, environment_id)
    publication.sections.create(
        publication.courses.get(course.id, environment_id), "Empty Section", 1
    )

    with pytest.raises(CourseNotReadyForPublicationError):
        publication.publish(course.id, environment_id)

    assert publication.courses.get(course.id, environment_id).status is CourseStatus.DRAFT


def test_published_course_republishes_idempotently(
    publication: CoursePublicationService,
) -> None:
    environment_id = uuid4()
    course = publication.courses.create(environment_id, "Course")
    create_structure(publication, course.id, environment_id)

    published = publication.publish(course.id, environment_id)
    republished = publication.publish(course.id, environment_id)

    assert republished == published
    assert republished.updated_at == published.updated_at


def test_archived_course_publish_keeps_transition_error(
    publication: CoursePublicationService,
) -> None:
    environment_id = uuid4()
    course = publication.courses.create(environment_id, "Course")
    create_structure(publication, course.id, environment_id)
    publication.publish(course.id, environment_id)
    publication.courses.archive(course.id, environment_id)

    with pytest.raises(InvalidCourseTransitionError):
        publication.publish(course.id, environment_id)


def test_predicate_requires_draft_status(publication: CoursePublicationService) -> None:
    environment_id = uuid4()
    course = publication.courses.create(environment_id, "Course")
    sections = publication.sections.create(course, "Section", 0)
    unit = publication.units.create(sections.id, course, "Unit", 0)
    activity = publication.activities.create(
        unit.id, course, "Activity", ActivityType.LECTURE, 0
    )
    ready_arguments = (
        [sections],
        {sections.id: [unit]},
        {unit.id: [activity]},
    )

    assert is_ready_for_publication(course, *ready_arguments) is True

    published = publication.courses.publish(course.id, environment_id)
    assert is_ready_for_publication(published, *ready_arguments) is False
