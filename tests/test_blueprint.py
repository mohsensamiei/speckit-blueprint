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

    def test_accept_keeps_a_built_epic(self):
        self.json_cli("bootstrap")
        self.json_cli("compile", "E01")
        (self.feature() / "tasks.md").write_text("- [x] T001 a\n")
        (self.feature() / "review.md").write_text("Status: DONE\n")
        bp = self.tmp / "docs" / "BLUEPRINT.md"
        bp.write_text(bp.read_text(encoding="utf-8").replace("| CP-SCR01-2 | Button | ثبت |", "| CP-SCR01-2 | Button | ذخیره |"), encoding="utf-8")
        self.assertEqual([s["epic"] for s in self.json_cli("stale")], ["E01"])
        self.assertNotEqual(self.run_cli("accept", "E01", check=False).returncode, 0)  # a note is required
        out = self.json_cli("accept", "E01", "--note", "covered by E02 (A-01)")
        self.assertIn("SCR-01", out["accepted"])
        self.assertEqual(self.json_cli("stale"), [])
        e01 = next(e for e in self.state()["epics"] if e["epic"] == "E01")
        self.assertNotIn("changed_since_compile", e01)
        trace = json.loads((self.feature() / ".blueprint.json").read_text(encoding="utf-8"))
        self.assertEqual(trace["accepted"][0]["note"], "covered by E02 (A-01)")
        self.assertIn("ثبت", (self.feature() / "spec.md").read_text(encoding="utf-8"))  # compiled files untouched

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
        self.assertNotIn("AGENTS.md", claude)  # the block names no file the project may not have
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


PROJECT_CONSTITUTION = """<!--
Sync Impact Report
- Version change: 2.2.0 → 2.3.0 (principle I reworded)
-->
# Evida Constitution

## Core Principles

### I. One planning home
Every change, however small, is recorded as a Spec Kit task first.

## Governance

Amendments need two approvals.

**Version**: 2.3.0 | **Ratified**: 2025-01-01 | **Last Amended**: 2026-09-01
"""


class AdoptTest(ProjectTest):
    """An existing Spec Kit project: its constitution, checklist and features stay its own."""

    def setUp(self):
        super().setUp()
        self.cpath = self.tmp / ".specify" / "memory" / "constitution.md"
        self.cpath.write_text(PROJECT_CONSTITUTION, encoding="utf-8")
        (self.tmp / "docs" / "REVIEW-CHECKLIST.md").write_text("# Our checklist\n- [ ] Two reviewers\n")
        (self.tmp / "specs" / "001-existing-work").mkdir(parents=True)

    def test_bootstrap_appends_a_managed_block(self):
        out = self.json_cli("bootstrap")
        self.assertEqual(out["constitution"]["mode"], "append")
        self.assertEqual((out["constitution"]["block"], out["constitution"]["version"]), ("added", "2.3.0 → 2.4.0"))
        c = self.cpath.read_text(encoding="utf-8")
        before, rest = c.split("<!-- speckit-blueprint:rules:start -->")
        block, after = rest.split("<!-- speckit-blueprint:rules:end -->")
        # the project's text is kept; only the report gains a line
        self.assertIn("Sync Impact Report\n- Version change: 2.3.0 → 2.4.0", before)
        self.assertIn("Blueprint Rules block added by speckit-blueprint", before)
        self.assertIn("- Version change: 2.2.0 → 2.3.0 (principle I reworded)", before)
        self.assertIn(PROJECT_CONSTITUTION.split("-->\n")[1].split("## Governance")[0], before)
        self.assertTrue(after.lstrip().startswith("## Governance"))
        self.assertRegex(after, r"\*\*Version\*\*: 2\.4\.0 \| \*\*Ratified\*\*: 2025-01-01 \| \*\*Last Amended\*\*: \d{4}-\d{2}-\d{2}")
        self.assertNotIn("2026-09-01", after)
        self.assertIn("### B-I. The blueprint is the source of truth", block)
        self.assertIn("the principles above win", block)
        self.assertIn("No ORMs.", block)
        self.assertEqual((self.tmp / "docs" / "REVIEW-CHECKLIST.md").read_text(), "# Our checklist\n- [ ] Two reviewers\n")
        self.assertEqual(self.json_cli("status")["constitution"], "appended")
        self.assertEqual(self.json_cli("status")["next"]["command"], "speckit-blueprint-compile")
        # compile continues the project's numbering
        self.assertEqual(self.json_cli("compile", "E00")["feature_directory"], "specs/002-e00-foundation")

        # idempotent (no second bump); a project edit outside the block survives a re-run
        self.cpath.write_text(c.replace("however small", "however small (agreed 2026)"), encoding="utf-8")
        self.assertEqual(self.json_cli("bootstrap")["constitution"]["version"], "unchanged")
        c2 = self.cpath.read_text(encoding="utf-8")
        self.assertIn("however small (agreed 2026)", c2)
        self.assertIn("**Version**: 2.4.0", c2)
        self.assertEqual(c2.count("speckit-blueprint:rules:start"), 1)
        # a blueprint change rewrites only the block
        bp = self.tmp / "docs" / "BLUEPRINT.md"
        bp.write_text(bp.read_text(encoding="utf-8").replace("No ORMs.", "No ORMs. No GraphQL."), encoding="utf-8")
        self.assertEqual(self.json_cli("bootstrap")["constitution"]["block"], "updated")
        c3 = self.cpath.read_text(encoding="utf-8")
        self.assertIn("No GraphQL.", c3)
        self.assertIn("**Version**: 2.5.0", c3)
        self.assertIn("2.4.0 → 2.5.0", c3)
        self.assertIn("Blueprint Rules block updated", c3)

    def test_no_sync_impact_report_is_created(self):
        # Spec Kit removes the report before committing an amendment; bootstrap must not leave a new one behind
        self.cpath.write_text(PROJECT_CONSTITUTION.split("-->\n", 1)[1], encoding="utf-8")
        out = self.json_cli("bootstrap")
        self.assertEqual(out["constitution"]["version"], "2.3.0 → 2.4.0")
        self.assertIn("Blueprint Rules block added", out["constitution"]["amendment"])
        c = self.cpath.read_text(encoding="utf-8")
        self.assertNotIn("Sync Impact Report", c)
        self.assertTrue(c.startswith("# Evida Constitution"))
        self.assertIn("**Version**: 2.4.0", c)

    def test_version_bump_can_be_switched_off(self):
        cfg = self.tmp / ".specify" / "extensions" / "blueprint"
        cfg.mkdir(parents=True)
        (cfg / "blueprint-config.yml").write_text("constitution_version_bump: none\n")
        self.assertEqual(self.json_cli("bootstrap")["constitution"]["version"], "unchanged")
        c = self.cpath.read_text(encoding="utf-8")
        self.assertIn("**Version**: 2.3.0 | **Ratified**: 2025-01-01 | **Last Amended**: 2026-09-01", c)
        self.assertIn("speckit-blueprint:rules:start", c)

    def test_guard_protects_only_the_block(self):
        self.json_cli("bootstrap")
        text = self.cpath.read_text(encoding="utf-8")

        def guard(tool, ti):
            ti = {"file_path": str(self.cpath), **ti}
            return self.run_cli("hook", "guard", stdin=json.dumps({"tool_name": tool, "tool_input": ti}), check=False).returncode

        self.assertEqual(guard("Edit", {"old_string": "however small", "new_string": "x"}), 0)
        self.assertEqual(guard("Edit", {"old_string": "No ORMs.", "new_string": "ORMs ok."}), 2)
        self.assertEqual(guard("MultiEdit", {"edits": [{"old_string": "however small"}, {"old_string": "B-II."}]}), 2)
        self.assertEqual(guard("Write", {"content": text.replace("however small", "x")}), 0)
        self.assertEqual(guard("Write", {"content": text.replace("No ORMs.", "")}), 2)
        self.assertEqual(guard("Write", {"content": PROJECT_CONSTITUTION}), 2)

    def test_template_constitution_is_replaced(self):
        self.cpath.write_text("# [PROJECT_NAME] Constitution\n", encoding="utf-8")
        self.assertEqual(self.json_cli("bootstrap")["constitution"]["mode"], "own")
        self.assertEqual(self.json_cli("status")["constitution"], "compiled")

    def test_session_start_is_silent_without_a_blueprint(self):
        (self.tmp / "docs" / "BLUEPRINT.md").unlink()
        (self.tmp / ".specify" / "extensions" / "blueprint").mkdir(parents=True)
        self.assertEqual(self.run_cli("hook", "session-start", stdin="{}").stdout, "")
        # a fresh `specify init` project still gets the hint
        shutil.rmtree(self.tmp / "specs")
        self.cpath.write_text("# [PROJECT_NAME] Constitution\n", encoding="utf-8")
        self.assertIn("/speckit-blueprint-discover", self.run_cli("hook", "session-start", stdin="{}").stdout)


class ProjectLayoutTest(ProjectTest):
    """Options for projects that keep their own layout: repositories per epic, paths, CLAUDE.md."""

    def test_repository_fields_become_sections(self):
        bp = self.tmp / "docs" / "BLUEPRINT.md"
        bp.write_text(bp.read_text(encoding="utf-8").replace(
            "**Risks specific to this epic** R-01.\n",
            "**Risks specific to this epic** R-01.\n"
            "**Target repositories**\n\n| Repository | Role |\n|---|---|\n| `core` | Provides the sale API |\n| `app` | Consumes it |\n\n"
            "**Repositories** — Order: `core` first, then `app`.\n\n- `core`: base `master`, branch `feat/sales`, provides API-01.\n",
        ), encoding="utf-8")
        self.json_cli("compile", "E01")
        spec = (self.feature() / "spec.md").read_text(encoding="utf-8")
        plan = (self.feature() / "plan.md").read_text(encoding="utf-8")
        self.assertIn("## Target Repositories\n\n| Repository | Role |", spec)
        self.assertIn("| `app` | Consumes it |", spec)
        context = spec.split("## Epic Context")[1].split("## Target Repositories")[0]
        self.assertNotIn("Target repositories", context)
        self.assertNotIn("feat/sales", spec)
        self.assertIn("## Repositories\n\nOrder: `core` first, then `app`.", plan.replace("— ", ""))
        self.assertIn("- `core`: base `master`, branch `feat/sales`, provides API-01.", plan)
        self.assertLess(plan.index("## Constitution Check"), plan.index("## Repositories"))
        self.assertLess(plan.index("## Repositories"), plan.index("## Project Structure"))

    def test_without_fields_no_sections(self):
        self.json_cli("compile", "E01")
        self.assertNotIn("## Target Repositories", (self.feature() / "spec.md").read_text(encoding="utf-8"))

    def test_paths_and_claude_md_switch(self):
        cfg = self.tmp / ".specify" / "extensions" / "blueprint"
        cfg.mkdir(parents=True)
        (cfg / "blueprint-config.yml").write_text(
            "blueprint_path: specs/blueprint/BLUEPRINT.md\ndecisions_path: specs/blueprint/DECISIONS.md\n"
            "review_checklist_path: specs/blueprint/REVIEW-CHECKLIST.md\nclaude_md: false\n"
        )
        (self.tmp / "specs" / "blueprint").mkdir(parents=True)
        shutil.move(str(self.tmp / "docs" / "BLUEPRINT.md"), self.tmp / "specs" / "blueprint" / "BLUEPRINT.md")
        (self.tmp / "CLAUDE.md").write_text("@AGENTS.md\n")
        out = self.json_cli("bootstrap")
        self.assertEqual(out["claude_md"], "skipped (claude_md: false)")
        self.assertEqual((self.tmp / "CLAUDE.md").read_text(), "@AGENTS.md\n")
        self.assertTrue((self.tmp / "specs" / "blueprint" / "DECISIONS.md").is_file())
        self.assertTrue((self.tmp / "specs" / "blueprint" / "REVIEW-CHECKLIST.md").is_file())
        self.assertFalse((self.tmp / "docs" / "DECISIONS.md").exists())
        c = (self.tmp / ".specify" / "memory" / "constitution.md").read_text(encoding="utf-8")
        self.assertIn("`specs/blueprint/DECISIONS.md`", c)
        self.assertNotIn("docs/DECISIONS.md", c)
        st = self.json_cli("status")
        self.assertEqual((st["decisions"], st["review_checklist"]), ("specs/blueprint/DECISIONS.md", "specs/blueprint/REVIEW-CHECKLIST.md"))
        # the blueprint folder under specs/ is not mistaken for a feature
        out = self.json_cli("compile", "E00")
        self.assertTrue(out["feature_directory"].startswith("specs/001-"))
        plan = (self.tmp / out["feature_directory"] / "plan.md").read_text(encoding="utf-8")
        self.assertIn("`specs/blueprint/DECISIONS.md`", plan)


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


MULTI_CONFIG = """# two products in one planning repository
default_blueprint: one
blueprints:
  one:
    path: docs/BLUEPRINT.md
  desk:
    path: docs/desk/BLUEPRINT.md
    number_base: 500
    constitution_sections: ["13.2"]
    sources:
      - ../evida-desk  # the product's code lives next door
      - ../desk-prototype
"""


class MultiBlueprintTest(ProjectTest):
    """Two blueprints (ONE, the existing one, and DESK) in one project: nothing of one touches the other."""

    def setUp(self):
        super().setUp()
        (self.tmp / "docs" / "desk").mkdir()
        desk = FIXTURE.read_text(encoding="utf-8").replace("# Tally", "# Desk", 1).replace("No ORMs.", "Desk rules: Dart only.")
        (self.tmp / "docs" / "desk" / "BLUEPRINT.md").write_text(desk, encoding="utf-8")
        self.cfg_dir = self.tmp / ".specify" / "extensions" / "blueprint"
        self.cfg_dir.mkdir(parents=True)

    def configure(self, text=MULTI_CONFIG):
        (self.cfg_dir / "blueprint-config.yml").write_text(text, encoding="utf-8")

    def legacy_one(self):
        """ONE as it was before blueprint ids: bare markers, folders without blueprint_id."""
        self.json_cli("bootstrap")
        self.json_cli("compile", "E01")
        trace = self.feature() / ".blueprint.json"
        t = json.loads(trace.read_text(encoding="utf-8"))
        del t["blueprint_id"]
        trace.write_text(json.dumps(t), encoding="utf-8")
        (self.feature() / "tasks.md").write_text("- [x] T001 a\n- [ ] T002 b\n")

    def test_compile_never_reaches_the_other_blueprints_folder(self):
        self.legacy_one()
        spec_before = (self.feature() / "spec.md").read_text(encoding="utf-8")
        self.configure()
        out = self.json_cli("compile", "desk:E01")
        self.assertEqual(out["feature_directory"], "specs/502-desk-e01-record-sales")
        self.assertEqual(out["blueprint_id"], "desk")
        self.assertEqual((self.feature() / "spec.md").read_text(encoding="utf-8"), spec_before)
        desk = self.tmp / out["feature_directory"]
        self.assertEqual(json.loads((desk / ".blueprint.json").read_text())["blueprint_id"], "desk")
        self.assertIn("(blueprint `desk`)", (desk / "spec.md").read_text(encoding="utf-8"))
        self.assertIn("DESK:E01-S02-T3", (desk / "plan.md").read_text(encoding="utf-8"))
        # the legacy folder still belongs to ONE (the default): recompiling it hits the finished-task check
        res = self.run_cli("compile", "E01", "--blueprint", "one", check=False)
        self.assertIn("completed tasks", res.stderr)
        # the active feature decides the default: desk's folder is active now
        self.assertEqual(self.json_cli("compile", "E00")["feature_directory"], "specs/501-desk-e00-foundation")
        self.assertEqual(self.json_cli("compile", "E00", "--blueprint", "ONE")["feature_directory"], "specs/001-one-e00-foundation")
        res = self.run_cli("compile", "desk:E00", "--blueprint", "one", check=False)
        self.assertNotEqual(res.returncode, 0)

    def test_status_reads_each_blueprint_from_its_own_folders(self):
        self.legacy_one()
        self.configure()
        st = self.json_cli("status")  # active feature is ONE's E01
        self.assertEqual(st["blueprint_id"], "one")
        e01 = next(e for e in st["epics"] if e["epic"] == "E01")
        self.assertEqual((e01["state"], e01["feature_directory"]), ("in-progress", "specs/002-e01-record-sales"))
        self.assertEqual([b["blueprint_id"] for b in st["blueprints"]], ["one", "desk"])
        desk = st["blueprints"][1]
        self.assertEqual((desk["epics_done"], desk["constitution"]), (0, "not-from-blueprint"))
        self.assertEqual(desk["sources"], ["../evida-desk", "../desk-prototype"])
        self.assertEqual(desk["decisions"], "docs/desk/DECISIONS.md")
        st = self.json_cli("status", "--blueprint", "desk")
        self.assertTrue(all(e["state"] == "not-compiled" for e in st["epics"]))
        self.assertEqual(st["next"]["command"], "speckit-blueprint-bootstrap")
        brief = self.run_cli("status", "--brief").stdout
        self.assertIn("Tally (one)", brief)
        self.assertIn("Also: Desk (desk)", brief)
        self.assertIn("Tally (one)", self.run_cli("hook", "session-start", stdin="{}").stdout)

    def test_bootstrap_keeps_one_block_per_blueprint(self):
        cpath = self.tmp / ".specify" / "memory" / "constitution.md"
        cpath.write_text(PROJECT_CONSTITUTION, encoding="utf-8")
        (self.tmp / "CLAUDE.md").write_text("# Wiki rules\n")
        self.legacy_one()
        self.assertIn("<!-- speckit-blueprint:rules:start -->", cpath.read_text(encoding="utf-8"))
        self.configure()
        out = self.json_cli("bootstrap", "--blueprint", "desk")
        self.assertEqual((out["constitution"]["mode"], out["constitution"]["block"]), ("append", "added"))
        c = cpath.read_text(encoding="utf-8")
        self.assertIn("No ORMs.", c)  # ONE's rules survive
        self.assertIn("<!-- speckit-blueprint:rules:start id=desk -->", c)
        self.assertIn("Desk rules: Dart only.", c)
        self.assertIn('"blueprint_id": "desk"', c)
        self.assertIn("### DESK-I. The blueprint is the source of truth", c)
        self.assertLess(c.index("rules:end -->"), c.index("rules:start id=desk"))
        # ONE re-bootstraps: its bare block gets its id, DESK's block stays
        self.json_cli("bootstrap", "--blueprint", "one")
        c = cpath.read_text(encoding="utf-8")
        self.assertNotIn("<!-- speckit-blueprint:rules:start -->", c)
        self.assertEqual(c.count("speckit-blueprint:rules:start id=one"), 1)
        self.assertEqual(c.count("speckit-blueprint:rules:start id=desk"), 1)
        self.assertEqual(self.json_cli("status", "--blueprint", "desk")["constitution"], "appended")
        # rules prints only the active blueprint's block
        rules = self.run_cli("rules", "--blueprint", "desk").stdout
        self.assertIn("Dart only", rules)
        self.assertNotIn("No ORMs", rules)
        # CLAUDE.md: one block each, the project's text kept
        claude = (self.tmp / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("# Wiki rules", claude)
        self.assertEqual(claude.count("speckit-blueprint:start id=one"), 1)
        self.assertEqual(claude.count("speckit-blueprint:start id=desk"), 1)
        self.assertNotIn("<!-- speckit-blueprint:start -->", claude)
        self.assertIn("--blueprint desk", claude)
        # checklists and decisions are separate files; DESK's DR rows carry its prefix
        self.assertTrue((self.tmp / "docs" / "desk" / "REVIEW-CHECKLIST.md").is_file())
        self.assertIn("| DESK:DR-01 | Integer rials |", (self.tmp / "docs" / "desk" / "DECISIONS.md").read_text(encoding="utf-8"))
        self.assertIn("| DR-01 | Integer rials |", (self.tmp / "docs" / "DECISIONS.md").read_text(encoding="utf-8"))
        # the guard protects every block
        def guard(old):
            payload = {"tool_name": "Edit", "tool_input": {"file_path": str(cpath), "old_string": old}}
            return self.run_cli("hook", "guard", stdin=json.dumps(payload), check=False)
        self.assertEqual(guard("No ORMs.").returncode, 2)
        res = guard("Dart only.")
        self.assertEqual(res.returncode, 2)
        self.assertIn("docs/desk/BLUEPRINT.md", res.stderr)
        self.assertEqual(guard("however small").returncode, 0)

    def test_own_constitution_keeps_other_blocks(self):
        self.configure()
        self.assertEqual(self.json_cli("bootstrap", "--blueprint", "one")["constitution"]["mode"], "own")
        self.assertEqual(self.json_cli("bootstrap", "--blueprint", "desk")["constitution"]["mode"], "append")
        self.assertEqual(self.json_cli("bootstrap", "--blueprint", "one")["constitution"]["mode"], "own")
        c = (self.tmp / ".specify" / "memory" / "constitution.md").read_text(encoding="utf-8")
        self.assertIn("blueprint-id one", c.split("\n", 1)[0])
        self.assertIn("Desk rules: Dart only.", c)
        self.assertLess(c.index("rules:end id=desk"), c.index("## Governance"))
        self.assertEqual(self.json_cli("status", "--blueprint", "one")["constitution"], "compiled")
        self.assertEqual(self.json_cli("status", "--blueprint", "desk")["constitution"], "appended")
        cfg = MULTI_CONFIG + "constitution_mode: own\n"
        self.configure(cfg)
        self.assertIn("compiled whole from blueprint 'one'", self.run_cli("bootstrap", "--blueprint", "desk", check=False).stderr)

    def test_lookups_by_prefix(self):
        self.configure()
        out = self.run_cli("find", "DESK:DR-01", "one:ENT-Shop").stdout
        self.assertIn("<!-- DESK:DR-01 -->", out)
        self.assertIn("<!-- ONE:ENT-Shop -->", out)
        self.assertIn("Dart only", self.run_cli("section", "desk:13.2").stdout)
        self.assertIn("No ORMs", self.run_cli("section", "13.2").stdout)  # the default blueprint
        self.assertNotEqual(self.run_cli("find", "nope:DR-01", check=False).returncode, 0)

    def test_discover_mode_per_blueprint(self):
        self.configure()
        (self.tmp / "docs" / "desk" / "BLUEPRINT.md").unlink()
        st = self.json_cli("status", "--blueprint", "desk")
        self.assertEqual((st["state"], st["next"]["command"]), ("no-blueprint", "speckit-blueprint-discover"))
        self.assertEqual(st["blueprints"][0]["state"], "building")  # ONE is unaffected
        self.assertEqual(self.json_cli("status")["blueprint_id"], "one")

    def test_config_errors(self):
        self.configure("blueprints:\n  one:\n    path: docs/BLUEPRINT.md\n  desk:\n    path: docs/x.md\n    decisions: docs/DECISIONS.md\n")
        res = self.run_cli("status", check=False)
        self.assertIn("both use docs/DECISIONS.md", res.stderr)
        self.assertEqual(self.run_cli("hook", "guard", stdin="{}", check=False).returncode, 0)
        self.configure("blueprint_path: docs/BLUEPRINT.md\nblueprints:\n  desk:\n    path: docs/desk/BLUEPRINT.md\n")
        self.assertIn("ambiguous", self.run_cli("status", check=False).stderr)
        self.configure("blueprints:\n  Desk!:\n    path: x.md\n")
        self.assertIn("lowercase", self.run_cli("status", check=False).stderr)

    def test_single_blueprint_map_keeps_ids_out_of_ids(self):
        # one entry under `blueprints:`: folder names carry the id, IDs need no prefix
        self.configure("blueprints:\n  one:\n    path: docs/BLUEPRINT.md\n")
        out = self.json_cli("compile", "E01")
        self.assertEqual(out["feature_directory"], "specs/002-one-e01-record-sales")
        self.assertIn("E01-S02-T3", (self.tmp / out["feature_directory"] / "plan.md").read_text(encoding="utf-8"))
        self.assertNotIn("ONE:", (self.tmp / out["feature_directory"] / "plan.md").read_text(encoding="utf-8"))


class YamlTest(unittest.TestCase):
    def test_nested_maps_and_lists(self):
        sys.path.insert(0, str(REPO / "scripts"))
        import blueprint

        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / "c.yml").write_text(MULTI_CONFIG + "plan_sections:\n- \"13.4\"\nguard: false\n", encoding="utf-8")
            data = blueprint.load_simple_yaml(tmp / "c.yml")
        finally:
            shutil.rmtree(tmp)
        self.assertEqual(data["default_blueprint"], "one")
        self.assertEqual(data["blueprints"]["one"], {"path": "docs/BLUEPRINT.md"})
        self.assertEqual(data["blueprints"]["desk"]["constitution_sections"], ["13.2"])
        self.assertEqual(data["blueprints"]["desk"]["sources"], ["../evida-desk", "../desk-prototype"])
        self.assertEqual(data["blueprints"]["desk"]["number_base"], "500")
        self.assertEqual((data["plan_sections"], data["guard"]), (["13.4"], False))


if __name__ == "__main__":
    unittest.main()
