"""Identity registration and authentication use cases."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.identity.application.errors import (
    DuplicateIdentityError,
    InvalidCredentialsError,
    InvalidSessionError,
)
from app.identity.application.ports import IdentityRepository, PasswordService, SessionRepository
from app.identity.domain.email import normalize_email
from app.identity.domain.models import Identity, IdentityStatus


def digest_session_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class IdentityService:
    def __init__(
        self,
        identities: IdentityRepository,
        passwords: PasswordService,
        sessions: SessionRepository,
        session_ttl: timedelta,
    ) -> None:
        self.identities = identities
        self.passwords = passwords
        self.sessions = sessions
        self.session_ttl = session_ttl

    def register(self, email: str, password: str) -> Identity:
        normalized_email = normalize_email(email)
        if self.identities.get_by_email(normalized_email):
            raise DuplicateIdentityError
        now = datetime.now(UTC)
        identity = Identity(
            id=uuid4(),
            email=normalized_email,
            password_hash=self.passwords.hash(password),
            status=IdentityStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        return self.identities.add(identity)

    def login(self, email: str, password: str) -> tuple[Identity, str]:
        identity = self.identities.get_by_email(normalize_email(email))
        if (
            identity is None
            or identity.status is not IdentityStatus.ACTIVE
            or not self.passwords.verify(password, identity.password_hash)
        ):
            raise InvalidCredentialsError
        token = secrets.token_urlsafe(32)
        now = datetime.now(UTC)
        self.sessions.create(identity.id, digest_session_token(token), now + self.session_ttl)
        return identity, token

    def authenticate(self, token: str) -> Identity:
        identity_id = self.sessions.get_identity_id(
            digest_session_token(token), datetime.now(UTC)
        )
        identity = self.identities.get_by_id(identity_id) if identity_id else None
        if identity is None or identity.status is not IdentityStatus.ACTIVE:
            raise InvalidSessionError
        return identity

    def logout(self, token: str) -> None:
        """Revoke a session when present; logout is intentionally idempotent."""
        self.sessions.revoke(digest_session_token(token), datetime.now(UTC))
