from uuid import uuid4

import pytest

from app.assessment.application.attempts import (
    AssessmentAttemptService,
    AssessmentDefinitionUnavailableError,
)
from app.assessment.domain.models import AssessmentDefinition


class Definitions:
    def __init__(self, d):
        self.d = d

    def get(self, i, a):
        return self.d if self.d.id == i and self.d.activity_id == a else None

    def get_by_activity(self, a):
        return self.d if self.d.activity_id == a else None

    def add(self, d):
        return d

    def update(self, d):
        return d


class Attempts:
    def __init__(self):
        self.items = {}

    def add(self, a):
        self.items[a.id] = a
        return a

    def get_owned(self, i, d, s):
        a = self.items.get(i)
        return a if a and a.assessment_definition_id == d and a.student_id == s else None

    def update(self, a):
        self.items[a.id] = a
        return a

    def list_owned(self, d, s):
        return [
            a for a in self.items.values() if a.assessment_definition_id == d and a.student_id == s
        ]


def test_multiple_attempts_and_archived_definition_rules():
    activity, student = uuid4(), uuid4()
    definition = AssessmentDefinition.create(activity, None)
    attempts = Attempts()
    service = AssessmentAttemptService(attempts, Definitions(definition))
    draft = service.create(definition.id, activity, student, "one")
    second = service.create(definition.id, activity, student, "two")
    assert draft.id != second.id
    archived = definition.archive()
    blocked = AssessmentAttemptService(attempts, Definitions(archived))
    with pytest.raises(AssessmentDefinitionUnavailableError):
        blocked.create(archived.id, activity, student, None)
    assert blocked.submit(draft.id, archived.id, student).status.value == "submitted"
