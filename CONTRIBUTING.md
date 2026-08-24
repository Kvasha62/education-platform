# Contributing to Education Platform

## Development model

The project uses GitHub Issues and Pull Requests. This workflow applies to every repository change, including governance and documentation changes.

```text
Issue
→ Branch
→ Arena implementation
  (DeepSeek Flash by default; Pro escalation when required)
→ Tests
→ Pull Request
→ Review
→ Project Architect / ChatGPT approval
→ Human Project Owner merge
```

The `main` branch is the stable integration branch.

The Human Project Owner is the human owner of the project and final merge authority.

The Project Architect is ChatGPT 5.6 Luna and is responsible for architecture, scope, requirements and acceptance or rejection of external review findings.

DeepSeek Flash is the default execution-assistance model for Arena (configured as DeepSeek V4 Flash). DeepSeek Pro is used as an escalation model for unusually complex, security-sensitive, architecture-heavy or ambiguous tasks (configured as DeepSeek V4 Pro). Neither model has authority over architecture, scope, requirements, PR acceptance or merge decisions.

Execution assistance and external review are distinct activities. DeepSeek execution output and review findings remain advisory until evaluated and accepted by ChatGPT 5.6 Luna.

Human Project Owner merges PRs after the Project Architect has approved the implementation and all required checks/reviews have passed.

AI agents and DeepSeek execution models do not merge their own PRs. The Project Architect / ChatGPT 5.6 Luna accepts PRs from the architecture and scope perspective; the Human Project Owner performs the final merge.

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
