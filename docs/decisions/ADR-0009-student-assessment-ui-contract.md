# ADR-0009 — Student Assessment UI Contract

- **Status:** Accepted
- **Date:** 2026-08-27
- **Issue:** EDU-064 / #127
- **Decision:** Define the Student-facing Assessment entry, DRAFT editor, submit flow, read-only states, Result presentation, detail-only history, errors, API sequencing, and frontend module ownership before UI implementation.

## Context

ADR-0006 defines the Assessment lifecycle and historical invariants:

```text
DRAFT → SUBMITTED → REVIEWED
```

ADR-0007 defines the complete AssessmentResult shown after review. ADR-0008 defines nullable
plain-text submission, meaningful-content validation, the ownership-scoped Attempt aggregate detail,
and distinct authorization behavior for mutable DRAFT access and historical SUBMITTED/REVIEWED reads.
EDU-063 implements those backend application and persistence contracts but intentionally exposes no
public Student Assessment HTTP API or frontend UI.

The existing Student Activity page is the Student-facing Activity and Content experience. Frontend
architecture requires React Router, TanStack Query for server state, normalized API errors, and explicit
module boundaries. It does not yet define an Assessment frontend module or the Student Assessment UX.

The UI contract must therefore be fixed before an API milestone and a later UI implementation. This
ADR introduces no runtime implementation.

## Decision

### Frontend ownership

A new frontend module is approved:

```text
apps/frontend/src/modules/assessment/
```

The Assessment module owns Assessment-specific UI, local form behavior, server-state queries and
mutations, validation presentation, Attempt status presentation, and Result presentation. Backend HTTP
communication continues to use the shared API client required by ADR-0002.

The Learning module continues to own the Student Activity page. It may consume only a minimal public
integration component or interface exported by the Assessment module. Learning must not implement
Assessment lifecycle, submission, Result, or error-mapping business logic.

Global route registration remains in the application routing layer. This ADR does not approve an exact
URL path or route-parameter schema; those depend on the separately approved Student Assessment HTTP
API contract.

### Assessment entry

The Student discovers Assessment from the existing Student Activity page. The Activity page presents
an Assessment call to action that enters an Assessment-owned flow and navigates to a dedicated Attempt
detail experience.

Attempt creation is always explicit. Opening the Assessment experience must not automatically create a
DRAFT. When creating a new Attempt, the Student explicitly invokes `Create DRAFT`; after successful
creation, the UI opens the dedicated detail for the returned Attempt identifier.

A known Attempt may be opened directly through its dedicated detail navigation. The UI does not infer
or persist a current, final, or best Attempt.

### DRAFT experience

A DRAFT detail displays:

- DRAFT status;
- a plain-text textarea containing the current submission or empty when submission is `null`;
- an explicit Save action;
- an explicit Submit action.

The textarea represents the complete submission. Save fully replaces the DRAFT submission. Saving an
empty or whitespace-only textarea may clear the persisted submission to `null`, consistent with
ADR-0008. There is no autosave, structured editor, attachment control, partial patch, or change history.

Unsaved textarea state is local UI state. TanStack Query remains the owner of confirmed server state.
A successful Save updates or invalidates the corresponding Attempt detail query rather than creating a
second Attempt.

### Submit flow

Submit follows this order:

```text
Student selects Submit
→ client checks meaningful plain-text content
→ invalid content shows inline validation and no submit request is sent
→ valid content opens a confirmation dialog
→ Student confirms
→ submit request is sent
→ success renders SUBMITTED read-only state
```

Client validation uses the same meaningful-content rule as ADR-0008: `null`, empty, and
whitespace-only content are invalid. Client validation is a UX guard and does not replace backend
validation.

The confirmation dialog communicates that the submitted Attempt becomes immutable. Cancelling the
dialog sends no submit request and leaves the DRAFT unchanged.

Backend validation failure (`422`) is rendered as an inline validation error associated with the
submission/submit operation. Unexpected submit failure leaves the current Attempt view available.
No successful status transition is inferred by the frontend.

### SUBMITTED state

A SUBMITTED detail displays:

- SUBMITTED status;
- the immutable submission as normal read-only text or preformatted text;
- an explicit `Create another Attempt` action.

The current Attempt exposes no textarea, Save, Clear, Edit, Submit, reopen, or delete control. `Create
another Attempt` explicitly creates a separate DRAFT and then opens that new Attempt detail. The create
operation remains subject to the current published-Activity and enrollment authorization required by
ADR-0008; historical read access does not grant creation access. The action does not change or
designate the submitted Attempt as current, final, or best.

The Result is absent in SUBMITTED state and no score placeholder is shown.

### REVIEWED state

A REVIEWED detail displays:

- REVIEWED status;
- the immutable submission as normal read-only text or preformatted text;
- an AssessmentResult card.

The Result card displays the integer score as:

```text
score / max_score
```

When `feedback` is non-null, the card displays its plain text. When `feedback` is `null`, no feedback
section, placeholder, or inferred message is rendered.

The UI exposes no Attempt editor, Save, Clear, Edit, Submit, reopen, delete, Result correction, grading,
or Progress control in REVIEWED state. The Student cannot infer pass/fail, Activity completion, or
Course completion from the Result.

### REVIEWED Attempt without Result

A REVIEWED Attempt without its required Result is an inconsistent backend state. The UI must:

- keep the immutable submission and REVIEWED status visible;
- display `Result unavailable` instead of a fabricated or partial Result;
- provide Retry for the Result/detail read.

Retry repeats the read only. It does not create a Result, change Attempt status, calculate a score,
submit again, or invoke any recovery mutation.

### Historical Attempts

The UI is detail-only by known Attempt identifier. No Assessment history page, Attempt list, ordering,
pagination, latest/current Attempt selector, or best/final Attempt designation is introduced.

A detail reached with a known SUBMITTED or REVIEWED Attempt identifier remains compatible with
ADR-0008 historical authorization and must not be hidden in the frontend merely because current Course
publication or enrollment has changed. The frontend does not attempt to reproduce backend
authorization rules.

### Read-only controls

For SUBMITTED and REVIEWED Attempts, submission is rendered as normal text or preformatted text rather
than as a disabled editor. Mutation controls for that existing Attempt are absent rather than disabled.

The `Create another Attempt` action in SUBMITTED state creates a different Attempt and is not a
mutation control for the read-only Attempt.

### Error states

The Assessment module maps normalized API errors to the following feature behavior:

```text
404 → Assessment Attempt not found
403 → Assessment access denied
422 → inline validation error
unexpected/5xx → retryable Assessment error
```

A retryable Assessment read error provides a Retry action.

The UI must not infer mutation success from an unexpected error.
Retry semantics for mutations are deferred to the Student Assessment API contract.

The UI must not treat 403, 404, validation failure, or an unexpected backend failure as an empty
successful state. Existing application-level authentication/session behavior remains owned by the
Identity/application shell contract and is not redefined here.

### Student Assessment HTTP API sequencing

The required milestone order is:

```text
ADR-0009
→ Student Assessment API decision/contract
→ Student Assessment API implementation
→ Student Assessment UI implementation
```

No Student Assessment UI implementation begins against an invented or mocked production contract. A
separate milestone must first define and implement the Student Assessment HTTP API required for:

- explicit DRAFT creation;
- DRAFT replacement/clearing;
- submit;
- ownership-scoped aggregate detail read;
- the approved current and historical authorization behavior;
- normalized error/status mapping required by this UI contract.

The API milestone must be complete before the Student Assessment UI implementation milestone. This ADR
does not define endpoint paths, request/response DTOs, or route parameters.

## Invariants

```text
Activity page
→ Assessment CTA
→ Assessment-owned flow
→ dedicated Attempt detail

Create DRAFT
→ explicit Student action
→ never automatic

DRAFT
→ textarea
→ explicit Save
→ empty/whitespace Save may persist null
→ meaningful client validation
→ confirmation before submit

SUBMITTED
→ read-only status and submission
→ no mutation controls for existing Attempt
→ Result absent
→ Create another Attempt creates a new DRAFT

REVIEWED
→ read-only status and submission
→ Result card shows score / max_score
→ feedback shown only when non-null
→ no Attempt or Result mutation controls

REVIEWED without Result
→ submission remains visible
→ Result unavailable
→ read Retry only

Historical UI
→ detail by known Attempt ID only
→ no list/history/current/final/best semantics

Frontend ownership
→ modules/assessment owns Assessment UI logic
→ modules/learning consumes only a minimal public integration interface

Student Assessment API
→ separate milestone before UI implementation
```

## Alternatives

### Inline Assessment editor on the Activity page

Rejected. The Activity page is the discovery point, while Attempt interaction uses a dedicated detail
experience owned by the Assessment module.

### Automatic DRAFT creation

Rejected. DRAFT creation requires an explicit Student action and must not occur merely because a page
or panel is opened.

### Autosave or implicit submission replacement

Rejected. The textarea uses explicit Save, including explicit clearing to `null`.

### Immediate submit without confirmation

Rejected. Meaningful-content validation and confirmation precede the submit request.

### Editable SUBMITTED or REVIEWED presentation

Rejected by the Attempt lifecycle. Existing submitted and reviewed Attempts expose no mutation
controls.

### Show placeholder feedback

Rejected. Null feedback is omitted from the Result card.

### Hide the whole Attempt when Result is missing

Rejected. The historical submission remains visible with `Result unavailable` and read Retry.

### Attempt history/list

Rejected for this UI milestone. Historical navigation is detail-only by known Attempt identifier.

### Disabled editor for read-only states

Rejected. Immutable submissions use normal text/pre presentation and omit mutation controls.

### Implement Assessment UI inside Learning

Rejected. Assessment owns its frontend feature logic; Learning consumes only an explicit public
integration boundary.

### Implement UI before an HTTP API contract

Rejected. The separate Student Assessment API milestone precedes UI implementation.

## Consequences

- Student Activity remains the Assessment discovery surface without becoming the owner of Assessment
  UI logic.
- Dedicated Attempt detail keeps DRAFT, SUBMITTED, REVIEWED, and Result presentation in the Assessment
  frontend module.
- Explicit Save and submit confirmation make persistence and the irreversible submit transition
  visible to the Student.
- SUBMITTED supports explicit resubmission by creating a separate DRAFT without introducing current or
  best Attempt semantics.
- REVIEWED Result presentation remains limited to the approved score, maximum score, and optional
  feedback.
- Missing Result handling preserves historical submission visibility without inventing recovery or
  scoring behavior.
- Detail-only history avoids new collection, ordering, and pagination contracts, but the UI cannot
  provide general historical discovery.
- Status-specific error presentation depends on an API contract that preserves the required HTTP/error
  distinctions.
- A new Assessment frontend module extends the ADR-0002 module inventory while preserving the approved
  app → modules → shared dependency direction.
- At least two separate future milestones are required: Student Assessment API first, then Student
  Assessment UI.

## Non-goals

This decision does not implement or authorize:

- frontend code;
- backend services or HTTP endpoints;
- database migrations;
- new domain fields or lifecycle states;
- AssessmentResult semantic changes;
- ActivityProgress changes or authorization;
- Attempt history/list, ordering, or pagination;
- current, best, or final Attempt semantics;
- new permissions;
- direct Assessment access to Education or Learning persistence;
- JSON submission, attachments, or structured submission editors.
