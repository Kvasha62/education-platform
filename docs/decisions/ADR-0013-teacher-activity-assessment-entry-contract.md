# ADR-0013 — Teacher Activity Assessment Entry Contract

- **Status:** Accepted
- **Date:** 2026-08-28
- **Issue:** EDU-071
- **Decision:** Define the normative contract for how Teacher Activity UI determines whether an Activity has an AssessmentDefinition and therefore exposes the `Assessment review` entry point. The Teacher Activity projection carries an optional `assessment_definition_id` reference; `null` means no AssessmentDefinition and no `Assessment review` CTA.

## Context

ADR-0006 defines the Assessment bounded context and the relationship:

```text
Activity (Education)
    1 ─── 0..1 ─── AssessmentDefinition (Assessment)
```

Education owns `Activity`. Assessment owns `AssessmentDefinition`, `AssessmentAttempt`, and `AssessmentResult`. An Activity has at most one AssessmentDefinition, and each AssessmentDefinition belongs to exactly one Activity.

ADR-0009 defines the Student Assessment UI contract. Student Activity UI already receives the Activity → AssessmentDefinition relationship through the Student Course projection: `StudentActivityResponse.assessment_definition_id` is `UUID | null` and is composed by `StudentCourseService` from Assessment's public `AssessmentDefinitionIdLookup.get_id_for_activity(activity_id)` application boundary. Education does not read Assessment persistence.

ADR-0011 defines the Teacher Assessment Review API contract and the Teacher entry/navigation flow:

```text
Teacher Activity
→ Activity has AssessmentDefinition
→ dedicated Teacher Assessment Review queue
→ queue item
→ dedicated Review detail
```

ADR-0012 (EDU-070 / PR #135) defines the Teacher Assessment Review UI contract. It requires:

```text
Teacher Activity
    ↓
Assessment review
    ↓
Teacher Assessment Review queue
```

and states the entry condition is `activity has an AssessmentDefinition`. ADR-0012 also records a **Known integration limitation**: as of EDU-070, the Teacher Activity API response model exposed to the Teacher Activity page does not carry an `assessment_definition_id` field, so the Teacher Activity page today has no direct data attribute that proves an Activity is assessment-bearing. The Teacher Activity model does not include that field, while the Student Activity model does.

The Teacher Activity page is the discovery surface for Teacher Assessment Review, but the Teacher Activity projection does not currently expose the relationship that the entry point depends on. Teacher Assessment review and correction require AssessmentDefinition context, so the UI needs an approved source of `assessment_definition_id` rather than a heuristic or a lookup endpoint.

## Problem

The Teacher Activity UI cannot know whether an Activity is assessment-bearing without an approved signal. Without that signal the `Assessment review` CTA described by ADR-0012 cannot be rendered correctly. The UI must not guess the relationship from Activity type, title, contents, or other Activity data, and it must not derive Definition identity from Attempt data, URL fragments, or an invented Assessment lookup endpoint.

The gap is architectural: Education owns the Activity; Assessment owns the Definition. The Teacher Activity projection must therefore carry the AssessmentDefinition identity reference as a projection/reference field, composed at an approved application boundary, without coupling the two bounded contexts' persistence or private implementation.

## Decision

### 1. Canonical relationship

The Teacher Activity projection exposes the Activity → AssessmentDefinition relationship as an optional reference field:

```text
Teacher Activity projection
    └── assessment_definition_id: UUID | null
```

Semantics:

```text
assessment_definition_id == null
→ the Activity has no AssessmentDefinition
→ the Activity is not assessment-bearing
→ Assessment review CTA is not available

assessment_definition_id != null
→ the Activity has an AssessmentDefinition
→ the value identifies the AssessmentDefinition bound to that Activity
→ the Assessment review CTA is available
```

The value is the AssessmentDefinition identity owned by Assessment. It is a projection/reference field, not Assessment aggregate expansion. It does not include Definition internals, instructions, Attempt data, Result, submission, review state, or scoring data.

### 2. How the projection obtains the reference

The field is composed at the teacher-facing application/API boundary, not by Education or Assessment domain logic:

```text
Teacher-facing projection composition
    ├── Education public Activity read/scope boundary (Activity identity and structure)
    ├── Assessment public AssessmentDefinitionIdLookup.get_id_for_activity(activity_id)
    └── returns activity_id → assessment_definition_id | null
```

This is the same approved pattern already used by the Student Course projection. `StudentCourseService` composes the published Course from a `PublishedCourseReader` (Education public boundary) and an `AssessmentDefinitionIdLookup` (Assessment public boundary), then maps each Activity to its `assessment_definition_id` or `null`.

Rules:

- The field is sourced from Assessment's public application `AssessmentDefinitionIdLookup` protocol; it is never read from Assessment private persistence by Education, Teacher Space, or the frontend.
- The reference is projected onto the teacher-facing Activity response. It is not persisted as a new Education column and is not added to the Education `Activity` domain model.
- The composition happens in application/API orchestration, consistent with existing Teacher Space and Student Space orchestration roles and ADR-0006's requirement that cross-context interaction use explicit application/public contracts.
- No new Assessment lookup HTTP endpoint is introduced.
- The existing Teacher Activity API routes and response shape are extended only by this projection reference; no new route is created by this milestone.

### 3. Ownership

Ownership remains explicit and unchanged from the approved architecture:

```text
Education
├── owns Activity
└── owns the Activity structure/visibility portion of the Teacher Activity projection
```

```text
Assessment
├── owns AssessmentDefinition, AssessmentAttempt, AssessmentResult
└── owns the public AssessmentDefinitionIdLookup boundary used to resolve the reference
```

```text
Teacher Space / teacher-facing application boundary
└── composes the teacher-facing Activity projection from Education and Assessment public boundaries
```

```text
Teacher Activity UI (modules/education)
└── consumes the Teacher Activity projection and renders the Assessment public entry
```

```text
modules/assessment
└── owns Assessment Review UI, queue, detail, review, correction, and Result behavior
```

Rules:

- The Activity/Learning side owns the Teacher Activity page and the Activity projection consumed by that page.
- `modules/education` must not implement Assessment business logic, lifecycle, Result, review, correction, or error-mapping logic.
- `modules/assessment` owns all Assessment-specific UI and behavior. Teacher Activity UI consumes only the Assessment module's minimal public integration interface.
- No Assessment domain logic moves into Learning/Education.
- No Education/Teacher Space dependency on Assessment private persistence is introduced.
- No Assessment dependency on Education private persistence is introduced.

Conceptual flow:

```text
Teacher Activity projection
        │
        │ assessment_definition_id
        ↓
Teacher Activity UI (modules/education)
        │
        │ public Assessment integration
        ↓
modules/assessment
        │
        ↓
Teacher Assessment Review queue (ADR-0012)
```

### 4. Optionality / null semantics

The field is optional and nullable. Both states are valid and explicit:

```json
{
  "id": "...",
  "title": "...",
  "type": "lecture",
  "position": 1,
  "contents": [],
  "assessment_definition_id": null
}
```

```json
{
  "id": "...",
  "title": "...",
  "type": "lecture",
  "position": 1,
  "contents": [],
  "assessment_definition_id": "..."
}
```

Rules:

- The field is always present in the Teacher Activity projection shape.
- `null` is the stable, authoritative representation of "no AssessmentDefinition".
- The frontend must not infer assessment presence from Activity type, title, contents, or any other heuristic.
- The frontend must not treat a missing field as equivalent to `null` in production; a missing field is an unknown/unsupported projection and the Assessment entry CTA is unavailable rather than guessed (see §8).
- The relationship is known by the Teacher Activity projection at the time the projection is composed. It is not a runtime discovery operation performed by the frontend.

### 5. Teacher Activity CTA visibility

Teacher Activity UI behavior:

```text
assessment_definition_id != null
→ expose the Assessment review entry / CTA

assessment_definition_id == null
→ the Assessment review CTA is absent
```

Rules:

- Do not display a disabled Assessment button for non-assessment Activities.
- Do not expose Assessment controls merely because an Activity type appears compatible with Assessment.
- Do not render the full Review queue inline on the Teacher Activity page. The CTA enters the dedicated Teacher Assessment Review queue owned by ADR-0011 / ADR-0012.
- The CTA is a discovery/entry control, not an Assessment behavior implementation.

### 6. Frontend module ownership

- Teacher Activity UI and the Teacher Activity projection consumer remain in `modules/education`. They decide CTA visibility from `assessment_definition_id` only.
- Teacher Assessment Review UI belongs to `modules/assessment` (`modules/assessment/teacher/`), per ADR-0011 §18 and ADR-0012 §1.
- The Assessment module exposes a minimal public integration interface, e.g. `TeacherAssessmentReviewEntry`, which the Teacher Activity page may render when the Activity is assessment-bearing.
- `modules/education` does not implement Assessment lifecycle, Result, validation, review, correction, or error mapping.
- `modules/learning` and Student Assessment UI remain unchanged by this decision.
- Global route registration remains in `app/router.tsx` per ADR-0002.

### 7. Navigation / integration boundary

The CTA provides the Assessment module with the navigation context already available from the current Teacher Activity context/projection:

```text
teacher_space_id
activity_id
assessment_definition_id
```

The Teacher Activity UI receives both `teacher_space_id` and `activity_id` as navigation/scope context and `assessment_definition_id` from the projection. It passes these to the Assessment module public entry.

Conceptual flow:

```text
Teacher Activity
    ↓
Assessment review CTA
    ↓
Assessment module public entry
    ↓
Teacher Assessment Review queue
```

Rules:

- The frontend routes remain governed by ADR-0012:

```text
/app/teacher-spaces/:teacherSpaceId/activities/:activityId/assessment-review
/app/teacher-spaces/:teacherSpaceId/activities/:activityId/assessment-review/:attemptId
```

- This milestone does not create a new frontend route.
- Route context is navigation only and is not authorization. Backend authorization remains authoritative.
- The Assessment module does not receive the Definition as a Review route/query parameter; ADR-0011 requires the Teacher Review path to use only `teacher_space_id`, `activity_id`, and `attempt_id`. `assessment_definition_id` is the entry signal, not a Review namespace identifier.

### 8. Stale / missing projection behavior

The field indicates the Activity → AssessmentDefinition relationship known by the Teacher Activity projection at composition time.

The frontend must not:

- cache its own inferred relationship permanently;
- derive Definition identity from Attempt ID;
- reconstruct Definition identity from URL fragments;
- guess Definition IDs;
- fall back to Activity type;
- query Assessment persistence directly;
- treat an absent field as a positive "has AssessmentDefinition" signal.

If the projection does not provide an explicit `assessment_definition_id` value, the Assessment entry point is unavailable. The frontend must not invent, infer, or synthesize a Definition identity. A stale projection that still contains a non-null Definition reference may continue to expose the CTA until the projection refreshes; if the reference is removed, the CTA disappears on the next projection load.

### 9. API boundary

The Teacher Activity projection exposes only the identity reference:

```text
assessment_definition_id → UUID | null
```

The projection must not include:

- AssessmentDefinition internals (instructions, lifecycle/status, configuration);
- Attempt data;
- Result;
- submission;
- review state;
- scoring data;
- Student identity data;
- ActivityProgress.

The reference keeps Activity and Assessment bounded contexts separated: Education/Activity owns the Activity structure and visibility; Assessment owns Definition identity and all Assessment aggregate behavior. The value is an opaque reference used for UI entry decisions, not an authorization input and not a source of domain behavior outside the Assessment module.

### 10. Relationship to ADR-0012

ADR-0012 (Teacher Assessment Review UI Contract) owns:

- Teacher Activity → `Assessment review` → queue entry point;
- Review queue, Attempt detail, review, correction, Result presentation, loading/empty/error/pagination/navigation;
- frontend routes;
- Assessment module ownership and the API/application boundary for the Review HTTP contract.

EDU-071 / ADR-0013 owns only the Activity → AssessmentDefinition discovery/reference contract that ADR-0012 depends on:

- how Teacher Activity UI knows an Activity has an AssessmentDefinition;
- the optional `assessment_definition_id` projection field;
- `null` semantics and CTA visibility;
- where the reference is composed from approved public boundaries;
- what the projection must not expand.

This decision resolves the "Known integration limitation" recorded in ADR-0012 §2. It does not duplicate the full Teacher Assessment Review UI contract and does not change any ADR-0012 review/queue/detail/correction semantics.

If ADR-0012's wording is later found to conflict with this contract, ADR-0012 would need an explicit amendment approved before implementation. No amendment is made by this milestone.

### 11. Architecture consistency

The proposed contract is consistent with the approved architecture:

- **Bounded-context ownership:** Education owns Activity; Assessment owns AssessmentDefinition. The reference is composed through public application boundaries, matching the already-approved Student Course projection pattern.
- **Frontend module boundaries:** `modules/education` consumes the Activity projection and the Assessment public entry; `modules/assessment` owns Assessment Review behavior.
- **Teacher Activity ownership:** Teacher Activity UI remains in `modules/education` and only decides CTA visibility from the projected reference.
- **Assessment ownership:** Definition identity resolution uses Assessment's existing public `AssessmentDefinitionIdLookup`, not Assessment private persistence access.
- **ADR-0002:** The change is a documentation/projection contract only; no routing, state, shared-module, or API-client change is introduced by this milestone.
- **ADR-0009:** The Student → Activity CTA precedent already uses `assessment_definition_id` from the Student Course projection. The Teacher contract mirrors it without touching Student behavior.
- **ADR-0011:** The Teacher Review path keeps only `teacher_space_id` + `activity_id` + `attempt_id`; `assessment_definition_id` is not added to the Review route namespace. ADR-0011 §19 already requires the entry condition "Activity has AssessmentDefinition".
- **ADR-0012:** The contract supplies the entry signal ADR-0012 requires and does not change queue/detail/review/correction semantics.

No contradiction with an approved ADR was found.

## Invariants

```text
Teacher Activity projection
→ carries assessment_definition_id: UUID | null
→ null = no AssessmentDefinition, no Assessment review CTA
→ non-null = AssessmentDefinition bound to the Activity, Assessment review CTA available
→ field is a reference, not an Assessment aggregate expansion

Composition
→ Teacher-facing application/API boundary
→ Education public Activity boundary
→ Assessment public AssessmentDefinitionIdLookup.get_id_for_activity()
→ no Assessment private persistence access
→ no Education private persistence access by Assessment
→ no new lookup endpoint
→ no new frontend route

CTA
→ rendered only when assessment_definition_id != null
→ absent when null
→ never disabled for non-assessment Activities
→ never inferred from type/title/contents
→ enters Assessment module public entry, not an inline queue

Ownership
→ modules/education owns Teacher Activity page and projection consumer
→ modules/assessment owns Assessment Review behavior
→ modules/education implements no Assessment lifecycle/result/review/correction logic

Projection scope
→ reference only
→ no Definition internals, Attempt, Result, submission, review state, scoring, Student identity, ActivityProgress

Entry signal
→ not a Review route/query/body parameter
→ not an authorization input
→ not inferred, guessed, or reconstructed by the frontend
```

## Alternatives

### Add `assessment_definition_id` to the Education `Activity` domain model and persist it in Education

Rejected. AssessmentDefinition is Assessment-owned. Persisting the relationship in Education would duplicate Assessment-owned identity and couple the bounded contexts. The existing Student projection composes the value at the application boundary without persisting it under Education; the Teacher projection follows the same pattern.

### Add a new `GET /assessment-definitions/{id}` or `GET /activities/{activity_id}/assessment-definition` lookup endpoint

Rejected. The Activity projection already carries the relationship; a lookup endpoint would add a redundant request and a new public surface. It would also contradict the requirement not to introduce a lookup endpoint and would not be necessary if the projection composes the existing Definition identity lookup.

### Have Teacher Activity UI query Assessment for `assessment_definition_id`

Rejected. The frontend must not reach across module boundaries for the relationship and must not depend on Assessment persistence/API directly. The projection is the approved source.

### Infer assessment presence from Activity type, title, contents, or other heuristics

Rejected. Assessment presence is a domain relationship, not a presentational inference. Heuristics are unverifiable and would produce false positives/negatives.

### Derive Definition identity from Attempt or URL data on the frontend

Rejected. The Definition is bound to the Activity; deriving it from an Attempt or route fragment would reverse the relationship, add hidden coupling, and break when the queue is empty or a history entry changes.

### Treat a missing field as `null` and hide the CTA permanently

Rejected as the only behavior. An absent field is an unsupported projection and the CTA must be unavailable rather than guessed, but the normative Teacher Activity projection always includes the field.

### Render a disabled Assessment button for non-assessment Activities

Rejected. ADR-0012 and the Teacher activity discovery contract define `assessment_definition_id == null` as "CTA absent", not "CTA disabled".

## Consequences

- Teacher Activity UI has a verified, explicit source for whether an Activity is assessment-bearing.
- The Teacher Assessment Review entry point required by ADR-0011 §19 and ADR-0012 is no longer blocked by the previously recorded integration limitation.
- Activity and Assessment remain separated bounded contexts; Education and Teacher Space never read Assessment private persistence for this reference.
- The Teacher Activity projection stays readable and does not expose Assessment aggregate data.
- No new Assessment lookup endpoint is required.
- The frontend has a deterministic nullable signal for CTA visibility without heuristic guessing.
- The relationship is projected, not persisted, and remains a reference-only field.
- A future Teacher Activity READ/WRITE projection change is required to physically carry `assessment_definition_id` to the frontend; this milestone does not implement it.

## Non-goals

This decision does not implement or authorize:

- frontend components, API clients, hooks, routes, state, styling, or UI tests;
- Teacher Assessment Review queue, Attempt detail, review, or correction UI;
- Assessment API changes;
- Attempt API changes;
- database schema changes or migrations;
- a new Teacher Activity column or persisted relationship;
- AssessmentDefinition CRUD or lifecycle changes;
- a new `/assessment-definitions/{id}` or Activity Definition lookup endpoint;
- Student Assessment behavior changes;
- ActivityProgress changes or authorization;
- Student identity lookup;
- a new Teacher Assessment dashboard;
- a cross-Activity Assessment collection;
- expansion of `assessment_definition_id` into Definition internals or Assessment aggregate data.
