"""Campus AI OS kernel fixtures - 5.2.0 Phase 2 (one source of truth).

Isolated: every mutation happens on a copy of the kernel tree under a temp dir.
Nothing here reads a live campus.

  2.3  version-lockstep gate  - package.py refuses a tree whose version homes disagree
  2.4  registry enum gate     - validate_registry.py refuses an entry without type/status
                                or with a value outside the spec's enum

Run: tests/run-tests.sh   (or: python3 -m unittest discover -s tests)
platform: claude-code; seat: m4-claude-code
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KERNEL = Path(os.environ.get("KERNEL_SRC", Path(__file__).resolve().parent.parent)).resolve()
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".pytest_cache", "tests"}


def copy_tree(dst: Path):
    shutil.copytree(KERNEL, dst, ignore=lambda d, names: [n for n in names if n in SKIP_DIRS])
    return dst


class KernelCopy(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="campus-phase2-")
        self.addCleanup(self.tmp.cleanup)
        self.src = copy_tree(Path(self.tmp.name) / "kernel")

    def tool(self, name, *args, stdin=None):
        return subprocess.run(
            [sys.executable, str(self.src / "tools" / name), *map(str, args)],
            input=stdin, text=True, capture_output=True, cwd=self.src, timeout=60,
        )


class Lockstep(KernelCopy):
    """2.3 - package.py --check-lockstep."""

    def test_conformant_tree_agrees(self):
        p = self.tool("package.py", "--src", self.src, "--check-lockstep")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("OK: version lockstep", p.stdout)
        # every home the plan names is actually read (a gate that reads one
        # home is not a lockstep gate)
        for home in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json",
                     "packs/education/pack.json", "templates/registry.json:campus_os_version",
                     "skills/campus-doctor/SKILL.md"):
            self.assertIn(home, p.stdout, f"home not read: {home}")

    def _bump(self, rel, mutate):
        p = self.src / rel
        p.write_text(mutate(p.read_text(encoding="utf-8")), encoding="utf-8")

    def test_pack_json_drift_refused(self):
        self._bump("packs/education/pack.json",
                   lambda t: t.replace('"version": "', '"version": "9.', 1))
        p = self.tool("package.py", "--src", self.src, "--check-lockstep")
        self.assertEqual(p.returncode, 1, p.stdout)
        self.assertIn("FAIL: version lockstep", p.stdout)
        self.assertIn("!! packs/education/pack.json", p.stdout)

    def test_codex_manifest_drift_refused(self):
        self._bump(".codex-plugin/plugin.json",
                   lambda t: re.sub(r'"version":\s*"[^"]+"', '"version": "0.0.1"', t, count=1))
        p = self.tool("package.py", "--src", self.src, "--check-lockstep")
        self.assertEqual(p.returncode, 1, p.stdout)

    def test_registry_template_drift_refused(self):
        self._bump("templates/registry.json",
                   lambda t: t.replace('"campus_os_version": "', '"campus_os_version": "0.', 1))
        p = self.tool("package.py", "--src", self.src, "--check-lockstep")
        self.assertEqual(p.returncode, 1, p.stdout)
        self.assertIn("!! templates/registry.json:campus_os_version", p.stdout)

    def test_skill_frontmatter_drift_refused(self):
        self._bump("skills/campus-doctor/SKILL.md",
                   lambda t: re.sub(r"^version:\s*[0-9.]+", "version: 0.0.1", t, count=1, flags=re.M))
        p = self.tool("package.py", "--src", self.src, "--check-lockstep")
        self.assertEqual(p.returncode, 1, p.stdout)

    def test_build_refuses_before_packaging(self):
        """A full build on a drifted tree exits non-zero and writes no artifact."""
        self._bump("packs/education/pack.json",
                   lambda t: t.replace('"version": "', '"version": "9.', 1))
        out = Path(self.tmp.name) / "shelf"
        p = self.tool("package.py", "--src", self.src, "--out", out)
        self.assertNotEqual(p.returncode, 0)
        self.assertFalse(out.exists() and any(out.iterdir()), "artifact written despite refusal")


class RegistryEnums(KernelCopy):
    """2.4 - validate_registry.py against the kernel's own template + mutations."""

    def registry(self):
        return json.loads((self.src / "templates" / "registry.json").read_text(encoding="utf-8"))

    def write_registry(self, data):
        p = self.src / "templates" / "registry.json"
        p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return p

    def validate(self, *extra):
        return self.tool("validate_registry.py", "--registry", self.src / "templates" / "registry.json",
                         "--spec", self.src / "templates" / "registration-block-spec.md", *extra)

    def test_template_registry_validates(self):
        p = self.validate()
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("OK:", p.stdout)

    def test_enums_come_from_the_spec(self):
        p = self.validate("--json")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        d = json.loads(p.stdout)
        self.assertEqual(d["enums"]["type"], ["plugin", "authored-skill", "kernel", "department", "systems"])
        self.assertEqual(d["enums"]["status"], ["active", "legacy", "disabled", "retired"])
        self.assertIn("marketing", d["enums"]["department"])

    def test_missing_type_refused(self):
        r = self.registry()
        r["teams"][0].pop("type")
        self.write_registry(r)
        p = self.validate("--json")
        self.assertEqual(p.returncode, 1)
        d = json.loads(p.stdout)
        self.assertTrue(any(f["field"] == "type" and f["problem"] == "missing" for f in d["failures"]))

    def test_missing_status_refused(self):
        r = self.registry()
        r["teams"][0].pop("status")
        self.write_registry(r)
        p = self.validate("--json")
        self.assertEqual(p.returncode, 1)
        d = json.loads(p.stdout)
        self.assertTrue(any(f["field"] == "status" and f["problem"] == "missing" for f in d["failures"]))

    def test_unknown_enum_value_refused(self):
        r = self.registry()
        r["teams"][0]["status"] = "sleeping"
        r["teams"][1]["type"] = "widget"
        self.write_registry(r)
        p = self.validate("--json")
        self.assertEqual(p.returncode, 1)
        d = json.loads(p.stdout)
        problems = {(f["field"], f["value"]) for f in d["failures"]}
        self.assertIn(("status", "sleeping"), problems)
        self.assertIn(("type", "widget"), problems)

    def test_legacy_alias_dean_is_read_permissively(self):
        """`department: dean` is the pre-5.1.x alias of dean-office; reading stays permissive."""
        r = self.registry()
        r["teams"][0]["department"] = "dean"
        self.write_registry(r)
        p = self.validate()
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_missing_spec_is_loud(self):
        p = self.tool("validate_registry.py", "--registry", self.src / "templates" / "registry.json",
                      "--spec", self.src / "templates" / "does-not-exist.md")
        self.assertNotEqual(p.returncode, 0)


if __name__ == "__main__":
    unittest.main()
