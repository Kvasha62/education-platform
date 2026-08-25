# Frontend

React 19, strict TypeScript, Vite, React Router, TanStack Query, and Vitest form the
frontend foundation. Architecture is defined by `docs/decisions/ADR-0002-frontend-architecture.md`.

## Local development

```bash
cp .env.example .env.local
npm ci
npm run dev
```

`VITE_API_BASE_URL` is the browser-visible backend origin. It defaults to the same origin when
unset; local Docker and standalone development should use `http://localhost:8000`.
Authenticated requests use the backend HttpOnly cookie with `credentials: "include"`.

## Checks

```bash
npm run typecheck
npm test
npm run build
```

## Boundaries

- `app/` owns routing and application provider composition.
- `modules/` owns product/domain frontend logic.
- `shared/` contains reusable technical and presentation primitives only.
- Backend communication goes through `shared/api/`.
