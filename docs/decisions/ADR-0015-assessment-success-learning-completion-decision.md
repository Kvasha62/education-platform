# ADR-0015 — Assessment Success & Learning Completion Decision

- **Status:** Proposed
- **Date:** 2026-08-27
- **Issue:** EDU-077
- **Decision:** Assessment success and Learning completion remain independent in the MVP. `AssessmentResult → ActivityProgress` and `AssessmentResult → Course completion` are forbidden for the current product model. Any future coupling is deferred and requires an explicit product + architecture decision and an approved application/integration boundary.

## Context

Assessment and Learning are separate bounded contexts. Assessment owns `AssessmentDefinition`, `AssessmentAttempt`, and `AssessmentResult`; Learning owns `ActivityProgress` and Course progress. Accepted ADR-0006 deliberately separates assessment outcomes from learning progress.

EDU-077 resolves whether that separation should change for the MVP and, if not, records the conditions under which a future product decision could introduce a controlled integration.

## Problem

The platform needs an explicit answer to whether an assessment result means that an Activity or Course has been completed. Without a decision, implementation work could incorrectly infer that a high score, a reviewed attempt, or an archived assessment definition changes Learning state.

The MVP currently has no approved concept of an assessment "pass" or "success" and no authoritative selection among multiple attempts. A Result represents the completed manual review of one specific Attempt.

## Decision

For the current MVP:

```text
AssessmentResult → ActivityProgress = FORBIDDEN
AssessmentResult → Course completion = FORBIDDEN
```

Assessment success is **not a persisted domain concept** in the MVP. `REVIEWED` means that Teacher review is complete; it does not mean that the Activity has been completed.

A numerical score does not imply success, passing, Activity completion, or Course completion. In particular:

```text
score == max_score
        ≠
ActivityProgress.COMPLETED
```

The relationship between Assessment and Learning completion is **DEFERRED** for future product/architecture work. No future coupling may be introduced implicitly by an implementation Issue.

## Decision table

| # | Question | MVP decision |
|---|---|---|
| 1 | Is there an Assessment success concept? | No persisted success/pass concept. A Result represents completed manual review. |
| 2 | Is `passing_score` required? | No. It remains outside the MVP domain model. |
| 3 | Is Assessment required for Activity completion? | No. Assessment is optional and independent of Learning completion. |
| 4 | Can an Activity be completed without Assessment? | Yes. Activities without a Definition/Attempt/Result remain valid. |
| 5 | Which Result is authoritative among multiple Attempts? | None in MVP. The domain does not designate a current, final, best, or passing Attempt. |
| 6 | What happens after Teacher correction? | The existing Result is corrected in place. Attempt remains `REVIEWED`; no new Result or Attempt is created. |
| 7 | Can correction undo Activity completion? | No. Assessment correction never changes `ActivityProgress`; there is no Assessment-derived completion to undo. |
| 8 | What does `AssessmentDefinition = ARCHIVED` mean for Progress? | Nothing. Archival blocks new Attempts and preserves existing Attempts/Results; it has no Progress effect. |
| 9 | What about Activities without Assessment? | They remain valid; Learning Progress is independent of Assessment. |
| 10 | Can Assessment directly affect Course completion? | No. Course completion remains a Learning-owned aggregation. |
| 11 | Who owns `ActivityProgress`? | Learning. |
| 12 | What boundary would a future integration use? | An application/integration boundary: Assessment operation/result → approved orchestration use case → Learning-owned application boundary → `ActivityProgress`. |
| 13 | Is implementation required now? | No. A separate implementation EDU is required only after an explicit product + architecture decision authorizes coupling. |

## Assessment success semantics

The MVP deliberately avoids a separate success state.

The current lifecycle is:

```text
DRAFT → SUBMITTED → REVIEWED
```

`REVIEWED` means that the Teacher has completed assessment of that Attempt and created its single Result. It does not establish that the Student has satisfied a passing threshold or completed the Activity.

The existing scoring constraints remain those defined by ADR-0006/0007:

```text
max_score > 0
0 <= score <= max_score
```

No passing threshold is inferred from these constraints.

## Multiple Attempts

Students may have multiple Attempts. MVP intentionally does not designate one Attempt as authoritative for Activity completion because Assessment has no Activity-completion responsibility.

There is therefore no persisted:

- `current_attempt`;
- `final_attempt`;
- `best_attempt`;
- `passing_attempt`;
- maximum-attempt selection.

A future product decision must explicitly define selection semantics before any Progress integration can be implemented.

## Teacher correction

Teacher correction updates the existing `AssessmentResult` in place, consistent with ADR-0006.

Correction does not:

- create another Result;
- create another Attempt;
- change Attempt state away from `REVIEWED`;
- create or update `ActivityProgress`;
- create or update Course completion.

Therefore the MVP has no Assessment-driven completion state that correction could retract.

## AssessmentDefinition archival

ADR-0008 and the Assessment domain lifecycle remain authoritative.

```text
ACTIVE → ARCHIVED
```

Archival makes the Definition immutable and prevents new Attempts. Existing Attempts and Results remain available according to their existing authorization/read rules. Archival does not alter Learning Progress and does not reinterpret historical Results.

An existing DRAFT Attempt retains the behavior already approved by ADR-0008; this ADR does not change that lifecycle rule.

## Activities without Assessment

An Activity may have no `AssessmentDefinition`. This is a valid state and does not prevent Learning from tracking its own Activity Progress.

The absence of Assessment means only that Assessment-specific operations are unavailable for that Activity. It does not imply `COMPLETED`, `IN_PROGRESS`, or any other Progress state.

## Course completion

Assessment has no direct Course-completion semantics in the MVP.

Course completion remains a Learning concern derived from Learning-owned completion rules. Assessment does not bypass that aggregation and does not write Course Progress.

## Ownership and future integration boundary

Learning remains the sole owner of `ActivityProgress`.

If a future product decision authorizes Assessment-derived completion, the preferred boundary is:

```text
Assessment
   │
   │ approved result/domain fact
   ▼
Orchestration application use case
   │
   ▼
Learning application boundary
   │
   ▼
ActivityProgress
```

The following shapes remain forbidden:

```text
Assessment → Learning repository
Assessment → ActivityProgress persistence
Assessment → Learning ORM/model
Assessment → direct CourseProgress persistence
```

The integration must be explicit, testable, and owned by an approved application boundary. The future implementation must also define success criteria, authoritative Attempt/Result selection, correction/retraction semantics, idempotency, failure handling, and consistency guarantees before runtime coupling is introduced.

## Relationship to existing ADRs

### ADR-0006 — Assessment & Submission Domain Model

This ADR preserves the accepted rule that Assessment outcomes and Learning Progress are independent in the MVP. No domain ownership is moved and no AssessmentResult → ActivityProgress mutation is introduced.

### ADR-0007 — Assessment Result Semantics

This ADR does not add pass/fail semantics or `passing_score`. Existing score/max-score semantics remain unchanged.

### ADR-0008 — Student Assessment Submission Contract

This ADR preserves archived-Definition behavior and existing Attempt lifecycle semantics. It does not change submission eligibility or DRAFT/SUBMITTED/REVIEWED transitions.

### ADR-0014 — Teacher AssessmentDefinition Management Contract

Teacher Definition management does not acquire any Progress-completion responsibility. CREATE/PATCH/ARCHIVE operations remain AssessmentDefinition operations only.

## Alternatives considered

### Automatically complete Activity on `REVIEWED`

Rejected. Review completion is an Assessment lifecycle fact, not a Learning completion rule.

### Automatically complete Activity when `score == max_score`

Rejected. A perfect score has no approved product meaning of Activity completion, and ADR-0007 does not define passing semantics.

### Introduce `passing_score` now

Rejected. This would expand the Assessment domain beyond the accepted MVP semantics and requires an explicit product decision.

### Select the best or latest Attempt automatically

Rejected. MVP intentionally has no authoritative Attempt selection and does not need one while Assessment remains independent of Progress.

### Let Assessment write Learning persistence directly

Rejected architecturally. It would violate bounded-context ownership and create coupling to Learning persistence.

## Consequences

- Assessment and Learning retain clear bounded-context ownership.
- A reviewed assessment is not silently treated as completed learning.
- Activities can use Assessment or omit it without changing Learning semantics.
- Multiple Attempts remain historical Assessment data without an artificial authoritative selection.
- Teacher correction remains local to Assessment.
- Definition archival remains local to Assessment and does not alter Progress.
- No runtime integration, event bus, repository coupling, migration, or API changes are required by EDU-077.
- Future coupling, if desired, will require a new explicit product and architecture decision rather than an implementation assumption.

## Implementation boundary

**EDU-077 requires no implementation.**

If the product later requires Assessment-derived Activity completion, create a separate architecture/implementation milestone only after the following are explicitly approved:

1. success/pass definition;
2. authoritative Attempt/Result selection;
3. correction and retraction semantics;
4. Activity completion ownership and orchestration;
5. Learning application boundary;
6. consistency/idempotency/failure semantics;
7. Course-completion implications;
8. required API/domain/persistence changes.

Until those decisions exist, `AssessmentResult → ActivityProgress` remains forbidden.

## Non-goals

EDU-077 does not:

- modify `AssessmentResult`;
- modify `AssessmentAttempt`;
- modify `AssessmentDefinition`;
- add `passing_score`;
- modify `ActivityProgress`;
- modify Course Progress or Course completion;
- add HTTP endpoints;
- add database tables or migrations;
- change frontend behavior;
- implement events or integration handlers;
- alter Assessment or Definition lifecycle;
- alter existing authorization semantics.

## Open follow-up

No implementation EDU is required from this decision alone.

If product requirements later establish that an assessment must control learning completion, the next architecture milestone must explicitly amend this decision before runtime implementation begins.
