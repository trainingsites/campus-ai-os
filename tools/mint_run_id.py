#!/usr/bin/env python3
"""Mint and parse run ids, and build their canonical paths.

Writing is exact; reading is permissive. Stock Python only.
Exit codes: 0 success, 1 refused, 2 usage/runtime error.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import secrets
import sys
from pathlib import Path


CANONICAL = re.compile(
    r"^(?P<slug>.+)-(?P<date>\d{8})-(?P<time>\d{6})(?P<millis>\d{3})(?:-(?P<suffix>[0-9a-f]{4}))?$"
)
LEGACY_DASH = re.compile(r"^(?P<slug>.+)-(?P<date>\d{8})-(?P<time>\d{6})$")
LEGACY_COMPACT = re.compile(r"^(?:(?P<slug>.+)-)?(?P<date>\d{8})T(?P<time>\d{6})Z$")
LEGACY_ISO_MINUTE = re.compile(r"^(?:(?P<slug>.+)-)?(?P<date>\d{4}-\d{2}-\d{2})T(?P<time>\d{4})Z$")
LEGACY_DATE_SLUG_TIME = re.compile(r"^(?P<date>\d{8})-(?P<slug>.+)-(?P<time>\d{4})$")
SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class MintRefused(RuntimeError):
    """A run target exists and may not be overwritten."""


def _segment(value: str, label: str) -> str:
    if not SEGMENT.fullmatch(value or "") or value in {".", ".."}:
        raise ValueError(f"invalid {label}: {value!r}")
    return value


def _stamp(date: str, time: str, millis: str = "000") -> str | None:
    compact_date = date.replace("-", "")
    fmt = "%Y%m%d%H%M%S%f"
    if len(time) == 4:
        time += "00"
    try:
        value = dt.datetime.strptime(compact_date + time + millis, fmt).replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return None
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse(run_id: str) -> dict:
    """Parse canonical and historical ids without rejecting unknown read shapes."""
    for rx, canonical in ((CANONICAL, True), (LEGACY_DASH, False),
                          (LEGACY_COMPACT, False), (LEGACY_ISO_MINUTE, False),
                          (LEGACY_DATE_SLUG_TIME, False)):
        match = rx.fullmatch(run_id)
        if not match:
            continue
        values = match.groupdict()
        stamp = _stamp(values["date"], values["time"], values.get("millis") or "000")
        if stamp is None:
            break
        slug = values.get("slug") or run_id
        return {"slug": slug, "stamp_utc": stamp, "legacy": not canonical, "canonical": canonical}
    return {"slug": run_id, "stamp_utc": None, "legacy": True, "canonical": False}


def run_path(campus_root: str | Path, team: str, slug: str, *, kind: str = "team",
             month: str | None = None, standalone: bool = False,
             run_id: str | None = None) -> Path:
    """Build the one canonical base/run directory for teams and playbooks."""
    root = Path(campus_root).resolve()
    team = _segment(team, "team")
    slug = _segment(slug, "slug")
    if kind not in {"team", "playbook"}:
        raise ValueError(f"invalid kind: {kind!r}")
    if standalone:
        owner = "playbooks" if kind == "playbook" else team
        base = root / "teams-shared" / "runs" / owner / slug
    else:
        month = month or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m")
        if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
            raise ValueError(f"invalid month: {month!r}")
        owner = "playbooks" if kind == "playbook" else team
        base = root / "outputs" / month / "runs" / owner / slug
    return base / _segment(run_id, "run_id") if run_id else base


def _stub(run_id: str, team: str, generated: dt.datetime) -> dict:
    # Envelope v1.1 (schemas/results.schema.json): the completion-only stub now
    # carries an empty assets[] so one schema validates every emitter.
    return {
        "schema_version": "1.1",
        "profile": "completion-only",
        "run_id": run_id,
        "team": team,
        "external_ref": None,
        "generated_at": generated.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "assets": [],
        "completion": {"execution_success": False, "artifact_passed": False, "owner_approved": False},
    }


def mint(slug: str, *, campus_root: str | Path = ".", team: str | None = None,
         kind: str = "team", standalone: bool = False, create: bool = True,
         now: dt.datetime | None = None, run_id: str | None = None,
         random_suffix=None) -> dict:
    """Mint a canonical id. `run_id` exists only for deterministic callers/tests."""
    slug = _segment(slug, "slug")
    team = _segment(team or slug, "team")
    now = now or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=dt.timezone.utc)
    now = now.astimezone(dt.timezone.utc)
    base_id = f"{slug}-{now.strftime('%Y%m%d-%H%M%S')}{now.microsecond // 1000:03d}"
    chosen = _segment(run_id, "run_id") if run_id else base_id
    if run_id and not parse(run_id)["canonical"]:
        raise ValueError("explicit run_id must use the canonical format")
    if not create:
        return {"run_id": chosen, "run_dir": None}

    base = run_path(campus_root, team, slug, kind=kind, standalone=standalone)
    target = base / chosen
    if run_id:
        if target.exists():
            reason = "existing-results-json" if (target / "results.json").exists() else "existing-run-dir"
            raise MintRefused(f"{reason}: {target}")
    elif target.exists():
        suffixer = random_suffix or (lambda: secrets.token_hex(2))
        for _ in range(32):
            candidate = f"{base_id}-{suffixer()}"
            target = base / candidate
            if not target.exists():
                chosen = candidate
                break
        else:
            raise MintRefused(f"collision-exhausted: {base / base_id}")

    try:
        target.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise MintRefused(f"existing-run-dir: {target}") from exc
    results = target / "results.json"
    try:
        with results.open("x", encoding="utf-8") as handle:
            json.dump(_stub(chosen, team, now), handle, indent=2)
            handle.write("\n")
    except FileExistsError as exc:
        raise MintRefused(f"existing-results-json: {results}") from exc
    return {"run_id": chosen, "run_dir": str(target)}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    mint_p = sub.add_parser("mint")
    mint_p.add_argument("slug")
    mint_p.add_argument("--team")
    mint_p.add_argument("--kind", choices=("team", "playbook"), default="team")
    mint_p.add_argument("--campus-root", default=".")
    mint_p.add_argument("--standalone", action="store_true")
    mint_p.add_argument("--json", action="store_true")
    parse_p = sub.add_parser("parse")
    parse_p.add_argument("run_id")
    parse_p.add_argument("--json", action="store_true")
    path_p = sub.add_parser("path")
    path_p.add_argument("--team", required=True)
    path_p.add_argument("--slug", required=True)
    path_p.add_argument("--kind", choices=("team", "playbook"), default="team")
    path_p.add_argument("--month")
    path_p.add_argument("--campus-root", default=".")
    path_p.add_argument("--standalone", action="store_true")
    path_p.add_argument("--run-id")
    path_p.add_argument("--json", action="store_true")
    return parser


def main(argv=None) -> int:
    try:
        args = _parser().parse_args(argv)
        if args.command == "mint":
            result = mint(args.slug, campus_root=args.campus_root, team=args.team,
                          kind=args.kind, standalone=args.standalone)
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(result["run_id"])
                print(result["run_dir"])
        elif args.command == "parse":
            result = parse(args.run_id)
            print(json.dumps(result, indent=2) if args.json else json.dumps(result))
        else:
            result = run_path(args.campus_root, args.team, args.slug, kind=args.kind,
                              month=args.month, standalone=args.standalone, run_id=args.run_id)
            print(json.dumps({"run_dir": str(result)}, indent=2) if args.json else result)
        return 0
    except MintRefused as exc:
        print(f"REFUSED(1): {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError) as exc:
        print(f"FAIL(2): {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
