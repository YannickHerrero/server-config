---
name: three-stage-workflow
description: Enforces a separate plan, implement-and-test, and release workflow for any software project. Use for feature requests, bug fixes, repository changes, commits, pushes, and releases.
---

# Three-stage delivery workflow

Project-local instructions override this skill.

## Stages

Never combine these stages unless the user explicitly asks to advance.

1. **Plan** — inspect the repository and report the intended behavior, affected files, architecture/state/lifecycle concerns, test and verification strategy, risks, and atomic commit sequence. Do not edit files, run builds/tests, commit, push, or release.
2. **Implement and test** — begin only after the user explicitly approves the plan or asks to implement it. Make small independently valid changes, test according to project rules, and create atomic commits. Do not push or release.
3. **Release** — begin only after the user explicitly asks to push, publish, deploy, upload, or release. Run release preflight, push only intended commits, and use the repository's documented release workflow.

## Rules

- Read project instructions before acting and obey them over this skill.
- Before edits or commits, inspect Git status and never overwrite or stage unrelated user changes.
- Be explicit about what verification proves and what requires manual confirmation.
- At the end of every stage, state the result and the exact user action needed to move forward, for example: `Plan ready; say “implement and test it” to continue.`
