"""Campus AI OS 5.2.0 Phase 3.6 - materialized registration spec (defaults + campus overrides + stamp).

Temp campuses only. The Foundry reader check runs only when a Foundry sits beside this tree.
platform: claude-code; seat: m4-claude-code
"""
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KERNEL = Path(os.environ.get("KERNEL_SRC", Path(__file__).resolve().parent.parent)).resolve()
FOUNDRY = Path(os.environ.get("FOUNDRY_SRC", KERNEL.parents[2] / "library/teams/_foundry")).resolve()
TOOL = KERNEL / "tools" / "materialize_registration_spec.py"
TEMPLATE = KERNEL / "templates" / "registration-block-spec.md"
SPEC = Path(".campus-os/registration-block-spec.md")
OVR = Path(".campus-os/registration-overrides.json")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class Materialize(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="campus-phase36-")
        self.addCleanup(self.tmp.cleanup)
        self.campus = Path(self.tmp.name) / "campus"
        (self.campus / ".campus-os").mkdir(parents=True)

    def run_tool(self, *args):
        return subprocess.run([sys.executable, str(TOOL), "--campus-root", str(self.campus), "--kernel", str(KERNEL),
                               *map(str, args)], text=True, capture_output=True, timeout=60)

    def spec_text(self):
        return (self.campus / SPEC).read_text(encoding="utf-8")

    def enum(self, text):
        m = re.search(r'^\s*"department"\s*:\s*"([^"]+)"', text, re.M)
        return [v.strip() for v in m.group(1).split("|")]

    # --- founding: no overrides -----------------------------------------
    def test_fresh_campus_gets_template_plus_stamp(self):
        p = self.run_tool()
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        text = self.spec_text()
        self.assertTrue(text.startswith("<!-- campus-ai-os:registration-block-spec materialized | template_sha256="))
        body = text.split("\n", 2)[2]
        self.assertEqual(body, TEMPLATE.read_text(encoding="utf-8"))
        self.assertEqual(self.run_tool("--check").returncode, 0)

    def test_idempotent(self):
        self.run_tool()
        first = self.spec_text()
        p = self.run_tool("--json")
        self.assertEqual(p.returncode, 0)
        self.assertFalse(json.loads(p.stdout)["written"])
        self.assertEqual(self.spec_text(), first)

    # --- overrides -------------------------------------------------------
    def test_overrides_extend_enum_and_keep_notes(self):
        (self.campus / OVR).write_text(json.dumps({"schema_version": "1",
                                                   "departments_extra": ["coaching-delivery"],
                                                   "annotations": ["- **`coaching-delivery`** — added by the owner 2026-09-07."]}),
                                       encoding="utf-8")
        p = self.run_tool()
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        text = self.spec_text()
        vals = self.enum(text)
        self.assertEqual(vals[-1], "coaching-delivery")
        self.assertEqual(vals[:-1], self.enum(TEMPLATE.read_text(encoding="utf-8")))
        self.assertIn("## Campus notes (owner-written; preserved across upgrades)", text)
        self.assertIn("added by the owner", text)
        self.assertEqual(self.run_tool("--check").returncode, 0)

    def test_invalid_override_id_is_exit_2(self):
        (self.campus / OVR).write_text(json.dumps({"departments_extra": ["Bad Id"]}), encoding="utf-8")
        self.assertEqual(self.run_tool().returncode, 2)

    def test_kernel_readers_parse_the_materialized_copy(self):
        (self.campus / OVR).write_text(json.dumps({"departments_extra": ["coaching-delivery"]}), encoding="utf-8")
        self.run_tool()
        v = load("validate_registry", KERNEL / "tools" / "validate_registry.py")
        enums = v.enums_from_spec(self.campus / SPEC)
        self.assertIn("coaching-delivery", enums["department"])
        self.assertIn("plugin", enums["type"])
        # an entry filed under the campus department validates
        entry = {"team": "coach-team", "type": "plugin", "status": "active", "department": "coaching-delivery",
                 "version": "1.0.0"}
        self.assertEqual(v.validate([entry], enums), [])

    # --- states ----------------------------------------------------------
    def test_states_missing_stale_drift_hand_edited(self):
        self.assertEqual(self.run_tool("--check").returncode, 1)
        self.assertIn("missing", self.run_tool("--check", "--json").stdout)
        self.run_tool()
        text = self.spec_text()
        stale = re.sub(r"template_sha256=[0-9a-f]{64}", "template_sha256=" + "0" * 64, text, count=1)
        (self.campus / SPEC).write_text(stale, encoding="utf-8")
        self.assertEqual(json.loads(self.run_tool("--check", "--json").stdout)["state"], "stale-template")
        self.run_tool()  # refresh
        self.assertEqual(json.loads(self.run_tool("--check", "--json").stdout)["state"], "current")
        (self.campus / OVR).write_text(json.dumps({"departments_extra": ["x-dept"]}), encoding="utf-8")
        self.assertEqual(json.loads(self.run_tool("--check", "--json").stdout)["state"], "overrides-drift")
        (self.campus / OVR).unlink()
        (self.campus / SPEC).write_text(TEMPLATE.read_text(encoding="utf-8") + "\n- owner line\n", encoding="utf-8")
        self.assertEqual(json.loads(self.run_tool("--check", "--json").stdout)["state"], "hand-edited")

    def test_hand_edited_copy_is_never_clobbered_without_capture(self):
        hand = TEMPLATE.read_text(encoding="utf-8").replace(
            '"department": "marketing', '"department": "coaching-delivery | marketing', 1) + "\n- **owner canon line kept**\n"
        (self.campus / SPEC).write_text(hand, encoding="utf-8")
        p = self.run_tool()
        self.assertEqual(p.returncode, 1)
        self.assertIn("capture-notes", p.stderr)
        self.assertEqual(self.spec_text(), hand, "must not touch a hand-edited copy")
        p = self.run_tool("--capture-notes")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        ovr = json.loads((self.campus / OVR).read_text(encoding="utf-8"))
        self.assertEqual(ovr["departments_extra"], ["coaching-delivery"])
        self.assertIn("- **owner canon line kept**", ovr["annotations"])
        text = self.spec_text()
        self.assertIn("coaching-delivery", self.enum(text))
        self.assertIn("owner canon line kept", text)
        self.assertEqual(self.run_tool("--check").returncode, 0)
        # a second capture refuses unless forced
        self.assertEqual(self.run_tool("--capture-notes").returncode, 1)

    def test_dry_run_writes_nothing(self):
        p = self.run_tool("--dry-run")
        self.assertEqual(p.returncode, 0)
        self.assertIn("materialized | template_sha256=", p.stdout)
        self.assertFalse((self.campus / SPEC).exists())

    # --- founding/migration name it; doctor reads it -----------------------
    def test_migration_materializes_on_every_path(self):
        # Found on the 5.2.2 sign-off: materialization lived only in baseline item 8, which
        # 4.x+ campuses skip, so no upgraded campus ever got a stamped spec.
        text = (KERNEL / "skills/update-workspace/SKILL.md").read_text(encoding="utf-8")
        tail = text[text.index("run on every path"):]
        self.assertIn("materialize_registration_spec.py", tail,
                      "the materializer must be an every-campus additions item, not only baseline item 8")

    def test_founding_migration_and_doctor_name_the_tool(self):
        for rel in ("skills/campus-start/SKILL.md", "skills/update-workspace/SKILL.md", "skills/campus-doctor/SKILL.md"):
            self.assertIn("materialize_registration_spec.py", (KERNEL / rel).read_text(encoding="utf-8"), rel)


@unittest.skipUnless((FOUNDRY / "bin/_common.py").is_file(), "no Foundry beside this tree")
class FoundryReader(unittest.TestCase):
    def test_foundry_department_enum_reads_overrides(self):
        with tempfile.TemporaryDirectory(prefix="campus-phase36f-") as tmp:
            campus = Path(tmp) / "campus"
            (campus / ".campus-os").mkdir(parents=True)
            (campus / OVR).write_text(json.dumps({"departments_extra": ["coaching-delivery"]}), encoding="utf-8")
            p = subprocess.run([sys.executable, str(TOOL), "--campus-root", str(campus), "--kernel", str(KERNEL)],
                               text=True, capture_output=True, timeout=60)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            sys.path.insert(0, str(FOUNDRY / "bin"))
            try:
                common = importlib.import_module("_common")
            finally:
                sys.path.pop(0)
            vals, spec_path = common.department_enum(str(campus))
            self.assertEqual(Path(spec_path).resolve(), (campus / SPEC).resolve())
            self.assertIn("coaching-delivery", vals)
            self.assertIn("marketing", vals)


if __name__ == "__main__":
    unittest.main()
