#!/usr/bin/env python3
"""
hr-recruit clusterer (Campus AI OS v4, kernel).

Reads every campus activity ledger (the primary dean/.activity.jsonl plus any satellite
shard dean/.activity.{seat}.jsonl - Seat Contract Phase 2), filters to recent ad-hoc completed
workflows, clusters them by trigger-keyword overlap, dedupes against installed employees
(canonical registry + scan) and rejected candidates, and prints proposed skill candidates as
JSON. Flag-only: it PROPOSES; it never authors a skill. Stdlib only, deterministic.

Usage: python3 cluster_ledger.py --campus-root <dir> [--days 30] [--min-cluster 3]
Prints a JSON object: {window_count, candidates:[...], existing_should_have_fired:[...]}
"""
import argparse, json, os, re, datetime

STOP = set("the a an of to for and or with this that my your me i we run write build make "
           "create update check draft into from on in at is are be as it its our".split())

def toks(s):
    return set(w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if w not in STOP and len(w) > 2)

def jaccard(a, b):
    if not a or not b: return 0.0
    return len(a & b) / len(a | b)

def ledger_files(root):
    """Every activity-ledger file on the campus, primary first.

    Seat Contract Phase 2: the primary seat writes `dean/.activity.jsonl`
    (unchanged, forever); satellite seats write `dean/.activity.{seat}.jsonl`.
    Reading is permissive - merge every shard present - which is what makes the
    shard split invisible to everything downstream. Canon: the campus copy of
    `.campus-os/ledger-paths.md`. Returns files that exist, in a stable order.
    """
    dean = os.path.join(root, "dean")
    primary = os.path.join(dean, ".activity.jsonl")
    files = [primary] if os.path.isfile(primary) else []
    if os.path.isdir(dean):
        for f in sorted(os.listdir(dean)):
            if f.startswith(".activity.") and f.endswith(".jsonl") and f != ".activity.jsonl":
                files.append(os.path.join(dean, f))
    return files


def load_ledger(paths, days):
    if isinstance(paths, str): paths = [paths]
    cutoff = datetime.datetime.now().astimezone() - datetime.timedelta(days=days)
    rows = []
    for path in paths:
        if not os.path.isfile(path): continue
        # A line with no `seat` predates the stamp and belongs to the primary
        # seat. Attribute it, never drop it - ledgers are append-only and are
        # never retro-edited (canon: .campus-os/ledger-paths.md).
        shard = os.path.basename(path)
        default_seat = "primary" if shard == ".activity.jsonl" else shard[len(".activity."):-len(".jsonl")]
        for ln in open(path, encoding="utf-8", errors="ignore"):
            ln = ln.strip()
            if not ln or ln.startswith("#"): continue
            try: d = json.loads(ln)
            except Exception: continue
            if d.get("skill") != "ad-hoc" or d.get("outcome") != "completed": continue
            ts = d.get("ts")
            try:
                t = datetime.datetime.fromisoformat(ts)
                if t.tzinfo is None: t = t.astimezone()
                if t < cutoff: continue
            except Exception:
                pass  # keep undated ad-hoc entries
            d.setdefault("seat", default_seat)
            rows.append(d)
    # Sort ONLY when shards were actually merged - a single-seat campus must
    # behave byte-identically to the pre-shard reader (same rule as the campus
    # map generator, where an unconditional sort silently reordered entries).
    if len(paths) > 1:
        rows.sort(key=lambda r: str(r.get("ts") or ""))
    return rows

def slugify(words):
    return "-".join(list(words)[:4]) or "adhoc-cluster"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--campus-root", default=".")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--min-cluster", type=int, default=3)
    args = ap.parse_args()
    root = os.path.abspath(args.campus_root)

    rows = load_ledger(ledger_files(root), args.days)
    # installed employee triggers for dedupe
    reg = {}
    try: reg = json.load(open(os.path.join(root, ".campus-os/registry.json")))
    except Exception: pass
    installed = []
    for t in reg.get("teams", []) + reg.get("playbooks", []):
        name = t.get("team") or t.get("name") or t.get("playbook")
        trigs = t.get("triggers", []) or []
        installed.append((name, toks(name + " " + " ".join(trigs))))
    # rejected candidates
    rejected = []
    rdir = os.path.join(root, "dean/skill-candidates/_rejected")
    if os.path.isdir(rdir):
        for f in os.listdir(rdir):
            if f.endswith(".md"): rejected.append(toks(f[:-3]))
    # existing proposed candidates (don't re-propose)
    existing_slugs = set()
    cdir = os.path.join(root, "dean/skill-candidates")
    if os.path.isdir(cdir):
        for f in os.listdir(cdir):
            if f.endswith(".md"): existing_slugs.add(f[:-3])

    # greedy clustering by trigger overlap
    items = [dict(row=r, tk=toks(r.get("trigger",""))) for r in rows if toks(r.get("trigger",""))]
    used = [False]*len(items)
    clusters = []
    for i in range(len(items)):
        if used[i]: continue
        group = [i]; used[i] = True
        for j in range(i+1, len(items)):
            if used[j]: continue
            if jaccard(items[i]["tk"], items[j]["tk"]) >= 0.5:
                group.append(j); used[j] = True
        if len(group) >= args.min_cluster:
            clusters.append(group)

    candidates, should_have_fired = [], []
    for group in clusters:
        members = [items[g] for g in group]
        # common keywords across the cluster
        common = set.intersection(*[m["tk"] for m in members]) or members[0]["tk"]
        # dedupe vs installed — use the cluster's COMMON tokens + per-member max
        # (union dilutes Jaccard and lets duplicates of existing skills slip through)
        matched = None
        allk = set().union(*[m["tk"] for m in members])
        for name, itk in installed:
            ntk = toks(name)
            name_hit = ntk and ntk.issubset(allk)          # skill name fully present in cluster
            common_hit = jaccard(common, itk) >= 0.5
            member_hit = max((jaccard(m["tk"], itk) for m in members), default=0) >= 0.5
            if name_hit or common_hit or member_hit:
                matched = name; break
        rep_triggers = []
        for m in members:
            tr = m["row"].get("trigger","").strip()
            if tr and tr not in rep_triggers: rep_triggers.append(tr)
        if matched:
            should_have_fired.append({"existing_skill": matched, "occurrences": len(members),
                                      "trigger_examples": rep_triggers[:3]})
            continue
        if any(jaccard(allk, rj) >= 0.5 for rj in rejected):
            continue
        depts = {}
        for m in members:
            # `dept` is canon. `team` is a legacy spelling shipped in the v5.0.x
            # dean template - real ledgers contain BOTH, and the ledger is
            # append-only so old lines can never be corrected. Read both or
            # silently bucket every kernel-skill line as "dean" (observed on a
            # real Codex campus 2026-07-26: 4 of 7 lines mis-attributed).
            d = m["row"].get("dept") or m["row"].get("team") or "dean"; depts[d] = depts.get(d,0)+1
        slug = slugify(sorted(common))
        base = slug; n = 2
        while slug in existing_slugs:
            slug = f"{base}-{n}"; n += 1
        existing_slugs.add(slug)
        candidates.append({
            "slug": slug,
            "occurrences": len(members),
            "trigger_examples": rep_triggers[:4],
            "suggested_dept": max(depts, key=depts.get),
            "keywords": sorted(common)[:8],
        })

    candidates.sort(key=lambda c: -c["occurrences"])
    # merge should-have-fired by skill name (sum occurrences, union trigger examples)
    shf_merged = {}
    for s in should_have_fired:
        k = s["existing_skill"]
        if k not in shf_merged:
            shf_merged[k] = {"existing_skill": k, "occurrences": 0, "trigger_examples": []}
        shf_merged[k]["occurrences"] += s["occurrences"]
        for tr in s["trigger_examples"]:
            if tr not in shf_merged[k]["trigger_examples"]:
                shf_merged[k]["trigger_examples"].append(tr)
    out = {"window_days": args.days, "window_count": len(items),
           "candidates": candidates[:5], "overflow": max(0, len(candidates)-5),
           "existing_should_have_fired": sorted(shf_merged.values(), key=lambda x: -x["occurrences"])}
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
