# ADR-0005 — Activity Publication and Student Visibility

- **Status:** Accepted
- **Date:** 2026-08-27
- **Issue:** EDU-054 / #109
- **Decision:** Project Architect approved Variant A: Activity has no independent publication or visibility lifecycle. A `PUBLISHED` Course is the publication boundary for every Activity that belongs to it.

## Context

EDU-053 needs one authoritative denominator for Student Course Progress. Education owns Course,
Section, Learning Unit, Activity, Course publication, and the Student-facing Course structure, while
Learning owns Activity Progress and its aggregation. The existing model has no Activity status or
visibility field and cannot represent a hidden Activity inside a `PUBLISHED` Course.

The contract must therefore state explicitly which Activities Education exposes to Learning without
inferring visibility from Content or allowing Learning to access Education persistence.

## Decision

Activity has no independent publication or Student-visibility lifecycle. Course publication and
Activity membership are the authoritative sources of Activity visibility.

An Activity is Student-visible if and only if it belongs, through its Learning Unit and Section, to a
Course whose current status is `PUBLISHED`. Every Activity belonging to a `PUBLISHED` Course is in the
Student-visible published Course structure. A hidden, unpublished, or independently archived Activity
inside a `PUBLISHED` Course does not exist in the current architecture.

No `Activity.status`, `publication_status`, `available_for_student`, `published_at`, `archived_at`, or
equivalent independent publication field is introduced.

## Rules

```text
Course.DRAFT
→ its Activities are not in Student-visible published Activity scope

Course.PUBLISHED
→ all Activities belonging to the Course are in Student-visible published Activity scope

Course.ARCHIVED
→ its Activities are not in Student-visible published Activity scope
```

The Student Course read model returns all Activities belonging to a currently `PUBLISHED` Course and
returns no Course structure for a DRAFT, ARCHIVED, or unknown Course under the existing safe not-found
semantics.

## Content boundary

Activity visibility and Content availability are independent concepts:

```text
Activity visibility ≠ Content availability
```

`Content.status` and `Content.available_for_student` must not determine whether an Activity is visible.
A Student-visible Activity may have zero Student-available Content items. Content continues to apply
its own publication and availability rules to the Activity's associated Content references.

## Course publication interaction and Teacher mutations

Publishing a DRAFT Course makes every Activity currently belonging to that Course Student-visible as
part of the Course structure. DRAFT and ARCHIVED Courses expose no Student-visible Activity scope.

EDU-054 introduces no new Teacher mutation rules, Activity publication operation, republish
requirement, or visibility operation. Existing Course publication and immutability rules remain in
force. Any future requirement to add, remove, or reorder Activities after Course publication must be
handled under those existing rules or defined by a separate architectural decision; this ADR does not
expand them.

## Learning boundary

Education exposes the published Course Activity scope through a minimal read-only application/public
boundary conceptually equivalent to:

```python
class PublishedCourseActivityReader(Protocol):
    def list_activity_ids(self, course_id: UUID) -> list[UUID]: ...
```

For a `PUBLISHED` Course, the reader returns all Activity IDs belonging to that Course. For a DRAFT,
ARCHIVED, or unknown Course, it uses the existing safe published-Course not-found semantics. It applies
no additional Activity visibility or Content filter.

Learning may consume this boundary to aggregate Course Progress but must not query Education
persistence directly.

## Progress interaction

Existing Activity Progress lifecycle and records remain unchanged. Course Progress counts all
Activities returned by the Education boundary and counts as completed only those with the current
Student's `ActivityProgress.status == COMPLETED`. An Activity without a Progress record is not
completed, and aggregation creates no Progress rows.

Because independent Activity hiding or unpublishing does not exist, the scenario "completed Activity
becomes hidden while its Course remains PUBLISHED" is not representable. A result of 100 percent means
only that every counted Activity is completed; it creates no Course completion state.

## Migration and backward compatibility

No database migration, new column, or backfill is required. Existing data has deterministic semantics:

- every Activity belonging to an existing `PUBLISHED` Course is Student-visible;
- Activities belonging to DRAFT or ARCHIVED Courses are outside published Student scope.

## Consequences

- Education can provide an unambiguous Student-visible Activity scope without a new lifecycle.
- EDU-053 may use all Activities belonging to a `PUBLISHED` Course as its denominator.
- Student Course reads, Activity Progress authorization, and Course Progress use the same Course-level
  publication boundary.
- Content publication remains isolated from Activity visibility.
- The model is deliberately simple and cannot hide an individual Activity inside a `PUBLISHED` Course.

## Future

Any requirement for independently hidden, scheduled, drafted, published, or archived Activities would
change this contract and requires a new architectural decision covering state, migration, Course
publication interaction, Teacher mutations, Student reads, and existing Progress behavior. It must not
be added as an incremental field or inferred from Content.
