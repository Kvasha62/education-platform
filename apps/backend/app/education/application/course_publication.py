"""Teacher-facing Course publication use case (ADR-0016 readiness enforcement)."""

from uuid import UUID

from app.education.application.errors import CourseNotReadyForPublicationError
from app.education.application.publication_readiness import is_ready_for_publication
from app.education.application.services import (
    ActivityService,
    CourseService,
    LearningUnitService,
    SectionService,
)
from app.education.domain.models import (
    Activity,
    Course,
    CourseStatus,
    LearningUnit,
)


class CoursePublicationService:
    """Publish a Course only when it satisfies the ADR-0016 readiness predicate.

    Publishing readiness is Education application policy composed from the
    Education-owned Course → Section → Learning Unit → Activity structure.
    The evaluation runs inside the same request-scoped transaction as the
    publication transition, is never persisted, and does not modify the
    Course domain state machine. Repeated publication of an already
    PUBLISHED Course keeps the existing idempotent behavior, and an
    ARCHIVED Course keeps the existing InvalidCourseTransitionError
    behavior of the domain transition.
    """

    def __init__(
        self,
        courses: CourseService,
        sections: SectionService,
        units: LearningUnitService,
        activities: ActivityService,
    ) -> None:
        self.courses = courses
        self.sections = sections
        self.units = units
        self.activities = activities

    def publish(self, course_id: UUID, environment_id: UUID) -> Course:
        course = self.courses.get(course_id, environment_id)
        if course.status is CourseStatus.DRAFT:
            sections = self.sections.list(course.id)
            units_by_section: dict[UUID, list[LearningUnit]] = {
                section.id: self.units.list(section.id) for section in sections
            }
            activities_by_unit: dict[UUID, list[Activity]] = {
                unit.id: self.activities.list(unit.id)
                for units in units_by_section.values()
                for unit in units
            }
            if not is_ready_for_publication(
                course, sections, units_by_section, activities_by_unit
            ):
                raise CourseNotReadyForPublicationError
        return self.courses.publish(course_id, environment_id)
