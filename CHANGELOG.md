# Changelog

## 0.1.0 — 2026-10-27

First release, Claude Code only, tested with Spec Kit 1.2.4.

- `discover`, `lint`: the idea-to-blueprint method (intake, research, decision brief, blueprint, linter),
  adapted to the spec-kit build flow (`references/speckit-flow.md`).
- `compile`: one epic → spec-kit feature folder, with every referenced ID resolved; trace for staleness.
- `bootstrap`: constitution, review checklist, decisions log and a managed CLAUDE.md block.
- `context` (before_implement) and `review` (after_implement) hooks.
- `amend`: in-place blueprint amendments with recompilation of affected epics.
- `flow` skill and `status`; Claude Code SessionStart status and a PreToolUse guard for compiled files.
