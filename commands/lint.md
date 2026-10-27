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

1. Run (it lints the configured blueprint, then checks that every ID each epic uses has a definition
   compile can find):

   ```bash
   python3 .specify/extensions/blueprint/scripts/blueprint.py lint
   ```

   To lint another file directly: `python3 .specify/extensions/blueprint/scripts/lint_blueprint.py <file>`.

2. Fix every **error** in the blueprint, then lint again until there are none. Errors are structural
   defects that compile or a build session would trip over (missing ACs, an `[UNKNOWN → OQ-nn]` with no
   OQ row, an undefined persona, a stack row without evidence).
3. For each **warning**, either fix it or state in one line why it stays.
4. An unresolved ID in the reference part is a blueprint defect too. The output's `how_to_define` says
   which shapes compile recognises; define the ID in its home section, or fix the reference. Repeat until
   the command exits 0.
5. Report: errors fixed, warnings fixed or justified, and the final PASS line.
