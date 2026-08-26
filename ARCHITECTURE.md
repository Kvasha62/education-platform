# Education Platform — Architecture

**Version:** 1.0  
**Status:** Active Baseline  
**Purpose:** Technical source of truth for the project

> This document is the architectural law of Education Platform. Implementation must comply with it. Any architectural deviation requires explicit approval and, where appropriate, an ADR.

## 1. Vision

Education Platform is a **constructor of educational environments**, not merely an LMS or course catalogue.

The platform must evolve through independent modules and user spaces:

- Platform Core
- Domain Engines
- Teacher Space
- Student Space
- Parent Space
- future Mentor/Admin spaces

The first product slice is Teacher Space and a minimal educational environment builder.

## 2. Architectural style

The project starts as a **Modular Monolith + Domain-Oriented Architecture + API-first + Event-ready Architecture**.

Microservices are explicitly out of scope at the start. Module boundaries must nevertheless be strong enough that a module could later be extracted into a service if real scale or operational requirements justify it.

## 3. Technology baseline

### Frontend
- React
- TypeScript
- Vite

### Backend
- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic

### Data
- PostgreSQL
- S3-compatible object storage; MinIO locally

### API
- REST
- OpenAPI
- `/api/v1/...`

### Testing
- Pytest
- Vitest
- Playwright

### Infrastructure
- Docker
- Docker Compose
- GitHub Actions

## 4. Explicitly prohibited infrastructure at the start

Without an explicit architectural decision, do not introduce:

- Kubernetes
- Kafka
- RabbitMQ
- Elasticsearch
- Redis
- service mesh
- GraphQL
- event sourcing
- CQRS
- distributed microservices

## 5. Monorepo

```text
education-platform/
├── apps/
│   ├── backend/
│   └── frontend/
├── packages/
├── tests/
├── docs/
├── docker/
├── scripts/
├── .github/
├── ARCHITECTURE.md
├── AGENTS.md
├── PLATFORM_VISION.md
├── CONTRIBUTING.md
├── README.md
├── docker-compose.yml
└── .env.example
```

## 6. Backend modules

```text
apps/backend/app/
├── core/
├── identity/
├── users/
├── teacher/
├── education/
├── content/
├── learning/
├── assessment/
├── commerce/
├── advertising/
└── events/
```

A domain module should use these layers where appropriate:

```text
module/
├── api/
├── application/
├── domain/
├── infrastructure/
└── tests/
```

### API layer
HTTP, validation, serialization, authentication context and HTTP-to-application mapping. No business logic.

### Application layer
Use cases, orchestration, transaction boundaries and calls to domain/public module interfaces.

### Domain layer
Entities, value objects, business rules, domain services and domain events. It must not depend on FastAPI, PostgreSQL or concrete infrastructure providers.

### Infrastructure layer
Repositories, SQLAlchemy, external APIs, storage adapters, payment adapters and technical implementations.

## 7. Core

`core` contains technical foundations: configuration, environment, logging, database connection, dependency injection, common errors and security primitives. It must not contain education business logic.

## 8. Identity and Users

Identity answers **who is this user?** and owns authentication, sessions, credentials and identity verification.

Users owns general user data. Profile-specific data must remain in appropriate modules rather than turning User into a giant entity.

Authorization should be permission-oriented. Examples:

```text
course:create
course:update
course:publish
course:archive
activity:create
activity:update
activity:delete
homework:review
```

Avoid spreading hard-coded role checks through business logic.

## 9. Teacher Space

Teacher Space is the first user-facing system. It provides the teacher dashboard and uses domain engines for educational functionality.

Teacher Space does **not** own Course, Activity, Payment or Advertisement domain entities.

## 10. Education Engine

Core entities:

```text
EducationalEnvironment
Course
Section
LearningUnit
Activity
```

Teacher owns an Educational Environment containing courses.

### Course
Course contains title, description, age range, status, pricing configuration and metadata.

Initial lifecycle:

```text
DRAFT → PUBLISHED → ARCHIVED
```

#### Course Publication Immutability

`PUBLISHED` is an immutable published state for teacher-facing mutation APIs. Once a Course reaches `PUBLISHED`, the Course and its educational structure are read-only through teacher-facing mutation APIs.

The following policy applies:

```text
DRAFT
  ├── Course mutation                 allowed
  ├── Section mutation                allowed
  ├── Learning Unit mutation          allowed
  ├── Activity mutation               allowed
  └── Activity ↔ Content attach/detach allowed

PUBLISHED
  ├── read                            allowed
  ├── Course mutation                 forbidden
  ├── Section mutation                forbidden
  ├── Learning Unit mutation          forbidden
  ├── Activity mutation               forbidden
  └── Activity ↔ Content attach/detach forbidden

ARCHIVED
  ├── read                            allowed
  └── all teacher-facing mutations    forbidden
```

`ARCHIVED` is permanently read-only. No reactivation or reverse lifecycle transition is introduced by this decision.

This MVP contract does not introduce Course versioning, revisions, draft copies, republishing, or any other mechanism for editing an already published Course. A future requirement to modify published educational material requires a separate architecture decision and implementation scope.

The immutability rule applies to teacher-facing mutation APIs and must be enforced at the appropriate Education application/domain boundary rather than by frontend behavior alone.

### Section
Groups learning material.

### Learning Unit
Logical educational unit containing activities.

### Activity
Extensible learning action. Initial types:

- LECTURE
- VIDEO
- HOMEWORK

Future examples:

- GAME
- QUEST
- ONLINE
- HOMEWORK_REVIEW
- QUIZ
- TEST
- SIMULATION
- CODING
- INTERACTIVE
- PROJECT
- DISCUSSION

Adding an Activity type must not require rewriting the Course Engine.

## 11. Content Engine

Content represents reusable educational material: text, image, video, audio, file, code and interactive content.

Activity answers **what does the learner do?** Content answers **what material does the learner use?**

Large files must use object storage rather than PostgreSQL.

The Content bounded context owns the user-owned `Content` entity and its persistence. Content ownership is derived from authenticated Identity through `owner_user_id`; clients never control ownership. The initial Content types are `ARTICLE` and `RESOURCE`, and the minimal statuses are `DRAFT` and `PUBLISHED`. Content is created as `DRAFT`. The explicit publish operation performs the only approved transition, `DRAFT → PUBLISHED`, and repeated publication is idempotent. Clients cannot mutate status through the general update contract.

### Education / Content integration boundary

`education` owns `EducationalEnvironment`, `Course`, `Section`, `LearningUnit`, and `Activity`, including their persistence. The `content` module owns its own domain entities and persistence. Neither module may directly access or modify the other module's private persistence.

The approved dependency direction is:

```text
Education application
        ↓
Content public interface
        ↓
Content implementation
```

`Activity` remains an Education entity and its persistence is owned exclusively by Education. Content is a separate bounded context. Content must not depend on Education, and Education must not access Content ORM models, repositories, infrastructure, or private implementation.

Education owns the approved N:M Activity/Content relationship. A later implementation will use an Education-owned `activity_content_links` association with an internal FK to Activity and an opaque, non-null `content_id` without a Content FK. Content persistence must not add foreign keys to `teacher_spaces`, `educational_environments`, `courses`, `sections`, `learning_units`, or `activities`.

The Content public interface is read-only: Education may look up owner-scoped safe Content reference data (`id`, type, status, and Student availability). Education cannot create, update, publish, or delete Content through this interface. Student Space consumes the Education application boundary and never Content persistence directly.

For student-facing published-course reads, Content additionally exposes the following approved read-only public operation:

```text
lookup_published(content_id: UUID)
    → ContentReference
    → ContentReferenceNotFound
    → ContentLookupUnavailable
```

`lookup_published` is deliberately distinct from the teacher-facing owner-scoped operation:

```text
lookup_owned(content_id: UUID, owner_user_id: UUID)
```

`lookup_owned` remains unchanged. Student Space must never use student identity as `owner_user_id` to resolve teacher-owned Content. `lookup_published` performs publication/availability semantics inside the Content bounded context and does not require a teacher or student owner identifier.

For `lookup_published`:

- `PUBLISHED` and student-available Content returns a safe `ContentReference`;
- DRAFT, non-public or missing Content returns `ContentReferenceNotFound`;
- technical Content lookup failure returns `ContentLookupUnavailable`.

Content ownership and persistence remain entirely inside Content. Education may consume these operations only through the public interface. Student Space never accesses Content ORM models, repositories, tables or infrastructure directly.

The approved `ContentReference` exposes only safe integration data:

```text
id
ContentType
ContentStatus
available_for_student
```

The operation is read-only and does not change the Content HTTP API. It does not create, update, publish, unpublish or delete Content. `lookup_owned` remains the owner-scoped interface for teacher-facing operations.

### Student Space read boundary

The first Student-facing read contract is:

```text
GET /api/v1/student/courses/{course_id}
```

The authenticated student identity comes from the existing authentication/session context and is not supplied as a URL owner identifier.

Student Space may read any `PUBLISHED` Course in this MVP slice. `DRAFT`, `ARCHIVED` and unknown Courses are invisible through this endpoint and return `404`.

### Activity publication and Student visibility

Activity has no independent publication or visibility lifecycle. Course publication and Activity
membership are authoritative: every Activity belonging through its Learning Unit and Section to a
`PUBLISHED` Course is Student-visible, while Activities of DRAFT or ARCHIVED Courses are outside the
published Student scope. The architecture cannot represent an individually hidden Activity inside a
`PUBLISHED` Course.

Activity visibility must not be derived from `Content.status` or `Content.available_for_student`.
Content availability controls only which associated Content references a visible Activity may expose.
Education may provide all Activity IDs belonging to a `PUBLISHED` Course through a minimal read-only
application/public boundary for Learning aggregation; Learning must not access Education persistence.
The complete decision is recorded in
[`ADR-0005`](docs/decisions/ADR-0005-activity-publication-student-visibility.md).

The dependency direction is:

```text
Student Space API
        ↓
Student/application orchestration
        ↓
Education application/public interface
        ↓
Education domain/repositories
        ↓
Content public interface
```

Education resolves the Education-owned Activity/Content associations and uses `lookup_published` to obtain safe student-visible Content references. Student Space must not bypass Education to call Content.

The minimum Student Activity representation is:

```text
id
title
type
position
contents
```

Teacher/internal fields such as `learning_unit_id`, `created_at` and `updated_at` are not part of this Student response contract unless a later architectural decision explicitly adds them.

DRAFT Content may remain associated with an Activity, but only published/student-available Content may appear in the Student response. A stale or unavailable association must not expose private Content details.

DRAFT Content may be associated, but only PUBLISHED Content is available to Student Space. Content deletion leaves a stale/unavailable association; Activity deletion removes its Education-owned association rows. No public attach/detach HTTP API is approved by this decision.

The complete contract, lifecycle/failure semantics, persistence details, alternatives, and required guards are recorded in [`ADR-0001`](docs/decisions/0001-activity-content-integration-contract.md). Runtime integration remains deferred to a separate implementation Issue.

## 12. Learning Engine

Learning owns enrollment, progress, completion and learning state. Teacher Space must not become the owner of student progress.

## 13. Assessment Engine

Assessment owns submissions, assessment results, grades and feedback.

Example flow:

```text
Homework → Submission → Teacher Review → Assessment → Feedback
```

## 14. Commerce Engine

Commerce is independent and owns pricing, purchases, payments, payment methods, providers, subscriptions and transactions.

Courses may be FREE or PAID. Paid courses contain amount and currency.

Payment providers must be hidden behind a `PaymentProvider` abstraction. Domain code must not import provider SDKs directly.

## 15. Advertising Engine

Advertising is independent. A platform policy may allow advertising for free content and disallow it for paid content, but this decision belongs to backend policy/domain logic, not frontend guesses.

## 16. Events

The platform should be event-ready. Examples include CourseCreated, CoursePublished, ActivityCreated, HomeworkSubmitted and PaymentCompleted.

Initially the event mechanism may be internal. Do not introduce an external broker without a demonstrated need.

## 17. Module dependency rules

User spaces may depend on domain engines:

```text
Teacher → Education
Teacher → Content
Teacher → Commerce
```

Domain engines must not depend on user spaces:

```text
Education ✗→ Teacher
Content ✗→ Teacher
Commerce ✗→ Teacher
```

Circular dependencies are forbidden. If a task appears to require one, stop and report the architectural conflict.

Other modules may use only public interfaces of a module, not its private infrastructure implementation.

## 18. Database ownership

Each module owns its own tables. One module must not directly modify another module's tables.

PostgreSQL requirements:

- foreign keys where appropriate
- unique constraints
- indexes
- timestamps
- transactions
- migrations

Use UUIDs for public identifiers where appropriate.

## 19. Migrations

Use Alembic. Every schema change requires a migration and appropriate tests. Do not rewrite already-applied migrations to hide problems.

## 20. API

All public APIs use `/api/v1/`, Pydantic schemas, validation, standardized errors, pagination/filtering where applicable, and backend authorization.

ORM models must not be returned directly as API contracts.

OpenAPI is the official API contract.

## 21. Frontend

```text
apps/frontend/src/
├── app/
├── modules/
│   ├── teacher/
│   ├── education/
│   ├── content/
│   └── learning/
└── shared/
    ├── ui/
    ├── api/
    ├── types/
    └── utils/
```

Shared UI components must not contain business logic.

## 22. Course Builder

The first builder must support:

- create
- edit
- delete
- reorder where needed
- save draft
- preview
- publish

Initial structure:

```text
Course
└── Section
    └── Learning Unit
        └── Activity
```

Drag-and-drop is optional and must not be allowed to distort the domain model.

## 23. Storage

Use an `ObjectStorage` abstraction with local MinIO and an S3-compatible implementation. PostgreSQL stores metadata, not large binary files.

## 24. Security

Mandatory principles:

- secure password hashing
- backend authorization
- input validation
- upload validation
- secrets outside Git
- least privilege
- audit logging for sensitive operations where appropriate
- rate limiting where required

Frontend checks never replace backend authorization.

## 25. Secrets

Never commit API keys, passwords, tokens, private keys, payment credentials or production secrets. Use environment variables and keep `.env.example` in the repository.

## 26. Testing

Unit tests cover domain rules and application logic. Integration tests cover API, repositories, database and module interactions. E2E tests cover critical user journeys.

The first critical E2E journey is:

```text
Login → Teacher Dashboard → Create Educational Environment → Create Course
→ Create Section → Create Learning Unit → Create Activity → Save Draft
→ Preview → Publish
```

## 27. CI

Every PR should run applicable:

- lint
- type checks
- unit tests
- integration tests
- build

E2E and security/dependency checks may be added as the project matures.

## 28. Docker

Initial local infrastructure:

```text
frontend
backend
postgres
minio
```

Use Docker Compose.

## 29. Architecture decisions

Architectural decisions live under `docs/decisions/` and should use ADR format:

```text
Context
Decision
Alternatives
Consequences
```

Architecture must not be silently changed. If a task requires changing module boundaries, stack, database architecture, authentication, authorization or event architecture, stop and request an architectural decision.

## 30. MVP sequence

The first vertical slice is:

```text
Identity
→ Teacher Space
→ Educational Environment
→ Course
→ Section
→ Learning Unit
→ Activity
→ Draft
→ Preview
→ Publish
```

Initial activities: LECTURE, VIDEO, HOMEWORK.

Future systems must not be implemented in advance merely for speculation.

## 31. Extensibility principle

Optional systems should be removable with minimal impact on the rest of the platform. Future systems may include Student Space, Parent Space, Mentor Space, Admin Space, Gamification, AI, Analytics, Marketplace and Community.

The architecture must support adding these systems without requiring a rewrite of the platform core.

## 32. Definition of Done

A task is complete only when:

1. Scope is implemented.
2. Acceptance criteria are met.
3. Architecture is respected.
4. Relevant tests pass.
5. CI passes.
6. No unauthorized changes remain.
7. PR is documented.
8. Known limitations are stated.

## 33. Governance and mandatory implementation rules

The active governance roles are:

- **Human Project Owner** — final repository merge authority;
- **Project Architect — ChatGPT 5.6 Luna** — final authority for architecture, scope, requirements and acceptance of external review findings;
- **Implementation Agent — Arena** — sole active implementation agent.

DeepSeek Flash and DeepSeek Pro are execution/review models operating under these roles, not autonomous governance authorities. DeepSeek Flash is the default execution-assistance model for routine implementation tasks (configured as DeepSeek V4 Flash). DeepSeek Pro is the escalation model for unusually complex, security-sensitive, architecture-heavy or ambiguous tasks (configured as DeepSeek V4 Pro).

DeepSeek execution assistance does not create independent scope or architectural authority. Arena remains responsible for implementation, tests, commits and Pull Requests. DeepSeek output and recommendations remain advisory unless accepted by ChatGPT 5.6 Luna. Arena validates implementation assistance only within the approved Issue scope; architecture, scope, requirements and PR acceptance remain under ChatGPT 5.6 Luna, and final merge authority remains with the Human Project Owner.

DeepSeek V4 Flash and DeepSeek V4 Pro may participate in external review when explicitly assigned. External review is separate from execution assistance and remains advisory. Review recommendations must be evaluated and accepted or rejected by ChatGPT 5.6 Luna.

The Implementation Agent is not the autonomous owner of project architecture and must not merge Pull Requests. DeepSeek execution/review models have no architecture, scope or merge authority. ChatGPT 5.6 Luna accepts PRs from the architecture and scope perspective. The Human Project Owner performs the final merge after Project Architect approval and all required checks/reviews have passed.

Every repository change, including governance and documentation changes, follows:

```text
Issue → branch → Arena implementation
→ DeepSeek Flash by default / Pro escalation when required
→ tests → PR → review
→ Project Architect / ChatGPT approval (ChatGPT 5.6 Luna)
→ Human Project Owner merge
```

Before every task the Implementation Agent MUST read:

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. relevant ADRs
4. the assigned GitHub Issue
5. relevant existing code

Before every significant change the Implementation Agent MUST verify:

1. Is this explicitly allowed?
2. Is this explicitly forbidden?
3. Is it inside the task scope?
4. Does it comply with architecture?
5. Does it change an existing contract?
6. Is the change actually necessary?

The rules must be checked continuously, not just once at task start.

### The Implementation Agent must

- implement only assigned scope;
- inspect existing code before changing it;
- preserve module boundaries;
- add/update tests;
- run applicable checks;
- inspect the final diff;
- document PR changes and tests;
- report architectural impact;
- report known limitations;
- stop when an important decision is ambiguous.

### The Implementation Agent must not

- change architecture without approval;
- introduce microservices or prohibited infrastructure without approval;
- add speculative future features;
- perform unrelated refactoring;
- add dependencies without justification;
- silently change public APIs or database contracts;
- delete or disable tests to make CI pass;
- bypass security checks;
- commit secrets;
- merge its own PR or any PR;
- invent product decisions.

### STOP rule

If the Implementation Agent is unsure whether an action is permitted, whether it belongs to scope, or how to resolve an architectural conflict:

```text
STOP
→ DO NOT GUESS
→ REPORT THE CONFLICT
→ WAIT FOR A DECISION
```

## 34. Instruction priority

When instructions conflict, use this priority:

1. Explicit Human Project Owner decision for repository administration and merge authority
2. Explicit Project Architect decision for architecture, scope, requirements and accepted review findings
3. `ARCHITECTURE.md`
4. Approved ADRs
5. Assigned GitHub Issue
6. Existing project conventions
7. The Implementation Agent's engineering preference
