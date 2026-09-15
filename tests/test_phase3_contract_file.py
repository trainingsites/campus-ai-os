"""Campus AI OS 5.2.0 Phase 3.7 - contracts/campus.json is generated, current, and in parity with code.

Temp copies only. The resolver parity fixture (Python vs JS) is Codex's, in test_phase3_resolvers.py.
platform: claude-code; seat: m4-claude-code
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KERNEL = Path(os.environ.get("KERNEL_SRC", Path(__file__).resolve().parent.parent)).resolve()
SKIP = {".git", "__pycache__", "node_modules", ".pytest_cache", "tests"}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class Copy(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="campus-phase37-")
        self.addCleanup(self.tmp.cleanup)
        self.src = Path(self.tmp.name) / "kernel"
        shutil.copytree(KERNEL, self.src, ignore=lambda d, n: [x for x in n if x in SKIP])

    def tool(self, *args):
        return subprocess.run([sys.executable, str(self.src / "tools" / "build_contract.py"), *map(str, args)],
                              text=True, capture_output=True, timeout=120)

    def contract(self):
        return json.loads((self.src / "contracts" / "campus.json").read_text(encoding="utf-8"))


class Generated(Copy):
    def test_committed_contract_is_current(self):
        p = self.tool("--check")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("OK: campus contract current", p.stdout)

    def test_rebuild_is_deterministic(self):
        before = self.contract()
        p = self.tool()
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        after = self.contract()
        self.assertEqual(before, after, "rebuild changed the contract (non-deterministic or stale commit)")

    def test_sections_and_sources(self):
        c = self.contract()
        for k in ("hosts", "context_aliases", "registry_enums", "seat", "run_id", "results_envelope",
                  "capability_record", "generated_from"):
            self.assertIn(k, c)
        self.assertEqual({r["canonical"] for r in c["context_aliases"]["files"]},
                         {"identity.md", "icp.md", "brand.md", "voice.md", "goals.md", "offers-summary.md", "connections.md"})
        offers = next(r for r in c["context_aliases"]["files"] if r["canonical"] == "offers-summary.md")
        self.assertEqual((offers["founding_writes"], offers["aliases"][0]), ("offers.md", "offers.md"))   # 5.2.4: summary owns price
        icp = next(r for r in c["context_aliases"]["files"] if r["canonical"] == "icp.md")
        self.assertEqual(icp["founding_writes"], "audience.md")
        self.assertEqual(icp["aliases"][0], "audience.md")
        self.assertEqual(c["registry_enums"]["enums"]["status"], ["active", "legacy", "disabled", "retired"])
        self.assertIn("dean-office", c["registry_enums"]["enums"]["department"])
        self.assertEqual(c["registry_enums"]["legacy_read_aliases"]["department"], {"dean": "dean-office"})
        self.assertTrue(any(k["file"] == "icp.md" and "primary_audience" in k["keys"] for k in c["context_aliases"]["field_keys"]))
        self.assertEqual(c["hosts"]["clients"]["codex"]["entry_file"], "AGENTS.md")
        self.assertIn("CODEX.md", c["hosts"]["entry_file_read_names"])
        self.assertEqual(c["seat"]["ledger"]["satellite"], "dean/.activity.{seat}.jsonl")
        self.assertIn(".campus-os/registry.json", c["seat"]["primary_owned_paths"])
        self.assertEqual(c["run_id"]["run_dir"]["campus"], "outputs/{YYYY-MM}/runs/{team}/{slug}/{run_id}/")
        for src in c["generated_from"].values():
            self.assertTrue((self.src / src["path"]).is_file(), src["path"])

    def test_run_id_patterns_match_the_minter(self):
        c = self.contract()
        m = load("mint", self.src / "tools" / "mint_run_id.py")
        self.assertEqual(c["run_id"]["patterns"]["canonical"], m.CANONICAL.pattern)
        self.assertEqual(c["run_id"]["patterns"]["legacy_date_slug_time"], m.LEGACY_DATE_SLUG_TIME.pattern)

    def test_source_change_makes_check_fail(self):
        spec = self.src / "templates" / "registration-block-spec.md"
        spec.write_text(spec.read_text(encoding="utf-8").replace('"status": "active | legacy', '"status": "active | napping | legacy', 1),
                        encoding="utf-8")
        p = self.tool("--check")
        self.assertEqual(p.returncode, 1, p.stdout)
        self.assertIn("stale", p.stdout)
        p = self.tool()
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("napping", self.contract()["registry_enums"]["enums"]["status"])
        self.assertEqual(self.tool("--check").returncode, 0)

    def test_code_literal_drift_is_a_parity_failure(self):
        pkg = self.src / "tools" / "package.py"
        pkg.write_text(pkg.read_text(encoding="utf-8").replace(
            'MANIFEST_PROBE = (".claude-plugin/plugin.json", ".codex-plugin/plugin.json", "plugin.json")',
            'MANIFEST_PROBE = (".codex-plugin/plugin.json", ".claude-plugin/plugin.json", "plugin.json")', 1),
            encoding="utf-8")
        p = self.tool("--check")
        self.assertEqual(p.returncode, 1)
        self.assertIn("MANIFEST_PROBE", p.stdout)

    def test_tables_are_generated_and_stale_tables_fail(self):
        t = self.src / "contracts" / "campus-contract.md"
        text = t.read_text(encoding="utf-8")
        for h in ("## Hosts", "## Shared-context files", "## Registry enums", "## Seat identity", "## run_id", "## Results envelope"):
            self.assertIn(h, text)
        t.write_text(text + "\nhand edit\n", encoding="utf-8")
        p = self.tool("--check")
        self.assertEqual(p.returncode, 1)
        self.assertIn("campus-contract.md is stale", p.stdout)

    def test_package_refuses_a_stale_contract(self):
        c = self.src / "contracts" / "campus.json"
        d = json.loads(c.read_text(encoding="utf-8"))
        d["registry_enums"]["enums"]["status"].append("napping")
        c.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
        out = Path(self.tmp.name) / "shelf"
        p = subprocess.run([sys.executable, str(self.src / "tools" / "package.py"), "--src", self.src, "--out", out],
                           text=True, capture_output=True, timeout=180)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("campus.json is stale", p.stdout + p.stderr)
        self.assertFalse(out.exists() and any(out.iterdir()))


class Inventory(Copy):
    def test_registry_and_hires_become_valid_capability_records(self):
        campus = Path(self.tmp.name) / "campus"
        (campus / ".campus-os" / "hires").mkdir(parents=True)
        (campus / ".campus-os" / "registry.json").write_text(json.dumps({
            "campus_os_version": "5.1.11",
            "teams": [
                {"team": "dean", "type": "kernel", "status": "active", "version": "5.1.11", "department": "dean", "permission": "draft-only"},
                {"team": "seo-team", "type": "plugin", "status": "active", "version": "1.2.0", "department": "marketing",
                 "permission": "draft-only", "accepts": [{"from": "atlas", "artifact_type": "research-brief"}],
                 "produces": [{"artifact_type": "seo-audit", "done_check": "x"}]},
                {"team": "publisher", "type": "plugin", "status": "active", "version": "1.0.0", "department": "marketing",
                 "permission": "publish-community-feed"},
                {"team": "marketing", "type": "department", "employees": []},
            ],
            "playbooks": [{"playbook": "weekly-reset", "stages": [], "recurring": True, "done_check": "x"}],
        }), encoding="utf-8")
        (campus / ".campus-os" / "hires" / "obsidian-skills.json").write_text(json.dumps({"tool": "obsidian-skills", "version": "0.3.0"}), encoding="utf-8")
        (campus / ".campus-os" / "hires" / "_scanner.json").write_text("{}", encoding="utf-8")
        p = self.tool("--inventory", "--campus-root", campus, "--json")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        d = json.loads(p.stdout)
        self.assertEqual(d["invalid"], 0)
        kinds = {r["id"]: r["kind"] for r in d["results"]}
        self.assertEqual(kinds, {"dean": "kernel-skill", "seo-team": "team", "publisher": "team",
                                 "weekly-reset": "playbook", "obsidian-skills": "hire"})
        self.assertEqual(d["records"], 5)


if __name__ == "__main__":
    unittest.main()
