#!/usr/bin/env python3
"""
Kernel workforce scanner (Campus AI OS v4).

Reads the CANONICAL registry (.campus-os/registry.json) — it does NOT maintain a
second registry store. Walks the installed-plugin cache + the scheduled-tasks dir +
authored kernel skills, cross-references against the canonical registry, and writes a
regenerable snapshot to .campus-os/scan/latest.json (rotating the prior run to
previous.json). hr-review diffs latest vs previous.

Stdlib only. No network, no model call. Deterministic.

Usage:
  python3 scan_workforce.py --campus-root <dir> [--plugins-root <dir>]
Defaults: campus-root auto-detected by walking up for .campus-os/registry.json.
"""
import argparse, json, os, sys, datetime, shutil, glob

def find_up(start, needle):
    d = os.path.abspath(start)
    while True:
        if os.path.exists(os.path.join(d, needle)):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent

def detect_plugins_roots(campus_root):
    # ALL existing install-cache roots (walk up + home). A stale partial cache must
    # not shadow the real one, so we scan every root found and merge by name.
    cands = []
    d = campus_root
    while True:
        cands.append(os.path.join(d, ".remote-plugins"))
        p = os.path.dirname(d)
        if p == d: break
        d = p
    cands.append(os.path.expanduser("~/.remote-plugins"))
    # Host install-cache roots. Non-existent roots are dropped below, so listing
    # every known host is free. Without the Codex roots the scanner finds nothing
    # on that host and reports an empty workforce as if it were a clean one.
    cands.append(os.path.expanduser("~/.claude/plugins"))   # Claude
    # Codex. The docs describe ~/.codex/plugins + ~/.agents/plugins/marketplace.json,
    # but OBSERVED BEHAVIOUR puts the plugin at a BARE ~/plugins - twice, on two
    # different machines, once by hand (S217) and once by Codex's own installer
    # (2026-07-26, an earlier plugin install path). It was recorded here
    # as "non-canonical" on the first sighting; the second sighting settles it.
    # Observed beats documented - list it first.
    cands.append(os.path.expanduser("~/plugins"))            # Codex, OBSERVED (2x)
    cands.append(os.path.expanduser(
        os.path.join(os.environ.get("CODEX_HOME", "~/.codex"), "plugins")))  # documented
    cands.append(os.path.expanduser("~/.agents/plugins"))    # marketplace record
    seen, roots = set(), []
    for c in cands:
        rc = os.path.realpath(c)
        if os.path.isdir(c) and rc not in seen:
            seen.add(rc); roots.append(c)
    return roots

# Manifest probe order — MUST stay in lockstep with PLATFORM.md (kernel
# reference, plugin root). This script probed a list rather than a literal
# before the rest of the kernel did; PLATFORM.md generalises the pattern.
# Adding a host = adding one entry here AND one row in PLATFORM.md.
MANIFEST_CANDIDATES = (
    ".claude-plugin/plugin.json",      # Claude / Claude Code / Cowork  platform-literal-ok
    ".codex-plugin/plugin.json",       # Codex / OpenAI
    "plugin.json",                     # bare / unknown host
    ".agents/plugins/marketplace.json", # Codex marketplace record
    ".claude-plugin/marketplace.json",  # platform-literal-ok
    ".codex-plugin/marketplace.json",
)


def read_plugin_meta(plugin_dir):
    for rel in MANIFEST_CANDIDATES:
        p = os.path.join(plugin_dir, rel)
        if os.path.isfile(p):
            try:
                j = json.load(open(p))
                # plugin.json may be an object or a marketplace wrapper
                if isinstance(j, dict) and j.get("name"):
                    return j.get("name"), j.get("version", "unknown")
            except Exception:
                pass
    return None, None

def count_dir(plugin_dir, sub):
    p = os.path.join(plugin_dir, sub)
    if not os.path.isdir(p):
        return 0
    if sub == "skills":
        return sum(1 for e in os.listdir(p) if os.path.isdir(os.path.join(p, e)))
    if sub == "commands":
        return sum(1 for e in os.listdir(p) if e.endswith(".md"))
    return 0

def scan_plugins(plugins_roots):
    # Merge across all cache roots; a named entry wins, dedupe by name (else install_id).
    merged = {}
    for plugins_root in plugins_roots:
        if not plugins_root or not os.path.isdir(plugins_root):
            continue
        for entry in sorted(os.listdir(plugins_root)):
            pdir = os.path.join(plugins_root, entry)
            if not os.path.isdir(pdir):
                continue
            name, version = read_plugin_meta(pdir)
            rec = {
                "install_id": entry,
                "name": name or entry,
                "version": version or "unknown",
                "skills": count_dir(pdir, "skills"),
                "commands": count_dir(pdir, "commands"),
                "named": bool(name),
            }
            key = name if name else entry
            prev = merged.get(key)
            # prefer the named / richer record
            if prev is None or (not prev["named"] and rec["named"]) or rec["skills"] > prev["skills"]:
                merged[key] = rec
    return [merged[k] for k in sorted(merged)]

def scan_scheduled(campus_root):
    out = []
    sdir = os.path.join(campus_root, "scheduled")
    if not os.path.isdir(sdir):
        return out
    for f in sorted(os.listdir(sdir)):
        if not f.endswith(".md") or f.lower() == "readme.md":
            continue
        path = os.path.join(sdir, f)
        title = f[:-3]
        cadence = None
        status = "active"
        try:
            for ln in open(path, encoding="utf-8", errors="ignore").read().splitlines()[:40]:
                low = ln.lower()
                if title == f[:-3] and ln.startswith("# "):
                    title = ln[2:].strip()
                if "cadence:" in low and not cadence:
                    cadence = ln.split(":", 1)[1].strip()
                if any(w in low for w in ("disabled", "paused", "stale", "retired")):
                    status = "flagged"
        except Exception:
            pass
        out.append({"file": f, "title": title, "cadence": cadence, "status": status})
    return out

def scan_authored_skills(campus_root):
    out = []
    adir = os.path.join(campus_root, "library", "skills")
    if not os.path.isdir(adir):
        return out
    for e in sorted(os.listdir(adir)):
        if os.path.isfile(os.path.join(adir, e, "SKILL.md")):
            out.append(e)
    return out

def scan_hires(campus_root):
    # Hires are contractors from .campus-os/hires/*.json (schema: dean/tasks/hire-registry-phase1.md,
    # .campus-os/hires/README.md). A manifest is identified by having a top-level "hire" key — this
    # excludes _scanner.json (a tool card for the security scanner itself, not a hire) and any future
    # non-manifest file in the folder without guessing filenames.
    out = []
    hdir = os.path.join(campus_root, ".campus-os", "hires")
    if not os.path.isdir(hdir):
        return out
    for f in sorted(os.listdir(hdir)):
        if not f.endswith(".json"):
            continue
        path = os.path.join(hdir, f)
        try:
            m = json.load(open(path, encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(m, dict) or "hire" not in m:
            continue
        scan = m.get("scan") or {}
        out.append({
            "hire": m.get("hire"),
            "kind": m.get("kind"),
            "repo": m.get("repo"),
            "pin7": (m.get("pin") or "")[:7],
            "trust_tier": m.get("trust_tier"),
            "owns": m.get("owns"),
            "triggers": m.get("triggers", []),
            "scan_verdict": scan.get("verdict"),
            "created": m.get("created"),
            "manifest": os.path.relpath(path, campus_root),
        })
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--campus-root", default=None)
    ap.add_argument("--plugins-root", default=None)
    args = ap.parse_args()

    campus_root = args.campus_root or find_up(os.getcwd(), ".campus-os/registry.json")
    if not campus_root:
        print("ERROR: could not locate .campus-os/registry.json (pass --campus-root)", file=sys.stderr)
        sys.exit(2)
    campus_root = os.path.abspath(campus_root)   # absolutize so plugin-cache walk-up is correct
    reg_path = os.path.join(campus_root, ".campus-os", "registry.json")
    reg = json.load(open(reg_path))
    teams = reg.get("teams", [])
    playbooks = reg.get("playbooks", [])
    registered_names = set()
    for t in teams:
        n = t.get("team") or t.get("name")
        if n: registered_names.add(n)
    active_registered = set(t.get("team") or t.get("name") for t in teams
                            if t.get("status") not in ("retired", "disabled"))

    plugins_roots = [args.plugins_root] if args.plugins_root else detect_plugins_roots(campus_root)
    plugins = scan_plugins(plugins_roots)
    scheduled = scan_scheduled(campus_root)
    authored = scan_authored_skills(campus_root)
    hires = scan_hires(campus_root)

    installed_named = set(p["name"] for p in plugins if p["named"])
    # teams that don't live in the plugin cache by design: authored/kernel + department managers
    non_plugin_types = {"authored-skill", "kernel"}
    non_plugin_teams = set(
        (t.get("team") or t.get("name")) for t in teams
        if t.get("type") in non_plugin_types or t.get("status") in ("legacy", "retired", "disabled")
    )
    # version drift: registry version != installed version (both known)
    installed_ver = {p["name"]: p["version"] for p in plugins if p["named"]}
    version_drift = []
    for t in teams:
        n = t.get("team") or t.get("name")
        rv = t.get("version")
        iv = installed_ver.get(n)
        if n and iv and rv and rv not in ("unknown",) and iv not in ("unknown",) and rv != iv:
            version_drift.append({"team": n, "registry": rv, "installed": iv})
    # cross-reference flags (names only — hr-review turns these into recommendations)
    unregistered_installed = sorted(n for n in installed_named if n not in registered_names)
    registered_not_installed = sorted(
        n for n in active_registered
        if n and n not in installed_named
        and n not in ("dean", "campus-ai-os")            # kernel platform entries
        and n not in set(authored)                        # authored kernel skills
        and n not in non_plugin_teams                     # authored/legacy/retired by type
    )

    snap = {
        "schema_version": "1.0",
        "kind": "workforce-scan",
        "generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "campus_root": os.path.abspath(campus_root),
        "plugins_roots": [os.path.abspath(r) for r in plugins_roots if r and os.path.isdir(r)],
        "counts": {
            "installed_plugins": len(plugins),
            "installed_named": len(installed_named),
            "registered_teams": len(teams),
            "registered_playbooks": len(playbooks),
            "authored_kernel_skills": len(authored),
            "scheduled_tasks": len(scheduled),
            "hires": len(hires),
        },
        "installed_plugins": plugins,
        "authored_kernel_skills": authored,
        "scheduled_tasks": scheduled,
        "hires": hires,
        "cross_reference": {
            "unregistered_installed": unregistered_installed,
            "registered_not_installed": registered_not_installed,
            "version_drift": version_drift,
            "scheduled_flagged": [s["file"] for s in scheduled if s["status"] == "flagged"],
            "hires_unclear": [h["hire"] for h in hires if h["scan_verdict"] != "clear"],
        },
        "note": "Regenerable snapshot. Canonical registry stays .campus-os/registry.json — this is NOT a second store. Hires are contractors (.campus-os/hires/), reported separately from installed_plugins — they are never installed into the campus (see .campus-os/hires/README.md).",
    }

    scan_dir = os.path.join(campus_root, ".campus-os", "scan")
    os.makedirs(scan_dir, exist_ok=True)
    latest = os.path.join(scan_dir, "latest.json")
    prev = os.path.join(scan_dir, "previous.json")
    if os.path.exists(latest):
        shutil.copy2(latest, prev)  # rotate
    json.dump(snap, open(latest, "w"), indent=2)

    c = snap["counts"]
    print("scan written:", latest)
    print("rotated previous:", os.path.exists(prev))
    print("installed_plugins={installed_plugins} named={installed_named} teams={registered_teams} "
          "playbooks={registered_playbooks} authored={authored_kernel_skills} scheduled={scheduled_tasks} "
          "hires={hires}".format(**c, authored=c["authored_kernel_skills"]))
    print("unregistered_installed:", unregistered_installed or "none")
    print("registered_not_installed:", registered_not_installed or "none")
    print("hires_unclear:", snap["cross_reference"]["hires_unclear"] or "none")

if __name__ == "__main__":
    main()
