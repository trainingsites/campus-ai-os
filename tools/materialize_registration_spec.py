#!/usr/bin/env python3
"""materialize_registration_spec.py - the campus's registration spec is GENERATED, not copied
(Campus AI OS 5.2.0 Phase 3.6; shape per Codex critique 2026-09-05 #3).

    .campus-os/registration-block-spec.md  =  kernel templates/registration-block-spec.md
                                              + .campus-os/registration-overrides.json
                                              + a stamp line that records both inputs

Why not a bare pointer: the Foundry (`_common.department_enum`), `tools/validate_registry.py`
and campus-doctor check 7 all READ the campus file - a pointer is not a transparent replacement,
and it would delete the campus's legitimate overrides (owner-added departments, owner notes).
Why not "md5 equal": a campus with overrides is deliberately different from the template.
The stamp is what makes drift detectable without forbidding difference.

Overrides file (`.campus-os/registration-overrides.json`, owner-owned, additive only):
  {"schema_version": "1",
   "departments_extra": ["coaching-delivery"],           # appended to the department enum line
   "annotations": ["free-text markdown lines the owner wrote"],   # kept under "## Campus notes"
   "updated": "YYYY-MM-DD"}

Usage:
  python3 tools/materialize_registration_spec.py --campus-root DIR            # write/refresh the campus copy
  python3 tools/materialize_registration_spec.py --campus-root DIR --check    # status only (exit 0 current / 1 not)
  python3 tools/materialize_registration_spec.py --campus-root DIR --capture-notes
        # one-time: turn a hand-edited copy's non-template lines into overrides.json, then materialize
  add --json for machine output, --dry-run to print instead of write, --kernel DIR to point at a tree.
Exit 0 ok · 1 refused / not current · 2 cannot run.
"""
import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

KERNEL = Path(__file__).resolve().parent.parent
SPEC_REL = Path(".campus-os") / "registration-block-spec.md"
OVR_REL = Path(".campus-os") / "registration-overrides.json"
DEPT_LINE = re.compile(r'^(\s*"department"\s*:\s*")([^"]+)(".*)$', re.M)
STAMP_RE = re.compile(r"^<!-- campus-ai-os:registration-block-spec materialized \| template_sha256=([0-9a-f]{64}) "
                      r"\| overrides_sha256=([0-9a-f]{64}|none) \| kernel=([^ |]+) \| generated=([^ ]+) -->\s*$")
DEPT_ID = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
NOTES_HEADING = "## Campus notes (owner-written; preserved across upgrades)"


def sha(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode("utf-8")).hexdigest()


def fail2(msg):
    """Cannot run (bad input, missing template): exit 2, never 1 (1 = refused)."""
    print(f"FAIL(2): {msg}", file=sys.stderr)
    sys.exit(2)


def kernel_version(kernel):
    for rel in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json", "plugin.json"):
        p = kernel / rel
        if p.is_file():
            try:
                return str(json.loads(p.read_text(encoding="utf-8")).get("version", "unknown"))
            except ValueError:
                pass
    return "unknown"


def load_overrides(path):
    """Return (dict, raw_bytes_or_None). Invalid file -> SystemExit(2)."""
    if not path.is_file():
        return {"schema_version": "1", "departments_extra": [], "annotations": []}, None
    raw = path.read_bytes()
    try:
        d = json.loads(raw.decode("utf-8"))
    except ValueError as exc:
        fail2(f"{path} is not valid JSON: {exc}")
    if not isinstance(d, dict):
        fail2(f"{path} must be a JSON object")
    extra = d.get("departments_extra") or []
    notes = d.get("annotations") or []
    if not isinstance(extra, list) or not all(isinstance(x, str) and DEPT_ID.match(x) for x in extra):
        fail2(f"{path}: departments_extra must be a list of kebab-case ids")
    if not isinstance(notes, list) or not all(isinstance(x, str) for x in notes):
        fail2(f"{path}: annotations must be a list of strings")
    d["departments_extra"], d["annotations"] = extra, notes
    return d, raw


def render(template_text, overrides, kernel_ver, template_hash, overrides_hash, generated):
    m = DEPT_LINE.search(template_text)
    if not m:
        sys.exit("FAIL(2): template has no `\"department\":` enum line")
    values = [v.strip() for v in m.group(2).split("|") if v.strip()]
    for x in overrides["departments_extra"]:
        if x not in values:
            values.append(x)
    body = template_text[:m.start()] + m.group(1) + " | ".join(values) + m.group(3) + template_text[m.end():]
    if overrides["annotations"]:
        body = body.rstrip("\n") + "\n\n" + NOTES_HEADING + "\n\n" + "\n".join(overrides["annotations"]) + "\n"
    stamp = (f"<!-- campus-ai-os:registration-block-spec materialized | template_sha256={template_hash} "
             f"| overrides_sha256={overrides_hash} | kernel={kernel_ver} | generated={generated} -->\n\n")
    return stamp + body


def parse_stamp(text):
    first = text.split("\n", 1)[0]
    m = STAMP_RE.match(first)
    return {"template_sha256": m.group(1), "overrides_sha256": m.group(2),
            "kernel": m.group(3), "generated": m.group(4)} if m else None


def status(campus, kernel):
    """Classify the campus copy. Returns dict with 'state' in
    missing | current | stale-template | overrides-drift | hand-edited."""
    spec = campus / SPEC_REL
    tmpl = kernel / "templates" / "registration-block-spec.md"
    if not tmpl.is_file():
        fail2(f"kernel template not found: {tmpl}")
    t_hash = sha(tmpl.read_bytes())
    ovr, raw = load_overrides(campus / OVR_REL)
    o_hash = sha(raw) if raw is not None else "none"
    out = {"spec": str(spec), "template_sha256": t_hash, "overrides_sha256": o_hash,
           "departments_extra": ovr["departments_extra"], "annotations": len(ovr["annotations"]),
           "kernel": kernel_version(kernel)}
    if not spec.is_file():
        out["state"] = "missing"
        return out
    stamp = parse_stamp(spec.read_text(encoding="utf-8"))
    if stamp is None:
        out["state"] = "hand-edited"
        return out
    out["materialized_from_kernel"] = stamp["kernel"]
    if stamp["template_sha256"] != t_hash:
        out["state"] = "stale-template"
    elif stamp["overrides_sha256"] != o_hash:
        out["state"] = "overrides-drift"
    else:
        out["state"] = "current"
    return out


def capture(campus, kernel):
    """Turn a hand-edited copy into overrides: extra departments from its enum line,
    every non-blank line that is not in the template as an annotation."""
    spec = campus / SPEC_REL
    tmpl = kernel / "templates" / "registration-block-spec.md"
    cur = spec.read_text(encoding="utf-8")
    tt = tmpl.read_text(encoding="utf-8")
    if parse_stamp(cur):
        cur = cur.split("\n", 2)[2] if cur.count("\n") >= 2 else ""
    extra = []
    m_cur, m_t = DEPT_LINE.search(cur), DEPT_LINE.search(tt)
    if m_cur and m_t:
        tvals = {v.strip() for v in m_t.group(2).split("|")}
        for v in (x.strip() for x in m_cur.group(2).split("|")):
            if v and v not in tvals and v != "dean" and DEPT_ID.match(v):
                extra.append(v)
    tlines = {l.rstrip() for l in tt.splitlines()}
    notes = []
    in_notes = False
    for line in cur.splitlines():
        s = line.rstrip()
        if s == NOTES_HEADING:
            in_notes = True
            continue
        if not s.strip():
            continue
        if in_notes or (s not in tlines and not DEPT_LINE.match(s)):
            notes.append(s)
    return {"schema_version": "1", "departments_extra": extra, "annotations": notes,
            "updated": dt.date.today().isoformat(),
            "_note": "Captured from a hand-edited registration-block-spec.md by materialize_registration_spec.py. "
                     "Review: keep owner canon, delete lines that were merely an older kernel's prose."}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--campus-root", required=True)
    ap.add_argument("--kernel", default=str(KERNEL))
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--capture-notes", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="overwrite an existing overrides file on --capture-notes")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    campus, kernel = Path(a.campus_root).resolve(), Path(a.kernel).resolve()
    if not campus.is_dir():
        print(f"FAIL(2): campus root not found: {campus}", file=sys.stderr)
        return 2

    if a.check:
        st = status(campus, kernel)
        if a.json:
            print(json.dumps(st, indent=2))
        else:
            n = len(st["departments_extra"])
            msg = {"current": f"[OK] Registration spec current (kernel {st['kernel']}; {n} campus department override(s), {st['annotations']} note line(s))",
                   "stale-template": f"[--] Registration spec predates the installed kernel (materialized from {st.get('materialized_from_kernel')}, installed {st['kernel']}) - say \"refresh the spec\"",
                   "overrides-drift": "[--] Registration overrides changed since the spec was materialized - say \"refresh the spec\"",
                   "hand-edited": "[--] Registration spec is hand-edited (no materialization stamp) - say \"capture my spec notes\" and I'll keep them as overrides",
                   "missing": "[!!] Registration spec missing - /update-workspace writes it"}[st["state"]]
            print(msg)
        return 0 if st["state"] == "current" else 1

    ovr_path = campus / OVR_REL
    spec = campus / SPEC_REL
    if a.capture_notes:
        if not spec.is_file():
            print("FAIL(1): nothing to capture - no campus spec", file=sys.stderr)
            return 1
        if ovr_path.is_file() and not a.force:
            print(f"REFUSED(1): {ovr_path} exists - review it, or pass --force to recapture", file=sys.stderr)
            return 1
        cap = capture(campus, kernel)
        if a.dry_run:
            print(json.dumps(cap, indent=2))
            return 0
        else:
            ovr_path.parent.mkdir(parents=True, exist_ok=True)
            ovr_path.write_text(json.dumps(cap, indent=2) + "\n", encoding="utf-8")
            print(f"captured {len(cap['departments_extra'])} department override(s), {len(cap['annotations'])} note line(s) -> {ovr_path}")

    st = status(campus, kernel)
    if st["state"] == "hand-edited" and not ovr_path.is_file():
        print("REFUSED(1): campus spec is hand-edited and no overrides file exists - run --capture-notes first "
              "so the owner's lines survive (never clobber owner canon)", file=sys.stderr)
        return 1
    tmpl = kernel / "templates" / "registration-block-spec.md"
    ovr, raw = load_overrides(ovr_path)
    text = render(tmpl.read_text(encoding="utf-8"), ovr, kernel_version(kernel), sha(tmpl.read_bytes()),
                  sha(raw) if raw is not None else "none",
                  dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    if a.dry_run:
        sys.stdout.write(text)
        return 0
    changed = True
    if spec.is_file():
        old = spec.read_text(encoding="utf-8")
        # idempotent: same inputs -> only the generated= stamp differs; do not rewrite
        strip = lambda t: re.sub(r"generated=[^ ]+", "generated=", t, count=1)
        changed = strip(old) != strip(text)
    if changed:
        spec.parent.mkdir(parents=True, exist_ok=True)
        try:
            spec.write_text(text, encoding="utf-8")
        except PermissionError:
            # Some campuses keep the copy read-only (found on the reference campus:
            # mode 444). It is a generated file, so restore the owner write bit
            # and retry once; anything else is a real refusal.
            import os
            import stat
            try:
                os.chmod(spec, os.stat(spec).st_mode | stat.S_IWUSR)
                spec.write_text(text, encoding="utf-8")
            except OSError as exc:
                print(f"REFUSED(1): cannot write {spec}: {exc}", file=sys.stderr)
                return 1
    result = {"spec": str(spec), "written": changed, "state_before": st["state"],
              "departments_extra": ovr["departments_extra"], "annotations": len(ovr["annotations"])}
    if a.json:
        print(json.dumps(result, indent=2))
    else:
        print(("wrote " if changed else "unchanged ") + str(spec)
              + f" ({len(ovr['departments_extra'])} department override(s), {len(ovr['annotations'])} note line(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
