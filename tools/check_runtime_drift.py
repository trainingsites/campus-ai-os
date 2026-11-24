#!/usr/bin/env python3
"""check_runtime_drift.py - runtime copy vs canonical definition, for EVERY scheduled job (5.3.0 item 4).

THE FAULT CLASS
---------------
A host fires its own RUNTIME copy of a job (Cowork: `{store}/{taskId}/SKILL.md`; Claude Code:
`~/.claude/scheduled-tasks/{taskId}/SKILL.md`), not the campus's canonical `scheduled/{taskId}.md`.
The campus-ambassador evening job ran from a runtime copy that had drifted from its canonical file
and wrote nothing for 8 days while every check that read the CANONICAL file stayed green. A check
that verifies the definition, not what fires, is not a check. That one job got a one-off guard;
this is the general check the logging PRD asked for, and campus-doctor runs it.

WHAT IT CHECKS (per runtime copy)
---------------------------------
  pointer form  the runtime copy names `scheduled/{x}.md` and defers to it (the safe shape):
                drift if it names a file that does not exist, or a DIFFERENT job's file.
  copy form     the runtime copy carries the instructions itself: drift if its body differs from
                `scheduled/{taskId}.md` (frontmatter, HTML comments and whitespace ignored).
  unowned       a runtime copy with no canonical file - reported as an opportunity, never drift.

Same restraint as check_cron_parity.py: the `scheduled/` folder is an opt-in convention. No folder
means not applicable, exit 0. Host-neutral: the CALLER passes where this host keeps runtime copies
(`--runtime-dir`, repeatable); this tool calls no scheduler API. It NEVER edits either side - drift
is a decision for the owner (which copy is right?), not a sync.
platform: claude-code; seat: m4-claude-code

Usage:
  python3 tools/check_runtime_drift.py --campus-root DIR --runtime-dir DIR [--runtime-dir DIR] [--json]
Exit 0 = no drift (or not applicable / nothing supplied) · 1 = drift · 2 = bad input.
"""
import argparse
import json
import re
import sys
from pathlib import Path

POINTER_RE = re.compile(r"scheduled/([A-Za-z0-9_.-]+?\.md)\b")
SKIP = {"README.md"}


def body(text):
    """Instruction body for comparison: no frontmatter, no HTML comments, whitespace collapsed."""
    if text.startswith("---"):
        parts = text.split("\n---", 1)
        text = parts[1].split("\n", 1)[1] if len(parts) == 2 and "\n" in parts[1] else ""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    return " ".join(text.split())


def runtime_copies(dirs):
    found = {}
    for d in dirs:
        if not d.is_dir():
            continue
        for sub in sorted(d.iterdir()):
            if sub.is_symlink():
                continue
            if sub.is_dir() and (sub / "SKILL.md").is_file():
                found.setdefault(sub.name, sub / "SKILL.md")
            elif sub.is_file() and sub.suffix == ".md" and sub.name not in SKIP:
                found.setdefault(sub.stem, sub)
    return found


def check(campus_root, runtime_dirs, scheduled="scheduled"):
    root = Path(campus_root)
    sched = Path(scheduled) if Path(scheduled).is_absolute() else root / scheduled
    dirs = [Path(d) if Path(d).is_absolute() else root / d for d in runtime_dirs]
    if not runtime_dirs:
        return {"status": "skipped", "reason": "no-runtime-dir", "drift": [], "unowned": [], "in_sync": [], "checked": 0}
    if not sched.is_dir():
        return {"status": "not_applicable", "reason": "no-scheduled-dir", "drift": [], "unowned": [], "in_sync": [], "checked": 0}
    missing_dirs = [str(d) for d in dirs if not d.is_dir()]
    drift, unowned, in_sync = [], [], []
    copies = runtime_copies(dirs)
    for task, path in sorted(copies.items()):
        text = path.read_text(encoding="utf-8", errors="replace")
        canonical = sched / f"{task}.md"
        refs = sorted(set(POINTER_RE.findall(text)))
        if refs:
            bad = [r for r in refs if not (sched / r).is_file()]
            other = [r for r in refs if r != f"{task}.md" and (sched / r).is_file()]
            if bad:
                drift.append({"task": task, "runtime": str(path), "kind": "points-at-missing-canonical", "names": bad})
            elif other and f"{task}.md" not in refs:
                drift.append({"task": task, "runtime": str(path), "kind": "points-at-another-job", "names": other})
            else:
                in_sync.append({"task": task, "form": "pointer"})
        elif canonical.is_file():
            if body(text) == body(canonical.read_text(encoding="utf-8", errors="replace")):
                in_sync.append({"task": task, "form": "copy"})
            else:
                drift.append({"task": task, "runtime": str(path), "kind": "copy-diverges-from-canonical",
                              "names": [f"{task}.md"]})
        else:
            unowned.append({"task": task, "runtime": str(path)})
    status = "drift" if drift else "ok"
    return {"status": status, "reason": None, "drift": drift, "unowned": unowned, "in_sync": in_sync,
            "checked": len(copies), "missing_runtime_dirs": missing_dirs}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--campus-root", required=True)
    ap.add_argument("--runtime-dir", action="append", default=[])
    ap.add_argument("--scheduled", default="scheduled")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if not Path(a.campus_root).is_dir():
        print(f"FAIL(2): campus root not found: {a.campus_root}", file=sys.stderr)
        return 2
    r = check(a.campus_root, a.runtime_dir, a.scheduled)
    if a.json:
        print(json.dumps(r, indent=2, sort_keys=True))
    else:
        for d in r["drift"]:
            print(f"  !! {d['task']}: {d['kind']} ({', '.join(d['names'])}) - {d['runtime']}")
        print(f"{'DRIFT' if r['drift'] else 'OK'}: {r['checked']} runtime copies, {len(r['drift'])} drift, "
              f"{len(r['unowned'])} unowned ({r['status']})")
    return 1 if r["drift"] else 0


if __name__ == "__main__":
    sys.exit(main())
