---
description: "Compile the constitution, review checklist, decisions log and CLAUDE.md block from the blueprint"
---

# Bootstrap the project from the blueprint

Run once after the blueprint is approved and linted, and again whenever an amendment touches the sections
the constitution is built from (by default §12.10, §13.2, §13.5–13.7, §13.9–13.10, §14.2, §14.3, §14.8).

## User Input

```text
$ARGUMENTS
```

## Steps

1. Confirm the blueprint lints clean: `python3 .specify/extensions/blueprint/scripts/blueprint.py lint`
   must exit 0. If it does not, follow `/speckit-blueprint-lint` to fix it first.
2. Run:

   ```bash
   python3 .specify/extensions/blueprint/scripts/blueprint.py bootstrap
   ```

   It writes, deterministically:
   - `.specify/memory/constitution.md` — five fixed principles (blueprint is the source of truth, evidence
     or silence, tests first and green gate, copy by ID and decisions by record, review before done) plus
     the configured blueprint sections verbatim. Version bumps only when the content changed.
   - `docs/REVIEW-CHECKLIST.md` — blueprint §14.4 verbatim.
   - `docs/DECISIONS.md` — created once, with an index of the blueprint's DRs; sessions append to it.
   - `CLAUDE.md` — a managed block between `speckit-blueprint:start/end` markers; the rest of the file is
     left alone.
3. If the JSON reports `missing_sections`, the blueprint lacks a section the config expects: fix the
   blueprint, or remove the number from `constitution_sections` in
   `.specify/extensions/blueprint/blueprint-config.yml` if it truly does not apply.
4. Do not run `/speckit-constitution` afterwards: it would rewrite the compiled constitution from its
   generic template.
5. Report the constitution size and version, and the next step from
   `python3 .specify/extensions/blueprint/scripts/blueprint.py status --brief`.
