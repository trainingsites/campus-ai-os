#!/usr/bin/env python3
"""
Packaging-time generator (Campus AI OS v4.1.4, Seam C section 4).

Reads every shipped skill's frontmatter `department:` and writes the staff-org
entries into templates/registry.json -> teams[]:

  - FIVE `type: department` employee groups (community, education, marketing,
    sales, dean-office), each carrying an `employees[]` roster. These are the
    counted staff.
  - ONE `type: systems` entry (campus-systems) whose `systems[]` lists the
    kernel/platform skills (department: kernel). These are the campus's own
    machinery - shown as "N campus systems", NOT counted as employees.

This is the single source of truth for the org-chart line (campus-doctor /
campus-map) so a fresh cold-install buyer sees a real headcount on day one:
"{E} employees + {S} campus systems + {P} playbooks".

Frontmatter departments recognized:
  community | education | marketing | sales | dean-office  -> counted employees
  kernel                                                    -> campus systems
The chief-of-staff kernel *team* entries (dean, campus-ai-os) are the
orchestrator/platform meta records and are left untouched.

- Idempotent: removes any existing type:department + type:systems entries,
  then re-adds fresh from frontmatter.
- Deterministic, stdlib only. Run before packaging; the promise-parity gate
  (`--check`) then verifies rosters == shipped skills.

Usage:  python3 tools/gen_department_entries.py [--check]
"""
import json, os, re, sys, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---- Where the registry being written lives (v5.1.1) ------------------------
# The SKILLS are always read from the plugin (ROOT/skills) - that is correct for
# a live campus too, because skills ship in the plugin, not in the campus. Only
# the WRITE TARGET differs:
#
#   default        -> ROOT/templates/registry.json   (packaging time)
#   --campus PATH  -> PATH/.campus-os/registry.json  (a real, live campus)
#
# One generator, two targets - the same shape as lint_managers.py's
# --pack/--campus, deliberately, because two copies of a rule is the defect
# class this release exists to close.
#
# Why --campus was owed: the staff-org entries are DERIVED from skill
# frontmatter, but an upgrade PRESERVED them ("never touch existing teams[]
# entries"). So the org chart froze at whatever kernel version first wrote it,
# and every release that adds skills left upgraded campuses with a stale roster
# - permanently, while reporting success. Measured on a live campus after the
# v5.1.0 upgrade: "28 employees + 14 campus systems" against a founded campus's
# "23 employees + 20 campus systems", with all six Atlas internals missing and
# no dean-office entry for the seven user-facing Atlas skills to land in.
def registry_path(campus=None):
    if campus:
        return os.path.join(campus, ".campus-os", "registry.json")
    return os.path.join(ROOT, "templates", "registry.json")

# The six entries this generator OWNS and may replace. Anything else with
# type department/systems belongs to the owner (e.g. a department they
# registered under their own name via campus-doctor check 8a-i) and is never
# touched. Replacing all type:department entries wholesale - which the
# packaging-time path did - would have DELETED those on a live campus.
OWNED_TEAMS = None   # computed in main() from EMP_DEPTS + campus-systems

# employee departments, in display order
EMP_DEPTS = ["marketing", "sales", "lead-generation", "operations", "finance",
             "people", "community", "education", "dean-office"]
# operations/finance/people are new in v5.1.8 - lead-generation's empty-starter
# pattern (v5.1.4): the department exists on the org chart so the diagnosis is
# honest, and it is staffed by a team the owner installs.
# ---- Department labels: kernel default + pack override (v5.1.6) ------------
# TWO LAYERS, and the kernel layer must stay GENERIC. This dict used to read
# "Community" and "Education" - which are the EDUCATION PACK's words sitting in
# the kernel, i.e. the kernel hardcoding one niche's vocabulary. Straight S206:
# the fix belongs in the architecture (pack-declared config), not in the labels.
#
# Canon: wiki/decisions/drop-in-department-model.md - "the label is
# pack-declared. Kernel default = Support; education pack overrides to
# Community." And the naming canon: "Client Delivery reads 'Teaching' on an
# education campus."
#
# Resolution order is the same shape as CONTEXT_CANON and ENTRY_FILE: default,
# then override, first hit wins. The override layer is OPTIONAL by necessity -
# `dean-office` is a department with no manager entry, so it can only ever come
# from the default.
KERNEL_LABEL = {"marketing": "Marketing", "sales": "Sales",
                "lead-generation": "Lead Generation",
                "operations": "Operations", "finance": "Finance",
                "people": "People",
                "community": "Client Support", "education": "Client Delivery",
                "dean-office": "Dean's office"}


def resolve_labels(pack_json=None):
    """KERNEL_LABEL, overridden per department by the pack's display_name.

    The ONE place a department's display label is decided. Both readers - this
    generator and campus-start - take it from here (campus-start reads the
    `label` field this writes into templates/registry.json, so it never parses
    a pack or a python dict). Build-gate check 24 fails the build if either
    side grows its own list again.

    Why it needed fixing: v5.1.5's founding rendered the pack's display names
    ("Media Desk", "Teaching Desk") while campus-doctor rendered this dict
    ("Marketing", "Education") - two vocabularies for the same five departments,
    shown to the same owner minutes apart. The v5.1.4 hardcode in campus-start
    had been MASKING the divergence by accident; deriving the list surfaced it.
    """
    labels = dict(KERNEL_LABEL)
    if pack_json and os.path.isfile(pack_json):
        try:
            pk = json.load(open(pack_json, encoding="utf-8"))
        except (OSError, ValueError):
            return labels
        for m in pk.get("managers") or []:
            if m.get("id") in labels and m.get("display_name"):
                labels[m["id"]] = m["display_name"]
    return labels
OWNS = {
    "community": "Community department - member and student engagement, care, and coaching prep.",
    "education": "Education department - courses, lessons, class prep, and curriculum.",
    "marketing": "Marketing department - content, social, email, and reach.",
    "sales":     "Sales department - offers, launches, and revenue.",
    "lead-generation": "Lead Generation department - finding and qualifying the people Sales talks to: prospect research, list building, and cold outreach drafts.",
    "operations": "Operations department - the business's own running: procedures, scheduling, delivery, and document control.",
    "finance": "Finance department - money in and money owed: job costing, receivables follow-through, and cost visibility.",
    "people": "People department - hiring, onboarding, and the humans on the team.",
    "dean-office": "Dean's office - the chief of staff's own working staff: daily brief, weekly review, the wiki memory, and the strategy and research bench (brainstorming council, scans, competitor audits, briefs, and reading back what worked).",
}

# ---- Department vocabulary (v5.1.4) ----------------------------------------
# `dean` is a LEGACY ALIAS for `dean-office`: accepted on read, never written.
# The org chart has always counted `dean-office`; registration-block-spec.md
# offered `dean`. An entry filed exactly as the spec instructed was therefore
# counted by NEITHER reader - the same writer/reader-vocabulary defect as the
# `seo-team` orphan, one layer up. Reconciled by teaching every reader the
# alias, NOT by renaming an internal id.
DEPT_ALIAS = {"dean": "dean-office"}
# Values that are legitimately not a staffed department. `kernel` is the
# campus's own machinery (counted separately as "campus systems"); core/cross
# serve no single department. An active entry carrying anything OUTSIDE
# EMP_DEPTS | DEPT_ALIAS | NON_DEPT is an orphan - build-gate check 20.
NON_DEPT = {"kernel", "core", "cross"}
# The kernel META records. Excluded from both counts by TYPE, not by
# department - which is why they may keep `department: dean` forever without
# tripping the orphan check. Internal ids are never renamed.
META_TYPES = {"kernel"}


def resolve_dept(dep):
    """Read-side resolution. Exact on write, permissive on read."""
    return DEPT_ALIAS.get(dep, dep)
SYSTEMS_OWNS = "Campus systems - the platform machinery (founding, upgrades, health, dashboard, self-authoring loop, workforce governance). Not employees; the campus running itself."

def read_department(skill_md):
    txt = open(skill_md, encoding="utf-8", errors="replace").read().split("\n")
    if not txt or txt[0].strip() != "---":
        return None
    for line in txt[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^department:\s*(\S+)", line)
        if m:
            return m.group(1).strip()
    return None

def collect():
    roster = {d: [] for d in EMP_DEPTS}
    systems = []
    for skill_md in sorted(glob.glob(os.path.join(ROOT, "skills", "*", "SKILL.md"))):
        slug = os.path.basename(os.path.dirname(skill_md))
        dep = resolve_dept(read_department(skill_md))
        if dep in roster:
            roster[dep].append(slug)
        elif dep == "kernel":
            systems.append(slug)
    for d in roster:
        roster[d].sort()
    systems.sort()
    return roster, systems

def build_entries(roster, systems, labels):
    entries = []
    for d in EMP_DEPTS:
        entries.append({
            "team": d,
            "type": "department",
            "department": d,
            "label": labels[d],
            "status": "active",
            "owns": OWNS[d],
            "employees": roster[d],
            "permission": "draft-only",
        })
    entries.append({
        "team": "campus-systems",
        "type": "systems",
        "department": "kernel",
        "label": "Campus systems",
        "status": "active",
        "owns": SYSTEMS_OWNS,
        "systems": systems,
        "permission": "draft-only",
    })
    return entries

def summary(roster, systems, labels):
    emp = sum(len(roster[d]) for d in EMP_DEPTS)
    parts = ", ".join("{} {}".format(labels[d], len(roster[d])) for d in EMP_DEPTS)
    return "{} employees ({}) + {} campus systems".format(emp, parts, len(systems))

def derivable_names(teams):
    """{department -> {team names derivable from their OWN registry entry}}.

    v5.1.4, payload item 2. A team already declares its department once, on its
    own entry. Copying that name into the department's roster gives one fact two
    homes - and the write landed in only one of them: `seo-team` carried
    `department: marketing` while missing from Marketing's roster, and
    `campus-stack-diagnostic` did the same to Sales. A reconciliation check
    could not see it, because the headline and the breakdown were both read from
    the stale copy. Derive instead of storing twice.

    Status is consulted here for the same reason every other reader consults it:
    a team the owner stood down is not staff.
    """
    out = {}
    for t in teams:
        if t.get("type") in ("department", "systems") or t.get("type") in META_TYPES:
            continue
        if (t.get("status") or "active") in ("retired", "legacy", "disabled"):
            continue
        d = resolve_dept(t.get("department"))
        if d in EMP_DEPTS:
            out.setdefault(d, set()).add(t.get("team"))
    return out


def merge_owner_additions(fresh, existing, teams):
    """Preserve owner-added employees while regenerating the derived list.

    THE MERGE POLICY (v5.1.1, amended v5.1.4):

      employees[]        kernel-derived from shipped skill frontmatter.
                         Regenerated wholesale every time.
      employees_added[]  owner-added AND NOT DERIVABLE FROM ANYWHERE ELSE.
                         Shrunk, never destroyed.

    Readers (campus-doctor 8a, campus-map) count the de-duplicated union of
    employees[] + employees_added[] + every active entry whose `department`
    resolves to this one.

    v5.1.4 adds the third rule: a name that IS derivable from its own registry
    entry is REMOVED from employees_added[], because the entry is now its single
    home. This is lossless by construction - the name is dropped only when an
    active entry carrying that department has been seen in this same pass - and
    it is the difference between fixing the orphan and papering over it. Adding
    `seo-team` to the stored roster would have left the second home in place and
    guaranteed the next orphan.

    A name with NO entry of its own is genuinely owner data with a single home,
    and is preserved untouched. Build-gate check 15 requires this behaviour to
    exist at all.
    """
    derivable = derivable_names(teams)
    # The name is dropped if it is derivable from ANY department, not merely
    # from THIS one. A team that moves department (prep-agents-team sales ->
    # education) is derivable at its new home while its name sits stale in the
    # old department's roster - and a per-department test leaves it there
    # forever, which is the stale second copy this item exists to delete. The
    # entry is the single home wherever it points.
    derivable_anywhere = set().union(*derivable.values()) if derivable else set()
    dropped = {}
    for e in fresh:
        cur = existing.get(e["team"])
        if not cur:
            continue
        if e["type"] == "department":
            derived = set(e["employees"])
            # One-time reclassification + preservation of prior additions.
            prior_added = set(cur.get("employees_added") or [])
            reclassified = {n for n in (cur.get("employees") or []) if n not in derived}
            added = prior_added | reclassified
            now_derivable = added & derivable_anywhere
            if now_derivable:
                dropped[e["team"]] = sorted(now_derivable)
            added = sorted(added - now_derivable)
            if added:
                e["employees_added"] = added
        else:
            prior_added = set(cur.get("systems_added") or [])
            reclassified = {n for n in (cur.get("systems") or []) if n not in set(e["systems"])}
            added = sorted(prior_added | reclassified)
            if added:
                e["systems_added"] = added
    return fresh, dropped


def orphans(teams):
    """Active entries whose department no reader can resolve (check 20).

    The failure this catches, stated plainly: a team files itself under a
    department name that is real to the person who typed it and invisible to
    every counter. `tech-advisor-team` filed `dean-office` before any roster
    existed for it; anything filed `dean` per the old spec landed nowhere.
    """
    bad = []
    known = set(EMP_DEPTS) | set(DEPT_ALIAS) | NON_DEPT
    for t in teams:
        if t.get("type") in ("department", "systems") or t.get("type") in META_TYPES:
            continue
        if (t.get("status") or "active") in ("retired", "legacy", "disabled"):
            continue
        d = t.get("department")
        if d is None or d not in known:
            bad.append((t.get("team"), d))
    return bad


def collisions(teams, systems):
    """Names that would be counted BOTH as an employee and as a campus system.

    v5.1.4. Introduced by the `dean` -> `dean-office` alias, and worth keeping
    permanently. The four `hr-*` skills SHIP as `department: kernel` (campus
    systems) but were registered on this campus years earlier as
    `department: dean` - so the moment `dean` started resolving, they were
    counted once in each figure and the org chart quietly inflated.

    A name belongs to exactly one count. Systems wins, because the shipped
    skill's own frontmatter is the owner of "what kind of thing is this" and a
    campus registry entry is a copy. **Report the collision rather than
    absorbing it** - silently deduplicating would hide a stale record that
    should be re-filed, which is how the `seo-team` orphan survived so long.
    """
    sysnames = set(systems)
    hits = []
    for t in teams:
        if t.get("type") in ("department", "systems") or t.get("type") in META_TYPES:
            continue
        if (t.get("status") or "active") in ("retired", "legacy", "disabled"):
            continue
        if t.get("team") in sysnames and resolve_dept(t.get("department")) in EMP_DEPTS:
            hits.append((t.get("team"), t.get("department")))
    return hits


def main():
    check = "--check" in sys.argv
    campus = None
    if "--campus" in sys.argv:
        campus = sys.argv[sys.argv.index("--campus") + 1]
    REG = registry_path(campus)
    if not os.path.isfile(REG):
        print("no registry at", REG); sys.exit(1)
    reg = json.load(open(REG))
    teams = reg.get("teams", [])
    pack = "education"
    if "--pack" in sys.argv:
        pack = sys.argv[sys.argv.index("--pack") + 1]
    labels = resolve_labels(os.path.join(ROOT, "packs", pack, "pack.json"))
    roster, systems = collect()
    fresh = build_entries(roster, systems, labels)

    owned = set(EMP_DEPTS) | {"campus-systems"}
    existing = {t["team"]: t for t in teams
                if t.get("type") in ("department", "systems") and t.get("team") in owned}
    drift = []
    for e in fresh:
        cur = existing.get(e["team"])
        key = "employees" if e["type"] == "department" else "systems"
        if not cur or cur.get(key) != e[key]:
            drift.append(e["team"])

    orphaned = orphans(teams)
    collided = collisions(teams, systems)

    if check:
        if collided:
            print("COLLISION FAIL - counted as BOTH an employee and a campus system:")
            for name, d in collided:
                print("  {:26s} department={!r} but ships as `department: kernel`".format(name, d))
            sys.exit(1)
        if orphaned:
            print("ORPHAN FAIL - active entries filed under a department no reader resolves:")
            for name, d in orphaned:
                print("  {:26s} department={!r}".format(name, d))
            print("  known: " + " | ".join(sorted(set(EMP_DEPTS) | set(DEPT_ALIAS) | NON_DEPT)))
            sys.exit(1)
        if drift:
            print("PROMISE-PARITY FAIL - staff-org entries drift from shipped skills:", drift)
            for e in fresh:
                key = "employees" if e["type"] == "department" else "systems"
                print("  {:14s} listed={} shipped={}".format(
                    e["team"], (existing.get(e["team"], {}) or {}).get(key), e[key]))
            sys.exit(1)
        print("PROMISE-PARITY OK - staff-org entries match shipped skills.")
        print("  no orphans - every active entry's department resolves to a roster.")
        print("  " + summary(roster, systems, labels) + " + {} playbooks".format(len(reg.get("playbooks", []))))
        return

    if orphaned:
        print("WARN - {} active entr{} filed under an unresolvable department:".format(
            len(orphaned), "y is" if len(orphaned) == 1 else "ies are"))
        for name, d in orphaned:
            print("  {:26s} department={!r}".format(name, d))
        print("  These are invisible to the org chart. Fix the entry's `department`"
              " field - the roster is derived from it.")

    if collided:
        print("WARN - {} entr{} would be counted TWICE (employee AND campus system):".format(
            len(collided), "y" if len(collided) == 1 else "ies"))
        for name, d in collided:
            print("  {:26s} registered department={!r}, ships as `kernel`".format(name, d))
        print("  A name belongs to exactly one count. Re-file the registry entry to"
              " `department: kernel` to match what the skill ships as.")

    fresh, dropped = merge_owner_additions(fresh, existing, teams)

    # Replace ONLY the six entries this generator owns. An owner-registered
    # department (their own name, via campus-doctor 8a-i) is type:department too
    # and must survive untouched - dropping it would make an upgrade destructive,
    # which is update-workspace's one prime directive.
    preserved = [t for t in teams
                 if not (t.get("type") in ("department", "systems") and t.get("team") in owned)]
    kernel = [t for t in preserved if t.get("type") == "kernel"]
    rest   = [t for t in preserved if t.get("type") != "kernel"]
    reg["teams"] = kernel + fresh + rest
    json.dump(reg, open(REG, "w"), indent=2)
    open(REG, "a").write("\n")
    kept = [t.get("team") for t in rest
            if t.get("type") in ("department", "systems")]
    if kept:
        print("preserved {} owner-registered org entr{}: {}".format(
            len(kept), "y" if len(kept) == 1 else "ies", kept))
    for e in fresh:
        extra = e.get("employees_added") or e.get("systems_added")
        if extra:
            print("preserved {} owner-added on {}: {}".format(len(extra), e["team"], extra))
    for team, names in sorted(dropped.items()):
        print("de-duplicated {} on {} - now derived from each team's own "
              "`department:` field, not stored twice: {}".format(
                  len(names), team, names))
    print("wrote {} department entries + 1 campus-systems entry to {}".format(
        len(EMP_DEPTS), REG))
    print("  " + summary(roster, systems, labels) + " + {} playbooks".format(len(reg.get("playbooks", []))))
    for d in EMP_DEPTS:
        print("  {:12s}: {}".format(d, roster[d]))
    print("  {:12s}: {}".format("systems", systems))

if __name__ == "__main__":
    main()
