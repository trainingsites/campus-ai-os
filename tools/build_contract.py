#!/usr/bin/env python3
"""build_contract.py - the machine-readable campus contract (5.2.0 Phase 3.7 + R1).

`contracts/campus.json` is GENERATED from the files that already own each fact, so it can never
become a second hand-maintained home:

  section             owner (parsed from)                          consumers
  ------------------  -------------------------------------------  -------------------------------
  hosts               PLATFORM.md facts, encoded here once          package.py / build_niche.py /
                                                                    seat_contract_checks.py literals
                                                                    (parity-checked, see --check)
  context_aliases     templates/context-files.md canon table        every context resolver
  registry_enums      templates/registration-block-spec.md          validate_registry.py, Foundry
  seat                seat_contract_checks.py literals + rules       ledger + lane resolvers
  run_id              tools/mint_run_id.py regexes                   parse/mint on every host
  results_envelope    schemas/results.schema.json (hash)             validate_results.py
  capability_record   authored schema (R1)                           --inventory over registry + hires

Resolvers (Python `tools/contract.py`, JS `tools/contract.mjs`; Phase 3.7, Codex) read ONLY this file.
The human tables `contracts/campus-contract.md` are generated from it (--tables).

Usage:
  python3 tools/build_contract.py                 # (re)generate contracts/campus.json + campus-contract.md
  python3 tools/build_contract.py --check          # exit 1 if the committed contract is stale or a code literal drifted
  python3 tools/build_contract.py --inventory --campus-root DIR [--json]
                                                   # R1: every registry entry + hire manifest as a capability record, validated
Exit 0 ok · 1 stale/invalid · 2 cannot run.
"""
import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

KERNEL = Path(__file__).resolve().parent.parent
CONTRACT = KERNEL / "contracts" / "campus.json"
TABLES = KERNEL / "contracts" / "campus-contract.md"
SOURCES = {
    "context": KERNEL / "templates" / "context-files.md",
    "spec": KERNEL / "templates" / "registration-block-spec.md",
    "mint": KERNEL / "tools" / "mint_run_id.py",
    "seat_checks": KERNEL / "tools" / "seat_contract_checks.py",
    "package": KERNEL / "tools" / "package.py",
    "build_niche": KERNEL / "tools" / "build_niche.py",
    "results_schema": KERNEL / "schemas" / "results.schema.json",
    "manifest": KERNEL / ".claude-plugin" / "plugin.json",   # platform-literal-ok: the OWNER manifest (PLATFORM.md Fact 1); .codex-plugin is derived from it
}
BACKTICK = re.compile(r"`([^`]+)`")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def fail2(msg):
    print(f"FAIL(2): {msg}", file=sys.stderr)
    sys.exit(2)


# ---- parsed sections ---------------------------------------------------------------

def parse_context_aliases(text):
    """Rows of the 'Canonical filenames' table: concept | `canonical` … | `alias`, `alias` …"""
    start = text.find("## Canonical filenames")
    if start < 0:
        fail2("context-files.md has no 'Canonical filenames' section")
    end = text.find("\n## ", start + 5)
    block = text[start:end if end > 0 else None]
    rows = []
    in_table = False
    for line in block.splitlines():
        if not line.startswith("|"):
            if in_table:
                break          # the FIRST table only; later tables are history/examples
            continue
        in_table = True
        if line.startswith("|---") or "Concept" in line:
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) < 3:
            continue
        canon = BACKTICK.findall(cols[1])
        if not canon or not canon[0].endswith(".md"):
            continue
        # alias cell: filenames before the first ';' are aliases; after it is prose
        alias_cell = cols[2].split(";", 1)[0]
        aliases = [a for a in BACKTICK.findall(alias_cell) if a.endswith(".md") and a != canon[0]]
        founding = [a for a in aliases if "what founding actually writes" in alias_cell.split(f"`{a}`", 1)[1][:60]]
        if "what founding actually writes" in cols[1]:
            founding.insert(0, canon[0])
        rows.append({"concept": cols[0], "canonical": canon[0], "aliases": aliases,
                     "founding_writes": founding[0] if founding else canon[0]})
    if len(rows) < 5:
        fail2(f"parsed only {len(rows)} context rows - table format changed; fix the parser, not the data")
    return rows


def parse_field_keys(text):
    start = text.find("## Canonical FIELD keys")
    if start < 0:
        return []
    end = text.find("\n## ", start + 5)
    keys = []
    # bullet format: - `file.md`: `key`, `key[]`, `key` (each `sub`, `sub[]`)
    for line in text[start:end if end > 0 else None].splitlines():
        s = line.strip()
        if not s.startswith("- `"):
            continue
        toks = BACKTICK.findall(s)
        if not toks or not toks[0].endswith(".md"):
            continue
        keys.append({"file": toks[0], "keys": toks[1:]})
    return keys


def parse_enums(text):
    out = {}
    for field in ("type", "status", "department"):
        m = re.search(r'^\s*"%s"\s*:\s*"([^"]+)"' % field, text, re.M)
        if not m:
            fail2(f"registration-block-spec.md has no enum line for {field}")
        out[field] = [v.strip() for v in m.group(1).split("|") if v.strip()]
    return out


def literal_tuple(src_text, name):
    """Read a module-level tuple/list literal of strings without importing side effects."""
    m = re.search(r"^%s\s*=\s*[\(\[](.*?)[\)\]]" % re.escape(name), src_text, re.M | re.S)
    if not m:
        fail2(f"literal {name} not found")
    return re.findall(r"[\"']([^\"']+)[\"']", m.group(1))


# ---- build ---------------------------------------------------------------------------

def build():
    for k, p in SOURCES.items():
        if not p.is_file():
            fail2(f"source missing: {k} -> {p}")
    ctx = SOURCES["context"].read_text(encoding="utf-8")
    spec = SOURCES["spec"].read_text(encoding="utf-8")
    mint = load_module("contract_mint", SOURCES["mint"])
    seat_src = SOURCES["seat_checks"].read_text(encoding="utf-8")
    pkg_src = SOURCES["package"].read_text(encoding="utf-8")
    niche_src = SOURCES["build_niche"].read_text(encoding="utf-8")
    version = json.loads(SOURCES["manifest"].read_text(encoding="utf-8")).get("version", "unknown")

    manifest_candidates = literal_tuple(niche_src, "MANIFEST_CANDIDATES")
    entry_names = literal_tuple(seat_src, "MANAGER_ENTRY_NAMES")
    primary_owned = literal_tuple(seat_src, "PRIMARY_OWNED")
    seat_re = re.search(r're\.fullmatch\(r"([^"]+)", info\["seat"\]\)', seat_src)

    contract = {
        "$schema_note": "Campus AI OS machine-readable contract. GENERATED by tools/build_contract.py - edit the owning source, never this file.",
        "contract_version": "1.0",
        "kernel_version": version,
        "hosts": {
            # platform-literal-ok: this block IS the machine home of PLATFORM.md Facts 1-2;
            # every other tool resolves through the contract (gate check 7 exempts these lines).
            "clients": {
                "claude-cowork": {"manifest_dir": ".claude-plugin", "entry_file": "CLAUDE.md", "seat_default_role": "primary-eligible"},   # platform-literal-ok
                "claude-code": {"manifest_dir": ".claude-plugin", "entry_file": "CLAUDE.md", "seat_default_role": "satellite"},   # platform-literal-ok
                "codex": {"manifest_dir": ".codex-plugin", "entry_file": "AGENTS.md", "seat_default_role": "satellite"},   # platform-literal-ok
            },
            "manifest_candidates": manifest_candidates,
            "entry_file_by_manifest_dir": {".claude-plugin": "CLAUDE.md", ".codex-plugin": "AGENTS.md", "": "CLAUDE.md"},   # platform-literal-ok
            "entry_file_read_names": entry_names,
            "rule": "PLATFORM.md Facts 1-2: resolve PLUGIN_MANIFEST by probe order, derive ENTRY_FILE from the manifest dir; READ any name in entry_file_read_names, WRITE only the derived one.",
        },
        "context_aliases": {
            "resolution": ["canonical", "legacy alias (in listed order)", "case-insensitive match"],
            "canon_file": {"campus": ".campus-os/context-files.md", "kernel": "templates/context-files.md"},
            "files": parse_context_aliases(ctx),
            "field_keys": parse_field_keys(ctx),
        },
        "registry_enums": {
            "canon_file": {"campus": ".campus-os/registration-block-spec.md (materialized)", "kernel": "templates/registration-block-spec.md"},
            "enums": parse_enums(spec),
            "legacy_read_aliases": {"department": {"dean": "dean-office"}},
            "required_since_5_2_0": ["type", "status"],
            "exempt_from_live_shape": {"status": ["legacy", "retired"]},
            "unversioned_types": ["department", "systems"],
        },
        "seat": {
            "seat_file": ".campus-os/seat.json",
            "roles": ["primary", "satellite"],
            "states": ["valid", "missing", "invalid", "unresolved"],
            "seat_id_pattern": seat_re.group(1) if seat_re else "[A-Za-z0-9][A-Za-z0-9_.-]*",
            "ledger": {"primary": "dean/.activity.jsonl", "satellite": "dean/.activity.{seat}.jsonl",
                       "unknown": "dean/.activity.unknown.jsonl", "merge_glob": "dean/.activity.*.jsonl",
                       "unstamped_lines_belong_to": "primary"},
            "lane": {"satellite": "active-work/lanes/{seat}/", "proposals": "active-work/lanes/{seat}/proposals/"},
            "primary_owned_paths": primary_owned,
            "resolver": ".campus-os/resolve-seat.py",
            "host_binding": {
                "file": re.search(r'^HOST_BINDING_FILE\s*=\s*"([^"]+)"', seat_src, re.M).group(1),
                "schema_version": int(re.search(r"^HOST_BINDING_SCHEMA\s*=\s*(\d+)", seat_src, re.M).group(1)),
                "ttl_hours_max": int(re.search(r"^HOST_BINDING_TTL_MAX_HOURS\s*=\s*(\d+)", seat_src, re.M).group(1)),
                "via_values": literal_tuple(seat_src, "HOST_BINDING_VIA"),
                "issue": "python3 .campus-os/resolve-seat.py --issue-binding --client <primary-client> [--ttl-hours N]",
                "never_sync": True,
            },
            "rules": ["missing or invalid seat file => satellite, never primary",
                      "a stamp that differs from today's primary is unresolved history, never a violation by itself",
                      "satellites write only their lane and their own ledger shard",
                      "a host binding is consulted only when the fingerprint is unavailable; it never overrides a mismatch",
                      "a session resolved via host-binding stamps \"via\": \"host-binding\" on every ledger line it writes"],
        },
        "run_id": {
            "canonical_write": "{slug}-{YYYYMMDD-HHMMSSfff}[-xxxx]",
            "patterns": {"canonical": mint.CANONICAL.pattern, "legacy_dash": mint.LEGACY_DASH.pattern,
                         "legacy_compact": mint.LEGACY_COMPACT.pattern, "legacy_iso_minute": mint.LEGACY_ISO_MINUTE.pattern,
                         "legacy_date_slug_time": mint.LEGACY_DATE_SLUG_TIME.pattern},
            "segment_pattern": mint.SEGMENT.pattern,
            "run_dir": {"campus": "outputs/{YYYY-MM}/runs/{team}/{slug}/{run_id}/",
                        "playbook": "outputs/{YYYY-MM}/runs/playbooks/{slug}/{run_id}/",
                        "standalone": "teams-shared/runs/{team}/{slug}/{run_id}/"},
            "rule": "mint with tools/mint_run_id.py; inherit a fed id unchanged; read every legacy shape permissively",
        },
        "results_envelope": {"schema": "schemas/results.schema.json", "schema_sha256": sha(SOURCES["results_schema"]),
                             "write_version": "1.1", "read_legacy_versions": ["1.0", "", "1.1-completion-only"],
                             "validator": "tools/validate_results.py"},
        "capability_record": {
            "$comment": "R1 (5.2.0 Revision 1): one record shape for kernel skill / team / playbook / hire. 5.3.0's resolver binds stages against these. Only id, kind and permission_ceiling are required today; the rest is filled as inventories mature.",
            "type": "object",
            "required": ["id", "kind", "permission_ceiling"],
            "properties": {
                "id": {"type": "string"},
                "kind": {"type": "string", "enum": ["kernel-skill", "team", "playbook", "hire"]},
                "permission_ceiling": {"type": "string", "enum": ["draft-only", "publish"]},
                "accepts": {"type": "array", "items": {"type": "string"}},
                "produces": {"type": "array", "items": {"type": "string"}},
                "tier": {"type": "string", "enum": ["native", "browser", "local"]},
                "cost": {"type": "object"},
                "host": {"type": "array", "items": {"type": "string", "enum": ["claude-cowork", "claude-code", "codex", "any"]}},
                "health": {"type": "string", "enum": ["unknown", "ok", "degraded", "down"]},
                "version": {"type": "string"},
                "source": {"type": "string"},
            },
        },
        "generated_from": {k: {"path": str(p.relative_to(KERNEL)), "sha256": sha(p)} for k, p in SOURCES.items()},
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    return contract


def parity_problems(contract):
    """Code literals that must equal the contract (the lockstep pattern for facts)."""
    problems = []
    pkg = literal_tuple(SOURCES["package"].read_text(encoding="utf-8"), "MANIFEST_PROBE")
    if pkg != contract["hosts"]["manifest_candidates"][:len(pkg)]:
        problems.append(f"package.py MANIFEST_PROBE {pkg} != contract manifest_candidates prefix")
    for client, spec in contract["hosts"]["clients"].items():
        exp = contract["hosts"]["entry_file_by_manifest_dir"].get(spec["manifest_dir"])
        if exp != spec["entry_file"]:
            problems.append(f"host {client}: entry_file {spec['entry_file']} != derived {exp}")
    if contract["hosts"]["entry_file_by_manifest_dir"][""] not in contract["hosts"]["entry_file_read_names"]:
        problems.append("default entry file is not in entry_file_read_names")
    vr = load_module("contract_vr", KERNEL / "tools" / "validate_registry.py")
    if vr.READ_ALIASES.get("department") != contract["registry_enums"]["legacy_read_aliases"]["department"]:
        problems.append("validate_registry.READ_ALIASES != contract legacy_read_aliases")
    return problems


def strip_ts(c):
    d = json.loads(json.dumps(c))
    d.pop("generated_at", None)
    return d


def render_tables(c):
    L = [f"# Campus contract — generated tables (kernel {c['kernel_version']})", "",
         "GENERATED by `tools/build_contract.py` from `contracts/campus.json`. Do not edit; edit the owning source named in each section.", "",
         "## Hosts (owner: PLATFORM.md facts; literals parity-checked)", "", "| Client | Manifest dir | Entry file (write) | Seat default |", "|---|---|---|---|"]
    for k, v in c["hosts"]["clients"].items():
        L.append(f"| `{k}` | `{v['manifest_dir']}` | `{v['entry_file']}` | {v['seat_default_role']} |")
    L += ["", f"Manifest probe order: {' → '.join('`'+m+'`' for m in c['hosts']['manifest_candidates'])}. Entry files accepted on read: {', '.join('`'+n+'`' for n in c['hosts']['entry_file_read_names'])}.", "",
          "## Shared-context files (owner: templates/context-files.md)", "", "| Concept | Canonical | Founding writes | Legacy aliases |", "|---|---|---|---|"]
    for r in c["context_aliases"]["files"]:
        L.append(f"| {r['concept']} | `{r['canonical']}` | `{r['founding_writes']}` | {', '.join('`'+a+'`' for a in r['aliases']) or '—'} |")
    L += ["", "## Registry enums (owner: templates/registration-block-spec.md)", "", "| Field | Values |", "|---|---|"]
    for f, vals in c["registry_enums"]["enums"].items():
        L.append(f"| `{f}` | {' · '.join('`'+v+'`' for v in vals)} |")
    L += [f"| legacy read alias | {', '.join(f'`{a}` → `{b}`' for a, b in c['registry_enums']['legacy_read_aliases']['department'].items())} |", "",
          "## Seat identity (owner: tools/seat_contract_checks.py + ledger-paths.md)", "",
          f"Roles: {', '.join(c['seat']['roles'])}. States: {', '.join(c['seat']['states'])}. Seat id: `{c['seat']['seat_id_pattern']}`.", "",
          "| Role | Ledger | Lane |", "|---|---|---|",
          f"| primary | `{c['seat']['ledger']['primary']}` | (whole campus) |",
          f"| satellite | `{c['seat']['ledger']['satellite']}` | `{c['seat']['lane']['satellite']}` |",
          f"| unknown seat | `{c['seat']['ledger']['unknown']}` | `{c['seat']['lane']['satellite']}` |", "",
          "Primary-owned paths: " + ", ".join("`" + p + "`" for p in c["seat"]["primary_owned_paths"]) + ".", "",
          "## run_id (owner: tools/mint_run_id.py)", "", f"Write: `{c['run_id']['canonical_write']}`. Run dir: `{c['run_id']['run_dir']['campus']}`.", "",
          "| Shape | Regex |", "|---|---|"]
    for k, v in c["run_id"]["patterns"].items():
        L.append(f"| {k} | `{v}` |")
    L += ["", "## Results envelope (owner: schemas/results.schema.json)", "",
          f"Write `schema_version` `{c['results_envelope']['write_version']}`; read {', '.join('`'+v+'`' if v else '(missing)' for v in c['results_envelope']['read_legacy_versions'])} as legacy. Schema sha256 `{c['results_envelope']['schema_sha256'][:12]}…`.", "",
          "## Capability record (R1)", "",
          f"Required: {', '.join('`'+r+'`' for r in c['capability_record']['required'])}. Kinds: {', '.join('`'+k+'`' for k in c['capability_record']['properties']['kind']['enum'])}.", ""]
    return "\n".join(L)


# ---- R1 inventory ----------------------------------------------------------------------

def inventory(campus, contract):
    vres = load_module("contract_vres", KERNEL / "tools" / "validate_results.py")
    schema = contract["capability_record"]
    records = []
    reg = campus / ".campus-os" / "registry.json"
    if reg.is_file():
        try:
            data = json.loads(reg.read_text(encoding="utf-8"))
        except ValueError as exc:
            fail2(f"registry unreadable: {exc}")
        kind_of = {"plugin": "team", "authored-skill": "kernel-skill", "kernel": "kernel-skill"}
        for e in data.get("teams", []):
            if not isinstance(e, dict) or e.get("type") in ("department", "systems"):
                continue
            # Ceiling is a two-value fact (draft-only | publish). The registry's
            # `permission` is spec'd as draft-only but live entries carry grant
            # prose ("publish-community-feed", "owner-gated write ..."): anything
            # that is not draft-only is a publish-class ceiling; the raw text is
            # kept so nothing is lost.
            raw_perm = e.get("permission") or "draft-only"
            rec = {"id": e.get("team") or e.get("name"), "kind": kind_of.get(e.get("type"), "team"),
                   "permission_ceiling": "draft-only" if raw_perm == "draft-only" else "publish", "source": "registry"}
            if raw_perm not in ("draft-only", "publish"):
                rec["permission_note"] = raw_perm
            if e.get("accepts"):
                rec["accepts"] = [a.get("artifact_type") for a in e["accepts"] if isinstance(a, dict)]
            if e.get("produces"):
                rec["produces"] = [p.get("artifact_type") for p in e["produces"] if isinstance(p, dict)]
            if isinstance(e.get("version"), str):
                rec["version"] = e["version"]
            records.append(rec)
        for p in data.get("playbooks", []) or []:
            if isinstance(p, dict) and p.get("playbook"):
                records.append({"id": p["playbook"], "kind": "playbook", "permission_ceiling": "draft-only", "source": "registry"})
    hires = campus / ".campus-os" / "hires"
    if hires.is_dir():
        for f in sorted(hires.glob("*.json")):
            if f.name.startswith("_"):
                continue
            try:
                h = json.loads(f.read_text(encoding="utf-8"))
            except ValueError:
                records.append({"id": f.stem, "kind": "hire", "permission_ceiling": "draft-only", "source": "hire:unreadable"})
                continue
            rec = {"id": h.get("tool") or f.stem, "kind": "hire", "permission_ceiling": "draft-only",
                   "source": f"hire:{f.name}", "health": "unknown"}
            if isinstance(h.get("version"), str):
                rec["version"] = h["version"]
            records.append(rec)
    results = []
    for r in records:
        errs = vres.validate(r, schema)
        results.append({"id": r["id"], "kind": r["kind"], "valid": not errs, "errors": errs})
    return results


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--inventory", action="store_true")
    ap.add_argument("--campus-root")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    if a.inventory:
        if not a.campus_root:
            fail2("--inventory needs --campus-root")
        if not CONTRACT.is_file():
            fail2("no contracts/campus.json - build it first")
        c = json.loads(CONTRACT.read_text(encoding="utf-8"))
        res = inventory(Path(a.campus_root).resolve(), c)
        bad = [r for r in res if not r["valid"]]
        if a.json:
            print(json.dumps({"records": len(res), "invalid": len(bad), "results": res}, indent=2))
        else:
            for r in bad:
                print(f"  !! {r['kind']} {r['id']}: {'; '.join(r['errors'][:3])}")
            kinds = {}
            for r in res:
                kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
            print(f"{'FAIL' if bad else 'OK'}: {len(res)} capability records ({', '.join(f'{k} {n}' for k, n in sorted(kinds.items()))}), {len(bad)} invalid")
        return 1 if bad else 0

    fresh = build()
    if a.check:
        problems = parity_problems(fresh)
        if not CONTRACT.is_file():
            problems.append("contracts/campus.json missing - run tools/build_contract.py")
        else:
            cur = json.loads(CONTRACT.read_text(encoding="utf-8"))
            if strip_ts(cur) != strip_ts(fresh):
                changed = [k for k in fresh if k != "generated_at" and cur.get(k) != fresh.get(k)]
                problems.append(f"contracts/campus.json is stale (sections changed: {', '.join(changed)}) - run tools/build_contract.py")
            if not TABLES.is_file() or TABLES.read_text(encoding="utf-8") != render_tables(cur):
                problems.append("contracts/campus-contract.md is stale - run tools/build_contract.py")
        for p in problems:
            print(f"  !! {p}")
        print(("FAIL" if problems else "OK") + f": campus contract {'has ' + str(len(problems)) + ' problem(s)' if problems else 'current - ' + str(len(fresh['generated_from'])) + ' sources, literals in parity'}")
        return 1 if problems else 0

    CONTRACT.parent.mkdir(parents=True, exist_ok=True)
    if CONTRACT.is_file() and strip_ts(json.loads(CONTRACT.read_text(encoding="utf-8"))) == strip_ts(fresh):
        fresh["generated_at"] = json.loads(CONTRACT.read_text(encoding="utf-8")).get("generated_at", fresh["generated_at"])
    CONTRACT.write_text(json.dumps(fresh, indent=2) + "\n", encoding="utf-8")
    TABLES.write_text(render_tables(fresh), encoding="utf-8")
    problems = parity_problems(fresh)
    for p in problems:
        print(f"  !! {p}")
    print(f"wrote {CONTRACT.relative_to(KERNEL)} + {TABLES.relative_to(KERNEL)} ({len(fresh['context_aliases']['files'])} context files, "
          f"{sum(len(v) for v in fresh['registry_enums']['enums'].values())} enum values, {len(fresh['run_id']['patterns'])} run_id shapes)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
