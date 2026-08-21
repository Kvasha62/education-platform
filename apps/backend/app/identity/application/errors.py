"""Stable identity application errors."""


class IdentityError(Exception):
    pass


class DuplicateIdentityError(IdentityError):
    pass


class InvalidCredentialsError(IdentityError):
    pass


class InvalidSessionError(IdentityError):
    pass
