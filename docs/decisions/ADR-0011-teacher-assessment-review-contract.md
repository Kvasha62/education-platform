# ADR-0011 — Teacher Assessment Review Contract

- **Status:** Accepted
- **Date:** 2026-08-28
- **Issue:** EDU-068
- **Decision:** Define the Teacher-facing Assessment Attempt review queue, Attempt detail, review command, correction command, DTOs, Teacher authorization, error mapping, transaction boundary, and frontend ownership before any Teacher Assessment Review backend/API implementation.

## Context

ADR-0006 defines Assessment as an independent bounded context and the complete Attempt lifecycle:

```text
DRAFT → SUBMITTED → REVIEWED
```

ADR-0007 defines the complete `AssessmentResult` semantics, integer scoring, optional normalized feedback, correction behavior, and the atomic `SUBMITTED → REVIEWED → exactly one Result` rule. ADR-0008 defines Student-facing plain-text submission and the Student authorization boundaries. ADR-0009 defines the Student Assessment UI contract and the Assessment frontend module. ADR-0010 defines the Student Assessment HTTP API and the request-scoped transaction boundary.

EDU-063 / EDU-064 implemented internal Student and Teacher Space assessment application capabilities, but no public Teacher Assessment Review HTTP API or Teacher Review UI exists. The existing Teacher Space application layer already defines Teacher Space ownership and Education Activity-scope orchestration for AssessmentDefinition and AssessmentResult operations. Those application capabilities are not yet exposed through a canonical public Teacher API contract or a Teacher Review UI contract.

The Teacher Review flow must be fixed before implementation because it introduces:

- the first Teacher collection of AssessmentAttempts;
- the `student_id` visibility rule;
- a `status` queue filter;
- deterministic UUID ordering and pagination;
- review and correction commands that return a complete Result;
- explicit resource/scope, authorization, lifecycle, validation, and invariant error distinctions;
- a transaction contract that joins the request-scoped transaction rather than opening a nested transaction.

## Decision

### 1. Teacher Assessment Review collection

The Teacher Assessment Review collection is an Activity-scoped collection of AssessmentAttempts that an authorized Teacher may review or later correct. It is defined here as an API and application contract only; no runtime implementation is authorized by this ADR.

**Scope identifiers.** Every Teacher Review route uses exactly two scope identifiers:

```text
teacher_space_id → Teacher Space ownership scope
activity_id      → Assessment/Activity scope binding
```

**Route parameters.** The HTTP contract uses only:

```text
teacher_space_id
activity_id
attempt_id (when addressing one Attempt)
```

The contract does **not** require or accept `course_id`, `section_id`, `unit_id`, or a separate `assessment_definition_id` in the Teacher Review path. `assessment_definition_id` is resolved by Assessment from the Attempt's Assessment-owned relationship and is never client-supplied for Teacher Review. The `teacher_space_id + activity_id` pair is the approved Teacher Space + Activity scope; hierarchy identifiers are not part of the Teacher Assessment Review namespace.

### 2. Teacher discovery

The collection exists only for Teacher discovery of actionable Attempts:

```text
SUBMITTED Attempts requiring review
REVIEWED Attempts requiring correction, or at minimum requiring durable discovery
```

The collection is therefore:

```text
membership = the Activity's SUBMITTED and REVIEWED AssessmentAttempts
```

`DRAFT` Attempts are **not** members of the Teacher Assessment Review collection. A Student-owned `DRAFT` is still mutable and is outside Teacher Review for this milestone.

### 3. Collection membership and `status` filter

The query parameter is:

```text
status: optional
```

Explicit semantics:

```text
status omitted    → return SUBMITTED and REVIEWED
status=submitted  → return only SUBMITTED
status=reviewed   → return only REVIEWED
```

The accepted `status` values are exactly `submitted` and `reviewed`, using the existing lowercase lifecycle value convention. Any other value is a malformed query and returns `422 Unprocessable Entity`. The value `draft` is not accepted because `DRAFT` is not a Teacher Review collection member.

The **default behavior** is inclusion of both `SUBMITTED` and `REVIEWED`. It must not default to only one status. This is required so REVIEWED Attempts remain durably discoverable for correction after they have been reviewed.

### 4. Deterministic ordering

The collection ordering is:

```text
ORDER BY assessment_attempt.id ASC
```

`id` is the server-owned AssessmentAttempt UUID. It is the sole ordering key. No timestamp ordering, submission ordering, score ordering, Student ordering, or database natural order is used. Filtering and Teacher authorization are applied before ordering and pagination.

### 5. Pagination

The collection is paginated and follows ADR-0003.

**Request semantics:**

```text
page:      integer, optional, default 1, minimum 1
page_size: integer, optional, default 20, minimum 1, maximum 100
```

- `page` is one-based. `page=1` is the first page. `page=0`, negative values, and non-integers are invalid and return `422`.
- `page_size` is the validated requested page size, not the number of returned items.
- `page` and `page_size` are always independent query parameters. Cursor parameters are not part of this contract.

**Response shape:**

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "has_next": false
}
```

- `has_next` is determined by requesting at most `page_size + 1` rows and returning only the first `page_size` items.
- `total`, `total_pages`, and equivalent count fields are not returned.
- An empty first page returns `200`, not `404`.
- A page beyond the available range returns `200` with empty `items`, the requested `page` value, and `has_next: false`.

### 6. Teacher-visible Student identity

The Teacher Review contract exposes the Student only as an opaque identifier:

```text
student_id: UUID
```

`student_id` is the Assessment-owned Student reference stored on the Attempt. The contract does **not** expose a Student name, email, profile, users identifier, or any other identity attribute, and it does **not** require or permit a Users lookup. Teacher Review must remain usable without any Education, Identity, or Users public lookup dependency.

`student_id` is presentation/discovery data. It is never an authorization input. Teacher authorization is determined only by Teacher Space ownership plus Activity scope binding.

### 7. Teacher authorization

Teacher Review authorization uses the approved boundary:

```text
Teacher Space ownership
        +
Education Activity scope binding
        ↓
Assessment Review operation
```

The normative orchestration is:

```text
Teacher
  │
  ▼
Teacher Space application
  ├── verifies authenticated teacher_id owns teacher_space_id
  │
  ├── asks Education whether activity_id belongs to teacher_space_id
  │
  ├── if either check is DENIED → AuthorizationError
  │
  └── if both checks are ALLOWED
          │
          ▼
      Assessment
          └── performs the activity/attempt/result operation
```

Rules:

- The authenticated Teacher identity comes from the existing session identity dependency. `teacher_id` is never accepted in a path, query, header, or body.
- Teacher Space ownership and Education Activity scope are evaluated by the application orchestration, not by the HTTP controller and not by Assessment domain logic.
- Assessment evaluates Attempt/Definition/Activity and Result relationships only from Assessment-owned data.
- Assessment does not access Education or Learning private persistence.
- Teacher Space and Education application boundaries do not access Assessment private persistence.
- No named review or correction permission is added.
- No cross-owner or global Teacher access is granted.
- No controller-level authorization or domain logic is permitted.

### 8. Canonical Teacher API namespace and routes

The canonical Teacher Assessment Review namespace is:

```text
/api/v1/teacher-spaces/{teacher_space_id}/activities/{activity_id}/assessment-attempts
```

The complete endpoint set for this milestone is:

```text
GET  /api/v1/teacher-spaces/{teacher_space_id}/activities/{activity_id}/assessment-attempts
GET  /api/v1/teacher-spaces/{teacher_space_id}/activities/{activity_id}/assessment-attempts/{attempt_id}
POST /api/v1/teacher-spaces/{teacher_space_id}/activities/{activity_id}/assessment-attempts/{attempt_id}/review
POST /api/v1/teacher-spaces/{teacher_space_id}/activities/{activity_id}/assessment-attempts/{attempt_id}/correction
```

- `GET` collection returns the paginated review queue.
- `GET` detail returns the complete Teacher Attempt read.
- `POST` review completes review by creating the single Result and transitioning the Attempt to `REVIEWED`.
- `POST` correction updates the existing Result.

No separate Teacher Assessment Result collection endpoint, correction history endpoint, recovery endpoint, or global Teacher Assessment dashboard endpoint is introduced.

### 9. Collection and detail DTOs

**Collection item.**

Each `items[]` entry is:

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "student_id": "00000000-0000-0000-0000-000000000000",
  "status": "submitted",
  "assessment_definition_id": "00000000-0000-0000-0000-000000000000",
  "activity_id": "00000000-0000-0000-0000-000000000000",
  "result": null
}
```

Field rules:

```text
id                      → AssessmentAttempt id; UUID; required
student_id              → opaque Assessment-owned Student reference; UUID; required
status                  → submitted | reviewed; required
assessment_definition_id→ AssessmentDefinition id resolved from the Attempt; UUID; required
activity_id             → AssessmentDefinition Activity reference; UUID; required
result                  → complete AssessmentResult when status=reviewed
                        → null when status=submitted
```

The collection item is a queue summary. It does not include the submission text.

**Detail.**

`GET` detail returns one object with the collection item fields plus the immutable submission:

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "student_id": "00000000-0000-0000-0000-000000000000",
  "status": "reviewed",
  "assessment_definition_id": "00000000-0000-0000-0000-000000000000",
  "activity_id": "00000000-0000-0000-0000-000000000000",
  "submission": "Student plain-text submission",
  "result": {
    "id": "00000000-0000-0000-0000-000000000000",
    "attempt_id": "00000000-0000-0000-0000-000000000000",
    "score": 8,
    "max_score": 10,
    "feedback": null
  }
}
```

Field rules:

```text
submission → string | null in the schema
           → normalized non-null string for every SUBMITTED/REVIEWED collection member
```

The successful `status` values in the Teacher Review contract are exactly:

```text
submitted
reviewed
```

The collection and detail never return `draft`. There is no Student name/email, Users identifier, Course/Enrollment/ActivityProgress field, audit timestamp, `assessed_at`, `assessed_by`, or correction history field.

**AssessmentResult DTO.**

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

`feedback` is always present and nullable. `max_score` is the immutable Result snapshot.

### 10. Review command contract

```text
POST /api/v1/teacher-spaces/{teacher_space_id}/activities/{activity_id}/assessment-attempts/{attempt_id}/review
```

Request object:

```json
{
  "score": 8,
  "max_score": 10,
  "feedback": "Look at the second example."
}
```

or:

```json
{
  "score": 8,
  "max_score": 10,
  "feedback": null
}
```

Field rules:

```text
score      → integer; required; 0 <= score <= max_score
max_score  → integer; required; max_score > 0
feedback   → string or null; optional; blank/whitespace-only normalized to null
```

Normalization of blank `feedback` to `null` is mandatory.

Preconditions:

```text
Teacher Space ownership ALLOWED
Activity scope binding ALLOWED
Attempt exists and belongs to the supplied Activity scope
Attempt.status = SUBMITTED
Attempt is not already REVIEWED
No AssessmentResult already exists for the Attempt
```

The operation is atomic:

```text
SUBMITTED Attempt
→ REVIEWED Attempt
→ exactly one AssessmentResult created with the supplied score/max_score/feedback
```

A successful review returns `200 OK` and the complete `AssessmentResult`. The response is the Result object only, not an Attempt aggregate and not a partial Result.

Review is a state-transition command and is intentionally not repeat-idempotent. Repeating review on an already `REVIEWED` Attempt returns `409 Conflict` and does not mutate the Attempt or Result.

### 11. Correction command contract

```text
POST /api/v1/teacher-spaces/{teacher_space_id}/activities/{activity_id}/assessment-attempts/{attempt_id}/correction
```

Request object:

```json
{
  "result_id": "00000000-0000-0000-0000-000000000000",
  "score": 9,
  "feedback": "Updated feedback."
}
```

Field rules:

```text
result_id → UUID; required; must match the single Result for this Attempt
score     → integer; required; 0 <= score <= max_score
feedback  → string or null; required; blank/whitespace-only normalized to null
```

Preconditions:

```text
Teacher Space ownership ALLOWED
Activity scope binding ALLOWED
Attempt exists and belongs to the supplied Activity scope
Attempt.status = REVIEWED
Attempt has exactly one AssessmentResult
result_id matches that Result
```

The correction updates the existing Result only:

```text
existing AssessmentResult
→ same Result.id
→ same attempt_id
→ same max_score
→ score may change
→ feedback may change or become null
→ no second AssessmentResult
→ no new AssessmentAttempt
→ Attempt remains REVIEWED
```

A successful correction returns `200 OK` and the complete corrected `AssessmentResult`. The response is the Result object only.

Correction is a destructive replacement with no prior-value history; ADR-0007 is not changed.

### 12. Success response representation

Review and correction both return a complete `AssessmentResult`:

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "attempt_id": "00000000-0000-0000-0000-000000000000",
  "score": 8,
  "max_score": 10,
  "feedback": null
}
```

The response must not be:

```text
a partial score/feedback object
an Attempt aggregate wrapper
a status-transition envelope
a fabricated placeholder Result
```

Both commands return the Result directly with `200 OK`.

### 13. Error mapping

The Teacher Assessment Review API uses this normative status mapping:

| Condition | HTTP status |
|---|---:|
| Missing/invalid session | `401 Unauthorized` |
| Unknown `teacher_space_id`, `activity_id`, `attempt_id`, or `result_id` | `404 Not Found` |
| Valid identifiers outside the authenticated Teacher's authorized scope (Teacher Space not owned, or Activity not in that Teacher Space) | `403 Forbidden` |
| Malformed request DTO or invalid field type | `422 Unprocessable Entity` |
| Invalid `score` or `max_score` invariant on Review or Correction | `422 Unprocessable Entity` |
| Invalid `page`, `page_size`, or `status` query value | `422 Unprocessable Entity` |
| Review for non-SUBMITTED state, already REVIEWED, or existing Result | `409 Conflict` |
| Correction for non-REVIEWED state | `409 Conflict` |
| Correction with a non-matching `result_id` | `404 Not Found` |
| REVIEWED Attempt missing its required Result | `500 Internal Server Error` |
| Unexpected server failure | `500 Internal Server Error` |

The mapping preserves the required distinction:

```text
resource/scope errors        → 404
authorization errors         → 403
lifecycle conflicts          → 409
validation errors            → 422
server-side invariant errors → 500
```

Controllers map approved application/domain errors to these statuses. They must not turn a denied, conflicted, or failed operation into a successful empty response. Authorization and scope errors are distinct from validation and lifecycle conflicts.

### 14. REVIEWED Attempt invariant

The server-side invariant is:

```text
REVIEWED AssessmentAttempt
must have exactly one AssessmentResult
```

Rules:

```text
REVIEWED without Result → server-side invariant failure
Failure representation  → 500 Internal Server Error
No valid 200 Result = null response
No fabricated placeholder Result
No partial Result DTO
No recovery or Result-creation endpoint
```

This applies to collection reads, detail reads, and review/correction commands. If the store contains a REVIEWED Attempt without its Result, the affected operation fails as `500` and returns no partial response. The API must not silently create a Result to repair the state.

### 15. Transaction semantics

All Teacher Assessment Review operations use the existing request-scoped SQLAlchemy transaction:

```text
HTTP request
→ request-scoped Session (one active transaction)
→ Teacher Space authorization
→ Education Activity scope check
→ Assessment application operation
→ success: request-scoped transaction owner commits
→ exception: request-scoped transaction owner rolls back
```

Rules:

- Teacher Review operations **join** the already active request-scoped transaction.
- Teacher Review operations must **not** open a new nested transaction, a `begin()` wrapper, a savepoint, or an independent transaction manager.
- The request-scoped transaction owns commit and rollback. HTTP controllers, application services, and domain entities must not commit or roll back.
- Review and correction remain atomic: either the state transition and Result creation/update both succeed or neither is persisted.

The existing internal `TeacherAssessmentResultService` transaction-callable wrapper is an implementation detail and must not be exposed as a nested commit boundary in the public Teacher Assessment Review implementation.

### 16. Assessment bounded-context boundary

Assessment owns all Review-relevant persistence:

```text
AssessmentDefinition
AssessmentAttempt
AssessmentResult
```

Boundary rules:

- Assessment must not access Education private persistence or Learning private persistence.
- Teacher Space must not access Assessment private persistence.
- Education must not access Assessment private persistence.
- Cross-context interaction uses application/public boundaries only.
- No shared ORM models, repositories, foreign keys, or private persistence types cross bounded-context ownership.
- The Teacher Space Activity-scope check is performed through the existing Education application boundary, never through Education private database access.

### 17. ActivityProgress

`ActivityProgress` is not an authorization mechanism and is not a Review discovery or filtering mechanism. Teacher Review does not read, create, update, or depend on `ActivityProgress`. The presence or state of Student Activity Progress never grants or denies Teacher Review access, and a successful Review or Correction never creates or mutates Activity Progress.

### 18. Frontend ownership

Teacher Assessment Review UI is owned by the Assessment frontend module:

```text
apps/frontend/src/modules/assessment/
```

The Teacher Review feature is a distinct feature within that module:

```text
apps/frontend/src/modules/assessment/teacher/
```

Rules:

- Teacher Review UI, queries, mutations, and validation presentation belong in `modules/assessment`.
- The Teacher Review feature must be separated from Student/Learning Assessment UI and must not share per-user state, query cache keys, mutation flows, or component internals with Student Attempt flows.
- Shared code inside the Assessment module may contain only generic presentational/type/query helpers that do not encode Student or Teacher feature state.
- `modules/education` owns the Teacher Activity page and may provide only the entry link/interface into Teacher Assessment Review. It must not implement Assessment Review lifecycle, Result, validation, or error-mapping logic.
- `modules/learning` and Student Assessment UI remain unchanged by this decision.
- Global route registration stays in the application routing layer.

### 19. Teacher UI entry/navigation

The Teacher discovers Review from the existing Teacher Activity page:

```text
Teacher Activity
→ Activity has AssessmentDefinition
→ dedicated Teacher Assessment Review queue
→ queue item
→ dedicated Review detail
```

Canonical frontend routes:

```text
/app/teacher-spaces/:teacherSpaceId/activities/:activityId/assessment-review
/app/teacher-spaces/:teacherSpaceId/activities/:activityId/assessment-review/:attemptId
```

- `teacherSpaceId` and `activityId` are navigation context and mirror the API scope.
- `attemptId` is the canonical Attempt identity.
- Route context is not authorization; the backend remains authoritative for Teacher Space ownership and Activity scope.
- No global Teacher Assessment dashboard route, shortcut, or landing page is introduced.

### 20. Next milestone

The next milestone is **Teacher Assessment Review backend/API implementation**, which implements this ADR. It is explicitly out of scope for the current documentation/contract milestone.

The next implementation milestone must not:

- reopen any decision carried forward in this ADR;
- add a global Teacher Assessment dashboard;
- add a DRAFT membership to the Teacher Review collection;
- add Course/Section/Unit identifiers to the Teacher Review route namespace;
- change AssessmentResult semantics, Attempt lifecycle, Student submission, Activity Progress, or bounded-context ownership.

## Approved constraints carried forward

The following decisions are already approved and are not reopened by ADR-0011:

```text
AssessmentAttempt lifecycle:
  DRAFT → SUBMITTED → REVIEWED

DRAFT editable only by Student owner.
SUBMITTED and REVIEWED immutable.
Submission is optional plain text: string | null.
Blank submission normalizes to null.
DRAFT may be created empty.
Submit requires meaningful submission.
New Attempt only for ACTIVE AssessmentDefinition.
Resubmission creates a new Attempt.
Student cannot read another Student's Attempts/Results.
Historical Student SUBMITTED/REVIEWED detail does not require current enrollment/publication.
Student Assessment uses aggregate detail only; no history collection endpoint.

Teacher review must discover SUBMITTED Attempts.
REVIEWED Attempts remain durably discoverable for correction.
Teacher collection supports both SUBMITTED and REVIEWED.
UUID ascending is the stable ordering key.
Student identity is exposed as opaque student_id.
Teacher routes are scoped by Teacher Space + Activity.
Review/correction return complete AssessmentResult.
Teacher Assessment frontend is separate from Learning/Student Assessment frontend.
Transaction join-existing-request-transaction semantics are approved.
No ActivityProgress authorization.
No cross-bounded-context private persistence access.
```

## Invariants

```text
API scope = /api/v1/teacher-spaces/{teacher_space_id}/activities/{activity_id}

Teacher Review namespace:
  GET  assessment-attempts                    → paginated collection
  GET  assessment-attempts/{attempt_id}       → detail
  POST assessment-attempts/{attempt_id}/review    → complete Result
  POST assessment-attempts/{attempt_id}/correction → complete Result

Collection membership:
  SUBMITTED + REVIEWED by default
  DRAFT is never a member
  status filter: submitted | reviewed
  invalid status → 422

Ordering:
  id ASC only
  authorization/filter before order/page

Pagination:
  ADR-0003
  page default 1, min 1
  page_size default 20, min 1, max 100
  response = items + page + page_size + has_next
  no total/count
  page beyond range → 200 empty items

DTO:
  item    = id + student_id + status + assessment_definition_id + activity_id + result
  detail  = item + submission
  result  = id + attempt_id + score + max_score + feedback
  student_id is opaque; no Users lookup

Authorize:
  teacher_id owns teacher_space_id
  + activity_id in teacher_space_id scope
  Assessment performs operation after both ALLOWED
  no controller authorization/domain logic
  no named permission

Errors:
  unknown resources      → 404
  authorization deny     → 403
  lifecycle conflict    → 409
  request/domain validation → 422
  REVIEWED without Result  → 500
  unexpected failure       → 500

REVIEWED invariant:
  exactly one AssessmentResult
  missing Result → 500
  never valid 200 with result=null
  never fabricate or return partial Result

Transaction:
  join active request-scoped transaction
  no nested transaction/savepoint
  request-scoped owner commits/rolls back
  review/correction atomic

Bounded context:
  no Assessment → Education/Learning private persistence
  no Teacher Space → Assessment private persistence
  no cross-context ORM/repository/FK sharing

ActivityProgress:
  not authorization
  not discovery/filter
  no read/create/update in Teacher Review

Frontend:
  modules/assessment owns Teacher Review
  Teacher Review separated from Student/Learning Assessment UI
  no global Teacher Assessment dashboard

Entry:
  Teacher Activity → assessment-review queue/detail
```

## Alternatives

### Course/Section/Unit-discoverable route

Rejected. The approved Teacher Review scope is Teacher Space plus Activity. Including Course, Section, or Learning Unit identifiers would add hierarchy to the Review namespace without adding authorization capability. The existing Course/Section/Unit API nesting is used where it is already part of the Education hierarchy contract, not for Assessment Review.

### Route carrying `assessment_definition_id`

Rejected. Activity has at most one AssessmentDefinition, and an Attempt already binds to its Definition. Teacher Review resolves Definition from Assessment-owned Attempt data. Requiring it as a client route/query identifier is redundant.

### Collection default of only SUBMITTED

Rejected. REVIEWED Attempts must remain durably discoverable for correction. A default of only SUBMITTED would hide every already-reviewed Attempt and break the approved correction loop.

### Collection includes DRAFT

Rejected. DRAFT is a Student-owned mutable state and is not a Teacher actionable queue item in this milestone.

### Ordering by submission or creation time

Rejected. No timestamp ordering is part of the approved Assessment contract, and `id ASC` is the approved stable ordering key.

### No pagination

Rejected. A Teacher Review queue can grow with Student submissions and must follow the platform pagination contract.

### Return Attempt aggregate from review/correction

Rejected. The approved decision requires review/correction respond with the complete `AssessmentResult`, not an Attempt wrapper.

### Separate `assessment-results/{result_id}` correction namespace

Rejected. Correction is attempt-scoped under the Teacher Space + Activity namespace. `result_id` is validated in the request against the Attempt's single Result rather than adding a second collection/resource namespace.

### Auto-create a Result for REVIEWED without Result

Rejected. That would fabricate a Result and repair inconsistent state implicitly. The correct response is a `500` invariant failure.

### Use ActivityProgress to decide review access

Rejected. ActivityProgress is not an authorization mechanism and must not connect Assessment Review access to Learning progress state.

### Global Teacher Assessment dashboard

Rejected. Teacher Review is entered from the Teacher Activity page. A global dashboard is a new product surface outside this milestone.

### Teacher Review UI in `modules/teacher` or `modules/education`

Rejected. Teacher Assessment Review is Assessment UI, not Teacher Space shell or Education structure UI. It belongs to the Assessment frontend module, separated from Student Assessment UI.

## Consequences

- Teachers can discover both SUBMITTED Attempts requiring review and REVIEWED Attempts requiring correction.
- The collection uses one stable UUID ordering key and the platform pagination contract.
- `student_id` is exposed as an opaque identifier without a Users lookup dependency.
- Teacher Review authorization remains Teacher Space ownership plus Education Activity scope.
- Review and correction return the complete Result and preserve the Result semantics defined by ADR-0007.
- Resource/scope, authorization, lifecycle, validation, and invariant failures are distinguished explicitly.
- REVIEWED without Result is treated as a server-side invariant failure rather than a recoverable partial state.
- Teacher Review joins the request-scoped transaction and keeps review/correction atomic without nested transaction ownership.
- Assessment persistence remains Assessment-owned; no cross-context private persistence access is introduced.
- `ActivityProgress` remains outside Assessment Review authorization and lifecycle.
- Teacher Review UI is owned by the Assessment frontend module and remains separated from Student/Learning Assessment UI.
- The next milestone is Teacher Assessment Review backend/API implementation.

## Next implementation milestone scope

The next milestone is **Teacher Assessment Review backend/API implementation**, which may implement:

- Teacher Space + Activity scoped Review collection and detail HTTP endpoints;
- one-based page/page-size pagination per ADR-0003;
- `status=submitted|reviewed` filtering with both-status default;
- UUID ascending ordering;
- opaque `student_id` DTO visibility;
- Review and Correction commands returning complete `AssessmentResult`;
- the approved 401/403/404/409/422/500 error mapping;
- Teacher Space ownership and Education Activity-scope orchestration at the application boundary;
- request-scoped transaction joining without nested transaction/savepoint ownership;
- REVIEWED-without-Result invariant failure handling;
- the `git diff --check`, status, test, lint, and architecture-boundary checks required by the issue.

Teacher Review frontend queue/detail implementation, Teacher Activity-page entry, and any path from this contract through the frontend are **not** part of the next milestone. They require a separate authorized milestone after the Teacher Assessment Review backend/API implementation.

The milestone must change no existing implementation file semantics outside the scope required by this approved contract, and must not implement earlier/later product behavior.

## Non-goals

This decision does not implement or authorize:

- backend services, HTTP controllers, DTO classes, or persistence;
- frontend code;
- tests;
- migrations or database schema changes;
- new domain fields or lifecycle states;
- `AssessmentResult` semantic changes;
- `ActivityProgress` changes or authorization;
- Education or Learning private persistence access;
- a global Teacher Assessment dashboard;
- Course/Section/Unit hierarchy identifiers in Teacher Review routes;
- DRAFT membership in the Teacher Review collection;
- `AssessmentDefinition` public Review routes;
- a separate Result collection/history API;
- Result correction history, versions, audit metadata, `assessed_at`, or `assessed_by`;
- Result deletion or review reversal;
- Student-facing Teacher endpoints;
- new permission names;
- review/correction retry idempotency infrastructure beyond the approved command semantics.
