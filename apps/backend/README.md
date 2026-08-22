# Backend

Minimal FastAPI entry point for the modular monolith.

## Local development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

The operational health endpoint is `GET http://localhost:8000/health`.

Checks:

```bash
ruff check .
pytest
```

## Database migrations

Apply the identity schema before starting the API outside Docker Compose:

```bash
alembic upgrade head
```

## Authentication rate-limit limitations

Authentication rate limiting is process-local and keyed by the direct client IP. Users behind
shared NAT therefore share one limit. Trusted proxy and forwarded-header handling will be
addressed separately if a reverse proxy is introduced; forwarded headers are not trusted today.
