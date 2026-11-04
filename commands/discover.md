---
description: "Turn an idea into an evidence-backed build blueprint (intake, research, decisions, epics) in a Spec Kit project. Inside a project that has this extension (.specify/extensions/blueprint), use this instead of the idea-to-blueprint skill: it runs the same method and hands the epics to Spec Kit."
---

# Idea → Build Blueprint

Turn a raw idea (even 2–3 lines) into a single markdown document complete enough to build the product epic
by epic without guessing. Build sessions never read the whole blueprint; `/speckit-blueprint-compile`
hands each epic exactly the parts it needs. So be complete here, not brief.

Run on the strongest model at the highest effort the harness offers. If you cannot tell whether that is the
case, say so once at the start and continue.

## User Input

```text
$ARGUMENTS
```

## The method comes from idea-to-blueprint

The method is the idea-to-blueprint skill, shipped unmodified with this extension. Read its instructions
first and follow them, phase by phase:

```
.specify/extensions/blueprint/upstream/idea-to-blueprint/SKILL.md
```

Paths it mentions (`references/…`, `scripts/…`, `assets/…`) are relative to that folder
(`.specify/extensions/blueprint/upstream/idea-to-blueprint/`). Read each reference when its phase starts,
not all up front.

This command changes the skill only where the spec-kit build flow differs. Where this file and the skill
disagree, this file wins; where `.specify/extensions/blueprint/references/speckit-flow.md` and the
skill's `references/blueprint-template.md` disagree, `speckit-flow.md` wins.

## Which blueprint

A project can hold several blueprints, one per product, listed under `blueprints:` in
`.specify/extensions/blueprint/blueprint-config.yml` (id → `path`, and optionally `decisions`,
`checklist`, `prefix`, `sources`, `number_base`, section lists). Settle the target before anything else:

1. Run `python3 .specify/extensions/blueprint/scripts/blueprint.py status --json`. `blueprints` lists every
   configured blueprint with its `blueprint` path, `state` (`no-blueprint` when its file does not exist
   yet) and `sources`.
2. The target is the blueprint the input names (`--blueprint <id>`, or a product name matching one), else
   the one the idea extends. If the idea is a different product from every configured blueprint, it is a
   **new blueprint**: ask the user for its id (lowercase, e.g. `desk`), its path (its own folder, e.g.
   `docs/desk/BLUEPRINT.md`, so no file collides with another blueprint's on merge) and the repositories
   or folders that hold the existing product, if any. Then add the entry to the config. If the config has
   no `blueprints:` map yet, move the current top-level `blueprint_path`, `decisions_path` and
   `review_checklist_path` into an entry for the existing blueprint first (its `path`, `decisions`,
   `checklist`; listed first, or named by `default_blueprint`, so its existing feature folders stay its own).
3. Pass `--blueprint <id>` to every `blueprint.py` command below. Write only that blueprint's files: its
   `path`, and through bootstrap its decisions log, checklist and its own managed blocks.

Never add one product's epics to another product's blueprint.

## Modes

The mode is decided for the target blueprint alone; other blueprints in the project do not change it.

- **New product** — the target's file does not exist and no existing product backs it: run phases 0–4.
- **Incremental** — the target's blueprint exists and the input adds scope (a new capability, a new persona, a new
  integration): run phases 0–4 scoped to the addition. Read only the sections you must stay consistent
  with (`blueprint.py section <n>`, `blueprint.py find <ID>`), continue every ID series from its highest
  existing number, add new epics after the last one, add rows to the Amendments log, and do not rewrite
  decided sections unless the addition forces it (then that is an amendment: `/speckit-blueprint-amend`).
- **Existing product (brownfield)** — the target's file does not exist yet, but the product does: in
  this repository (code, feature folders under `specs/`, a constitution of its own, product docs) or in
  the target's `sources` (other repositories or folders, such as the product's code repository or a
  prototype with its own blueprint and decisions). The blueprint covers only the new idea, turned into
  epics that fit what exists. Differences from new-product mode:
  - The product is the first source. Read this repository's constitution, `AGENTS.md`/`CLAUDE.md`, README,
    product docs and existing specs, and every path in `sources` (its README, docs, decisions, code
    layout, gate), before intake; cite them as `[VERIFIED — repo:<path>]` or
    `[VERIFIED — repo:<source>/<path>]`. Documents in another language are sources too; the skill's
    language convention still decides the blueprint's language. Ask only what they do not answer. If the product lives
    elsewhere and `sources` is empty, ask where before calling it a new product.
  - The planning repository is not the product. Its other blueprints and their features belong to other
    products; do not describe them as this product's.
  - Do not re-decide what exists. Stack, architecture, gate, conventions and module map are summarised
    from the repository with paths, not researched afresh; research covers only what the idea adds (a
    new integration, a competitor benchmark for the new capability, a library it needs).
  - Never invent the existing product. A section the repository does not document is
    `[UNKNOWN → OQ-nn]`, not a plausible description.
  - Epic 00 is a short **Baseline** epic, not a scaffold: the existing gate is green, bootstrap's
    outputs are in place, nothing else.
  - The project's rules shape the epics: if the constitution says tasks carry a repository prefix, or
    contracts change on the provider side first, stories and task seeds follow it.
  - If the constitution asks each spec or plan for sections of its own across repositories (for example
    a "Target Repositories" table, or per repository the base branch, working branch, contracts and
    order), give every epic two header fields: `**Target repositories**` (a table: repository, role in
    this epic) and `**Repositories**` (order, then per repository: base branch, working branch,
    contracts provided or consumed). Compile turns them into spec.md's "Target Repositories" and
    plan.md's "Repositories" sections.
  - Check every decision and AC against the project's principles before writing them (backward
    compatibility, data rules, gates). In particular, an AC that existing tests or callers must keep
    passing unchanged cannot sit next to a decision that changes what they observe.
  - Compile continues the numbering of the existing feature folders; bootstrap keeps the project's
    constitution and adds a managed block to it.

## Changes to the skill's phases

- **Phases 0–2** (intake, research, decision brief): as the skill says, with the mode rules above. Do not
  skip phases 0 and 2, and wait for the user's go on the brief unless they pre-authorised it.
- **Phase 3** (write): as the skill says, plus:
  - Before writing, read `.specify/extensions/blueprint/references/speckit-flow.md` as well as the
    template. It replaces the session protocol (section 18), the appendices and Epic 00, and sets the
    definition shapes compile relies on: every ID is defined once, in its home section, outside the
    epics.
  - Do not read the skill's `references/session-protocol.md` or use its `assets/`; `speckit-flow.md`
    and bootstrap replace them.
  - Save to the target blueprint's path (`blueprint` in `status --json --blueprint <id>`), written in
    chunks as the skill says.
- **Phase 4** (lint and deliver) is replaced by:
  1. Lint, and check that compile can resolve every ID each epic uses; fix every error and unresolved
     ID (warnings: fix or justify), until it exits 0:

     ```bash
     python3 .specify/extensions/blueprint/scripts/blueprint.py lint --blueprint <id>
     ```

  2. The human pass from the skill: read the Executive summary, one persona, one flow and one epic as a
     stranger, and fix anything you had to infer.
  3. Run `/speckit-blueprint-bootstrap --blueprint <id>` (constitution or its managed block, review
     checklist, decisions log, CLAUDE.md block). Do not create `PROGRESS.md`, `AGENTS.md` or other files from the skill's
     `assets/`. In incremental mode, run bootstrap only if constitution sections changed.
  4. Wrap up in 5–10 lines: point at the Assumptions table and the Open Questions, name the two or three
     things you are least sure about, and say the next step: a fresh session, then "continue" (or
     `/speckit-blueprint-compile <id>:E00` when the project has several blueprints, else `E00`). Do not
     re-summarise the document. Do not commit unless the user asks.
- **Phase 5** (build sessions) is the spec-kit flow: `speckit-blueprint-flow` runs it. The skill's
  session prompts appendix is not written.
- The skill's language convention, market detection, design reference handling and guardrails apply
  unchanged. Ignore its "Test prompts" section.
