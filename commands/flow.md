---
description: "Use when the user shares a new product or feature idea to turn into a blueprint and epics, or, in a project with docs/BLUEPRINT.md, for 'continue', 'next step', 'build the next epic', 'where are we' or a change to a blueprint epic's scope, acceptance criteria or copy. Reads the project state and runs the right blueprint or spec-kit step. In a project with this extension, prefer it over the idea-to-blueprint skill. Not for features that were not compiled from the blueprint: those follow the project's own workflow."
---

# Blueprint flow

You are the conductor of the blueprint-driven part of a project. The user talks in plain language; you
decide which step runs next. You never skip a step, and you never edit compiled spec files by hand.

The project's own rules come first. Before acting, check `.specify/memory/constitution.md` (its principles
outside the `speckit-blueprint:rules` block) and the project's agent instructions (`CLAUDE.md` and whatever
it imports, `AGENTS.md`, where present). Where they set a stricter or
different rule (every change is recorded as a task first, tasks name their repository, extra approvals),
follow them; this skill fills in only what they leave open. Features whose folder has no `.blueprint.json`
are not this skill's business.

`docs/DECISIONS.md` and `docs/REVIEW-CHECKLIST.md` below are the default paths; a project can move them
(`decisions_path`, `review_checklist_path` in the config). `blueprint.py status --json` reports the ones in
use as `decisions` and `review_checklist`.

## User Input

```text
$ARGUMENTS
```

Consider the user input (and the conversation) before deciding.

## 1. Read the state (cheap, deterministic)

```bash
python3 .specify/extensions/blueprint/scripts/blueprint.py status --json
```

The JSON has `state`, `constitution`, `active_feature`, one row per epic (`state`: not-compiled, compiled,
stale, tasked, in-progress, implemented, done) and `next` (`command`, `epic`, `why`, `new_session`,
optional `activate`). Do not read `docs/BLUEPRINT.md` to work this out.

`check` means the project's gate command (blueprint §13.4, repeated in each plan.md), not a
`blueprint.py` subcommand.

## 2. Classify the request

| The user… | Do |
|---|---|
| shares a new idea and there is no blueprint (`state: no-blueprint`) | run `/speckit-blueprint-discover` with the idea (it picks brownfield mode by itself when the repository already has a product) |
| shares a new idea or big new scope and a blueprint exists | run `/speckit-blueprint-discover` in incremental mode (it adds epics to the existing blueprint) |
| wants to change behaviour, an AC, copy, data, scope of a planned epic, or reports that the spec is wrong | run `/speckit-blueprint-amend` with their words |
| says continue / next / go / build, or asks what is next | follow `next` from the status (section 3) |
| asks where things stand | print the status as a short table (epic, state, tasks) and the next step; stop |
| asks for a small fix to already-built code that does not change any AC | record nothing in the blueprint; handle it the way the project's rules say (if they require a task or spec for every change, create it first). Only when they say nothing: do it directly and run `check` |
| works on a feature without `.blueprint.json`, or on the project's normal work | leave it to the project's own Spec Kit workflow; do not redirect it to the blueprint |

When unsure whether a request changes the product, treat it as an amendment and ask.

## 3. Run the next step

- `speckit-blueprint-bootstrap` → run it.
- `speckit-blueprint-compile` (with `epic`) → run `/speckit-blueprint-compile <epic>`, then continue with
  `/speckit-tasks` and `/speckit-analyze` in the same session (they are cheap).
  If this runs as the `before_specify` hook and the user's request is not a blueprint epic, return at once
  and let `/speckit-specify` continue.
- `speckit-tasks` → run `/speckit-tasks`, then `/speckit-analyze`. If analyze finds a defect in spec.md,
  plan.md or the data model, that is an amendment; if it finds a defect only in tasks.md, fix tasks.md.
- `speckit-implement` → if `next.activate` is set, first write it to `.specify/feature.json` as
  `{"feature_directory": "<value>"}`. Then run `/speckit-implement`.
- `speckit-blueprint-review` → run it.
- `speckit-blueprint-discover` with `state: all-done` → tell the user every epic is done and ask whether to
  start incremental discovery.

**Keep going.** After a step finishes, re-read the status and run the next step yourself, without asking,
until you reach one of these stops:

- a gate from section 4;
- `next.new_session` is true and this session already did work (bootstrap, a compile+tasks pass, an
  implementation, a review). That is the boundary between planning an epic and building it, and between
  epics. Stop and tell the user, in their language: "Open a fresh session in this project and say:
  continue." Implementation starts with a clean context;
- a step reported a problem it could not fix (a precondition failed, an unresolved ID, red `check`).

So "continue" on a fresh project runs bootstrap → compile E00 → tasks → analyze and stops before
implement; "continue" in the next session implements and reviews E00 and stops.

## 4. Gates you never pass for the user

- Approval of the decision brief in discover.
- Amendments that change user-visible behaviour, money, data retention or security.
- `git commit` and `git push`: follow the user's and the repository's rules; never commit or push unasked.

## 5. When you stop

Run `status --brief` and tell the user in a few lines what was done, anything they must check or decide,
and what comes next.
