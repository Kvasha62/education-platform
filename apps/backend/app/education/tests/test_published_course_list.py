from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.education.application.published_course_list import PublishedCourseListService
from app.education.domain.models import CourseStatus
from app.education.infrastructure.models import CourseModel
from app.education.infrastructure.repositories import SqlAlchemyCourseRepository


def test_published_course_list_filters_and_orders_by_created_at_then_id_desc() -> None:
    engine = create_engine("sqlite+pysqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    created_at = datetime(2026, 8, 26, tzinfo=UTC)
    environment_id = UUID("00000000-0000-0000-0000-000000000001")
    lower_id = UUID("00000000-0000-0000-0000-000000000010")
    higher_id = UUID("00000000-0000-0000-0000-000000000020")

    with Session(engine) as session:
        session.add_all(
            [
                CourseModel(
                    id=lower_id,
                    educational_environment_id=environment_id,
                    title="Lower ID",
                    status=CourseStatus.PUBLISHED,
                    created_at=created_at,
                    updated_at=created_at,
                ),
                CourseModel(
                    id=higher_id,
                    educational_environment_id=environment_id,
                    title="Higher ID",
                    status=CourseStatus.PUBLISHED,
                    created_at=created_at,
                    updated_at=created_at,
                ),
                CourseModel(
                    id=UUID("00000000-0000-0000-0000-000000000030"),
                    educational_environment_id=environment_id,
                    title="Draft",
                    status=CourseStatus.DRAFT,
                    created_at=created_at,
                    updated_at=created_at,
                ),
            ]
        )
        session.commit()
        summaries = PublishedCourseListService(
            SqlAlchemyCourseRepository(session)
        ).list_published()

    assert [(item.id, item.title) for item in summaries] == [
        (higher_id, "Higher ID"),
        (lower_id, "Lower ID"),
    ]
