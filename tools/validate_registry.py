#!/usr/bin/env python3
"""validate_registry.py - enum enforcement for `.campus-os/registry.json` (5.2.0 Phase 2.4).

Every `teams[]` entry must carry `type` and `status`, and each must be a value
from the enum in `templates/registration-block-spec.md`. `department` and
`version` are checked the same way. The enums are READ FROM THE SPEC, never
stored here - the foundry's `_common.department_enum()` set that rule after a
second copy of the department list fell three values behind the spec.

Reading is permissive where the campus has always been permissive:
  * `department: dean` is the pre-5.1.x alias of `dean-office` (read OK, never written new)
  * `status: legacy` (spec: pre-v3 teams keep working as they are) and `status: retired`
    (historical record) entries are exempt from the department/version checks - but they
    still need `type` and `status` themselves, since `status` is the field that exempts them.
  * `type: department` / `type: systems` entries are org-chart groups, not versioned teams;
    `version` is not required of them.

Usage:
  python3 tools/validate_registry.py [--campus-root DIR]        # DIR/.campus-os/registry.json + DIR's installed spec
  python3 tools/validate_registry.py --registry FILE --spec FILE [--json]
Exit 0 = every entry valid. Exit 1 = failures listed. Exit 2 = could not run (spec/registry unreadable).
"""
import argparse
import json
import re
import sys
from pathlib import Path

KERNEL = Path(__file__).resolve().parent.parent
ENUM_LINE = {
    "type": re.compile(r'^\s*"type"\s*:\s*"([^"]+)"', re.M),
    "status": re.compile(r'^\s*"status"\s*:\s*"([^"]+)"', re.M),
    "department": re.compile(r'^\s*"department"\s*:\s*"([^"]+)"', re.M),
}
SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
READ_ALIASES = {"department": {"dean": "dean-office"}}


def spec_has_enums(p: Path):
    try:
        text = p.read_text(encoding="utf-8")
    except OSError:
        return False
    return all(rx.search(text) for rx in ENUM_LINE.values())


def find_spec(campus_root: Path):
    """The campus's installed spec wins when it carries every enum line. A campus
    that has not yet upgraded to a spec with `type`/`status` lines falls back to
    this kernel's template and says so - the list is still read from a spec,
    never from this file."""
    kernel_spec = KERNEL / "templates" / "registration-block-spec.md"
    for rel in (".campus-os/registration-block-spec.md",
                "templates/registration-block-spec.md"):
        p = campus_root / rel
        if p.is_file():
            if spec_has_enums(p):
                return p
            if kernel_spec.is_file() and spec_has_enums(kernel_spec):
                print(f"note: {p} predates the type/status enum lines; reading them from "
                      f"{kernel_spec} (run /update-workspace to refresh the installed spec)",
                      file=sys.stderr)
                return kernel_spec
            return p
    return kernel_spec if kernel_spec.is_file() else None


def enums_from_spec(spec: Path):
    text = spec.read_text(encoding="utf-8")
    enums = {}
    for field, rx in ENUM_LINE.items():
        m = rx.search(text)
        if not m:
            sys.exit(f"FAIL(2): {spec} has no enum line for \"{field}\" - fix the spec or this parser, "
                     "do not store the list in this tool")
        vals = [v.strip() for v in m.group(1).split("|") if v.strip()]
        if len(vals) < 2:
            sys.exit(f"FAIL(2): parsed only {vals!r} for \"{field}\" from {spec}")
        enums[field] = vals
    return enums


def validate(entries, enums):
    failures = []

    def fail(i, e, field, problem, value=None):
        failures.append({"index": i, "team": e.get("team") or e.get("name"),
                         "field": field, "problem": problem, "value": value})

    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            failures.append({"index": i, "team": None, "field": "entry", "problem": "not an object", "value": None})
            continue
        if not e.get("team") and not e.get("name"):
            fail(i, e, "team", "missing")
        for field in ("type", "status"):
            v = e.get(field)
            if v in (None, ""):
                fail(i, e, field, "missing")
            elif v not in enums[field]:
                fail(i, e, field, "not in enum", v)
        # legacy (pre-v3, spec §status) and retired (historical record) entries
        # keep their type + status but are not held to the live-team shape.
        if e.get("status") in ("legacy", "retired"):
            continue
        d = e.get("department")
        if d in (None, ""):
            fail(i, e, "department", "missing")
        elif d not in enums["department"] and d not in READ_ALIASES["department"]:
            fail(i, e, "department", "not in enum", d)
        # `department` / `systems` entries are org-chart groups written by
        # gen_department_entries.py - they are not versioned teams.
        if e.get("type") in ("department", "systems"):
            continue
        ver = e.get("version")
        if ver in (None, ""):
            fail(i, e, "version", "missing")
        elif not SEMVER.match(str(ver)):
            fail(i, e, "version", "not semver", ver)
    return failures


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--campus-root", default=None)
    ap.add_argument("--registry", default=None)
    ap.add_argument("--spec", default=None)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    root = Path(a.campus_root).resolve() if a.campus_root else Path.cwd()
    registry = Path(a.registry) if a.registry else root / ".campus-os" / "registry.json"
    spec = Path(a.spec) if a.spec else find_spec(root)
    if not spec or not spec.is_file():
        sys.exit(f"FAIL(2): registration-block-spec.md not found (looked at {spec}) - pass --spec")
    if not registry.is_file():
        sys.exit(f"FAIL(2): registry not found: {registry}")
    try:
        data = json.loads(registry.read_text(encoding="utf-8"))
    except ValueError as ex:
        sys.exit(f"FAIL(2): {registry} is not valid JSON: {ex}")

    enums = enums_from_spec(spec)
    entries = data.get("teams", []) if isinstance(data, dict) else []
    failures = validate(entries, enums)
    counts = {}
    for f in failures:
        counts[f["field"] + ":" + f["problem"]] = counts.get(f["field"] + ":" + f["problem"], 0) + 1

    if a.json:
        print(json.dumps({"registry": str(registry), "spec": str(spec), "entries": len(entries),
                          "enums": enums, "failures": failures, "counts": counts}, indent=2))
    else:
        for f in failures:
            v = f" ({f['value']})" if f.get("value") is not None else ""
            print(f"  !! [{f['index']}] {f['team']}: {f['field']} {f['problem']}{v}")
        if failures:
            print(f"FAIL: {len(failures)} problems across {len(entries)} entries - "
                  + ", ".join(f"{k} x{n}" for k, n in sorted(counts.items())))
        else:
            print(f"OK: {len(entries)} registry entries carry type + status from the spec's enum")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
