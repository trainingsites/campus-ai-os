#!/usr/bin/env python3
"""resolve_context.py - find the campus, and the file a shared-context concept resolves to (5.2.12).

One testable function for the two rules in templates/context-files.md that teams kept re-implementing
in prose (and got wrong on real installs):

  campus rule   a folder holding workspace.json plus an accepted entry file (root or dean/),
                found by walking up from the working folder; if none is above, exactly one campus
                among the folder's own children (5.2.16 - hosts often open the folder above the
                campus). Two or more children: not found, listed, the owner picks. Never a fixed name.
  read order    per concept, contracts/campus.json `read_order`: founding name first (unless the
                row says canonical wins), then canonical, then aliases; each candidate is also
                matched case-insensitively before the next is tried (5.2.13, audit F1).

Usage:
  python3 tools/resolve_context.py --find-campus [--start DIR]
  python3 tools/resolve_context.py --concept icp [--campus-root DIR | --start DIR] [--json]

Prints the path, or nothing when absent. Exit 0 found · 3 not found · 1 usage · 2 contract error.
Read-only; stock Python. platform: claude-code; seat: m4-claude-code
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

# Kit copies run from .campus-os/kernel/tools, a folder other campus writers can reach (Codex audit F1,
# 5.2.14). Sibling modules are found at the END of the path, so a planted file can never shadow the
# standard library, and Python's bytecode cache points at an unguessable path that does not exist,
# so a planted __pycache__ is never read and nothing is written into the kit. Run as `python3 -I -B`.
NO_CACHE = os.path.join(tempfile.gettempdir(), f"campus-os-nocache-{os.getpid()}-{os.urandom(8).hex()}")
if __name__ == "__main__":  # only when run as a tool; an importing program keeps its own settings
    sys.dont_write_bytecode = True
    sys.pycache_prefix = NO_CACHE
sys.path.append(str(Path(__file__).resolve().parent))
from contract import ContractError, Resolver  # noqa: E402


def is_campus(folder: Path, entry_names) -> bool:
    if not (folder / "workspace.json").is_file():
        return False
    return any((folder / n).is_file() or (folder / "dean" / n).is_file() for n in entry_names)


def child_campuses(start: Path, entry_names) -> list:
    """Campuses one level BELOW the start folder: real folders only, no links, no hidden folders."""
    try:
        kids = sorted(e for e in start.iterdir() if e.is_dir() and not e.is_symlink() and not e.name.startswith("."))
    except OSError:
        return []
    return [k for k in kids if is_campus(k, entry_names)]


def find_campus(start: Path, entry_names):
    """Walk up from the start folder; else accept exactly ONE campus among its children.

    Hosts often open the folder ABOVE the campus (Cowork mounting `MyBusiness/` when the campus is
    `MyBusiness/Campus/`). Two or more child campuses are never guessed between: the owner
    picks. Returns (campus or None, how: "here" | "above" | "child" | None, candidates)."""
    start = start.resolve()
    for folder in (start, *start.parents):
        if is_campus(folder, entry_names):
            return folder, ("here" if folder == start else "above"), [folder]
    kids = child_campuses(start, entry_names)
    if len(kids) == 1:
        return kids[0], "child", kids
    return None, None, kids


def context_dir(campus):
    """Founded campus -> {campus}/shared. Otherwise the peer folder ./teams-shared/context."""
    return campus / "shared" if campus else Path("teams-shared/context").resolve()


def resolve(concept: str, folder: Path, resolver: Resolver):
    row = resolver.resolve_context(concept)
    if not row["concept"]:
        raise ValueError(f"unknown concept: {concept}")
    if not folder.is_dir():
        return row, None
    # Match against the real listing, never is_file(name): on a case-insensitive disk (macOS)
    # that reports `brand.md` for a file actually named `BRAND.md`. Priority comes first: each
    # candidate is matched (exact spelling, else case-insensitively) BEFORE the next candidate is
    # tried. Two passes (all exact, then all case-insensitive) let a lower-priority exact name beat
    # a preferred file in other capitals - `offers.md` over `OFFERS-SUMMARY.MD` (5.2.12 audit F1).
    actual = sorted(e.name for e in folder.iterdir() if e.is_file())
    for name in row["read_order"]:
        if name in actual:
            return row, folder / name
        for real in actual:
            if real.lower() == name.lower():
                return row, folder / real
    return row, None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--find-campus", action="store_true")
    mode.add_argument("--concept")
    ap.add_argument("--campus-root")
    ap.add_argument("--start", default=".")
    ap.add_argument("--contract")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    try:
        resolver = Resolver(args.contract)
    except ContractError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    names = resolver.hosts["entry_file_read_names"]
    candidates = []
    if args.campus_root:
        campus = Path(args.campus_root).resolve()
        if not is_campus(campus, names):
            print(f"USAGE: not a campus (needs workspace.json + an entry file): {campus}", file=sys.stderr)
            return 1
    else:
        campus, how, candidates = find_campus(Path(args.start), names)

    if args.find_campus:
        many = [] if campus or args.campus_root else [str(c) for c in candidates]
        if args.json:
            out = {"campus_root": str(campus) if campus else None}
            if not args.campus_root:
                out["found"] = how
                if many:
                    out["several_campuses"] = many  # never picked automatically: ask the owner
            print(json.dumps(out))
        elif campus:
            print(campus)
        elif many:
            print("SEVERAL CAMPUSES below this folder - ask the owner which one:\n  " + "\n  ".join(many), file=sys.stderr)
        return 0 if campus else 3

    if campus is None and len(candidates) > 1:
        print("SEVERAL CAMPUSES below this folder - ask the owner which one, then pass --campus-root:\n  "
              + "\n  ".join(str(c) for c in candidates), file=sys.stderr)
        return 3
    try:
        row, path = resolve(args.concept, context_dir(campus), resolver)
    except ValueError as exc:
        print(f"USAGE: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({"concept": row["concept"], "campus_root": str(campus) if campus else None,
                          "path": str(path) if path else None, "read_order": row["read_order"],
                          "write_to": str(path) if path else str(context_dir(campus) / (row["founding_writes"] or row["canonical"]))}))
    elif path:
        print(path)
    return 0 if path else 3


if __name__ == "__main__":
    raise SystemExit(main())
