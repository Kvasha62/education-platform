# ADR-0013 Amendment 001 — Teacher AssessmentDefinition Management Read API

- **Status:** Accepted
- **Date:** 2026-08-28
- **Amends:** ADR-0013 — Teacher Activity Assessment Entry Contract

## Context

ADR-0013 defines the AssessmentDefinition reference exposed by the Teacher Activity projection. Its purpose is to let Teacher Activity UI determine whether an Activity has an AssessmentDefinition without introducing an additional discovery request.

ADR-0013 therefore rejects a dedicated lookup endpoint whose purpose is only to discover the AssessmentDefinition relationship or obtain its identifier.

A subsequent Teacher AssessmentDefinition Management capability requires a resource-level READ operation so a teacher can retrieve the complete AssessmentDefinition associated with an Activity. This is a different responsibility from the entry-signal projection defined by ADR-0013.

## Decision

ADR-0013's prohibition is clarified:

> The prohibition against a separate AssessmentDefinition lookup endpoint applies specifically to an endpoint whose purpose is to discover whether an AssessmentDefinition exists for an Activity or to obtain its identifier for entry/navigation purposes.

The prohibition does **not** apply to a separately defined Teacher AssessmentDefinition Management API whose purpose is to retrieve the complete AssessmentDefinition resource for management.

Therefore the Teacher AssessmentDefinition Management contract may define:

```text
GET /api/v1/teacher-spaces/{teacher_space_id}/activities/{activity_id}/assessment-definition
```

provided that:

1. the operation belongs to the Teacher AssessmentDefinition Management API;
2. it returns the complete AssessmentDefinition management representation rather than merely its identifier;
3. Teacher Space authorization is enforced;
4. the Activity belongs to the specified Teacher Space;
5. the AssessmentDefinition belongs to the specified Activity;
6. the operation does not replace or duplicate the AssessmentDefinition identity projection defined by ADR-0013.

## Relationship with ADR-0013

ADR-0013 remains authoritative for the Teacher Activity projection:

```text
Activity
  |
  | assessment_definition_id
  v
Teacher Activity projection
```

The projection continues to use Assessment's public:

```text
AssessmentDefinitionIdLookup.get_id_for_activity(activity_id)
```

The projection remains the preferred mechanism for deciding whether the Teacher Activity UI should expose the Assessment review entry point.

The management READ operation has a different purpose:

```text
Teacher
  |
  | management request
  v
Teacher AssessmentDefinition API
  |
  v
complete AssessmentDefinition
```

It is therefore not a violation of ADR-0013.

## API Boundary

The Teacher AssessmentDefinition Management API may expose the Activity-scoped resource READ operation:

```text
GET /api/v1/teacher-spaces/{teacher_space_id}/activities/{activity_id}/assessment-definition
```

This is a **resource management operation**, not an entry-signal lookup endpoint.

It must return the complete management representation defined by the subsequent Teacher AssessmentDefinition Management contract.

It must not be introduced into the Teacher Activity projection merely to obtain `assessment_definition_id`.

## Scope and Authorization

The management API remains subject to the existing Teacher Space authorization boundary.

The required scope chain is:

```text
Teacher
  |
  v
Teacher Space
  |
  v
Activity
  |
  v
AssessmentDefinition
```

A teacher must not access an AssessmentDefinition through an Activity outside the teacher's Teacher Space.

## Non-Goals

This amendment does not itself define:

- AssessmentDefinition creation;
- AssessmentDefinition update semantics;
- AssessmentDefinition archive semantics;
- request/response DTOs;
- validation rules;
- HTTP error semantics;
- database migrations;
- UI behavior.

Those responsibilities belong to the Teacher AssessmentDefinition Management contract.

## Consequences

### Positive

- ADR-0013 remains valid for the projection/entry-signal use case.
- Teacher Activity does not need an additional lookup request.
- Teacher AssessmentDefinition Management can expose a complete resource READ operation.
- API responsibilities remain separated by use case.
- AssessmentDefinition persistence remains owned by Assessment.

### Negative

Two concepts must remain distinct:

1. **AssessmentDefinition identity projection** — defined by ADR-0013.
2. **AssessmentDefinition management resource** — defined by the Teacher AssessmentDefinition Management contract.

Implementations must preserve this distinction.

## Updated Interpretation of ADR-0013

ADR-0013's rejected alternative involving:

```text
GET /assessment-definitions/{id}
GET /activities/{activity_id}/assessment-definition
```

is interpreted as rejected when introduced as a redundant lookup mechanism for discovering or exposing the AssessmentDefinition relationship already represented by the Activity projection.

It is not a permanent prohibition against a later resource-level Teacher AssessmentDefinition Management READ operation that is separately contracted and authorized.

## Decision

**Accepted.**

ADR-0013 retains its original architectural intent. This amendment explicitly permits a separately contracted Teacher AssessmentDefinition Management READ API.
