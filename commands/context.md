---
description: "Load the active feature's spec and build rules before implementation (hook)"
---

# Load build context (before_implement hook)

`/speckit-implement` reads tasks.md, plan.md and the optional design files, but not spec.md. In a
blueprint project spec.md holds the acceptance criteria, edge cases and exact copy that decide whether the
work is right, so this hook puts it in front of the implementation.

`docs/DECISIONS.md` and `docs/REVIEW-CHECKLIST.md` below are the default paths; a project can move them
(`decisions_path`, `review_checklist_path` in the config). `blueprint.py status --json` reports the ones in
use as `decisions` and `review_checklist`.

## User Input

```text
$ARGUMENTS
```

## Steps

`check` below is the project's own gate command, the one plan.md's Technical Context gives from blueprint
§13.4 (for example `npm run check` or `python3 scripts/check.py`). It is not a `blueprint.py` subcommand.

0. **Scope.** Read the active feature from `.specify/feature.json` (`feature_directory`). If that folder
   has no `.blueprint.json`, the feature was not compiled from the blueprint: this hook does not apply.
   Say nothing, change nothing, and return to `/speckit-implement`. Everything below is for blueprint
   features only.
1. Find the active feature:

   ```bash
   python3 -c "import json;print(json.load(open('.specify/feature.json'))['feature_directory'])"
   ```

2. Read `<feature>/spec.md` in full, once. It is compiled to contain only this epic, so it is the one large
   file worth reading whole.
3. Read `<feature>/plan.md` section "Preconditions and VERIFY-AT-BUILD". Check every precondition (previous
   epics done per `blueprint.py status`, `check` green on a clean tree, required env vars present). Re-check
   each `[VERIFY-AT-BUILD]` item this epic depends on (a search or a sandbox request) and record `✔ date` or
   `✘ date + what changed` at the top of `<feature>/review.md` under a `## VERIFY-AT-BUILD` heading
   (create the file with `Status: IN PROGRESS` as its first line if it does not exist).
   If a precondition fails or an item is `✘`, stop and report; the user decides.
4. Hold these rules for the whole implementation:
   - Tests for a story come from its ACs and **Tests** block and fail before the code exists.
   - Run `check` after each task; keep it green; never weaken the gate.
   - Mark each task `[X]` in `tasks.md` as soon as it is done and green, one task at a time, before
     starting the next. Never tick tasks in bulk at the end: the ticks are the resume point if the
     session stops, and `blueprint.py status` reads progress from them.
   - User-facing text only from `CP-` IDs in spec.md; no improvised strings.
   - A decision the spec does not cover → `DR-nn` in `docs/DECISIONS.md` (with its index row) in the same
     commit. An AC that is wrong or impossible → stop and use `/speckit-blueprint-amend`; never implement
     something different silently.
   - Read source files over 200 lines by range (`grep -n` first). Do not re-read files you have not changed.
     For anything outside the feature folder use `blueprint.py section <n>` or `blueprint.py find <ID>`,
     not the whole blueprint.
   - The project's own rules still hold: where the constitution's own principles, `AGENTS.md` or
     `CLAUDE.md` are stricter (task format, which repository a task runs in, approvals), follow them.
   - Blueprint lines that mention `PROGRESS.md` map to this flow: story and AC evidence go to the ticked
     tasks in `tasks.md` and to `review.md`.
5. If the session is already long (another epic was built in it, or you are past a few hundred thousand
   tokens of context), say so and recommend finishing the current story, then continuing in a fresh session
   with "continue"; `/speckit-implement` resumes from the first unchecked task.
6. Return to `/speckit-implement`.
