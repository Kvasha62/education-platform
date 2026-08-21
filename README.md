# Education Platform

Education Platform is a modular platform for constructing educational environments for learners approximately 6–17 years old.

The project is being developed as a **Modular Monolith** with clear domain boundaries and independent user spaces.

## Current focus

The first product system is **Teacher Space**.

The first vertical slice will establish the technical foundation and then enable a teacher to create and publish a minimal course structure.

## Core documents

- [`PLATFORM_VISION.md`](./PLATFORM_VISION.md) — what we are building.
- [`ARCHITECTURE.md`](./ARCHITECTURE.md) — technical source of truth.
- [`AGENTS.md`](./AGENTS.md) — mandatory operating rules for Arena and other implementation agents.
- [`CONTRIBUTING.md`](./CONTRIBUTING.md) — development and Git/PR workflow.

## Development principle

Build small, preserve boundaries, test continuously, and add future systems through independent modules rather than creating one tightly coupled application.

## Local development

Copy the local environment template and start the four-service stack:

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: `http://localhost:5173`
- Backend health: `http://localhost:8000/health`
- Backend OpenAPI: `http://localhost:8000/docs`
- MinIO console: `http://localhost:9001`

Service-specific setup and checks are documented in `apps/backend/README.md` and
`apps/frontend/README.md`.

## Status

EDU-001 provides the runnable repository and architecture foundation. Product functionality is intentionally not implemented yet.
