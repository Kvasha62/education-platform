# ADR-0008 — Student Assessment Submission Contract

- **Status:** Accepted
- **Date:** 2026-08-27
- **Issue:** EDU-062 / #123
- **Decision:** Define the minimum Student-facing plain-text AssessmentAttempt submission, DRAFT mutation, submit validation, archival, aggregate read, and authorization contracts for the next Student Assessment implementation milestone.

## Context

ADR-0006 defines `AssessmentAttempt` as the Assessment-owned representation of one Student submission
and establishes the lifecycle:

```text
DRAFT → SUBMITTED → REVIEWED
```

It also establishes that a Student may create and edit their own DRAFT Attempts, that SUBMITTED and
REVIEWED Attempts are immutable, that resubmission creates a new Attempt, and that Student operations
must remain inside approved Course/Activity access and ownership boundaries. The exact submission
payload and validation rules were explicitly deferred.

EDU-058 implemented a foundation using nullable text `submission_data`, allowed DRAFT creation and
replacement, and authorized Student operations through published Activity visibility and enrollment.
It also allowed existing DRAFT Attempts to be submitted after Definition archival. Those runtime
choices require an explicit normative contract before the next Student-facing vertical slice.

ADR-0007 and EDU-061 define the associated AssessmentResult. They do not define the Student submission
payload or Student read and authorization behavior.

## Decision

### AssessmentAttempt submission model

The approved business field is:

```text
submission: string | null
```

`submission` is optional plain text. Structured JSON, attachments, external references, and
submission-type-specific schemas are not part of this contract.

The required normalization rule is:

```text
null                  → null
empty string          → null
whitespace-only text  → null
non-blank text        → string
```

The same normalization applies when a DRAFT is created and when its submission is replaced. No other
text transformation or product-level maximum length is introduced in this milestone.

### DRAFT creation

An authenticated and authorized Student may create a DRAFT Attempt for an ACTIVE
AssessmentDefinition. Creation accepts either:

```text
submission = null
```

or an initial plain-text submission. Initial text is normalized before the DRAFT is persisted.

An ARCHIVED Definition rejects creation of every new Attempt. Multiple Attempts remain allowed, and a
resubmission is represented by creating another DRAFT rather than reopening an existing Attempt.

### DRAFT editing

The Student owner may fully replace the submission while the Attempt is DRAFT:

```text
string → string
string → null
null   → string
null   → null
```

Every replacement applies the approved normalization rule. No patch, append-only, block-level,
attachment-level, or change-history semantics are introduced.

SUBMITTED and REVIEWED Attempts remain immutable. Their submission, identity, Definition association,
Student ownership, and status cannot be edited or reopened.

### Submit validation

The only approved submission-content precondition for `DRAFT → SUBMITTED` is meaningful plain text.
Normalization is applied before validation, and submit is allowed only when the normalized submission
is non-null:

```text
null                  → submit denied
empty string          → submit denied
whitespace-only text  → submit denied
non-blank text        → SUBMITTED
```

A denied submit leaves the Attempt in DRAFT. No JSON schema, attachment validation, content-quality
rule, minimum or maximum character count, or type-specific validation is introduced.

### Existing DRAFT after Definition archival

Archiving an AssessmentDefinition prevents only the creation of new Attempts. A DRAFT Attempt that
already existed before archival remains editable and submittable under the normal DRAFT rules:

```text
ACTIVE Definition
→ create DRAFT
→ Definition becomes ARCHIVED
→ owner may replace submission
→ owner may submit meaningful submission
```

Definition archival does not mutate, cancel, freeze, delete, or submit existing Attempts.

### Student aggregate detail read

The minimum Student read contract is one ownership-scoped aggregate detail:

```text
Attempt
├── id
├── assessment_definition_id
├── submission
├── status
└── result: AssessmentResult | null
```

The authenticated Student identity is authorization context and is not an additional field in this
aggregate contract. A Student may read only their own Attempt.

Result presence follows the existing lifecycle invariant:

```text
DRAFT     → result = null
SUBMITTED → result = null
REVIEWED  → result = exactly one AssessmentResult
```

When present, `result` uses the complete ADR-0007 contract:

```text
AssessmentResult
├── id
├── attempt_id
├── score
├── max_score
└── feedback
```

The detail read does not introduce a collection, ordering, pagination, current/final/best Attempt, or
separate Student Result resource.

### Student authorization boundary

Student Space remains the application orchestrator. Assessment does not query Education or Learning
private persistence.

#### Mutation and mutable-DRAFT access

The following operations:

```text
create DRAFT
read DRAFT
replace DRAFT submission
submit DRAFT
```

require:

```text
published Activity
+
current ENROLLED status for the Activity's Course
+
Student ownership for an existing Attempt
+
valid Assessment scope binding
```

Student Space asks Education for the existing published Activity application contract and Learning for
the existing enrollment application contract. Assessment verifies its own Definition/Attempt binding
and Attempt ownership. `ActivityProgress` is not consulted.

#### Historical read

Reading the Student's own SUBMITTED or REVIEWED Attempt, including its Result, requires:

```text
Attempt ownership
+
valid Assessment scope binding
```

Historical read does not require current Course publication, current Activity visibility, or current
enrollment. A later Course archive or enrollment change therefore does not hide an already existing
owned SUBMITTED/REVIEWED submission or Result.

Valid Assessment scope binding means that the requested Attempt belongs to the requested
AssessmentDefinition and any nested Result belongs to that Attempt. When an operation carries an
Activity identifier, the Definition's opaque `activity_id` must also match it. Assessment evaluates
these relationships only from Assessment-owned data and does not access Education persistence.

The dependency directions remain:

```text
Student Space → Education application/public boundary
Student Space → Learning enrollment application boundary
Student Space → Assessment application boundary
```

The reverse directions and direct cross-context persistence access remain forbidden.

## Invariants

```text
submission = string | null
blank/whitespace-only submission → null

ACTIVE Definition
→ new DRAFT allowed when Student mutation authorization succeeds

ARCHIVED Definition
→ new Attempt forbidden
→ existing DRAFT remains editable and submittable

DRAFT
→ owner may fully replace submission
→ submit requires normalized non-null submission

SUBMITTED
→ submission immutable
→ result = null until Teacher review

REVIEWED
→ Attempt immutable
→ result = exactly one AssessmentResult

Student aggregate detail
→ own Attempt only
→ DRAFT/SUBMITTED result is null
→ REVIEWED result is present

DRAFT create/edit/submit/read
→ published Activity + current enrollment + ownership where applicable

SUBMITTED/REVIEWED historical read
→ ownership + valid Assessment scope binding
→ independent of current publication and enrollment

Assessment ✗→ Education private persistence
Assessment ✗→ Learning private persistence
ActivityProgress is not an authorization mechanism
```

## Alternatives

### Structured JSON submission

Rejected for this milestone. No JSON schema, schema version, or structured submission payload is
introduced.

### Attachment or external reference submission

Rejected for this milestone. No file ownership, object-storage, attachment cardinality, or reference
availability contract is introduced.

### Always-empty or required-content DRAFT creation

Rejected. Initial submission is optional: a DRAFT may start empty or with normalized text.

### Partial or append-only DRAFT editing

Rejected. DRAFT editing fully replaces the one submission field and retains no change history.

### Empty SUBMITTED Attempt

Rejected. A normalized non-null plain-text submission is required for `DRAFT → SUBMITTED`.

### Freeze or cancel existing DRAFT on Definition archival

Rejected. Archival blocks only new Attempt creation and does not remove edit or submit capability from
an existing DRAFT.

### Separate Attempt and Result Student reads

Rejected for the next milestone. The approved minimum read is one Attempt aggregate detail with an
optional nested Result.

### Require current publication and enrollment for historical read

Rejected. Current access gates mutations and mutable-DRAFT access but does not hide owned historical
SUBMITTED/REVIEWED assessment data.

## Consequences

- Existing nullable text persistence can represent the approved submission type, but implementation
  must align the business field name and normalization behavior with this ADR.
- Empty DRAFTs remain supported, while empty SUBMITTED Attempts become invalid.
- Existing DRAFTs survive Definition archival as actionable Student work.
- SUBMITTED and REVIEWED Attempts retain immutable historical submission content.
- Student historical assessment data remains readable after Course archival or enrollment changes.
- Student Space needs status-aware read authorization: DRAFT detail uses current Activity/enrollment
  access, while SUBMITTED/REVIEWED detail uses Assessment ownership and scope binding.
- The aggregate detail exposes the current corrected Result values and no correction history.
- No collection, HTTP route, frontend, structured payload, attachment, or Progress integration is
  implied by this decision.

## Next implementation milestone scope

A separately authorized implementation Issue may:

- align the AssessmentAttempt business contract with nullable plain-text `submission`;
- normalize blank and whitespace-only submission to `null` during DRAFT creation and replacement;
- require normalized non-null submission for `DRAFT → SUBMITTED`;
- preserve full DRAFT replacement and SUBMITTED/REVIEWED immutability;
- preserve edit and submit behavior for an existing DRAFT after Definition archival;
- add the ownership-scoped Student Attempt aggregate detail with optional nested ADR-0007 Result;
- keep current published-Activity and enrollment checks for DRAFT creation, read, edit, and submit;
- authorize SUBMITTED/REVIEWED historical detail reads through Assessment ownership and scope binding
  without current publication or enrollment checks;
- preserve Assessment-owned persistence and existing cross-context application boundaries;
- add domain, application, persistence, authorization, historical-read, archive, and architecture
  boundary tests for these invariants.

The implementation Issue must not add:

- JSON, attachments, external references, or type-specific submission schemas;
- empty SUBMITTED Attempts;
- additional Attempt lifecycle states;
- reopening or mutation of SUBMITTED/REVIEWED Attempts;
- current/final/best Attempt semantics or attempt limits;
- new permission names or authorization contexts;
- ActivityProgress authorization or lifecycle integration;
- direct cross-context persistence dependencies;
- AssessmentResult semantic changes;
- public HTTP APIs or frontend work unless separately authorized.
