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

`total_activities` counts only Activities in the Education-owned, Student-visible structure of the
published Course. Missing or stale Activity IDs outside that scope are excluded.
`completed_activities` counts scoped Activities whose Learning-owned Activity Progress status is
`COMPLETED`; an Activity without a Progress row is not completed, and this read creates no rows.

The integer percentage is calculated with floor division:

```text
completed_activities * 100 // total_activities
```

A zero total returns `0`. A `100` percentage means only that all counted Activities are completed; it
does not introduce a Course completion state.

Education exposes the minimal read-only `PublishedCourseActivityReader` application boundary.
Learning owns enrollment checks, the set-based completed-progress count, and Course Progress
aggregation. Student Space serializes the Learning application result and accesses neither Education
nor Learning persistence. The implementation uses bounded set-based queries and never performs a
per-Activity Progress lookup.
