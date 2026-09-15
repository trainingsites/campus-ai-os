"""Campus AI OS 5.2.0 Phase 3.5 - one run-id/interop contract, per-team deltas.

Kernel-only checks run everywhere; fleet checks (the eleven team deltas, the Foundry
scaffold) run only when a campus and Foundry sit beside this tree.
platform: claude-code; seat: m4-claude-code
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KERNEL = Path(os.environ.get("KERNEL_SRC", Path(__file__).resolve().parent.parent)).resolve()
CAMPUS = Path(os.environ.get("CAMPUS_ROOT", KERNEL.parents[2])).resolve()
FOUNDRY = Path(os.environ.get("FOUNDRY_SRC", CAMPUS / "library/teams/_foundry")).resolve()
CANON = KERNEL / "templates" / "run-id-and-interop.md"
NAME = "run-id-and-interop.md"


def delta_files(root):
    return sorted(p for p in root.glob(f"library/**/{NAME}") if "campus-ai-os-v5-src" not in p.parts)


class Canon(unittest.TestCase):
    def test_canon_exists_and_states_the_contract(self):
        text = CANON.read_text(encoding="utf-8")
        for needle in ("tools/mint_run_id.py", "{slug}-{YYYYMMDD-HHMMSSfff}", "runs/{team}/{slug}/{run_id}/",
                       "schemas/results.schema.json", "tools/validate_results.py", '"1.1"',
                       "Ledger-lint", "attribution: {}", ".campus-os/run-id-and-interop.md"):
            self.assertIn(needle, text, needle)

    def test_founding_and_migration_both_copy_it(self):
        for rel in ("skills/campus-start/SKILL.md", "skills/update-workspace/SKILL.md"):
            self.assertIn(NAME, (KERNEL / rel).read_text(encoding="utf-8"), rel)

    def test_kernel_carries_exactly_one_copy(self):
        self.assertEqual([p for p in KERNEL.rglob(NAME)], [CANON])


@unittest.skipUnless((CAMPUS / "library/teams").is_dir(), "no campus library beside this tree")
class FleetDeltas(unittest.TestCase):
    def test_every_team_file_is_a_five_line_delta_naming_the_canon(self):
        files = delta_files(CAMPUS)
        self.assertGreaterEqual(len(files), 1)
        for p in files:
            with self.subTest(file=str(p.relative_to(CAMPUS))):
                text = p.read_text(encoding="utf-8")
                lines = text.rstrip("\n").split("\n")
                self.assertLessEqual(len(lines), 5, "not a delta")
                self.assertIn(".campus-os/run-id-and-interop.md", text)
                self.assertIn("{run_id}/", text, "run dir must be run_id level")
                self.assertIn("HHMMSSfff", text, "canonical mint shape")

    def test_one_canonical_plus_deltas(self):
        canon = [p for p in CAMPUS.glob("library/**/" + NAME) if "campus-ai-os-v5-src" in p.parts]
        self.assertEqual(canon, [CANON])


@unittest.skipUnless((FOUNDRY / "bin/scaffold-team").is_file(), "no Foundry beside this tree")
class Scaffold(unittest.TestCase):
    def test_scaffolded_team_gets_a_delta_and_passes_validate_team(self):
        with tempfile.TemporaryDirectory(prefix="campus-phase35-") as tmp:
            campus = Path(tmp) / "campus"
            (campus / "library/teams").mkdir(parents=True)
            (campus / ".campus-os").mkdir()
            # the scaffolder validates --department against the campus's spec copy
            (campus / ".campus-os/registration-block-spec.md").write_bytes(
                (KERNEL / "templates/registration-block-spec.md").read_bytes())
            p = subprocess.run([sys.executable, str(FOUNDRY / "bin/scaffold-team"), "delta-demo",
                                "--mission", "prove the delta", "--campus", str(campus),
                                "--dest", str(campus / "library/teams")],
                               text=True, capture_output=True, timeout=60)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            delta = campus / "library/teams/delta-demo/references" / NAME
            self.assertTrue(delta.is_file(), "scaffold must write the delta")
            lines = delta.read_text(encoding="utf-8").rstrip("\n").split("\n")
            self.assertLessEqual(len(lines), 5)
            self.assertIn(".campus-os/run-id-and-interop.md", delta.read_text(encoding="utf-8"))
            orch = (campus / "library/teams/delta-demo/skills/delta-demo/SKILL.md").read_text(encoding="utf-8")
            self.assertIn("tools/mint_run_id.py", orch)
            self.assertNotIn("{YYYYMMDD-HHMMSS}}", orch)
            # validate-team I8: a 6-line copy is refused, the delta is not
            v = subprocess.run([sys.executable, str(FOUNDRY / "bin/validate-team"),
                                str(campus / "library/teams/delta-demo"), "--campus", str(campus)],
                               text=True, capture_output=True, timeout=120)
            self.assertNotIn("interop: references/run-id-and-interop.md", v.stdout + v.stderr)
            delta.write_text("\n".join(["# copy"] * 6) + "\n", encoding="utf-8")
            v2 = subprocess.run([sys.executable, str(FOUNDRY / "bin/validate-team"),
                                 str(campus / "library/teams/delta-demo"), "--campus", str(campus)],
                                text=True, capture_output=True, timeout=120)
            self.assertIn("must be a <=5-line delta", v2.stdout + v2.stderr)


if __name__ == "__main__":
    unittest.main()
