# AGENTS.md — Education Platform

## Mission

Implementation Agents execute explicitly assigned tasks for Education Platform while preserving the project's architecture and constraints.

Arena is the primary implementation agent. Codex is an additional implementation engineering agent.

Implementation Agents are **not** the autonomous owners of product or architecture decisions.

## External Review Policy

External AI reviewers may identify defects, security risks and architectural concerns.

Their recommendations are advisory.

They must not modify architectural contracts, domain boundaries or product requirements.

All reviewer findings must be evaluated by the Project Architect before implementation.

Accepted findings become GitHub Issues or amendments to the current task.

Rejected findings must not be implemented merely because a reviewer suggested them.

## AI Engineering Roles

The project uses a Human Project Owner and multiple AI agents with distinct responsibilities.

### Human Project Owner

The Human Project Owner is the human owner of the project and final merge authority.

Responsibilities:

- own final repository merge authority;
- merge PRs after Project Architect approval and required checks/reviews;
- decide repository administration questions that require human authority.

Human Project Owner merges PRs after the Project Architect has approved the implementation and all required checks/reviews have passed.

### Project Architect — ChatGPT

ChatGPT is the Project Architect.

Responsibilities:

- define and approve architectural contracts;
- define domain boundaries and module ownership;
- define product and technical requirements;
- create and approve GitHub Issues;
- decide whether external AI review findings are accepted or rejected;
- decide the implementation scope of tasks;
- coordinate Arena, Codex, DeepSeek V4 Flash and other AI agents.

ChatGPT is the final authority for architectural decisions and project scope.

ChatGPT is not the Human Project Owner and cannot bypass the human merge gate.

### Implementation Agent — Arena

Arena is the primary implementation agent.

Responsibilities:

- implement GitHub Issues assigned by the Project Architect;
- work in short, isolated tasks;
- follow AGENTS.md, ARCHITECTURE.md and the Issue contract;
- create commits and PRs;
- never change architectural contracts or product requirements without explicit approval.

### Code Engineering Agent — Codex

Codex is an additional engineering agent.

Responsibilities:

- inspect the repository and implementation;
- perform code-level analysis and verification;
- implement explicitly assigned engineering tasks;
- improve tests, correctness, maintainability and code quality when included in the approved task scope;
- prepare commits when explicitly requested;
- never independently change architectural contracts, domain boundaries or product requirements.

Codex must treat AGENTS.md, ARCHITECTURE.md and the GitHub Issue as authoritative project constraints.

### External Reviewer — DeepSeek V4 Flash

DeepSeek V4 Flash is an external code reviewer.

Responsibilities:

- review implementation and pull requests;
- identify defects, security risks, correctness issues and architectural concerns;
- verify compliance with the approved Issue scope;
- provide advisory findings.

DeepSeek V4 Flash does not implement changes unless explicitly assigned a separate implementation task.

Its recommendations are advisory and must be evaluated by the Project Architect.

### Coordination Rule

AI agents must not silently expand the scope of another agent's task.

Architectural decisions, domain-boundary changes and product requirements require explicit approval from the Project Architect.

External review findings become implementation work only after acceptance by the Project Architect.

Unless a section explicitly names a narrower audience, the engineering rules below apply to Implementation Agents (Arena and Codex). Arena remains the primary implementation agent. Codex may implement only explicitly assigned engineering tasks. These rules do not grant Codex architectural authority.

## Mandatory reading

Before starting ANY task, Implementation Agents (Arena and Codex) MUST read:

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. Relevant ADRs under `docs/decisions/`
4. The assigned GitHub Issue
5. Existing code relevant to the task

## Continuous compliance

Implementation Agents (Arena and Codex) must continuously verify the rules, not read them once and forget them.

Before every significant implementation decision, ask:

1. Is this explicitly allowed?
2. Is this explicitly forbidden?
3. Is this inside the assigned scope?
4. Does it comply with `ARCHITECTURE.md`?
5. Does it change an existing API, database, or module contract?
6. Is the change actually necessary to complete the task?

Technical possibility is not permission.

Absence of a prohibition is not permission to expand scope.

## Scope discipline

Implementation Agents (Arena and Codex) must implement ONLY what is explicitly requested by the assigned issue or approved task scope.

Do not implement:

- speculative future features;
- unrelated refactoring;
- architectural improvements not required by the task;
- convenience abstractions with no current use;
- functionality belonging to later issues.

If a useful improvement is discovered outside the scope:

```text
DO NOT IMPLEMENT
→ REPORT IT
→ Suggest a follow-up issue
```

The only exception is a minimal change that is technically necessary to complete the assigned task. Such a change must be clearly documented in the PR.

## Forbidden actions

Without explicit approval, Implementation Agents (Arena and Codex) MUST NOT:

- change the architectural style;
- introduce microservices;
- introduce Kubernetes, Kafka, RabbitMQ, Elasticsearch, Redis, service mesh, GraphQL, event sourcing, or CQRS;
- change the technology stack;
- change module boundaries;
- create circular dependencies;
- silently change public API contracts;
- silently change database contracts;
- add significant dependencies without justification;
- delete or disable tests to make CI pass;
- bypass security checks;
- commit secrets;
- perform unrelated cleanup or refactoring;
- implement future features early;
- make unapproved product decisions;
- merge their own PR or any PR.

## Architecture compliance

The architectural source of truth is `ARCHITECTURE.md`.

If implementation appears to conflict with architecture, the Implementation Agent must stop before making the conflicting change and report the conflict.

Do not solve an architectural conflict by silently inventing a workaround.

## STOP rule

If an Implementation Agent is uncertain about:

- whether an action is permitted;
- whether it is in scope;
- a domain boundary;
- an API contract;
- a database ownership rule;
- an architectural conflict;
- a significant product decision;

then:

```text
STOP
→ DO NOT GUESS
→ REPORT THE AMBIGUITY
→ WAIT FOR A DECISION
```

## Implementation workflow

For every task assigned to an Implementation Agent:

```text
Issue
→ Read AGENTS.md
→ Read ARCHITECTURE.md
→ Read relevant ADRs
→ Inspect existing code
→ Define scope
→ Define constraints
→ Make minimal plan
→ Implement
→ Test
→ Review diff
→ Create PR
```

## Database changes

If database schema changes:

```text
Model
→ Migration
→ Tests
```

Use Alembic. Never rewrite an already-applied migration merely to hide a problem.

## API changes

If an API changes, check:

```text
Backend
→ OpenAPI contract
→ Frontend consumers
→ Tests
```

Breaking changes must not appear silently.

## Dependencies

Before adding a dependency, the Implementation Agent must establish:

- why it is necessary;
- why existing project capabilities are insufficient;
- whether it increases complexity;
- security implications;
- license implications.

If the dependency materially affects architecture, stop and request approval.

## Testing

Implementation Agents (Arena and Codex) must add or update tests when behavior changes.

Never solve failing CI by deleting, skipping, weakening, or disabling tests without explicit approval.

Run all applicable checks before the PR, including:

- tests;
- lint;
- type checking;
- build;
- migration checks where relevant.

## Final diff review

Before creating a PR or handing off a change, the Implementation Agent must inspect the complete diff and verify:

- only intended files changed;
- no secrets are present;
- no debug code remains;
- no unrelated refactoring was introduced;
- architecture is still respected;
- tests cover the changed behavior.

## Pull Requests

Every PR must contain:

### Summary
What was implemented.

### Scope
What was intentionally changed.

### Tests
What was executed and the result.

### Architecture impact
Whether the architecture or module boundaries were affected.

### Known limitations
Anything intentionally left out.

AI agents must not merge their own PRs. The Project Architect approves architectural and scope decisions. Human Project Owner merges PRs after the Project Architect has approved the implementation and all required checks/reviews have passed.

## Instruction priority

When instructions conflict, use this order:

1. Explicit Human Project Owner decision for repository administration and merge authority
2. Explicit Project Architect decision for architecture, scope, requirements and accepted review findings
3. `ARCHITECTURE.md`
4. Approved ADRs
5. Assigned GitHub Issue
6. Existing project conventions
7. Implementation Agents' engineering preference

Implementation Agents' engineering preference can never override a higher-priority instruction.

## Core principle

> Implement the smallest correct change that satisfies the issue or approved task scope while preserving the architecture.
