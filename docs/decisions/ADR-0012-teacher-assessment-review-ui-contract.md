# ADR-0012 — Teacher Assessment Review UI Contract

- **Status:** Accepted
- **Date:** 2026-08-28
- **Issue:** EDU-070
- **Decision:** Define the Teacher-facing Assessment Attempt review queue, Attempt detail, review interaction, correction interaction, Result presentation, loading/empty/error states, pagination, navigation, Student identity presentation, and frontend API boundary before any Teacher Assessment Review UI implementation.

## Context

ADR-0002 defines the React frontend architecture: React Router for navigation, `shared/api` for all backend HTTP communication, TanStack Query for server state, explicit `app → modules → shared` dependency direction, and normalized API errors. ADR-0009 establishes the Assessment frontend module and the Student Assessment UI contract. ADR-0010 defines the Student Assessment HTTP API and sequencing. ADR-0011 defines the Teacher Assessment Review API contract, the Teacher Space + Activity scope, the `SUBMITTED`/`REVIEWED` collection, the `id ASC` ordering and ADR-0003 pagination, the review and correction commands, the opaque `student_id`, the approved error mapping, and the Assessment module ownership of Teacher Review UI.

EDU-069 implements and merges the Teacher Assessment Review HTTP API described by ADR-0011:

```text
GET  /api/v1/teacher-spaces/{teacher_space_id}/activities/{activity_id}/assessment-attempts
GET  /api/v1/teacher-spaces/{teacher_space_id}/activities/{activity_id}/assessment-attempts/{attempt_id}
POST /api/v1/teacher-spaces/{teacher_space_id}/activities/{activity_id}/assessment-attempts/{attempt_id}/review
POST /api/v1/teacher-spaces/{teacher_space_id}/activities/{activity_id}/assessment-attempts/{attempt_id}/correction
```

There is no Teacher Assessment Review frontend contract yet. The Teacher Activity page is the discovery surface for Teacher Review, but the Teacher UI must be fixed before implementation because it introduces:

- the first Teacher paginated Review queue;
- a `status` queue filter with both-status default;
- a dedicated Attempt detail that distinguishes `SUBMITTED` and `REVIEWED`;
- a Review interaction that is available only for `SUBMITTED`;
- a Correction interaction that is available only for `REVIEWED`;
- immutable Student submission rendering;
- complete Review Result presentation without invented fields;
- the `500` REVIEWED-without-Result invariant failure treatment;
- page-level, operation-level, and field-level error behavior;
- explicit mutation states without optimistic lifecycle transitions;
- conservative opaque `student_id` presentation;
- a typed Assessment module API boundary that fixes the exact EDU-069 request/response shapes.

This ADR defines the UI/navigation contract only. It introduces no runtime implementation.

## Decision

### 1. Frontend module ownership

Teacher Assessment Review belongs to the Assessment frontend module:

```text
apps/frontend/src/modules/assessment/
```

The Teacher Review feature is a distinct feature within that module:

```text
apps/frontend/src/modules/assessment/teacher/
```

Rules:

- Teacher Review queue, Attempt detail, review and correction forms, validation presentation, Result presentation, and error mapping belong to `modules/assessment`.
- Teacher Review must remain separated from Student/Learning Assessment UI. It must not share per-user state, query cache keys, mutation flows, or component internals with the Student Attempt flow.
- Shared code inside the Assessment module may contain only generic presentational/type/query helpers that do not encode Student or Teacher feature state.
- `modules/education` owns the Teacher Activity page. It provides only the minimal entry interface into Teacher Assessment Review. It must not implement Review lifecycle, Result, validation, or error-mapping logic.
- `modules/learning` and Student Assessment UI remain unchanged by this decision.
- Global route registration remains in the application routing layer.
- The frontend must not depend on backend persistence, ORM models, or repository internals.

Boundary:

```text
Teacher Activity UI (modules/education)
        ↓
Assessment public UI integration (modules/assessment)
        ↓
Assessment API client/application boundary (modules/assessment)
        ↓
Teacher Assessment HTTP API (EDU-069)
```

### 2. Entry point

The canonical Teacher entry point is:

```text
Teacher Activity page
    ↓
"Assessment review" entry
    ↓
Teacher Assessment Review queue
```

The Teacher Activity page remains the discovery surface. The complete Review queue must not be rendered inline inside the Teacher Activity page.

The Assessment module exposes a minimal public integration interface, for example:

```text
TeacherAssessmentReviewEntry
```

The Teacher Activity page renders this entry when the Activity is assessment-bearing. The Assessment module receives the minimum navigation context required by ADR-0011:

```text
teacherSpaceId
activityId
```

The entry contract does **not** require the Teacher Activity page to implement Assessment logic. It only supplies navigation context and renders the Assessment-owned entry.

**Assessment-bearing Activity signal.** The UI contract treats "Activity has an AssessmentDefinition" as the condition for showing the Teacher Review entry. ADR-0011 requires that condition. The source of that signal is the Activity page's existing/project data; this contract does **not** define a new backend endpoint or a new frontend Activity field.

**Known integration limitation (must be resolved before UI implementation).** As of this contract, the Teacher Activity API response model exposed to the Teacher Activity page does not carry an `assessment_definition_id` field, so the Teacher Activity page today has no direct data attribute that proves an Activity is assessment-bearing. The Student Activity model has this field, but the Teacher Activity model does not. The UI implementation milestone must supply this signal through an approved source (an approved Activity-side field or an equivalent approved public boundary) before rendering the entry by that condition. The contract does not invent or authorize a new Review API endpoint for this purpose.

### 3. Canonical frontend routes

Frontend routes are a UI/navigation contract only. They are **not** backend routes.

Queue route:

```text
/app/teacher-spaces/:teacherSpaceId/activities/:activityId/assessment-review
```

Attempt detail route:

```text
/app/teacher-spaces/:teacherSpaceId/activities/:activityId/assessment-review/:attemptId
```

Route semantics:

```text
teacherSpaceId → Teacher Space ownership navigation context (mirrors API scope)
activityId     → Activity navigation context (mirrors API scope)
attemptId      → canonical AssessmentAttempt identity (detail only)
```

Rules:

- The frontend route uses exactly `teacherSpaceId` and `activityId` plus optional `attemptId`. It does not use Course/Section/Learning Unit or `assessment_definition_id`.
- Route context is not authorization. The backend remains authoritative for Teacher Space ownership and Activity scope.
- Historical direct navigation must work with the Attempt ID in the URL. A user may open the detail URL directly and the UI must render from the known attempt ID.
- No global Teacher Assessment dashboard route, shortcut, or landing page is introduced.

Example React Router paths (contract, not implementation):

```text
app/teacher-spaces/:teacherSpaceId/activities/:activityId/assessment-review
app/teacher-spaces/:teacherSpaceId/activities/:activityId/assessment-review/:attemptId
```

### 4. Review queue

The Review queue consumes the EDU-069 collection endpoint:

```text
GET /api/v1/teacher-spaces/{teacher_space_id}/activities/{activity_id}/assessment-attempts
    ?page={page}
    &page_size={page_size}
    &status={submitted|reviewed}   // optional
```

Queue contract:

- Teacher sees only Attempts from the authorized Teacher Space + Activity. The frontend does not reproduce backend authorization and does not filter by enrollment, ActivityProgress, or Student identity.
- Default membership is `SUBMITTED` + `REVIEWED`. The status filter follows ADR-0011.
- Ordering is `id ASC` exactly. The frontend must not sort, reorder, or group client-side.
- Pagination follows ADR-0003: one-based `page` default 1, `page_size` default 20 max 100, response `{items, page, page_size, has_next}`.
- No infinite scroll and no cursor pagination.
- The response has no `total`/`total_pages`; the frontend must not assume an exact page count.
- A page beyond range returns `200` with empty `items`, requested `page`, and `has_next: false`.
- Opaque `student_id` may be displayed as the approved Student reference (see Student identity section).
- No Student profile lookup, no enrollment check, no ActivityProgress dependency.
- Historical REVIEWED Attempts remain discoverable because default membership includes REVIEWED.

#### Loading

While a page is loading, the queue shows a page-level loading state for the collection. Loading state replaces the queue content, not only a spinner inside an already-rendered list, so the user is not shown stale items as if they were the loading result.

#### Empty

An empty result shows an explicit empty state, not an error and not a fabricated submission/Result row.

- Empty default/all view: no SUBMITTED or REVIEWED Attempts in the authorized Activity scope → "No attempts to review".
- Empty filtered view with `status=submitted`: no SUBMITTED Attempts.
- Empty filtered view with `status=reviewed`: no REVIEWED Attempts.

The empty state is distinguished per selected filter only when the filter is explicit. The frontend does not infer a global empty state when a filter is applied.

#### Status filter

The UI provides the approved two-value filter plus an all view:

```text
All
Submitted
Reviewed
```

- `status` is never sent as `draft`.
- Invalid status values are client-suppressed by the approved two-value control; the backend remains authoritative and returns `422` for malformed query values.
- Changing the filter resets pagination to `page = 1`.

#### Pagination navigation

Page navigation is previous/next buttons driven by `page` and `has_next`.

```text
has_next true  → Next enabled
has_next false → Next disabled or hidden
page > 1       → Previous enabled
page = 1       → Previous disabled or hidden
```

The queue keeps the current `page` in local/query state. The frontend must not compute a page count from an unavailable total. The implementation may maintain the selected status filter and page in the URL query so the queue state survives refresh/back navigation.

### 5. Attempt detail

The Attempt detail consumes the EDU-069 aggregate detail endpoint:

```text
GET /api/v1/teacher-spaces/{teacher_space_id}/activities/{activity_id}/assessment-attempts/{attempt_id}
```

Detail DTO fields:

```text
id
student_id
status                 = submitted | reviewed
assessment_definition_id
activity_id
submission             (string | null)
result                 (AssessmentResult | null)
```

#### SUBMITTED

Displays:

- `SUBMITTED` status;
- Student reference (opaque `student_id`);
- immutable submission as normal read-only text or preformatted text;
- Review action.

The UI must not display a Result.

#### REVIEWED

Displays:

- `REVIEWED` status;
- Student reference (opaque `student_id`);
- immutable submission as normal read-only text or preformatted text;
- complete Result;
- Correction action.

The UI must not display an editor for the Student submission.

#### Submission rendering

Submission is always read-only. It is rendered as normal text or preformatted text, not as a disabled editor, for both `SUBMITTED` and `REVIEWED`. There is no Save/Clear/Edit control for Student submission.

`submission` is `string | null` in the schema. For every SUBMITTED/REVIEWED collection member it is normalized non-null. The UI renders `null`/`""` conservatively as empty content and does not invent a submission placeholder.

#### Detail status re-validation

The detail view must not assume the queue filter. It renders whatever status the detail response contains and shows Review for `submitted` and Correction for `reviewed`. A response whose status is neither `submitted` nor `reviewed` is treated as an unexpected/invariant failure state, not a rendered lifecycle.

### 6. Review flow

Review is the approved `SUBMITTED → REVIEWED` transition:

```text
POST /api/v1/teacher-spaces/{teacher_space_id}/activities/{activity_id}/assessment-attempts/{attempt_id}/review
```

Request:

```text
score      → integer; required; 0 <= score <= max_score
max_score  → integer; required; max_score > 0
feedback   → string | null; optional
```

The UI:

1. shows the immutable submission;
2. collects `score`, `max_score`, and optional `feedback`;
3. sends the review mutation;
4. treats a returned complete `AssessmentResult` as authoritative;
5. updates the Attempt detail state with `status = REVIEWED` and the returned Result;
6. renders the REVIEWED read-only state with the complete Result;
7. handles validation and other failures without inferring the transition.

Rules:

- Review is available only for `SUBMITTED`.
- There is no second independent client-side lifecycle. The UI does not assign a local `REVIEWED` status before backend success.
- The UI must never represent `SUBMITTED + editable submission` or `REVIEWED + editable submission`.
- The frontend supplies no `student_id`, no `definition_id`, and no `attempt` identifier fields; those come from the authenticated scope and the detail URL.
- Backend `422` validation maps to the relevant Result form fields (see error policy).

### 7. Correction flow

Correction is the approved update of the existing Result on a `REVIEWED` Attempt:

```text
POST /api/v1/teacher-spaces/{teacher_space_id}/activities/{activity_id}/assessment-attempts/{attempt_id}/correction
```

Request:

```text
result_id → UUID; required; the single Result for this Attempt
score     → integer; required; 0 <= score <= max_score
feedback  → string | null; required
```

The approved interaction is **explicit Edit → Save/Cancel**.

```text
REVIEWED read-only Result card
    ↓ Teacher selects "Edit"
    ↓ editable score + feedback form (max_score is read-only)
    ↓ Teacher enters values and selects Save
    ↓ correction mutation
    ↓ success renders complete corrected Result
Cancel → discards local edits, returns to read-only Result card
```

Rules:

- Correction modifies the Result only. The submission is never editable.
- The Attempt remains `REVIEWED`; the UI must not render it as SUBMITTED or reopen it.
- `max_score` is the immutable Result snapshot. It is shown read-only in the correction form and is never sent as a changeable field by the frontend.
- `result_id` is carried from the loaded Result and is never editable by the Teacher.
- `feedback` is required in the correction request; the form may allow clearing feedback by submitting a null/blank value, which the backend normalizes to null.
- No autosave. Save is explicit.
- No optimistic Result replacement before backend success.

### 8. Result presentation

The Result uses exactly the ADR-0007 / EDU-069 fields:

```text
id
attempt_id
score
max_score
feedback
```

The UI displays:

```text
score / max_score
```

and, when `feedback` is non-null, the plain-text feedback.

When `feedback` is `null`, no feedback section, placeholder, or inferred message is rendered. This follows the approved ADR-0009 semantics.

The UI must not invent Result fields such as pass/fail, percentage conversion, grade, assessed_at, assessed_by, version, or correction history.

### 9. REVIEWED without Result

A REVIEWED Attempt without its required Result is a backend invariant violation. EDU-069 maps it to `500 Internal Server Error`. The UI contract preserves that behavior.

For direct detail navigation:

```text
500
→ retryable Assessment error state
```

Rules:

- The UI displays a retryable Assessment error state with a Retry action.
- It does not fabricate a Result, a status, a score, feedback, or any placeholder Result card.
- It does not define a new partial error DTO.
- It does not require the backend to return submission inside the error payload.
- If cached Attempt data exists (for example from a previously loaded detail or queue), the UI may retain the cached immutable submission beside the error state, but cache presence is not a correctness requirement. If no snapshot is available, no submission is required to remain visible.
- Retry repeats the detail read only. It does not create a Result, change status, calculate a score, submit, or invoke any recovery mutation.

### 10. Error policy

Feature-specific Teacher Assessment UI error behavior is consistent with the EDU-069 HTTP contract.

| HTTP | UI meaning | Where shown |
|---|---:|---|
| 404 | Attempt/resource unavailable | page-level |
| 403 | Assessment access denied | page-level |
| 409 | Invalid lifecycle/state conflict | page-level (queue state changed) or operation-level (mutation) |
| 422 | Validation failure | operation-level / field-level for mutation payload; page-level for malformed queue query |
| 500 / unexpected | Retryable Assessment error | page-level for reads; operation-level retryable for mutations |

Rules:

- Raw backend exception details are never exposed to the user. Errors are normalized at the Assessment module API/application boundary into feature-specific messages.
- No new HTTP statuses are invented.
- The UI does not turn 404, 403, 409, 422, or 500 into an empty successful state.
- Authentication/session (`401`) behavior remains owned by the existing application shell and is not redefined here.
- 403 and 404 are not conflated. A 404 retains the "resource unavailable" state; a 403 retains the "access denied" state.

#### Page-level errors

Collection load and detail load errors show a page-level error state. The queue/detail content is not rendered as if loaded.

#### Operation-level errors

Review and correction mutation errors show an operation-level error state attached to the mutation (`review` or `correction`). The mutation button returns to enabled after failure; no successful transition is shown.

#### Field-level errors

For review and correction, backend `422` validation is mapped to the relevant form controls:

```text
score     → score field
max_score → max_score field (review only; correction max_score is read-only and never re-validated as an input)
feedback  → feedback field
```

The form keeps the user-entered values after a validation failure where safe.

### 11. Mutation UX

For Review and Correction:

```text
idle
→ submitting
→ success
```

and:

```text
submitting
→ error
```

Requirements:

- The mutation button is disabled while the operation is in flight.
- Duplicate submission is prevented by the in-flight disabled state and by not issuing a new request until the current mutation settles.
- No optimistic lifecycle transition is performed before confirmed backend success.
- User-entered Result data is preserved after validation or network failure where safe, so the Teacher can correct the form rather than retype values.
- No generic autosave infrastructure is introduced.
- Review and Correction are distinct mutations with distinct mutation states.

### 12. Success behavior

EDU-069 review and correction return the complete `AssessmentResult` as `200 OK`.

Preferred behavior:

```text
mutation success
→ update Attempt detail state from the returned Result
→ status/result presentation becomes authoritative
```

For Review, the returned Result plus the known Attempt identity and Activity scope is sufficient to render the REVIEWED state (`status = REVIEWED`, `result = returned Result`). The UI must not infer the Result from anything other than the returned response.

For Correction, the returned Result replaces the existing Result in the Attempt detail state while preserving:

```text
submission = unchanged (from loaded detail)
status = REVIEWED
result = returned corrected Result
```

The UI does not require an immediate extra GET when the mutation response contains everything needed to update the current detail view. If the UI nevertheless needs a GET to reconcile a broader cached aggregate (for example queue summary), that GET is refresh/invalidation only; it is never required to display the confirmed mutation result and is not used to re-issue the mutation.

### 13. Navigation

#### Queue → Attempt detail

Selecting an Attempt in the queue navigates to the detail route with the Attempt ID:

```text
/app/teacher-spaces/:teacherSpaceId/activities/:activityId/assessment-review/:attemptId
```

#### Attempt detail → Queue

Back navigation preserves queue context where practical: the selected `page` and `status` filter, when maintained in URL query/state, are restored on return. The frontend must not require browser-history behavior as the only navigation mechanism.

#### Attempt detail → Activity

A clear route back to the originating Activity is provided from both the queue and the detail. Because the queue/detail route carries only `teacherSpaceId` and `activityId`, the originating Teacher Activity page navigation is supplied by the Activity-side integration context. The UI contract does not require the Assessment module to know Course/Section/Learning Unit identifiers.

#### Direct navigation

Historical direct navigation must work with the Attempt ID in the URL. Opening:

```text
/app/teacher-spaces/:teacherSpaceId/activities/:activityId/assessment-review/:attemptId
```

must render the detail from the known Attempt ID and the supplied scope, even when the queue was never visited in the current session.

### 14. Student identity

EDU-069 exposes opaque `student_id`. There is no Student profile lookup contract.

The UI treats the Student identifier conservatively:

- The identifier may be displayed as an opaque Student reference with a label that makes clear it is a reference, for example "Student reference".
- The UI does not invent or display a name, email, avatar, profile link, enrollment details, or any other Student attribute.
- The UI does not look up a Student profile.
- `student_id` is presentation data only and is never an authorization input.

### 15. Frontend API boundary

A typed frontend API boundary lives in `modules/assessment` and conceptually exposes these operations:

```text
listAssessmentAttempts({ teacher_space_id, activity_id, status, page, page_size })
getAssessmentAttempt({ teacher_space_id, activity_id, attempt_id })
reviewAssessmentAttempt({ teacher_space_id, activity_id, attempt_id, score, max_score, feedback })
correctAssessmentAttempt({ teacher_space_id, activity_id, attempt_id, result_id, score, feedback })
```

Contract requirements:

- These are conceptual types/operations, not runtime code authorized by this ADR.
- API client code belongs to `modules/assessment`. Teacher Activity components must not call the Assessment API directly; they consume only the module's public integration interface.
- Backend HTTP communication uses the existing `shared/api` client (cookie credentials, base-URL configuration, normalized errors) required by ADR-0002.
- The boundary types mirror the EDU-069 response DTOs exactly:

```text
TeacherAssessmentAttemptPageResponse
  └── items: TeacherAssessmentAttemptItemResponse[]
      └── id, student_id, status, assessment_definition_id, activity_id, result
  └── page, page_size, has_next

TeacherAssessmentAttemptDetailResponse
  = TeacherAssessmentAttemptItemResponse + submission

AssessmentResultResponse
  └── id, attempt_id, score, max_score, feedback
```

- The boundary never exposes `student_id` as a client-submittable field.
- The boundary never exposes a `definition_id`, Course/Section/Unit id, or `teacher_id` as a mutation-input field.
- The boundary does not directly access backend persistence, ORM, domain, or repository objects.

### 16. No new product semantics

The contract does not introduce:

- a global Teacher Assessment dashboard;
- A cross-Activity Review queue;
- Attempt history outside the authorized Activity scope;
- Student profile discovery;
- ActivityProgress dependency or authorization;
- current/best/final Attempt semantics;
- resubmission semantics beyond the approved Attempt lifecycle;
- automatic review assignment;
- autosave;
- bulk review;
- bulk correction;
- sorting other than `id ASC`;
- cursor pagination;
- new backend endpoints;
- new frontend Activity fields or new Review API fields unless separately approved.

## Invariants

```text
Frontend ownership
→ modules/assessment/teacher owns Teacher Review
→ modules/education provides only entry link/interface
→ no Assessment logic in Teacher Activity page
→ no Student/Teacher feature state sharing inside modules/assessment

Entry
→ Teacher Activity → "Assessment review" → queue
→ entry condition: Activity is assessment-bearing (source approved separately)
→ no inline full queue in Activity page

Frontend routes
→ /app/teacher-spaces/:teacherSpaceId/activities/:activityId/assessment-review
→ /app/teacher-spaces/:teacherSpaceId/activities/:activityId/assessment-review/:attemptId
→ frontend route ≠ HTTP API route
→ teacherSpaceId + activityId are navigation context only

Queue
→ GET EDU-069 collection
→ SUBMITTED + REVIEWED default
→ status = submitted | reviewed, default both
→ id ASC only
→ page one-based, page_size default 20 max 100
→ response items + page + page_size + has_next
→ no total/count
→ no infinite scroll/cursor/client sorting
→ opaque student_id may be shown as Student reference

Detail
→ SUBMITTED: submission + status + Student reference + Review
→ REVIEWED: submission + status + Student reference + Result + Correction
→ submission read-only, never editable
→ Result absent for SUBMITTED

Review
→ only SUBMITTED
→ score + max_score + optional feedback
→ no optimistic REVIEWED
→ mutation success updates detail to REVIEWED + complete Result

Correction
→ only REVIEWED
→ Edit → Save/Cancel
→ score + required feedback (blank may normalize to null)
→ max_score read-only
→ result_id carried, not edited
→ submission immutable
→ no autosave

Result
→ id + attempt_id + score + max_score + feedback
→ display score / max_score
→ feedback shown only when non-null
→ no extra Result fields

REVIEWED without Result
→ 500 → retryable Assessment error
→ never fabricate Result
→ cached submission may remain but is not required

Errors
→ 404 resource unavailable (page-level)
→ 403 access denied (page-level)
→ 409 lifecycle conflict (page/operation-level)
→ 422 validation (operation/field-level)
→ 500/unexpected retryable
→ no raw backend details
→ no new statuses

Mutation UX
→ idle → submitting → success
→ submitting → error
→ button disabled in flight
→ duplicate prevented
→ no optimistic transition
→ entered values preserved after validation failure

Success
→ mutation result authoritative
→ review: status REVIEWED + result
→ correction: same id/attempt_id/max_score + updated score/feedback
→ no required immediate GET unless reconciliation is needed

Navigation
→ Queue → Detail
→ Detail → Queue preserves page/filter where practical
→ Detail → Activity clear route
→ direct Attempt ID URL works

Student identity
→ opaque student_id as "Student reference"
→ no profile/name/email/avatar/enrollment
→ never authorization

API boundary
→ modules/assessment owns typed client interface
→ exact EDU-069 DTO shapes
→ no direct backend persistence access
```

## Alternatives

### Render the full queue inline on the Teacher Activity page

Rejected. The Teacher Activity page is the discovery surface, while Review interaction uses a dedicated Assessment-owned queue/detail experience consistent with ADR-0009 and ADR-0011.

### Teacher Review UI in `modules/teacher`

Rejected. Teacher Assessment Review is Assessment UI, not Teacher Space shell UI. It belongs to `modules/assessment`, separated from Student/Learning Assessment UI.

### Demonstrate the entry solely from an `assessment_definition_id` field already available on the Teacher Activity page

Not currently possible. The contract records that the Teacher Activity API does not expose that field today and requires an approved source of the activity-assessment signal before UI implementation. This does not authorize a new Review API.

### Infinite scrolling or cursor pagination

Rejected. ADR-0003 one-based page pagination and ADR-0011 `id ASC` ordering are the approved contract.

### Client-side sorting/filtering of the queue

Rejected. Ordering is `id ASC` and membership is backend-authoritative.

### Editable submission textarea for SUBMITTED/REVIEWED

Rejected. Student submission is immutable; the UI renders read-only text.

### Inline always-visible correction inputs

Rejected. Explicit Edit → Save/Cancel matches the existing explicit-action frontend convention and avoids accidental edits.

### Autosave for review/correction input

Rejected. The contract uses explicit mutations to avoid duplicate/ambiguous writes.

### Optimistic REVIEWED/Result display before backend success

Rejected. The UI must not represent a lifecycle transition before the backend confirms it.

### Fabricate a Result placeholder for REVIEWED-without-Result

Rejected. ADR-0011 maps the invariant to 500; the UI shows a retryable error instead.

### Display Student name/email/profile/avatar

Rejected. EDU-069 exposes only opaque `student_id`.

### Require a backend GET after every successful review/correction

Rejected by default. The mutation response contains the complete Result; an extra GET is only refresh/invalidation when needed to reconcile a broader cache.

## Consequences

- Teacher Review UI is owned by `modules/assessment` and separated from Student/Learning Assessment UI.
- Activity remains the discovery surface without implementing Assessment logic.
- The Review queue uses the EDU-069 collection contract with ADR-0003 pagination and `id ASC` ordering.
- Review and Correction are explicit, distinct mutations without optimistic lifecycle transitions.
- Student submission is always read-only; the Result uses the approved ADR-0007 fields only.
- REVIEWED-without-Result remains a retryable `500` invariant error without a fabricated Result.
- Opaque `student_id` is presented conservatively as a Student reference only.
- A typed Assessment module API boundary mirrors the real EDU-069 DTOs.
- The frontend never invents new backend endpoints, fields, or product semantics.
- The UI implementation milestone must first resolve how the Teacher Activity page obtains the approved activity-assessment signal, because the current Teacher Activity API does not expose it.

## Non-goals

This decision does not implement or authorize:

- React components, React Router code, TanStack Query code, hooks, state management, styling, or UI tests;
- a new backend endpoint, controller, schema, or persistence change;
- a Teacher-facing AssessmentDefinition HTTP API;
- new frontend Activity fields or a new Review API field;
- Student Assessment UI changes;
- ActivityProgress changes or authorization;
- a global Teacher Assessment dashboard;
- cross-Activity Review history;
- bulk review/correction, autosave, client-side sorting, cursor pagination, or infinite scroll;
- Student profile discovery;
- current/best/final Attempt semantics or resubmission beyond the approved lifecycle;
- automatic review assignment.
