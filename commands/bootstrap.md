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
     the configured blueprint sections verbatim. Two modes (`constitution.mode` in the JSON):
     - `own` (the constitution was missing or still the `specify init` template): the whole file is
       compiled. Version bumps only when the content changed.
     - `append` (the project already has its own constitution): the file stays the project's. Bootstrap
       keeps one managed block between `speckit-blueprint:rules:start/end` markers, inserted before
       `## Governance`. The block applies only to features compiled from the blueprint and yields to the
       project's principles. When the block is added or its rules change, bootstrap follows Spec Kit's
       constitution governance for the project: it bumps the version (minor by default,
       `constitution_version_bump` in the config), sets Last Amended to today and adds a line to the Sync
       Impact Report. A re-run with unchanged rules changes nothing.
   - `docs/REVIEW-CHECKLIST.md` — blueprint §14.4 verbatim, unless the project already has its own
     checklist there (then it is left alone and the review hook uses it).
   - `docs/DECISIONS.md` — created once, with an index of the blueprint's DRs; sessions append to it.
   - `CLAUDE.md` — a managed block between `speckit-blueprint:start/end` markers; the rest of the file is
     left alone.
3. If the JSON reports `missing_sections`, the blueprint lacks a section the config expects: fix the
   blueprint, or remove the number from `constitution_sections` in
   `.specify/extensions/blueprint/blueprint-config.yml` if it truly does not apply.
4. In `own` mode, do not run `/speckit-constitution` afterwards: it would rewrite the compiled
   constitution from its generic template. In `append` mode the project may keep amending its own
   principles as usual; if it ever drops the managed block, run bootstrap again.
   Tell the user the version change from the JSON (`constitution.version`). If the project's governance
   asks for more than a version bump (an approval, a review), say so; bootstrap did not do that part.
5. Report the constitution size and version, and the next step from
   `python3 .specify/extensions/blueprint/scripts/blueprint.py status --brief`.
