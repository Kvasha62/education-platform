from uuid import uuid4

import pytest

from app.assessment.application.services import AssessmentDefinitionService
from app.education.application.activity_scope import ActivityTeacherSpaceScopeQuery
from app.teacher_space.application.assessment_definitions import (
    AssessmentDefinitionAuthorizationError,
    TeacherAssessmentDefinitionService,
)
from app.teacher_space.application.services import TeacherSpaceService
from app.teacher_space.domain.models import TeacherSpace


class Spaces:
    def __init__(self, space):
        self.space = space

    def get_owned(self, sid, owner):
        return self.space if self.space.id == sid and self.space.owner_user_id == owner else None

    def add(self, value):
        return value

    def list_owned(self, owner):
        return []

    def update(self, value):
        return value


class Scope:
    def __init__(self, allowed):
        self.allowed = allowed

    def belongs_to_teacher_space(self, activity_id, teacher_space_id):
        return self.allowed


class Definitions:
    def __init__(self):
        self.items = {}

    def add(self, v):
        self.items[v.id] = v
        return v

    def get(self, i, a):
        v = self.items.get(i)
        return v if v and v.activity_id == a else None

    def get_by_activity(self, a):
        return next((v for v in self.items.values() if v.activity_id == a), None)

    def update(self, v):
        self.items[v.id] = v
        return v


def orchestrator(owner, allowed=True):
    space = TeacherSpace.create(owner, "Space")
    return TeacherAssessmentDefinitionService(
        TeacherSpaceService(Spaces(space)),
        ActivityTeacherSpaceScopeQuery(Scope(allowed)),
        AssessmentDefinitionService(Definitions()),
    ), space


def test_authorized_teacher_manages_definition():
    owner = uuid4()
    service, space = orchestrator(owner)
    activity = uuid4()
    value = service.create(owner, space.id, activity, "a")
    value = service.update_instructions(owner, space.id, activity, value.id, "b")
    assert service.archive(owner, space.id, activity, value.id).status.value == "archived"


@pytest.mark.parametrize("wrong_owner,allowed", [(True, True), (False, False)])
def test_either_authorization_denial_rejects_operation(wrong_owner, allowed):
    owner = uuid4()
    service, space = orchestrator(owner, allowed)
    with pytest.raises(AssessmentDefinitionAuthorizationError):
        service.create(uuid4() if wrong_owner else owner, space.id, uuid4(), None)
