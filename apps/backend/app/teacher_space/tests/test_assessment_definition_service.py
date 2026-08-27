from typing import cast
from uuid import uuid4

import pytest

from app.assessment.application.services import AssessmentDefinitionService
from app.education.application.activity_scope import (
    ActivityScopeResolution,
    ActivityTeacherSpaceScopeQuery,
)
from app.teacher_space.application.assessment_definitions import (
    AssessmentDefinitionAuthorizationError,
    TeacherAssessmentDefinitionService,
)
from app.teacher_space.application.errors import TeacherSpaceNotFoundError
from app.teacher_space.application.services import TeacherSpaceService
from app.teacher_space.domain.models import TeacherSpace


class TeacherSpaces:
    """Service-level double matching TeacherSpaceService.get_owned()."""

    def __init__(self, space):
        self.space = space

    def get_owned(self, teacher_space_id, owner_user_id):
        if (
            self.space.id != teacher_space_id
            or self.space.owner_user_id != owner_user_id
        ):
            raise TeacherSpaceNotFoundError
        return self.space


class Scope:
    def __init__(self, allowed):
        self.allowed = allowed

    def belongs_to_teacher_space(self, activity_id, teacher_space_id):
        return self.allowed

    def resolve_activity_scope(self, activity_id, teacher_space_id):
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


def orchestrator(owner, activity_allowed=True):
    space = TeacherSpace.create(owner, "Space")
    return TeacherAssessmentDefinitionService(
        cast(TeacherSpaceService, TeacherSpaces(space)),
        ActivityTeacherSpaceScopeQuery(Scope(activity_allowed)),
        AssessmentDefinitionService(Definitions()),
    ), space


def test_authorized_teacher_manages_definition():
    owner = uuid4()
    service, space = orchestrator(owner)
    activity = uuid4()
    value = service.create(owner, space.id, activity, "a")
    value = service.update_instructions(owner, space.id, activity, value.id, "b")
    assert service.archive(owner, space.id, activity, value.id).status.value == "archived"


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
