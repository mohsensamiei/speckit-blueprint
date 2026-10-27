---
description: "Compile one blueprint epic into a spec-kit feature folder and make it active"
---

# Compile an epic

Turns one `## Epic nn` of the blueprint into a spec-kit feature folder. A script resolves every ID the
epic uses (personas, flows, screens, copy lines, entities, endpoints, integrations, edge cases, decisions,
drivers, risks, open questions, sources) to its definition, so the build session reads only what this
epic needs and never searches the blueprint.

## User Input

```text
$ARGUMENTS
```

The input names the epic (`E03`, `3`, `Epic 03`). If it is empty, take `next.epic` from
`python3 .specify/extensions/blueprint/scripts/blueprint.py status --json`.

## Steps

1. Run:

   ```bash
   python3 .specify/extensions/blueprint/scripts/blueprint.py compile E03
   ```

   Output: `specs/NNN-e03-<slug>/` with `spec.md`, `plan.md`, `research.md`, `quickstart.md`, and when
   the epic touches them `data-model.md` and `contracts/`; a `.blueprint.json` trace; and
   `.specify/feature.json` pointing at the folder, so spec-kit commands treat it as the active feature.

2. If the script refuses because the folder already has completed tasks, do not add `--force` on your own.
   Tell the user that the epic is partly built and that a product change belongs in
   `/speckit-blueprint-amend`, which decides how to handle built work.

3. If `unresolved_ids` is not empty, the blueprint references something it never defines. Stop and fix the
   blueprint (or ask the user when the right definition is not obvious), lint, and compile again. Do not
   build on an unresolved ID.

4. Do not edit the compiled files. They are regenerated on every compile, and a Claude Code hook blocks
   hand edits.

5. If the project uses spec-kit's git extension and the user wants a branch per epic, create it now
   (`/speckit-git-feature` or `git switch -c <folder name>`), following the user's git rules.

6. Report: folder, files with sizes, total size versus the blueprint size, and the next step —
   `/speckit-tasks`, then `/speckit-analyze`.
