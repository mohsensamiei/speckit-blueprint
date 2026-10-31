"""The vendored idea-to-blueprint copy is pristine, and the overlay still fits it.

Run from the repository root:  python3 -m unittest discover -s tests -v
"""

import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import sync_upstream  # noqa: E402


class UpstreamTest(unittest.TestCase):
    def test_copy_matches_manifest(self):
        self.assertEqual(sync_upstream.verify(), [], "edit the overlay, never upstream/; or re-run tools/sync_upstream.py")

    def test_anchors_still_exist(self):
        self.assertEqual(sync_upstream.missing_anchors(sync_upstream.DEST), [])

    def test_no_second_copy_outside_upstream(self):
        for rel in sync_upstream.json.loads(sync_upstream.MANIFEST.read_text())["files"]:
            if rel.startswith("references/"):
                self.assertFalse((REPO / rel).exists(), f"{rel} duplicates the upstream copy")

    def test_lint_wrapper_drops_only_retired_findings(self):
        fixture = str(REPO / "tests" / "fixtures" / "mini-blueprint.md")
        ours = subprocess.run([sys.executable, str(REPO / "scripts" / "lint_blueprint.py"), fixture], capture_output=True, text=True)
        theirs = subprocess.run([sys.executable, str(sync_upstream.DEST / "scripts" / "lint_blueprint.py"), fixture], capture_output=True, text=True)
        self.assertIn("Session Prompts", theirs.stdout)
        self.assertNotIn("Session Prompts", ours.stdout)
        drop = [l for l in theirs.stdout.splitlines() if "Session Prompts" not in l and not l.startswith("WARNINGS")]
        keep = [l for l in ours.stdout.splitlines() if not l.startswith("WARNINGS")]
        self.assertEqual(keep, drop)
        self.assertEqual(ours.returncode, theirs.returncode)

    def test_discover_points_at_upstream_skill(self):
        text = (REPO / "commands" / "discover.md").read_text(encoding="utf-8")
        self.assertIn("upstream/idea-to-blueprint/SKILL.md", text)
        for phase in ("Phase 3", "Phase 4", "Phase 5"):
            self.assertIn(phase, text)


if __name__ == "__main__":
    unittest.main()
