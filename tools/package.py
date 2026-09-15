#!/usr/bin/env python3
"""package.py - build the shipping artifacts for Campus AI OS.

Implements the Packaging & Interop SOP convention and v5.1 payload item 5:

  * ships `{name}-v{version}.plugin` AND a byte-identical `.zip`
  * contents at ARCHIVE ROOT - no wrapping folder
  * runs the conformance gate first; refuses to package a failing tree
  * **emits the md5 into a machine-readable record (`PACKAGE.json`) rather than
    a human retyping it into prose**
  * **version lockstep (5.2.0 Phase 2.3):** refuses to cut when the version
    homes disagree - the two plugin manifests, every `packs/*/pack.json`,
    `templates/registry.json` (`campus_os_version` + every `type: kernel`
    entry), and any skill frontmatter that carries `version:`.

Why the hash matters (S218): the recorded md5 for v5.0.3 was `8d031709` while
the artifact was `8d03170e` - one character, hand-copied. Same defect class as
the version marker: a shared fact with two homes and no reconciliation. The
packager now owns it. Nobody types a hash again.

Why lockstep matters (5.0.2, 5.1.8): v5.0.2 hardcoded `5.0.0` in seven places
across two skills, so a fresh install stamped itself 5.0.0 and said so out
loud; the 5.1.7 authoring tree carried a 5.1.8 package whose manifests still
said 5.1.7. A version is one fact with many homes; the packager is the only
place every home is read at once, so it is where the disagreement is refused.

Usage:
  python3 tools/package.py [--out DIR]        # default: ../ (the plugins shelf)
  python3 tools/package.py --check-lockstep   # report the version homes, exit 1 on disagreement
  python3 tools/package.py --src TREE ...     # operate on another tree (tests use this)
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_SRC = Path(__file__).resolve().parent.parent

# Never ship these into a buyer's install. `tests` holds the kernel's own
# fixtures (5.2.0 Phase 1.7); a buyer never needs them and they must not
# change the artifact hash.
EXCLUDE_DIRS = {".git", "__pycache__", ".DS_Store", "node_modules", ".pytest_cache", "tests"}
EXCLUDE_FILES = {".DS_Store"}

MANIFEST_PROBE = (".claude-plugin/plugin.json", ".codex-plugin/plugin.json", "plugin.json")
FRONTMATTER_VERSION_RE = re.compile(r"^version:\s*([0-9]+\.[0-9]+\.[0-9]+)\s*$", re.M)


def manifest(src: Path):
    """Resolve the owning manifest - same probe order as PLATFORM.md."""
    for rel in MANIFEST_PROBE:
        p = src / rel
        if p.is_file():
            return json.loads(p.read_text(encoding="utf-8"))
    sys.exit("FAIL: no plugin manifest found")


def version_homes(src: Path):
    """Every place the tree states its own version. Returns [(rel_path, version)].

    Missing homes are skipped (a tree without packs is not a mismatch); a home
    that exists but is unreadable is reported as version '<unreadable>' so it
    counts as a disagreement rather than vanishing.
    """
    homes = []

    def read_json(rel):
        p = src / rel
        if not p.is_file():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            homes.append((rel, "<unreadable>"))
            return None

    for rel in MANIFEST_PROBE:
        d = read_json(rel)
        if d is not None:
            homes.append((rel, str(d.get("version", "<missing>"))))

    for pack in sorted(src.glob("packs/*/pack.json")):
        rel = str(pack.relative_to(src))
        d = read_json(rel)
        if d is not None:
            homes.append((rel, str(d.get("version", "<missing>"))))

    reg = read_json("templates/registry.json")
    if reg is not None:
        homes.append(("templates/registry.json:campus_os_version",
                      str(reg.get("campus_os_version", "<missing>"))))
        for e in reg.get("teams", []):
            if isinstance(e, dict) and e.get("type") == "kernel":
                homes.append((f"templates/registry.json:teams[{e.get('team')}].version",
                              str(e.get("version", "<missing>"))))

    # Most skills carry their OWN semver (skill-creator 3.1.0, hr-recruit 0.3.0 ...)
    # and are not version homes. These three are stamped with the OS version on
    # every cut (they were the "seven places across two skills" in 5.0.2) and
    # must move in lockstep. Add a skill here only when its frontmatter version
    # is meant to equal the OS version.
    OS_STAMPED_SKILLS = {"campus-start", "campus-doctor", "update-workspace"}
    for skill in sorted(src.glob("skills/*/SKILL.md")):
        if skill.parent.name not in OS_STAMPED_SKILLS:
            continue
        try:
            text = skill.read_text(encoding="utf-8")
        except OSError:
            homes.append((str(skill.relative_to(src)), "<unreadable>"))
            continue
        fm = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
        head = fm.group(1) if fm else ""
        m = FRONTMATTER_VERSION_RE.search(head)
        if m:
            homes.append((str(skill.relative_to(src)), m.group(1)))

    return homes


def lockstep(src: Path, verbose=True):
    """True when every version home agrees. Prints the table when verbose."""
    homes = version_homes(src)
    distinct = sorted({v for _, v in homes})
    ok = len(distinct) == 1
    if verbose:
        width = max(len(r) for r, _ in homes) if homes else 0
        majority = max(distinct, key=lambda x: sum(1 for _, v in homes if v == x)) if homes else None
        for rel, v in homes:
            flag = "  " if v == majority else "!!"
            print(f"  {flag} {rel.ljust(width)}  {v}")
        if ok:
            print(f"OK: version lockstep - {len(homes)} homes all say {distinct[0]}")
        else:
            print(f"FAIL: version lockstep - {len(homes)} homes disagree: {', '.join(distinct)}")
    return ok, homes, distinct


def gate(src: Path):
    """Refuse to package a tree that does not pass its own conformance gate."""
    r = subprocess.run(
        [sys.executable, str(src / "tools" / "build_niche.py"), "--check"],
        capture_output=True, text=True,
    )
    print(r.stdout.strip() or r.stderr.strip())
    if r.returncode != 0:
        sys.exit("FAIL: conformance gate failed - not packaging")
    # 5.2.0 Phase 3.7: the machine-readable contract must be current with its
    # sources and every code literal it mirrors (same rule as version lockstep:
    # a shared fact with two homes needs a reconciler, and this is it).
    contract_tool = src / "tools" / "build_contract.py"
    if contract_tool.is_file():
        r = subprocess.run([sys.executable, str(contract_tool), "--check"], capture_output=True, text=True)
        print(r.stdout.strip() or r.stderr.strip())
        if r.returncode != 0:
            sys.exit("FAIL: contracts/campus.json is stale or a literal drifted - run tools/build_contract.py, then re-run")


def changelog_gate(src: Path, version: str):
    """Refuse to cut a version that has no CHANGELOG.md entry (5.2.6). A release
    with no recorded change is the same defect class as a hand-copied hash: a
    fact with no home. The entry must exist and carry at least one line."""
    p = src / "CHANGELOG.md"
    if not p.is_file():
        sys.exit("FAIL: CHANGELOG.md missing - not packaging")
    text = p.read_text(encoding="utf-8")
    m = re.search(r"^## \[" + re.escape(version) + r"\][^\n]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m or not m.group(1).strip():
        sys.exit(f"FAIL: CHANGELOG.md has no entry for [{version}] - write it (rename [Unreleased]), then re-run")
    print(f"OK: CHANGELOG.md has an entry for [{version}]")


def collect(src: Path):
    files = []
    for p in sorted(src.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(src)
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        if rel.name in EXCLUDE_FILES:
            continue
        files.append((p, rel))
    return files


def build(src: Path, out_dir: Path):
    ok, _, _ = lockstep(src)
    if not ok:
        sys.exit("FAIL: version homes disagree - not packaging (fix every home, then re-run)")
    gate(src)
    changelog_gate(src, manifest(src)["version"])
    m = manifest(src)
    name, version = m["name"], m["version"]
    out_dir.mkdir(parents=True, exist_ok=True)

    files = collect(src)
    zip_path = out_dir / f"{name}-v{version}.zip"

    # Deterministic archive: sorted entries, fixed timestamps. Two runs of the
    # same tree produce the same bytes - which is what makes the hash meaningful.
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for src_file, rel in files:
            zi = zipfile.ZipInfo(str(rel), date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, src_file.read_bytes())

    data = zip_path.read_bytes()
    md5 = hashlib.md5(data).hexdigest()
    sha256 = hashlib.sha256(data).hexdigest()

    # The .plugin is a byte-identical copy (SOP convention).
    plugin_path = out_dir / f"{name}-v{version}.plugin"
    plugin_path.write_bytes(data)
    assert hashlib.md5(plugin_path.read_bytes()).hexdigest() == md5

    record = {
        "name": name,
        "version": version,
        "built_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "artifacts": [zip_path.name, plugin_path.name],
        "byte_identical": True,
        "entry_count": len(files),
        "md5": md5,
        "sha256": sha256,
        "note": "Emitted by tools/package.py. Never hand-copy a hash - cite this file.",
    }
    (out_dir / f"{name}-v{version}.PACKAGE.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )

    print(f"\nOK: packaged {name} v{version}")
    print(f"  {zip_path.name}")
    print(f"  {plugin_path.name}   (byte-identical)")
    print(f"  entries : {len(files)}")
    print(f"  md5     : {md5}")
    print(f"  record  : {name}-v{version}.PACKAGE.json  <- cite this, never retype the hash")
    return record


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(DEFAULT_SRC), help="kernel tree to package (default: this tree)")
    ap.add_argument("--out", default=None, help="shelf directory (default: the tree's parent)")
    ap.add_argument("--check-lockstep", action="store_true",
                    help="only report the version homes; exit 1 if they disagree")
    args = ap.parse_args()
    src = Path(args.src).resolve()
    if args.check_lockstep:
        ok, _, _ = lockstep(src)
        sys.exit(0 if ok else 1)
    build(src, Path(args.out) if args.out else src.parent)
