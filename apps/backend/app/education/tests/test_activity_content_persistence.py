from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

from sqlalchemy import Index, Table, create_engine, event
from sqlalchemy.orm import Session

from app.core.database import Base
from app.education.domain.content_links import ActivityContentLink
from app.education.domain.models import ActivityType
from app.education.infrastructure.content_links import (
    SqlAlchemyActivityContentLinkRepository,
)
from app.education.infrastructure.models import (
    ActivityContentLinkModel,
    ActivityModel,
    CourseModel,
    EducationalEnvironmentModel,
    LearningUnitModel,
    SectionModel,
)


def test_association_schema_contract() -> None:
    table = cast(Table, ActivityContentLinkModel.__table__)
    assert [column.name for column in table.primary_key.columns] == [
        "activity_id",
        "content_id",
    ]
    assert {key.target_fullname for key in table.foreign_keys} == {"activities.id"}
    activity_fk = next(iter(table.foreign_keys))
    assert activity_fk.ondelete == "CASCADE"
    assert not table.c.content_id.nullable
    assert not table.c.content_id.foreign_keys
    assert any(
        isinstance(index, Index) and [column.name for column in index.columns] == ["content_id"]
        for index in table.indexes
    )


def test_repository_supports_idempotent_attach_detach_and_both_list_directions() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    activity_id, content_id = uuid4(), uuid4()
    with Session(engine) as session:
        repository = SqlAlchemyActivityContentLinkRepository(session)
        link = ActivityContentLink(activity_id, content_id)
        repository.attach(link)
        repository.attach(link)

        assert repository.exists(activity_id, content_id)
        assert repository.list_for_activity(activity_id) == [link]
        assert repository.list_for_content(content_id) == [link]

        repository.detach(activity_id, content_id)
        repository.detach(activity_id, content_id)
        assert not repository.exists(activity_id, content_id)


def test_activity_delete_cascades_association_rows() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    now = datetime.now(UTC)
    environment_id, course_id, section_id, unit_id, activity_id = (uuid4() for _ in range(5))
    with Session(engine) as session:
        session.add(
            EducationalEnvironmentModel(
                id=environment_id,
                teacher_space_id=uuid4(),
                name="Environment",
                created_at=now,
                updated_at=now,
            )
        )
        session.flush()
        session.add(
            CourseModel(
                id=course_id,
                educational_environment_id=environment_id,
                title="Course",
                created_at=now,
                updated_at=now,
            )
        )
        session.flush()
        session.add(
            SectionModel(
                id=section_id,
                course_id=course_id,
                title="Section",
                position=0,
                created_at=now,
                updated_at=now,
            )
        )
        session.flush()
        session.add(
            LearningUnitModel(
                id=unit_id,
                section_id=section_id,
                title="Unit",
                position=0,
                created_at=now,
                updated_at=now,
            )
        )
        session.flush()
        session.add(
            ActivityModel(
                id=activity_id,
                learning_unit_id=unit_id,
                title="Activity",
                type=ActivityType.LECTURE,
                position=0,
                created_at=now,
                updated_at=now,
            )
        )
        session.flush()
        session.add(ActivityContentLinkModel(activity_id=activity_id, content_id=uuid4()))
        session.commit()

        session.delete(session.get(ActivityModel, activity_id))
        session.commit()

        assert session.query(ActivityContentLinkModel).count() == 0
