## {{PRODUCT}} — blueprint-driven features (speckit-blueprint)

Features whose folder in `{{SPECS}}/` contains `.blueprint.json` are compiled from `{{BLUEPRINT}}`, one
epic at a time, with Spec Kit. Other features follow this project's own workflow and rules.

- For a new idea, "continue" on a blueprint epic, a change to a blueprint epic's scope or ACs, or
  "what's next" in the blueprint, use the `speckit-blueprint-flow` skill. It reads the project state and
  picks the next command.
- Flow per epic: `/speckit-blueprint-compile Enn` → `/speckit-tasks` → `/speckit-analyze` →
  `/speckit-implement` (its hooks load the spec and run `/speckit-blueprint-review`).
- In those feature folders every file other than `tasks.md` and `review.md` is compiled, and so is the
  blueprint part of `.specify/memory/constitution.md`. Never edit them by hand: product or AC changes go
  through `/speckit-blueprint-amend`.
- Do not read `{{BLUEPRINT}}` whole. Use `blueprint.py section <n>` or `blueprint.py find <ID>`
  (in `.specify/extensions/blueprint/scripts/`) for anything outside the active feature folder.
- Read files over 200 lines by range: `grep -n` first, then only the lines you need. Do not re-read
  unchanged files in the same session.
- Decisions the blueprint does not cover: add a `DR-nn` to `{{DECISIONS}}` (index row too).
- Start a fresh session for each epic's implementation.
- Where the rest of this file (and anything it imports) or the constitution's own principles set a
  stricter rule, that rule wins.
