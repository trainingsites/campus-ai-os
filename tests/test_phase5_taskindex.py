"""Campus AI OS 5.2.0 Phase 5.4 - task-index generator: status cap, compact digest, normalized parity.

Temp task dirs only. The parity test against the campus's Node generator runs only when
this tree sits inside a campus that has `dean/tasks/_meta/generate.mjs` and Node.
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
TOOL = KERNEL / "tools" / "generate_task_index.py"
NODE = shutil.which("node")
TODAY = "2026-09-08"


def task(name, **fm):
    lines = ["---"] + [f'{k}: "{v}"' if isinstance(v, str) and (":" in v or "#" in v) else f"{k}: {v}" for k, v in fm.items()] + ["---", "", "## body", ""]
    return name, "\n".join(lines)


class Index(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="campus-phase54-")
        self.addCleanup(self.tmp.cleanup)
        self.tasks = Path(self.tmp.name) / "dean" / "tasks"
        self.tasks.mkdir(parents=True)
        self.out = Path(self.tmp.name) / "dean" / "TASKS.md"
        long = "x" * 900
        for name, text in (
            task("a-active.md", title="Active thing", stage="active", updated="2026-09-07", status="short"),
            task("b-wait.md", title="Waiting thing", stage="waiting-owner", updated="2026-09-01", needs="an answer", status=long),
            task("c-james.md", title="Campus-vocab thing", stage="waiting-james", updated="2026-09-06", needs="a click", status="ok"),
            task("d-rotten.md", title="Rotten thing", stage="active", updated="2026-06-01", status="old"),
            task("e-done-old.md", title="Old done", stage="done", updated="2026-08-01"),
            task("f-queued.md", title="Queued thing", stage="queued", updated="2026-09-05", lane="dean", status="q"),
        ):
            (self.tasks / name).write_text(text, encoding="utf-8")

    def run_tool(self, *args):
        return subprocess.run([sys.executable, str(TOOL), "--tasks", str(self.tasks), "--out", str(self.out),
                               "--today", TODAY, *map(str, args)], text=True, capture_output=True, timeout=60)

    def test_bake_check_and_status_cap(self):
        p = self.run_tool()
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        text = self.out.read_text(encoding="utf-8")
        self.assertIn("Status lines are cut at 500 chars", text)
        self.assertIn("… [+400 chars — see task file]", text)          # 900 - 500
        self.assertNotIn("x" * 501, text)
        self.assertIn("b-wait.md: status is 900 chars (max 500)", text)  # lint at source
        self.assertIn("🔴ROTTEN", text)
        self.assertIn("**Board health:** 1 rotten", text)
        self.assertNotIn("Old done", text)                               # done > 7d drops
        self.assertIn("Campus-vocab thing", text)                        # waiting-james read as waiting-owner
        self.assertIn("## ⏳ Waiting on you (2)", text)
        self.assertEqual(self.run_tool("--check").returncode, 0)
        self.out.write_text(text + "hand edit\n", encoding="utf-8")
        self.assertEqual(self.run_tool("--check").returncode, 1)

    def test_compact_digest_honours_budgets(self):
        p = self.run_tool("--compact")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertTrue(p.stdout.startswith(f"TASKS digest {TODAY}"))
        self.assertLessEqual(len(p.stdout.encode("utf-8")), 6000)
        self.assertNotIn("Old done", p.stdout)
        self.assertIn("Full index:", p.stdout)
        for line in p.stdout.splitlines():
            self.assertLessEqual(len(line.encode("utf-8")), 240 + 4, line[:60])
        tight = self.run_tool("--compact", "--budget", "400")
        self.assertEqual(tight.returncode, 0)
        self.assertLessEqual(len(tight.stdout.encode("utf-8")), 400 + 160)
        self.assertIn("omitted for budget", tight.stdout)
        self.assertFalse(self.out.exists(), "--compact must not write the index")

    def test_json_is_normalized(self):
        p = self.run_tool("--json")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        d = json.loads(p.stdout)
        by = {t["file"]: t for t in d["tasks"]}
        self.assertEqual(by["c-james.md"]["stage"], "waiting-owner")
        self.assertEqual(by["c-james.md"]["stage_raw"], "waiting-james")
        self.assertTrue(by["b-wait.md"]["status_truncated"])
        self.assertEqual(by["b-wait.md"]["status_len"], 900)
        self.assertTrue(by["d-rotten.md"]["rotten"])
        self.assertNotIn("e-done-old.md", by)
        self.assertEqual(d["limits"]["status_max"], 500)


@unittest.skipUnless(NODE and (CAMPUS / "dean/tasks/_meta/generate.mjs").is_file(), "no campus Node generator beside this tree")
class ParityWithCampusGenerator(unittest.TestCase):
    """Same task set, normalized - not byte equality (Codex critique #10)."""

    def test_same_task_set_and_flags(self):
        with tempfile.TemporaryDirectory(prefix="campus-phase54p-") as tmp:
            root = Path(tmp)
            tasks = root / "dean" / "tasks"
            shutil.copytree(CAMPUS / "dean" / "tasks", tasks)
            for junk in tasks.rglob("__pycache__"):
                shutil.rmtree(junk)
            # kernel view
            p = subprocess.run([sys.executable, str(TOOL), "--tasks", str(tasks), "--json"], text=True, capture_output=True, timeout=120)
            self.assertEqual(p.returncode, 0, p.stderr)
            kernel = {t["file"]: t for t in json.loads(p.stdout)["tasks"]}
            # campus view: bake its index into the temp copy and parse the rows
            out = root / "dean" / "TASKS.md"
            n = subprocess.run([NODE, str(tasks / "_meta" / "generate.mjs"), "--out", str(out)], text=True, capture_output=True, timeout=120)
            self.assertEqual(n.returncode, 0, n.stdout + n.stderr)
            campus = {}
            for line in out.read_text(encoding="utf-8").splitlines():
                if line.startswith("- **") and "`tasks/" in line:
                    f = line.rsplit("`tasks/", 1)[1].split("`", 1)[0]
                    # the flag is always the FIRST bit after the title; a status that merely
                    # mentions "STALE" must not count (it happened on the reference campus)
                    bits = line.split("** — ", 1)[1] if "** — " in line else ""
                    first = bits.split(" · ", 1)[0].strip()
                    campus[f] = {"stale": first in ("⚠️STALE", "🔴ROTTEN"), "rotten": first == "🔴ROTTEN",
                                 "truncated": "chars — see task file]" in line}
            self.assertEqual(set(kernel), set(campus), "the two generators index different task sets")
            for f, k in kernel.items():
                with self.subTest(file=f):
                    self.assertEqual(k["rotten"], campus[f]["rotten"])
                    self.assertEqual(k["stale"] or k["rotten"], campus[f]["stale"])
                    self.assertEqual(k["status_truncated"], campus[f]["truncated"])


if __name__ == "__main__":
    unittest.main()
