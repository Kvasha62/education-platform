# ADR-0006 — Assessment & Submission Domain Model

- **Status:** Accepted
- **Date:** 2026-08-27
- **Issue:** EDU-056 / #113
- **Decision:** Define Assessment as an independent bounded context for manual assessment definitions, Student attempts/submissions, results, scoring, and feedback, without coupling assessment outcomes to Learning Activity Progress.

## Context

The platform has Education-owned Activities and Learning-owned Activity Progress, but no approved
model for Student submissions or Teacher assessment. `ActivityProgress` records participation and
learning completion; it cannot also represent submission content, review, scoring, or feedback without
mixing bounded-context responsibilities.

The MVP needs an Assessment boundary before persistence, application contracts, APIs, or UI are
implemented. The boundary must preserve existing Education, Learning, Student Space, Teacher Space,
and authorization semantics.

## Problem

The architecture must represent a Teacher-configured assessment associated with an Activity, multiple
Student submissions, and a manual result for a specific submission. It must define ownership,
cardinality, lifecycle, authorization, archival behavior, and its relationship to Activity Progress.

Assessment and Learning completion are intentionally distinct:

```text
AssessmentAttempt != ActivityProgress
AssessmentResult  != ActivityProgress
```

## Decision

Assessment is a separate bounded context. It owns `AssessmentDefinition`, `AssessmentAttempt`, and
`AssessmentResult`, including numerical scoring and feedback. Education continues to own `Activity`.
Learning continues to own `ActivityProgress`.

MVP assessment is manual. No assessment action or result implicitly starts, completes, or otherwise
mutates Activity Progress.

## Domain model

```text
Education
└── Activity
      1
      │ 0..1
Assessment
├── AssessmentDefinition
│     1
│     │ 0..N
├── AssessmentAttempt
│     1
│     │ 0..1
└── AssessmentResult

Learning
└── ActivityProgress
```

`AssessmentAttempt` is the domain representation of one concrete Student submission/attempt. MVP does
not introduce a second independent `Submission` entity for the same concept.

## Ownership

- **Education** owns Activity identity, Course membership, and Activity visibility.
- **Assessment** owns definitions, attempts/submissions, results, scoring, and feedback.
- **Learning** owns Activity Progress and its lifecycle.
- **Student Space** and **Teacher Space** expose authorized use cases but own none of the Assessment
  persistence.

Assessment may reference an Education Activity identifier only through an approved Education
application/public boundary. Ownership of Activity does not move to Assessment.

## Relationships

```text
Activity             1 ─── 0..1 AssessmentDefinition
AssessmentDefinition 1 ─── 0..N AssessmentAttempt
AssessmentAttempt    1 ─── 0..1 AssessmentResult
```

Each AssessmentDefinition belongs to exactly one Activity, and an Activity has at most one
AssessmentDefinition. Each AssessmentAttempt belongs to exactly one Student and one
AssessmentDefinition. Each AssessmentResult belongs to exactly one AssessmentAttempt.

An Attempt may exist without a Result while it is DRAFT or SUBMITTED. A Result cannot exist for a
DRAFT Attempt or independently of an Attempt.

## AssessmentDefinition

AssessmentDefinition is the Assessment-owned configuration for one assessable Activity. It supports
manual assessment and has only these lifecycle states in MVP:

```text
ACTIVE
ARCHIVED
```

An ACTIVE Definition accepts new Attempts. An ARCHIVED Definition accepts no new Attempts but remains
available for historical reads of its existing Attempts and Results.

This ADR does not add assessment types, passing scores, rubrics, automated criteria, or automated
grading. Exact submission-content and instruction fields are deferred to a scoped implementation
contract and must not be invented from this ADR.

## Attempt lifecycle

The complete MVP lifecycle is:

```text
DRAFT → SUBMITTED → REVIEWED
```

- DRAFT is editable by the owning Student.
- SUBMITTED is the final submission of that specific Attempt.
- A SUBMITTED Attempt is immutable.
- REVIEWED means Teacher review of that Attempt is complete.
- A REVIEWED Attempt remains immutable.
- No other Attempt states or reverse transitions exist in MVP.

Multiple Attempts are allowed without a maximum. Resubmission creates a new Attempt; it never edits or
reopens an existing SUBMITTED or REVIEWED Attempt. No persisted `current_attempt`, `final_attempt`,
"best attempt", or maximum-attempt state is introduced. Consumers may list Attempts, but the domain
does not designate one as current, final, or best.

## AssessmentResult

An AssessmentResult represents the completed manual assessment of one specific submitted Attempt. It
is created by an authorized Teacher as part of completing review; the associated Attempt becomes
REVIEWED. There is at most one Result per Attempt.

The Teacher may correct an existing Result after creation. Correction updates that Result rather than
creating another Result or another Attempt. MVP does not model Result lifecycle states, versions, or
change history.

## Scoring

AssessmentResult uses numerical scoring:

```text
max_score > 0
0 <= score <= max_score
```

`score` and `max_score` belong to the Result contract. No `passing_score`, pass/fail state, separate
Grade aggregate, best-score selection, or automatic score calculation is introduced.

## Feedback

AssessmentResult may contain optional plain-text `feedback`. An authorized Teacher may change feedback
when correcting the Result. MVP does not include structured rubrics, feedback categories, comment
history, private Teacher notes, or AI-generated feedback.

## Authorization

### Student

Within existing authenticated Student and Course/Activity access boundaries, a Student may:

- create a DRAFT Attempt for an ACTIVE Definition;
- edit and submit their own DRAFT Attempt;
- read their own Attempts, Results, and feedback;
- create another Attempt without a maximum.

A Student may not edit SUBMITTED or REVIEWED Attempts, create or modify AssessmentDefinitions, create
or modify AssessmentResults, or read another Student's assessment data.

### Teacher

Within existing Teacher Space, Course, Activity, and ownership authorization boundaries, an authorized
Teacher may:

- create and modify the Activity's AssessmentDefinition;
- read Attempts for that authorized scope;
- review a SUBMITTED Attempt and create its AssessmentResult;
- correct an existing AssessmentResult, including score and feedback;
- read Student submissions and Results in that scope.

This ADR grants no cross-owner or global Teacher access and does not replace existing backend
authorization checks.

## Persistence boundaries

Assessment persistence belongs exclusively to Assessment. Assessment must not access Education private
persistence, and Education, Learning, Student Space, and Teacher Space must not access Assessment
persistence directly.

Cross-context interaction uses explicit application/public contracts. Database models, repositories,
and tables are not shared across bounded contexts. This ADR intentionally does not define concrete
tables, repository interfaces, foreign keys, migrations, or storage representation.

## Learning Progress boundary

Assessment completion and Learning completion are independent:

```text
SUBMITTED != ActivityProgress.COMPLETED
REVIEWED  != ActivityProgress.COMPLETED
AssessmentResult != ActivityProgress
```

Assessment never automatically mutates `ActivityProgress`. A Result with `score == max_score` does not
complete an Activity. Activity Progress may exist without an AssessmentResult, and Assessment Attempts
or Results do not require or create Activity Progress records.

Any future rule connecting assessment success to learning completion requires a separate explicit
architectural and product decision.

## API implications

Future Student-facing operations must enter through a Student-authorized Assessment application
boundary. Future Teacher-facing operations must enter through a Teacher-authorized Assessment
application boundary. Neither user space may access Assessment persistence directly.

This ADR defines no HTTP paths, request/response DTOs, pagination, submission payload format, or error
mapping. Those contracts require separate implementation Issues consistent with the lifecycle and
authorization rules above.

## Deletion and archive

AssessmentAttempts and AssessmentResults are not physically deleted in MVP.

An AssessmentDefinition with existing Attempts cannot be physically deleted and must be ARCHIVED.
Archival prevents new Attempts while preserving historical Attempts, Results, scores, and feedback for
authorized reads. No additional deletion, restoration, or archival states are introduced.

## Non-goals

This decision does not implement or define:

- runtime domain entities, persistence, migrations, repositories, services, APIs, or UI;
- automated, AI, or code-execution grading;
- rubrics or structured criteria;
- passing scores or pass/fail semantics;
- maximum attempts, current/final/best Attempt selection;
- Result or feedback history;
- certificates, analytics, ranking, gamification, or Course completion;
- changes to Activity, Enrollment, Activity Progress, Content, EDU-053, EDU-054, EDU-055, or ADR-0005.

## Consequences

- Assessment has a clear independent ownership boundary.
- Student submissions and Teacher results can evolve without overloading Activity Progress.
- Attempts retain immutable submitted history while allowing unlimited new Attempts.
- Correctable Results support manual Teacher review without introducing version history in MVP.
- Archival preserves assessment history and prevents destructive deletion after participation.
- Numerical scores do not imply passing, Activity completion, or Course completion.
- Later implementation Issues must define concrete submission payloads, application contracts,
  persistence, API DTOs, and error mappings without changing this domain decision.

## Open questions

The approved domain semantics above are complete for architectural implementation planning. The
following implementation contracts remain deliberately unspecified and require scoped follow-up
Issues:

- exact AssessmentDefinition instruction/configuration fields beyond manual assessment and lifecycle;
- exact DRAFT submission payload and validation limits;
- concrete identifier, timestamp, audit-metadata, persistence, and concurrency representation;
- API paths, DTOs, pagination/order, and error mappings.

These are not resolved by introducing additional domain states, relationships, grading semantics, or
Progress coupling.
