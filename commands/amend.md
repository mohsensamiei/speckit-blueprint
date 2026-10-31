---
description: "Change the blueprint deliberately (A-nn amendment) and recompile the affected epics"
---

# Amend the blueprint

The blueprint is the source of truth. When reality or the user disagrees with it, the blueprint changes
first, explicitly, and the compiled specs follow. This is the only way spec files change.

`docs/DECISIONS.md` and `docs/REVIEW-CHECKLIST.md` below are the default paths; a project can move them
(`decisions_path`, `review_checklist_path` in the config). `blueprint.py status --json` reports the ones in
use as `decisions` and `review_checklist`.

## User Input

```text
$ARGUMENTS
```

## Steps

1. **Understand the change.** Restate it in one or two lines: what changes, for which epic(s), and why.
   Scope additions (a new capability) are not amendments: they become new stories in a later epic — use
   `/speckit-blueprint-discover` in incremental mode for anything bigger than a story or two.

2. **Find what it touches without reading the whole blueprint.** Use IDs and section numbers:

   ```bash
   python3 .specify/extensions/blueprint/scripts/blueprint.py find E03-S02 SCR-04 ENT-Order
   python3 .specify/extensions/blueprint/scripts/blueprint.py section 12.4
   grep -n "CP-SCR04-" docs/BLUEPRINT.md
   ```

3. **Ask first** when the change alters user-visible behaviour, money, data retention or security, unless
   the user's message already decided it. Smaller technical amendments can go ahead and be reported.

4. **Edit the blueprint in place.** Change the affected AC, copy row, entity, endpoint or decision where it
   lives, and mark it `(amended A-nn)`. Never append a "version 2" section. Add a row to the Amendments log
   in the Session Protocol section: `A-nn | date | epic/story | what changed | why | approved by`.
   If a decision changed, mark the old DR superseded and add the new one. Keep the evidence rules: new
   external facts carry `[VERIFIED — S-nn, date]` or `[ASSUMED — why]`.

5. **Lint**: `python3 .specify/extensions/blueprint/scripts/blueprint.py lint` until it exits 0
   (see `/speckit-blueprint-lint` for how to fix findings).

6. **Propagate.** Run:

   ```bash
   python3 .specify/extensions/blueprint/scripts/blueprint.py stale
   ```

   For each listed epic:
   - no tasks done (`tasks_done` = 0): recompile with `compile <Enn>`; if it had a tasks.md, regenerate it
     with `/speckit-tasks` (the old one no longer matches).
   - partly or fully built: do not recompile over finished work silently. Tell the user what changed under
     built code and propose either recompiling with `--force` and regenerating tasks (the implement step
     then reworks only what changed), or a follow-up story in a later epic. The user decides. If they keep
     the built epic as it is (the change is covered elsewhere, or does not affect the built code), record it
     so status stops reporting the change:
     `python3 .specify/extensions/blueprint/scripts/blueprint.py accept <Enn> --note "<why, e.g. covered by E04 (A-03)>"`.
   - If constitution sections changed, also run `/speckit-blueprint-bootstrap`.

7. Report: the amendment ID, files and epics affected, what was recompiled, and what waits on the user.
