#!/usr/bin/env python3
"""validate_results.py - results.json against schemas/results.schema.json (5.2.0 Phase 3.1).

Writing is exact; reading is permissive (Interop spec v1 §6). One schema file, two ways to use it:

  * WRITE check  - a document that says `schema_version: "1.1"` must satisfy the schema fully.
  * READ classify - every other document is classified, never failed:
        legacy-1.0   run_id + (assets[] or completion{})   - the Interop v1 / foundry stub shapes
        ledger       run_id but neither assets nor completion - a job ledger, not an envelope
        foreign      no run_id at all                       - not a back-socket file
        malformed    unreadable / not a JSON object          - reported, counts as failure

Normalization applied on read (never written back): missing schema_version -> "1.0";
"1.1-completion-only" -> "1.0" + profile completion-only (Foundry CANON Break 5).

Stock Python; the validator supports the draft-07 subset our schemas use (type incl. lists,
required, enum, pattern, properties, items, minItems). Same subset as the Foundry's
_common.validate_against_schema so both sides agree.

Usage:
  python3 tools/validate_results.py FILE [FILE...]            # validate given files
  python3 tools/validate_results.py --campus-root DIR          # every outputs/**/results.json + teams-shared/**/results.json
  python3 tools/validate_results.py --schema PATH ... [--json] [--strict]
Exit 0 = no v1.1-invalid and no malformed. Exit 1 = some. Exit 2 = cannot run.
--strict also exits 1 when legacy/ledger/foreign documents are present (use on fresh campuses).
"""
import argparse
import glob
import json
import os
import re
import sys
from pathlib import Path

KERNEL = Path(__file__).resolve().parent.parent
DEFAULT_SCHEMA = KERNEL / "schemas" / "results.schema.json"
LEGACY_VERSIONS = {"1.0", "1.1-completion-only", None, ""}

_TYPES = {"object": dict, "array": list, "string": str, "integer": int, "number": (int, float), "boolean": bool}


def _type_ok(value, jtype):
    if isinstance(jtype, list):
        return any(_type_ok(value, t) for t in jtype)
    if jtype == "null":
        return value is None
    if jtype in ("integer", "number"):
        return isinstance(value, (int, float) if jtype == "number" else int) and not isinstance(value, bool)
    if jtype == "boolean":
        return isinstance(value, bool)
    py = _TYPES.get(jtype)
    return isinstance(value, py) if py else True


def validate(instance, schema, path="$"):
    """Human-readable error strings; empty list = valid."""
    errors = []
    jtype = schema.get("type")
    if jtype is not None and not _type_ok(instance, jtype):
        errors.append(f"{path}: expected {jtype}, got {type(instance).__name__}")
        return errors
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: {instance!r} not in {schema['enum']}")
    if isinstance(instance, str) and "pattern" in schema and not re.search(schema["pattern"], instance):
        errors.append(f"{path}: {instance!r} does not match /{schema['pattern']}/")
    if isinstance(instance, dict):
        for req in schema.get("required", []):
            if req not in instance:
                errors.append(f"{path}: missing required '{req}'")
        for key, sub in schema.get("properties", {}).items():
            if key in instance:
                errors.extend(validate(instance[key], sub, f"{path}.{key}"))
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{path}: needs >= {schema['minItems']} items")
        if "items" in schema:
            for i, item in enumerate(instance):
                errors.extend(validate(item, schema["items"], f"{path}[{i}]"))
    return errors


def normalize(doc):
    """Read-side normalization. Returns (doc_copy, notes)."""
    d = dict(doc)
    notes = []
    sv = d.get("schema_version")
    if sv in (None, ""):
        d["schema_version"] = "1.0"
        notes.append("schema_version missing -> 1.0")
    elif sv == "1.1-completion-only":
        d["schema_version"] = "1.0"
        d.setdefault("profile", "completion-only")
        notes.append("1.1-completion-only -> 1.0 + profile")
    return d, notes


def classify(doc, schema):
    """Return (category, errors, notes) for one parsed document."""
    if not isinstance(doc, dict):
        return "malformed", ["not a JSON object"], []
    d, notes = normalize(doc)
    if d.get("schema_version") == "1.1":
        errs = validate(d, schema)
        return ("v1.1-valid" if not errs else "v1.1-invalid"), errs, notes
    if d.get("schema_version") not in LEGACY_VERSIONS:
        notes.append(f"unknown schema_version {d.get('schema_version')!r} read as legacy")
    if not isinstance(d.get("run_id"), str) or not d.get("run_id"):
        return "foreign", [], notes
    has_assets = isinstance(d.get("assets"), list)
    has_completion = isinstance(d.get("completion"), dict)
    if has_assets or has_completion:
        return "legacy-1.0", [], notes
    return "ledger", [], notes


def load(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh), None
    except (OSError, ValueError) as exc:
        return None, f"{type(exc).__name__}: {exc}"


def collect(campus_root):
    root = Path(campus_root)
    pats = [str(root / "outputs" / "**" / "results.json"), str(root / "teams-shared" / "**" / "results.json")]
    files = set()
    for p in pats:
        files.update(glob.glob(p, recursive=True))
    return sorted(files)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--campus-root")
    ap.add_argument("--schema", default=str(DEFAULT_SCHEMA))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="legacy/ledger/foreign also fail")
    a = ap.parse_args(argv)

    schema_path = Path(a.schema)
    if not schema_path.is_file():
        print(f"FAIL(2): schema not found: {schema_path}", file=sys.stderr)
        return 2
    schema, err = load(schema_path)
    if err:
        print(f"FAIL(2): schema unreadable: {err}", file=sys.stderr)
        return 2

    files = list(a.files)
    if a.campus_root:
        files.extend(collect(a.campus_root))
    if not files:
        print("FAIL(2): no files given (pass FILE... or --campus-root)", file=sys.stderr)
        return 2

    rows = []
    for f in files:
        doc, err = load(f)
        if err:
            rows.append({"file": f, "category": "malformed", "errors": [err], "notes": []})
            continue
        cat, errs, notes = classify(doc, schema)
        rows.append({"file": f, "category": cat, "errors": errs, "notes": notes})

    counts = {}
    for r in rows:
        counts[r["category"]] = counts.get(r["category"], 0) + 1
    failing = counts.get("v1.1-invalid", 0) + counts.get("malformed", 0)
    if a.strict:
        failing += counts.get("legacy-1.0", 0) + counts.get("ledger", 0) + counts.get("foreign", 0)

    if a.json:
        print(json.dumps({"schema": str(schema_path), "files": len(rows), "counts": counts,
                          "failing": failing, "rows": rows}, indent=2))
    else:
        for r in rows:
            if r["category"] in ("v1.1-invalid", "malformed"):
                print(f"  !! {r['file']}: {r['category']}")
                for e in r["errors"][:6]:
                    print(f"       {e}")
        order = ["v1.1-valid", "v1.1-invalid", "legacy-1.0", "ledger", "foreign", "malformed"]
        summary = "  ".join(f"{k} {counts.get(k, 0)}" for k in order if counts.get(k))
        verdict = "FAIL" if failing else "OK"
        print(f"{verdict}: {len(rows)} results.json  -  {summary}")
    return 1 if failing else 0


if __name__ == "__main__":
    sys.exit(main())
