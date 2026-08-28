# ADR-0016 — Teacher Course Publishing Readiness

- **Status:** Proposed
- **Date:** 2026-08-28
- **Issue:** EDU-078 / #147
- **Decision:** A Course is publication-ready when its Education-owned hierarchy is structurally complete. Content availability, Assessment, Enrollment, and Learning Progress are not Course publication prerequisites.

## Context

Education owns `EducationalEnvironment`, `Course`, `Section`, `LearningUnit`, and `Activity`. The Course lifecycle is `DRAFT → PUBLISHED → ARCHIVED`. ADR-0005 establishes that Course publication is the authoritative Student-visibility boundary for Activities and explicitly separates Activity visibility from Content availability. Therefore EDU-078 must define readiness without making Content availability a hidden Activity-visibility dependency.

## Decision

### 1. Structural readiness

A Course is structurally ready only when:

- it contains at least one Section;
- every Section contains at least one Learning Unit;
- every Learning Unit contains at least one Activity.

| Structure | Result |
|---|---|
| Empty Course | NOT READY |
| Course without Sections | NOT READY |
| Section without Learning Units | NOT READY |
| Learning Unit without Activities | NOT READY |
| Complete hierarchy | READY |

No additional structural minimum is imposed.

### 2. Content readiness

Content availability is **not** a Course publication prerequisite in the MVP.

An Activity may have zero associated Content items and the Course may still be published if the Education hierarchy is structurally ready. This preserves ADR-0005, which states that Activity visibility and Content availability are independent and that a Student-visible Activity may have zero Student-available Content items. fileciteturn793file0L2-L2

Content remains responsible for its own lifecycle, publication, and availability rules. Education must not duplicate Content rules or access Content private persistence merely to decide whether a Course may be published.

### 3. Assessment

Assessment is not required for Course publication.

`AssessmentDefinition`, `AssessmentAttempt`, and `AssessmentResult` do not participate in publication readiness. No passing score or Assessment success rule is introduced.

This preserves ADR-0015:

```text
AssessmentResult → ActivityProgress = FORBIDDEN
AssessmentResult → Course completion = FORBIDDEN
```

### 4. Learning and Enrollment

Publication readiness is independent of Student participation.

The following are not prerequisites:

- Enrollment;
- `ActivityProgress`;
- Course Progress;
- Course completion;
- Student Assessment Results.

Learning owns participation and progress. Education publication must not query or mutate Learning persistence to evaluate readiness.

### 5. Teacher Space lifecycle

The existing Teacher Space policy remains authoritative:

- ACTIVE Teacher Space permits authorized publishing operations;
- DISABLED Teacher Space is read-only and rejects mutations.

EDU-078 introduces no new authorization or lifecycle model.

### 6. Readiness result

Readiness has a conceptual binary evaluation result:

```text
READY
NOT_READY
```

This result is not persisted and is not a new Course lifecycle state.

`READY` means all structural readiness conditions are satisfied and the Course is in `DRAFT` state. `NOT_READY` means at least one required structural condition is missing.

EDU-078 does not introduce a new HTTP error envelope or semantic error-code model.

### 7. Ownership

Publishing readiness is an Education application policy composed from Education-owned structure.

```text
Teacher Space
    ↓
Education Course publication use case
    ↓
Education structural readiness policy
```

The HTTP router is responsible only for transport concerns. Content, Assessment, and Learning remain separate bounded responsibilities.

### 8. Publication-time consistency

A future publication implementation must evaluate readiness against the Course structure observed by the publication operation and must not publish a structurally invalid Course.

The implementation must follow existing repository transaction and concurrency conventions. EDU-078 introduces no new transaction abstraction.

### 9. Published Course invariants

EDU-078 does not change existing published-Course immutability.

After publication, existing teacher-facing rules governing mutations of Course, Section, Learning Unit, Activity, and their associations remain authoritative. Course revisions, republishing, scheduling, or editable published structures require a separate architectural decision.

### 10. Archive interaction

`PUBLISHED → ARCHIVED` remains the existing Course lifecycle transition. Archived Courses are outside Student-visible published Course scope under ADR-0005.

Archival does not retroactively change the meaning of publication readiness; it changes Course lifecycle state according to the existing contract.

## Normative readiness predicate

A Course is `READY` for publication if and only if:

```text
Course.status = DRAFT
AND
Course has ≥ 1 Section
AND
Every Section has ≥ 1 Learning Unit
AND
Every Learning Unit has ≥ 1 Activity
```

Otherwise:

```text
NOT READY
```

No Content, Assessment, Enrollment, Progress, or Course-completion condition is part of this predicate.

## Decision table

| Condition | Required? | Owner / source |
|---|---:|---|
| Course is DRAFT | Yes | Education Course lifecycle |
| At least one Section | Yes | Education |
| Every Section has a Learning Unit | Yes | Education |
| Every Learning Unit has an Activity | Yes | Education |
| Activity has Content | **No** | Content independent from Activity visibility |
| Content is published | **No** | Content |
| Content is Student-available | **No** | Content |
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

- There is one deterministic structural definition of Course publication readiness.
- Empty Courses, empty Sections, and empty Learning Units cannot be published as ready Courses.
- Activities may remain content-less without violating Course publication readiness.
- Content publication and availability remain independent from Activity visibility, preserving ADR-0005.
- Assessment remains optional and independent.
- Learning participation and progress remain outside the publishing boundary.
- No new lifecycle state is required.
- Future publication enforcement can be implemented without reopening the structural product decision.

## Rejected alternatives

### Publish an empty Course

Rejected. A published Course is the Student-visible boundary for its Activities, but the authoring hierarchy must contain at least one Section, one Learning Unit per Section, and one Activity per Learning Unit to be publication-ready.

### Require Content for every Activity

Rejected for MVP. This would make Content availability a publication prerequisite and conflict with ADR-0005's explicit separation of Activity visibility from Content availability. fileciteturn793file0L2-L2

### Require Assessment for every Activity

Rejected. Assessment is optional and remains independent from publication readiness.

### Use Enrollment or Progress as readiness input

Rejected. Those concepts belong to Learning and describe Student participation, not Teacher authoring readiness.

### Put readiness logic in the HTTP router

Rejected. Readiness is Education application policy.

### Persist READY as a Course status

Rejected for MVP. READY/NOT_READY is an evaluation result; Course lifecycle remains `DRAFT`, `PUBLISHED`, and `ARCHIVED`.

### Introduce Course revisions or republishing now

Rejected. Published-Course revision semantics require a separate architectural decision.

## Relationship to existing ADRs

### ADR-0005 — Activity Publication and Student Visibility

Course publication remains the authoritative Activity visibility boundary. Content availability does not determine Activity visibility. EDU-078 deliberately preserves that rule. fileciteturn793file0L2-L2

### ADR-0006 — Assessment & Submission Domain Model

Assessment remains separate from Learning Progress and is not a Course publication prerequisite.

### ADR-0008 — Student Assessment Submission Contract

AssessmentDefinition archival and Attempt behavior remain unchanged. Publication does not require an Attempt or Result.

### ADR-0014 — Teacher AssessmentDefinition Management Contract

Teacher Definition management remains an Assessment concern and does not become a Course publication prerequisite.

### ADR-0015 — Assessment Success & Learning Completion Decision

No AssessmentResult → ActivityProgress or AssessmentResult → Course completion coupling is introduced.

## Implementation boundary

EDU-078 is decision-only. It does not implement Course publication enforcement.

A future implementation EDU may enforce the normative predicate during the existing Course publication workflow. It must define concrete application/API behavior, failure representation, transaction/concurrency handling, and tests without changing the predicate or adding new product prerequisites.

## Non-goals

EDU-078 does not:

- implement Course publication enforcement;
- add Course readiness persistence or a READY status;
- modify Course lifecycle states;
- modify Section, LearningUnit, Activity, or Content lifecycle states;
- make Content availability a publication prerequisite;
- change Assessment semantics;
- connect AssessmentResult to ActivityProgress or Course completion;
- modify Enrollment or Learning Progress;
- add authentication or authorization mechanisms;
- add HTTP endpoints;
- add database tables or migrations;
- implement Course versioning, revisions, republishing, scheduling, or draft copies.

## Open follow-up

If product later requires Content completeness before publication, that requirement must be introduced by a separate explicit architectural/product decision because ADR-0005 currently keeps Content availability independent from Activity visibility.
