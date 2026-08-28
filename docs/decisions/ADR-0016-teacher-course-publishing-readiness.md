# ADR-0016 — Teacher Course Publishing Readiness

- **Status:** Proposed
- **Date:** 2026-08-28
- **Issue:** EDU-078 / #147
- **Decision:** Course publication readiness is defined by the Education-owned Course structure and the publication validity of its associated Content. A Course must contain at least one Section, each Section must contain at least one Learning Unit, each Learning Unit must contain at least one Activity, and every Activity must have at least one associated Content item that is PUBLISHED and student-available. Assessment, Enrollment, ActivityProgress, and Course completion are not publication-readiness requirements.

## Context

The Education Engine owns `EducationalEnvironment`, `Course`, `Section`, `LearningUnit`, and `Activity`. The Content Engine owns Content and its publication/availability state. A Course is the publication boundary for Activity visibility: ADR-0005 establishes that every Activity belonging to a `PUBLISHED` Course is Student-visible, while Content availability remains a separate concern.

The current Course domain supports `DRAFT → PUBLISHED → ARCHIVED`, and the current `Course.publish()` transition does not itself evaluate whether the educational structure or associated Content is ready. EDU-078 defines the product and architectural readiness rule before any enforcement implementation is attempted.

ADR-0006 and ADR-0015 keep Assessment independent from Learning completion. ADR-0004/ADR-0005 and the current Content model establish that Content has its own publishability and publication lifecycle.

## Decision

### Course structure

A Course is publishable only when its educational hierarchy is non-empty at every required level:

```text
Course
└── at least 1 Section
    └── each Section has at least 1 Learning Unit
        └── each Learning Unit has at least 1 Activity
```

Thus an empty Course, a Course with no Sections, a Section with no Learning Units, or a Learning Unit with no Activities is NOT READY. No additional minimum count is imposed.

### Activity and Content

Every Activity in the Course must have at least one associated Content item that is valid for Student consumption. Under the current Content contract, the required Content is `PUBLISHED` and student-available.

A DRAFT, unavailable, missing, or stale Content association does not satisfy publishing readiness.

Content's own body validation remains authoritative. Education must not duplicate Content-body validation or access Content private persistence.

### Assessment

Assessment is not required for Course publication. An Activity may be published without an `AssessmentDefinition`; Definition existence or archival state, Attempts, and Results do not affect publication readiness.

This preserves ADR-0006 and ADR-0015:

```text
AssessmentResult → ActivityProgress = FORBIDDEN
AssessmentResult → Course completion = FORBIDDEN
```

No passing score, assessment success state, or assessment-derived completion is introduced.

### Learning and Enrollment

Publishing readiness is independent of Student participation. Enrollment, ActivityProgress, Course Progress, Course completion, and Student assessment results are not readiness prerequisites.

Learning remains responsible for enrollment and progress. Education publication must not query or mutate Learning persistence to determine readiness.

### Teacher Space

The existing Teacher Space lifecycle policy remains authoritative:

- ACTIVE Teacher Space permits authorized publishing operations;
- DISABLED Teacher Space is read-only and rejects mutations.

EDU-078 introduces no new authorization model.

### Readiness result

The policy has a conceptual binary result:

```text
READY
NOT_READY
```

`READY` means every normative publication condition is satisfied. `NOT_READY` means at least one required condition is not satisfied. EDU-078 does not prescribe a new HTTP error envelope or semantic error-code system.

Readiness evaluation is non-mutating.

### Ownership

Publishing readiness is an Education application policy. It composes Education-owned structural checks with the Content public/application read boundary.

```text
Teacher Space
    ↓
Education application / Course publication use case
    ├── Education structural readiness
    └── Content public/application read boundary
```

The HTTP router maps transport concerns and does not own the educational readiness policy. Existing domain invariants remain in the relevant domain entities.

### Publication-time snapshot

Readiness is evaluated against the Course state observed by the publication operation. The implementation must not commit a published Course when a required readiness condition observed by that operation has been invalidated within the same publication transaction boundary.

No new transaction abstraction or concurrency mechanism is prescribed; the implementation EDU must follow existing repository conventions.

### Published Course immutability

The existing architecture defines `PUBLISHED` Course and its educational structure as read-only through teacher-facing mutation APIs. EDU-078 does not change that rule.

After publication, Course, Section, Learning Unit, Activity, and Activity ↔ Content association mutations remain forbidden through the teacher-facing Education mutation surface.

Course revisions, republishing, scheduling, or editable published structures require a separate architecture decision.

### Archive interaction

`PUBLISHED → ARCHIVED` remains the existing Course lifecycle transition. Archived Courses are outside Student-visible published Course scope under ADR-0005. EDU-078 does not change archival semantics.

## Normative readiness predicate

A Course is `READY` for publication if and only if all of the following are true at publication time:

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
Every required associated Content item is PUBLISHED
AND
Every required associated Content item is student-available
```

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
| Required Content is PUBLISHED | Yes | Content |
| Required Content is student-available | Yes | Content |
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
- Published Courses cannot contain Activities without valid Student-available Content.
- Content publication remains owned by Content.
- Assessment remains optional and independent from Course publication.
- Learning Progress and Enrollment remain outside the publishing boundary.
- Existing published Course immutability remains unchanged.
- A future implementation can enforce this predicate without inventing new lifecycle states.

## Rejected alternatives

### Publish an empty Course

Rejected because the published Course is the Student-visible boundary for its Activities and an empty educational hierarchy is not publication-ready.

### Require only one non-empty Activity

Rejected because the Course model explicitly represents Section and Learning Unit hierarchy; readiness must validate every required level.

### Allow Activities without Student-available Content

Rejected because a Student-visible Activity without valid Student-available material is not publication-ready under the current Course/Content model.

### Require Assessment for every Activity

Rejected because Assessment is optional and independent under ADR-0006 and ADR-0015.

### Use Student Progress or Enrollment as readiness input

Rejected because publication is an authoring concern owned by Education while Learning owns participation and progress.

### Put readiness logic in the HTTP router

Rejected because readiness is application policy, not transport mapping.

### Persist a Course READY state

Rejected for MVP. `READY`/`NOT_READY` is an evaluation result, not a new Course lifecycle state.

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

A future implementation EDU may enforce the readiness predicate during Course publication. That implementation must define the concrete application/API behavior, failure representation, transaction/concurrency behavior, tests, and any required public Content read boundary while preserving this decision.

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
