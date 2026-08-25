# ADR-0003 — Pagination Architecture

- **Status:** Accepted
- **Date:** 2026-08-25
- **Issue:** EDU-034 / #68
- **Decision:** Use one-based page pagination for MVP collection APIs that require bounded responses.

## Context

The current API returns collection responses either as bare JSON arrays or, for Student enrollments,
as an object containing an unpaginated `items` array. No request parameters, response metadata, or
shared pagination types currently exist. Frontend consumers load these collections through TanStack
Query without pagination state.

Not every collection has the same expected cardinality or UI requirement. Content is a reusable,
user-owned collection that can grow independently of one Course structure and is already used as a
selection source when attaching Content to Activities. Structural collections such as Sections,
Learning Units, and Activities are scoped to a parent and their current editing UI needs the complete,
server-ordered sequence.

The platform needs one pagination contract before any endpoint changes, without adding pagination to
collections that do not need it in the current MVP.

## Current collection inventory

| Collection endpoint | Current ordering | Current frontend consumer |
|---|---|---|
| `GET /api/v1/contents` | `created_at ASC, id ASC` | Activity Content selection |
| `GET /api/v1/teacher-spaces` | `created_at ASC, id ASC` | Teacher Spaces list |
| `GET /api/v1/teacher-spaces/{teacher_space_id}/environment/courses` | `created_at ASC, id ASC` | Courses list |
| `GET .../courses/{course_id}/sections` | `position ASC, id ASC` | Section editor |
| `GET .../sections/{section_id}/units` | `position ASC, id ASC` | Learning Unit editor |
| `GET .../units/{unit_id}/activities` | `position ASC, id ASC` | Activity editor |
| `GET .../activities/{activity_id}/contents` | `content_id ASC` | Linked Content panel |
| `GET /api/v1/student/enrollments` | `created_at ASC, id ASC` | No product UI yet |

`GET /api/v1/student/courses/{course_id}` is a single aggregate projection. Its nested Sections,
Learning Units, Activities, and Content references are not independent collection endpoints and are
outside this pagination contract.

The singleton Educational Environment endpoint is not a collection.

## Decision

### Strategy

Use one-based page pagination:

```text
?page=1&page_size=20
```

This is the single platform pagination strategy for MVP endpoints that require pagination.

### Request contract

```text
page:      integer, optional, default 1, minimum 1
page_size: integer, optional, default 20, minimum 1, maximum 100
```

Invalid values use the existing API validation behavior and return `422`.

A client must not send page/offset and cursor parameters together. Cursor parameters are not part of
the MVP contract.

### Response contract

Every paginated collection returns an object:

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "has_next": false
}
```

The item schema remains owned by the endpoint's bounded context. Pagination metadata has the same
field names and semantics across all paginated endpoints.

`page_size` reports the validated requested page size, not the number of returned items.

### Page availability

Repositories should determine `has_next` by requesting at most `page_size + 1` rows, returning only
the first `page_size` items. This avoids a mandatory count query.

### Total-count policy

`total`, `total_pages`, and equivalent count fields are not part of the baseline contract.

Reasons:

- current MVP screens need sequential navigation or incremental access, not an exact global count;
- count queries add work and can become disproportionately expensive as filtering and authorization
  scopes grow;
- a total can become stale immediately under concurrent writes;
- omitting it keeps the contract usable by endpoints where an efficient exact count is unavailable.

An exact or estimated total requires a separate architecture/product decision and must not be added to
only one endpoint under the same baseline pagination contract.

### Empty-result behavior

An empty first page returns `200`:

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "has_next": false
}
```

A page beyond the available range also returns `200` with empty `items`, the requested page number,
and `has_next: false`. It is not a `404`.

### Stable ordering

Every paginated query must define deterministic ordering before applying page boundaries.

Rules:

1. Preserve an endpoint's approved existing primary ordering unless a separate Issue explicitly
   changes it.
2. Append the public entity `id` as the final unique tie-breaker.
3. Apply filtering and authorization before ordering and pagination.
4. Do not rely on database natural order.

For the first applicable endpoint:

```text
GET /api/v1/contents
ORDER BY created_at ASC, id ASC
```

Future paginated endpoints use their approved semantic order plus `id`. For position-based
collections this would be `position ASC, id ASC` if pagination is later approved for them.

Offset-based page pagination can shift under concurrent inserts/deletes. That trade-off is accepted
for the current MVP. Stable ordering makes results deterministic for a fixed dataset but does not
promise snapshot isolation across separate requests.

## MVP applicability

### Pagination required in MVP

#### `GET /api/v1/contents`

Content requires pagination in the current MVP because:

- it is a reusable user-owned library rather than a bounded child sequence;
- it can grow independently across Courses and Activities;
- the Activity–Content UI loads it as a selection source;
- returning every Content record creates an avoidable unbounded response and frontend selection.

Its future implementation Issue must update the Content backend contract, OpenAPI, tests, and all
frontend consumers in the same coordinated change.

### Intentionally unpaginated in the current MVP

#### `GET /api/v1/teacher-spaces`

Expected cardinality per owner is small in the current product slice. The complete set is used as
workspace navigation. Reassess if multi-tenant organization requirements or observed cardinality
make the list materially larger.

#### Course collection

Courses are scoped to the singleton Educational Environment. The current teacher workflow benefits
from displaying the complete Course list, and no marketplace/catalog search exists. Reassess when
filtering, archiving history, or materially larger course libraries are introduced.

#### Section collection

Sections form an ordered Course structure. The editor needs the complete `position, id` sequence for
structure management. Paginating it would complicate ordering without an approved reorder contract.

#### Learning Unit collection

Learning Units form an ordered Section structure and are edited as a complete scoped sequence in the
current MVP.

#### Activity collection

Activities form an ordered Learning Unit structure and are edited as a complete scoped sequence in
the current MVP.

#### Activity linked Content collection

Links are scoped to one Activity, expected to remain small, and the complete set is required to
manage attach/detach and prevent duplicate selection.

#### `GET /api/v1/student/enrollments`

Enrollment history is currently limited to the early Learning MVP and has no dashboard/catalog scale
requirement. It remains unpaginated until a Student dashboard or observed cardinality requires
bounded navigation. Its existing `{ "items": [...] }` response is not considered a pagination
contract and must not be extended ad hoc with different metadata.

#### Nested Student Course projection

The projection is one Course aggregate used for reading its learning structure. Partial pagination of
nested arrays is not approved; if Course structures outgrow the aggregate read model, that requires a
separate API/product decision.

## Implementation and compatibility expectations

This ADR changes no API behavior by itself.

Pagination must be introduced through endpoint-specific implementation Issues. Each such Issue must
update together:

```text
application/repository port
→ persistence query
→ API schema and OpenAPI
→ backend tests
→ typed frontend contract
→ every frontend consumer
```

Changing a bare array response to the paginated object is a breaking response-shape change. It must
not be released silently or backend-only. During the current pre-public MVP, a coordinated backend
and frontend change within one Issue is acceptable. Once external consumers exist, compatibility or
a new API version must be defined explicitly.

Endpoints intentionally left unpaginated must keep their current response shape. They must not wrap
responses in pagination metadata merely for visual consistency.

## Alternatives considered

### Offset/limit pagination

Example:

```text
?offset=0&limit=20
```

Rejected for the platform's MVP public contract. It maps directly to SQL and works well for
programmatic clients, but page-number navigation is clearer for the current frontend and avoids
requiring each consumer to calculate and preserve offsets. It has the same concurrent-write shifting
limitations as page/page-size pagination.

### Cursor pagination

Example:

```text
?cursor=<opaque>&limit=20
```

Deferred, not rejected permanently. Cursor pagination provides better continuity and large-offset
performance for high-volume, frequently changing feeds. Current collections are owner-scoped,
small-to-moderate, and do not justify cursor encoding, cursor validation, filter binding, or more
complex frontend state.

Cursor pagination must not be added as a second convention to an existing `/api/v1` endpoint without
a new architecture decision. If future scale requires it, use opaque cursors bound to the endpoint's
filter and stable ordering, and define a compatibility/versioning path rather than accepting both
page and cursor semantics ambiguously.

### Paginate every collection immediately

Rejected because it adds API and UI complexity to small ordered child collections and works against
the current Course structure editing workflow.

### Keep every collection unpaginated

Rejected because owned Content is already an independently growing library and an unbounded Content
response is unnecessary technical debt.

### Include exact totals in every response

Rejected because current product flows do not require totals and mandatory count queries provide no
corresponding MVP value.

## Consequences

### Positive

- The platform has one explicit pagination vocabulary.
- The first implementation target is limited to a collection with demonstrated need.
- Small ordered structural collections remain simple.
- Stable ordering and empty-page behavior are defined consistently.
- Total-count cost is avoided by default.
- Future cursor adoption has an explicit decision gate.

### Trade-offs

- Page pagination can duplicate or skip rows when data changes between requests.
- Clients cannot display an exact page count under the baseline contract.
- Paginated and intentionally unpaginated endpoints retain different response envelopes.
- Endpoint implementation requires coordinated frontend and backend changes.
