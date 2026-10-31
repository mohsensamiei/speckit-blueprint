#!/usr/bin/env python3
"""Lint a blueprint with the idea-to-blueprint linter, unmodified, minus the findings this flow retires.

Usage:
    python3 lint_blueprint.py path/to/blueprint.md [--strict]

The linter itself is upstream/idea-to-blueprint/scripts/lint_blueprint.py (see its docstring for what it
checks and the exit codes). This wrapper loads it and drops the warnings listed in DROPPED, which the
spec-kit build flow makes obsolete (references/speckit-flow.md). Keeping the change here, not in the
upstream file, is what lets tools/sync_upstream.py replace that file on every upstream release.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

UPSTREAM = Path(__file__).resolve().parent.parent / "upstream" / "idea-to-blueprint" / "scripts" / "lint_blueprint.py"

# Warning prefixes dropped, each with the reason.
DROPPED = (
    # Build sessions start from /speckit-blueprint-compile; a per-epic prompt appendix is not needed.
    "No appendix with 'Session Prompts'",
)


def load():
    sys.dont_write_bytecode = True  # keep upstream/ byte-for-byte as shipped (no __pycache__ in it)
    spec = importlib.util.spec_from_file_location("idea_to_blueprint_lint", UPSTREAM)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # dataclasses resolve annotations through sys.modules
    spec.loader.exec_module(mod)
    warn = mod.Findings.warn

    def filtered(self, line, msg):
        if not msg.startswith(DROPPED):
            warn(self, line, msg)

    mod.Findings.warn = filtered
    return mod


if __name__ == "__main__":
    sys.exit(load().main(sys.argv))
