"""Campus AI OS 5.3.0 item 4 - the agent-activity-logging standard, kernel half.

One ledger line shape for registered and ad-hoc runs (schemas/ledger-line.schema.json),
cost keys reserved as optional for 5.3.1, read-permissive so every existing line still
validates, and the generalized runtime-vs-canonical drift check inside campus-doctor
(reported, never fixed). Kernel-only; runs everywhere.
platform: claude-code; seat: m4-claude-code
"""
import datetime as dt
import hashlib
import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KERNEL = Path(os.environ.get("KERNEL_SRC", Path(__file__).resolve().parent.parent)).resolve()
TOOLS = KERNEL / "tools"
SCHEMA = KERNEL / "schemas" / "ledger-line.schema.json"
RESERVED = {"provider": "string", "model": "string", "tokens_in": "integer", "tokens_out": "integer", "cost": "number"}

OLD_LINE = {"ts": "2026-07-01T10:00:00Z", "session": "S200", "skill": "ad-hoc", "trigger": "fix x",
            "dept": "dean", "outcome": "completed", "files_touched": 2}          # pre-seat-stamp shape
LEGACY_ODD = {"timestamp": "2026-06-01", "skill": "agent-log", "note": {"free": "form"},
              "external_ref": None, "files_touched": ["a.md"]}                    # real-world legacy variety
STAMPED = dict(OLD_LINE, seat="m4-mini", via="host-binding", run_id="demo-20260920-120000000",
               tier_requested="light", tier_used="full")                          # 5.2.x shape
NEW_LINE = dict(STAMPED, skill="content-repurposer", provider="openrouter", model="some/model",
                tokens_in=1200, tokens_out=300, cost=0.0042)
ADHOC = {"ts": "2026-09-23T01:00:00Z", "seat": "m4-mini", "skill": "ad-hoc", "trigger": "draft plan",
         "dept": "dean", "outcome": "completed", "logged_for": "decision"}


def sys_path_tools():
    if str(TOOLS) not in sys.path:
        sys.path.insert(0, str(TOOLS))


class LineShape(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys_path_tools()
        cls.vl = importlib.import_module("validate_ledger")
        cls.schema = cls.vl.load_schema(SCHEMA)

    def cat(self, rec, write=False):
        return self.vl.classify(rec, self.schema, write)[0]

    def test_schema_reserves_cost_keys_as_optional(self):
        props, req = self.schema["properties"], set(self.schema["required"])
        for key, jtype in RESERVED.items():
            self.assertIn(key, props, key)
            self.assertEqual(props[key]["type"], jtype, key)
            self.assertNotIn(key, req, f"{key} must stay optional until 5.3.1")
        self.assertIn("tier_used", props)
        self.assertEqual(req, {"ts", "seat", "skill", "dept", "outcome"})
        self.assertNotIn("team", props, "NICHE-009: the field is `dept`")

    def test_old_lines_still_valid_on_read(self):
        self.assertEqual(self.cat(OLD_LINE), "legacy")
        self.assertEqual(self.cat(LEGACY_ODD), "legacy")
        self.assertEqual(self.cat(STAMPED), "valid")

    def test_new_line_valid_with_and_without_cost_keys(self):
        self.assertEqual(self.cat(NEW_LINE, write=True), "valid")
        self.assertEqual(self.cat(STAMPED, write=True), "valid")
        self.assertEqual(self.cat(ADHOC, write=True), "valid")

    def test_write_side_requires_the_stamp(self):
        self.assertEqual(self.cat(OLD_LINE, write=True), "invalid")   # no seat

    def test_bad_types_rejected_on_both_sides(self):
        for key, bad in [("tokens_in", "12"), ("tokens_out", 1.5), ("cost", "0.01"), ("cost", -1),
                         ("tokens_in", -3), ("provider", 5), ("model", None), ("tokens_in", True),
                         ("seat", "../x"), ("ts", "yesterday"), ("via", 5)]:
            for write in (False, True):
                self.assertEqual(self.cat(dict(NEW_LINE, **{key: bad}), write), "invalid", (key, bad, write))
        # 5.3.0 review: a word outside a list is legacy on read (ledgers are append-only, so a red line
        # on history could never be fixed) and still refused on write.
        for key, word in [("via", "binding-file-read"), ("via", "guess"), ("logged_for", "chat")]:
            self.assertEqual(self.cat(dict(NEW_LINE, **{key: word}), False), "legacy", (key, word))
            self.assertEqual(self.cat(dict(NEW_LINE, **{key: word}), True), "invalid", (key, word))
        self.assertEqual(self.cat(dict(NEW_LINE, via="unresolved"), True), "valid")
        self.assertEqual(self.cat(["not", "an", "object"]), "malformed")

    def test_cli_line_and_campus_modes(self):
        run = lambda *a: subprocess.run([sys.executable, str(TOOLS / "validate_ledger.py"), *a],
                                        capture_output=True, text=True, timeout=30)
        self.assertEqual(run("--line", json.dumps(NEW_LINE), "--write").returncode, 0)
        self.assertEqual(run("--line", json.dumps(OLD_LINE)).returncode, 0)
        self.assertEqual(run("--line", json.dumps(OLD_LINE), "--write").returncode, 1)
        self.assertEqual(run("--line", json.dumps(dict(NEW_LINE, cost="free"))).returncode, 1)
        self.assertEqual(run("--line", "{not json").returncode, 1)
        with tempfile.TemporaryDirectory(prefix="ledger-shape-") as tmp:
            root = Path(tmp)
            (root / "dean").mkdir()
            (root / "dean/.activity.jsonl").write_text("# header\n\n" + "\n".join(
                json.dumps(x) for x in (OLD_LINE, LEGACY_ODD, STAMPED)) + "\n")
            (root / "dean/.activity.m4-mini.jsonl").write_text(json.dumps(NEW_LINE) + "\n" + json.dumps(ADHOC) + "\n")
            p = run("--campus-root", str(root), "--json")
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertEqual(json.loads(p.stdout)["counts"], {"legacy": 2, "valid": 3})
            with (root / "dean/.activity.m4-mini.jsonl").open("a") as fh:
                fh.write(json.dumps(dict(NEW_LINE, tokens_in="many")) + "\n")
            p = run("--campus-root", str(root), "--json")
            self.assertEqual(p.returncode, 1)
            self.assertEqual(json.loads(p.stdout)["rows"][0]["line"], 3)

    def test_ledger_canon_states_the_standard_on_single_lines(self):
        canon = (KERNEL / "templates" / "ledger-paths.md").read_text(encoding="utf-8")
        self.assertIn("## The line shape", canon)
        lines = canon.splitlines()
        rule = next((l for l in lines if l.startswith("An ad-hoc turn")), "")
        for needle in ('"skill":"ad-hoc"', "output, a write or a decision", "pure conversation does not log"):
            self.assertIn(needle, rule)
        reserved = next((l for l in lines if l.startswith("Reserved optional keys")), "")
        for key in RESERVED:
            self.assertIn(f"`{key}`", reserved)
        self.assertIn("`tier_used`", reserved)
        for brain in ("templates/dean-CLAUDE.md", "templates/dean-CODEX.md"):
            t = (KERNEL / brain).read_text(encoding="utf-8")
            self.assertIn("per ad-hoc turn that produced an output, a write or a decision", t, brain)
            ex = next(l for l in t.splitlines() if '"skill":' in l and '"outcome":' in l)
            self.assertIn('"seat":"{seat}"', ex, brain)
            self.assertIn('"dept":', ex, brain)
            self.assertNotIn('"team":', ex, brain)


class DoctorIntegration(unittest.TestCase):
    def setUp(self):
        sys_path_tools()
        tmp = tempfile.TemporaryDirectory(prefix="logging-doctor-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "campus"
        (self.root / "dean").mkdir(parents=True)
        self.de = importlib.import_module("doctor_evidence")

    def evidence(self, runtime_dirs=()):
        return self.de.Evidence(self.root, dt.date(2026, 9, 23), runtime_dirs=runtime_dirs)

    def test_doctor_accepts_lines_with_and_without_cost_keys(self):
        (self.root / "dean/.activity.jsonl").write_text(
            "\n".join(json.dumps(x) for x in (STAMPED, NEW_LINE, ADHOC)) + "\n")
        sec = self.evidence().ledger()
        self.assertEqual(sec["status"], "ok", sec)
        self.assertEqual(sec["detail"]["shape_errors"], [])
        (self.root / "dean/.activity.jsonl").write_text(json.dumps(OLD_LINE) + "\n")
        sec = self.evidence().ledger()
        self.assertEqual(sec["status"], "opportunity")      # unstamped legacy: [--], never red
        self.assertEqual(sec["detail"]["legacy_lines"], 1)

    def test_doctor_reports_mistyped_lines_without_rewriting(self):
        path = self.root / "dean/.activity.jsonl"
        path.write_text(json.dumps(STAMPED) + "\n" + json.dumps(dict(NEW_LINE, cost="lots")) + "\n")
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        sec = self.evidence().ledger()
        self.assertEqual(sec["status"], "needs-decision")
        self.assertIn("1 mis-typed", sec["line"])
        self.assertEqual(sec["detail"]["shape_errors"][0]["line"], 2)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), before)


class RuntimeDrift(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="runtime-drift-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "campus"
        self.rt = Path(tmp.name) / "host-store"
        sched = self.root / "scheduled"
        sched.mkdir(parents=True)
        (self.root / "dean").mkdir()
        (sched / "README.md").write_text("# not a job\n")
        (sched / "good.md").write_text("<!-- TASK REGISTRATION\ntaskId: good\n-->\nDo the good job.\n")
        (sched / "copied.md").write_text("---\nname: copied\n---\nStep 1. Read the inbox.\nStep 2. Draft.\n")
        (sched / "stale.md").write_text("---\nname: stale\n---\nStep 1. New instructions.\n")
        (sched / "other.md").write_text("Other job.\n")
        jobs = {
            "good": "---\nname: good\n---\nFollow scheduled/good.md exactly; it is the source of truth.\n",
            "copied": "---\nname: copied\ndescription: runtime\n---\n\nStep 1.  Read the inbox.\nStep 2. Draft.\n",
            "stale": "---\nname: stale\n---\nStep 1. Old instructions that drifted.\n",
            "gone": "---\nname: gone\n---\nFollow scheduled/gone.md.\n",
            "crossed": "---\nname: crossed\n---\nFollow scheduled/other.md.\n",
            "orphan": "---\nname: orphan\n---\nNo canonical file for me.\n",
        }
        for name, text in jobs.items():
            (self.rt / name).mkdir(parents=True)
            (self.rt / name / "SKILL.md").write_text(text)

    def digest(self):
        h = hashlib.sha256()
        for base in (self.root, self.rt):
            for p in sorted(base.rglob("*")):
                if p.is_file():
                    h.update(str(p).encode() + p.read_bytes())
        return h.hexdigest()

    def run_tool(self, *extra):
        return subprocess.run([sys.executable, str(TOOLS / "check_runtime_drift.py"), "--campus-root", str(self.root),
                               "--json", *extra], capture_output=True, text=True, timeout=30)

    def test_drift_kinds_and_never_edits(self):
        before = self.digest()
        p = self.run_tool("--runtime-dir", str(self.rt))
        self.assertEqual(p.returncode, 1, p.stderr)
        r = json.loads(p.stdout)
        kinds = {d["task"]: d["kind"] for d in r["drift"]}
        self.assertEqual(kinds, {"stale": "copy-diverges-from-canonical", "gone": "points-at-missing-canonical",
                                 "crossed": "points-at-another-job"})
        self.assertEqual({x["task"]: x["form"] for x in r["in_sync"]}, {"good": "pointer", "copied": "copy"})
        self.assertEqual([u["task"] for u in r["unowned"]], ["orphan"])
        self.assertEqual(self.digest(), before, "the drift check must never edit either side")

    def test_opt_in_and_skip_rules(self):
        self.assertEqual(json.loads(self.run_tool().stdout)["status"], "skipped")
        shutil.rmtree(self.root / "scheduled")
        p = self.run_tool("--runtime-dir", str(self.rt))
        self.assertEqual((p.returncode, json.loads(p.stdout)["status"]), (0, "not_applicable"))

    def test_campus_doctor_runs_it(self):
        sys_path_tools()
        de = importlib.import_module("doctor_evidence")
        self.assertIn("runtime_drift", de.ORDER)
        sec = de.Evidence(self.root, dt.date(2026, 9, 23), runtime_dirs=[str(self.rt)]).runtime_drift()
        self.assertEqual(sec["status"], "needs-decision", sec)
        self.assertIn("3 drift from canonical", sec["line"])
        self.assertEqual(de.Evidence(self.root, dt.date(2026, 9, 23)).runtime_drift()["status"], "skipped")
        skill = (KERNEL / "skills/campus-doctor/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("| `runtime_drift` |", skill)
        self.assertIn("--runtime-dir", skill)


class LedgerSchemaParityGate(unittest.TestCase):
    def test_niche_009_scans_the_codex_brain(self):
        with tempfile.TemporaryDirectory(prefix="niche009-") as tmp:
            tree = Path(tmp) / "kernel"
            shutil.copytree(KERNEL, tree, ignore=shutil.ignore_patterns("tests", "__pycache__", ".git"))
            gate = [sys.executable, str(tree / "tools/build_niche.py"), "--check", "--only", "NICHE-009"]
            self.assertEqual(subprocess.run(gate, capture_output=True, text=True).returncode, 0)
            codex = tree / "templates/dean-CODEX.md"
            codex.write_text(codex.read_text().replace('"dept":"{department or null}"', '"team":"{team or null}"'))
            p = subprocess.run(gate, capture_output=True, text=True)
            self.assertEqual(p.returncode, 1, p.stdout)
            self.assertIn("dean-CODEX.md", p.stdout + p.stderr)


if __name__ == "__main__":
    unittest.main()
