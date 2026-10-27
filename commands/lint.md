---
description: "Lint the blueprint for the structural guarantees compile and build sessions rely on"
---

# Lint the blueprint

## User Input

```text
$ARGUMENTS
```

If the input names a file, lint that file; otherwise lint the configured blueprint (`docs/BLUEPRINT.md`
unless `blueprint_path` in `.specify/extensions/blueprint/blueprint-config.yml` says otherwise).

## Steps

1. Run:

   ```bash
   python3 .specify/extensions/blueprint/scripts/lint_blueprint.py docs/BLUEPRINT.md
   ```

2. Fix every **error** in the blueprint, then lint again until there are none. Errors are structural
   defects that compile or a build session would trip over (missing ACs, an `[UNKNOWN → OQ-nn]` with no
   OQ row, an undefined persona, a stack row without evidence).
3. For each **warning**, either fix it or state in one line why it stays.
4. Lint does not check that compile can find a definition for every ID an epic uses. Check that too:

   ```bash
   python3 .specify/extensions/blueprint/scripts/blueprint.py refs
   ```

   An unresolved ID is a blueprint defect: define it where its kind lives (a copy row in §11, an entity
   in §12.4, an edge case in §15, …), or fix the reference. Repeat until `refs` exits 0.
5. Report: errors fixed, warnings fixed or justified, and the final PASS line.
