# ADR-0014 — Teacher AssessmentDefinition Management Contract

- **Status:** Proposed
- **Date:** 2026-08-28
- **Issue:** EDU-075
- **Decision:** Define the normative Teacher AssessmentDefinition Management HTTP/application contract for retrieving, creating, updating, and archiving the AssessmentDefinition associated with an Activity inside an authorized Teacher Space.

## Context

ADR-0006 establishes Assessment as an independent bounded context. Education owns `Activity`; Assessment owns `AssessmentDefinition`, `AssessmentAttempt`, and `AssessmentResult`. An Activity has at most one AssessmentDefinition.

ADR-0013 defines `assessment_definition_id: UUID | null` on the Teacher Activity projection as an entry signal. It intentionally rejects a redundant lookup endpoint whose purpose is only to discover that relationship or obtain its identifier.

ADR-0013 Amendment 001 clarifies that this rejection does not prohibit a separately defined Teacher AssessmentDefinition Management resource READ operation. The management API returns the complete AssessmentDefinition resource and serves a different responsibility from the Activity projection entry signal.

## Decision

Teacher AssessmentDefinition Management is an Assessment-owned management capability exposed through the existing Teacher Space authorization orchestration.

The canonical resource is Activity-scoped:

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

No reactivation or delete operation is introduced.

## Resource Ownership

AssessmentDefinition remains owned by Assessment.

Education owns Activity. Teacher Space provides authorized application orchestration. No bounded context may access another bounded context's private persistence.

Teacher authorization follows the existing orchestration model:

```text
Teacher
  |
  v
Teacher Space
  ├── verifies teacher owns teacher_space
  ├── verifies Activity belongs to teacher_space
  |
  v
Assessment
  └── performs AssessmentDefinition operation
```

`teacher_space_id` is authorization context, not AssessmentDefinition domain state. AssessmentDefinition does not store `teacher_id` or `teacher_space_id`.

## Lifecycle

AssessmentDefinition has exactly two MVP states:

```text
ACTIVE → ARCHIVED
```

Creation produces `ACTIVE`.

`ACTIVE` definitions are editable by an authorized Teacher.

`ARCHIVED` definitions are immutable and remain readable for historical integrity.

MVP provides no reactivation/restoration and no physical delete operation.

## GET

### Route

```http
GET /api/v1/teacher-spaces/{teacher_space_id}/activities/{activity_id}/assessment-definition
```

### Behavior

The application must:

1. authenticate the Teacher;
2. validate access to `teacher_space_id`;
3. validate that `activity_id` belongs to that Teacher Space through the existing Education public/application boundary;
4. resolve the AssessmentDefinition associated with the Activity;
5. return the complete AssessmentDefinition management representation.

If the Activity has no AssessmentDefinition, the operation returns the existing not-found error representation with semantic error `ASSESSMENT_DEFINITION_NOT_FOUND`.

An archived AssessmentDefinition remains readable.

The operation must not expose a Definition from another Teacher Space or Activity.

## Management Representation

The response represents the complete AssessmentDefinition resource required by the existing domain model and subsequent implementation contract.

The conceptual representation is:

```json
{
  "id": "uuid",
  "activity_id": "uuid",
  "status": "ACTIVE",
  "title": "string",
  "description": "string | null",
  "instructions": "string | null",
  "configuration": {},
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

These fields are illustrative where the current AssessmentDefinition model does not already define them. An implementation must not invent unsupported domain fields. The final DTO must be derived from the existing AssessmentDefinition model and approved application contract.

Server-owned fields include identity, Activity relationship, lifecycle status, ownership context, and timestamps.

## POST

### Route

```http
POST /api/v1/teacher-spaces/{teacher_space_id}/activities/{activity_id}/assessment-definition
```

### Behavior

Creates the Activity's AssessmentDefinition.

The application validates:

1. Teacher authorization;
2. Activity membership in the Teacher Space;
3. that no AssessmentDefinition already exists for the Activity;
4. request/application validation;
5. AssessmentDefinition domain invariants.

Creation is atomic.

Successful creation returns:

```text
201 Created
```

with the complete AssessmentDefinition management representation and `status = ACTIVE`.

### Duplicate Creation

Because Activity → AssessmentDefinition is `1 → 0..1`, an Activity cannot have two definitions.

A second creation attempt returns the existing conflict representation with semantic error:

```text
ASSESSMENT_DEFINITION_ALREADY_EXISTS
```

The existing Definition remains unchanged.

## PATCH

### Route

```http
PATCH /api/v1/teacher-spaces/{teacher_space_id}/activities/{activity_id}/assessment-definition
```

### Behavior

PATCH is a partial update of mutable AssessmentDefinition fields.

The application validates:

1. Teacher authorization;
2. Activity membership in the Teacher Space;
3. AssessmentDefinition existence;
4. current lifecycle state;
5. request/application validation;
6. domain invariants.

The following are immutable through PATCH:

```text
id
activity_id
teacher ownership
teacher_space authorization context
status
created_at
updated_at
```

An archived Definition cannot be updated.

Semantic conflict:

```text
ASSESSMENT_DEFINITION_ARCHIVED
```

PATCH is atomic. If validation or persistence fails, no subset of the update may remain persisted.

## Archive

### Route

```http
POST /api/v1/teacher-spaces/{teacher_space_id}/activities/{activity_id}/assessment-definition/archive
```

### Behavior

The only lifecycle transition introduced is:

```text
ACTIVE → ARCHIVED
```

Archiving is atomic.

An already archived Definition returns the existing conflict representation with semantic error:

```text
ASSESSMENT_DEFINITION_ALREADY_ARCHIVED
```

No reactivation and no delete endpoint are introduced.

## Archived Resource Rules

| Operation | ACTIVE | ARCHIVED |
|---|---|---|
| GET | allowed | allowed |
| POST create | allowed when none exists | not applicable to existing resource; duplicate remains conflict |
| PATCH | allowed | `409 ASSESSMENT_DEFINITION_ARCHIVED` |
| ARCHIVE | `ACTIVE → ARCHIVED` | `409 ASSESSMENT_DEFINITION_ALREADY_ARCHIVED` |
| DELETE | unsupported | unsupported |
| Reactivate | unsupported | unsupported |

## Request Rules

Clients provide only mutable/create fields supported by the AssessmentDefinition model.

Clients must not provide authoritative values for:

```text
id
activity_id
teacher_space_id
teacher_id
status
created_at
updated_at
```

The server derives scope and lifecycle state from route/application context and domain rules.

The contract does not introduce a new AssessmentDefinition field merely because it would be convenient for the API.

## Validation Boundary

Application validation handles request shape, required fields, immutable-field protection, and operation-specific constraints.

The AssessmentDefinition domain remains authoritative for domain invariants and lifecycle semantics.

The API must not duplicate domain rules in a way that creates conflicting sources of truth.

## Error Model

The API uses the repository's existing normalized error model and error envelope.

Semantic errors used by this contract are:

```text
ASSESSMENT_DEFINITION_NOT_FOUND
ASSESSMENT_DEFINITION_ALREADY_EXISTS
ASSESSMENT_DEFINITION_ARCHIVED
ASSESSMENT_DEFINITION_ALREADY_ARCHIVED
VALIDATION_ERROR
```

HTTP status semantics follow existing platform conventions:

```text
400 → malformed/invalid request when the existing error model classifies it as 400
404 → resource unavailable within the authorized scope
409 → lifecycle or uniqueness conflict
422 → validation failure when the existing platform convention uses 422
500 → unexpected/invariant failure
```

The implementation must not introduce a second error envelope or invent authorization error semantics.

## Atomicity

CREATE, PATCH, and ARCHIVE are atomic operations.

Required invariants:

```text
CREATE failure
→ no partial Definition remains

PATCH failure
→ existing Definition remains unchanged

ARCHIVE failure
→ Definition remains ACTIVE
```

## Concurrency and Uniqueness

The Activity → AssessmentDefinition cardinality is at most one.

The implementation must preserve that invariant under concurrent creation attempts. A race must not result in two Definitions for one Activity. The application may rely on the existing persistence/domain mechanism appropriate to the repository, but the externally visible contract remains a single successful creation and a conflict for subsequent creation.

No new concurrency architecture is defined by this ADR beyond preservation of the existing cardinality invariant.

## Projection Boundary

ADR-0013 remains responsible for the Teacher Activity entry signal:

```text
assessment_definition_id: UUID | null
```

The projection is used to decide whether the Assessment Review entry point is available.

ADR-0014's management API is used after entering the management flow and returns the complete Definition resource.

The management API does not replace the projection and does not add Definition internals to the Activity projection.

## Review Boundary

Teacher AssessmentDefinition Management is distinct from Teacher Assessment Review.

Teacher Assessment Review remains governed by ADR-0011 and ADR-0012, including Attempt review/correction semantics and routes.

`assessment_definition_id` is not added to the Review route namespace merely because it exists as an entry signal.

## Frontend Boundary

EDU-075 does not implement frontend behavior.

Teacher Activity UI remains responsible for the Assessment Review entry signal according to ADR-0013/ADR-0012.

Assessment frontend management UI, if later required, must consume this approved API contract through the existing frontend API boundary.

## Tests Required for Implementation

The subsequent implementation milestone must test:

### GET

- existing Definition is returned;
- complete response representation is returned;
- missing Definition returns `ASSESSMENT_DEFINITION_NOT_FOUND`;
- Activity outside Teacher Space is rejected;
- cross-Teacher-Space Definition cannot be exposed;
- archived Definition remains readable.

### POST

- creates a Definition;
- returns 201;
- new Definition is ACTIVE;
- duplicate creation returns conflict;
- duplicate creation leaves the existing Definition unchanged;
- invalid request is rejected;
- out-of-scope Activity is rejected;
- concurrent creation preserves the 0..1 invariant;
- failed creation is atomic.

### PATCH

- mutable fields can be updated;
- partial update works;
- immutable fields cannot be changed;
- invalid update is rejected;
- archived Definition cannot be updated;
- failed update leaves the resource unchanged;
- out-of-scope Activity is rejected;
- failed update is atomic.

### ARCHIVE

- ACTIVE transitions to ARCHIVED;
- archived Definition remains readable;
- already archived Definition returns conflict;
- failed archive leaves Definition ACTIVE;
- out-of-scope Activity is rejected;
- archive is atomic.

### Authorization

- authorized Teacher can manage an owned Teacher Space Activity;
- another Teacher's Activity is inaccessible;
- mismatched Teacher Space + Activity is rejected;
- mismatched Activity + AssessmentDefinition relationship is rejected.

## Non-Goals

This decision does not define or implement:

- Student Assessment APIs;
- Student Attempt APIs;
- Teacher Assessment Review behavior;
- AssessmentResult scoring semantics;
- frontend implementation;
- payment;
- notifications;
- analytics;
- AssessmentDefinition reactivation;
- AssessmentDefinition deletion;
- new lifecycle states;
- Activity ownership changes;
- Education persistence of AssessmentDefinition identity;
- a new Assessment identity lookup mechanism.

## Alternatives

### Definition-ID-only management route

Not selected as the canonical route. The Activity-scoped route keeps Teacher Space and Activity scope explicit and matches the domain relationship while avoiding an additional client-side scope discovery step.

### Dedicated lookup endpoint for entry-signal discovery

Rejected by ADR-0013 and remains rejected. The Teacher Activity projection already exposes the identity reference needed for entry decisions.

### Persist AssessmentDefinition ownership in Education

Rejected. AssessmentDefinition remains Assessment-owned, and cross-context composition uses explicit application/public boundaries.

## Consequences

- Teacher AssessmentDefinition Management has an explicit resource-level API separate from the Activity projection entry signal.
- The Activity remains the canonical management navigation boundary.
- Teacher Space remains the authorization boundary.
- Assessment retains ownership of AssessmentDefinition persistence and lifecycle.
- Archived definitions preserve historical integrity without introducing delete or reactivation.
- The contract can be implemented without changing the architecture defined by ADR-0013.

## Implementation Rule

Any implementation that requires a new lifecycle state, reactivation, deletion, a new authorization model, a new error envelope, persisted ownership duplication, or a different canonical route must stop and obtain an explicit ADR amendment before proceeding.

No implementation milestone may silently reinterpret this contract.
