"""Tests for scripts/blueprint.py against tests/fixtures/mini-blueprint.md.

Run from the repository root:  python3 -m unittest discover -s tests -v
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "blueprint.py"
FIXTURE = REPO / "tests" / "fixtures" / "mini-blueprint.md"


class ProjectTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / ".specify" / "memory").mkdir(parents=True)
        (self.tmp / "docs").mkdir()
        shutil.copy(FIXTURE, self.tmp / "docs" / "BLUEPRINT.md")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_cli(self, *args, stdin="", check=True):
        res = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=self.tmp,
            input=stdin,
            capture_output=True,
            text=True,
        )
        if check and res.returncode != 0:
            self.fail(f"{args} exited {res.returncode}: {res.stderr}")
        return res

    def json_cli(self, *args):
        return json.loads(self.run_cli(*args).stdout)

    def feature(self, epic="E01"):
        return self.tmp / "specs" / {"E00": "001-e00-foundation", "E01": "002-e01-record-sales"}[epic]


class CompileTest(ProjectTest):
    def test_compile_resolves_every_reference(self):
        out = self.json_cli("compile", "E01")
        self.assertEqual(out["feature_directory"], "specs/002-e01-record-sales")
        self.assertEqual(out["unresolved_ids"], [])
        f = self.feature()
        spec = (f / "spec.md").read_text(encoding="utf-8")
        # stories become prioritised user stories, tasks move to the plan
        self.assertIn("### User Story 1 - Enter and save a sale (Priority: P1)", spec)
        self.assertIn("### User Story 2 - Undo the last sale (Priority: P2)", spec)
        self.assertNotIn("E01-S01-T1", spec)
        # ranges expand: SCR-01 to SCR-02 brings both copy tables; EC-INPUT-01 to 02 both rows
        self.assertIn("CP-SCR02-1", spec)
        self.assertIn("EC-INPUT-01", spec)
        self.assertIn("EC-INPUT-02 (new)", spec)
        self.assertIn("EC-NET-01", spec)
        # personas, flows, open questions resolved
        self.assertIn("P1 — Sara, shop owner", spec)
        self.assertIn("F-01 — Record a sale", spec)
        self.assertIn("OQ-01", spec)
        self.assertNotIn("Reza", spec)  # P2 is not referenced by this epic
        self.assertIn("**Definition of Done**", spec)

        plan = (f / "plan.md").read_text(encoding="utf-8")
        self.assertIn("E01-S01-T2 API-01 handler.", plan)
        self.assertIn("### US2 — E01-S02 Undo the last sale", plan)
        self.assertIn("12.2 Module map", plan)
        self.assertIn("[VERIFY-AT-BUILD]", plan)
        self.assertIn("R-01", plan)

        dm = (f / "data-model.md").read_text(encoding="utf-8")
        self.assertIn("**ENT-Sale**", dm)
        self.assertIn("amount_rial", dm)
        self.assertIn("integer rials", dm)  # §12.4 conventions
        self.assertNotIn("ENT-Shop", dm)

        api = (f / "contracts" / "api.md").read_text(encoding="utf-8")
        self.assertIn("API-01", api)
        self.assertNotIn("API-02", api)
        self.assertIn("error envelope", api)
        self.assertIn("Kavenegar", (f / "contracts" / "integrations.md").read_text(encoding="utf-8"))
        self.assertIn("AD-1", (f / "research.md").read_text(encoding="utf-8"))

        quick = (f / "quickstart.md").read_text(encoding="utf-8")
        self.assertIn("Record and undo end to end", quick)

        self.assertEqual(
            json.loads((self.tmp / ".specify" / "feature.json").read_text())["feature_directory"],
            "specs/002-e01-record-sales",
        )

    def test_second_level_copy_from_flow(self):
        self.json_cli("compile", "E00")
        spec = (self.feature("E00") / "spec.md").read_text(encoding="utf-8")
        self.assertIn("DR-01", (self.feature("E00") / "research.md").read_text(encoding="utf-8"))
        self.assertIn("FF-01", (self.feature("E00") / "research.md").read_text(encoding="utf-8"))
        self.assertIn("Manual", (self.feature("E00") / "quickstart.md").read_text(encoding="utf-8"))
        self.assertNotIn("data-model.md", json.loads((self.feature("E00") / ".blueprint.json").read_text())["files"])
        self.assertIn("Sara", spec)

    def test_recompile_refuses_over_finished_tasks(self):
        self.json_cli("compile", "E01")
        (self.feature() / "tasks.md").write_text("- [X] T001 done\n- [ ] T002 todo\n")
        res = self.run_cli("compile", "E01", check=False)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("completed tasks", res.stderr)
        self.json_cli("compile", "E01", "--force")

    def test_refs_and_unresolved(self):
        self.assertEqual(self.run_cli("refs").returncode, 0)
        bp = self.tmp / "docs" / "BLUEPRINT.md"
        bp.write_text(bp.read_text(encoding="utf-8").replace("ENT-Sale migration", "ENT-Refund migration"), encoding="utf-8")
        res = self.run_cli("refs", check=False)
        self.assertEqual(res.returncode, 1)
        self.assertIn("ENT-Refund", json.loads(res.stdout)["E01"]["unresolved"])


class StatusTest(ProjectTest):
    def state(self):
        return self.json_cli("status")

    def test_walks_the_lifecycle(self):
        self.assertEqual(self.state()["next"]["command"], "speckit-blueprint-bootstrap")
        self.json_cli("bootstrap")
        st = self.state()
        self.assertEqual(st["constitution"], "compiled")
        self.assertEqual((st["next"]["command"], st["next"]["epic"]), ("speckit-blueprint-compile", "E00"))

        self.json_cli("compile", "E00")
        self.assertEqual(self.state()["next"]["command"], "speckit-tasks")
        tasks = self.feature("E00") / "tasks.md"
        tasks.write_text("- [ ] T001 [US1] E00-S01-T1 init\n- [ ] T002 [US1] test\n")
        self.assertEqual(self.state()["epics"][0]["state"], "tasked")
        tasks.write_text("- [x] T001 [US1] E00-S01-T1 init\n- [ ] T002 [US1] test\n")
        st = self.state()
        self.assertEqual((st["epics"][0]["state"], st["next"]["command"]), ("in-progress", "speckit-implement"))
        tasks.write_text("- [x] T001 a\n- [X] T002 b\n")
        self.assertEqual(self.state()["next"]["command"], "speckit-blueprint-review")
        (self.feature("E00") / "review.md").write_text("Status: IN PROGRESS\n")
        self.assertEqual(self.state()["epics"][0]["state"], "implemented")
        (self.feature("E00") / "review.md").write_text("Status: DONE\n# Handoff\n")
        st = self.state()
        self.assertEqual(st["epics"][0]["state"], "done")
        self.assertEqual((st["next"]["command"], st["next"]["epic"]), ("speckit-blueprint-compile", "E01"))

    def test_stale_after_blueprint_change(self):
        self.json_cli("bootstrap")
        self.json_cli("compile", "E01")
        bp = self.tmp / "docs" / "BLUEPRINT.md"
        bp.write_text(bp.read_text(encoding="utf-8").replace("| CP-SCR01-2 | Button | ثبت |", "| CP-SCR01-2 | Button | ذخیره |"), encoding="utf-8")
        stale = self.json_cli("stale")
        self.assertEqual([s["epic"] for s in stale], ["E01"])
        self.assertIn("SCR-01", stale[0]["changed"])
        e01 = next(e for e in self.state()["epics"] if e["epic"] == "E01")
        self.assertEqual(e01["state"], "stale")

    def test_no_blueprint(self):
        (self.tmp / "docs" / "BLUEPRINT.md").unlink()
        st = self.state()
        self.assertEqual((st["state"], st["next"]["command"]), ("no-blueprint", "speckit-blueprint-discover"))


class BootstrapTest(ProjectTest):
    def test_outputs_and_idempotence(self):
        (self.tmp / "CLAUDE.md").write_text("# My rules\n\nKeep me.\n")
        out = self.json_cli("bootstrap")
        self.assertEqual(out["constitution"]["missing_sections"], [])
        c = (self.tmp / ".specify" / "memory" / "constitution.md").read_text(encoding="utf-8")
        self.assertIn("# Tally Constitution", c)
        self.assertIn("No ORMs.", c)
        self.assertIn("**Version**: 1.0.0", c)
        claude = (self.tmp / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("Keep me.", claude)
        self.assertEqual(claude.count("speckit-blueprint:start"), 1)
        self.assertIn("Every AC has a test", (self.tmp / "docs" / "REVIEW-CHECKLIST.md").read_text(encoding="utf-8"))
        self.assertIn("| DR-01 | Integer rials | blueprint | accepted |", (self.tmp / "docs" / "DECISIONS.md").read_text(encoding="utf-8"))

        # unchanged blueprint → same version, one managed block
        self.json_cli("bootstrap")
        c2 = (self.tmp / ".specify" / "memory" / "constitution.md").read_text(encoding="utf-8")
        self.assertIn("**Version**: 1.0.0", c2)
        self.assertEqual((self.tmp / "CLAUDE.md").read_text(encoding="utf-8").count("speckit-blueprint:start"), 1)

        # changed constitution section → patch bump
        bp = self.tmp / "docs" / "BLUEPRINT.md"
        bp.write_text(bp.read_text(encoding="utf-8").replace("No ORMs.", "No ORMs. No GraphQL."), encoding="utf-8")
        self.json_cli("bootstrap")
        self.assertIn("**Version**: 1.0.1", (self.tmp / ".specify" / "memory" / "constitution.md").read_text(encoding="utf-8"))


class HookTest(ProjectTest):
    def guard(self, tool, path):
        payload = json.dumps({"tool_name": tool, "tool_input": {"file_path": str(self.tmp / path)}})
        return self.run_cli("hook", "guard", stdin=payload, check=False)

    def test_guard(self):
        self.json_cli("bootstrap")
        self.json_cli("compile", "E01")
        f = "specs/002-e01-record-sales"
        self.assertEqual(self.guard("Edit", f"{f}/spec.md").returncode, 2)
        self.assertEqual(self.guard("Write", f"{f}/contracts/api.md").returncode, 2)
        self.assertEqual(self.guard("Edit", ".specify/memory/constitution.md").returncode, 2)
        self.assertEqual(self.guard("Edit", f"{f}/tasks.md").returncode, 0)
        self.assertEqual(self.guard("Write", f"{f}/review.md").returncode, 0)
        self.assertEqual(self.guard("Edit", "docs/BLUEPRINT.md").returncode, 0)
        self.assertEqual(self.guard("Read", f"{f}/spec.md").returncode, 0)
        cfg = self.tmp / ".specify" / "extensions" / "blueprint"
        cfg.mkdir(parents=True)
        (cfg / "blueprint-config.yml").write_text("guard: false\n")
        self.assertEqual(self.guard("Edit", f"{f}/spec.md").returncode, 0)

    def test_session_start_brief(self):
        out = self.run_cli("hook", "session-start", stdin="{}").stdout
        self.assertIn("Tally: 0/2 epics done", out)
        self.assertIn("/speckit-blueprint-bootstrap", out)


class LookupTest(ProjectTest):
    def test_section_and_find(self):
        self.assertIn("`npm run check`", self.run_cli("section", "13.4").stdout)
        out = self.run_cli("find", "ENT-Shop", "CP-SCR01-3").stdout
        self.assertIn("`name` text", out)
        self.assertIn("مبلغ نامعتبر است", out)
        self.assertNotEqual(self.run_cli("find", "ENT-Nope", check=False).returncode, 0)


class ConfigTest(ProjectTest):
    def test_config_overrides(self):
        cfg = self.tmp / ".specify" / "extensions" / "blueprint"
        cfg.mkdir(parents=True)
        (cfg / "blueprint-config.yml").write_text(
            "# comment\nspecs_dir: features\nplan_sections:\n  - \"13.4\"\nconstitution_sections: [\"13.2\"]\n"
        )
        out = self.json_cli("compile", "E01")
        self.assertTrue(out["feature_directory"].startswith("features/"))
        plan = (self.tmp / out["feature_directory"] / "plan.md").read_text(encoding="utf-8")
        self.assertIn("npm run check", plan)
        self.assertNotIn("12.2 Module map", plan)


if __name__ == "__main__":
    unittest.main()
