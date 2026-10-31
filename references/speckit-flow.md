# Writing a blueprint for the spec-kit build flow

The other references (`upstream/idea-to-blueprint/references/`) come from the idea-to-blueprint skill
unmodified, and there build sessions read the blueprint directly. In this extension they do not: `/speckit-blueprint-compile` extracts each epic and the
definitions it references into a spec-kit feature folder. Where this file and `blueprint-template.md`
disagree, this file wins.

## 1. Definitions compile can find

Compile resolves an ID by its definition, found outside section 17 (Epics) and outside the appendices, in
one of three shapes:

1. **A heading that starts with the ID** (after an optional section number):
   `### P1 — Maya, solo freelancer`, `### F-03 — See who owes me`, `#### DR-07 — Postgres over SQLite`,
   `### 11.4 SCR-04 Time zone` (this is how a screen's whole copy table is attached to `SCR-04`).
   The definition runs to the next heading of the same or higher level.
2. **A paragraph that starts with the bold ID**: `**ENT-Order** (`order`, owner `billing`)` followed by
   its field table, or `**INT-sms — Kavenegar**` followed by its card. It runs to the next bold-ID line or
   heading.
3. **A table row whose first cell is the ID**: copy lines (`| CP-SCR04-2 | …`), screens, endpoints
   (`| API-12 | …`), edge cases (`| EC-PAY-04 | …`, a trailing note like `(new)` is fine), drivers,
   fitness functions, risks, open questions, sources, metrics.

Consequences for writing:

- Define every ID in its home section; mention it anywhere else. An entity whose fields appear only inside
  a story is invisible to compile.
- Ranges are understood: `SCR-01 to SCR-06`, `CP-SCR20-1 to CP-SCR20-12`, `EC-BOT-01 to 04`,
  `CP-SCR03-1…7`, and wildcards `EC-BOT-*` / `CP-SCR03-*`.
- Flows, screens and edge cases pull in the copy lines and edge cases they name (second level), so a flow
  step that says "shows CP-SCR07-3" brings that line into the epic even if the story does not name it.
- `blueprint.py lint` runs the linter and then lists, per epic, the IDs with no definition. Phase 4
  requires it to exit 0.

## 2. Epic and story structure (unchanged, now load-bearing)

Compile relies on the template's conventions exactly:

- `## Epic 03 — <Title>`; header fields (Goal, Personas served, Depends on, Preconditions for the session,
  Scope, Flows and screens implemented, Data and API touched, Risks) before the first story.
- `### E03-S02 — <Title>`; inside, the bold labels in order: Story, Context, Scope, Acceptance Criteria,
  Edge cases, Tests, Tasks, Story DoD.
- After the last story: `**Epic-level tests**`, `**Definition of Done**`, `**Session handoff checklist**`.

How they map: each story becomes a spec-kit user story (priority = blueprint order); its Tasks become the
"Blueprint Task Seeds" in plan.md, which `/speckit-tasks` keeps by ID; Epic-level tests and DoD become the
spec's Success Criteria and the quickstart; `- Manual:` lines in Tests become quickstart manual checks;
`[VERIFY-AT-BUILD]` lines in the epic are listed in plan.md for re-checking.

## 3. Section 18 — Build workflow (replaces the session protocol)

Title it `## 18. Session protocol (Session Protocol)` so the linter finds it, and describe this flow
instead of the per-session runbook:

- **Per epic:** `/speckit-blueprint-compile Enn` → `/speckit-tasks` → `/speckit-analyze` →
  `/speckit-implement` (hook loads spec.md, re-checks preconditions and `[VERIFY-AT-BUILD]` items) →
  `/speckit-blueprint-review` (hook: gate, AC evidence, review checklist, Definition of Done, handoff in
  `review.md`). A fresh session per epic implementation; `/speckit-implement` resumes from the first
  unchecked task after a crash or a deliberate session break.
- **State lives in files:** `tasks.md` checkboxes (progress), `review.md` (evidence and handoff),
  `docs/DECISIONS.md` (decisions, with an index), the blueprint's Amendments log (changes to the plan).
  There is no PROGRESS.md; `blueprint.py status` derives progress from the feature folders.
- **Gates** (an epic is done only when all are true): every AC has evidence, `check` and CI green, epic-level and regression tests green, review checklist
  applied with results, no gate weakened without a DR, no unexplained TODO or skipped test, no new flaky
  test, decisions and amendments recorded.
- **Amendments log** (keep it here; the linter looks for it):
  `| A-nn | Date | Epic/story | What changed | Why | Approved by |`. Changes go through
  `/speckit-blueprint-amend`: edit in place, mark `(amended A-nn)`, recompile affected epics.
- **`[VERIFY-AT-BUILD]` re-check list**: every such item with the epic that first depends on it.

## 4. Appendices

- **Appendix A (session prompts) is not needed.** The user says "continue" in a fresh session; the
  `speckit-blueprint-flow` skill and the session-start hook know the next step.
- **Appendix B** keeps only what the product needs and bootstrap does not generate: `.env.example` and the
  `check` script (or its configuration). Bootstrap generates `.specify/memory/constitution.md`,
  `docs/REVIEW-CHECKLIST.md` (from §14.4), `docs/DECISIONS.md` and the `CLAUDE.md` block.

## 5. Epic 00 — Foundation

Keep every item of `stories-ac-tests.md` §6 except item 5, which becomes: `docs/BLUEPRINT.md`,
`docs/DECISIONS.md`, `docs/REVIEW-CHECKLIST.md`, the constitution and the `CLAUDE.md` block already exist
(bootstrap); E00 verifies them, adds `AGENTS.md` only if another agent will work on the repo, and adds
`.env.example` from Appendix B. Do not write stories or DoD lines that create or update PROGRESS.md; evidence
goes to `tasks.md` and `review.md`.

## 6. Section numbers compile and bootstrap read

Keep the template's numbering, because the extension config refers to it:

- Constitution (default): §12.10 fitness functions, §13.2 forbidden choices, §13.5 strictness,
  §13.6 testing conventions, §13.7 git conventions, §13.9 error handling and logging, §13.10 dependency
  policy, §14.2 the gate, §14.3 test strategy, §14.8 definitions of green and done.
- Every epic's plan.md (default): §12.2 module map, §13.1 stack table, §13.3 repository layout, §13.4 `check`.
- data-model.md uses the opening conventions paragraph of §12.4; contracts/api.md the opening of §12.5.
- `docs/REVIEW-CHECKLIST.md` is §14.4 verbatim.

These sections are read in every epic, so keep them tight: rules and numbers, not narrative.
