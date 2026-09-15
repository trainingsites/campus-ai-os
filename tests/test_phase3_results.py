"""Campus AI OS 5.2.0 Phase 3.1 - results.json envelope v1.1 fixtures.

Isolated: temp dirs only. Optional Foundry parity check skips when no Foundry sits beside
this tree (bare kernel copy).
platform: claude-code; seat: m4-claude-code
"""
import datetime as dt
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KERNEL = Path(os.environ.get("KERNEL_SRC", Path(__file__).resolve().parent.parent)).resolve()
FOUNDRY = Path(os.environ.get("FOUNDRY_SRC", KERNEL.parents[2] / "library/teams/_foundry")).resolve()
SCHEMA = KERNEL / "schemas" / "results.schema.json"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def good_doc(**over):
    d = {
        "schema_version": "1.1",
        "profile": "completion-only",
        "run_id": "demo-20260907-194512345",
        "team": "demo-team",
        "slug": "demo",
        "generated_at": "2026-09-07T19:45:12Z",
        "external_ref": None,
        "permission": "draft-only",
        "assets": [
            {"type": "email", "path": "01-email.md", "status": "draft", "tier": "local",
             "url": None, "external_ref": None, "completion": {"done_check": "voice-check>=85"}}
        ],
        "completion": {"execution_success": True, "artifact_passed": True, "owner_approved": False},
        "bindings": [
            {"stage": "draft", "employee": "copy-team", "employee_type": "team", "version": "1.2.0",
             "reason": "only installed team that produces email", "alternatives": ["email-desk"], "outcome": None}
        ],
    }
    d.update(over)
    return d


class Envelope(unittest.TestCase):
    def setUp(self):
        self.v = load_module("validate_results", KERNEL / "tools" / "validate_results.py")
        self.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.tmp = tempfile.TemporaryDirectory(prefix="campus-phase31-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write(self, name, obj):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(obj if isinstance(obj, str) else json.dumps(obj), encoding="utf-8")
        return p

    def cli(self, *args):
        return subprocess.run([sys.executable, str(KERNEL / "tools" / "validate_results.py"), *map(str, args)],
                              text=True, capture_output=True, timeout=60)

    # --- write side -----------------------------------------------------
    def test_schema_is_draft07_and_requires_the_spine(self):
        self.assertEqual(self.schema["$schema"], "http://json-schema.org/draft-07/schema#")
        self.assertEqual(sorted(self.schema["required"]),
                         sorted(["schema_version", "run_id", "team", "generated_at", "assets", "completion"]))
        self.assertEqual(self.schema["properties"]["schema_version"]["enum"], ["1.1"])

    def test_new_combined_document_validates(self):
        self.assertEqual(self.v.validate(good_doc(), self.schema), [])
        self.assertEqual(self.v.classify(good_doc(), self.schema)[0], "v1.1-valid")

    def test_empty_assets_is_valid(self):
        self.assertEqual(self.v.validate(good_doc(assets=[]), self.schema), [])

    def test_missing_completion_is_invalid_on_write(self):
        d = good_doc(); d.pop("completion")
        cat, errs, _ = self.v.classify(d, self.schema)
        self.assertEqual(cat, "v1.1-invalid")
        self.assertTrue(any("completion" in e for e in errs))

    def test_bad_enum_and_pattern_are_named(self):
        d = good_doc(run_id="made up", assets=[{"type": "x", "status": "shipped"}])
        d["completion"]["owner_approved"] = "yes"
        errs = self.v.validate(d, self.schema)
        joined = "\n".join(errs)
        self.assertIn("$.run_id", joined)
        self.assertIn("$.assets[0].status", joined)
        self.assertIn("$.completion.owner_approved", joined)

    def test_both_run_id_forms_validate(self):
        for rid in ("demo-20260907-194512345", "demo-20260907-194512345-a1b2", "email-desk-20260902-113811"):
            with self.subTest(rid=rid):
                self.assertEqual(self.v.validate(good_doc(run_id=rid), self.schema), [])

    def test_binding_requires_stage_employee_type(self):
        d = good_doc(bindings=[{"stage": "draft", "employee": "x", "employee_type": "robot"}])
        self.assertTrue(any("employee_type" in e for e in self.v.validate(d, self.schema)))
        d = good_doc(bindings=[{"employee": "x"}])
        self.assertTrue(any("stage" in e for e in self.v.validate(d, self.schema)))

    def test_mint_stub_is_a_valid_v1_1_document(self):
        m = load_module("mint_run_id", KERNEL / "tools" / "mint_run_id.py")
        r = m.mint("demo", campus_root=self.root, team="demo-team",
                   now=dt.datetime(2026, 9, 7, 19, 45, 12, 345000, tzinfo=dt.timezone.utc))
        doc = json.loads((Path(r["run_dir"]) / "results.json").read_text(encoding="utf-8"))
        self.assertEqual(doc["schema_version"], "1.1")
        self.assertEqual(doc["assets"], [])
        self.assertEqual(self.v.validate(doc, self.schema), [], doc)

    # --- read side ------------------------------------------------------
    def test_legacy_asset_only_1_0_is_read_not_failed(self):
        d = {"schema_version": "1.0", "run_id": "seo-team-20260801-101010", "team": "seo-team",
             "assets": [{"type": "post", "status": "published"}]}
        self.assertEqual(self.v.classify(d, self.schema)[0], "legacy-1.0")

    def test_legacy_run_only_foundry_stub_is_read_not_failed(self):
        d = {"schema_version": "1.1-completion-only", "run_id": "seo-team-20260801-101010", "team": "seo-team",
             "completion": {"execution_success": False, "artifact_passed": False, "owner_approved": False}}
        cat, _, notes = self.v.classify(d, self.schema)
        self.assertEqual(cat, "legacy-1.0")
        self.assertTrue(any("1.1-completion-only" in n for n in notes))

    def test_missing_version_ledger_and_foreign_are_classified(self):
        self.assertEqual(self.v.classify({"run_id": "x-20260101-000000", "notes_written": 3}, self.schema)[0], "ledger")
        self.assertEqual(self.v.classify({"ts": "2026-01-01", "gmail": True}, self.schema)[0], "foreign")
        self.assertEqual(self.v.classify({"schema_version": "9.9", "run_id": "x", "assets": []}, self.schema)[0], "legacy-1.0")

    def test_malformed_and_non_object_are_failures(self):
        self.assertEqual(self.v.classify(["not", "an", "object"], self.schema)[0], "malformed")
        p1 = self.write("a/results.json", "{not json")
        p2 = self.write("b/results.json", good_doc())
        r = self.cli("--schema", SCHEMA, p1, p2, "--json")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual(out["counts"], {"malformed": 1, "v1.1-valid": 1})

    def test_cli_campus_root_reports_counts_and_exit(self):
        self.write("outputs/2026-09/runs/t/a/results.json", good_doc())
        self.write("outputs/2026-09/runs/t/b/results.json",
                   {"schema_version": "1.0", "run_id": "t-20260901-000000", "team": "t", "assets": []})
        self.write("teams-shared/runs/t/c/results.json", {"ts": 1})
        r = self.cli("--schema", SCHEMA, "--campus-root", self.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("OK: 3 results.json", r.stdout)
        strict = self.cli("--schema", SCHEMA, "--campus-root", self.root, "--strict")
        self.assertEqual(strict.returncode, 1)

    def test_missing_schema_is_exit_2(self):
        r = self.cli("--schema", self.root / "nope.json", self.write("x/results.json", good_doc()))
        self.assertEqual(r.returncode, 2)

    # --- one file, two homes -------------------------------------------
    def test_foundry_copy_is_byte_identical(self):
        copy = FOUNDRY / "schemas" / "results.schema.json"
        if not copy.is_file():
            self.skipTest("FOUNDRY_SRC not set and no campus Foundry beside this tree")
        self.assertEqual(copy.read_bytes(), SCHEMA.read_bytes(),
                         "Foundry schemas/results.schema.json drifted from the kernel canonical copy")

    def test_readers_point_at_the_one_file(self):
        for rel in ("skills/results-aggregator/SKILL.md",
                    "skills/outcome-reporter/references/rollup-schema.md"):
            with self.subTest(rel=rel):
                self.assertIn("schemas/results.schema.json", (KERNEL / rel).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
