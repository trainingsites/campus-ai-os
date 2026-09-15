#!/usr/bin/env python3
"""
generate_task_index.py  -  Task System v2  (v5.1 payload item 3, owed since S207;
5.2.0 Phase 5.4: status cap, compact startup view, normalized JSON for parity)

THE PROBLEM IT SOLVES
---------------------
A single growing TASKS.md file is read in full every session and edited by hand
in the middle of work. It rots in a specific way: the file gets long, entries get
stale, two sessions edit different parts of the same list, and eventually nobody
trusts it - so a second, informal task list appears in someone's head.

Task System v2 splits it:

  dean/tasks/{slug}.md   ONE FILE PER TASK. Frontmatter = state. Body = history.
                         Permanent. This is the source of truth.
  dean/TASKS.md          A GENERATED INDEX. Cheap to read, never edited by hand,
                         thrown away and rebuilt on every change.

DERIVATION IS THE POINT
-----------------------
The index is *derived*, so it cannot disagree with the tasks - the way a
hand-kept summary always eventually does. `--check` proves it: it regenerates in
memory and compares byte-for-byte against what is on disk. A difference means
either someone edited the index directly (their edit is about to be lost) or a
task changed and nobody rebaked (the index is lying right now). Both are worth
knowing; neither is discoverable by reading the file.

This is the same lesson the Codex manifest taught: a parity check between two
hand-maintained files is a smoke alarm, but derivation is a fix.

SIZE IS A CONTRACT (5.2.0 Phase 5.4)
------------------------------------
The reference campus once shipped a 22,843-byte `status:` - 36% of the whole
index. So: `status` is truncated IN THE VIEW at STATUS_MAX chars (the task file
keeps the full text), lint flags the source, `needs` is capped the same way, and
`--compact` renders the startup digest under a per-row and an overall byte
budget with a drill-down line to the full index. `--json` emits the normalized
task set (stage vocabulary mapped to the kernel's) so a campus running its own
generator can be compared on the *same task set* rather than byte-equality
(Codex critique 2026-09-05 #10).

WHAT IS *NOT* A TASK
--------------------
Recurring jobs are not tasks. They are definitions that run on a schedule; their
runs belong in the activity ledger, and only a FAILURE earns a task file. Filing
one task per run buries the real work under machine noise - which is exactly how
the first version of this became unreadable.

Usage:
  generate_task_index.py --tasks dean/tasks --out dean/TASKS.md
  generate_task_index.py --tasks dean/tasks --out dean/TASKS.md --check
  generate_task_index.py --tasks dean/tasks --compact [--row-budget 240] [--budget 6000]
  generate_task_index.py --tasks dean/tasks --json [--today YYYY-MM-DD]
"""

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

# Stage vocabulary. ONE owner for this list - the skill prose and any lint must
# read it from here rather than restating it, or the vocabulary forks.
ORDER = ["waiting-owner", "active", "queued", "blocked", "done", "idea"]
HEADINGS = {
    "waiting-owner": "⏳ Waiting on you",
    "active": "\U0001f528 Active",
    "queued": "\U0001f4cb Queued",
    "blocked": "\U0001f6ab Blocked",
    "done": "✅ Done This Week",
    "idea": "\U0001f4a1 Ideas",
}
# A campus may name the owner in its stage ("waiting-james" on the reference
# campus). READ those as the kernel stage; never write them. One place.
STAGE_ALIASES = {"waiting-james": "waiting-owner", "waiting": "waiting-owner"}
# How long a stage may sit untouched before the index flags it. `active` is
# short on purpose: "active" means a session is on it NOW. If nothing has touched
# it in days, it is queued and mislabelled, and mislabelled work is invisible.
STALE_DAYS = {"active": 4, "waiting-owner": 7, "queued": 90}
ROT_DAYS = 30               # stale by this much more = rotten (loud, not decoration)
DONE_DROPS_AFTER_DAYS = 7   # from the INDEX only. The task file is permanent.
STATUS_MAX = 500            # view truncation + lint threshold (chars)
NEEDS_MAX = 240
COMPACT_ROW_BUDGET = 240    # bytes per row in --compact
COMPACT_BUDGET = 6000       # bytes for the whole --compact digest

def utc_today():
    """Day arithmetic is UTC, like every stamp the kernel writes (run ids, ledger
    lines) and like the reference campus's Node generator (Date.now() minus a
    UTC-midnight `updated`). A local-date default made the two generators
    disagree by one day near midnight - found by the parity fixture."""
    return datetime.datetime.now(datetime.timezone.utc).date()


FM_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
KV_RE = re.compile(r"^(\w[\w-]*):\s*(.*?)\s*(#.*)?$")


def parse(path: Path):
    raw = path.read_text(encoding="utf-8", errors="replace")
    m = FM_RE.match(raw)
    if not m:
        return None, f"{path.name}: no frontmatter"
    fm = {}
    for line in m.group(1).split("\n"):
        kv = KV_RE.match(line)
        if kv:
            fm[kv.group(1)] = kv.group(2).strip('"')
    return fm, None


def clip(text, limit):
    """View-only truncation. The task file keeps the full text."""
    if text is None:
        return None
    return text if len(text) <= limit else text[:limit] + f"… [+{len(text) - limit} chars — see task file]"


def collect(tasks_dir: Path, today=None):
    """Read every task file once. Returns (tasks, lint). Tasks carry normalized
    `stage` (kernel vocabulary), `_stage_raw`, `_days`, `_stale`, `_rotten`."""
    today = today or utc_today()
    tasks, lint = [], []
    for path in sorted(tasks_dir.glob("*.md")):
        fm, err = parse(path)
        if err:
            lint.append(err)
            continue
        raw_stage = fm.get("stage")
        stage = STAGE_ALIASES.get(raw_stage, raw_stage)
        if stage not in ORDER:
            lint.append(f"{path.name}: invalid stage \"{raw_stage}\" "
                        f"(expected one of {', '.join(ORDER)})")
            continue
        days = None
        if fm.get("updated"):
            try:
                days = (today - datetime.date.fromisoformat(fm["updated"])).days
            except ValueError:
                lint.append(f"{path.name}: updated is not a YYYY-MM-DD date")
        needs = fm.get("needs")
        if stage == "waiting-owner" and needs in (None, "", "null"):
            lint.append(f"{path.name}: waiting-owner without a needs: line - "
                        f"say what you are waiting for")
        if stage == "done" and not fm.get("updated"):
            lint.append(f"{path.name}: done without a date")
        status = fm.get("status")
        if stage != "done" and status not in (None, "", "null") and len(status) > STATUS_MAX:
            lint.append(f"{path.name}: status is {len(status)} chars (max {STATUS_MAX}) - "
                        f"status is a one-liner for the index; put detail in the body")
        if stage != "done" and needs not in (None, "", "null") and len(needs) > NEEDS_MAX:
            lint.append(f"{path.name}: needs is {len(needs)} chars (max {NEEDS_MAX}) - one ask per line")
        if stage == "done" and days is not None and days > DONE_DROPS_AFTER_DAYS:
            continue    # drops from the index; the file stays on disk forever
        fm["_file"] = path.name
        fm["_stage_raw"] = raw_stage
        fm["stage"] = stage
        fm["_days"] = days
        fm["_stale"] = (STALE_DAYS.get(stage) is not None
                        and days is not None and days > STALE_DAYS[stage])
        fm["_rotten"] = bool(fm["_stale"] and days > STALE_DAYS[stage] + ROT_DAYS)
        tasks.append(fm)
    return tasks, lint


def row_bits(t, stage):
    bits = []
    if t["_rotten"]:
        bits.append("🔴ROTTEN")
    elif t["_stale"]:
        bits.append("⚠️STALE")
    if t.get("lane") not in (None, "", "null"):
        bits.append(f"lane:{t['lane']}")
    if t.get("updated"):
        bits.append(f"upd {t['updated']}")
    if stage == "waiting-owner" and t.get("needs") not in (None, "", "null"):
        bits.append(f"needs: {clip(t['needs'], NEEDS_MAX)}")
    if t.get("status") not in (None, "", "null"):
        bits.append(clip(t["status"], STATUS_MAX))
    return bits


def build(tasks_dir: Path, today=None) -> tuple[str, int, int]:
    today = today or utc_today()
    tasks, lint = collect(tasks_dir, today)
    rotten = [t for t in tasks if t["_rotten"]]
    stale = [t for t in tasks if t["_stale"] and not t["_rotten"]]

    out = [
        f"# TASKS (GENERATED {today.isoformat()})",
        "",
        "**This file is a baked index - NEVER edit it by hand.** Source of truth: "
        "`dean/tasks/*.md`, one file per task (frontmatter = state, body = "
        "history). Change a task -> edit its file -> rebake with "
        "`tools/generate_task_index.py`. Anything typed here is lost on the next "
        "rebake. Recurring jobs are NOT tasks: they live in `scheduled/`, their "
        "runs go to the activity ledger, and only a failure earns a task file. "
        f"Task files are permanent; `done` older than {DONE_DROPS_AFTER_DAYS} "
        f"days drops from this index only. Status lines are cut at {STATUS_MAX} chars here.",
        "",
        f"**Board health:** {len(rotten)} rotten (past clock +{ROT_DAYS}d) · {len(stale)} stale · {len(lint)} lint"
        + (("\n\n> 🔴 **" + str(len(rotten)) + " ROTTEN — decide or close these before starting anything new.** "
            + " · ".join(f"`{t['_file'][:-3]}` ({t['_days']}d)" for t in rotten[:8])
            + (f" · +{len(rotten) - 8} more" if len(rotten) > 8 else "")) if rotten else ""),
    ]

    for stage in ORDER:
        group = sorted((t for t in tasks if t["stage"] == stage),
                       key=lambda t: t.get("updated") or "", reverse=True)
        if not group:
            continue
        out += ["", f"## {HEADINGS[stage]} ({len(group)})", ""]
        for t in group:
            out.append(f"- **{t.get('title', t['_file'])}** - "
                       f"{' · '.join(row_bits(t, stage))} -> `tasks/{t['_file']}`")

    if lint:
        out += ["", f"## \U0001f9f9 Lint ({len(lint)})", ""]
        out += [f"- {l}" for l in lint]

    return "\n".join(out) + "\n", len(tasks), len(lint)


def compact(tasks_dir: Path, today=None, row_budget=COMPACT_ROW_BUDGET, budget=COMPACT_BUDGET, index_path="dean/TASKS.md"):
    """The startup digest: what a session must know, under a byte budget, with
    one drill-down line. Open stages only; done/idea never make the digest."""
    today = today or utc_today()
    tasks, lint = collect(tasks_dir, today)
    rotten = sum(1 for t in tasks if t["_rotten"])
    stale = sum(1 for t in tasks if t["_stale"] and not t["_rotten"])
    lines = [f"TASKS digest {today.isoformat()} · {len(tasks)} open+recent · {rotten} rotten · {stale} stale · {len(lint)} lint"]
    shown = omitted = 0
    for stage in ("waiting-owner", "active", "blocked", "queued"):
        group = sorted((t for t in tasks if t["stage"] == stage), key=lambda t: t.get("updated") or "", reverse=True)
        if not group:
            continue
        lines.append(f"{HEADINGS[stage]} ({len(group)})")
        for t in group:
            flag = "🔴" if t["_rotten"] else "⚠️" if t["_stale"] else "·"
            need = f" needs: {t['needs']}" if stage == "waiting-owner" and t.get("needs") not in (None, "", "null") else ""
            row = f"  {flag} {t.get('title', t['_file'])}{need}"
            if t.get("status") not in (None, "", "null"):
                row += f" — {t['status']}"
            row = row.encode("utf-8")[:row_budget].decode("utf-8", errors="ignore")
            if row_budget and len(row.encode("utf-8")) >= row_budget:
                row = row.rstrip() + "…"
            projected = sum(len(l.encode("utf-8")) + 1 for l in lines) + len(row.encode("utf-8")) + 1
            if budget and projected > budget - 120:
                omitted += 1
                continue
            lines.append(row)
            shown += 1
    lines.append(f"Full index: `{index_path}` ({shown} rows shown" + (f", {omitted} omitted for budget" if omitted else "") + ")")
    return "\n".join(lines) + "\n", shown, omitted


def normalized(tasks_dir: Path, today=None):
    """Machine view for parity with any other generator: the task SET and the
    facts a startup view depends on - not the rendering."""
    today = today or utc_today()
    tasks, lint = collect(tasks_dir, today)
    rows = []
    for t in sorted(tasks, key=lambda t: t["_file"]):
        rows.append({
            "file": t["_file"], "title": t.get("title"), "stage": t["stage"], "stage_raw": t["_stage_raw"],
            "updated": t.get("updated"), "lane": t.get("lane") if t.get("lane") not in ("", "null") else None,
            "stale": t["_stale"], "rotten": t["_rotten"],
            "needs_present": t.get("needs") not in (None, "", "null"),
            "status_len": len(t["status"]) if t.get("status") not in (None, "", "null") else 0,
            "status_truncated": t.get("status") not in (None, "", "null") and len(t["status"]) > STATUS_MAX,
        })
    return {"today": today.isoformat(), "vocabulary": ORDER, "aliases": STAGE_ALIASES,
            "limits": {"status_max": STATUS_MAX, "needs_max": NEEDS_MAX, "stale_days": STALE_DAYS, "rot_days": ROT_DAYS,
                       "done_drops_after_days": DONE_DROPS_AFTER_DAYS},
            "tasks": rows, "lint": lint}


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tasks", default="dean/tasks", help="the per-task files")
    ap.add_argument("--out", default="dean/TASKS.md", help="the generated index")
    ap.add_argument("--check", action="store_true",
                    help="verify the index on disk matches a fresh bake; "
                         "changes nothing. Exit 1 if it has drifted.")
    ap.add_argument("--compact", action="store_true", help="print the startup digest (no file written)")
    ap.add_argument("--json", action="store_true", help="print the normalized task set (no file written)")
    ap.add_argument("--today", default=None, help="YYYY-MM-DD, for reproducible output")
    ap.add_argument("--row-budget", type=int, default=COMPACT_ROW_BUDGET)
    ap.add_argument("--budget", type=int, default=COMPACT_BUDGET)
    args = ap.parse_args()

    today = datetime.date.fromisoformat(args.today) if args.today else None
    tasks_dir = Path(args.tasks)
    if not tasks_dir.is_dir():
        # An owner who has not adopted per-task files is not broken. Say nothing
        # and pass - same restraint as every other opt-in check in this kernel.
        return 0

    if args.json:
        print(json.dumps(normalized(tasks_dir, today), indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    if args.compact:
        text, _, _ = compact(tasks_dir, today, args.row_budget, args.budget, args.out)
        sys.stdout.write(text)
        return 0

    text, n_tasks, n_lint = build(tasks_dir, today)
    out_path = Path(args.out)

    if args.check:
        current = out_path.read_text(encoding="utf-8") if out_path.exists() else None
        if current is None:
            print(f"[!!] {out_path} does not exist - the index has never been "
                  f"generated. Run without --check to create it.")
            return 1
        if current != text:
            print(f"[!!] {out_path} does NOT match its source task files.\n"
                  f"     Either it was edited by hand (that edit will be lost on "
                  f"the next rebake) or a task changed and nobody rebaked (the "
                  f"index is out of date right now).\n"
                  f"     Fix: rebake it. Never edit the index directly.")
            return 1
        print(f"[OK] Index matches its {n_tasks} source task files.")
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    print(f"Index: {out_path} ({len(text)} bytes, ~{len(text)//4} tokens) "
          f"· {n_tasks} tasks indexed · {n_lint} lint flags")
    return 0


if __name__ == "__main__":
    sys.exit(main())
