---
description: "Self-review an implemented epic against its ACs and the review checklist, then write the handoff"
---

# Review and hand off (after_implement hook)

The human reviewer sees a large diff produced quickly; their attention is the scarcest resource in the
process. Everything you can catch here is worth far more than it costs. Review the diff as if someone else
wrote it.

## User Input

```text
$ARGUMENTS
```

## Steps

0. **Scope.** Read the active feature from `.specify/feature.json` (`feature_directory`). If that folder
   has no `.blueprint.json`, the feature was not compiled from the blueprint: this hook does not apply.
   Say nothing, change nothing, and return to the caller. Everything below is for blueprint
   features only.
1. Active feature: `feature_directory` in `.specify/feature.json`. Epic ID: `epic` in
   `<feature>/.blueprint.json`. Base of the epic's diff: the commit before its first task (ask git:
   `git log --oneline -- <feature>/tasks.md` and the epic branch, if one exists).

2. **Gate.** Run the full `check` and the epic-level tests from `<feature>/quickstart.md`. Run the whole
   regression suite. If the project spans several repositories, run the gate of every repository the
   epic's tasks touched, as the project's rules define it. Red → fix, do not continue with red.

3. **Coverage of the spec.** For every story in `<feature>/spec.md`, for every `AC-n`: name the passing
   test that proves it, or the manual check (with date and observation). An AC with neither is not done.
   Check the story's **Edge cases** the same way.

4. **Checklist.** Walk `docs/REVIEW-CHECKLIST.md` (the project's own, if it has one) over the diff, story by story, and answer every item.
   Fix what fails instead of noting it. Pay particular attention to the agent-code failure profile:
   invented APIs (every external symbol must trace to a pinned dependency), duplicated helpers the codebase
   already had, authorization and input-handling defects behind clean code, and tests that assert too
   little.

5. **Diff size.** If any story's diff exceeds the limit the checklist sets, say so: the story was
   mis-sized, and that is worth an amendment for later epics.

6. **Definition of Done.** Walk the epic's Definition of Done in spec.md ("Success Criteria") line by line;
   each line gets ✔ with evidence or the epic stays IN PROGRESS. Lines that mention `PROGRESS.md` are
   satisfied by `tasks.md` plus this review file.

7. **Decisions and amendments.** Every decision taken that the spec did not cover has a `DR-nn` in
   `docs/DECISIONS.md` with its index row. Every AC that changed went through `/speckit-blueprint-amend`.

8. **Write `<feature>/review.md`** (keep a `## VERIFY-AT-BUILD` section if the context hook created one):

   ```
   Status: DONE | IN PROGRESS
   # Handoff — E03 <Title> — <date>
   Stories: E03-S01 DONE · E03-S02 DONE · …
   check: green (commit abc123) · CI: green|not run · staging: deployed|n/a, smoke n/n
   AC evidence: E03-S01 AC-1 test/…::name · AC-2 … (one line per story)
   Self-review: <n> items failed and fixed (list), <n> accepted with reason (list)
   Diff size: within limit | E03-S02 620 lines, over the 400 limit
   Deviations / amendments: none | A-nn, DR-nn
   Accepted risks: none | …
   Decisions added: DR-nn …
   Next epic preconditions: …
   Manual checks for you: …
   ```

   `Status: DONE` only when steps 2–7 all pass. Otherwise `IN PROGRESS` with the exact remaining items.

9. Tell the user, in their language: the status, what they must check by hand, and that the next epic
   starts in a fresh session with "continue". Do not commit or push unless the user asks; follow their git
   rules.
