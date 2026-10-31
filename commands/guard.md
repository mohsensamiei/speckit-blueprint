---
description: "Internal: Claude Code PreToolUse guard that blocks hand edits of compiled files"
scripts:
  py: scripts/blueprint.py hook guard
---

# Blueprint guard (event handler)

This command exists so spec-kit can register it as a Claude Code `PreToolUse` hook. It is not meant to be
run by hand.

When an `Edit`, `Write`, `MultiEdit` or `NotebookEdit` targets a compiled file — `spec.md`, `plan.md`,
`research.md`, `data-model.md`, `quickstart.md` or `contracts/*` inside a feature folder that has a
`.blueprint.json`, a constitution compiled by `/speckit-blueprint-bootstrap`, or the managed
`speckit-blueprint:rules` block inside a project-owned constitution (the rest of that file stays editable) — the hook exits with
code 2 and tells the agent to amend the blueprint and recompile instead. `tasks.md` and `review.md` stay
editable.

If you were invoked directly: explain the rule above and stop. To switch the guard off for a project, set
`guard: false` in `.specify/extensions/blueprint/blueprint-config.yml`.
