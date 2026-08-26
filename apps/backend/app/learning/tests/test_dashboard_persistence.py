from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.identity.infrastructure import models as identity_models  # noqa: F401
from app.learning.domain.progress import ProgressStatus
from app.learning.infrastructure.models import ActivityProgressModel
from app.learning.infrastructure.progress import SqlAlchemyProgressRepository


def test_in_progress_dashboard_query_filters_student_status_and_orders_stably() -> None:
    engine = create_engine("sqlite+pysqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    student_id = UUID("00000000-0000-0000-0000-000000000001")
    other_student_id = UUID("00000000-0000-0000-0000-000000000002")
    now = datetime.now(UTC)
    lower_id = UUID("00000000-0000-0000-0000-000000000010")
    higher_id = UUID("00000000-0000-0000-0000-000000000020")

    def model(
        progress_id: UUID,
        owner_id: UUID,
        status: ProgressStatus,
        updated_at: datetime,
    ) -> ActivityProgressModel:
        return ActivityProgressModel(
            id=progress_id,
            student_user_id=owner_id,
            activity_id=progress_id,
            status=status,
            created_at=updated_at,
            updated_at=updated_at,
        )

    with Session(engine) as session:
        session.add_all(
            [
                model(lower_id, student_id, ProgressStatus.IN_PROGRESS, now),
                model(higher_id, student_id, ProgressStatus.IN_PROGRESS, now),
                model(
                    UUID("00000000-0000-0000-0000-000000000030"),
                    student_id,
                    ProgressStatus.COMPLETED,
                    now + timedelta(minutes=1),
                ),
                model(
                    UUID("00000000-0000-0000-0000-000000000040"),
                    other_student_id,
                    ProgressStatus.IN_PROGRESS,
                    now + timedelta(minutes=2),
                ),
            ]
        )
        session.commit()
        result = SqlAlchemyProgressRepository(session).list_in_progress(student_id)

    assert [item.id for item in result] == [higher_id, lower_id]
