# ADR-0016 — Teacher Course Publishing Readiness

- **Status:** Proposed
- **Date:** 2026-08-28
- **Issue:** EDU-078 / #147
- **Decision:** A Course is publication-ready only when its Education-owned hierarchy is structurally complete and every Activity has at least one Content item that the approved Content publication/availability boundary exposes as suitable for Student consumption. Assessment and Learning participation are not publication prerequisites.

## Context

Education owns `EducationalEnvironment`, `Course`, `Section`, `LearningUnit`, and `Activity`. Content owns Content publication and availability. ADR-0005 makes Course publication the boundary for Activity visibility, while Content availability remains independent. The current Course domain supports `DRAFT → PUBLISHED → ARCHIVED`; its existing `publish()` transition does not evaluate publication readiness.

EDU-078 defines the product and architecture rule before enforcement is implemented.

## Decision

### 1. Structural readiness

A Course must contain at least one Section. Every Section must contain at least one Learning Unit. Every Learning Unit must contain at least one Activity.

Therefore:

| Structure | Result |
|---|---|
| Empty Course | NOT READY |
| Course without Sections | NOT READY |
| Section without Learning Units | NOT READY |
| Learning Unit without Activities | NOT READY |
| Complete hierarchy | structurally READY |

No additional minimum count is imposed.

### 2. Activity Content readiness

Every Activity must have at least one associated Content item that the approved Content public/application boundary identifies as valid for Student consumption.

For the current approved integration semantics, required Content must be published and student-available. A DRAFT, unavailable, missing, or stale Content association does not satisfy readiness.

Content's own body publishability remains authoritative. Education must not duplicate Content-body validation or access Content private persistence.

### 3. Assessment

Assessment is not required for Course publication. An Activity may have no `AssessmentDefinition`. Definition status, Attempts, and Results do not affect publication readiness.

This preserves ADR-0006 and ADR-0015:

```text
AssessmentResult → ActivityProgress = FORBIDDEN
AssessmentResult → Course completion = FORBIDDEN
```

No passing score, assessment success state, or assessment-derived completion is introduced.

### 4. Learning and Enrollment

Publishing readiness is independent of Student participation. Enrollment, `ActivityProgress`, Course Progress, Course completion, and Student assessment results are not readiness prerequisites.

Learning owns participation and progress. Education publication must not query or mutate Learning persistence to determine readiness.

### 5. Teacher Space

The existing Teacher Space lifecycle policy remains authoritative:

- ACTIVE Teacher Space permits authorized publishing operations;
- DISABLED Teacher Space is read-only and rejects mutations.

EDU-078 introduces no new authorization model.

### 6. Readiness result

The readiness policy has a conceptual binary result:

```text
READY
NOT_READY
```

`READY` means every normative publication condition is satisfied. `NOT_READY` means at least one required condition is not satisfied. This is an evaluation result, not a persisted Course lifecycle state.

EDU-078 does not prescribe a new HTTP error envelope or semantic error-code system.

### 7. Ownership

Publishing readiness is an Education application policy. It composes Education-owned structural checks with the approved Content public/application read boundary.

```text
Teacher Space
    ↓
Education application / Course publication use case
    ├── Education structural readiness
    └── Content public/application read boundary
```

The HTTP router maps transport concerns and does not own the educational readiness policy. Existing domain entities retain their own invariants.

### 8. Publication-time consistency

Readiness is evaluated against the Course state observed by the publication operation. The future implementation must not commit a published Course when a required readiness condition is invalidated within the publication transaction boundary.

No new transaction or concurrency abstraction is introduced by this ADR; the implementation must follow existing repository conventions.

### 9. Published Course immutability

The existing architecture defines a `PUBLISHED` Course and its educational structure as read-only through teacher-facing mutation APIs. EDU-078 does not change that rule.

After publication, Course, Section, Learning Unit, Activity, and Activity ↔ Content association mutations remain forbidden through the teacher-facing Education mutation surface.

Course revisions, republishing, scheduling, or editable published structures require a separate architecture decision.

### 10. Archive interaction

`PUBLISHED → ARCHIVED` remains the existing Course lifecycle transition. Archived Courses are outside Student-visible published Course scope under ADR-0005. EDU-078 does not change archival semantics.

## Normative readiness predicate

A Course is `READY` for publication if and only if all conditions hold at publication time:

```text
Course.status = DRAFT
AND
Course has ≥ 1 Section
AND
Every Section has ≥ 1 Learning Unit
AND
Every Learning Unit has ≥ 1 Activity
AND
Every Activity has ≥ 1 associated Content item
AND
Every required associated Content item is valid for Student consumption
```

Under the approved Content publication/availability semantics, that final condition means the required Content is published and student-available.

Otherwise:

```text
NOT READY
```

No other prerequisite is introduced by this ADR.

## Decision table

| Condition | Required? | Owner / source |
|---|---:|---|
| Course is DRAFT | Yes | Education Course lifecycle |
| At least one Section | Yes | Education |
| Every Section has a Learning Unit | Yes | Education |
| Every Learning Unit has an Activity | Yes | Education |
| Every Activity has Content | Yes | Education Activity/Content association |
| Required Content is valid for Student consumption | Yes | Content public/application boundary |
| AssessmentDefinition exists | No | Assessment |
| AssessmentDefinition is ACTIVE | No | Assessment |
| AssessmentAttempt exists | No | Assessment |
| AssessmentResult exists | No | Assessment |
| Assessment success/pass exists | No | Assessment / ADR-0015 |
| Student Enrollment exists | No | Learning |
| ActivityProgress exists | No | Learning |
| Course Progress exists | No | Learning |
| Course completion exists | No | Learning |

## Consequences

- Course publication has one deterministic readiness predicate.
- Structurally incomplete Courses are not publication-ready.
- Published Courses require valid Student-consumable Content for every Activity.
- Content publication remains owned by Content.
- Assessment remains optional and independent from Course publication.
- Learning Progress and Enrollment remain outside the publishing boundary.
- Existing published Course immutability remains unchanged.
- A future implementation can enforce this predicate without inventing a new lifecycle state.

## Rejected alternatives

### Publish an empty Course

Rejected. The published Course is the Student-visible boundary for its Activities, and a structurally empty Course is not publication-ready.

### Require only one non-empty Activity

Rejected. The Course model explicitly represents Section and Learning Unit hierarchy; readiness validates every required level.

### Allow Activities without Student-consumable Content

Rejected. A Student-visible Activity without valid Student-consumable material is not publication-ready under the approved Course/Content integration boundary.

### Require Assessment for every Activity

Rejected. Assessment is optional and independent under ADR-0006 and ADR-0015.

### Use Enrollment or Progress as readiness input

Rejected. Publication is an Education authoring concern; Learning owns participation and progress.

### Put readiness logic in the HTTP router

Rejected. Readiness is application policy, not transport mapping.

### Persist a Course READY state

Rejected for MVP. `READY`/`NOT_READY` is an evaluation result, not a new Course lifecycle state.

### Dynamically mutate a published Course when Content changes

Rejected. Published Course educational structure is already immutable through teacher-facing mutation APIs. Dynamic composition requires a separate architecture decision.

## Relationship to existing ADRs

### ADR-0004 — Content Body and Editor Architecture

Content remains responsible for body validation and publishability. Education consumes Content readiness through a public boundary.

### ADR-0005 — Activity Publication and Student Visibility

Course publication remains the authoritative Activity visibility boundary. EDU-078 adds prerequisites before entering that boundary and introduces no Activity lifecycle.

### ADR-0006 — Assessment & Submission Domain Model

Assessment remains independent from Learning Progress and is not a Course publication prerequisite.

### ADR-0008 — Student Assessment Submission Contract

AssessmentDefinition archival and Attempt lifecycle remain unchanged. Publication does not require an Attempt or Result.

### ADR-0014 — Teacher AssessmentDefinition Management Contract

Teacher Definition management remains an Assessment concern. Definition existence/status does not become a Course publication prerequisite.

### ADR-0015 — Assessment Success & Learning Completion Decision

Assessment success remains outside Course publication readiness. No AssessmentResult → ActivityProgress or Course completion coupling is introduced.

## Implementation boundary

EDU-078 is decision-only and requires no production implementation.

A future implementation EDU may enforce the readiness predicate during Course publication. That implementation must define concrete application/API behavior, failure representation, transaction/concurrency behavior, tests, and any required public Content read boundary while preserving this decision.

The implementation EDU must not reinterpret the predicate or add product prerequisites without a new architectural/product decision.

## Non-goals

EDU-078 does not:

- implement Course publication enforcement;
- add Course readiness persistence or a `READY` status;
- modify Course lifecycle states;
- modify Section, LearningUnit, Activity, or Content lifecycle states;
- change Assessment semantics;
- connect AssessmentResult to ActivityProgress or Course completion;
- modify Enrollment or Learning Progress;
- add authentication or authorization mechanisms;
- add HTTP endpoints;
- add database tables or migrations;
- implement Course versioning, revisions, republishing, scheduling, or draft copies.

## Open follow-up

If product work confirms that publication enforcement is required, the next implementation milestone should enforce the normative predicate above without changing its meaning.
