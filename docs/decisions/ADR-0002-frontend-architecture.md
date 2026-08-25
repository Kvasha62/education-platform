# ADR-0002 — Frontend Architecture

- **Status:** Accepted
- **Date:** 2026-08-25
- **Decision:** Establish the architectural foundation for the React frontend before feature implementation.

## Context

The backend foundation is ready to proceed to frontend development. EDU-024 confirmed that the backend architecture, bounded-context boundaries, authentication, ownership enforcement, migrations, API contracts, and test suite are suitable for starting Frontend Foundation.

The existing frontend is intentionally minimal. Before EDU-025, the project needs explicit frontend architectural rules so implementation tasks do not introduce ad-hoc routing, API access, state management, authentication, or cross-module business logic.

## Decision

### 1. Frontend stack

The frontend remains:

- React 19;
- TypeScript with strict mode;
- Vite.

No framework migration is introduced by this ADR.

### 2. Application structure

The frontend follows this structure:

```text
apps/frontend/src/
├── app/
│   ├── App.tsx
│   ├── router.tsx
│   └── providers.tsx
│
├── modules/
│   ├── identity/
│   ├── teacher/
│   ├── education/
│   ├── content/
│   └── learning/
│
└── shared/
    ├── api/
    ├── ui/
    ├── types/
    ├── utils/
    └── config/
```

The structure is a boundary, not a requirement to create empty files or speculative abstractions. Directories are introduced when they have a concrete implementation need.

### 3. Routing

Use React Router for client-side routing.

Route definitions belong to `app/router.tsx` or its directly associated routing modules. Feature modules must not create unrelated global routes implicitly.

### 4. API client

All backend HTTP communication must go through `shared/api/`.

Feature components must not scatter raw `fetch` calls throughout UI code.

The API client must support the backend's cookie-based authentication model and use:

```text
credentials: "include"
```

for authenticated requests.

The backend API base URL must be configuration-driven, not hard-coded into feature code.

### 5. Authentication

Authentication uses the existing backend session-cookie model.

The frontend must not store authentication/session tokens in:

- `localStorage`;
- `sessionStorage`;
- frontend-readable persistent token stores.

Application bootstrap must establish authentication state through:

```text
GET /api/v1/auth/me
```

The frontend must distinguish at least:

- authenticated;
- unauthenticated;
- authentication state loading;
- authentication/bootstrap error where applicable.

Login, registration, and logout UI are feature work and are not part of this ADR's implementation scope unless explicitly included by a later Issue.

### 6. Server state

Use TanStack Query for server/API state.

Server state must not be duplicated into a custom global store without a concrete architectural reason.

TanStack Query owns concerns such as:

- fetching;
- caching;
- refetching;
- request loading state;
- request error state;
- invalidation.

### 7. Client state

Use normal React state and context for local/application UI state where appropriate.

Do not introduce Redux or another global state framework as part of Frontend Foundation unless a concrete requirement demonstrates that the existing approach is insufficient.

### 8. Module boundaries

Frontend modules mirror the backend product/domain boundaries:

```text
identity
teacher
education
content
learning
```

Business logic belonging to a module stays inside that module.

`shared/` contains reusable technical/UI primitives only. It must not become a dumping ground for product-specific business logic.

Examples of shared concerns:

- API infrastructure;
- generic UI primitives;
- generic types/utilities;
- application configuration.

Examples that belong in modules:

- course creation rules;
- teacher-space workflows;
- content lifecycle UI logic;
- enrollment workflows;
- progress workflows.

### 9. UI foundation

`shared/ui/` contains reusable presentation primitives such as:

- Button;
- Input;
- FormField;
- Modal;
- Spinner/LoadingState;
- ErrorState;
- generic layout primitives.

Product-specific components remain in their owning module.

### 10. Error handling

API errors must be normalized at the API/application boundary rather than parsed independently throughout feature components.

The frontend should provide consistent handling for:

- validation errors;
- unauthorized/session-expired responses;
- not-found responses;
- conflict responses;
- forbidden responses;
- unavailable/backend errors.

The exact visual treatment belongs to the relevant feature Issue, not to this ADR.

### 11. Environment configuration

Frontend runtime/build configuration must use Vite environment variables, for example:

```text
VITE_API_BASE_URL
```

Development URLs must not be hard-coded into production-oriented application code.

The exact local proxy strategy may be implemented consistently with this decision, but it must preserve the same API contract and cookie behavior.

### 12. Testing foundation

Frontend Foundation should establish a minimal test foundation using:

- Vitest;
- React Testing Library.

Browser E2E is intentionally not part of EDU-025. It should be introduced once a meaningful end-to-end user workflow exists and the E2E strategy is approved.

### 13. Accessibility and UI quality

New reusable UI primitives should use semantic HTML and accessible interaction patterns by default.

A full accessibility test/tooling strategy is outside EDU-025 unless explicitly added to its scope.

## Dependency Rules

The following direction is allowed:

```text
app
 ↓
modules
 ↓
shared
```

Shared code must not import product-specific modules.

Modules should not reach into another module's private implementation. Cross-module interaction must use explicit public interfaces where such interaction is required.

The frontend must not depend directly on backend infrastructure, database models, or persistence implementation details.

## Scope of EDU-025

EDU-025 — Frontend Foundation may implement:

- application shell;
- React Router setup;
- provider composition;
- API client foundation;
- API base URL configuration;
- authentication bootstrap through `/api/v1/auth/me`;
- authenticated/unauthenticated application state;
- TanStack Query foundation;
- module boundaries;
- shared UI foundation;
- minimal frontend test foundation;
- loading/error/session-expired infrastructure required by the above.

## Explicitly Out of Scope for EDU-025

The following are feature work for later Issues:

- login page;
- registration page;
- Teacher Dashboard;
- Course Builder;
- Course Editor;
- Content Editor;
- Student Dashboard;
- Student Player;
- enrollment UI;
- progress UI;
- complete teacher-to-student workflow;
- browser E2E suite.

## Consequences

### Positive

- Frontend implementation follows explicit architectural boundaries.
- API access is centralized.
- Backend cookie authentication is preserved without exposing session tokens to JavaScript.
- Server state has a defined owner.
- Feature code remains separated from shared infrastructure.
- Future EDU tasks can be smaller and more deterministic.

### Trade-offs

- TanStack Query becomes an additional frontend dependency.
- The project has both server-state management and ordinary React state, requiring developers to understand the distinction.
- Explicit module boundaries require discipline when features interact.

## Rejected Alternatives

### Redux as the default global state layer

Rejected for the current foundation because the existing requirements do not justify a general-purpose global state store. It can be reconsidered if concrete product requirements require it.

### Token storage in localStorage/sessionStorage

Rejected because the backend already uses HttpOnly session cookies and the frontend does not need direct access to authentication tokens.

### Raw fetch calls throughout components

Rejected because it would duplicate authentication, error handling, base URL, and request behavior across the application.

### Browser E2E in EDU-025

Deferred until there is a meaningful user-facing workflow to test.

## Compliance Requirements

Future frontend Issues must comply with this ADR unless an Issue explicitly proposes an architectural change and obtains approval before implementation.

Arena must not silently replace these decisions with alternative routing, state-management, authentication, or module-boundary strategies.