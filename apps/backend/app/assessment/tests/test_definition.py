from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from app.assessment.application.services import (
    AssessmentDefinitionAlreadyExistsError,
    AssessmentDefinitionService,
)
from app.assessment.domain.models import (
    AssessmentDefinition,
    AssessmentDefinitionImmutableError,
    AssessmentDefinitionStatus,
)


class Repo:
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
        return next((v for v in self.items.values() if v.activity_id == activity_id), None)

    def update(self, value):
        self.items[value.id] = value
        return value


def test_definition_lifecycle_and_identity():
    activity_id = uuid4()
    definition = AssessmentDefinition.create(activity_id, None)
    assert definition.activity_id == activity_id and definition.instructions is None
    assert definition.status is AssessmentDefinitionStatus.ACTIVE
    with pytest.raises(FrozenInstanceError):
        definition.activity_id = uuid4()  # type: ignore[misc]
    updated = definition.update_instructions("")
    assert updated.instructions == "" and updated.activity_id == activity_id
    archived = updated.archive()
    assert archived.status is AssessmentDefinitionStatus.ARCHIVED
    with pytest.raises(AssessmentDefinitionImmutableError):
        archived.update_instructions("x")
    with pytest.raises(AssessmentDefinitionImmutableError):
        archived.archive()


def test_one_definition_per_activity():
    service = AssessmentDefinitionService(Repo())
    activity_id = uuid4()
    service.create(activity_id, "one")
    with pytest.raises(AssessmentDefinitionAlreadyExistsError):
        service.create(activity_id, "two")
