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
