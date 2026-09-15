#!/usr/bin/env python3
"""
lint_managers.py  -  the Manager Layer contract, as code  (v5.1 payload items 1+2)

WHAT A MANAGER IS
-----------------
A department is a MANAGER only if it has all three:

  1. owned state   - one canonical file answering "what is the situation here"
  2. cadence       - scheduled work that advances that state unprompted
  3. gate          - explicit publish authority, declared per surface

Missing any one and it is a folder, not a manager. This file is the only place
that rule is enforced, and it is the reason the rule survives contact with real
campuses instead of living in prose nobody runs.

ONE VALIDATOR, TWO INPUTS
-------------------------
The same rules apply in two places, so they are written once:

  --pack packs/{niche}/pack.json    the DEFAULTS the product ships
  --campus <campus-root>            what a real campus actually resolved to

Two copies of these rules would drift - which is the exact defect class v5.1
exists to close (one owner per shared fact). So: one file, two modes.

THE NAMING RULE (learned from James's own install, S217)
--------------------------------------------------------
Three layers, none derived from another:

  id            marketing            logical key, stable WITHIN a campus,
                                     NOT a product-wide constant
  dept_dir      departments/marketing/   physical folder - varies by campus AND
                                     by filing structure
  display_name  Media Desk           cosmetic label, owner-overridable

`state_file` must be a LITERAL declared path, never built as `{id}/...`. Phase 1
survived on James's campus only because of this: his folder is
`marketing-manager/`, so a derived path would have gone looking for `marketing/`
and found nothing on day one.

FILING STRUCTURE IS NOT THE STAFF ORG  (the thing that nearly broke this)
------------------------------------------------------------------------
`campus-start` files work as departments | clients | projects | mix. A CLIENTS
campus has NO department folders on disk - and still has Marketing, Sales,
Community and Education staff, because the org chart is independent of filing.
So a manager's `dept_dir` may legitimately not exist. Requiring it would fail a
correct clients campus - the same defect class as the Codex entry-file bug and
the cron check's empty-scheduler bug. It is a warning at most, never an error.

Exit codes:  0 = clean (warnings allowed)   1 = contract violated   2 = bad input
"""

import argparse
import json
import sys
from pathlib import Path

SHAPES = ["calendar", "pipeline", "roster", "hybrid"]
GATE_MODES = ["auto", "draft", "owner_batch_gate", "dark"]
REQUIRED = ["id", "display_name", "shape", "state_file", "cadence", "gates"]
MODEL_TIERS = ["light", "full"]


class Findings:
    def __init__(self):
        self.errors, self.warns = [], []

    def error(self, who, msg):
        self.errors.append(f"{who}: {msg}")

    def warn(self, who, msg):
        self.warns.append(f"{who}: {msg}")

    def report(self, header):
        out = [header]
        for e in self.errors:
            out.append(f"  [!!] {e}")
        for w in self.warns:
            out.append(f"  [--] {w}")
        if not self.errors and not self.warns:
            out.append("  [OK] every manager satisfies the contract")
        elif not self.errors:
            out.append(f"  [OK] contract satisfied ({len(self.warns)} advisory)")
        return "\n".join(out)


def check_manager(m, f, *, campus_root=None, is_pack_default=False):
    """Validate one manager contract. Shared by both modes.

    campus_root set => we can check that declared paths actually exist.
    is_pack_default  => this is a shipped TEMPLATE, so paths are defaults that
                        founding will resolve; existence is not checkable and
                        must not be asserted.
    """
    who = m.get("id") or m.get("display_name") or "<unnamed>"

    for field in REQUIRED:
        if m.get(field) is None:
            f.error(who, f"missing required field: {field}")

    # --- the three-layer naming rule -------------------------------------
    if m.get("id") and m.get("id") == m.get("display_name"):
        f.warn(who, "id and display_name are identical - the label should be "
                    "free to change without touching the key")

    if not m.get("dept_dir"):
        f.warn(who, "no dept_dir declared - consumers would have to guess the folder")
    elif campus_root and not (campus_root / m["dept_dir"]).is_dir():
        # NOT an error. A clients/projects campus has no department folders and
        # is still perfectly valid - the staff org exists independently of how
        # finished work is filed.
        f.warn(who, f"dept_dir not on disk ({m['dept_dir']}) - correct on a "
                    f"clients/projects campus, worth a look on a departments one")

    # --- shape: CLOSED enum ----------------------------------------------
    shape = m.get("shape")
    if shape and shape not in SHAPES:
        f.error(who, f"unknown shape '{shape}' - the enum is CLOSED "
                     f"[{', '.join(SHAPES)}]. A fifth shape is a kernel change "
                     f"and a version bump, not a config edit.")

    # a pipeline manager without stages cannot age anything through them
    if shape == "pipeline" and not m.get("stages"):
        f.warn(who, "shape is 'pipeline' but no stages[] declared - the kernel "
                    "does not know your stage names, so it cannot age items "
                    "without them")

    # --- state: the never-derive rule ------------------------------------
    state = m.get("state_file")
    if state:
        if m.get("id") and state.startswith(f"{m['id']}/"):
            f.error(who, f"state_file looks DERIVED from id ('{state}'). It must "
                         f"be a literal declared path - deriving breaks on any "
                         f"campus whose folder name differs from the id, which "
                         f"includes the one this was written on.")
        if campus_root and not is_pack_default:
            if not (campus_root / state).exists():
                f.error(who, f"state_file does not exist: {state} - a manager "
                             f"whose state file is missing owns nothing")

    # --- cadence: state that never advances is not managed ---------------
    cadence = m.get("cadence")
    if isinstance(cadence, list):
        if not cadence:
            f.warn(who, "no cadence declared - state plus a gate but nothing to "
                        "advance it is a folder, not a manager")
        for c in cadence:
            if not isinstance(c, dict) or not c.get("task"):
                f.error(who, "cadence entry missing 'task'")
                continue
            tier = c.get("model_tier")
            if tier and tier not in MODEL_TIERS:
                f.error(who, f"cadence '{c['task']}' has invalid model_tier "
                             f"'{tier}' ({'|'.join(MODEL_TIERS)})")
            if c.get("enabled") is None:
                f.warn(who, f"cadence '{c['task']}' does not declare enabled - "
                            f"ambiguous whether it runs")
            if campus_root and c.get("definition") \
                    and not (campus_root / c["definition"]).exists():
                f.error(who, f"cadence '{c['task']}' points at a missing "
                             f"definition: {c['definition']}")
    elif cadence is not None:
        f.error(who, "cadence must be a list")

    # --- gates: authority is explicit or it is not authority -------------
    gates = m.get("gates")
    if isinstance(gates, dict):
        if not gates:
            f.warn(who, "no gates declared - publish authority is undefined")
        for surface, g in gates.items():
            if not isinstance(g, dict) or not g.get("mode"):
                f.error(who, f"gate '{surface}' has no mode")
                continue
            if g["mode"] not in GATE_MODES:
                f.error(who, f"gate '{surface}' has unknown mode '{g['mode']}' "
                             f"({'|'.join(GATE_MODES)})")
            if g["mode"] == "auto" and not g.get("preflight"):
                f.warn(who, f"gate '{surface}' is AUTO with no preflight - "
                            f"publish authority is permission to post, not "
                            f"permission to skip checks")
    elif gates is not None:
        f.error(who, "gates must be an object keyed by surface")

    # --- the buyer floor: non-negotiable ---------------------------------
    bd = m.get("buyer_defaults")
    if not bd:
        f.warn(who, "no buyer_defaults - a packaged install would inherit this "
                    "campus's own publish grants")
    elif bd.get("all_surfaces") not in (None, "draft"):
        f.error(who, f"buyer_defaults.all_surfaces is '{bd['all_surfaces']}' - a "
                     f"customer install MUST ship all-draft-first. A buyer has "
                     f"not heard the voice yet; their first live post should be "
                     f"one they approved.")

    if not m.get("interop"):
        f.warn(who, "no interop block - cadence runs should mint a run_id, write "
                    "results.json, and append a ledger line")


def lint_pack(pack_path: Path, f: Findings) -> int:
    try:
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"[!!] cannot read {pack_path}: {e}", file=sys.stderr)
        return 2

    managers = pack.get("managers")
    if managers is None:
        f.warn("pack", "no managers[] declared - departments will be folders "
                       "until a local manager.json is written by hand")
        return 0
    if not isinstance(managers, list):
        f.error("pack", "managers must be a list")
        return 0

    declared = pack.get("departments", [])
    ids = [m.get("id") for m in managers if isinstance(m, dict)]

    for m in managers:
        if isinstance(m, dict):
            check_manager(m, f, is_pack_default=True)
        else:
            f.error("pack", "managers[] entry is not an object")

    # every manager must belong to a department the pack actually declares,
    # or the pack is promising staff for a department that does not exist
    for i in ids:
        if declared and i not in declared:
            f.error("pack", f"manager '{i}' is not in departments[] "
                            f"({', '.join(declared)})")
    dupes = {i for i in ids if ids.count(i) > 1}
    for d in dupes:
        f.error("pack", f"duplicate manager id '{d}'")
    return 0


def lint_campus(root: Path, f: Findings) -> int:
    """Validate the managers a real campus resolved to.

    Reads every {dept}/manager.json. Absence is NOT a failure - a campus with no
    managers is a campus that has not adopted the layer, which is allowed.
    """
    found = sorted(root.glob("*/manager.json")) + \
        sorted(root.glob("departments/*/manager.json"))
    if not found:
        return 0

    seen = {}
    for path in found:
        try:
            m = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            f.error(str(path.parent.name), f"manager.json is not valid JSON - {e}")
            continue
        check_manager(m, f, campus_root=root)
        mid = m.get("id")
        if mid in seen:
            f.error(mid, f"two managers claim id '{mid}' ({seen[mid]}, {path}) - "
                         f"ids must be unique within a campus")
        elif mid:
            seen[mid] = path
    return len(found)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--pack", help="validate a pack.json's declared managers[]")
    g.add_argument("--campus", help="validate a live campus's manager.json files")
    ap.add_argument("--quiet", action="store_true",
                    help="print only on failure")
    args = ap.parse_args()

    f = Findings()
    if args.pack:
        rc = lint_pack(Path(args.pack), f)
        if rc == 2:
            return 2
        header = f"Manager contract - pack defaults ({args.pack})"
    else:
        n = lint_campus(Path(args.campus), f)
        if n == 0:
            if not args.quiet:
                print("[OK] No managers declared on this campus - the layer is "
                      "opt-in and nothing here needs it.")
            return 0
        header = f"Manager contract - {n} manager(s) on this campus"

    if f.errors or not args.quiet:
        print(f.report(header))
    return 1 if f.errors else 0


if __name__ == "__main__":
    sys.exit(main())
