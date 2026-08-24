from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.learning.domain.progress import ActivityProgress
from app.learning.infrastructure.models import ActivityProgressModel
from app.learning.infrastructure.progress import SqlAlchemyProgressRepository


def test_concurrent_start_creates_one_progress_row(tmp_path) -> None:
    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path / 'progress.db'}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    student_id, activity_id = uuid4(), uuid4()
    ready = Barrier(2)

    def start() -> ActivityProgress:
        with factory() as session:
            ready.wait()
            progress = SqlAlchemyProgressRepository(session).get_or_create(
                ActivityProgress.start(student_id, activity_id)
            )
            session.commit()
            return progress

    with ThreadPoolExecutor(max_workers=2) as executor:
        first, second = executor.submit(start), executor.submit(start)
        results = [first.result(), second.result()]

    assert results[0].id == results[1].id
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(ActivityProgressModel)) == 1
