"""Campus AI OS 5.2.0 Phase 3.2 run-id contract fixtures.

Every write happens inside a temporary directory.
platform: codex; seat: codex
"""
from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


KERNEL = Path(os.environ.get("KERNEL_SRC", Path(__file__).resolve().parent.parent)).resolve()
FOUNDRY = Path(os.environ.get(
    "FOUNDRY_SRC", KERNEL.parents[2] / "library/teams/_foundry"
)).resolve()


def load_module(path):
    spec = importlib.util.spec_from_file_location("phase3_mint_run_id", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RunIdContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="campus-phase3-")
        self.addCleanup(self.tmp.cleanup)
        self.root = (Path(self.tmp.name) / "campus").resolve()
        self.root.mkdir()
        self.module = load_module(KERNEL / "tools/mint_run_id.py")
        self.fixed = dt.datetime(2026, 9, 7, 19, 45, 12, 345000, tzinfo=dt.timezone.utc)

    def test_two_mints_in_one_second_create_distinct_ids_and_dirs(self):
        first = self.module.mint("demo", campus_root=self.root, team="demo-team", now=self.fixed)
        second = self.module.mint(
            "demo", campus_root=self.root, team="demo-team", now=self.fixed,
            random_suffix=lambda: "a1b2",
        )
        self.assertNotEqual(first["run_id"], second["run_id"])
        self.assertTrue(Path(first["run_dir"]).is_dir())
        self.assertTrue(Path(second["run_dir"]).is_dir())
        self.assertEqual(second["run_id"], first["run_id"] + "-a1b2")

    def test_existing_results_refused_exit_one_and_preserved(self):
        run_id = "demo-20260907-194512345"
        target = self.module.run_path(
            self.root, "demo-team", "demo", month="2026-09", run_id=run_id
        )
        target.mkdir(parents=True)
        results = target / "results.json"
        results.write_bytes(b'{"owner":"keep"}\n')
        before = hashlib.sha256(results.read_bytes()).hexdigest()
        with self.assertRaisesRegex(self.module.MintRefused, "existing-results-json"):
            self.module.mint("demo", campus_root=self.root, team="demo-team",
                             now=self.fixed, run_id=run_id)
        self.assertEqual(hashlib.sha256(results.read_bytes()).hexdigest(), before)

    def test_explicit_run_id_cannot_escape_run_tree(self):
        outside = self.root.parent / "pwned-20260907-194512345"
        for bad in ("../../../../pwned-20260907-194512345",
                    "a/b-20260907-194512345", " lead-20260907-194512345"):
            with self.subTest(run_id=bad):
                with self.assertRaisesRegex(ValueError, "invalid run_id"):
                    self.module.mint("demo", campus_root=self.root, team="demo-team",
                                     now=self.fixed, run_id=bad)
        self.assertFalse(outside.exists())

    def test_mint_cli_has_no_explicit_run_id_surface(self):
        help_run = subprocess.run(
            [sys.executable, str(KERNEL / "tools/mint_run_id.py"), "mint", "--help"],
            text=True, capture_output=True,
        )
        self.assertEqual(help_run.returncode, 0)
        self.assertNotIn("run-id", help_run.stdout)
        refused = subprocess.run(
            [sys.executable, str(KERNEL / "tools/mint_run_id.py"), "mint", "demo",
             "--run-id", "demo-20260907-194512345"], text=True, capture_output=True,
        )
        self.assertEqual(refused.returncode, 2)

    def test_mkdir_race_is_named_refusal(self):
        with mock.patch.object(Path, "mkdir", side_effect=FileExistsError):
            with self.assertRaisesRegex(self.module.MintRefused, "existing-run-dir"):
                self.module.mint("demo", campus_root=self.root, now=self.fixed)

    def test_parse_round_trips_canonical(self):
        made = self.module.mint("demo", campus_root=self.root, now=self.fixed, create=False)
        parsed = self.module.parse(made["run_id"])
        self.assertEqual(parsed["slug"], "demo")
        self.assertTrue(parsed["canonical"])
        self.assertFalse(parsed["legacy"])
        self.assertEqual(parsed["stamp_utc"], "2026-09-07T19:45:12.345Z")

    def test_parse_accepts_all_live_legacy_shapes(self):
        samples = (
            "campus-ambassador-20260901-113914",
            "email-desk-20260902-113811",
            "crm1to1activity-20260907T060741Z",
            "2026-09-06T1209Z",
            "20260906T040745Z",
            "20260905-crm-1to1-activity-0106",
        )
        for sample in samples:
            with self.subTest(sample=sample):
                parsed = self.module.parse(sample)
                self.assertTrue(parsed["legacy"])
                self.assertFalse(parsed["canonical"])
                self.assertIsNotNone(parsed["stamp_utc"])

    def test_unknown_parse_shape_is_permissive(self):
        parsed = self.module.parse("owner-made-run")
        self.assertEqual(parsed, {"slug": "owner-made-run", "stamp_utc": None,
                                  "legacy": True, "canonical": False})

    def test_run_path_campus_team_and_playbook(self):
        team = self.module.run_path(self.root, "alpha-team", "launch", month="2026-09")
        playbook = self.module.run_path(
            self.root, "ignored-team", "weekly-reset", kind="playbook", month="2026-09"
        )
        self.assertEqual(team, self.root / "outputs/2026-09/runs/alpha-team/launch")
        self.assertEqual(playbook, self.root / "outputs/2026-09/runs/playbooks/weekly-reset")

    def test_run_path_standalone_team_and_playbook(self):
        team = self.module.run_path(self.root, "alpha-team", "launch", standalone=True)
        playbook = self.module.run_path(
            self.root, "ignored-team", "weekly-reset", kind="playbook", standalone=True
        )
        self.assertEqual(team, self.root / "teams-shared/runs/alpha-team/launch")
        self.assertEqual(playbook, self.root / "teams-shared/runs/playbooks/weekly-reset")

    def test_path_cli_can_return_validated_run_directory(self):
        run_id = "demo-20260907-194512345"
        cli = subprocess.run(
            [sys.executable, str(KERNEL / "tools/mint_run_id.py"), "path",
             "--team", "demo-team", "--slug", "demo", "--month", "2026-09",
             "--campus-root", str(self.root), "--run-id", run_id],
            text=True, capture_output=True,
        )
        self.assertEqual(cli.returncode, 0, cli.stderr)
        self.assertEqual(Path(cli.stdout.strip()), self.module.run_path(
            self.root, "demo-team", "demo", month="2026-09", run_id=run_id
        ))
        bad = subprocess.run(
            [sys.executable, str(KERNEL / "tools/mint_run_id.py"), "path",
             "--team", "demo-team", "--slug", "demo", "--run-id", "../x"],
            text=True, capture_output=True,
        )
        self.assertEqual(bad.returncode, 2)

    def test_foundry_wrapper_uses_kernel_and_preserves_output_shape(self):
        if not FOUNDRY.is_dir():
            self.skipTest("FOUNDRY_SRC not set and no campus Foundry beside this tree")
        foundry = Path(self.tmp.name) / "foundry"
        shutil.copytree(FOUNDRY, foundry)
        wrapper = foundry / "bin/mint-run-id"
        env = dict(os.environ, CAMPUS_ROOT=str(self.root))
        kernel_dest = self.root / "library/plugins/campus-ai-os-v5-src/tools"
        kernel_dest.mkdir(parents=True)
        shutil.copy2(KERNEL / "tools/mint_run_id.py", kernel_dest / "mint_run_id.py")
        cli = subprocess.run(
            [sys.executable, str(wrapper), "demo", "--team", "demo-team",
             "--campus", str(self.root), "--json"],
            env=env, text=True, capture_output=True,
        )
        self.assertEqual(cli.returncode, 0, cli.stdout + cli.stderr)
        result = json.loads(cli.stdout)
        self.assertRegex(result["run_id"], r"^demo-\d{8}-\d{9}(?:-[0-9a-f]{4})?$")
        self.assertEqual(Path(result["run_dir"]).name, result["run_id"])
        self.assertTrue((Path(result["run_dir"]) / "results.json").is_file())
        self.assertNotIn("compatibility fallback", cli.stderr)

    def test_foundry_wrapper_never_loads_a_decoy_plugin(self):
        if not FOUNDRY.is_dir():
            self.skipTest("FOUNDRY_SRC not set and no campus Foundry beside this tree")
        foundry = Path(self.tmp.name) / "foundry-decoy"
        shutil.copytree(FOUNDRY, foundry)
        decoy = self.root / "library/plugins/aaa-decoy/tools"
        decoy.mkdir(parents=True)
        (decoy / "mint_run_id.py").write_text(
            'def mint(*a, **k): return {"run_id":"DECOY","run_dir":None}\n',
            encoding="utf-8",
        )
        cli = subprocess.run(
            [sys.executable, str(foundry / "bin/mint-run-id"), "demo", "--json"],
            env=dict(os.environ, CAMPUS_ROOT=str(self.root)), text=True, capture_output=True,
        )
        self.assertEqual(cli.returncode, 0, cli.stdout + cli.stderr)
        self.assertNotEqual(json.loads(cli.stdout)["run_id"], "DECOY")
        self.assertIn("compatibility fallback", cli.stderr)


if __name__ == "__main__":
    unittest.main()
