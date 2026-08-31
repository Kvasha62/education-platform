# E2E Tests

Playwright end-to-end tests for Education Platform (ARCHITECTURE.md §3 testing baseline,
§26 first critical journey, §27 CI). EDU-085.

The suite covers the first critical user journey through the real UI:

```text
Login → Teacher Dashboard → Create Educational Environment → Create Course
→ Create Section → Create Learning Unit → Create Activity → Save Draft
→ Preview → Publish
```

The tests drive the application as a user: accessible roles, labels and text.
No direct API calls replace UI actions, no React/TanStack Query internals and no
domain/application code are used for verification.

## What Playwright manages

`playwright.config.ts` starts the application servers itself on dedicated ports
(they never collide with a running Docker Compose stack):

| Service  | Port | Started by                                            |
| -------- | ---- | ----------------------------------------------------- |
| frontend | 4173 | `npm run build && vite preview` (production build)    |
| backend  | 8100 | `alembic upgrade head && uvicorn app.main:app`        |
| postgres | 5432 | **external** — Docker Compose or a CI service container |

## Prerequisites (one time)

1. PostgreSQL reachable at `localhost:5432` with the `.env.example` defaults:

   ```bash
   docker compose up -d postgres
   ```

2. Backend dependencies installed (used by the Playwright-managed backend):

   ```bash
   cd apps/backend
   python -m venv .venv && . .venv/bin/activate
   pip install -e .
   ```

3. Frontend dependencies installed (used for the production build):

   ```bash
   cd apps/frontend
   npm ci
   ```

4. Playwright dependencies and the Chromium browser:

   ```bash
   cd tests/e2e
   npm ci
   npx playwright install --with-deps chromium
   ```

## Run locally

```bash
cd tests/e2e
npm test
```

Environment overrides (usually not needed):

- `DATABASE_URL` — PostgreSQL connection string for the Playwright-managed backend
  (default: the `.env.example` local development value).

## Test data and isolation

- Each run registers a fresh user through the public registration UI with a
  unique email, then logs out so the journey starts at Login.
- All created entities (Teacher Space, Environment, Course, structure) belong to
  that user, so runs are isolated even against a shared local database.
- `workers: 1`, no parallelism. The authentication rate limits
  (`AUTH_REGISTER_RATE_LIMIT=5`, `AUTH_LOGIN_RATE_LIMIT=10` per 60 s per client
  IP) are production behavior: repeated full runs within one minute may be
  throttled with `429` — wait 60 s and rerun.

## Failure artifacts

- HTML report: `tests/e2e/playwright-report/` (open `playwright-report/index.html`).
- Traces (first retry), screenshots and logs on failure: `tests/e2e/test-results/`.
- In CI both folders are uploaded as workflow artifacts on failure.

## CI

The `e2e` job in `.github/workflows/ci.yml` starts a PostgreSQL service
container, installs backend/frontend/Playwright dependencies and runs
`npx playwright test` from `tests/e2e`. Existing backend and frontend jobs are
unchanged.
