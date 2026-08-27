# ADR-0007 — Assessment Result Semantics

- **Status:** Accepted
- **Date:** 2026-08-27
- **Issue:** EDU-060 / #119
- **Decision:** Define the concrete MVP scoring, feedback, correction, lifecycle, deletion, authorization, and audit semantics for `AssessmentResult` before the next implementation milestone.

## Context

ADR-0006 defines Assessment as the bounded context that owns `AssessmentResult`, numerical scoring,
and feedback. It establishes that an authorized Teacher creates exactly one Result while reviewing a
submitted Attempt and may later correct that existing Result. It also excludes passing scores, Result
lifecycle states, physical Result deletion, correction history, and Activity Progress coupling.

EDU-059 implemented only the Result foundation:

```text
AssessmentResult
├── id
└── attempt_id
```

and the atomic lifecycle operation:

```text
SUBMITTED Attempt
→ REVIEWED Attempt
→ exactly one AssessmentResult
```

Concrete scoring field types, feedback normalization, correctable fields, named-permission policy, and
audit metadata were deliberately deferred. Those semantics must be fixed before Result scoring,
feedback, or correction is implemented. This ADR narrows ADR-0006 without changing it.

## Decision

### Result model

The approved MVP business model is:

```text
AssessmentResult
├── id
├── attempt_id
├── score
├── max_score
└── feedback
```

The field contract is:

| Field | Type | Nullability | Mutability | Teacher correction |
|---|---|---|---|---|
| `id` | UUID | required | immutable | forbidden |
| `attempt_id` | UUID | required and unique | immutable | forbidden |
| `score` | integer | required | mutable only through authorized correction | allowed |
| `max_score` | integer | required | immutable Result snapshot | forbidden |
| `feedback` | plain text | optional | mutable only through authorized correction | allowed, including clearing to `null` |

No other business or audit fields are part of the next implementation milestone.

### Scoring

Scoring uses integers. Decimal, fixed-point, and floating-point score representations are not used.
Every Result must satisfy:

```text
max_score > 0
0 <= score <= max_score
```

`score` and `max_score` are owned by Assessment and stored on the Result. `max_score` is captured when
the Result is created and remains unchanged for the lifetime of that Result.

There is no `passing_score`, pass/fail state, separate Grade aggregate, best-score selection, or
automatic score calculation. A score does not imply Activity or Course completion.

### Feedback

`feedback` is optional plain text with no maximum length in this milestone.

Empty or whitespace-only feedback is normalized to `null` on Result creation and correction. An
authorized Teacher may replace non-empty feedback or clear existing feedback back to `null`.

No structured rubric, feedback categories, private notes, comment thread, generated feedback, or
feedback history is introduced.

### Teacher correction

An authorized Teacher may correct only:

```text
score
feedback
```

Correction updates the existing Result:

```text
existing AssessmentResult
→ same id
→ same attempt_id
→ same max_score
→ score may change
→ feedback may change or become null
→ no second AssessmentResult
→ no new AssessmentAttempt
→ Attempt remains REVIEWED
```

The corrected score must satisfy the Result's original `max_score` invariant. Correction does not
reopen, replace, or otherwise mutate the reviewed Attempt.

### Result lifecycle

AssessmentResult has no lifecycle or status beyond existence. Creation is part of the atomic
`SUBMITTED → REVIEWED` operation. Correction is an update to that Result, not a lifecycle transition.
No draft, published, corrected, superseded, deleted, or archived Result state is introduced.

### Deletion

AssessmentResults are not physically deleted in MVP. A Result associated with a REVIEWED Attempt is
retained. No Result delete operation, soft-delete flag, tombstone, restoration flow, or archival state
is introduced.

### Teacher authorization boundary

Result creation and correction use the existing approved Teacher authorization boundary:

```text
Teacher Space ownership
        +
Education Activity scope
        ↓
Assessment Result operation
```

Teacher Space remains the application orchestrator. It verifies that `teacher_id` owns
`teacher_space_id`, asks Education whether `activity_id` belongs to that Teacher Space, and invokes the
Assessment application operation only after both checks allow it.

No named review or correction permission is added. This decision grants no global or cross-owner
Teacher access. Teacher Space and Education do not access Assessment persistence, and Assessment does
not access Teacher Space or Education private persistence.

### Audit and versioning

The next implementation milestone does not add:

```text
assessed_at
assessed_by
updated_at
updated_by
```

It also does not add correction history, Result versions, an audit entity, or an audit trail. A
correction replaces the existing `score` and/or `feedback` values without retaining prior values.

### Learning Progress boundary

AssessmentResult creation and correction remain independent from Learning Activity Progress. Neither
operation creates or updates `ActivityProgress`, regardless of the score.

## Invariants

```text
AssessmentResult fields
= id + attempt_id + score + max_score + feedback

score: integer
max_score: integer
max_score > 0
0 <= score <= max_score

feedback is null or plain text
empty/whitespace-only feedback → null

one Attempt → at most one Result
Result creation requires SUBMITTED Attempt
successful review → REVIEWED Attempt + exactly one Result

Result correction
→ same Result.id
→ same attempt_id
→ same max_score
→ score and feedback only may change
→ no second Result
→ no new Attempt
→ Attempt remains REVIEWED

Result has no status
Result is not physically deleted
Result does not mutate ActivityProgress
```

## Alternatives

### Decimal or fixed-point scoring

Rejected for this milestone. Integer scoring is the approved representation.

### Mutable `max_score`

Rejected. `max_score` is an immutable snapshot recorded when the Result is created.

### Passing score, pass/fail, or Grade

Rejected by ADR-0006. These semantics are not inferred from `score` and `max_score`.

### Required, length-limited, or structured feedback

Rejected for this milestone. Feedback is optional, unlimited plain text with blank input normalized to
`null`.

### Result lifecycle states

Rejected. Existence represents a completed review, and correction does not add a state transition.

### Physical or soft deletion

Rejected for MVP. Results attached to reviewed Attempts are retained.

### Named review/correction permissions

Rejected for this milestone. Existing Teacher Space ownership and Education Activity scope remain the
authorization contract.

### Audit fields, correction history, or versioning

Rejected for the next implementation milestone. Prior Result values are not retained.

## Consequences

- Result scoring has deterministic integer validation and no rounding policy.
- `max_score` remains a stable assessment snapshot across later corrections.
- Teachers can correct scoring mistakes and replace or clear feedback without creating another Result
  or Attempt.
- Consumers cannot derive pass/fail, Activity completion, or Course completion from a Result.
- Result correction is destructive with respect to previous score and feedback values because no
  history or audit metadata is stored.
- The model cannot answer who assessed or corrected a Result, or when those operations occurred.
- Unlimited feedback requires no product-level length validation in this milestone.
- Assessment ownership and existing Teacher/Education authorization boundaries remain unchanged.

## Next implementation milestone scope

A separately authorized implementation Issue may:

- extend the AssessmentResult domain contract with required integer `score`, required integer
  `max_score`, and optional normalized `feedback`;
- enforce `max_score > 0` and `0 <= score <= max_score` on creation and correction;
- persist the approved fields in Assessment-owned storage while preserving unique `attempt_id`;
- require score and max_score when the authorized Teacher completes review;
- add authorized Teacher correction of only score and feedback on the existing Result;
- preserve Result `id`, `attempt_id`, and `max_score` during correction;
- keep the associated Attempt REVIEWED and create neither another Result nor another Attempt;
- use the existing Teacher Space ownership and Education Activity-scope orchestration;
- add domain, application, persistence, transaction, authorization, and boundary tests for the approved
  invariants.

The implementation Issue must not invent score defaults for any pre-existing foundation rows. If a
data-migration policy is required for existing Results, that policy must be approved explicitly before
implementation.

The next implementation milestone must not add:

- public HTTP APIs or frontend UI unless separately authorized;
- `passing_score`, pass/fail, Grade, decimal scores, or automated grading;
- additional Result fields or lifecycle states;
- mutable `max_score`;
- Result deletion;
- audit metadata, history, versioning, or audit entities;
- ActivityProgress or Course-completion changes;
- changes to ADR-0006 or bounded-context ownership.
