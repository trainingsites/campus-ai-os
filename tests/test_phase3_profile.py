"""Campus AI OS 5.2.0 Phase 3.8 - distribution profile: commercial gates leave validate-team.

Plan proof: validate-team on a fixture WITHOUT membership copy passes; package-team --profile
trainingsites fails it. Foundry-present only (skips cleanly on a bare kernel).
platform: claude-code; seat: m4-claude-code
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KERNEL = Path(os.environ.get("KERNEL_SRC", Path(__file__).resolve().parent.parent)).resolve()
CAMPUS = Path(os.environ.get("CAMPUS_ROOT", KERNEL.parents[2])).resolve()
FOUNDRY = Path(os.environ.get("FOUNDRY_SRC", CAMPUS / "library/teams/_foundry")).resolve()


@unittest.skipUnless((FOUNDRY / "bin/package-team").is_file() and (FOUNDRY / "profiles").is_dir(),
                     "no Foundry with profiles/ beside this tree")
class Profile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="campus-phase38-")
        self.addCleanup(self.tmp.cleanup)
        self.campus = Path(self.tmp.name) / "campus"
        (self.campus / "library/teams").mkdir(parents=True)
        (self.campus / ".campus-os").mkdir()
        (self.campus / ".campus-os/registration-block-spec.md").write_bytes(
            (KERNEL / "templates/registration-block-spec.md").read_bytes())
        (self.campus / ".campus-os/registry.json").write_text(json.dumps({"teams": [], "playbooks": []}), encoding="utf-8")
        shutil.copytree(FOUNDRY, self.campus / "library/teams/_foundry")
        self.foundry = self.campus / "library/teams/_foundry"
        # a conformant team WITHOUT any membership / $197 / community copy
        self.team = self.campus / "library/teams/good-team"
        shutil.copytree(FOUNDRY / "tests/fixtures/good-team", self.team)
        readme = self.team / "README.md"
        text = readme.read_text(encoding="utf-8")
        stripped = "\n".join(l for l in text.splitlines()
                             if not any(w in l.lower() for w in ("member", "$197", "communit")))
        readme.write_text(stripped + "\n", encoding="utf-8")
        self.assertNotIn("member", readme.read_text(encoding="utf-8").lower())
        # the owner's brand-leak scanner: a stand-in that passes (the real one is campus tooling)
        scan = self.campus / "tools/brand-leak-scan/scan.py"
        scan.parent.mkdir(parents=True)
        scan.write_text("import sys\nprint('scan: clean')\nsys.exit(0)\n", encoding="utf-8")

    def tool(self, name, *args, env=None):
        e = dict(os.environ)
        e.pop("CAMPUS_DISTRIBUTION_PROFILE", None)
        e.update(env or {})
        return subprocess.run([sys.executable, str(self.foundry / "bin" / name), *map(str, args)],
                              text=True, capture_output=True, timeout=180, cwd=self.campus, env=e)

    def test_validate_team_passes_without_membership_copy(self):
        p = self.tool("validate-team", self.team, "--campus", self.campus)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertNotIn("membership bridge", p.stdout + p.stderr)

    def test_validate_team_with_profile_fails_on_membership_bridge(self):
        p = self.tool("validate-team", self.team, "--campus", self.campus, "--profile", "trainingsites")
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn("profile trainingsites: README.md: membership bridge missing", p.stdout + p.stderr)

    def test_package_team_with_trainingsites_profile_refuses(self):
        out = self.campus / "shelf"
        p = self.tool("package-team", self.team, "--campus", self.campus, "--out", out, "--profile", "trainingsites", "--json")
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        d = json.loads(p.stdout)
        self.assertFalse(d["packaged"])
        self.assertEqual(d["reason"], "validate-team failed")
        self.assertFalse(out.exists() and any(out.iterdir()), "artifact written despite refusal")

    def test_package_team_default_profile_is_the_one_marked_default(self):
        # the Foundry ships trainingsites as default -> same refusal without --profile
        p = self.tool("package-team", self.team, "--campus", self.campus, "--out", self.campus / "shelf", "--json")
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertEqual(json.loads(p.stdout)["reason"], "validate-team failed")

    def test_no_profile_packages_and_records_skipped_scan(self):
        for f in (self.foundry / "profiles").glob("*.json"):
            f.unlink()
        out = self.campus / "shelf"
        p = self.tool("package-team", self.team, "--campus", self.campus, "--out", out, "--json")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        d = json.loads(p.stdout)
        self.assertTrue(d["packaged"])
        self.assertIsNone(d["distribution_profile"])
        self.assertEqual(d["gates"]["brand-leak-scan"], "skipped")
        self.assertTrue(any(out.glob("good-team-v*.plugin")))

    def test_membership_copy_present_passes_the_profile(self):
        (self.team / "README.md").write_text(
            (self.team / "README.md").read_text(encoding="utf-8")
            + "\n- **Membership ($197/mo)** - live implementation inside the free community.\n", encoding="utf-8")
        p = self.tool("validate-team", self.team, "--campus", self.campus, "--profile", "trainingsites")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        out = self.campus / "shelf"
        p = self.tool("package-team", self.team, "--campus", self.campus, "--out", out, "--profile", "trainingsites", "--json")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        d = json.loads(p.stdout)
        self.assertEqual(d["distribution_profile"], "trainingsites")
        self.assertTrue(d["gates"]["brand-leak-scan"])

    def test_unknown_profile_is_refused_not_ignored(self):
        p = self.tool("package-team", self.team, "--campus", self.campus, "--out", self.campus / "shelf", "--profile", "nope", "--json")
        self.assertEqual(p.returncode, 2)
        self.assertEqual(json.loads(p.stdout)["reason"], "distribution profile unresolved")
        v = self.tool("validate-team", self.team, "--campus", self.campus, "--profile", "nope")
        self.assertEqual(v.returncode, 1)

    def test_profile_required_scan_missing_refuses(self):
        (self.team / "README.md").write_text(
            (self.team / "README.md").read_text(encoding="utf-8") + "\nMembership $197 and community.\n", encoding="utf-8")
        (self.campus / "tools/brand-leak-scan/scan.py").unlink()
        p = self.tool("package-team", self.team, "--campus", self.campus, "--out", self.campus / "shelf", "--profile", "trainingsites", "--json")
        self.assertEqual(p.returncode, 2)
        self.assertEqual(json.loads(p.stdout)["reason"], "brand-leak-scan missing")

    def test_env_profile_selection(self):
        p = self.tool("validate-team", self.team, "--campus", self.campus, env={"CAMPUS_DISTRIBUTION_PROFILE": "trainingsites"})
        # validate-team only honours an explicit --profile; the env var is package-team's resolution input
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for f in (self.foundry / "profiles").glob("*.json"):
            if "trainingsites" not in f.name:
                f.unlink()
        p = self.tool("package-team", self.team, "--campus", self.campus, "--out", self.campus / "shelf", "--json",
                      env={"CAMPUS_DISTRIBUTION_PROFILE": "trainingsites"})
        self.assertEqual(p.returncode, 2)
        self.assertEqual(json.loads(p.stdout)["reason"], "validate-team failed")


if __name__ == "__main__":
    unittest.main()
