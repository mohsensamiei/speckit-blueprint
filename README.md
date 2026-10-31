# speckit-blueprint

A [Spec Kit](https://github.com/github/spec-kit) extension that combines two things that are usually
traded off against each other:

- **Deep product discovery** from [idea-to-blueprint](https://github.com/iniesohidham/idea-to-blueprint):
  intake, web research, competitor benchmarking, ranked architecture drivers, a verified and pinned stack,
  the quality gate, personas, flows, screens, UX copy, edge cases, and epics → stories → Given/When/Then
  acceptance criteria → tests. The result is one evidence-backed `docs/BLUEPRINT.md`.
- **Token-efficient, drift-free implementation** from Spec Kit: each epic is built from a small feature
  folder (`spec.md`, `plan.md`, `tasks.md`, …) instead of a 100-page document.

The bridge is a deterministic compiler. `/speckit-blueprint-compile E03` resolves every ID the epic uses
(personas, flows, screens, copy lines, entities, endpoints, integrations, edge cases, decisions, risks,
open questions, sources) to its definition in the blueprint and writes a spec-kit feature folder with
exactly that. Build sessions never search the blueprint.

Status: **0.3.0, Claude Code only.** Tested against Spec Kit 1.2.4.

## Tested end to end

A one-paragraph idea in Persian (a personal expense tracker in tomans with Jalali-month reports) was taken
from nothing to a finished v1 with this extension and Claude Code (Sonnet), every session started with
"continue" in a fresh session:

| Stage | Outcome |
|---|---|
| Discover | 7 intake questions with defaults, web research with pinned versions, decision brief, a 133 KB blueprint (4 epics, 12 stories) that lints clean with every ID resolvable |
| Bootstrap | Constitution, review checklist, decisions log, CLAUDE.md block |
| 4 epics × (plan session + build session) | 130/130 tasks ticked one by one, every epic reviewed `Status: DONE`, 217 tests green at 97.8% coverage |
| Human gates | One manual terminal check (RTL column alignment) stopped the flow until the user confirmed; no commit or push without approval |

Total model cost of the whole run was about $13 on Sonnet, discovery included.

## Why

In blueprint-driven builds, most of a session's cost is re-reading context: every model call re-reads
everything already loaded. A session that opens a 100-page blueprint and greps it for the sections its epic
needs pays for those sections on every call that follows. On the example blueprint shipped with
idea-to-blueprint (581 KB, 9 epics), compiled feature folders are 63–127 KB each, and the compile itself
costs no model tokens.

## Install

Requires Python 3.9+ and Spec Kit 1.2+.

```bash
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@v1.2.4
specify init my-product --integration claude
cd my-product
specify extension add blueprint --from https://github.com/mohsensamiei/speckit-blueprint/archive/refs/tags/v0.3.0.zip
```

Installing from a URL asks for confirmation once (answer `y`). For development, install from a local
clone with `specify extension add --dev /path/to/speckit-blueprint`.

Installing registers the commands as Claude Code skills (`/speckit-blueprint-…`), two Spec Kit hooks
around `/speckit-implement`, and two Claude Code hooks in `.claude/settings.json` (session-start status and
a guard against hand-editing compiled files).

## Adding it to an existing Spec Kit project

The extension can join a project that already has its own constitution, features and workflow. Its job
there is to turn a new idea into epics; everything that exists stays the project's:

- **Constitution.** Bootstrap does not rewrite a constitution the project wrote. It adds one managed block
  (`speckit-blueprint:rules`, before `## Governance`) that applies only to features compiled from the
  blueprint and yields to the project's principles. The project's version line is not touched; the guard
  protects only that block. Set `constitution_mode` in the config to force `own` or `append`.
- **Existing features.** The `before_implement` and `after_implement` hooks return at once for any feature
  folder without `.blueprint.json`, so features written by hand keep their usual flow. Compiled epics
  continue the project's feature numbering.
- **Project rules.** The flow skill reads the constitution's own principles, `AGENTS.md` and `CLAUDE.md`
  first and follows them where they are stricter (for example, every change recorded as a task first).
- **Existing files.** `docs/REVIEW-CHECKLIST.md` is left alone if the project has its own; `CLAUDE.md`
  only gains a managed block; `docs/DECISIONS.md` is created only if missing.
- **Discovery.** With no blueprint and an existing product, discover runs in brownfield mode: the
  repository is the first source, what exists is summarised rather than re-decided, and the blueprint
  covers only the new idea.
- **Session start.** Without a blueprint, the status hook says nothing in a project that already has
  features or its own constitution.

## How you use it

You mostly talk in plain language; the `speckit-blueprint-flow` skill reads the project state
(`blueprint.py status`) and runs the right step.

```
"I want an app that …"          → /speckit-blueprint-discover   intake → research → decision brief → blueprint
                                  /speckit-blueprint-lint       structure + every epic's IDs resolve
                                  /speckit-blueprint-bootstrap  constitution, review checklist, DECISIONS, CLAUDE.md block
"continue"  (per epic)          → /speckit-blueprint-compile E03
                                  /speckit-tasks → /speckit-analyze
"continue"  (fresh session)     → /speckit-implement
                                     before: /speckit-blueprint-context  loads spec.md, re-checks preconditions
                                     after:  /speckit-blueprint-review   gate, AC evidence, checklist, review.md handoff
"clients should also get SMS"   → /speckit-blueprint-amend       edit blueprint in place (A-nn), recompile affected epics
"where are we?"                 → /speckit-blueprint-status
```

Every new Claude Code session starts with a short status block (current epic, tasks done, next step), so
"continue" is enough. You still approve the decision brief, product-changing amendments, and every commit
and push.

## What compile produces

| File | Content |
|---|---|
| `spec.md` | Epic context; each story as a prioritised user story with its ACs, edge cases and tests verbatim; resolved edge cases; Definition of Done as success criteria; personas, flows, screens with their copy tables, metrics; open questions with defaults |
| `plan.md` | Goal; blueprint §12.2, §13.1, §13.3, §13.4 (configurable); the stories' tasks as "Blueprint Task Seeds" that `/speckit-tasks` keeps by ID; preconditions and `[VERIFY-AT-BUILD]` lines; risks |
| `research.md` | Decision records, architecture drivers, fitness functions and sources the epic references |
| `data-model.md` | §12.4 conventions and the entities the epic touches |
| `contracts/` | API rows (with §12.5 conventions) and integration cards |
| `quickstart.md` | Epic-level tests and manual checks |
| `.blueprint.json` | Trace: blueprint hash, a hash per resolved definition, so `stale` and `status` know when the blueprint changed under a compiled epic |

The constitution (`.specify/memory/constitution.md`) is compiled from §12.10, §13.2, §13.5–13.7,
§13.9–13.10, §14.2, §14.3 and §14.8, plus five fixed principles. `docs/REVIEW-CHECKLIST.md` is §14.4.

## Configuration

`.specify/extensions/blueprint/blueprint-config.yml` (see [config-template.yml](config-template.yml)):
blueprint path, specs folder, which sections go into the constitution and into every plan, second-level
resolution, and the guard switch.

## Helper script

`.specify/extensions/blueprint/scripts/blueprint.py` (standard library only):

```bash
blueprint.py status [--json|--brief]   # state per epic and the next step
blueprint.py compile E03 [--force]     # feature folder for one epic
blueprint.py bootstrap                 # constitution, checklist, decisions log, CLAUDE.md block
blueprint.py section 14.4              # print a section by number
blueprint.py find ENT-Order SCR-04     # print definitions by ID
blueprint.py lint                      # structural linter, then refs
blueprint.py refs                      # unresolved IDs per epic (exit 1 if any)
blueprint.py stale                     # compiled epics whose blueprint text changed
```

## Development

```bash
python3 -m unittest discover -s tests -v
```

The tests run the script against [tests/fixtures/mini-blueprint.md](tests/fixtures/mini-blueprint.md).

## Keeping up with idea-to-blueprint

[upstream/idea-to-blueprint/](upstream/idea-to-blueprint) is an exact copy of the skill (its `SKILL.md`,
`references/`, `scripts/`, `assets/` and `LICENSE`) at the commit pinned in
[upstream/UPSTREAM.json](upstream/UPSTREAM.json). Nothing in it is edited here. This extension's changes
live in its own files, each of which reads the upstream copy and states where it differs:

| File | Changes to upstream |
|---|---|
| [commands/discover.md](commands/discover.md) | Runs upstream `SKILL.md`; adds the incremental and brownfield modes; replaces phase 4 (lint, bootstrap) and phase 5 (spec-kit flow) |
| [references/speckit-flow.md](references/speckit-flow.md) | Overrides `blueprint-template.md` where compile and the spec-kit flow need it |
| [scripts/lint_blueprint.py](scripts/lint_blueprint.py) | Loads the upstream linter and drops the warnings it lists in `DROPPED` |

To update:

```bash
python3 tools/sync_upstream.py            # or a tag/commit: tools/sync_upstream.py <ref>
python3 -m unittest discover -s tests -v
git diff -- upstream/
```

The sync replaces the copy, rewrites the manifest, prints the added, removed and changed files, and lists
any anchor the overlay relies on that upstream removed (`SKILL.md` phase headings, the blueprint section
numbers the constitution and plans read, the linter's finding hook). The tests fail if the copy was
edited by hand or an anchor is gone. A weekly workflow
([.github/workflows/upstream.yml](.github/workflows/upstream.yml)) opens one issue when upstream moves
past the pinned commit.

## Limitations

- Claude Code only for now. Other agents would need the hooks and the flow skill adapted.
- In an existing project, agents other than Claude Code (Codex, Cursor) do not get the blueprint flow;
  they keep the project's own Spec Kit workflow.
- Compile relies on the blueprint conventions in `upstream/idea-to-blueprint/references/blueprint-template.md` and
  `references/speckit-flow.md` (ID schemes, epic and story headings, bold labels). Blueprints written by
  hand in another shape will resolve fewer IDs; `blueprint.py refs` shows which.

## Credits and license

MIT — see [LICENSE](LICENSE). The discovery method, references and linter come from
[idea-to-blueprint](https://github.com/iniesohidham/idea-to-blueprint) (MIT, © 2026 Mahdi); see
[NOTICE](NOTICE).
