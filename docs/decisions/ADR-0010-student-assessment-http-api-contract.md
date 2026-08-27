# ADR-0010 — Student Assessment HTTP API Contract

- **Status:** Accepted
- **Date:** 2026-08-27
- **Issue:** EDU-065 / #129
- **Decision:** Define the minimal authenticated Student Assessment HTTP API for DRAFT creation, full submission replacement, submit, and ownership-scoped aggregate detail before API implementation.

## Context

ADR-0006 defines the Assessment lifecycle and ownership boundaries. ADR-0007 defines the complete
AssessmentResult. ADR-0008 defines nullable plain-text submission, DRAFT mutation, meaningful submit
validation, aggregate detail, and current versus historical Student authorization. ADR-0009 defines
the Student UI contract and requires a separate Student Assessment API decision and implementation
before UI implementation.

EDU-063 implements the internal Assessment and Student Space application capabilities but exposes no
public HTTP API. Existing public APIs use `/api/v1`, cookie-authenticated identity, Pydantic DTOs,
standard HTTP errors, trusted-origin protection for state changes, and request-scoped SQLAlchemy
sessions.

The exact Student Assessment routes, DTOs, status codes, error disclosure, retry semantics, and HTTP to
application mapping must be fixed before exposing those capabilities.

## Decision

### API prefix and routes

The canonical API prefix is:

```text
/api/v1/student
```

The complete endpoint set for this milestone is:

```text
POST /api/v1/student/activities/{activity_id}/assessment-definitions/{definition_id}/attempts
PUT  /api/v1/student/assessment-attempts/{attempt_id}
POST /api/v1/student/assessment-attempts/{attempt_id}/submit
GET  /api/v1/student/assessment-attempts/{attempt_id}
```

No collection, history, search, latest, current, final, or best-Attempt endpoint is introduced.

Create carries Activity and Definition identifiers in the route so Student Space can enforce the
current Activity/Enrollment boundary and Assessment can verify Definition scope. Every subsequent
operation is addressed only by the known Attempt identifier. The HTTP client does not provide Activity,
Definition, Course, enrollment, or Student identifiers for Replace, Submit, or Detail.

### Authentication and request protection

The authenticated Student identity comes exclusively from the existing session cookie and
`get_current_identity` dependency. The API never accepts `student_id` in a path, query, header, or
request body.

All mutation endpoints use the existing trusted-origin protection for cookie-authenticated state
changes:

```text
POST Create
PUT Replace
POST Submit
```

GET Detail remains an authenticated read and does not require trusted-origin mutation protection.

No new permission name, token model, or authentication mechanism is introduced.

### Create DRAFT

```text
POST /api/v1/student/activities/{activity_id}/assessment-definitions/{definition_id}/attempts
```

The JSON request object has one optional field:

```json
{
  "submission": "initial text"
}
```

The empty object is valid:

```json
{}
```

An omitted `submission` is equivalent to:

```json
{
  "submission": null
}
```

The field accepts only string or null. ADR-0008 normalization applies before persistence: empty and
whitespace-only strings become null. Create succeeds only for an ACTIVE Definition inside the supplied
Activity scope and when current published-Activity and enrollment authorization succeeds.

A successful Create returns `201 Created` and the complete Attempt aggregate. Create is
non-idempotent: each separately confirmed successful POST creates a new DRAFT with a new server-owned
Attempt identifier.

### Replace or clear DRAFT submission

```text
PUT /api/v1/student/assessment-attempts/{attempt_id}
```

The request object contains the required nullable replacement field:

```json
{
  "submission": "replacement text"
}
```

or:

```json
{
  "submission": null
}
```

The operation fully replaces the existing DRAFT submission. Empty and whitespace-only strings
normalize to null. An omitted field is not a valid Replace DTO because PUT represents an explicit full
replacement of the submission value.

A successful Replace returns `200 OK` and the complete Attempt aggregate. Repeating the same PUT
payload against the same mutable DRAFT is safe and returns the same confirmed submission state. It
requires no idempotency key or idempotency persistence. PUT cannot mutate a SUBMITTED or REVIEWED
Attempt.

### Submit DRAFT

```text
POST /api/v1/student/assessment-attempts/{attempt_id}/submit
```

Submit has no domain request payload. It applies ADR-0008 meaningful-submission validation to the
persisted DRAFT. A successful transition returns `200 OK` and the complete SUBMITTED Attempt aggregate.

Submit is not repeat-idempotent. A request for an already SUBMITTED or REVIEWED Attempt returns
`409 Conflict` and does not mutate the Attempt.

### Aggregate detail

```text
GET /api/v1/student/assessment-attempts/{attempt_id}
```

A successful read returns `200 OK` and one stable aggregate shape:

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "assessment_definition_id": "00000000-0000-0000-0000-000000000000",
  "submission": null,
  "status": "draft",
  "result": null
}
```

The top-level fields are exactly:

```text
id
assessment_definition_id
submission
status
result
```

`status` uses the existing lowercase values:

```text
draft
submitted
reviewed
```

`result` is always present. Its lifecycle representation is:

```text
DRAFT     → result = null
SUBMITTED → result = null
REVIEWED  → result = complete AssessmentResult
```

The complete Result object has exactly the ADR-0007 fields:

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "attempt_id": "00000000-0000-0000-0000-000000000000",
  "score": 8,
  "max_score": 10,
  "feedback": null
}
```

`feedback` remains present and nullable. The response does not add Student, Activity, Course,
enrollment, timestamps, audit metadata, pass/fail, Grade, or Progress fields.

### Authorization and disclosure

Student Space remains the application orchestrator. The HTTP controller supplies authenticated
identity and route/request data to Student Space application operations; it does not evaluate domain or
authorization rules itself.

#### Create

Create authorization requires:

```text
published Activity identified by activity_id
+
current ENROLLED status for that Activity's Course
+
ACTIVE AssessmentDefinition identified by definition_id
+
Definition.activity_id = activity_id
```

An unknown Activity, unknown Definition, or Activity/Definition scope mismatch is represented as not
found. A valid scope for which the authenticated Student lacks current mutation access is forbidden.
An ARCHIVED Definition is a valid existing resource in an invalid creation state and returns conflict.

#### Replace and Submit

For an Attempt-ID mutation, the application boundary resolves the Attempt, its Definition, and the
Definition's opaque Activity identifier from Assessment-owned data. It then enforces:

```text
Attempt belongs to authenticated Student
+
Attempt/Definition/Activity scope binding is valid
+
Activity is currently published
+
Student is currently ENROLLED in the Activity's Course
+
Attempt is DRAFT
```

Unknown Attempt, wrong Student owner, or invalid Assessment scope binding is returned as `404`. If the
owned, correctly bound DRAFT exists but current Activity publication or enrollment denies mutation,
the response is `403`.

#### Detail

The application resolves ownership and Assessment scope from the Attempt identifier. DRAFT detail uses
the current published-Activity and enrollment authorization required by ADR-0008. SUBMITTED and
REVIEWED detail is historical and requires only:

```text
Attempt ownership
+
valid Assessment scope binding
```

Historical detail does not require current Course publication, Activity visibility, or enrollment.
Unknown Attempt, wrong Student owner, or scope mismatch returns `404` without disclosing which condition
failed.

Assessment evaluates Attempt/Definition/Result relationships from Assessment-owned persistence only.
It does not access Education or Learning private persistence. Student Space accesses Education
publication and Learning enrollment only through their existing application/public boundaries.
`ActivityProgress` is not an authorization mechanism.

### HTTP error mapping

The API uses the following normative status mapping:

| Condition | HTTP status |
|---|---:|
| Missing/invalid session | `401 Unauthorized` |
| Unknown Attempt | `404 Not Found` |
| Wrong Student owner | `404 Not Found` |
| Assessment scope mismatch | `404 Not Found` |
| Unknown/unavailable Activity or Definition scope | `404 Not Found` |
| Owned DRAFT mutation denied by current publication/enrollment | `403 Forbidden` |
| Malformed request DTO or invalid field type | `422 Unprocessable Entity` |
| Empty/blank normalized submission on Submit | `422 Unprocessable Entity` |
| Replace or Submit for SUBMITTED/REVIEWED Attempt | `409 Conflict` |
| Create for ARCHIVED Definition | `409 Conflict` |
| REVIEWED Attempt missing its required Result | `500 Internal Server Error` |
| Unexpected server failure | `500 Internal Server Error` |

The `403`, `404`, `422`, and unexpected/5xx distinctions support the ADR-0009 UI error states. The API
must not turn denied or failed operations into successful empty responses.

A REVIEWED Attempt without a Result is an invariant violation. A direct Detail request returns `500`;
it must not fabricate a Result, return a valid `200` aggregate with `result = null`, or introduce a
partial Attempt/error DTO. Consistent with amended ADR-0009, direct navigation may show a retryable
Assessment error, while an immutable submission already present in client cache may remain visible.

### Mutation retry semantics

#### Create

Create is non-idempotent. Every separately confirmed successful POST creates another DRAFT. The API
does not add an idempotency key, client-generated Attempt identifier, deduplication key, or Attempt
collection for recovery.

After an ambiguous transport/server failure, the client must not automatically retry Create because a
first request may have committed even if its response was not received. Before issuing another Create,
the client must determine the outcome through another separately approved mechanism. This minimal
contract does not define or add a discovery mechanism for an Attempt whose identifier was not received.

#### Replace

PUT Replace is repeat-safe while the Attempt remains DRAFT. Retrying the identical replacement payload
sets the same normalized submission value and requires no idempotency storage. If the Attempt has since
become SUBMITTED or REVIEWED, the retry returns `409` and does not modify it.

#### Submit

Repeated Submit for an already SUBMITTED or REVIEWED Attempt returns `409`. After an ambiguous Submit
failure, the client performs GET Detail before deciding whether another Submit is appropriate:

```text
GET returns SUBMITTED or REVIEWED → do not repeat Submit
GET returns DRAFT                 → no successful transition is inferred
```

The API defines no automatic mutation retry policy.

### Transaction boundary

Mutations use the existing request-scoped SQLAlchemy transaction mechanism. One DB Session is shared by
the Student Space authorization composition and Assessment mutation repositories for the request.

```text
HTTP request
→ get_db Session
→ Student authorization and Assessment application operation
→ success: get_db commit
→ exception: get_db rollback
```

The HTTP controller and domain entities do not commit or roll back. No new transaction manager,
application transaction abstraction, distributed transaction, or cross-context persistence ownership
is introduced.

### API to application boundary

The HTTP layer exposes exactly four Student application use cases:

```text
create DRAFT
replace/clear DRAFT submission
submit DRAFT
read owned Attempt aggregate detail
```

Controllers are responsible only for:

- reading route and validated request data;
- obtaining authenticated Identity;
- invoking the composed Student application operation;
- serializing the application result;
- mapping approved application/domain errors to the normative HTTP statuses.

Submission normalization, lifecycle rules, ownership, current mutation authorization, historical read
authorization, and Assessment scope binding remain in domain/application layers. Controllers must not
query repositories or private persistence.

## Invariants

```text
API prefix = /api/v1/student

Create route
→ activity_id + definition_id
→ optional submission field
→ 201 + complete aggregate
→ non-idempotent

Replace route
→ attempt_id only
→ required nullable submission
→ full replacement
→ repeat-safe PUT
→ 200 + complete aggregate

Submit route
→ attempt_id only
→ meaningful persisted submission
→ first valid transition returns 200 aggregate
→ repeated transition returns 409

Detail route
→ attempt_id only
→ 200 stable aggregate
→ result key always present
→ DRAFT/SUBMITTED result is null
→ REVIEWED result is complete
→ REVIEWED without Result returns 500, never valid 200

unknown/wrong owner/scope mismatch → 404
owned DRAFT current mutation denial → 403
malformed/empty submit validation → 422
invalid lifecycle/Create on archived → 409

Student identity comes from session cookie
student_id is never client-controlled

one request-scoped Session
→ authorization + mutation
→ commit or rollback through get_db

no Attempt collection/history API
no ActivityProgress authorization
no cross-context private persistence access
```

## Alternatives

### Fully nested routes for every operation

Rejected. Only Create carries Activity and Definition scope; subsequent operations use the known
Attempt identifier.

### Definition-only Create route

Rejected. Create explicitly carries Activity and Definition identifiers for current scope
authorization.

### PATCH or action endpoint for replacement

Rejected. Full replacement uses repeat-safe PUT with a required nullable submission field.

### Omit `result` when absent

Rejected. The aggregate has a stable `result` key containing null or a complete Result.

### Return 403 for wrong owner or scope mismatch

Rejected. Unknown Attempt, wrong owner, and invalid Assessment scope are concealed as 404.

### Return a successful inconsistent REVIEWED aggregate

Rejected. Missing required Result is a server invariant violation and returns 500 without a new error
DTO.

### Idempotent or automatically retried Create

Rejected. Create is non-idempotent and this milestone adds no idempotency infrastructure.

### Idempotent repeated Submit

Rejected. Submit of an already SUBMITTED or REVIEWED Attempt returns 409; ambiguous outcomes are
checked with Detail before any manual retry decision.

### New application transaction abstraction

Rejected. The existing request-scoped `get_db` Session owns commit and rollback.

### Attempt collection or history endpoint

Rejected. The API is detail-only by known Attempt identifier.

## Consequences

- Create routes carry enough explicit context for current Activity/Definition scope validation.
- Dedicated Attempt routes remain stable after creation and support ADR-0009 known-ID navigation.
- Full mutation responses let the UI update confirmed Attempt state without an immediate extra GET.
- Stable aggregate and nested Result shapes avoid status-dependent response schemas.
- Wrong ownership and scope remain concealed while an owned DRAFT's current-access denial can be shown
  as forbidden.
- Non-idempotent Create cannot be automatically retried after an ambiguous outcome and has no recovery
  discovery operation in this minimal API.
- Repeat-safe PUT supports explicit Save without idempotency persistence.
- Strict repeated-Submit conflict requires GET after an ambiguous Submit result.
- A missing REVIEWED Result remains a server error; cached UI state is optional and no partial error
  payload is added.
- Existing request-scoped transaction and bounded-context ownership are preserved.
- Student Assessment API implementation must precede the UI implementation required by ADR-0009.

## Sequencing

```text
ADR-0009
→ ADR-0010 / EDU-065 Student Assessment API decision/contract
→ Student Assessment API implementation
→ Student Assessment UI implementation
```

## Non-goals

This decision does not implement or authorize:

- API controllers, routes, or DTO classes;
- frontend code;
- migrations or persistence changes;
- new domain fields or lifecycle states;
- AssessmentResult changes;
- ActivityProgress changes or authorization;
- Education or Learning private persistence access;
- Attempt collection/history, ordering, or pagination;
- current, final, or best Attempt semantics;
- idempotency storage, client-generated Attempt IDs, or automatic mutation retry;
- new permission names.
