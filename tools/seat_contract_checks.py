#!/usr/bin/env python3
"""
seat_contract_checks.py  -  the three Seat Contract health checks (Phase 2)

Backs campus-doctor check 11. Three findings, all derived from files alone -
no git, no scheduler, no host API, so it behaves identically on every transport
and every client.

  11a  FOREIGN WRITE   a seat wrote outside its lane, into primary-owned state
  11b  MISSING STAMP   a new-format ledger line carries no `seat`
  11c  SYNC HAZARD     conflicted copies, git inside a sync root, cloud
                       eviction placeholders
  11d  HOST BINDING    .campus-os/host-binding.json (5.2.4): absent is fine;
                       present must be fresh, well-formed, and issued for the
                       configured primary client. Reports hours to expiry so
                       a lapsed heartbeat is one doctor line, not a week of
                       blocked scheduled runs.

WHY THESE THREE
---------------
The Seat Contract's whole claim is that a second writer on one campus folder is
safe. Each check is the failure mode of one of its three load-bearing rules:
lanes (a), stamps (b), and transport safety (c). A rule with no check is a wish.

WHAT IT NEVER DOES
------------------
It changes nothing. Every finding is a report the owner acts on. A campus with
one seat and no sync folder produces zero findings and says so in one line -
having a single seat is not a defect, and this check must never nag a
perfectly healthy solo campus toward machinery it does not need.

Usage:
  python3 tools/seat_contract_checks.py --campus-root . [--json] [--verbose]
Exit 0 = no findings that need a decision. Exit 1 = at least one [!!].
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Primary-owned state: the files exactly one seat may write (the primary).
# This list is the machine-readable owner of the rule that AGENTS.md states in
# prose for humans. Keep them in step: prose that no code checks is how the
# lane rules shipped as 613 bytes of pointers for four months.
PRIMARY_OWNED = [
    "dean/memory.md",
    "dean/TASKS.md",
    "dean/tasks/",
    "wiki/",
    "shared/",
    ".campus-os/registry.json",
]
# A manager's own two files. The entry filename is host-specific (Claude reads
# CLAUDE.md, Codex reads AGENTS.md / AGENTS.override.md, CODEX.md is a legacy
# alias) so this READS permissively across the whole family - the same rule
# campus-doctor check 2a learned the expensive way when it hardcoded one name
# and reported a correct Codex campus as broken. Nothing here WRITES a file, so
# there is no exact-write counterpart to resolve.
MANAGER_ENTRY_NAMES = ("CLAUDE.md", "AGENTS.md", "AGENTS.override.md", "CODEX.md")
# Host binding (5.2.4): the file a host-observed process issues so a sandboxed
# session of the configured primary client can resolve primary. These literals
# are the machine home of the rule; build_contract.py copies them into
# contracts/campus.json and resolve-seat.py enforces the same numbers.
HOST_BINDING_FILE = ".campus-os/host-binding.json"
HOST_BINDING_SCHEMA = 1
HOST_BINDING_TTL_MAX_HOURS = 24
HOST_BINDING_VIA = ("observed", "host-binding", "unresolved")
MANAGER_OWNED_SUFFIX = tuple("/" + n for n in MANAGER_ENTRY_NAMES) + ("/memory.md",)

# Directories never worth walking. `active-work/lanes/` is deliberately NOT
# skipped - a lane is exactly where satellite work is supposed to be, and 11a
# needs to see it to tell inside-lane from outside-lane.
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", ".pytest_cache",
    ".DS_Store", "archive", "backups",
}

SYNC_ROOT_MARKERS = (
    "dropbox", "google drive", "googledrive", "my drive", "onedrive",
    "icloud drive", "com~apple~clouddocs",
)

# Names a sync service creates when it CANNOT merge two edits. Every pattern
# here must be unique to that event.
#
# Two patterns were cut after the false-positive guard run (S272): `.~lock.*`
# (LibreOffice's local editor lock - five of them on the unmodified campus, all
# from the owner opening spreadsheets, none a sync conflict) and `.sb-*`
# (Dropbox's in-flight partial write, which resolves itself). Both would have
# reported a healthy campus as corrupted on the first run. A hazard check that
# fires on ordinary desktop litter teaches the owner to ignore it, and then it
# is worth less than no check at all.
CONFLICT_PATTERNS = [
    re.compile(r"conflicted copy", re.I),          # Dropbox
    re.compile(r"\(conflict(ed)?\)", re.I),        # Drive / Box
    re.compile(r"-conflict-\d", re.I),
    re.compile(r"\(case conflict\)", re.I),
]
FM_SEAT = re.compile(r"^seat:\s*[\"']?([A-Za-z0-9_.-]+)[\"']?\s*$", re.M)


def read_seat(root: Path):
    """Read-only validation; missing identity never establishes ownership."""
    p = root / ".campus-os" / "seat.json"
    try:
        info = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"status": "missing", "code": "SEAT_MISSING", "value": None}
    except (OSError, ValueError) as e:
        return {"status": "invalid", "code": "SEAT_INVALID", "value": None,
                "detail": str(e)}
    if (not isinstance(info, dict) or
        not isinstance(info.get("seat"), str) or
        not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", info["seat"]) or
        info.get("role") not in ("primary", "satellite")):
        return {"status": "invalid", "code": "SEAT_INVALID", "value": None}
    return {"status": "valid", "code": "SEAT_VALID", "value": info}


def ledger_files(root: Path):
    """Primary ledger first, then every satellite shard. Canon: ledger-paths.md."""
    dean = root / "dean"
    out = []
    primary = dean / ".activity.jsonl"
    if primary.is_file():
        out.append(primary)
    if dean.is_dir():
        for f in sorted(os.listdir(dean)):
            if f.startswith(".activity.") and f.endswith(".jsonl") and f != ".activity.jsonl":
                out.append(dean / f)
    return out


def shard_seat(path: Path):
    n = path.name
    if n == ".activity.jsonl":
        return None
    return n[len(".activity."):-len(".jsonl")]


def iter_ledger_lines(path: Path):
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as e:
        yield 0, {"_ledger_error": str(e)}
        return
    for i, raw in enumerate(text.split("\n"), 1):
        ln = raw.strip()
        if not ln or ln.startswith("#"):
            continue
        try:
            obj = json.loads(ln)
            if not isinstance(obj, dict):
                raise ValueError("ledger record must be an object")
            yield i, obj
        except ValueError as e:
            yield i, {"_ledger_error": str(e)}


def walk(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".campus-os/scan")]
        for fn in filenames:
            yield Path(dirpath) / fn


# ---------------------------------------------------------------------------
# 11a - foreign write outside a seat's lane
def check_foreign_writes(root: Path, seat_info):
    """Different stamps require historical ownership evidence. Current identity
    alone cannot prove an unauthorized write; report attribution as unresolved."""
    primary_seat = None
    if seat_info and seat_info.get("role") == "primary":
        primary_seat = seat_info.get("seat")

    # Co-primary: every seat configured `primary` on this installation may legitimately write
    # shared state, so a stamp matching any of them is expected, not unresolved attribution.
    # On a single-primary campus this set is just {primary_seat} and behaviour is unchanged.
    allowed_seats = {primary_seat} if primary_seat else set()
    try:
        cfg = json.loads((root / ".campus-os" / "seat.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cfg = None
    clients = cfg.get("clients") if isinstance(cfg, dict) else None
    if isinstance(clients, dict):
        for v in clients.values():
            if isinstance(v, dict) and v.get("role") == "primary" and isinstance(v.get("seat"), str):
                allowed_seats.add(v["seat"])

    findings = []
    unresolved = []

    # (i) foreign lines inside the primary's own ledger file
    primary_ledger = root / "dean" / ".activity.jsonl"
    if primary_ledger.is_file() and primary_seat:
        for lineno, obj in iter_ledger_lines(primary_ledger):
            s = obj.get("seat")
            if s and s not in allowed_seats:
                unresolved.append({
                    "code": "OWNERSHIP_HISTORY_UNKNOWN",
                    "kind": "ledger",
                    "seat": s,
                    "path": "dean/.activity.jsonl",
                    "line": lineno,
                    "why": f"stamp '{s}' differs from today's primary; ownership at write time "
                           "is unknown. Preserve history; review attribution.",
                })

    # (ii) records stamped with a non-primary seat, sitting in primary-owned state
    for f in walk(root):
        try:
            rel = f.relative_to(root).as_posix()
        except ValueError:
            continue
        if f.suffix.lower() != ".md":
            continue
        owned = any(rel == p or rel.startswith(p) for p in PRIMARY_OWNED) or (
            rel.count("/") == 1 and rel.endswith(MANAGER_OWNED_SUFFIX)
        )
        if not owned:
            continue
        try:
            head = f.read_text(encoding="utf-8", errors="ignore")[:2000]
        except Exception:
            continue
        m = FM_SEAT.search(head)
        if m and primary_seat and m.group(1) not in allowed_seats:
            unresolved.append({
                "code": "OWNERSHIP_HISTORY_UNKNOWN",
                "kind": "record",
                "seat": m.group(1),
                "path": rel,
                "line": None,
                "why": f"record stamp '{m.group(1)}' differs from today's primary; "
                       "authorship does not establish unauthorized placement. Preserve and review.",
            })

    # (iii) informational: lanes belonging to seats with no ledger shard
    lanes_dir = root / "active-work" / "lanes"
    known = {shard_seat(p) for p in ledger_files(root)} - {None}
    known |= allowed_seats
    unknown_lanes = []
    if lanes_dir.is_dir():
        for d in sorted(os.listdir(lanes_dir)):
            if (lanes_dir / d).is_dir() and not d.startswith(".") and d not in known:
                unknown_lanes.append(d)

    return {"foreign": findings, "unresolved": unresolved,
            "status": "unresolved" if not primary_seat or unresolved else "complete",
            "unknown_lanes": unknown_lanes,
            "primary_seat": primary_seat, "seat_declared": seat_info is not None}


# ---------------------------------------------------------------------------
# 11b - missing seat stamp on a NEW-FORMAT ledger line
def check_seat_stamps(root: Path):
    """Self-anchoring: a file declares its own adoption point. Once ANY line in
    a file carries `seat`, every LATER line in that file must too. Lines before
    the first stamp are legacy and are never flagged - the ledger is
    append-only and is never retro-edited, so a date-based rule would either
    need a config nobody maintains or would condemn correct history."""
    findings = []
    scanned = 0
    errors = []
    for path in ledger_files(root):
        rel = path.relative_to(root).as_posix()
        sseat = shard_seat(path)
        adopted = sseat is not None   # a shard only exists post-Phase-2: stamps required from line 1
        for lineno, obj in iter_ledger_lines(path):
            if "_ledger_error" in obj:
                errors.append({"code": "LEDGER_INVALID", "path": rel, "line": lineno,
                               "detail": obj["_ledger_error"]})
                continue
            scanned += 1
            has = bool(obj.get("seat"))
            if has:
                adopted = True
                if sseat and obj["seat"] != sseat:
                    findings.append({"path": rel, "line": lineno, "kind": "wrong_seat",
                                     "why": f"line says seat '{obj['seat']}' but the file is "
                                            f"seat '{sseat}'s shard"})
            elif adopted:
                findings.append({"path": rel, "line": lineno, "kind": "missing_seat",
                                 "why": "line written after this file adopted seat stamps, "
                                        "but carries no `seat`"})
    return {"findings": findings, "lines_scanned": scanned, "errors": errors}


# ---------------------------------------------------------------------------
# 11c - sync hazards
def check_sync_hazards(root: Path):
    conflicted, placeholders = [], []
    for f in walk(root):
        name = f.name
        rel = f.relative_to(root).as_posix()
        if any(p.search(name) for p in CONFLICT_PATTERNS):
            conflicted.append(rel)
        elif name.startswith(".") and name.endswith(".icloud"):
            placeholders.append(rel)

    # git repo living inside a cloud-sync root: the two systems fight over
    # .git internals and the loser is the object store.
    lowered = str(root.resolve()).lower()
    in_sync_root = next((m for m in SYNC_ROOT_MARKERS if m in lowered), None)
    git_here = (root / ".git").exists()
    if not git_here:
        for parent in root.resolve().parents:
            if (parent / ".git").exists():
                git_here = True
                break
    return {"conflicted": sorted(conflicted)[:20], "conflicted_total": len(conflicted),
            "placeholders": sorted(placeholders)[:20], "placeholders_total": len(placeholders),
            "sync_root_marker": in_sync_root, "git_present": git_here,
            "git_in_sync_root": bool(in_sync_root and git_here)}


# ---------------------------------------------------------------------------
# 11d - host binding freshness
def check_host_binding(root: Path, now=None):
    """Read-only. `absent` is the ordinary state (solo campus, or a primary that
    observes its own fingerprint). Anything present is held to the resolver's
    rules so the doctor and the resolver can never disagree about one file."""
    import datetime as dt
    now = now or dt.datetime.now(dt.timezone.utc)
    path = root / HOST_BINDING_FILE
    if not path.is_file():
        return {"status": "absent", "path": HOST_BINDING_FILE}
    try:
        b = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return {"status": "invalid", "path": HOST_BINDING_FILE, "why": f"unreadable: {e}"}
    seat_cfg = None
    try:
        seat_cfg = json.loads((root / ".campus-os" / "seat.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    clients = seat_cfg.get("clients") if isinstance(seat_cfg, dict) else None
    # Co-primary: several clients may be primary, so the binding holder is named by clock_owner.
    # Fall back to the sole primary so a pre-co-primary seat.json is judged exactly as before.
    owner = seat_cfg.get("clock_owner") if isinstance(seat_cfg, dict) else None
    primaries = [k for k, v in (clients or {}).items() if isinstance(v, dict) and v.get("role") == "primary"]
    if isinstance(owner, str) and owner in primaries:
        primary = owner
    else:
        primary = primaries[0] if len(primaries) == 1 else None

    def parse(v):
        try:
            t = dt.datetime.fromisoformat(str(v).replace("Z", "+00:00"))
            return t if t.tzinfo else None
        except ValueError:
            return None
    out = {"status": "invalid", "path": HOST_BINDING_FILE, "client": b.get("client") if isinstance(b, dict) else None}
    if not isinstance(b, dict) or b.get("schema_version") != HOST_BINDING_SCHEMA:
        out["why"] = "unsupported schema"; return out
    if primary is None or b.get("client") != primary:
        out["why"] = f"issued for '{b.get('client')}', which is not the clock owner"; return out
    if not isinstance(seat_cfg, dict) or b.get("machine_id") != seat_cfg.get("machine_id"):
        out["why"] = "machine_id does not match seat.json"; return out
    issued, expires = parse(b.get("issued_at")), parse(b.get("expires_at"))
    if not issued or not expires:
        out["why"] = "timestamps malformed"; return out
    if issued > now + dt.timedelta(minutes=5):
        out["why"] = "issued in the future"; return out
    if expires - issued > dt.timedelta(hours=HOST_BINDING_TTL_MAX_HOURS, minutes=5):
        out["why"] = f"lifetime exceeds {HOST_BINDING_TTL_MAX_HOURS} hours"; return out
    hours = round((expires - now).total_seconds() / 3600, 1)
    out.update(issued_at=b.get("issued_at"), expires_at=b.get("expires_at"), issued_by=b.get("issued_by"), hours_to_expiry=hours)
    out["status"] = "expired" if expires <= now else "fresh"
    if out["status"] == "expired":
        out["why"] = f"expired {abs(hours)}h ago - the host heartbeat has not re-issued it"
    return out


# ---------------------------------------------------------------------------
def render(a, b, c, verbose=False, seat_info=None, d=None):
    lines = []

    # 11a
    seat_status = (seat_info or {}).get("status")
    if seat_status == "missing":
        lines.append("[--] Seat identity not declared (.campus-os/seat.json absent) - ownership "
                     "can't be verified. Fine on a single machine; declare it before a second "
                     "client or machine shares this folder.")
    elif seat_status == "invalid":
        lines.append("[!!] Seat identity invalid (.campus-os/seat.json: "
                     f"{(seat_info or {}).get('detail') or 'wrong shape - needs a string seat and a role of primary or satellite'}) "
                     "- ownership can't be verified until it is repaired.")
    elif a["status"] == "unresolved" and not a["primary_seat"]:
        lines.append("[!!] This campus's declared seat is a satellite; ownership verification "
                     "needs the primary seat's identity. Nothing is proven either way.")
    elif a["status"] == "unresolved":
        u = a["unresolved"]
        where = f" - e.g. {u[0]['path']}" + (f" line {u[0]['line']}" if u[0].get("line") else "")
        lines.append(f"[!!] Ownership check incomplete: {len(u)} record(s) carry a seat stamp that "
                     f"differs from today's primary ('{a['primary_seat']}'){where}. History is "
                     "preserved; attribution is unresolved, not a violation.")
    elif a["foreign"]:
        by_seat = {}
        for f in a["foreign"]:
            by_seat.setdefault(f["seat"], []).append(f)
        for s, items in sorted(by_seat.items()):
            lines.append(f"[!!] {len(items)} write(s) from seat '{s}' landed outside its lane "
                         f"- e.g. {items[0]['path']}. Move them into "
                         f"active-work/lanes/{s}/ as proposals for the primary seat to merge.")
    else:
        lines.append("[OK] Every seat wrote inside its own lane")
    for lane in a["unknown_lanes"]:
        lines.append(f"[--] Lane 'active-work/lanes/{lane}/' belongs to a seat this campus "
                     f"doesn't know about - add it or archive the lane")

    # 11b
    miss = [f for f in b["findings"] if f["kind"] == "missing_seat"]
    wrong = [f for f in b["findings"] if f["kind"] == "wrong_seat"]
    if miss:
        lines.append(f"[!!] {len(miss)} work-diary line(s) don't say which seat wrote them "
                     f"- e.g. {miss[0]['path']} line {miss[0]['line']}")
    if wrong:
        lines.append(f"[!!] {len(wrong)} work-diary line(s) are filed under the wrong seat "
                     f"- e.g. {wrong[0]['path']} line {wrong[0]['line']}")
    if b["errors"]:
        lines.append(f"[!!] {len(b['errors'])} unreadable or invalid ledger record(s); diary check incomplete")
    if not b["findings"] and not b["errors"] and b["lines_scanned"]:
        lines.append(f"[OK] Work diary consistent ({b['lines_scanned']} entries)")

    # 11c
    if c["conflicted_total"]:
        lines.append(f"[!!] {c['conflicted_total']} conflicted copy file(s) - your sync service "
                     f"couldn't merge two edits, so a change may be sitting in a duplicate "
                     f"instead of the real file. e.g. {c['conflicted'][0]}")
    if c["placeholders_total"]:
        lines.append(f"[!!] {c['placeholders_total']} file(s) have been evicted to the cloud and "
                     f"aren't really here - Claude will read them as missing. e.g. "
                     f"{c['placeholders'][0]}")
    if c["git_in_sync_root"]:
        lines.append(f"[!!] This campus is version-controlled AND inside a "
                     f"{c['sync_root_marker']} folder. Both want to manage the same files; "
                     f"pick one - move the campus out of the sync folder, or stop syncing it.")
    if not (c["conflicted_total"] or c["placeholders_total"] or c["git_in_sync_root"]):
        lines.append("[OK] No sync hazards")

    # 11d
    if d and d["status"] == "fresh":
        lines.append(f"[OK] Host binding fresh for '{d['client']}' - {d['hours_to_expiry']}h to expiry "
                     f"(issued by {d.get('issued_by') or 'unknown'})")
    elif d and d["status"] == "expired":
        lines.append(f"[!!] Host binding for '{d['client']}' {d['why']}. Sandboxed sessions of the "
                     f"primary client are satellites until it is re-issued: run "
                     f"`python3 .campus-os/resolve-seat.py --issue-binding --client {d['client']}` on the host.")
    elif d and d["status"] == "invalid":
        lines.append(f"[!!] Host binding unusable ({d['why']}) - delete {d['path']} and re-issue it from the host.")

    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--campus-root", default=".")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    root = Path(args.campus_root).resolve()
    if not root.is_dir():
        result = {"seat_resolution": {"status": "invalid", "code": "CAMPUS_MISSING"}}
        print(json.dumps(result) if args.json else f"ERROR: campus root not found: {root}")
        return 2

    seat_info = read_seat(root)
    a = check_foreign_writes(root, seat_info["value"])
    b = check_seat_stamps(root)
    c = check_sync_hazards(root)
    d = check_host_binding(root)

    if args.json:
        print(json.dumps({"seat_resolution": seat_info, "foreign_writes": a, "seat_stamps": b, "sync_hazards": c,
                          "host_binding": d}, indent=2))
    else:
        print(render(a, b, c, args.verbose, seat_info, d))

    failed = seat_info["status"] != "valid" or a["status"] != "complete" or bool(b["errors"]) or bool(a["foreign"]) or bool(b["findings"]) or bool(
        c["conflicted_total"] or c["placeholders_total"] or c["git_in_sync_root"]) or d["status"] in ("expired", "invalid")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
