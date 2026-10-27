---
description: "Show blueprint progress per epic and the next step"
scripts:
  py: scripts/blueprint.py hook session-start
---

# Blueprint status

Also wired as the Claude Code `SessionStart` event, so every new session starts knowing where the
project stands without reading any document.

## User Input

```text
$ARGUMENTS
```

## Steps

1. Run:

   ```bash
   python3 .specify/extensions/blueprint/scripts/blueprint.py status --json
   ```

2. Show the user a compact table: epic, title, state, tasks done/total, review. Mark epics whose
   blueprint text changed since compile (`changed_since_compile`).
3. End with the `next` step and its reason, in the user's language. Do not run it unless asked.
