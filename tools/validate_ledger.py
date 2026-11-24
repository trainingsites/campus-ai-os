#!/usr/bin/env python3
"""validate_ledger.py - activity-ledger lines against schemas/ledger-line.schema.json (5.3.0 item 4).

One line shape for registered and ad-hoc runs. Same two-sided rule as validate_results.py:

  * WRITE check (--write) - a line being written now must carry every `required` key and type
    every key it carries as the schema says.
  * READ classify (default) - lines written before the schema are never failed for what they
    lack (no `seat`, `timestamp` instead of `ts`, extra keys): they classify as `legacy`.
    A key that IS present with the wrong type is `invalid` on both sides - e.g. `tokens_in: "12"`.

Categories per line: valid · legacy · invalid · malformed (not JSON / not an object).
Header lines starting with `#` and blank lines are skipped, as every ledger reader does.

Stock Python; reuses validate_results.validate (the draft-07 subset) and adds `minimum`.
platform: claude-code; seat: m4-claude-code

Usage:
  python3 tools/validate_ledger.py FILE [FILE...] [--write] [--json]
  python3 tools/validate_ledger.py --campus-root DIR [--json]     # dean/.activity.jsonl + every shard
  python3 tools/validate_ledger.py --line '{"ts": ...}' --write     # one line (writer self-check)
Exit 0 = no invalid / malformed lines (and, with --write, no legacy either). 1 = some. 2 = cannot run.
"""
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

# Kit copies run from .campus-os/kernel/tools (Codex audit F1, 5.2.14): the sibling folder goes at the
# END of the path so a planted file never shadows the standard library, and the bytecode cache points
# at an unguessable path that does not exist. Run as `python3 -I -B`.
NO_CACHE = os.path.join(tempfile.gettempdir(), f"campus-os-nocache-{os.getpid()}-{os.urandom(8).hex()}")
if __name__ == "__main__":  # only when run as a tool; an importing program keeps its own settings
    sys.dont_write_bytecode = True
    sys.pycache_prefix = NO_CACHE
sys.path.append(str(Path(__file__).resolve().parent))
from validate_results import validate  # noqa: E402  (one validator subset for both schemas)

KERNEL = Path(__file__).resolve().parent.parent
DEFAULT_SCHEMA = KERNEL / "schemas" / "ledger-line.schema.json"
MERGE_GLOB = "dean/.activity.*.jsonl"
SHARED = "dean/.activity.jsonl"


def load_schema(path=DEFAULT_SCHEMA):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _minimums(record, schema):
    errs = []
    for key, sub in schema.get("properties", {}).items():
        v = record.get(key)
        if "minimum" in sub and isinstance(v, (int, float)) and not isinstance(v, bool) and v < sub["minimum"]:
            errs.append(f"$.{key}: {v!r} is below minimum {sub['minimum']}")
    return errs


def classify(record, schema, write=False):
    """Return (category, errors) for one parsed ledger record."""
    if not isinstance(record, dict):
        return "malformed", ["not a JSON object"]
    shape = {k: v for k, v in schema.items() if k != "required"}
    type_errors = validate(record, shape) + _minimums(record, schema)
    if type_errors and not write:
        # Read side: a value outside a word list (e.g. an older `via` word) is legacy, never a failure;
        # only a wrong TYPE fails a line someone already wrote.
        loose = dict(shape, properties={k: {kk: vv for kk, vv in v.items() if kk != "enum"}
                                        for k, v in shape.get("properties", {}).items()})
        if not (validate(record, loose) + _minimums(record, schema)):
            return "legacy", type_errors
    if type_errors:
        return "invalid", type_errors
    missing = [k for k in schema.get("required", []) if k not in record]
    if missing:
        errs = [f"$: missing required '{k}'" for k in missing]
        return ("invalid" if write else "legacy"), errs
    return "valid", []


def classify_text(line, schema, write=False):
    try:
        record = json.loads(line)
    except ValueError as exc:
        return "malformed", [f"{type(exc).__name__}: {exc}"]
    return classify(record, schema, write)


def ledger_files(root):
    root = Path(root)
    files = set(root.glob(MERGE_GLOB))
    if (root / SHARED).is_file():
        files.add(root / SHARED)
    return sorted(files)


def scan(paths, schema, write=False, root=None):
    rows, counts = [], {}
    for path in paths:
        path = Path(path)
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            rows.append({"file": str(path), "line": 0, "category": "malformed", "errors": [str(exc)]})
            counts["malformed"] = counts.get("malformed", 0) + 1
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            cat, errs = classify_text(line, schema, write)
            counts[cat] = counts.get(cat, 0) + 1
            if cat in ("invalid", "malformed"):
                name = str(path.relative_to(root)) if root else str(path)
                rows.append({"file": name, "line": n, "category": cat, "errors": errs})
    return counts, rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("files", nargs="*")
    ap.add_argument("--campus-root")
    ap.add_argument("--line", help="validate one JSON line")
    ap.add_argument("--schema", default=str(DEFAULT_SCHEMA))
    ap.add_argument("--write", action="store_true", help="write-side check: required keys must be present")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        schema = load_schema(a.schema)
    except (OSError, ValueError) as exc:
        print(f"FAIL(2): schema unreadable: {exc}", file=sys.stderr)
        return 2
    if a.line is not None:
        cat, errs = classify_text(a.line, schema, a.write)
        counts, rows = {cat: 1}, ([] if cat in ("valid", "legacy") else [{"file": "--line", "line": 1, "category": cat, "errors": errs}])
        files = 0
    else:
        paths = list(a.files) + (ledger_files(a.campus_root) if a.campus_root else [])
        if not paths and not a.campus_root:
            print("FAIL(2): no files given (pass FILE..., --campus-root or --line)", file=sys.stderr)
            return 2
        counts, rows = scan(paths, schema, a.write, Path(a.campus_root) if a.campus_root and not a.files else None)
        files = len(paths)
    failing = counts.get("invalid", 0) + counts.get("malformed", 0) + (counts.get("legacy", 0) if a.write else 0)
    if a.json:
        print(json.dumps({"schema": str(a.schema), "files": files, "counts": counts, "failing": failing,
                          "rows": rows}, indent=2, sort_keys=True))
    else:
        for r in rows[:20]:
            print(f"  !! {r['file']}:{r['line']}: {r['category']} - {'; '.join(r['errors'][:3])}")
        summary = "  ".join(f"{k} {counts[k]}" for k in ("valid", "legacy", "invalid", "malformed") if counts.get(k))
        print(f"{'FAIL' if failing else 'OK'}: {sum(counts.values())} ledger lines  -  {summary or 'none'}")
    return 1 if failing else 0


if __name__ == "__main__":
    sys.exit(main())
