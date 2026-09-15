#!/usr/bin/env python3
"""
QA regression validator - workspace.json interview-vs-record parity
(Campus AI OS v4.1.4). Sibling of the founding-vs-migration parity gate:
what the interview collects must actually land in the machine-read record.

Catches the v4.1.0 defect: a completed full-onboarding (path A) wrote the
shared/*.md files but left workspace.json's business block empty / holding a
prose placeholder ("(fill in during full onboarding)").

Checks any workspace.json:
  1. Parses as JSON.
  2. `business` is the CANONICAL NESTED object with string fields
     `what`, `sells_today`, `audience` (schema-drift guard).
  3. No FLAT top-level business schema (`business` must not be a string; no
     top-level `sell` key).
  4. NO placeholder / sentinel strings ANYWHERE in the file text.
  5. `version` + `structure` present; the matching filing key present.
With --after-full-onboarding (or --require-populated): the three business
fields must be NON-EMPTY (a completed path-A run populated them).

Usage:
  python3 tools/qa_workspace_json.py <path/to/workspace.json> [--after-full-onboarding]
Exit 0 = pass; non-zero = fail (with the reasons printed).
"""
import json, re, sys, os

PLACEHOLDER_PATTERNS = [
    r"fill\s*in", r"\(fill", r"to\s*be\s*filled", r"\btbd\b", r"placeholder",
    r"during\s+full\s+onboarding", r"your\s+answer\s+here", r"<fill", r"_{3,}",
    r"coming\s+soon", r"lorem ipsum",
]

def fail(reasons):
    print("QA FAIL - workspace.json interview-vs-record parity:")
    for r in reasons:
        print("  -", r)
    sys.exit(1)

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    require_pop = ("--after-full-onboarding" in sys.argv) or ("--require-populated" in sys.argv)
    if not args:
        print("usage: qa_workspace_json.py <workspace.json> [--after-full-onboarding]", file=sys.stderr)
        sys.exit(2)
    path = args[0]
    if not os.path.exists(path):
        print("QA FAIL - file not found:", path); sys.exit(1)
    raw = open(path, encoding="utf-8", errors="replace").read()

    reasons = []
    # 1. parse
    try:
        d = json.loads(raw)
    except Exception as e:
        fail(["not valid JSON: " + str(e)])

    # 4. placeholder scan (raw text, case-insensitive)
    for pat in PLACEHOLDER_PATTERNS:
        m = re.search(pat, raw, re.I)
        if m:
            reasons.append("placeholder/sentinel string found: '%s' (a machine-read field must never hold prose; empty is \"\")" % m.group(0))

    # 2 + 3. business schema
    biz = d.get("business")
    if biz is None:
        reasons.append("missing `business` key")
    elif isinstance(biz, str):
        reasons.append("`business` is a flat string - must be the nested object {what, sells_today, audience}")
    elif isinstance(biz, dict):
        for k in ("what", "sells_today", "audience"):
            if k not in biz:
                reasons.append("business.%s missing" % k)
            elif not isinstance(biz[k], str):
                reasons.append("business.%s must be a string" % k)
        if require_pop:
            for k in ("what", "sells_today", "audience"):
                if isinstance(biz.get(k), str) and not biz[k].strip():
                    reasons.append("business.%s is empty after a completed onboarding (write-back seam did not fire)" % k)
    else:
        reasons.append("`business` must be an object")

    if "sell" in d:
        reasons.append("flat top-level `sell` key present - schema drift; fold into business.sells_today")

    # 5. version + structure + filing key
    if not d.get("version"):
        reasons.append("missing `version` marker")
    structure = d.get("structure")
    if not structure:
        reasons.append("missing `structure` (filing choice)")
    elif structure in ("departments", "clients", "projects"):
        if structure not in d:
            reasons.append("structure is '%s' but the matching filing key is missing" % structure)
    elif structure == "mix":
        # canonical mix: departments ALWAYS + at least one of clients/projects
        if "departments" not in d:
            reasons.append("structure is 'mix' but `departments` key is missing")
        if not ("clients" in d or "projects" in d):
            reasons.append("structure is 'mix' but no secondary filing key (clients/projects) present - a mix is departments PLUS at least one of clients/projects")
    else:
        reasons.append("unknown structure value: '%s' (expected departments/clients/projects/mix)" % structure)

    if reasons:
        fail(reasons)
    scope = "populated" if require_pop else "schema"
    print("QA OK - workspace.json passes interview-vs-record parity (%s check)." % scope)
    print("  business:", json.dumps(d.get("business"), ensure_ascii=False))

if __name__ == "__main__":
    main()
