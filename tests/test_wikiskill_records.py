"""Campus AI OS 5.3.0 item 3 of the PRD - WikiSkill records B/C.

B: `skill_version` is an optional ledger key (read from the skill's frontmatter).
C: every kernel playbook carries a one-line PURPOSE, and a promoted skill keeps the
   PURPOSE its candidate was drafted with (promote-skills writes it, review-candidates keeps it).
The harness-written skill-impact record is NOT built here (owed; see BUILD-NOTES).
Kernel-only; runs everywhere.
platform: claude-code; seat: m4-claude-code
"""
import importlib
import json
import os
import sys
import unittest
from pathlib import Path

KERNEL = Path(os.environ.get("KERNEL_SRC", Path(__file__).resolve().parent.parent)).resolve()


class WikiSkillRecords(unittest.TestCase):
    def test_skill_version_is_an_optional_string(self):
        if str(KERNEL / "tools") not in sys.path:
            sys.path.insert(0, str(KERNEL / "tools"))
        vl = importlib.import_module("validate_ledger")
        schema = vl.load_schema(KERNEL / "schemas" / "ledger-line.schema.json")
        self.assertEqual(schema["properties"]["skill_version"]["type"], "string")
        self.assertNotIn("skill_version", schema["required"])
        base = {"ts": "2026-09-23T01:00:00Z", "seat": "m4-mini", "skill": "weekly-review", "dept": "dean", "outcome": "completed"}
        self.assertEqual(vl.classify(base, schema, write=True)[0], "valid")
        self.assertEqual(vl.classify(dict(base, skill_version="5.2.10"), schema, write=True)[0], "valid")
        self.assertEqual(vl.classify(dict(base, skill_version=5.2), schema)[0], "invalid")
        canon = (KERNEL / "templates" / "ledger-paths.md").read_text(encoding="utf-8")
        line = next((l for l in canon.splitlines() if "`skill_version`" in l), "")
        self.assertIn("never typed from memory", line)

    def test_every_kernel_playbook_carries_one_purpose_line(self):
        books = sorted(KERNEL.glob("playbooks/*/SKILL.md"))
        self.assertGreaterEqual(len(books), 2)
        for b in books:
            lines = [l for l in b.read_text(encoding="utf-8").splitlines() if l.startswith("**PURPOSE:**")]
            self.assertEqual(len(lines), 1, f"{b.parent.name}: exactly one **PURPOSE:** line")
            self.assertGreaterEqual(len(lines[0].split()), 12, f"{b.parent.name}: PURPOSE says too little")
            self.assertIn("evidence", lines[0], f"{b.parent.name}: PURPOSE must say where the evidence lives")
        readme = (KERNEL / "playbooks" / "README.md").read_text(encoding="utf-8")
        self.assertIn("- **PURPOSE**", readme)

    def test_promoted_skills_carry_purpose(self):
        promote = (KERNEL / "skills" / "promote-skills" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("\npurpose: \"", promote)
        self.assertIn("\n**PURPOSE:** ", promote)
        review = (KERNEL / "skills" / "review-candidates" / "SKILL.md").read_text(encoding="utf-8")
        line = next((l for l in review.splitlines() if l.startswith("1. Create `{dept-folder}/skills/{slug}/SKILL.md`")), "")
        for needle in ("`version: 1.0.0`", "`purpose:`", "`**PURPOSE:**` line kept"):
            self.assertIn(needle, line)

    def test_playbook_ledger_example_carries_skill_version(self):
        readme = (KERNEL / "playbooks" / "README.md").read_text(encoding="utf-8")
        ex = next(l for l in readme.splitlines() if l.startswith('{"ts"') and '"outcome":' in l)
        self.assertIn('"skill_version":', ex)
        json.loads(ex.replace('{version from its frontmatter}', '1.0.0').replace('"...', '"x').replace('S###', 'S1'))


if __name__ == "__main__":
    unittest.main()
