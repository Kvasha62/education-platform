from typing import cast

from sqlalchemy import JSON, Enum, Index, String, Table
from sqlalchemy.dialects import postgresql

from app.content.infrastructure.models import ContentModel


def test_content_persistence_contract_and_owner_fk() -> None:
    table = cast(Table, ContentModel.__table__)
    assert set(table.c.keys()) == {
        "id",
        "owner_user_id",
        "type",
        "title",
        "status",
        "body",
        "created_at",
        "updated_at",
    }
    assert {key.target_fullname for key in table.foreign_keys} == {"identities.id"}
    assert cast(String, table.c.title.type).length == 120
    assert set(cast(Enum, table.c.type.type).enums) == {"article", "resource"}
    assert set(cast(Enum, table.c.status.type).enums) == {"draft", "published"}
    assert isinstance(table.c.body.type, JSON)
    assert isinstance(table.c.body.type.dialect_impl(postgresql.dialect()), postgresql.JSONB)
    assert not table.c.body.nullable
    assert any(
        isinstance(index, Index)
        and [column.name for column in index.columns] == ["owner_user_id", "created_at"]
        for index in table.indexes
    )


def test_content_has_no_education_or_teacher_foreign_keys() -> None:
    forbidden = {
        "teacher_spaces",
        "educational_environments",
        "courses",
        "sections",
        "learning_units",
        "activities",
    }
    table = cast(Table, ContentModel.__table__)
    assert all(key.column.table.name not in forbidden for key in table.foreign_keys)


def test_content_page_ordering_uses_created_at_then_id() -> None:
    from datetime import UTC, datetime
    from uuid import UUID

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import StaticPool

    from app.content.domain.body import ContentBody
    from app.content.domain.models import Content, ContentStatus, ContentType
    from app.content.infrastructure.repositories import SqlAlchemyContentRepository
    from app.core.database import Base

    engine = create_engine("sqlite+pysqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    owner = UUID("00000000-0000-0000-0000-000000000001")
    created_at = datetime(2026, 8, 25, tzinfo=UTC)
    later_id = UUID("00000000-0000-0000-0000-000000000020")
    earlier_id = UUID("00000000-0000-0000-0000-000000000010")

    with Session(engine) as session:
        repository = SqlAlchemyContentRepository(session)
        for content_id in (later_id, earlier_id):
            repository.add(
                Content(
                    id=content_id,
                    owner_user_id=owner,
                    type=ContentType.ARTICLE,
                    title=str(content_id),
                    status=ContentStatus.DRAFT,
                    body=ContentBody.article_empty(),
                    created_at=created_at,
                    updated_at=created_at,
                )
            )
        session.commit()
        page = repository.list_owned(owner, offset=0, limit=3)

    assert [item.id for item in page] == [earlier_id, later_id]
