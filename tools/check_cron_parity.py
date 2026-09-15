#!/usr/bin/env python3
"""
check_cron_parity.py  -  canonical -> live schedule parity  (v5.1 payload item 6)

THE PROBLEM THIS EXISTS FOR
---------------------------
A campus keeps its recurring jobs in two places:

  canonical   scheduled/{task}.md   <- the file the owner edits, in their campus
  live        the host's scheduler  <- what actually fires

Nothing compared them. Three mismatches were found by hand across S206, S218 and
S219 - each one patched as an instance, and each time the NEXT one was found the
same way: by accident, months later, usually because a job didn't run.

A job that silently fires at the wrong hour is worse than one that fails: a
failure is loud, drift is quiet. `weekly-social-planner` was canonically Sunday
6pm and live Sunday 3am for ~2 months. Nobody noticed, because nothing looked.

THE SHAPE OF THE FIX  (S219 decision: one owner per shared fact + one loud check)
---------------------------------------------------------------------------------
The canonical file is the OWNER of a task's schedule. Live is a derived copy.
This script is the check that refuses to let them disagree quietly. It is
deliberately NOT a sync tool - it never edits either side. Drift is a decision
(which one is right?), and decisions belong to the owner.

THE CONVENTION IS OPT-IN  (this is the important part)
------------------------------------------------------
Keeping canonical definitions in `scheduled/*.md` is ONE campus's working habit,
not a rule of the product. Most owners will never have that folder and have no
reason to want it - they schedule a job by asking for it, and the host stores it.
That is a complete, correct way to run a campus.

No `scheduled/` directory means parity does not apply; live health still runs. It must never tell an owner their perfectly good campus is
"undocumented", never nag them toward a filing habit they didn't ask for, and
never present the absence of a convention as a finding. The check only has an
opinion when the owner has already shown they want one, by keeping the files.

This is the same restraint as check 8a-i (never impose the canonical department
names on someone running their own): report against the owner's structure, never
against ours.

HOST NEUTRALITY  (learned the expensive way in item 7)
------------------------------------------------------
Schedulers are host-specific; the caller supplies capability and retrieval evidence. So this script
does NOT call any scheduler API - it reads the live list as JSON from stdin or
--live, and the CALLER supplies it however their host allows. A campus on a host
with explicit unavailable capability reports EXEMPT and exits 0. Missing input
is unknown (exit 2). A retrieved empty list is available and participates in parity.
Accepts legacy arrays/tasks/scheduledTasks or an envelope with capability=available,
retrieval=success and tasks. No live scheduler is called or modified.

Exit codes:  0 = parity, not applicable, or no scheduler   1 = drift   2 = bad input
"""

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

# The canonical schedule fact lives in this block, and nowhere else:
#   <!-- TASK REGISTRATION
#   taskId: foo
#   cronExpression: 0 7 * * *
#   -->
TASK_ID_RE = re.compile(r"^\s*taskId:\s*(\S+)", re.MULTILINE)
CRON_RE = re.compile(r"^\s*cronExpression:\s*(.+?)\s*$", re.MULTILINE)

# A canonical file may legitimately declare "I am not on a timer."
NOT_SCHEDULED = re.compile(r"^\s*none\b", re.IGNORECASE)


def normalize_cron(expr: str) -> str:
    """Whitespace-normalize only.

    Deliberately NOT clever. Two cron strings that differ in any meaningful
    field are drift, and this check would rather over-report (the owner glances
    and says 'fine') than normalize away a real difference. `0 18 * * 0` and
    `0 18 * * 7` both mean Sunday but are NOT treated as equal - if a campus
    writes one and the host stores the other, that is worth one line of output.
    """
    return " ".join(expr.split())


def convention_in_use(scheduled_dir: Path) -> bool:
    """Does this owner actually keep canonical schedule files?

    If not, this check has no opinion to offer. Absence is not a finding - it is
    simply a campus that schedules jobs by asking for them, which is the normal
    way and needs no folder. Checking anyway would list the owner's own working
    jobs under a heading implying something is wrong with them.
    """
    if not scheduled_dir.is_dir():
        return False
    return any(
        p.name.upper() != "README.MD" for p in scheduled_dir.glob("*.md")
    )


def read_canonical(scheduled_dir: Path) -> tuple[dict, list, list]:
    """Return (by_task_id, unscheduled, prose_only).

    prose_only is the quiet root cause: a canonical file that states its schedule
    in English ("Run daily at 8:00 AM ET") but carries no machine-readable
    cronExpression. Such a file CANNOT be checked - the fact has no owner a
    machine can read - so it is reported separately rather than passing silently.
    """
    by_id, unscheduled, prose_only = {}, [], []

    if not scheduled_dir.is_dir():
        return by_id, unscheduled, prose_only

    for path in sorted(scheduled_dir.glob("*.md")):
        if path.name.upper() == "README.MD":
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        cron_match = CRON_RE.search(text)
        id_match = TASK_ID_RE.search(text)

        if not cron_match:
            prose_only.append(path.name)
            continue

        task_id = id_match.group(1) if id_match else path.stem
        raw = cron_match.group(1).strip()

        if NOT_SCHEDULED.match(raw):
            unscheduled.append(task_id)
            continue

        by_id[task_id] = {"cron": normalize_cron(raw), "file": path.name}

    return by_id, unscheduled, prose_only


def read_live(payload) -> tuple[dict, list]:
    """Return (recurring_by_id, one_time_ids).

    One-time tasks (a `fireAt` and no cron) are EXEMPT: a reminder someone set
    for next Tuesday is not supposed to have a canonical definition, and flagging
    it would train the owner to ignore this check - which is how a check dies.
    """
    live, one_time = {}, []

    if isinstance(payload, dict):
        keys = [k for k in ("tasks", "scheduledTasks") if k in payload]
        if len(keys) != 1 or "error" in payload:
            raise ValueError("unknown or ambiguous scheduler payload")
        payload = payload[keys[0]]
    if not isinstance(payload, list):
        raise ValueError("live task payload must be a JSON array of task objects")

    for entry in payload:
        if not isinstance(entry, dict):
            raise ValueError("task must be an object")
        task_id = entry.get("taskId") or entry.get("id")
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("task needs a string id")
        if task_id in live or task_id in one_time:
            raise ValueError("duplicate task id")
        cron = entry.get("cronExpression")
        if not cron:
            if not _parse_ts(entry.get("fireAt")):
                raise ValueError("task needs cronExpression or valid fireAt")
            one_time.append(task_id)
            continue
        if not isinstance(cron, str) or len(cron.split()) != 5:
            raise ValueError("cronExpression must have five fields")
        if not isinstance(entry.get("enabled"), bool):
            raise ValueError("recurring task needs boolean enabled")
        for field in ("lastRunAt", "nextRunAt"):
            if entry.get(field) is not None and _parse_ts(entry[field]) is None:
                raise ValueError(f"invalid {field}")
        live[task_id] = {
            "cron": normalize_cron(cron),
            "enabled": bool(entry.get("enabled", False)),
            "last_run": entry.get("lastRunAt"),
            "next_run": entry.get("nextRunAt"),
        }

    return live, one_time


# ---------------------------------------------------------------------------
# HEALTH  -  the layer that serves EVERY owner
#
# The parity layer above only helps someone who keeps canonical files. Most
# owners don't, and shouldn't have to - but they still have real recurring jobs
# running, and a health check that says nothing about them is a health check with
# a hole in it. This layer reads ONLY live data, so it works on every campus:
# how much is scheduled, how much is switched off, and which "on" jobs have
# quietly stopped firing.
#
# A job that is enabled but silently not running is the expensive failure. The
# owner believes it runs. Nothing tells them otherwise.
# ---------------------------------------------------------------------------

def _parse_ts(value):
    if not value or not isinstance(value, str):
        return None
    try:
        stamp = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return stamp if stamp.tzinfo is not None else None
    except ValueError:
        return None


def expected_interval_days(cron: str) -> float:
    """Coarse cadence from a cron string. Deliberately rough.

    Used only to decide "has this gone quiet for implausibly long", so being
    approximate is fine and being WRONG is cheap in one direction only: err
    toward silence. A real cron parser is not worth a dependency here.
    """
    fields = cron.split()
    if len(fields) < 5:
        return 1.0
    minute, hour, dom, month, dow = fields[:5]
    if "/" in hour or "/" in minute:      # every N hours / minutes
        return 0.5
    if dow != "*":                        # a weekday list => weekly-ish
        return 7.0
    if dom != "*":                        # a day-of-month => monthly-ish
        return 31.0
    return 1.0                            # daily


def assess_health(live: dict, now=None) -> dict:
    """Report on live recurring jobs, using no canonical files at all."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    enabled = {t: d for t, d in live.items() if d["enabled"]}
    disabled = sorted(t for t, d in live.items() if not d["enabled"])

    stalled, never_run = [], []
    for task, d in sorted(enabled.items()):
        last = _parse_ts(d.get("last_run"))
        if last is None:
            never_run.append(task)
            continue
        quiet_days = (now - last).total_seconds() / 86400.0
        # 3x the expected gap before we say anything - a job is allowed to be
        # late, and a check that cries early gets ignored.
        grace = expected_interval_days(d["cron"]) * 3
        if quiet_days > grace:
            stalled.append({
                "task": task,
                "days_quiet": round(quiet_days),
                "cron": d["cron"],
            })

    return {
        "total": len(live),
        "enabled": len(enabled),
        "disabled": disabled,
        "stalled": stalled,
        "never_run": never_run,
    }


def compare(canonical: dict, live: dict) -> dict:
    canon_ids, live_ids = set(canonical), set(live)

    drift = [
        {
            "task": tid,
            "canonical": canonical[tid]["cron"],
            "live": live[tid]["cron"],
            "enabled": live[tid]["enabled"],
            "file": canonical[tid]["file"],
        }
        for tid in sorted(canon_ids & live_ids)
        if canonical[tid]["cron"] != live[tid]["cron"]
    ]

    return {
        "match": sorted(
            t for t in canon_ids & live_ids
            if canonical[t]["cron"] == live[t]["cron"]
        ),
        "drift": drift,
        # Defined in the campus, never registered: the job the owner believes is
        # running and which has never once fired.
        "canonical_only": sorted(canon_ids - live_ids),
        # Registered with nothing in the campus describing it: real work with no
        # reviewable definition, invisible to anyone reading scheduled/.
        "live_only": sorted(live_ids - canon_ids),
    }


def render_health(h, one_time) -> str:
    """The universal layer. Every owner with a scheduler sees this."""
    out = []
    bits = [f"{h['enabled']} running"]
    if h["disabled"]:
        bits.append(f"{len(h['disabled'])} switched off")
    if one_time:
        bits.append(f"{len(one_time)} one-time")
    out.append(f"[OK] Recurring work: {h['total']} scheduled jobs  -  "
               + ", ".join(bits))

    if h["stalled"]:
        out.append("[!!] Switched on but not running:")
        for s in h["stalled"]:
            day_word = "day" if s["days_quiet"] == 1 else "days"
            out.append(f"     {s['task']}  -  last ran {s['days_quiet']} "
                       f"{day_word} ago, expected `{s['cron']}`")
        out.append("     These look on but aren't firing. Worth checking - a job "
                   "that fails loudly gets noticed; one that goes quiet doesn't.")

    if h["never_run"]:
        out.append(f"[--] Switched on but has never run: "
                   f"{', '.join(h['never_run'])}")

    return "\n".join(out)


def render(result, unscheduled, prose_only, one_time, verbose: bool) -> str:
    out = []
    n_ok = len(result["match"])
    n_drift = len(result["drift"])
    n_canon = len(result["canonical_only"])
    n_live = len(result["live_only"])

    out.append(f"Cron parity  -  {n_ok} in sync, {n_drift} drifted, "
               f"{n_canon} never registered, {n_live} undocumented")
    out.append("")

    if result["drift"]:
        out.append("[!!] SCHEDULE DRIFT  (canonical and live disagree)")
        for d in result["drift"]:
            state = "enabled" if d["enabled"] else "disabled"
            out.append(f"     {d['task']}")
            out.append(f"       canonical : {d['canonical']}   ({d['file']})")
            out.append(f"       live      : {d['live']}   [{state}]")
        out.append("")

    if result["canonical_only"]:
        out.append("[!!] DEFINED BUT NEVER REGISTERED  (cannot ever fire)")
        for t in result["canonical_only"]:
            out.append(f"     {t}")
        out.append("")

    if result["live_only"]:
        out.append("[--] REGISTERED BUT UNDOCUMENTED  (no canonical definition)")
        for t in result["live_only"]:
            out.append(f"     {t}")
        out.append("")

    if prose_only:
        out.append("[--] SCHEDULE NOT MACHINE-READABLE  (states its time in prose "
                   "only - cannot be checked)")
        for f in prose_only:
            out.append(f"     {f}")
        out.append("")

    if verbose:
        if unscheduled:
            out.append(f"[OK] Trigger-based, no timer expected: {', '.join(unscheduled)}")
        if one_time:
            out.append(f"[OK] One-time tasks, exempt: {len(one_time)}")
        if result["match"]:
            out.append(f"[OK] In sync: {', '.join(result['match'])}")
        out.append("")

    if not (result["drift"] or result["canonical_only"]):
        out.append("[OK] Every canonical schedule matches what is registered.")

    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scheduled", default="scheduled",
                    help="campus scheduled/ directory (default: ./scheduled)")
    ap.add_argument("--live", help="JSON file of live tasks; omit to read stdin")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--verbose", action="store_true", help="also list what passed")
    args = ap.parse_args()

    scheduled_dir = Path(args.scheduled)

    # A missing response is unknown, never evidence that a host has no scheduler.
    def early(status, code, detail, exit_code):
        payload = {"scheduler": {"status": status, "code": code, "detail": detail},
                   "health": None, "one_time": [], "parity_applicable": False,
                   "match": [], "drift": [], "canonical_only": [], "live_only": [],
                   "unscheduled": [], "prose_only": []}
        print(json.dumps(payload, indent=2) if args.json else f"[{code}] {detail}")
        return exit_code

    try:
        raw = Path(args.live).read_text(encoding="utf-8") if args.live else (
            sys.stdin.read() if not sys.stdin.isatty() else "")
        if not raw.strip():
            return early("unknown", "SCHEDULER_UNKNOWN", "No retrieval evidence supplied", 2)
        payload = json.loads(raw)
        if isinstance(payload, dict) and "capability" in payload:
            cap, retrieval = payload.get("capability"), payload.get("retrieval")
            if cap == "unavailable" and retrieval == "not_attempted" and not any(
                k in payload for k in ("tasks", "scheduledTasks", "error")):
                return early("unavailable", "SCHEDULER_UNAVAILABLE", "Caller reports scheduler unavailable", 0)
            if cap == "available" and retrieval == "failed":
                return early("failed", "SCHEDULER_RETRIEVAL_FAILED", "Scheduler retrieval failed", 2)
            if cap != "available" or retrieval != "success":
                raise ValueError("invalid capability/retrieval combination")
        live, one_time = read_live(payload)
    except (OSError, UnicodeError, ValueError) as e:
        return early("invalid", "SCHEDULER_INVALID", str(e), 2)

    # ---- LAYER 1: health. Universal. Needs no canonical files. ----
    health = assess_health(live)

    # ---- LAYER 2: parity. Only for owners who keep canonical files. ----
    # Not applicable beats a false finding: an owner who never adopted the
    # canonical-file habit has nothing to be out of sync WITH, and must never be
    # told their working jobs are "undocumented".
    applicable = convention_in_use(scheduled_dir)
    canonical, unscheduled, prose_only = (
        read_canonical(scheduled_dir) if applicable else ({}, [], [])
    )
    result = compare(canonical, live) if applicable else None

    if args.json:
        payload = {"scheduler": {"status": "populated" if live or one_time else "empty",
                                 "code": "SCHEDULER_RETRIEVED", "detail": "Task list retrieved"},
                   "health": health, "one_time": one_time, "parity_applicable": applicable,
                   "match": [], "drift": [], "canonical_only": [], "live_only": [],
                   "unscheduled": [], "prose_only": []}
        if applicable:
            payload.update({**result, "unscheduled": unscheduled,
                            "prose_only": prose_only})
        print(json.dumps(payload, indent=2))
    else:
        print(render_health(health, one_time))
        if applicable:
            print()
            print(render(result, unscheduled, prose_only, one_time, args.verbose))
        elif args.verbose:
            print("\n[OK] This campus doesn't keep canonical schedule files, so "
                  "there's nothing to compare them against. Not a problem.")

    # Stalled jobs are a real finding on ANY campus. Drift and never-registered
    # are real where the convention is in use. prose_only / live_only are
    # opportunities and never fail.
    failed = bool(health["stalled"]) or bool(
        applicable and (result["drift"] or result["canonical_only"])
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
