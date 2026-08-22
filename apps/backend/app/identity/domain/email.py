"""Identity email convention."""


def normalize_email(email: str) -> str:
    """Normalize identity keys using trimmed, case-insensitive email addresses."""
    return email.strip().casefold()
