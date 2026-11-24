#!/usr/bin/env python3
"""kernel_kit.py - the campus copy of the kernel tools (`.campus-os/kernel/`).

Why: on some hosts the installed plugin and the campus live on different machines (Cowork: the
plugin sits in a cloud container, the campus is mounted in a separate device shell). A kernel tool
run from the plugin cannot see the campus, so the kernel keeps a small mirror of the tools a campus
needs INSIDE the campus, in the same folder layout, and every skill runs them from there. The
tools find their data files relative to themselves, so the mirror needs no code changes. Same
pattern as `.campus-os/resolve-seat.py` (5.2.4).

This file is the ONE owner of the kit list (CORE, ON_DEMAND, PLUGIN_ONLY, MAINTAINER_ONLY).

  manifest   build the kit manifest from a kernel tree; --write saves tools/kit-manifest.json,
             --check exits 1 when the committed manifest is stale (package.py gate)
  check      verify a campus kit file by file; --manifest takes the expected hashes and version
             from the INSTALLED PLUGIN (the tamper check; run the plugin's own copy of this tool
             when the shell can see it), else from the campus KIT.json (catches damaged copies
             only); current / stale / newer against the installed plugin
  install    copy the kit from a kernel tree into a campus (hosts where both are visible);
             forward-only (a newer kit is replaced only with --repair, on the owner's say-so);
             never writes through a symlink or outside the kit folder

Where the plugin cannot see the campus, the model copies each listed file with its file tools
(read the plugin file, write the same bytes to `.campus-os/kernel/<same path>`), writes
`tools/kit-manifest.json` as `.campus-os/kernel/KIT.json`, then runs `check` in the shell that can
see the campus. Stock Python only. Exit codes: 0 ok, 1 needs action/refused, 2 usage/runtime error.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import secrets
import sys
from pathlib import Path

KERNEL = Path(__file__).resolve().parent.parent
KIT_DIR = ".campus-os/kernel"
STAMP = "KIT.json"
MANIFEST = "tools/kit-manifest.json"
KIT_NAME = "campus-os-kernel-kit"

# Copied at founding and on every update; every team run needs these.
CORE = (
    "tools/kernel_kit.py",
    "tools/mint_run_id.py",
    "tools/resolve_context.py",
    "tools/contract.py",
    "tools/validate_results.py",
    "tools/validate_registry.py",
    "tools/materialize_registration_spec.py",
    "tools/generate_task_index.py",
    "tools/wo.py",
    "contracts/campus.json",
    "schemas/results.schema.json",
    "templates/registration-block-spec.md",
    "templates/work-orders/quick.md",
    "templates/work-orders/full.md",
    "templates/work-orders/standing.md",
    "templates/work-orders/events.md",
)
# Copied the first time a skill needs them on a kernel version (campus-doctor, update-workspace).
ON_DEMAND = (
    "tools/doctor_evidence.py",
    "tools/check_cron_parity.py",
    "tools/seat_contract_checks.py",
    "tools/context-weight.mjs",
    "tools/context-prune.mjs",
    "tools/prune-write.mjs",
    "tools/validate_ledger.py",
    "tools/check_runtime_drift.py",
    "schemas/ledger-line.schema.json",
    "templates/context-files.md",
)
# The installed manifest travels with the kit so doctor_evidence can read the kit's version.
MANIFEST_CANDIDATES = (".claude-plugin/plugin.json", ".codex-plugin/plugin.json", "plugin.json")
# Run against the campus but need more of the plugin than a kit should carry. The skill runs them
# from the plugin root where it can, else does the step by hand and says so.
PLUGIN_ONLY = {
    "tools/gen_department_entries.py": "reads packs/ (the whole niche pack)",
    "tools/resolve-seat.py": "has its own campus copy, .campus-os/resolve-seat.py (5.2.4)",
    "tools/update_undo.py": "its snapshot runs before the kit is copied (5.3.8)",
}
# Build and release tools; never run against an owner's campus.
MAINTAINER_ONLY = (
    "tools/package.py", "tools/build_contract.py", "tools/build_niche.py", "tools/qa_workspace_json.py",
    "tools/contract.mjs", "tools/lint_managers.py",
)
TIERS = {"core": CORE, "on_demand": ON_DEMAND}


def read_input(source: str) -> str:
    """Text from a file path, or from stdin when source is '-'. A leading byte-order mark is
    dropped: Windows PowerShell 5.1 adds one when it pipes text to a program, and Notepad can
    save one, and json.loads refuses it (5.3.7)."""
    if source == "-":
        return sys.stdin.buffer.read().decode("utf-8-sig")
    return Path(source).read_text(encoding="utf-8-sig")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def version_key(value) -> tuple:
    parts = re.findall(r"\d+", str(value or ""))
    return tuple(int(p) for p in parts[:3]) if parts else (-1,)


def kernel_version(kernel: Path) -> str | None:
    for rel in MANIFEST_CANDIDATES:
        p = kernel / rel
        if p.is_file():
            return json.loads(p.read_text(encoding="utf-8")).get("version")
    return None


def build_manifest(kernel: Path) -> dict:
    manifests = tuple(rel for rel in MANIFEST_CANDIDATES if (kernel / rel).is_file())
    tiers = {"core": list(CORE) + list(manifests), "on_demand": list(ON_DEMAND)}
    files = {}
    for rel in tiers["core"] + tiers["on_demand"]:
        p = kernel / rel
        if not p.is_file():
            raise FileNotFoundError(f"kit file missing from the kernel tree: {rel}")
        files[rel] = sha256(p)
    return {"kit": KIT_NAME, "kernel_version": kernel_version(kernel), "dir": KIT_DIR,
            "tiers": tiers, "files": files}


def render(manifest: dict) -> str:
    return json.dumps(manifest, indent=2, sort_keys=True) + "\n"


class UnsafePath(PermissionError):
    """A kit path is a symlink or resolves outside the kit folder."""


def _safe_dest(campus: Path, rel: str) -> Path:
    """The kit file's path, refusing any symlink on the way down from the campus root.

    A campus can be shared or written by other teams; a planted link at `.campus-os`, the kit
    folder, a subfolder or the file itself would make a write land outside the campus."""
    root = campus.resolve()
    kit = root / KIT_DIR
    dest = kit / rel
    node = root
    for part in dest.relative_to(root).parts:
        node = node / part
        if node.is_symlink():
            raise UnsafePath(f"refused: {node} is a symlink; kit paths must be real files and folders")
    if not str(dest.resolve()).startswith(str(kit.resolve()) + os.sep) and dest.resolve() != kit.resolve():
        raise UnsafePath(f"refused: {rel} resolves outside {KIT_DIR}")
    return dest


def _write(dest: Path, data: bytes) -> None:
    # Write a fresh file and rename it over the old one: never writes THROUGH an existing link.
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f".{dest.name}.{secrets.token_hex(4)}.tmp")
    with open(tmp, "xb") as handle:
        handle.write(data)
    os.replace(tmp, dest)


def _reference(ref: dict) -> tuple[dict, dict]:
    """The tier lists and hashes from a manifest or stamp, validated: strings only, no duplicates."""
    tiers, files = ref.get("tiers"), ref.get("files")
    if not isinstance(tiers, dict) or not isinstance(files, dict):
        raise ValueError("kit reference has no tiers/files")
    out = {}
    for name in ("core", "on_demand"):
        rels = tiers.get(name, [])
        if not isinstance(rels, list) or not all(isinstance(r, str) and r for r in rels):
            raise ValueError(f"kit reference tier {name!r} is not a list of paths")
        out[name] = list(dict.fromkeys(rels))
    if not all(isinstance(k, str) and isinstance(v, str) for k, v in files.items()):
        raise ValueError("kit reference hashes are not path -> sha256 strings")
    return out, files


def _unexpected(campus: Path, expected: set) -> list:
    """Every entry under the kit the reference does not name: extra modules, caches, links.

    A kit tool imports from its own folder, so an unlisted `secrets.py` or a planted
    `__pycache__/*.pyc` would run even though every listed file checks (Codex audit F1, 5.2.14)."""
    kit = campus / KIT_DIR
    found = []
    for folder, dirs, files in os.walk(kit, followlinks=False):
        for name in sorted(dirs) + sorted(files):
            path = Path(folder) / name
            rel = path.relative_to(kit).as_posix()
            if path.is_symlink():
                found.append(rel)
            elif path.is_file() and rel != STAMP and rel not in expected:
                found.append(rel)
            elif path.is_dir() and name == "__pycache__":
                found.append(rel + "/")
    return sorted(set(found))


def check(campus: Path, installed: str | None = None, tier: str = "core", manifest: dict | None = None) -> dict:
    """Check the campus kit.

    With `manifest` (the INSTALLED PLUGIN's tools/kit-manifest.json), the expected file list,
    hashes and version come from the plugin, never from the campus: this is the tamper check.
    Without it, the campus KIT.json is the only reference: that catches damaged copies, not
    deliberate edits (anyone who can edit a kit file can edit KIT.json too).
    Every tier file that is present is checked; `tier="all"` also requires the on-demand files.
    Any file the reference does not name makes the kit not ok: the kit runs only known bytes."""
    kit = campus / KIT_DIR
    stamp = kit / STAMP
    out = {"kit_dir": str(kit), "present": stamp.is_file() and not stamp.is_symlink(), "kernel_version": None,
           "installed_version": installed, "anchor": "plugin-manifest" if manifest else "campus-stamp",
           "version": None, "missing": [], "mismatched": [], "unexpected": [], "stamp_invalid": False, "ok": False}
    if not out["present"]:
        out["version"] = "missing"
        return out
    try:
        data = json.loads(stamp.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("KIT.json is not an object")
        out["kernel_version"] = data.get("kernel_version")
        tiers, files = _reference(manifest or data)
    except ValueError as exc:
        out.update(stamp_invalid=True, version="invalid", error=str(exc))
        return out
    if manifest and installed is None:
        out["installed_version"] = installed = manifest.get("kernel_version")
    for rel in tiers["core"] + tiers["on_demand"]:
        try:
            p = _safe_dest(campus, rel)
        except (UnsafePath, ValueError):  # a link, or a path outside the kit: never read
            out["mismatched"].append(rel)
            continue
        if not p.is_file():
            if rel in tiers["core"] or tier == "all":
                out["missing"].append(rel)
        elif sha256(p) != files.get(rel):
            out["mismatched"].append(rel)
    out["unexpected"] = _unexpected(campus, set(tiers["core"]) | set(tiers["on_demand"]))
    if installed is None:
        out["version"] = "unchecked"
    else:
        a, b = version_key(out["kernel_version"]), version_key(installed)
        out["version"] = "current" if a == b else "stale" if a < b else "newer"
    out["ok"] = not (out["missing"] or out["mismatched"] or out["unexpected"]) and \
        out["version"] in ("current", "unchecked")
    return out


def _quarantine(campus: Path, rels: list) -> str | None:
    """Move unlisted kit entries out of the kit (never delete them: they may be someone's work).

    The destination is a NEW folder with an unguessable name under `.campus-os/kernel-quarantine/`,
    created here and checked for links all the way down, so a planted link cannot send the move
    outside the campus or into a folder someone prepared in advance (5.2.17)."""
    if not rels:
        return None
    root = campus.resolve()
    holder = root / ".campus-os" / "kernel-quarantine"
    for node in (root / ".campus-os", holder):
        if node.is_symlink():
            raise UnsafePath(f"refused: {node} is a symlink; quarantine never follows a link")
    holder.mkdir(exist_ok=True)
    if holder.is_symlink() or not holder.is_dir():
        raise UnsafePath(f"refused: {holder} is not a real folder")
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = holder / f"{stamp}-{secrets.token_hex(6)}"
    base.mkdir()  # fresh: fails rather than reuse anything that already exists
    for rel in rels:
        src = root / KIT_DIR / rel.rstrip("/")
        if not (src.exists() or src.is_symlink()):
            continue
        dest = base / rel.rstrip("/")
        folder = base
        for part in dest.relative_to(base).parts[:-1]:  # only folders this call creates
            folder = folder / part
            if folder.is_symlink():
                raise UnsafePath(f"refused: {folder} is a symlink")
            folder.mkdir(exist_ok=True)
        if dest.exists() or dest.is_symlink():
            raise UnsafePath(f"refused: {dest} already exists")
        os.replace(src, dest)  # moves a link itself, never its target
    return str(base)


def install(kernel: Path, campus: Path, tier: str = "core", repair: bool = False) -> dict:
    """Copy the kit from a plugin tree. Forward-only: a kit stamped newer than this plugin is left
    alone unless the owner asked to repair it (`repair`): a newer stamp can be genuine (the plugin
    on this machine is old) or planted, and only the owner can tell which. Entries the plugin's
    list does not name are moved to `.campus-os/kernel-quarantine/` first, so they cannot run."""
    manifest = build_manifest(kernel)
    stamp = _safe_dest(campus, STAMP)
    if stamp.is_file():
        have = json.loads(stamp.read_text(encoding="utf-8")).get("kernel_version")
        if version_key(have) > version_key(manifest["kernel_version"]) and not repair:
            raise PermissionError(f"refused: the campus kit says {have}, newer than this plugin "
                                  f"({manifest['kernel_version']}); update the plugin (never downgrade the kit), "
                                  "or, if the owner says the stamp is wrong, re-run with --repair")
    kit = campus / KIT_DIR  # _safe_dest above refused a link at .campus-os, kernel or KIT.json
    expected = set(manifest["tiers"]["core"]) | set(manifest["tiers"]["on_demand"])
    quarantined = _unexpected(campus, expected) if kit.is_dir() else []
    links = [rel for rel in quarantined if (kit / rel.rstrip("/")).is_symlink()]
    if links:
        # A link inside the kit is never followed, moved or written through; the owner looks at it.
        raise UnsafePath(f"refused: {', '.join(links)} in {KIT_DIR} is a symlink; remove it, then re-run")
    where = _quarantine(campus, quarantined)
    rels = manifest["tiers"]["core"] + (manifest["tiers"]["on_demand"] if tier == "all" else [])
    copied = []
    for rel in rels:
        dest = _safe_dest(campus, rel)
        if dest.is_file() and sha256(dest) == manifest["files"][rel]:
            continue
        _write(dest, (kernel / rel).read_bytes())
        copied.append(rel)
    _write(stamp, render(manifest).encode("utf-8"))
    return {"kit_dir": str(kit), "kernel_version": manifest["kernel_version"], "copied": copied,
            "quarantined": quarantined, "quarantine_dir": where}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    m = sub.add_parser("manifest")
    m.add_argument("--kernel", default=str(KERNEL))
    g = m.add_mutually_exclusive_group()
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    c = sub.add_parser("check")
    c.add_argument("--campus-root", default=".")
    c.add_argument("--installed-version")
    c.add_argument("--tier", choices=("core", "all"), default="core")
    c.add_argument("--manifest", help="the installed plugin's tools/kit-manifest.json ('-' = stdin); "
                                      "expected hashes and version come from it, not from the campus")
    c.add_argument("--json", action="store_true")
    i = sub.add_parser("install")
    i.add_argument("--kernel", default=str(KERNEL))
    i.add_argument("--campus-root", default=".")
    i.add_argument("--tier", choices=("core", "all"), default="core")
    i.add_argument("--repair", action="store_true", help="owner-approved: replace a kit stamped newer than this plugin")
    return parser


def main(argv=None) -> int:
    try:
        args = _parser().parse_args(argv)
        if args.command == "manifest":
            kernel = Path(args.kernel).resolve()
            text = render(build_manifest(kernel))
            target = kernel / MANIFEST
            if args.check:
                current = target.read_text(encoding="utf-8") if target.is_file() else ""
                if current != text:
                    print(f"STALE: {MANIFEST} - run python3 tools/kernel_kit.py manifest --write", file=sys.stderr)
                    return 1
                print(f"OK: {MANIFEST} is current")
            elif args.write:
                target.write_text(text, encoding="utf-8")
                print(f"wrote {MANIFEST}")
            else:
                print(text, end="")
            return 0
        if args.command == "check":
            manifest = None
            if args.manifest:
                manifest = json.loads(read_input(args.manifest))
            result = check(Path(args.campus_root).resolve(), args.installed_version, args.tier, manifest)
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(("OK" if result["ok"] else "NEEDS ACTION") +
                      f": kit {result['kernel_version']} ({result['version']}), "
                      f"{len(result['missing'])} missing, {len(result['mismatched'])} mismatched, "
                      f"{len(result['unexpected'])} unexpected")
            return 0 if result["ok"] else 1
        result = install(Path(args.kernel).resolve(), Path(args.campus_root).resolve(), args.tier, args.repair)
        print(json.dumps(result, indent=2))
        return 0
    except PermissionError as exc:
        print(f"REFUSED(1): {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError) as exc:
        print(f"FAIL(2): {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
