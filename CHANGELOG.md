# Changelog

## 0.2.0 — 2026-10-28

First release validated end to end with Claude Code: a Persian one-paragraph idea taken through
discover (intake, research, decision brief, a 133 KB blueprint, lint clean), bootstrap, and four epics of
compile → tasks → analyze → implement → review, every session started with "continue" only. Result:
130/130 tasks ticked, 4 reviews DONE, 217 tests green at 97.8% coverage, no compiled file edited by hand.

- The context hook requires ticking each task in tasks.md as soon as it is done (resume point and
  progress source), never in bulk at the end.

## 0.1.1 — 2026-10-27

From an end-to-end run with Claude Code (bootstrap → compile → tasks → analyze → implement → review):

- `blueprint.py lint` runs the linter and the reference check in one command; commands use it.
- `refs`/`lint` output explains the definition shapes compile recognises when an ID is unresolved.
- The flow skill keeps going through steps on "continue" and stops only at the plan/build session
  boundary, a user gate or an unfixable problem; compiling no longer asks for a fresh session.

## 0.1.0 — 2026-10-27

First release, Claude Code only, tested with Spec Kit 1.2.4.

- `discover`, `lint`: the idea-to-blueprint method (intake, research, decision brief, blueprint, linter),
  adapted to the spec-kit build flow (`references/speckit-flow.md`).
- `compile`: one epic → spec-kit feature folder, with every referenced ID resolved; trace for staleness.
- `bootstrap`: constitution, review checklist, decisions log and a managed CLAUDE.md block.
- `context` (before_implement) and `review` (after_implement) hooks.
- `amend`: in-place blueprint amendments with recompilation of affected epics.
- `flow` skill and `status`; Claude Code SessionStart status and a PreToolUse guard for compiled files.
