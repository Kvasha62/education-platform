from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.identity.infrastructure import models as identity_models  # noqa: F401
from app.learning.domain.progress import ProgressStatus
from app.learning.infrastructure.models import ActivityProgressModel
from app.learning.infrastructure.progress import SqlAlchemyProgressRepository


def test_completed_activity_count_is_one_set_based_query() -> None:
    engine = create_engine("sqlite+pysqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    student_id, other_student_id = uuid4(), uuid4()
    counted_completed, counted_in_progress, outside_scope = uuid4(), uuid4(), uuid4()
    now = datetime.now(UTC)

    def model(student_id, activity_id, status):
        return ActivityProgressModel(
            id=uuid4(),
            student_user_id=student_id,
            activity_id=activity_id,
            status=status,
            created_at=now,
            updated_at=now,
        )

    with Session(engine) as session:
        session.add_all(
            [
                model(student_id, counted_completed, ProgressStatus.COMPLETED),
                model(student_id, counted_in_progress, ProgressStatus.IN_PROGRESS),
                model(student_id, outside_scope, ProgressStatus.COMPLETED),
                model(other_student_id, counted_in_progress, ProgressStatus.COMPLETED),
            ]
        )
        session.commit()
        statements = 0

        def count_queries(*_args) -> None:
            nonlocal statements
            statements += 1

        event.listen(engine, "before_cursor_execute", count_queries)
        result = SqlAlchemyProgressRepository(session).count_completed(
            student_id,
            [counted_completed, counted_in_progress],
        )
        event.remove(engine, "before_cursor_execute", count_queries)

    assert result == 1
    assert statements == 1
