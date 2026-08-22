"""Argon2 password hashing adapter."""

from pwdlib import PasswordHash


class Argon2PasswordService:
    def __init__(self) -> None:
        self._password_hash = PasswordHash.recommended()
        self._dummy_hash = self._password_hash.hash("timing-only-dummy-password")

    def hash(self, password: str) -> str:
        return self._password_hash.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        return self._password_hash.verify(password, password_hash)

    def verify_or_dummy(self, password: str, password_hash: str | None) -> bool:
        """Always perform Argon2 verification, including for unknown identities."""
        return self.verify(password, password_hash or self._dummy_hash)
