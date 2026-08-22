# ADR-0001 — Activity / Content integration contract

**Status:** Approved

**Issue:** EDU-014 / #29

## Context

`Activity` is owned by the Education bounded context. `Content` is a separate, user-owned bounded context with its own domain model and persistence. The two contexts currently have no runtime or persistence integration.

The platform needs a future way to associate reusable Content with Activities without allowing Content to depend on Education or allowing Education to access Content persistence details.

## Decision

### Relationship ownership and cardinality

Education owns the Activity / Content relationship.

The relationship is many-to-many:

```text
Activity N ↔ M Content
```

A future implementation will represent it with an Education-owned association table named `activity_content_links`.

### Persistence and foreign keys

The association persistence contract is:

```text
activity_content_links
├── activity_id UUID NOT NULL
└── content_id  UUID NOT NULL
```

- `(activity_id, content_id)` is the composite primary key and prevents duplicate links.
- `activity_id` has an Education-internal FK to `activities.id` with `ON DELETE CASCADE`.
- `content_id` is an opaque UUID. It has no database FK to `contents` or any other Content table.
- `content_id` is not nullable.
- Add an index on `content_id`; the composite primary key already supports lookup by `activity_id`.
- Education owns the association table and its migration.
- No Content migration or Content persistence model may reference Education tables.

This is the only approved persistence relationship. Shared ORM models, cross-context SQLAlchemy relationships, and cross-context repository access are forbidden.

### Runtime dependency direction

The only permitted runtime direction is:

```text
Education application
        ↓
Content public interface
        ↓
Content implementation
```

Content must not import Education. Education must not import Content ORM models, repositories, infrastructure, or private domain/application implementation.

### Minimum Content public interface

A later implementation may introduce a read-only public interface owned by Content with the semantic operation:

```text
lookup_owned(content_id: UUID, owner_user_id: UUID)
    → ContentReference | NotFound | ContentLookupUnavailable
```

`ContentReference` exposes only safe integration data:

```text
id
ContentType
ContentStatus
available_for_student
```

`available_for_student` is true only when status is `PUBLISHED`.

The interface must apply Content ownership and existence checks internally. Education receives the same not-found result for missing and not-owned Content and must not infer which condition occurred.

Education is not permitted to create, update, publish, unpublish, or delete Content through this interface. No Content repository is exposed as a public interface.

### Lifecycle semantics

- An association may be created while Content is `DRAFT`.
- `DRAFT` Content is not available to Student Space.
- `PUBLISHED` Content is available to Student Space when the association and all Education ownership/scope checks are valid.
- Publishing Content requires no association mutation; a later lookup reflects the new status.
- Deleting Content does not trigger Content-side cleanup. The association remains stale and lookup returns not found/unavailable.
- Deleting Activity cascades deletion of its association rows inside Education.
- No Activity disabled/unavailable state currently exists. A future state must define its effect in a separate decision; EDU-014 does not invent one.
- Teacher access policy for associated DRAFT Content is deferred. This decision only permits creating the association and defines Student availability.
- Content ownership remains immutable under the current model. Any future ownership change requires a separate decision.

### Failure and isolation semantics

- Missing Content and Content not owned by the authenticated owner are indistinguishable outside Content and use not-found semantics.
- Stale associations are treated as unavailable and must not reveal whether Content was deleted or is owned by another user.
- Student access to DRAFT Content is denied using the same external resource-isolation semantics.
- Invalid Activity/association scope uses existing Education `404` isolation semantics.
- A technical failure of the Content public interface returns `ContentLookupUnavailable`, not `NotFound`. It remains distinguishable inside the application so it is not misreported as an ownership decision. EDU-014 adds no HTTP endpoint; any later public HTTP contract must explicitly map this application failure without weakening ownership isolation.

### HTTP API contract

EDU-014 adds no public HTTP API.

Attach/detach endpoints, request schemas, status codes, and ordering are not approved by this decision. If public HTTP operations are required, a separate implementation Issue must define them explicitly before implementation.

### Student Space evolution

Student Space must consume Education application interfaces and must not query Content persistence directly. Education resolves the scoped Activity and association, then uses the Content public interface. Content remains unaware of Student Space and Education persistence.

This permits future user spaces to reuse Content without reversing the dependency or sharing persistence models.

## Required architecture guards

A later implementation is accepted only if guards prove:

1. Content has no imports from Education or Teacher Space.
2. Education imports only the approved Content public-interface module.
3. Education does not import Content ORM models, repositories, infrastructure, or private services.
4. Content persistence has no FK to Activity or any Education table.
5. `activity_content_links.content_id` has no FK.
6. The association has exactly one FK, to `activities.id`, with cascade delete.
7. `(activity_id, content_id)` is unique through the composite primary key.
8. No shared ORM models or repositories exist across the contexts.
9. Student Space does not import Content persistence.
10. Any future API uses application/public interfaces rather than direct repository access.

## Alternatives considered

### Content-owned relationship

Rejected because it introduces `Content → Education` knowledge and reverses the approved dependency direction.

### Direct Activity → Content foreign key

Rejected because it couples Education persistence to Content persistence and cannot represent the approved N:M cardinality.

### Cross-context FK from an association table

Rejected because database referential integrity would cross bounded-context ownership and constrain independent evolution/deletion.

### Separate integration bounded context

Rejected for now because it adds a new bounded context and infrastructure not required by the current architecture.

### No persistent relationship

Rejected because the approved future integration needs stable Activity/Content associations. Persistence remains Education-owned without a Content FK.

## Consequences

- Bounded contexts remain independently owned.
- Referential integrity for Content IDs is enforced through the Content public interface rather than a database FK.
- Content deletion can leave stale links; consumers must handle unavailable lookup results.
- N:M reuse is supported without making Content aware of Education.
- A separate implementation Issue is required for the association model, Content public interface implementation, application use cases, guards, and any HTTP contract.
