from typing import cast
from uuid import uuid4

import pytest

from app.assessment.application.services import (
    AssessmentDefinitionAlreadyExistsError,
    AssessmentDefinitionNotFoundError,
    AssessmentDefinitionService,
)
from app.assessment.domain.models import AssessmentDefinitionImmutableError
from app.education.application.activity_scope import (
    ActivityScopeResolution,
    ActivityTeacherSpaceScopeQuery,
)
from app.teacher_space.application.assessment_definitions import (
    AssessmentDefinitionAuthorizationError,
    TeacherAssessmentDefinitionActivityNotFoundError,
    TeacherAssessmentDefinitionService,
)
from app.teacher_space.application.errors import TeacherSpaceNotFoundError
from app.teacher_space.application.services import TeacherSpaceService
from app.teacher_space.domain.models import TeacherSpace


class TeacherSpaces:
    """Service-level double matching TeacherSpaceService.get_by_id()."""

    def __init__(self, space):
        self.space = space

    def get_by_id(self, teacher_space_id):
        if self.space.id != teacher_space_id:
            raise TeacherSpaceNotFoundError
        return self.space


class Scope:
    def __init__(self, allowed, *, resolution=None):
        self.allowed = allowed
        self.resolution = resolution

    def belongs_to_teacher_space(self, activity_id, teacher_space_id):
        return self.allowed

    def resolve_activity_scope(self, activity_id, teacher_space_id):
        if self.resolution is not None:
            return self.resolution
        return (
            ActivityScopeResolution.IN_SCOPE
            if self.allowed
            else ActivityScopeResolution.OUTSIDE_SCOPE
        )


class Definitions:
    def __init__(self):
        self.items = {}

    def add(self, value):
        self.items[value.id] = value
        return value

    def get(self, definition_id, activity_id):
        value = self.items.get(definition_id)
        return value if value and value.activity_id == activity_id else None

    def get_by_id(self, definition_id):
        return self.items.get(definition_id)

    def get_by_activity(self, activity_id):
        return next(
            (value for value in self.items.values() if value.activity_id == activity_id),
            None,
        )

    def update(self, value):
        self.items[value.id] = value
        return value


def orchestrator(owner, *, activity_allowed=True, resolution=None):
    space = TeacherSpace.create(owner, "Space")
    return (
        TeacherAssessmentDefinitionService(
            cast(TeacherSpaceService, TeacherSpaces(space)),
            ActivityTeacherSpaceScopeQuery(Scope(activity_allowed, resolution=resolution)),
            AssessmentDefinitionService(Definitions()),
        ),
        space,
    )


def test_authorized_teacher_manages_definition():
    owner = uuid4()
    service, space = orchestrator(owner)
    activity = uuid4()
    value = service.create(owner, space.id, activity, "a")
    assert service.get(owner, space.id, activity).id == value.id
    value = service.update_instructions(owner, space.id, activity, "b")
    assert value.instructions == "b"
    value = service.archive(owner, space.id, activity)
    assert value.status.value == "archived"


def test_wrong_teacher_is_rejected_by_teacher_space_authorization():
    owner = uuid4()
    service, space = orchestrator(owner, activity_allowed=True)

    with pytest.raises(AssessmentDefinitionAuthorizationError):
        service.create(uuid4(), space.id, uuid4(), None)


def test_activity_outside_teacher_space_is_rejected_by_education_scope():
    owner = uuid4()
    service, space = orchestrator(owner, activity_allowed=False)

    with pytest.raises(AssessmentDefinitionAuthorizationError):
        service.create(owner, space.id, uuid4(), None)


def test_missing_teacher_space_raises_not_found():
    owner = uuid4()
    service, _ = orchestrator(owner)

    with pytest.raises(TeacherSpaceNotFoundError):
        service.get(owner, uuid4(), uuid4())


def test_missing_activity_raises_not_found():
    owner = uuid4()
    service, space = orchestrator(owner, resolution=ActivityScopeResolution.NOT_FOUND)

    with pytest.raises(TeacherAssessmentDefinitionActivityNotFoundError):
        service.get(owner, space.id, uuid4())


def test_missing_definition_raises_not_found():
    owner = uuid4()
    service, space = orchestrator(owner, activity_allowed=True)

    with pytest.raises(AssessmentDefinitionNotFoundError):
        service.get(owner, space.id, uuid4())


def test_duplicate_create_raises_already_exists():
    owner = uuid4()
    service, space = orchestrator(owner)
    activity = uuid4()
    service.create(owner, space.id, activity, "one")

    with pytest.raises(AssessmentDefinitionAlreadyExistsError):
        service.create(owner, space.id, activity, "two")


def test_archived_definition_cannot_be_updated_or_archived_again():
    owner = uuid4()
    service, space = orchestrator(owner)
    activity = uuid4()
    service.create(owner, space.id, activity, "a")
    service.archive(owner, space.id, activity)

    with pytest.raises(AssessmentDefinitionImmutableError):
        service.update_instructions(owner, space.id, activity, "b")
    with pytest.raises(AssessmentDefinitionImmutableError):
        service.archive(owner, space.id, activity)
    assert service.get(owner, space.id, activity).status.value == "archived"
