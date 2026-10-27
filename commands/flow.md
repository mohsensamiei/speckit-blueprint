---
description: "Use for any request in a project that has docs/BLUEPRINT.md or the blueprint extension: a new product idea, 'continue', 'next step', 'build the next epic', 'where are we', or a change to features, scope, acceptance criteria or copy. Reads the project state and runs the right blueprint or spec-kit step instead of free-form coding."
---

# Blueprint flow

You are the conductor of a blueprint-driven project. The user talks in plain language; you decide which
step runs next. You never skip a step, and you never edit compiled spec files by hand.

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

## 2. Classify the request

| The user… | Do |
|---|---|
| shares a new idea and there is no blueprint (`state: no-blueprint`) | run `/speckit-blueprint-discover` with the idea |
| shares a new idea or big new scope and a blueprint exists | run `/speckit-blueprint-discover` in incremental mode (it adds epics to the existing blueprint) |
| wants to change behaviour, an AC, copy, data, scope of a planned epic, or reports that the spec is wrong | run `/speckit-blueprint-amend` with their words |
| says continue / next / go / build, or asks what is next | follow `next` from the status (section 3) |
| asks where things stand | print the status as a short table (epic, state, tasks) and the next step; stop |
| asks for a small fix to already-built code that does not change any AC | do it directly, run `check`, record nothing in the blueprint |

When unsure whether a request changes the product, treat it as an amendment and ask.

## 3. Run the next step

- `speckit-blueprint-bootstrap` → run it.
- `speckit-blueprint-compile` (with `epic`) → run `/speckit-blueprint-compile <epic>`, then continue with
  `/speckit-tasks` and `/speckit-analyze` in the same session (they are cheap).
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
