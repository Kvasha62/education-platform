# Contributing to Education Platform

## Development model

The project uses GitHub Issues and Pull Requests.

```text
Issue
→ Branch
→ Implementation
→ Tests
→ Pull Request
→ Review
→ Project Architect approval
→ Merge
```

The `main` branch is the stable integration branch.

The Human Project Owner is the human owner of the project and final merge authority.

The Project Architect is ChatGPT and is responsible for architecture, scope, requirements and acceptance or rejection of external review findings.

Human Project Owner merges PRs after the Project Architect has approved the implementation and all required checks/reviews have passed.

AI agents do not merge their own PRs. The Project Architect approves architectural and scope decisions; the Human Project Owner performs the final merge.

## Branches

Use short-lived task branches named after the issue, for example:

```text
EDU-001-repository-foundation
EDU-002-identity-foundation
```

Do not commit task work directly to `main` unless explicitly authorized.

## One task, one PR

A normal development unit is:

```text
1 GitHub Issue
1 task branch
1 Pull Request
```

Keep PRs focused and reviewable.

The Human Project Owner performs the final merge only after Project Architect approval and all required checks/reviews have passed.

## Issue requirements

A development issue should define:

- Goal
- Scope
- Acceptance Criteria
- Constraints
- Explicit Do Not items
- References to relevant architecture documents

## Pull Request requirements

A PR should explain:

- what changed;
- why it changed;
- how it was tested;
- architecture impact;
- known limitations.

## Architectural changes

Do not silently change architecture.

If a task requires a significant architectural decision:

```text
STOP
→ Discuss decision
→ Update architecture / ADR if approved
→ Implement
```

Architectural and scope decisions require Project Architect approval and do not bypass the Human Project Owner merge gate.

## Quality

Before submitting a PR, run the applicable tests, lint, type checks, build and migration checks.

Never disable tests or CI merely to make a PR pass.
