"""PostgreSQL-compatible identity repositories."""

from datetime import datetime
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.identity.application.errors import DuplicateIdentityError
from app.identity.domain.models import Identity
from app.identity.infrastructure.models import AuthSessionModel, IdentityModel


def _to_domain(model: IdentityModel) -> Identity:
    return Identity(
        id=model.id,
        email=model.email,
        password_hash=model.password_hash,
        status=model.status,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyIdentityRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_email(self, email: str) -> Identity | None:
        model = self.db.scalar(select(IdentityModel).where(IdentityModel.email == email))
        return _to_domain(model) if model else None

    def get_by_id(self, identity_id: UUID) -> Identity | None:
        model = self.db.get(IdentityModel, identity_id)
        return _to_domain(model) if model else None

    def add(self, identity: Identity) -> Identity:
        model = IdentityModel(
            id=identity.id,
            email=identity.email,
            password_hash=identity.password_hash,
            status=identity.status,
            created_at=identity.created_at,
            updated_at=identity.updated_at,
        )
        try:
            with self.db.begin_nested():
                self.db.add(model)
                self.db.flush()
        except IntegrityError as error:
            raise DuplicateIdentityError from error
        return _to_domain(model)


class SqlAlchemySessionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, identity_id: UUID, token_digest: str, expires_at: datetime) -> None:
        self.db.add(
            AuthSessionModel(
                id=uuid4(), identity_id=identity_id, token_digest=token_digest,
                expires_at=expires_at, revoked_at=None, created_at=datetime.now(expires_at.tzinfo)
            )
        )
        self.db.flush()

    def get_identity_id(self, token_digest: str, now: datetime) -> UUID | None:
        return self.db.scalar(
            select(AuthSessionModel.identity_id).where(
                AuthSessionModel.token_digest == token_digest,
                AuthSessionModel.revoked_at.is_(None),
                AuthSessionModel.expires_at > now,
            )
        )

    def revoke(self, token_digest: str, now: datetime) -> bool:
        result = self.db.execute(
            update(AuthSessionModel)
            .where(AuthSessionModel.token_digest == token_digest, AuthSessionModel.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        return bool(cast(CursorResult[tuple[()]], result).rowcount)
