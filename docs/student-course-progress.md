# Student Course Progress contract

EDU-053 defines the authenticated Student endpoint:

```text
GET /api/v1/student/courses/{course_id}/progress
```

Access requires an `ENROLLED` Learning enrollment and a currently `PUBLISHED` Education Course.
Unknown, unpublished, and non-enrolled Courses use the existing safe Student Course `404 Course not
found` response. Authentication uses the existing Student session convention.

The response is:

```json
{
  "course_id": "<course-id>",
  "completed_activities": 8,
  "total_activities": 10,
  "progress_percent": 80
}
```

Per ADR-0005, Activity has no independent publication or visibility lifecycle. `total_activities`
counts every Activity belonging through its Learning Unit and Section to the currently `PUBLISHED`
Course. No additional Activity visibility filter is applied. Content publication, missing Content,
and `Content.available_for_student` do not affect this denominator.

`completed_activities` counts those Course Activities whose Learning-owned Activity Progress status is
`COMPLETED`; an Activity without a Progress row is not completed, and this read creates no rows.
Progress for an Activity outside the Course does not contribute.

The integer percentage is calculated with floor division:

```text
completed_activities * 100 // total_activities
```

A zero total returns `0`. A `100` percentage means only that all counted Activities are completed; it
does not introduce a Course completion state.

Education exposes the minimal read-only `PublishedCourseActivityReader` application boundary defined
by [ADR-0005](decisions/ADR-0005-activity-publication-student-visibility.md). Learning owns enrollment
checks, the set-based completed-progress count, and Course Progress
aggregation. Student Space serializes the Learning application result and accesses neither Education
nor Learning persistence. The implementation uses bounded set-based queries and never performs a
per-Activity Progress lookup.
