"""Normative Course Publishing Readiness predicate (ADR-0016, frozen)."""

from uuid import UUID

from app.education.domain.models import (
    Activity,
    Course,
    CourseStatus,
    LearningUnit,
    Section,
)


def is_ready_for_publication(
    course: Course,
    sections: list[Section],
    units_by_section: dict[UUID, list[LearningUnit]],
    activities_by_unit: dict[UUID, list[Activity]],
) -> bool:
    """Evaluate the ADR-0016 Course Publishing Readiness predicate.

    READY if and only if:
      - the Course is in DRAFT status, and
      - the Course has at least one Section, and
      - every Section has at least one Learning Unit, and
      - every Learning Unit has at least one Activity.

    The result is an evaluation only; it is never persisted and it is not a
    Course lifecycle state. Content, Assessment, Enrollment, and Learning
    Progress never participate in this predicate.
    """
    if course.status is not CourseStatus.DRAFT:
        return False
    if not sections:
        return False
    for section in sections:
        units = units_by_section.get(section.id, [])
        if not units:
            return False
        for unit in units:
            if not activities_by_unit.get(unit.id, []):
                return False
    return True
