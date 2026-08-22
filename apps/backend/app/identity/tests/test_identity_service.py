from datetime import timedelta
from typing import Any

import pytest

from app.identity.application.errors import DuplicateIdentityError, InvalidCredentialsError
from app.identity.application.services import IdentityService
from app.identity.infrastructure.passwords import Argon2PasswordService


class IdentityMemoryRepository:
    def __init__(self) -> None:
        self.by_email: dict[str, Any] = {}
        self.by_id: dict[Any, Any] = {}

    def get_by_email(self, email):
        return self.by_email.get(email)

    def get_by_id(self, identity_id):
        return self.by_id.get(identity_id)

    def add(self, identity):
        self.by_email[identity.email] = identity
        self.by_id[identity.id] = identity
        return identity


class SessionMemoryRepository:
    def __init__(self) -> None:
        self.sessions: dict[str, list[Any]] = {}

    def create(self, identity_id, token_digest, expires_at):
        self.sessions[token_digest] = [identity_id, expires_at, False]

    def get_identity_id(self, token_digest, now):
        session = self.sessions.get(token_digest)
        return session[0] if session and not session[2] and session[1] > now else None

    def revoke(self, token_digest, now):
        session = self.sessions.get(token_digest)
        if not session or session[2]:
            return False
        session[2] = True
        return True


@pytest.fixture
def service() -> IdentityService:
    return IdentityService(
        IdentityMemoryRepository(), Argon2PasswordService(), SessionMemoryRepository(),
        timedelta(hours=1),
    )


def test_registration_normalizes_email_and_hashes_password(service: IdentityService) -> None:
    identity = service.register("  Person@Example.COM ", "a secure password")
    assert identity.email == "person@example.com"
    assert identity.password_hash != "a secure password"
    assert service.passwords.verify("a secure password", identity.password_hash)


def test_duplicate_registration_is_rejected(service: IdentityService) -> None:
    service.register("person@example.com", "a secure password")
    with pytest.raises(DuplicateIdentityError):
        service.register("PERSON@example.com", "another password")


def test_valid_credentials_create_session(service: IdentityService) -> None:
    expected = service.register("person@example.com", "a secure password")
    identity, token = service.login("person@example.com", "a secure password")
    assert identity == expected
    assert service.authenticate(token) == expected


def test_invalid_credentials_are_rejected(service: IdentityService) -> None:
    service.register("person@example.com", "a secure password")
    with pytest.raises(InvalidCredentialsError):
        service.login("person@example.com", "wrong password")


def test_unknown_identity_still_performs_password_verification() -> None:
    class RecordingPasswordService:
        fallback_was_used = False

        def hash(self, password: str) -> str:
            return password

        def verify(self, password: str, password_hash: str) -> bool:
            return False

        def verify_or_dummy(self, password: str, password_hash: str | None) -> bool:
            self.fallback_was_used = password_hash is None
            return False

    passwords = RecordingPasswordService()
    service = IdentityService(
        IdentityMemoryRepository(), passwords, SessionMemoryRepository(), timedelta(hours=1)
    )

    with pytest.raises(InvalidCredentialsError):
        service.login("missing@example.com", "wrong password")

    assert passwords.fallback_was_used
