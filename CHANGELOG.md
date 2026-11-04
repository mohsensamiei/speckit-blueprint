# Changelog

## 0.4.0 — 2026-11-04

Several blueprints in one project (one per product), without one touching another's files.

- `blueprints:` in the config maps each id to its `path`, `decisions`, `checklist`, `prefix`, `sources`,
  `number_base` and, optionally, its own `constitution_sections` / `plan_sections`; `default_blueprint`
  picks the default. A config without it has one implicit blueprint and works as before. Two blueprints
  sharing a file, or path keys at the top level next to `blueprints:`, are config errors.
- `.blueprint.json` records `blueprint_id`. Compile, status, stale, accept and the session-start hook find
  an epic's folder by blueprint and epic together. Before, `compile E01` for a second blueprint reached the
  first one's `E01` folder and could overwrite its compiled files. Folders compiled before ids belong to
  the default blueprint.
- New folders are `NNN-<id>-eNN-<slug>` when the config uses ids; `number_base` gives each blueprint its own
  range of feature numbers.
- Commands take `--blueprint <id>` or qualified arguments (`desk:E01`, `DESK:DR-03`, `one:13.4`) and default
  to the active feature's blueprint (`SPECKIT_BLUEPRINT` also works). `status` lists every blueprint under
  `blueprints`; the brief names them all.
- Bootstrap keeps one constitution block and one CLAUDE.md block per blueprint, with the id in the markers;
  an unmarked block is the default blueprint's and gets its id on its next bootstrap. A constitution
  compiled whole from one blueprint keeps the other blueprints' blocks, and `constitution_mode: own` refuses
  to replace another blueprint's constitution. Scope sentences name the blueprint id, not just the
  presence of `.blueprint.json`.
- Each blueprint has its own decisions log and checklist (default: next to its file); with a prefix, DR
  index rows and task seeds carry it (`DESK:DR-01`, `DESK:E01-S02-T3`).
- `blueprint.py rules` prints the rules for the active feature's blueprint; the context hook uses it. The
  guard protects every block and names the right blueprint.
- No command, prompt or guard message names `docs/BLUEPRINT.md` any more; it is only the default path.
- Discover settles the target blueprint first (adding a config entry for a new product), decides its mode
  for that blueprint alone, and in brownfield mode reads the blueprint's `sources` outside the repository.
- The config parser reads nested maps.

## 0.3.2 — 2026-10-31

- Bootstrap no longer creates a Sync Impact Report comment in a project-owned constitution. Spec Kit
  treats that comment as scratch for reviewing one amendment and removes it before the commit, so a new
  one after every bootstrap was clutter to clean up. The version bump and Last Amended stay; the
  amendment is reported in bootstrap's output (`constitution.amendment`), and a line is added only to a
  report that is already open.

## 0.3.1 — 2026-10-31

- The CLAUDE.md block no longer names `AGENTS.md`; it defers to the rest of CLAUDE.md and what it imports.
- The flow and context commands name the project's agent instructions generically (`CLAUDE.md` and what it
  imports, `AGENTS.md` where present).

## 0.3.0 — 2026-10-31

Safe to add to an existing Spec Kit project, and easy to keep in step with idea-to-blueprint.

- Bootstrap keeps a constitution the project wrote and maintains one managed `speckit-blueprint:rules`
  block in it, scoped to blueprint features and yielding to the project's principles; the project's
  `constitution_mode: auto|own|append` in the config. A constitution that is
  missing or still the `specify init` template is compiled whole, as before.
- The guard protects only that block in a project-owned constitution; the rest stays editable.
- An existing `docs/REVIEW-CHECKLIST.md` is no longer overwritten.
- The `context` and `review` hooks do nothing for features without `.blueprint.json`.
- The flow skill follows the project's constitution, `AGENTS.md` and `CLAUDE.md` first; small fixes are
  recorded the way the project requires instead of skipped.
- Discover has a brownfield mode for an existing product: repository first, nothing existing re-decided
  or invented, Epic 00 as a short baseline.
- The session-start hook stays silent in an existing project without a blueprint.
- idea-to-blueprint is vendored unmodified under `upstream/idea-to-blueprint/` (pinned in
  `upstream/UPSTREAM.json`, still commit `38cbec9`). `discover.md` runs its `SKILL.md` with listed
  overrides, and the linter change became a wrapper. `tools/sync_upstream.py` updates the copy and
  reports the anchors the extension relies on; tests and a weekly workflow catch drift.
- `blueprint.py accept Enn --note "…"` records that a built epic stays as built after a blueprint change
  (for example, covered by a later epic), so status stops reporting it; `amend` uses it after the user
  decides.
- The commands say that `check` is the project's gate command from plan.md, not a `blueprint.py`
  subcommand.
- The lint wrapper no longer writes `__pycache__` into `upstream/`.
- In append mode, adding or changing the managed block bumps the project's constitution version
  (`constitution_version_bump: minor|patch|none`), sets Last Amended and adds a Sync Impact Report line;
  the user no longer has to do it by hand.
- Multi-repository projects: optional epic header fields `**Target repositories**` and `**Repositories**`
  compile into spec.md's "Target Repositories" and plan.md's "Repositories" sections (order, branches,
  contracts per repository); brownfield discover writes them when the constitution asks for them.
- `decisions_path`, `review_checklist_path` and `claude_md: false` in the config, for projects that keep
  `docs/` for other material or whose CLAUDE.md only imports other files; `blueprint_path` can already
  point under `specs/`.
- The discover and flow skills say to use them instead of the idea-to-blueprint skill inside a Spec Kit
  project with this extension; the two can stay installed side by side.
- Brownfield discover checks each decision and AC against the project's principles, so an AC that keeps
  existing tests unchanged cannot sit next to a decision that changes what they observe.

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
