#!/usr/bin/env python3
"""
hr-review diff (Campus AI OS v4, kernel).

Diffs two workforce scans (.campus-os/scan/latest.json vs previous.json) and emits a
flag-only markdown report: added/removed installs, version drift, unregistered installs,
registered-but-absent plugins, flagged schedules, and weak/off-spec registry entries
(teams with no done_check; playbooks with no done_check). Recommends an action per item —
never acts. Stdlib only, deterministic.

Usage: python3 diff_scan.py --campus-root <dir> [--out-md <file>]
"""
import argparse, json, os, datetime

def load(p):
    try: return json.load(open(p))
    except Exception: return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--campus-root", default=".")
    ap.add_argument("--out-md", default=None)
    args = ap.parse_args()
    root = os.path.abspath(args.campus_root)
    latest = load(os.path.join(root, ".campus-os/scan/latest.json"))
    prev = load(os.path.join(root, ".campus-os/scan/previous.json"))
    reg = load(os.path.join(root, ".campus-os/registry.json")) or {}
    if not latest:
        print("ERROR: no latest scan — run hr-registry first."); raise SystemExit(2)

    def names(scan):
        return set(p["name"] for p in scan.get("installed_plugins", []) if p.get("named")) if scan else set()
    cur, old = names(latest), names(prev)
    added = sorted(cur - old) if prev else []
    removed = sorted(old - cur) if prev else []

    teams = reg.get("teams", [])
    playbooks = reg.get("playbooks", [])

    # ---- DIRECTORY RECORDS ARE NOT PLUGINS (v5.0.5, payload item 4) ----------
    # `type: department` / `type: systems` / `type: kernel` entries are DIRECTORY
    # records — the org chart and the campus's own core. They are not team
    # plugins, so they can never be "installed", and they are not specs, so they
    # carry no done_check. campus-doctor already knows this (six references);
    # hr-review had zero. Same registry, two readings — one shared fact with no
    # single reader, which is the defect class this release is built against.
    #
    # Measured on a fresh clients campus (2026-07-26): 25 flags, of which 12
    # were these six records double-counted (5 departments + campus-systems,
    # each hit by registered-but-absent AND weak-no-done_check). 25 -> 13.
    # A buyer's day-one review read as a defect list when nothing was wrong.
    #
    # NOTE: departments legitimately gain a done_check when the Manager Layer
    # ships (payload item 1) — that closes the same half honestly. This
    # exemption stops the false alarm; item 1 supplies the real contract.
    DIRECTORY_TYPES = {"department", "systems", "kernel"}
    directory_names = {
        (t.get("team") or t.get("name"))
        for t in teams if t.get("type") in DIRECTORY_TYPES
    }
    directory_names.discard(None)

    # ---- RETIRED STATUS: RECLASSIFY, DO NOT SILENCE (v5.1.1) ----------------
    # The defect this fixes: `absent` was built WITHOUT consulting status, while
    # the remediation printed under it said "mark status if retired". So the
    # product told the owner to fix it by marking status, and the filter that
    # produced the flag never read status. Reproduced live — an entry was set to
    # `disabled`, verified written, and still appeared in the next run.
    #
    # That is worse than a silent wrong answer. A quiet wrong answer costs
    # nothing until it matters; this one SPENDS TRUST — the owner follows the
    # printed instruction, sees no change, and concludes either the tool is
    # broken or they did it wrong. Both are corrosive and neither is true.
    #
    # The design question underneath was: is registered-but-absent a FACT (the
    # code's view — true regardless of status) or a CHORE (the remediation
    # string's view — closable by marking status)? Both cannot be right.
    #
    # Resolution: RECLASSIFY, DO NOT SILENCE. An entry the owner has explicitly
    # marked stays a fact, but moves out of the red list into a quiet count
    # line. That keeps the fact and removes the chore — the campus's own
    # precedent, from item 4 (framing, not suppression) and item 6 (silence is
    # not the safe default for a health check) pointing the same direction.
    RETIRED_STATUSES = ("retired", "legacy", "disabled")

    def _name(a):
        return a.get("team") if isinstance(a, dict) else a

    status_by_name = {(t.get("team") or t.get("name")): t.get("status") for t in teams}

    xr = latest.get("cross_reference", {})
    unreg = xr.get("unregistered_installed", [])
    # A directory record is not an install — never report it as missing.
    _absent_all = [a for a in xr.get("registered_not_installed", [])
                   if _name(a) not in directory_names]
    # Explicitly-marked entries are still absent; they are just not a chore.
    absent = [a for a in _absent_all
              if status_by_name.get(_name(a)) not in RETIRED_STATUSES]
    absent_retired = [a for a in _absent_all
                      if status_by_name.get(_name(a)) in RETIRED_STATUSES]
    drift = xr.get("version_drift", [])
    sched_flagged = xr.get("scheduled_flagged", [])

    # weak/off-spec registry entries (quality flags — hr-review's domain)
    weak_teams = [ (t.get("team") or t.get("name")) for t in teams
                   if t.get("status") not in RETIRED_STATUSES
                   and t.get("type") not in DIRECTORY_TYPES
                   and not t.get("done_check") ]
    weak_playbooks = [ p.get("playbook") for p in playbooks if not p.get("done_check") ]

    total_flags = len(added)+len(removed)+len(unreg)+len(absent)+len(drift)+len(sched_flagged)+len(weak_teams)+len(weak_playbooks)

    L = []
    L.append(f"# HR Review — Workforce Flags")
    L.append("")
    L.append(f"*Generated {datetime.datetime.now().astimezone().isoformat(timespec='seconds')} · flag-only, nothing changed · {total_flags} item(s) flagged*")
    L.append("")
    c = latest.get("counts", {})
    L.append(f"**Roster:** {c.get('registered_teams','?')} teams · {c.get('registered_playbooks','?')} playbooks · "
             f"{c.get('authored_kernel_skills','?')} authored kernel skills · {c.get('installed_named','?')} installed plugins · "
             f"{c.get('scheduled_tasks','?')} scheduled tasks")
    L.append("")
    if not prev:
        L.append("_First review — no previous scan to diff against. Deltas will appear next run._")
        L.append("")

    def section(title, items, rec):
        L.append(f"## {title}  ({len(items)})")
        if not items:
            L.append("- none"); L.append(""); return
        for it in items:
            L.append(f"- {it}")
        L.append(f"  - **Recommended:** {rec}")
        L.append("")

    if prev:
        section("Newly installed since last scan", added, "confirm intended; register in .campus-os/registry.json if it's a team.")
        section("Disappeared since last scan", removed, "confirm intended uninstall; retire its registry entry (owner edits status).")
    section("Installed but UNregistered", unreg, "owner decides: register it (add a teams[] entry) or ignore if intentional.")
    section("Registered but not in the install cache", absent,
            "owner checks: stale registry entry, or installed in a different cache — "
            "mark status `retired`, `legacy`, or `disabled` and it moves to the "
            "intentionally-retired line below (the flag is a fact, not a chore).")
    # Reclassified, not silenced: the fact stays visible, the chore is gone.
    if absent_retired:
        L.append(f"_{len(absent_retired)} more registered entr"
                 f"{'y is' if len(absent_retired) == 1 else 'ies are'} not installed "
                 f"but explicitly marked retired/legacy/disabled — "
                 f"{', '.join(str(_name(a)) for a in absent_retired)}. "
                 f"Recorded, not flagged; nothing to do._")
        L.append("")
    section("Version drift (registry vs installed)", [f"{d['team']}: registry {d['registry']} vs installed {d['installed']}" for d in drift],
            "owner bumps the registry entry's version to match the installed plugin on its next touch.")
    section("Flagged scheduled tasks", sched_flagged, "owner reviews the task file — paused/stale tasks should be retired or re-enabled.")
    section("Weak registry entries (no done_check)", weak_teams + [f"playbook:{p}" for p in weak_playbooks],
            "add a done_check so the team/playbook isn't a weak spec (hr-review keeps flagging until present).")

    L.append("---")
    L.append("*HR proposes; the owner disposes. No entry here was acted on. Approve items individually to route a fix.*")
    md = "\n".join(L)
    if args.out_md:
        os.makedirs(os.path.dirname(args.out_md), exist_ok=True)
        open(args.out_md, "w").write(md)
        print("report written:", args.out_md)
    print(f"total_flags={total_flags} added={len(added)} removed={len(removed)} unreg={len(unreg)} "
          f"absent={len(absent)} drift={len(drift)} sched_flagged={len(sched_flagged)} "
          f"weak_teams={len(weak_teams)} weak_playbooks={len(weak_playbooks)}")

if __name__ == "__main__":
    main()
