## {{PRODUCT}} — blueprint-driven workflow (speckit-blueprint)

This project is built from `{{BLUEPRINT}}`, one epic at a time, with Spec Kit.

- For any request about building, continuing, changing scope or "what's next", use the
  `speckit-blueprint-flow` skill. It reads the project state and picks the next command.
- Flow per epic: `/speckit-blueprint-compile Enn` → `/speckit-tasks` → `/speckit-analyze` →
  `/speckit-implement` (its hooks load the spec and run `/speckit-blueprint-review`).
- Files in `{{SPECS}}/*/` other than `tasks.md` and `review.md`, and `.specify/memory/constitution.md`,
  are compiled. Never edit them by hand: product or AC changes go through `/speckit-blueprint-amend`.
- Do not read `{{BLUEPRINT}}` whole. Use `blueprint.py section <n>` or `blueprint.py find <ID>`
  (in `.specify/extensions/blueprint/scripts/`) for anything outside the active feature folder.
- Read files over 200 lines by range: `grep -n` first, then only the lines you need. Do not re-read
  unchanged files in the same session.
- Decisions the blueprint does not cover: add a `DR-nn` to `docs/DECISIONS.md` (index row too).
- Start a fresh session for each epic's implementation.
