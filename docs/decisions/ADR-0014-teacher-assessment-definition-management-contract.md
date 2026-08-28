# ADR-0014 — Teacher AssessmentDefinition Management Contract

- **Status:** Proposed
- **Date:** 2026-08-28
- **Issue:** EDU-075
- **Decision:** Define the normative Teacher-facing HTTP/application contract for reading, creating, updating, and archiving the AssessmentDefinition associated with an Activity inside an authorized Teacher Space.

## Context

ADR-0006 establishes Assessment as an independent bounded context. Education owns `Activity`; Assessment owns `AssessmentDefinition`, `AssessmentAttempt`, and `AssessmentResult`. The relationship is:

```text
Activity (Education)
    1 ─── 0..1 ─── AssessmentDefinition (Assessment)
```

ADR-0013 defines `assessment_definition_id: UUID | null` on the Teacher Activity projection as an entry signal. It rejects a redundant lookup endpoint whose purpose is only to discover that relationship or obtain its identifier.

ADR-0013 Amendment 001 clarifies that this rejection does not prohibit a separately defined Teacher AssessmentDefinition Management resource READ operation that returns the complete AssessmentDefinition resource.

The actual AssessmentDefinition resource in this repository is already minimal:

```text
AssessmentDefinition
├── id: UUID
├── activity_id: UUID
├── instructions: string | null
└── status: active | archived
```

The Assessment definition lifecycle already implemented by the domain is:

```text
ACTIVE → ARCHIVED
```

No reactivation and no deletion exist.

## Decision

Teacher AssessmentDefinition Management is an Assessment-owned management capability exposed through the existing Teacher Space authorization orchestration. The canonical resource is Activity-scoped:

```text
Teacher Space
    |
    +── Activity
           |
           +── 0..1 AssessmentDefinition
```

The canonical HTTP routes are:

```text
GET   /api/v1/teacher-spaces/{teacher_space_id}/activities/{activity_id}/assessment-definition
POST  /api/v1/teacher-spaces/{teacher_space_id}/activities/{activity_id}/assessment-definition
PATCH /api/v1/teacher-spaces/{teacher_space_id}/activities/{activity_id}/assessment-definition
POST  /api/v1/teacher-spaces/{teacher_space_id}/activities/{activity_id}/assessment-definition/archive
```

There is no separate `/assessment-definitions/{id}` resource and no separate `/activities/{activity_id}/assessment-definition` entry-signal lookup. The management API is the only Teacher AssessmentDefinition resource API. `assessment_definition_id` is never supplied by the client in a path, query parameter, or request body for these routes.

## Resource Representation

The normative response representation is exactly:

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "activity_id": "00000000-0000-0000-0000-000000000000",
  "instructions": "string | null",
  "status": "active"
}
```

Field rules:

```text
id           → UUID; required; server-owned; immutable
activity_id  → UUID; required; server-owned; immutable
instructions → string | null; optional content; mutable while ACTIVE
status       → "active" | "archived"; required; server-owned lifecycle state
```

The contract does **not** define `title`, `description`, `configuration`, `created_at`, `updated_at`, `owner_user_id`, `teacher_id`, `teacher_space_id`, audit metadata, revision numbers, or any other field. Those are not present in the current domain model. Serialization of `status` uses the existing `AssessmentDefinitionStatus` enum values:

```text
ACTIVE   → "active"
ARCHIVED → "archived"
```

The uppercase `ACTIVE` / `ARCHIVED` labels are conceptual lifecycle names only; the wire value is lowercase.

## Route and DTO Semantics

### Requests never contain Activity identity

`activity_id` is provided only by the route. It is never accepted or required in any request body, query parameter, or header.

All request DTOs use `extra = "forbid"`, consistent with the existing Assessment and Teacher Space API schema conventions. Unknown fields are rejected as `422`.

### CREATE

```http
POST /api/v1/teacher-spaces/{teacher_space_id}/activities/{activity_id}/assessment-definition
```

Request body:

```json
{
  "instructions": "Read chapter three and answer the questions."
}
```

or, to create without instructions:

```json
{
  "instructions": null
}
```

Field rules:

```text
instructions → string | null; required field
             → null creates a Definition with null instructions
             → string stores the exact supplied value
```

There is no trimming, no blank-to-null normalization, and no maximum length in the current domain model. Empty string `""` and whitespace-only strings are valid and are stored exactly.

Successful creation returns `201 Created` and the complete management representation:

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "activity_id": "00000000-0000-0000-0000-000000000000",
  "instructions": "Read chapter three and answer the questions.",
  "status": "active"
}
```

Creation always produces `status = "active"`.

### READ

```http
GET /api/v1/teacher-spaces/{teacher_space_id}/activities/{activity_id}/assessment-definition
```

A successful read returns `200 OK` and the complete management representation.

Both `active` and `archived` Definitions are readable. Archival does not hide the resource.

If the Activity is valid and authorized but has no AssessmentDefinition, the response is `404` with detail `"Assessment Definition not found"`.

### UPDATE

```http
PATCH /api/v1/teacher-spaces/{teacher_space_id}/activities/{activity_id}/assessment-definition
```

Request body (partial):

```json
{
  "instructions": "Updated instructions."
}
```

or, to clear instructions:

```json
{
  "instructions": null
}
```

Field rules:

```text
instructions → string | null; optional field
             → when present, fully replaces the existing instructions value
             → null clears instructions
             → no trimming, blank normalization, or maximum length
```

The only mutable field is `instructions`. The following are immutable and are never accepted or changed through PATCH:

```text
id
activity_id
status
any server-owned scope/owner/authorization context
```

A PATCH body that supplies no mutable field (for example `{}`) is invalid and returns `422` using the existing FastAPI/Pydantic validation representation.

An `active` Definition may be updated. An `archived` Definition may not be updated and returns `409` with detail `"Assessment Definition is archived"`.

Successful update returns `200 OK` and the complete management representation. Update is atomic; a failed update leaves the existing resource unchanged.

### ARCHIVE

```http
POST /api/v1/teacher-spaces/{teacher_space_id}/activities/{activity_id}/assessment-definition/archive
```

Request body: none.

A `active` Definition transitions atomically to `archived`:

```text
ACTIVE → ARCHIVED
```

Successful archive returns `200 OK` and the complete management representation with `status = "archived"`.

Repeated archive of an already `archived` Definition is a lifecycle conflict and returns `409` with detail `"Assessment Definition is already archived"`. It is not silently idempotent and does not mutate the resource.

There is no reactivation (`ARCHIVED → ACTIVE`) and no delete operation.

## Lifecycle Summary

| Operation | ACTIVE | ARCHIVED |
|---|---|---|
| READ | allowed | allowed |
| CREATE | allowed when none exists | not applicable; duplicate remains conflict |
| UPDATE | allowed | `409 "Assessment Definition is archived"` |
| ARCHIVE | `ACTIVE → ARCHIVED` | `409 "Assessment Definition is already archived"` |
| DELETE | unsupported | unsupported |
| Reactivate | unsupported | unsupported |

## Authorization and Scope

Authorization uses the existing Teacher Space boundary. It is evaluated by application orchestration, never by the HTTP controller and never by Assessment domain logic. The chain is:

```text
Authenticated Teacher
    ↓
Teacher Space ownership
    ↓
Activity belongs to Teacher Space
    ↓
AssessmentDefinition belongs to Activity
```

Required orchestration for every operation:

1. Resolve the Teacher Space by `teacher_space_id` through `TeacherSpaceService.get_by_id`.
2. Require the resolved Teacher Space's `owner_user_id` to equal the authenticated teacher's identity.
3. Ask Education's existing `ActivityTeacherSpaceScopeQuery.resolve_activity_scope(activity_id, teacher_space_id)`:
   - `IN_SCOPE` → continue.
   - `OUTSIDE_SCOPE` → authorization denied.
   - `NOT_FOUND` → the Activity does not exist.
4. Only after both checks allow it, perform the AssessmentDefinition operation through the existing Assessment application boundary.
5. Resolve the Definition for the Activity through Assessment-owned data. A Definition that does not belong to the requested Activity is never returned or mutated.

The existing `TeacherAssessmentDefinitionService` remains the Assessment Definition orchestration boundary. No new permission name, RBAC model, or cross-context private persistence access is introduced.

### Scope behavior

| Condition | Result |
|---|---|
| Missing/invalid session | `401` |
| Teacher Space does not exist | `404` |
| Authenticated teacher does not own the Teacher Space | `403` |
| Activity does not exist | `404` |
| Activity exists but is outside the Teacher Space | `403` |
| Activity is in scope but has no AssessmentDefinition | `404` |

### Mutation request protection

The mutation endpoints (`POST`, `PATCH`, `POST .../archive`) require the existing trusted-origin check:

```text
POST    CREATE
PATCH   UPDATE
POST    ../archive
```

A failed trusted-origin check returns `403` with detail `"Untrusted request origin"`.

The read endpoint (`GET`) is an authenticated read and does not require trusted-origin protection.

## Validation

The contract uses the repository's existing validation conventions:

- Route UUID parameters use FastAPI `UUID` path type; malformed UUIDs are `422`.
- Request fields are validated by Pydantic. Unknown fields are rejected (`extra = "forbid"`).
- `instructions` accepts a string or null.
- There is no maximum length, no trimming, and no blank-to-null normalization in the current domain model. The contract must not add these without an approved ADR amendment.
- PATCH with no mutable field is invalid (`422`).

The AssessmentDefinition domain remains authoritative for lifecycle and immutability invariants.

## Duplicate Creation and Uniqueness

The cardinality invariant is:

```text
one Activity → at most one AssessmentDefinition
```

The existing persistence already enforces this with the unique constraint:

```text
uq_assessment_definitions_activity
```

A duplicate CREATE returns `409` with detail `"Assessment Definition already exists"`. The existing Definition remains unchanged.

The implementation must preserve the invariant under concurrent CREATE requests. Concurrent requests for the same Activity must not produce two Definitions. The existing unique constraint and the existing repository `add` behavior are the approved mechanism; no migration is introduced by this milestone.

For concurrency, exactly one concurrent CREATE may succeed; every other concurrent CREATE must surface the duplicate conflict. The contract does not require idempotency keys or client-supplied Definition identifiers.

## AssessmentAttempt Interaction After Archival

The consequence of archiving a Definition is already established by ADR-0008 and is not reopened by this contract:

```text
ARCHIVED Definition
    ├── new Attempt creation → forbidden
    ├── existing DRAFT Attempt → remains editable and submittable
    ├── existing SUBMITTED Attempt → unchanged
    ├── existing REVIEWED Attempt → unchanged
    └── existing AssessmentResult → unchanged
```

Archival prevents the creation of new Attempts only. It does not delete, mutate, freeze, cancel, or submit existing Attempts. The management contract does not define any additional Attempt lifecycle behavior.

## Error Model

The API uses the repository's existing HTTP error representation: FastAPI `HTTPException` with a string `detail`, producing the standard body:

```json
{
  "detail": "<message>"
}
```

Validation failures use the existing FastAPI/Pydantic representation (the standard `422` `detail` array). This contract introduces no semantic error-code envelope and no second error model.

### Normative status mapping

| HTTP | Condition | `detail` |
|---|---:|---|
| `401` | Missing/invalid session | `"Authentication required"` |
| `403` | Mutation without trusted origin | `"Untrusted request origin"` |
| `403` | Teacher does not own the Teacher Space | `"Assessment access denied"` |
| `403` | Activity exists but outside the Teacher Space | `"Assessment access denied"` |
| `404` | Teacher Space does not exist | `"Teacher Space not found"` |
| `404` | Activity does not exist | `"Activity not found"` |
| `404` | Definition missing for the Activity | `"Assessment Definition not found"` |
| `409` | Duplicate CREATE | `"Assessment Definition already exists"` |
| `409` | UPDATE on ARCHIVED Definition | `"Assessment Definition is archived"` |
| `409` | ARCHIVE on ARCHIVED Definition | `"Assessment Definition is already archived"` |
| `422` | Malformed DTO, unknown field, invalid UUID, PATCH without mutable field | FastAPI/Pydantic validation `detail` |
| `500` | Unexpected failure or invariant violation | `"Internal Server Error"` |

Only the statuses above are normative. The contract does not use `400`.

## Atomicity and Transaction

CREATE, UPDATE, and ARCHIVE are atomic.

The operations use the existing request-scoped SQLAlchemy transaction:

```text
HTTP request
→ request-scoped Session (one active transaction)
→ Teacher Space authorization
→ Education Activity scope resolution
→ Assessment Definition operation
→ success: request-scoped transaction owner commits
→ exception: request-scoped transaction owner rolls back
```

Rules:

- AssessmentDefinition management joins the active request-scoped transaction.
- The request-scoped transaction owns commit and rollback. HTTP controllers, application services, and domain entities must not commit or roll back.
- No new transaction manager, nested transaction boundary, or independent transaction abstraction is introduced.
- The existing repository duplicate-creation protection remains the mechanism used to preserve the unique `activity_id` invariant.

Required invariants:

```text
CREATE failure     → no partial Definition remains
UPDATE failure     → existing Definition remains unchanged
ARCHIVE failure    → Definition remains ACTIVE
```

## Frontend and Projection Boundary

This milestone defines no frontend behavior and no Teacher Activity projection change.

ADR-0013 remains authoritative for the Teacher Activity entry-signal projection: `assessment_definition_id: UUID | null`. The management API returns the complete Definition resource and does not replace or expand that projection.

## Tests Required for Implementation

The subsequent implementation milestone must provide tests for the following behavior.

### READ

- Teacher can read the Definition for an owned Activity.
- The complete normalized representation is returned with exact fields and lowercase status.
- An `archived` Definition remains readable.
- Missing Definition returns `404 "Assessment Definition not found"`.
- Unknown Teacher Space returns `404`.
- Activity outside the Teacher Space returns `403`.
- Cross-Teacher-Space Definition is never exposed.
- Authenticated read works without trusted origin.

### CREATE

- Valid CREATE returns `201` and an `active` Definition.
- `activity_id` comes from the route, not the request body.
- Request with `activity_id` in the body is rejected (`422`).
- Duplicate CREATE returns `409` and leaves the existing Definition unchanged.
- Unauthorized Teacher returns `403`.
- Activity outside the Teacher Space returns `403`.
- Unknown Activity returns `404`.
- Malformed request body is rejected (`422`).
- Failed CREATE is atomic and leaves no Definition.
- Concurrent CREATE for the same Activity preserves the unique cardinality invariant.

### UPDATE

- An `active` Definition can update `instructions`.
- `instructions: null` clears instructions.
- `id` and `activity_id` cannot be changed.
- An `archived` Definition returns `409` and is not updated.
- Unauthorized Teacher returns `403`.
- Unknown Activity or Definition returns `404`.
- PATCH without a mutable field returns `422`.
- Failed UPDATE leaves the resource unchanged.
- No partial state is persisted on UPDATE failure.

### ARCHIVE

- An `active` Definition transitions to `archived`.
- An `archived` Definition remains readable.
- Repeated archive returns `409` deterministically.
- Unauthorized archive returns `403`.
- Failed archive leaves the Definition `active`.
- ARCHIVE is atomic.

### Attempt Interaction

- Archival forbids new Attempt creation for the Definition.
- An existing DRAFT remains editable and submittable after archival.
- Existing SUBMITTED and REVIEWED Attempts and Results are unchanged.

## Non-Goals

This contract does not implement or authorize frontend code, backend controllers, DTO classes, repositories, schema changes, migrations, or runtime behavior.

It does not define:

- reactivation or restoration;
- deletion or soft-deletion;
- additional lifecycle states;
- additional AssessmentDefinition fields;
- `title`, `description`, `configuration`, timestamps, audit metadata, or revision data;
- a separate `/assessment-definitions/{id}` resource;
- AssessmentResult, AssessmentAttempt, or Student Assessment changes;
- Teacher Assessment Review changes (ADR-0011 / ADR-0012);
- new permission names or RBAC;
- cross-context private persistence access;
- Teacher Activity projection changes;
- a new error envelope.

## Alternatives

### Definition-ID-scoped management routes

Not selected. The resource is bound to exactly one Activity and the Teacher Space + Activity scope is already the approved authorization boundary. An ID-scoped route would require the client to resolve the Definition identifier first and would duplicate scope discovery.

### Dedicated entry-signal lookup endpoint

Rejected by ADR-0013 and remains rejected. The Teacher Activity projection already exposes `assessment_definition_id`.

### Separate read and write route namespaces

Not selected. One Activity-scoped resource namespace keeps READ, CREATE, UPDATE, and ARCHIVE coherent and mirrors the existing Teacher assessment namespace style.

### Idempotent repeated archive

Rejected. The existing domain raises an immutable-transition error on repeated archive, so the contract maps it to `409` rather than inventing idempotent success.

### Blank normalization or maximum length on `instructions`

Rejected. The current domain model has neither rule. Adding either would require a separate architectural decision and an ADR amendment.

## Consequences

- Teacher AssessmentDefinition Management is a single Activity-scoped resource API.
- The resource representation matches the domain exactly (four fields only).
- Teacher Space ownership and Education Activity scope remain the authorization boundary.
- ARCHIVED Definitions remain readable and immutable.
- Archival preserves the ADR-0008 Attempt behavior already approved.
- Duplicate and concurrent creation is protected by the existing unique constraint.
- The error model matches the repository's existing `{"detail": string}` convention and Pydantic validation envelope.
- No production, frontend, database, migration, or runtime behavior is changed by this contract milestone.

## Implementation Rule

Any implementation that requires a new field, a new lifecycle state, reactivation, deletion, an additional resource route, a new error envelope, or a new authorization model must stop and obtain an explicit ADR amendment before proceeding.

No implementation milestone may silently reinterpret this contract.
