# ADR-0004 — Content Body and Editor Architecture

- **Status:** Accepted
- **Date:** 2026-08-25
- **Issue:** EDU-036 / #72
- **Decision:** Represent the educational body of Content as a Content-owned, versioned-schema structured JSON document, with type-specific root schemas and a deliberately small MVP block vocabulary.

## Problem statement

The existing Content bounded context owns Content identity, ownership, metadata, and lifecycle but does
not yet store actual educational material. Current Content is metadata:

```text
Content
├── id
├── owner_user_id
├── type: ARTICLE | RESOURCE
├── title
├── status: DRAFT | PUBLISHED
├── created_at
└── updated_at
```

Education owns the Activity ↔ Content association. Student Space reaches Content only through
Education application/public boundaries. ADR-0001 forbids Education, Teacher Space, and Student
Space from accessing Content persistence directly.

A body model is required before choosing an editor library or implementing storage/API changes. It
must support introductory programming education, remain safely renderable, avoid editor-vendor
lock-in, and preserve existing bounded-context ownership.

## Decision

### 1. Meaning and ownership of `Content.body`

`Content.body` is the complete pedagogical payload of one Content entity. It is owned by the Content
bounded context together with Content metadata and lifecycle.

The body does not own or encode:

- Activity, Course, Section, or Learning Unit identifiers;
- Activity ↔ Content links;
- student progress, submissions, or assessment results;
- teacher/user identity fields;
- uploaded binary data.

Education continues to own associations. Reusing one Content entity in multiple Activities reuses the
same body.

### 2. Storage representation

The canonical body is structured JSON stored in Content-owned PostgreSQL persistence as JSONB in a
future implementation. PostgreSQL stores the document, not large binary assets.

Every body is a discriminated envelope:

```json
{
  "schema_version": 1,
  "kind": "article",
  "blocks": []
}
```

or:

```json
{
  "schema_version": 1,
  "kind": "resource",
  "resource": {
    "url": "https://example.test/material",
    "description": "Optional plain-text description"
  }
}
```

`schema_version` versions the JSON schema, not the pedagogical Content revision. Unknown schema
versions must be rejected on writes and must not be guessed on reads.

The backend validates the body into Content-owned domain/value objects. Raw arbitrary JSON and
editor-specific document formats are not domain contracts.

Future implementation must enforce bounded payloads. The MVP contract is:

```text
maximum serialized body size: 256 KiB UTF-8
maximum article blocks:        500
maximum external URL length:   2048 characters
```

These limits apply after request decoding and before persistence.

### 3. MVP Article block model

`ARTICLE` supports an ordered `blocks` array containing exactly these discriminated block types:

#### Paragraph

```json
{
  "type": "paragraph",
  "text": "Plain text"
}
```

#### Heading

```json
{
  "type": "heading",
  "level": 2,
  "text": "Loops"
}
```

MVP heading levels are integers `1..4`.

#### Code

```json
{
  "type": "code",
  "language": "python",
  "code": "for item in items:\n    print(item)"
}
```

`language` is an optional syntax hint, not executable behavior. Code is displayed as text and must
never be executed by the editor, API, or student renderer.

#### List

```json
{
  "type": "list",
  "style": "unordered",
  "items": ["First item", "Second item"]
}
```

`style` is exactly `ordered` or `unordered`. MVP list items are plain text and are not recursively
nested blocks.

#### Link

```json
{
  "type": "link",
  "url": "https://docs.python.org/",
  "label": "Python documentation"
}
```

MVP links allow only explicitly validated `https` or `http` URLs. Renderers must not render arbitrary
HTML supplied through labels or URLs.

Article blocks contain plain text fields. Rich inline marks, arbitrary HTML, nested documents, tables,
embeds, and executable interactive blocks are not part of schema version 1.

### 4. MVP Resource body model

`RESOURCE` represents one external educational resource descriptor:

```json
{
  "schema_version": 1,
  "kind": "resource",
  "resource": {
    "url": "https://example.test/material",
    "description": "Optional plain-text description"
  }
}
```

For a DRAFT RESOURCE, `url` is `string | null`; the canonical empty body uses `"url": null` and an
empty or absent description. A non-null URL uses the same `http`/`https` validation policy as link
blocks. Publication requires a non-null valid URL. RESOURCE does not represent an uploaded file in
MVP and does not accept article blocks.

### 5. Relationship between `Content.type` and body schema

The mapping is strict:

```text
Content.type = ARTICLE  ↔ body.kind = article  ↔ ordered blocks schema
Content.type = RESOURCE ↔ body.kind = resource ↔ external resource descriptor
```

The API must reject a mismatched body kind. Content type remains immutable under the current model;
changing a Content entity between ARTICLE and RESOURCE is not an update operation. A different type
requires a new Content entity.

Both types share lifecycle, ownership, safe integration references, and body-level authorization, but
they do not share one ambiguous body union at runtime: `Content.type` selects the only valid body
schema.

### 6. Draft and publishing semantics

The lifecycle remains:

```text
DRAFT → PUBLISHED
```

#### DRAFT

The owner may freely replace a DRAFT body while it remains valid against the type-selected schema.
Draft saves update `updated_at`. An empty ARTICLE document is valid while drafting. The valid empty
RESOURCE body is the type-correct envelope with `resource.url = null`; arbitrary partial JSON is never
persisted.

Draft bodies are not exposed through student-facing public reads.

#### Publish

Publishing validates the persisted body as a complete publishable document:

```text
ARTICLE:  at least one meaningful non-empty block
RESOURCE: valid non-empty http/https URL
```

Publishing is idempotent when Content is already PUBLISHED and unchanged.

Activity associations require no mutation when Content is published. Existing links begin resolving
to the newly published body through Content's public read boundary.

#### PUBLISHED

Published Content is immutable in MVP. Its body and pedagogically meaningful metadata, including
`title` and `type`, cannot be changed in place.

This decision intentionally prevents an owner edit from silently changing material already visible in
multiple Activities and to students. Existing runtime title-update behavior must be aligned in the
future implementation Issue; this ADR itself changes no runtime behavior.

Delete behavior remains governed by ADR-0001: deletion can leave stale Education-owned links, which
resolve as unavailable/not found without leaking Content existence.

### 7. Editing after publication and versioning

Content revision/version history is deferred from MVP.

To revise published material before versioning exists, the owner creates a new DRAFT Content entity,
edits and publishes it, then explicitly updates Activity associations using existing attach/detach
operations. The platform does not automatically redirect links from the old Content entity.

MVP does not add:

- revision numbers;
- `derived_from` relationships;
- automatic draft forks;
- scheduled publication;
- rollback;
- simultaneous published and draft variants under one Content ID.

This is intentionally less convenient than in-place editing but preserves stable student-visible
material and the existing opaque Content-reference contract.

### 8. Asset, image, file, and media boundary

Binary bytes never live inside body JSON or PostgreSQL.

Images, uploaded files, audio, and hosted video are deferred until a Content-owned Asset contract is
approved. That future contract should use the existing `ObjectStorage` architectural abstraction and
store only asset metadata/references in PostgreSQL.

A future asset reference block may contain an opaque `asset_id`; it must not contain storage provider
keys, bucket credentials, filesystem paths, or unsigned internal URLs.

MVP decisions:

```text
external http/https links: supported
inline images:             deferred
uploaded files:            deferred
hosted video:              deferred
video/embed blocks:        deferred
base64/data-URI binaries:  forbidden
```

The RESOURCE body can link to an external file or video URL, but this does not make the platform the
owner or storage provider of that asset.

### 9. Backend API boundary

A future implementation should preserve current metadata endpoints and add an owner-scoped body
resource beneath Content:

```text
GET /api/v1/contents/{content_id}/body
PUT /api/v1/contents/{content_id}/body
```

`GET` returns the validated type-specific body envelope for the authenticated owner. `PUT` replaces
the complete DRAFT body; it is not a JSON merge or editor-operation endpoint.

Example owner write:

```json
{
  "schema_version": 1,
  "kind": "article",
  "blocks": [
    {"type": "heading", "level": 2, "text": "Variables"},
    {"type": "paragraph", "text": "A variable stores a value."}
  ]
}
```

The exact HTTP implementation requires a separate Issue and must update domain model, migration,
OpenAPI, tests, and frontend contracts together.

The existing metadata create/list/get response does not silently begin exposing full bodies. Collection
responses remain metadata-only to keep pagination and selectors bounded. The Activity ↔ Content
association API continues returning only its approved safe reference fields.

No endpoint accepts `owner_user_id` from clients. There is no public generic JSON patch endpoint and
no public persistence/repository contract.

### 10. Frontend/editor boundary

Content editor code belongs in `modules/content`. It consumes typed Content body API contracts through
the existing shared API client and uses existing authentication/session behavior.

The editor is responsible for:

- presenting type-appropriate editing controls;
- producing schema-version-1 domain JSON;
- preserving block order;
- showing validation and immutable-published errors;
- rendering previews through safe components.

The editor is not responsible for:

- authorizing ownership;
- deciding publication eligibility independently of the backend;
- storing session tokens;
- emitting arbitrary HTML;
- executing code blocks;
- writing directly to storage or persistence;
- managing Activity associations.

No rich-text editor framework is selected by this ADR. A later implementation Issue may select a
library only after proving it can produce and consume the platform-owned schema without making a
vendor-specific document its persistence contract.

### 11. Student read boundary

Student Space must not call Content persistence or body endpoints directly.

The approved direction is:

```text
Student Space API
    → Student application
    → Education application/public reader
    → scoped Activity ↔ Content association
    → Content published-body public interface
```

A future Content public operation has the semantics:

```text
read_published_body(content_id)
    → PublishedContentBodyReference | NotFound | ContentLookupUnavailable
```

It exposes only the validated published body and safe type/reference data required for rendering. It
never exposes owner identity, draft body, persistence fields, or editor metadata.

Education first establishes the requested Activity and association scope. Content then enforces
PUBLISHED status internally. Missing, stale, and DRAFT Content use the same external not-found
isolation semantics. Technical lookup failure remains distinguishable internally and maps consistently
with the existing unavailable behavior.

Under the current EDU-020 policy, an authenticated user may read a PUBLISHED Course without
Enrollment. Published body reads associated with that Course follow the same policy unless a later
approved Issue changes Course-read authorization. This ADR does not introduce Enrollment as a new
access gate.

### 12. Ownership and security

- Content body is owned by the same immutable `owner_user_id` as Content metadata.
- Owner body reads/writes derive identity from the authenticated backend session.
- DRAFT body writes require ownership and DRAFT status.
- PUBLISHED body writes are rejected with lifecycle/conflict semantics.
- Student reads expose only bodies reached through a valid published Education scope and Content
  public interface.
- Frontend checks never replace backend authorization.
- Body JSON is strictly validated; unknown block types and unknown fields are rejected.
- Renderers treat all text and code as data, not HTML or executable script.
- External URLs allow only approved schemes and must be rendered with safe browser-link behavior.
- Payload size and block-count limits are enforced server-side.
- Secrets, storage credentials, owner IDs, and internal object keys are forbidden in body contracts.

### 13. Explicit MVP exclusions

- rich inline text marks and arbitrary rich-text documents;
- arbitrary HTML or Markdown-with-HTML;
- tables;
- nested block trees;
- quizzes, assessments, submissions, and grading blocks;
- executable/sandboxed code blocks;
- interactive simulations;
- image blocks and image upload;
- file upload/download management;
- audio/video hosting;
- third-party embed HTML;
- Content version history and rollback;
- collaborative editing, comments, and presence;
- autosave protocol and conflict resolution;
- localization variants;
- AI-generated body operations;
- Content Editor implementation or library selection;
- Activity ↔ Content API changes;
- Student UI implementation.

## Alternatives considered

### Plain text

Rejected because it cannot represent headings, code, lists, and links as validated educational
structure.

### Markdown as canonical storage

Rejected for MVP canonical persistence. Markdown is portable, but parsing dialects, embedded HTML,
code metadata, sanitization, and future typed educational blocks would make server validation and safe
rendering less deterministic. Markdown import/export may be added later as a boundary adapter.

### Sanitized HTML

Rejected because HTML is presentation-oriented, increases XSS/sanitization risk, and couples stored
content to rendering details.

### Editor-specific JSON

Rejected because it would make a selected editor framework part of the domain and persistence
contract. Editor adapters must target the platform-owned schema.

### Fully normalized block tables

Rejected for MVP because separate tables and polymorphic relationships add migration/query complexity
without a demonstrated need for independent block querying or collaborative editing.

### One unrestricted body schema for every Content type

Rejected because ARTICLE and RESOURCE have materially different semantics. An unrestricted union
would permit invalid states and force every consumer to infer meaning from arbitrary JSON.

### In-place editing of published Content

Rejected because one Content can be reused by multiple Activities. In-place edits would immediately
and silently alter student-visible material without version/audit semantics.

### Full versioning in MVP

Deferred because immutable publication plus explicit creation of replacement Content is sufficient for
the first editor slice. Versioning requires product decisions about Activity pinning, replacement,
history visibility, and rollback.

## Future evolution

Schema evolution uses `schema_version` and explicit server-side migrations/adapters. New block types
must be approved, validated, safely rendered, and backward-readable before use.

Expected future sequence:

```text
MVP structured bodies
→ owner body API and basic editor
→ safe Student body reader
→ Content-owned Asset contract and object storage
→ image/file/media reference blocks
→ revision/version model
→ optional Markdown import/export adapters
→ richer educational/interactive blocks under separate decisions
```

A future version model should decide whether Activities reference a stable Content identity plus pinned
revision or an immutable published revision ID. That decision must preserve Education ownership of
associations and must not introduce cross-context persistence relationships.

## Consequences

### Positive

- Content has a platform-owned, editor-neutral pedagogical representation.
- Programming material has first-class code blocks.
- Server validation and safe rendering are deterministic.
- ARTICLE and RESOURCE semantics are explicit.
- Published material is stable across reused Activity links.
- Binary storage remains outside PostgreSQL and body JSON.
- Future blocks and schema upgrades have an explicit path.

### Trade-offs

- The MVP editor cannot offer arbitrary rich-text formatting.
- Published corrections require creating and relinking replacement Content until versioning exists.
- Full-document PUT can overwrite concurrent draft edits; collaborative/conflict-aware editing is
  deferred.
- JSONB is less directly portable than plain Markdown and requires explicit schema adapters.
- Existing published-title update behavior will require alignment in the future implementation Issue.

## Implementation boundary

This ADR records architecture only. It introduces no runtime behavior, API route, schema migration,
frontend component, editor dependency, Content CRUD change, Activity ↔ Content change, or Student UI.
