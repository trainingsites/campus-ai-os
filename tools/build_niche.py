#!/usr/bin/env python3
"""build_niche.py - niche-pack assembler + conformance gate (Campus AI OS v5).

The v5 kernel is niche-agnostic; all niche identity lives in packs/{name}/
(manifest + the domain skills listed in it). This tool proves that split:

  --check              validate the active pack against the source tree (gate)
  --list               list finding codes and titles
  --only CODE[,CODE]    run selected checks
  --pack NAME          which pack to operate on (default: education)
  --assemble OUT_DIR   build a variant source tree for the named pack: copy the
                       kernel, keep only that pack's domain skills + folder,
                       drop every other pack. For the shipped pack this is an
                       identity copy - which is exactly the factory proof.

Stdlib only. Exit 0 = pass, 1 = fail (prints each failure).
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent

# Manifest probe order - MUST stay in lockstep with PLATFORM.md (kernel
# reference at the plugin root) and scan_workforce.py's MANIFEST_CANDIDATES.
# Adding a host = one row in PLATFORM.md + one entry in each of those lists.
MANIFEST_CANDIDATES = (
    ".claude-plugin/plugin.json",   # Claude / Claude Code / Cowork  platform-literal-ok
    ".codex-plugin/plugin.json",    # Codex / OpenAI
    "plugin.json",                  # bare / unknown host
    ".agents/plugins/marketplace.json",   # Codex marketplace record
)

# Kernel components that must RESOLVE the platform facts rather than hardcode
# them. Scanned by check 7.
RESOLVER_SKILLS = ("campus-start", "campus-doctor", "update-workspace")

# Directories the campus must have, scaffolded (not copied from templates/), so
# check 8's templates/* filename diff cannot see them. Founding and migration
# must BOTH create every one - SOP standing gate (a). Adding a scaffold = one
# row here plus the step in both skills.
# Step 0's up-to-date branch must be a comparison, never a version literal.
# These are the exact markers build-gate check 12 requires in update-workspace.
UPTODATE_COMPARISON = "Marker == `OS_VERSION`"
CLOSING_RULE_MARKER = "Closing rule - every upgrade path ends the same way"

SCAFFOLD_PARITY = (
    (".campus-os/scan/", "hr-registry writes its scan snapshots here"),
    ("atlas/config/", "the strategy and research team's private config lives here"),
)

# A platform literal is permitted on a line that also carries one of these -
# i.e. the line is prose explaining the binding, or is the resolver itself.
# Prose may NAME a platform; logic may not.
PLATFORM_LITERAL_ALLOW = (
    "PLUGIN_MANIFEST", "ENTRY_FILE", "PLATFORM.md",
    # Naming any NON-Claude host on the line proves the line is platform-aware
    # prose, not a binding. AGENTS.md is Codex's real entry file (verified
    # 2026-07-25); CODEX.md is the legacy alias we still read.
    "AGENTS.md", "CODEX.md", ".codex-plugin", "hardcoded", "Rationale",
    "platform-literal-ok",   # explicit opt-out for declarations + this check itself
)

# ---- Shared-context canon (check 13, added v5.1.1) -------------------------
# One owner for every shared-context filename and its aliases. Same role
# PLATFORM.md plays for ENTRY_FILE: readers RESOLVE through it, they never type
# a filename. Moving this file = update this constant and the pointers in
# campus-doctor + the skills that cite it (check 13c enforces the pointers).
CONTEXT_CANON = "templates/context-files.md"

# Kept as a POINTER at the pre-v5.1.1 location so nothing that still references
# the old path reads a stale table. It must never regrow the alias list.
CONTEXT_CANON_POINTER = "skills/atlas-setup/references/context-files.md"

# Skills that CREATE context files may name what they create - writing is exact,
# reading is permissive (the ENTRY_FILE rule). Everyone else resolves.
CONTEXT_WRITERS = (
    "skills/campus-start/SKILL.md",
    "skills/full-onboarding/SKILL.md",
    "templates/setup-progress.md",
    CONTEXT_CANON,
    CONTEXT_CANON_POINTER,
)

# `setup-progress.md` is setup STATE, not business context - founding writes it
# and no skill resolves it as a concept, so it is exempt from 13a by name.
CONTEXT_NOT_A_CONCEPT = frozenset({"setup-progress.md"})

# A context filename may appear on a line that also carries one of these - the
# line is prose about resolution, not a binding. Mirrors PLATFORM_LITERAL_ALLOW.
CONTEXT_LITERAL_ALLOW = (
    "CONTEXT_CANON", "context-files.md", "canon", "alias", "Alias",
    "never hard-code", "never a filename", "resolve", "Resolve", "Rationale",
    "context-literal-ok",
)

REQUIRED_IDENTITY = [
    "business_noun", "owner_line", "customer_noun",
    "founding_frame", "q1", "q1_pushback", "q2_examples",
]


def frontmatter(path: Path) -> dict:
    """Tiny YAML-frontmatter reader (key: value lines only)."""
    out = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return out
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return out
    for line in m.group(1).splitlines():
        kv = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
        if kv and kv.group(2) and not kv.group(2).startswith((">", "|")):
            out[kv.group(1)] = kv.group(2).strip()
    return out


CLAUDE_MANIFEST = ".claude-plugin/plugin.json"   # platform-literal-ok  (the OWNER)
CODEX_MANIFEST = ".codex-plugin/plugin.json"     # DERIVED - never hand-edited


def render_codex_manifest(owner: dict) -> str:
    """Derive the Codex manifest from the Claude one. Single owner, one direction.

    A second hand-maintained manifest would be the exact defect this release is
    designed against - two copies of name/version/description with nothing
    reconciling them. So the Codex manifest is GENERATED and the gate verifies
    it still matches. `skills` is the one documented Codex-side addition.
    """
    derived = dict(owner)
    derived["skills"] = "./skills/"
    return json.dumps(derived, indent=2, ensure_ascii=False) + "\n"


def sync_manifests() -> list:
    """Write the derived Codex manifest. Returns [] on success."""
    src = SRC / CLAUDE_MANIFEST
    if not src.is_file():
        return [f"{CLAUDE_MANIFEST} missing - nothing to derive from"]
    try:
        owner = json.loads(src.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"{CLAUDE_MANIFEST} invalid JSON: {e}"]
    dst = SRC / CODEX_MANIFEST
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(render_codex_manifest(owner), encoding="utf-8")
    return []


def resolve_manifests():
    """Return (primary_path, [all_present_paths]) using PLATFORM.md probe order.

    The build tool must not hardcode the manifest directory either - it is the
    same shared fact. Resolving here is also what lets check 5b verify that a
    dual-manifest source keeps its manifests in agreement.
    """
    found = [SRC / rel for rel in MANIFEST_CANDIDATES if (SRC / rel).is_file()]
    return (found[0] if found else None), found


def load_pack(name: str):
    p = SRC / "packs" / name / "pack.json"
    if not p.exists():
        return None, [f"packs/{name}/pack.json missing"]
    try:
        return json.loads(p.read_text(encoding="utf-8")), []
    except json.JSONDecodeError as e:
        return None, [f"packs/{name}/pack.json invalid JSON: {e}"]


def plugin_version():
    """Read the same version as check 5, without running its findings."""
    primary, _ = resolve_manifests()
    if primary is not None:
        try:
            return json.loads(primary.read_text(encoding="utf-8")).get("version")
        except (OSError, json.JSONDecodeError):
            pass
    return None


def context_canon():
    """Return canon names and structural findings without running readers."""
    errors = []
    canon_names = None
    canon_path = SRC / CONTEXT_CANON
    if not canon_path.is_file():
        errors.append(
            f"{CONTEXT_CANON} missing - shared-context filenames have no owner"
        )
    else:
        canon_txt = canon_path.read_text(encoding="utf-8")
        # Every `backticked.md` name in the ALIAS TABLE - canonical or alias.
        #
        # Scoped to the table ON PURPOSE. The first draft regexed the whole
        # file, and negative test N2 proved that useless: deleting `tools.md`
        # from its table row did NOT fail the build, because the same name still
        # appeared in the explanatory prose underneath. The check was reading
        # documentation about the canon instead of the canon. A name is only
        # resolvable if it is in the table a resolver actually reads.
        table_rows = []
        in_table = False
        for line in canon_txt.splitlines():
            if line.startswith("| Concept | Canonical |"):
                in_table = True
                continue
            if in_table:
                if not line.startswith("|"):
                    break
                table_rows.append(line)
        if not table_rows:
            errors.append(
                f"{CONTEXT_CANON} has no '| Concept | Canonical |' alias table - "
                f"check 13a cannot resolve anything and is not actually running"
            )
        canon_names = set(re.findall(r"`([A-Za-z0-9_.-]+\.md)`", "\n".join(table_rows)))

    return canon_names, errors


def check_manifest_shape(pack_name, pack, warnings):
    """Manifest shape."""
    errors = []
    # 1. Manifest shape
    for key in ("pack", "label", "version", "identity", "departments", "domain_skills"):
        if key not in pack:
            errors.append(f"pack.json missing key: {key}")
    for key in REQUIRED_IDENTITY:
        if key not in pack.get("identity", {}):
            errors.append(f"pack.json identity missing: {key}")
    if pack.get("pack") != pack_name:
        errors.append(f"pack.json pack field '{pack.get('pack')}' != folder '{pack_name}'")
    return errors


def check_declared_domain_skills(pack_name, pack, warnings):
    """Declared domain skills."""
    errors = []
    # 2. Every declared domain skill exists and carries pack frontmatter
    declared = set(pack.get("domain_skills", []))
    for skill in sorted(declared):
        sk = SRC / "skills" / skill / "SKILL.md"
        if not sk.exists():
            errors.append(f"domain skill missing: skills/{skill}/SKILL.md")
            continue
        fm = frontmatter(sk)
        if fm.get("pack") != pack_name:
            errors.append(f"skills/{skill}/SKILL.md frontmatter 'pack: {pack_name}' missing/wrong (got: {fm.get('pack')})")
    return errors


def check_orphan_pack_skills(pack_name, pack, warnings):
    """Orphan pack skills."""
    errors = []
    # 3. No orphan pack-tagged skills (tagged but not declared in any pack)
    all_declared = set()
    for pdir in (SRC / "packs").iterdir():
        if pdir.is_dir():
            pj, _ = load_pack(pdir.name)
            if pj:
                all_declared.update(pj.get("domain_skills", []))
    for sk in sorted((SRC / "skills").iterdir()):
        f = sk / "SKILL.md"
        if f.exists():
            tag = frontmatter(f).get("pack")
            if tag and sk.name not in all_declared:
                errors.append(f"skills/{sk.name} tagged 'pack: {tag}' but declared in no pack manifest")
    return errors


def check_pack_departments(pack_name, pack, warnings):
    """Pack departments."""
    errors = []
    # 4. Pack departments exist in the registry template
    reg_path = SRC / "templates" / "registry.json"
    try:
        reg = json.loads(reg_path.read_text(encoding="utf-8"))
        reg_depts = {t.get("department") for t in reg.get("teams", []) if t.get("type") == "department"}
        for d in pack.get("departments", []):
            if d not in reg_depts:
                errors.append(f"pack department '{d}' has no type:department entry in templates/registry.json")
    except (OSError, json.JSONDecodeError) as e:
        errors.append(f"templates/registry.json unreadable: {e}")
    return errors


def check_pack_version_lockstep(pack_name, pack, warnings):
    """Pack version lockstep."""
    errors = []
    # 5. Version lockstep with the plugin manifest (resolved, not hardcoded).
    plug_version = None
    primary, all_manifests = resolve_manifests()
    if primary is None:
        errors.append(
            "no plugin manifest found - probed " + ", ".join(MANIFEST_CANDIDATES)
        )
    else:
        try:
            plug = json.loads(primary.read_text(encoding="utf-8"))
            plug_version = plug.get("version")
            if pack.get("version") != plug_version:
                errors.append(
                    f"pack version {pack.get('version')} != plugin version {plug_version}"
                )
        except (OSError, json.JSONDecodeError) as e:
            errors.append(f"{primary.relative_to(SRC)} unreadable: {e}")
    return errors


def check_derived_manifest_parity(pack_name, pack, warnings):
    """Derived manifest parity."""
    errors = []
    # 5b. The Codex manifest must be DERIVED, not maintained (upgraded v5.1
    #     after reviewing a hand-forked Codex build whose manifest had drifted
    #     to `5.0.3+codex.<timestamp>` - which then broke version lockstep with
    #     pack.json, the registry template, and three skill frontmatters, i.e.
    #     7 gate failures from one hand-edited copy).
    #
    #     Parity-checking two hand-kept files is a smoke alarm, not a fix. One
    #     owner (CLAUDE_MANIFEST), one derived artifact, byte-exact.
    #     Regenerate with: python3 tools/build_niche.py --sync-manifests
    codex_path = SRC / CODEX_MANIFEST
    owner_path = SRC / CLAUDE_MANIFEST
    if codex_path.is_file():
        if not owner_path.is_file():
            errors.append(f"{CODEX_MANIFEST} exists but {CLAUDE_MANIFEST} (its owner) does not")
        else:
            try:
                expected = render_codex_manifest(
                    json.loads(owner_path.read_text(encoding="utf-8"))
                )
                actual = codex_path.read_text(encoding="utf-8")
                if actual != expected:
                    ej = json.loads(expected)
                    try:
                        aj = json.loads(actual)
                        drift = [
                            f"{k}: {aj.get(k)!r} != {ej.get(k)!r}"
                            for k in sorted(set(ej) | set(aj))
                            if aj.get(k) != ej.get(k)
                        ] or ["formatting only"]
                    except json.JSONDecodeError:
                        drift = ["not valid JSON"]
                    errors.append(
                        f"{CODEX_MANIFEST} is hand-edited or stale -> "
                        + "; ".join(drift[:4])
                        + " (fix: python3 tools/build_niche.py --sync-manifests)"
                    )
            except (OSError, json.JSONDecodeError) as e:
                errors.append(f"manifest derivation check failed: {e}")
    return errors


def check_registry_version_lockstep(pack_name, pack, warnings):
    """Registry version lockstep."""
    errors = []
    plug_version = plugin_version()
    if plug_version:
        # 6a. templates/registry.json must be in lockstep - it seeds live state.
        try:
            reg_raw = (SRC / "templates" / "registry.json").read_text(encoding="utf-8")
            reg_j = json.loads(reg_raw)
            if reg_j.get("campus_os_version") != plug_version:
                errors.append(
                    f"templates/registry.json campus_os_version "
                    f"{reg_j.get('campus_os_version')} != plugin version {plug_version}"
                )
            for t in reg_j.get("teams", []):
                if t.get("type") == "kernel" and t.get("version") not in (None, plug_version):
                    errors.append(
                        f"templates/registry.json kernel entry '{t.get('team')}' version "
                        f"{t.get('version')} != plugin version {plug_version}"
                    )
        except (OSError, json.JSONDecodeError) as e:
            errors.append(f"templates/registry.json version check failed: {e}")
    return errors


def check_skill_version_resolution(pack_name, pack, warnings):
    """Skill version resolution."""
    errors = []
    plug_version = plugin_version()
    if plug_version:
        # 6b. Kernel skills that WRITE a version must resolve it, not hardcode it.
        for skill in ("campus-start", "update-workspace"):
            sk = SRC / "skills" / skill / "SKILL.md"
            if not sk.exists():
                continue
            body = sk.read_text(encoding="utf-8")
            if "OS_VERSION" not in body:
                errors.append(
                    f"skills/{skill}/SKILL.md writes a version but never resolves OS_VERSION "
                    f"- hardcoded version markers go stale on every patch"
                )
            fm_v = frontmatter(sk).get("version")
            if fm_v and str(fm_v) != plug_version:
                errors.append(
                    f"skills/{skill}/SKILL.md frontmatter version {fm_v} != plugin version {plug_version}"
                )
        # campus-doctor reports the version, so it tracks the plugin too.
        dk = SRC / "skills" / "campus-doctor" / "SKILL.md"
        if dk.exists():
            fm_v = frontmatter(dk).get("version")
            if fm_v and str(fm_v) != plug_version:
                errors.append(
                    f"skills/campus-doctor/SKILL.md frontmatter version {fm_v} != plugin version {plug_version}"
                )
    return errors


def check_platform_bindings(pack_name, pack, warnings):
    """Platform bindings."""
    errors = []
    # 7. No hardcoded platform bindings (added v5.1, payload item 7).
    #    Portability leg 1 (Codex) exposed ~55 hardcoded references to two facts
    #    that differ per host: the manifest directory and the workspace entry
    #    filename. campus-doctor check 2a hardcoded `CLAUDE.md` and therefore
    #    failed on a CORRECT Codex campus - reporting a healthy install as
    #    broken, on the platform whose portability had just been proven. Sixteen
    #    more skills carried the same guard.
    #
    #    This is the same class as check 6 (version markers): one shared fact,
    #    many private copies, no single reader. PLATFORM.md is now the single
    #    reader; this check is what makes that binding, not a request.
    #
    #    Rule enforced: prose may NAME a platform, logic may not. A literal is
    #    allowed only on a line that also carries a resolver token or is plainly
    #    explanatory (see PLATFORM_LITERAL_ALLOW).
    platform_targets = [SRC / "skills" / s / "SKILL.md" for s in RESOLVER_SKILLS]
    platform_targets += sorted(SRC.glob("skills/*/SKILL.md"))
    platform_targets += sorted(SRC.glob("skills/*/scripts/*.py"))
    platform_targets += sorted(SRC.glob("tools/*.py"))
    platform_targets += sorted(SRC.glob("playbooks/*.md"))

    # `dean-CLAUDE.md` is a real template filename, not a platform binding -
    # the negative lookbehind on `-`/word-char keeps it out.
    entry_literal = re.compile(r"(?<![-\w])CLAUDE\.md")      # platform-literal-ok
    manifest_literal = re.compile(r"\.claude-plugin\b")   # platform-literal-ok

    for path in dict.fromkeys(platform_targets):   # de-dup, keep order
        if not path.is_file():
            continue
        rel = path.relative_to(SRC)
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if any(tok in line for tok in PLATFORM_LITERAL_ALLOW):
                continue
            if entry_literal.search(line):
                errors.append(
                    f"{rel}:{n} hardcodes the entry filename 'CLAUDE.md' - "   # platform-literal-ok
                    f"resolve ENTRY_FILE per PLATFORM.md (breaks on non-Claude hosts)"
                )
            if manifest_literal.search(line):
                errors.append(
                    f"{rel}:{n} hardcodes the manifest dir '.claude-plugin' - "   # platform-literal-ok
                    f"resolve PLUGIN_MANIFEST per PLATFORM.md (breaks on non-Claude hosts)"
                )
    return errors


def check_founding_and_migration_templates(pack_name, pack, warnings):
    """Founding and migration templates."""
    errors = []
    # 8. FOUNDING vs MIGRATION parity on templates (added v5.0.6).
    #    SOP standing gate (a): "a fresh install and an upgraded install must
    #    produce the same campus." It has been a standing PROSE gate, and the
    #    bug class has now bitten FIVE times (v3.2.1 stale version marker;
    #    v4.0.0 missing model-routing.md; v4.2 goals.md/filing-key; v5.0.5
    #    entry-file detection; v5.0.5 registration-block-spec.md, found on a
    #    Codex cold install 2026-07-26 - update-workspace step 8 copied it,
    #    campus-start never did, so every FOUNDED campus was missing the file
    #    campus-doctor check 7 reads).
    #
    #    A rule that has failed five times is not a rule, it is a wish. Make it
    #    a check: any template copied by ONE path must be copied by the OTHER.
    start_sk = SRC / "skills" / "campus-start" / "SKILL.md"
    upd_sk = SRC / "skills" / "update-workspace" / "SKILL.md"
    tmpl_dir = SRC / "templates"
    if start_sk.is_file() and upd_sk.is_file() and tmpl_dir.is_dir():
        start_txt, upd_txt = start_sk.read_text(encoding="utf-8"), upd_sk.read_text(encoding="utf-8")
        for tmpl in sorted(tmpl_dir.glob("*.md")) + sorted(tmpl_dir.glob("*.json")):
            nm = tmpl.name
            # dean-CLAUDE.md is the brain template: founding writes it, migration
            # deliberately only INSERTS into an existing one. Genuinely asymmetric.
            if nm.startswith("dean-"):
                continue
            in_start, in_upd = nm in start_txt, nm in upd_txt
            if in_upd and not in_start:
                errors.append(
                    f"founding/migration parity: templates/{nm} is copied by "
                    f"update-workspace but NOT by campus-start - a founded campus "
                    f"would be missing it (SOP standing gate (a))"
                )
            elif in_start and not in_upd:
                errors.append(
                    f"founding/migration parity: templates/{nm} is written by "
                    f"campus-start but NOT by update-workspace - an upgraded campus "
                    f"would be missing it (SOP standing gate (a))"
                )
    return errors


def check_scaffold_directory_parity(pack_name, pack, warnings):
    """Scaffold directory parity."""
    errors = []
    start_sk = SRC / "skills" / "campus-start" / "SKILL.md"
    upd_sk = SRC / "skills" / "update-workspace" / "SKILL.md"
    tmpl_dir = SRC / "templates"
    if start_sk.is_file() and upd_sk.is_file() and tmpl_dir.is_dir():
        start_txt, upd_txt = start_sk.read_text(encoding="utf-8"), upd_sk.read_text(encoding="utf-8")
        # 8b. Scaffolded DIRECTORIES need the same parity as copied templates.
        #     Check 8 above compares templates/* filenames, so a folder that is
        #     created rather than copied is invisible to it - a real gap, since
        #     `.campus-os/scan/` and `atlas/config/` are scaffolds, not copies.
        #     Same rule, same gate (a): created by one path, created by both.
        for scaffold, why in SCAFFOLD_PARITY:
            in_start, in_upd = scaffold in start_txt, scaffold in upd_txt
            if in_upd and not in_start:
                errors.append(
                    f"founding/migration parity: '{scaffold}' is scaffolded by "
                    f"update-workspace but NOT by campus-start - a FOUNDED campus "
                    f"would be missing it ({why}) (SOP standing gate (a))"
                )
            elif in_start and not in_upd:
                errors.append(
                    f"founding/migration parity: '{scaffold}' is scaffolded by "
                    f"campus-start but NOT by update-workspace - an UPGRADED campus "
                    f"would be missing it ({why}) (SOP standing gate (a))"
                )
            elif not in_start and not in_upd:
                errors.append(
                    f"founding/migration parity: '{scaffold}' is scaffolded by "
                    f"neither campus-start nor update-workspace ({why})"
                )
    return errors


def check_ledger_schema_parity(pack_name, pack, warnings):
    """Ledger schema parity."""
    errors = []
    # 9. One ledger schema across the kernel (added v5.0.7).
    #    The activity ledger is written by kernel skills AND by playbook stages,
    #    and read by cluster_ledger.py for the self-authoring loop. It shipped
    #    with TWO spellings of the same field - templates/dean-CLAUDE.md said
    #    "team", playbooks/README.md and promote-skills said "dept" - while the
    #    consumer read only "dept". Result on a real Codex campus (2026-07-26):
    #    4 of 7 ledger lines silently bucketed to "dean". One field, two
    #    spellings, a reader that knows one. Same class as everything else in
    #    this release.
    ledger_writers = [SRC / "templates" / "dean-CLAUDE.md",
                      SRC / "playbooks" / "README.md",
                      SRC / "skills" / "promote-skills" / "SKILL.md"]
    spellings = {}
    for f in ledger_writers:
        if not f.is_file():
            continue
        body = f.read_text(encoding="utf-8")
        for line in body.splitlines():
            if '"skill":' in line and '"outcome":' in line:      # a ledger example line
                for key in ('"dept"', '"team"'):
                    if key in line:
                        spellings.setdefault(key, []).append(str(f.relative_to(SRC)))
    if len(spellings) > 1:
        detail = " vs ".join(f"{k} in {sorted(set(v))}" for k, v in sorted(spellings.items()))
        errors.append(
            f"activity-ledger schema split - the same field has two spellings: {detail}. "
            f"Canon is \"dept\"; cluster_ledger.py buckets unknown spellings to 'dean'."
        )
    return errors


def check_platform_resolver_pointer(pack_name, pack, warnings):
    """Platform resolver pointer."""
    errors = []
    # 7b. The three resolver skills must actually point at the single reader.
    if not (SRC / "PLATFORM.md").is_file():
        errors.append("PLATFORM.md missing at plugin root - the platform facts have no owner")
    else:
        for s in RESOLVER_SKILLS:
            sk = SRC / "skills" / s / "SKILL.md"
            if sk.is_file() and "PLATFORM.md" not in sk.read_text(encoding="utf-8"):
                errors.append(
                    f"skills/{s}/SKILL.md resolves platform facts but never references "
                    f"PLATFORM.md - the resolution rule must have one owner"
                )
    return errors


def check_manager_lint(pack_name, pack, warnings):
    """Manager lint."""
    errors = []
    # 10. Pack-declared managers must satisfy the Manager Layer contract.
    #     Delegated to tools/lint_managers.py rather than reimplemented here -
    #     the same rules also run against a live campus, and two copies of a rule
    #     is the exact defect class this release exists to close.
    lint = SRC / "tools" / "lint_managers.py"
    if not lint.is_file():
        errors.append("tools/lint_managers.py missing - the manager contract has no enforcer")
    else:
        pack_file = SRC / "packs" / pack_name / "pack.json"
        proc = subprocess.run(
            [sys.executable, str(lint), "--pack", str(pack_file), "--quiet"],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            detail = (proc.stdout or proc.stderr).strip().replace("\n", " | ")
            errors.append(f"pack managers[] violate the manager contract: {detail}")
    return errors


def check_up_to_date_comparison(pack_name, pack, warnings):
    """Up-to-date comparison."""
    errors = []
    upd = SRC / "skills" / "update-workspace" / "SKILL.md"
    if upd.is_file():
        body = upd.read_text(encoding="utf-8")
        # 12a. The up-to-date test must be a COMPARISON against OS_VERSION.
        if UPTODATE_COMPARISON not in body:
            errors.append(
                f"skills/update-workspace/SKILL.md has no '{UPTODATE_COMPARISON}' "
                f"branch - the up-to-date test must compare the campus marker to "
                f"OS_VERSION. A hardcoded version family goes stale the moment the "
                f"next version ships and silently strands every older campus"
            )
    return errors


def check_version_family_routing(pack_name, pack, warnings):
    """Version-family routing."""
    errors = []
    upd = SRC / "skills" / "update-workspace" / "SKILL.md"
    if upd.is_file():
        body = upd.read_text(encoding="utf-8")
        # 12b. ...and must not be re-expressed as a version-family literal.
        #      Scoped to branch bullets ('- **...') so explanatory prose that
        #      quotes the old wording as history does not trip it.
        stale_family = re.compile(r"\d+\.\d+\.x")
        for n, line in enumerate(body.splitlines(), 1):
            if not line.lstrip().startswith("- **"):
                continue
            if stale_family.search(line) and re.search(r"up[- ]to[- ]date", line, re.I):
                errors.append(
                    f"skills/update-workspace/SKILL.md:{n} ties 'up to date' to a "
                    f"hardcoded version family - it must compare against OS_VERSION "
                    f"(this exact defect stranded a 4.1.4 campus across three releases)"
                )
    return errors


def check_additions_reachability(pack_name, pack, warnings):
    """Additions reachability."""
    errors = []
    upd = SRC / "skills" / "update-workspace" / "SKILL.md"
    if upd.is_file():
        body = upd.read_text(encoding="utf-8")
        # 12c. Every additions item must be declared to run for EVERY campus,
        #      and the closing rule must run them on every path. An additions
        #      item some paths skip is one that never runs for the campuses
        #      that need it most.
        for n, line in enumerate(body.splitlines(), 1):
            m = re.match(r"\s*\d+\.\s+\*\*v[\d.]+ additions\b(.*)", line)
            if m and "every campus" not in m.group(1):
                errors.append(
                    f"skills/update-workspace/SKILL.md:{n} declares an additions item "
                    f"that is not marked 'every campus' - additions items must be "
                    f"additive, idempotent, and run on every upgrade path"
                )
        if CLOSING_RULE_MARKER not in body:
            errors.append(
                "skills/update-workspace/SKILL.md is missing the closing rule that "
                "runs the additions items and stamps OS_VERSION on EVERY upgrade "
                f"path (expected marker: '{CLOSING_RULE_MARKER}')"
            )
    return errors


def check_context_canon_table(pack_name, pack, warnings):
    """Context canon table."""
    errors = []
    _, errors = context_canon()
    return errors


def check_founding_and_context_canon_parity(pack_name, pack, warnings):
    """Founding and context canon parity."""
    errors = []
    canon_names, _ = context_canon()
    if canon_names is not None:
        # 13a. FOUNDING/CANON PARITY - the set comparison that would have caught
        #      all three at once. Anything campus-start writes into shared/ must
        #      be a name the canon knows, or a reader resolving that concept
        #      finds nothing on a perfectly healthy founded campus.
        start_p = SRC / "skills" / "campus-start" / "SKILL.md"
        if start_p.is_file():
            body = start_p.read_text(encoding="utf-8")
            # Anchor on the COLUMN-ALIGNED scaffold block (`shared/` + 2 or more
            # spaces), not on any line that happens to begin "shared/".
            # The first draft used \s+ and matched the prose line "shared/ with
            # content, .campus-os/..." 120 lines earlier - so it silently read
            # the wrong block and could never have failed. Caught by negative
            # test N1, which is the entire reason N1 exists.
            blocks = re.findall(r"^shared/[ \t]{2,}(.*?)(?=^\S|\Z)", body, re.M | re.S)
            if not blocks:
                errors.append(
                    "check 13a cannot find campus-start's shared/ scaffold block - "
                    "the founding/canon parity check is not actually running"
                )
            written_at_founding = set()
            for b in blocks:
                written_at_founding |= set(re.findall(r"([A-Za-z0-9_-]+\.md)", b))
            if blocks:
                for nm in sorted(written_at_founding - canon_names - CONTEXT_NOT_A_CONCEPT):
                    errors.append(
                        f"shared-context canon gap: campus-start writes "
                        f"shared/{nm} but {CONTEXT_CANON} never names it - every "
                        f"skill resolving that concept finds NOTHING on a "
                        f"correctly-founded campus (add it as an alias)"
                    )
    return errors


def check_context_readers_and_writers(pack_name, pack, warnings):
    """Context readers and writers."""
    errors = []
    canon_names, _ = context_canon()
    if canon_names is not None:
        # 13b. NO READER MAY NAME A CONTEXT FILE THAT NOTHING WRITES.
        #      This is the precise, self-maintaining rule: if founding writes it,
        #      naming it is merely a bypass; if NOTHING writes it, naming it is a
        #      reader that finds nothing on every correctly-founded campus. That
        #      distinction is what separated the 15 live defects from the 31
        #      latent ones when this check first ran.
        #
        #      It stayed hidden for a reason worth keeping in the comment: the
        #      campus this was developed on predates the founding convention and
        #      holds the CANONICAL names by hand, so `shared/icp.md` resolved
        #      perfectly there and nowhere else. Read-side defects hide on the
        #      developer's own campus when the developer upgrades rather than
        #      founds.
        written = set()
        for w in ("skills/campus-start/SKILL.md", "skills/full-onboarding/SKILL.md"):
            wp = SRC / w
            if wp.is_file():
                written |= set(re.findall(r"shared/([A-Za-z0-9_.-]+\.md)",
                                          wp.read_text(encoding="utf-8")))
                # campus-start lists its shared/ files in a block, not inline
                m = re.search(r"^shared/\s+(.*?)(?=^\S|\Z)",
                              wp.read_text(encoding="utf-8"), re.M | re.S)
                if m:
                    written |= set(re.findall(r"([A-Za-z0-9_-]+\.md)", m.group(1)))

        scan = sorted(SRC.glob("skills/*/SKILL.md"))
        scan += sorted(SRC.glob("skills/*/references/*.md"))
        scan += sorted(SRC.glob("playbooks/*/SKILL.md"))
        scan += sorted(SRC.glob("playbooks/*.md"))
        bypasses = []
        for path in dict.fromkeys(scan):
            rel = str(path.relative_to(SRC))
            if rel in CONTEXT_WRITERS or not path.is_file():
                continue
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if any(tok in line for tok in CONTEXT_LITERAL_ALLOW):
                    continue
                for nm in sorted(set(re.findall(r"shared/([A-Za-z0-9_.-]+\.md)", line))):
                    if nm in CONTEXT_NOT_A_CONCEPT:
                        continue
                    if nm not in written:
                        errors.append(
                            f"{rel}:{n} reads 'shared/{nm}', which NO path ever "
                            f"writes - this finds nothing on every correctly-founded "
                            f"campus. Resolve the concept through {CONTEXT_CANON} "
                            f"(canon -> alias -> case-insensitive)"
                        )
                    elif nm in canon_names:
                        bypasses.append(f"{rel}:{n} shared/{nm}")
        if bypasses:
            # WARNING, not an error. These resolve today because founding writes
            # exactly this name - but they bypass the canon, so they break the
            # day an alias or rename is introduced. Loud, not blocking: removing
            # a finding by removing the check is the S220 anti-pattern.
            warnings.append(
                f"{len(bypasses)} reader(s) name a context file directly instead of "
                f"resolving it. These WORK today (founding writes these names) but "
                f"bypass {CONTEXT_CANON}: " + "; ".join(bypasses[:8])
                + ("; ..." if len(bypasses) > 8 else "")
            )
    return errors


def check_context_canon_pointers(pack_name, pack, warnings):
    """Context canon pointers."""
    errors = []
    canon_names, _ = context_canon()
    if canon_names is not None:
        # 13c. The canon must have readers that actually point at it, and the
        #      old location must stay a pointer rather than regrow a copy.
        for s in ("campus-doctor",):
            sk = SRC / "skills" / s / "SKILL.md"
            if sk.is_file() and "context-files.md" not in sk.read_text(encoding="utf-8"):
                errors.append(
                    f"skills/{s}/SKILL.md reads shared context but never references "
                    f"{CONTEXT_CANON} - the resolution rule must have one owner"
                )
        ptr = SRC / CONTEXT_CANON_POINTER
        if ptr.is_file():
            ptxt = ptr.read_text(encoding="utf-8")
            if "| Concept | Canonical |" in ptxt:
                errors.append(
                    f"{CONTEXT_CANON_POINTER} has regrown the alias table - it must "
                    f"stay a POINTER to {CONTEXT_CANON}. A second rendering of the "
                    f"canon is the exact defect the move was made to close"
                )
    return errors


def check_registry_top_level_keys(pack_name, pack, warnings):
    """Registry top-level keys."""
    errors = []
    # 14. Registry TOP-LEVEL key parity between the template and migration.
    #     (added v5.1.1 - instance SEVEN of the founding/migration parity class)
    #
    #     Check 8 compares templates/* FILENAMES; it cannot see INSIDE a
    #     template. So when templates/registry.json gained a top-level
    #     `campus_os_version` key, founding got it (it writes the registry fresh
    #     from the template) and migration never did (it creates the registry
    #     only when absent, and stamped three named targets, none of them the
    #     top-level key). Every upgraded campus in the wild is missing it
    #     permanently, while every upgrade run reports success.
    #
    #     A fourth stamp target would fix today's key and guarantee a repeat.
    #     The durable rule: a top-level key the migration skill never even
    #     MENTIONS is a key upgraded campuses will never have.
    reg_t = SRC / "templates" / "registry.json"
    upd_p = SRC / "skills" / "update-workspace" / "SKILL.md"
    if reg_t.is_file() and upd_p.is_file():
        try:
            top_keys = list(json.loads(reg_t.read_text(encoding="utf-8")).keys())
        except (OSError, json.JSONDecodeError) as e:
            top_keys = []
            errors.append(f"check 14: templates/registry.json unreadable: {e}")
        upd_txt2 = upd_p.read_text(encoding="utf-8")
        for k in top_keys:
            if k.startswith("_"):        # `_note`/`_notes` are commentary
                continue
            if k not in upd_txt2:
                errors.append(
                    f"registry top-level key '{k}' exists in templates/registry.json "
                    f"but update-workspace/SKILL.md never mentions it - every "
                    f"UPGRADED campus would be permanently missing it while the "
                    f"upgrade reports success (SOP standing gate (a), instance 7)"
                )
    return errors


def check_derived_org_chart(pack_name, pack, warnings):
    """Derived org chart."""
    errors = []
    # 15. The org chart must be RE-DERIVED on upgrade, not preserved.
    #     (added v5.1.1 - instance EIGHT of the founding/migration parity class,
    #     and the one that hit item 8's own deliverable)
    #
    #     The staff-org entries are derived from skill frontmatter at build
    #     time, but migration was told to "never touch existing teams[] entries"
    #     - so the roster froze at whatever kernel version first wrote it and
    #     every release that adds skills silently staled it further. The fix is
    #     structural: the generator gained a --campus target, and migration must
    #     actually call it. Checking that BOTH exist is the point; either alone
    #     is a fix that never runs.
    gen = SRC / "tools" / "gen_department_entries.py"
    upd_o = SRC / "skills" / "update-workspace" / "SKILL.md"
    if not gen.is_file():
        errors.append("tools/gen_department_entries.py missing - the org chart has no generator")
    else:
        gen_txt = gen.read_text(encoding="utf-8")
        # Match the QUOTED argv token, not the bare string: negative test N13
        # renamed the flag to `--campusX`, which still contains "--campus" as a
        # substring and slipped straight through the first draft. A check that
        # a rename can satisfy is not a check.
        if '"--campus"' not in gen_txt:
            errors.append(
                "tools/gen_department_entries.py has no --campus target - it can only "
                "write templates/registry.json, so it cannot regenerate a LIVE campus "
                "and every upgraded campus keeps a stale org chart"
            )
        for token, why in (
            ("employees_added", "owner-added employees would be destroyed by the re-derive"),
            ("OWNED_TEAMS", "the generator must replace only the entries it owns, or an "
                            "owner-registered department is deleted on upgrade"),
        ):
            if token not in gen_txt:
                errors.append(f"tools/gen_department_entries.py missing '{token}' - {why}")
    if upd_o.is_file():
        upd_txt3 = upd_o.read_text(encoding="utf-8")
        if "gen_department_entries.py --campus" not in upd_txt3:
            errors.append(
                "update-workspace/SKILL.md never runs "
                "'gen_department_entries.py --campus' - the org-chart re-derive "
                "exists but no upgrade path calls it, so upgraded campuses keep "
                "reporting a stale roster (SOP standing gate (a), instance 8)"
            )
    return errors


def check_instruction_version_literals(pack_name, pack, warnings):
    """Instruction version literals."""
    errors = []
    plug_version = plugin_version()
    # 16. VERSION-LITERAL SWEEP across the whole tree (added v5.1.1).
    #     A standing SOP gate since 2026-07-06 that was run BY HAND - which is
    #     the whole problem, and it failed on this very build: CODEX-INSTALL.md
    #     told a buyer to `unzip campus-ai-os-v5.1.0.zip`, a filename that does
    #     not exist in a 5.1.1 package. Caught in post-package QA only because
    #     James asked whether the cut met the SOP; the automated check that
    #     existed (check 6) covers version markers in skills and JSON, not
    #     install instructions in prose.
    #
    #     Rules that matter ship as code that checks them. This is that rule
    #     applied to the sweep itself.
    #
    #     HISTORY IS ALLOWED, INSTRUCTIONS ARE NOT. A line recording what
    #     happened in a past release is correct and must not be rewritten; a
    #     line telling the owner what to type must never carry a version. The
    #     `version-literal-ok` marker draws that line explicitly, same shape as
    #     `platform-literal-ok`.
    if plug_version:
        maj_min = ".".join(plug_version.split(".")[:2])
        # Any full semver that is not the current one, in owner-facing prose.
        semver = re.compile(r"\bv?(\d+\.\d+\.\d+)\b")
        sweep = [SRC / "CODEX-INSTALL.md", SRC / "QUICKSTART.md", SRC / "PLATFORM.md"]
        sweep += sorted(SRC.glob("*.md"))
        for path in dict.fromkeys(sweep):
            if not path.is_file():
                continue
            rel = path.relative_to(SRC)
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if "version-literal-ok" in line:
                    continue
                for found in semver.findall(line):
                    if found == plug_version:
                        continue
                    # Only complain when the line reads as an instruction.
                    if re.search(r"unzip|download|attach|install|copy |curl|wget|`.*\.zip`|\.plugin\b",
                                 line, re.I):
                        errors.append(
                            f"{rel}:{n} names version {found} in an INSTRUCTION while "
                            f"this build is {plug_version} - a buyer following it types "
                            f"a filename that does not exist. Use v{{VERSION}} or a "
                            f"glob; mark genuine history with 'version-literal-ok'"
                        )
    return errors


def check_interop_emitter_and_reader(pack_name, pack, warnings):
    """Interop emitter and reader."""
    errors = []
    # 17. INTEROP: the assets[] emitter and reader must agree (added v5.1.1).
    #     playbooks/README.md is what a run EMITS; rollup-schema.md is what the
    #     reporting layer READS. They disagreed about assets[] from Interop v1
    #     until v5.1.1 - emitter wrote bare filename strings, reader specified
    #     objects carrying status/external_ref/completion. Reported after the
    #     Codex weekly-reset run (S222) and deferred twice as "minor".
    #
    #     One artifact, two hand-maintained contracts, no reconciliation: the
    #     class this release exists to close, inside its own runtime.
    emit = SRC / "playbooks" / "README.md"
    read = SRC / "skills" / "outcome-reporter" / "references" / "rollup-schema.md"
    if emit.is_file() and read.is_file():
        emit_txt = emit.read_text(encoding="utf-8")
        read_txt = read.read_text(encoding="utf-8")
        # The reader's status enum is the contract; the emitter must carry it.
        if "draft|published|local|scheduled|sent" in read_txt:
            for token, why in (
                ('"status"', "an asset with no status cannot be told from a published one"),
                ('"external_ref"', "a published asset with no handle cannot be found again, "
                                   "which is the join key outcome reads"),
            ):
                if token not in emit_txt:
                    errors.append(
                        f"interop: playbooks/README.md emits assets[] without {token}, "
                        f"but outcome-reporter/references/rollup-schema.md READS it - "
                        f"{why}. One artifact, two shapes (Interop v1 assets[])"
                    )
            # Scan ONLY inside fenced code blocks. Explanatory prose that quotes
            # the old bare-string form as history is correct and must not trip
            # this - the same false-positive guard check 12b needed, and it fired
            # here immediately: the paragraph documenting this very fix quotes
            # `"assets": ["01-extract-brief.md"]` and was flagged by the first
            # draft. A check that its own rationale cannot survive is too broad.
            in_fence = False
            for n, line in enumerate(emit_txt.splitlines(), 1):
                if line.lstrip().startswith("```"):
                    in_fence = not in_fence
                    continue
                if not in_fence:
                    continue
                if re.search(r'"assets"\s*:\s*\[\s*"', line):
                    errors.append(
                        f"interop: playbooks/README.md:{n} emits assets[] as bare "
                        f"filename STRINGS; Interop v1 and the reader schema both "
                        f"specify OBJECTS with status + external_ref. Emitter and "
                        f"reader must agree"
                    )
    return errors


def check_registry_writer_types(pack_name, pack, warnings):
    """Registry writer types."""
    errors = []
    # 18. A registry WRITE must target a type, not just a team name (v5.1.3).
    #     Found on the first real upgrade of a live campus. update-workspace
    #     item 11a said stamp "the `campus-ai-os` entry" - singular, no
    #     qualifier. That campus held TWO records under the name: the real
    #     type:kernel one and a stray type:authored-skill at 1.0.0. Matching by
    #     name hit both, promoting the stray to the current version and thereby
    #     HIDING it from the check that would have flagged it.
    #
    #     A bad read returns nothing; a bad write manufactures a fact. So a
    #     write step must name the type it means.
    upd_w = SRC / "skills" / "update-workspace" / "SKILL.md"
    if upd_w.is_file():
        body_w = upd_w.read_text(encoding="utf-8")
        # Scope to the numbered stamp-target list, then require the type to be
        # named inside it. The first draft used a single-line regex to hop from
        # "registry.json ->" to "`campus-ai-os`" - which sit on DIFFERENT lines,
        # so `.` never spanned them and the check failed on a correct tree.
        # Fourth regex fault of the session; the gate caught every one.
        # Scope to TARGET 2 ONLY - the numbered instruction line(s) between
        # "2." and "3." - never the surrounding rationale.
        #
        # Draft 1 scoped to the whole target list, which includes the paragraph
        # explaining WHY the type is required. That paragraph says "type:
        # kernel", so deleting the type from the instruction still passed:
        # the check was reading its own rationale as if it were the rule.
        # FIFTH instance this session of a check kept alive by nearby prose
        # (13a x2, 17, 19, this). Standing consequence: scope a structural
        # check to the line that carries the instruction, never to a block
        # that also explains it.
        m = re.search(r"\n\s*2\.\s+`\.campus-os/registry\.json`(.*?)\n\s*3\.\s",
                      body_w, re.S)
        target_block = m.group(1) if m else ""
        if not target_block:
            errors.append(
                "check 18 cannot find update-workspace's stamp target 2 - the "
                "write-target check is not actually running"
            )
        elif "type: kernel" not in target_block:
            errors.append(
                "update-workspace stamps the campus-ai-os registry entry without "
                "naming `type: kernel` - on a campus holding a duplicate record "
                "under that name it stamps BOTH, promoting the stray and hiding "
                "it. A write step must match on type AND team, never team alone"
            )
    return errors


def check_registry_reader_status(pack_name, pack, warnings):
    """Registry reader status."""
    errors = []
    # 19. Every registry READER that counts or reports must consult status
    #     (v5.1.3). diff_scan.py learned this in v5.1.1; campus-doctor did not,
    #     and reported a team retired months earlier as a current employee.
    #     Same registry, two readers, one taught and one not - payload item 4's
    #     defect recurring inside the release that closed it.
    #     Scoped to the ACTING line, never to prose that merely mentions the
    #     statuses - a comment explaining the rule kept draft 1 of this check
    #     passing after the filter itself was deleted.
    for rel, why, needle in (
        ("skills/campus-doctor/SKILL.md",
         "the staff count would include stood-down teams",
         # the instruction line must both SKIP and name all three statuses
         lambda t: any(
             "SKIP" in ln and "retired" in ln and "legacy" in ln and "disabled" in ln
             for ln in t.splitlines())),
        ("skills/hr-review/scripts/diff_scan.py",
         "flags would ignore the owner's own retirements",
         # The constant must be DEFINED non-empty *and* actually USED in a
         # comparison. Draft 2 accepted any non-comment line naming the three
         # statuses - which the printed remediation string does, so a gutted
         # filter still passed. Its own negative test refused to run and said
         # so, rather than reporting a false pass.
         lambda t: (
             re.search(r"RETIRED_STATUSES\s*=\s*\(\s*[\"']retired[\"']\s*,"
                       r"\s*[\"']legacy[\"']\s*,\s*[\"']disabled[\"']\s*,?\s*\)", t)
             and re.search(r"(?:not\s+)?in\s+RETIRED_STATUSES", t)
         )),
    ):
        p = SRC / rel
        if not p.is_file():
            continue
        if not needle(p.read_text(encoding="utf-8")):
            errors.append(
                f"{rel} reads .campus-os/registry.json but never consults `status` "
                f"(retired/legacy/disabled) in an acting line - {why}. Every "
                f"registry reader that counts, filters, or reports must read status"
            )
    return errors


def check_task_system_files(pack_name, pack, warnings):
    """Task system files."""
    errors = []
    # 11. Task System v2 must ship complete: the generator AND the spec that
    #     explains it. A generator with no spec is a tool nobody adopts; a spec
    #     with no generator is prose that requests a rule instead of checking it.
    for path, why in (
        ("tools/generate_task_index.py", "the task index would have to be kept by hand"),
        ("templates/tasks/_SPEC.md", "the task system would ship with no explanation"),
    ):
        if not (SRC / path).is_file():
            errors.append(f"{path} missing - {why}")
    return errors


def check_derived_department_rosters(pack_name, pack, warnings):
    """Derived department rosters."""
    errors = []
    # 20. The department roster must be DERIVED, and every department a team can
    #     file itself under must resolve to a roster (v5.1.4, payload item 2+7).
    #
    #     Two live orphans proved the class. `seo-team` carried
    #     `department: marketing` and was missing from Marketing's stored
    #     roster; `campus-stack-diagnostic` did the same to Sales. Both were
    #     invisible because check 19's reconciliation certified the headline
    #     against the same stale copy the breakdown came from - a reconciliation
    #     check proves the arithmetic, never the source set.
    #     Underneath them sat a second cause: registration-block-spec.md offered
    #     `dean` while every counter read `dean-office`, so an entry filed
    #     EXACTLY as the spec instructed was counted by neither.
    #
    #     Required as CODE - a constant defined AND used in a comparison - never
    #     as a string a comment or a printed message could also satisfy. That is
    #     the S223 rule: five checks passed that session while structurally
    #     unable to fail, every one of them kept alive by nearby prose.
    gen_d = SRC / "tools" / "gen_department_entries.py"
    if gen_d.is_file():
        gtxt = gen_d.read_text(encoding="utf-8")
        if not (re.search(r"^DEPT_ALIAS\s*=\s*\{[^}]*[\"']dean[\"']\s*:\s*[\"']dean-office[\"']",
                          gtxt, re.M)
                and re.search(r"DEPT_ALIAS\.get\(", gtxt)):
            errors.append(
                "gen_department_entries.py does not define AND use DEPT_ALIAS "
                "{'dean': 'dean-office'} - registration-block-spec.md offers a "
                "department value that no counter resolves, so a team filed "
                "exactly as the spec instructs lands in no roster at all"
            )
        # The CALL SITE, not the def. `re.search("derivable_names(teams)")`
        # matches `def derivable_names(teams):` too, so a gutted body with the
        # signature left behind would have passed - the S223 fault (a check a
        # rename can satisfy is not a check) reproduced inside the check
        # written to close it. Caught by negative test N20c refusing to run.
        if not (re.search(r"^def derivable_names\(", gtxt, re.M)
                and re.search(r"=\s*derivable_names\(teams\)", gtxt)):
            errors.append(
                "gen_department_entries.py does not derive the roster from each "
                "team's own `department:` field - the roster stays a second home "
                "for a fact the team already stores, which is the `seo-team` "
                "orphan. Derive, never store twice"
            )
        if not (re.search(r"^def orphans\(", gtxt, re.M)
                and re.search(r"=\s*orphans\(teams\)", gtxt)):
            errors.append(
                "gen_department_entries.py has no orphans() check wired into a "
                "run - an entry filed under an unresolvable department stays "
                "invisible to the org chart with nothing reporting it"
            )
    else:
        errors.append("tools/gen_department_entries.py missing - check 20 cannot run")
    return errors


def check_doctor_department_alias(pack_name, pack, warnings):
    """Doctor department alias."""
    errors = []
    #     20a. Every READER that counts must know the alias too. Teaching one
    #     reader and not the other is the exact defect S223 logged when
    #     `diff_scan.py` learned status and `campus-doctor` did not - the same
    #     registry, two readers, one taught. Scoped to the acting line.
    doc_d = SRC / "skills" / "campus-doctor" / "SKILL.md"
    if doc_d.is_file():
        dtxt = doc_d.read_text(encoding="utf-8")
        if not any("RESOLVE" in ln and "`dean`" in ln and "`dean-office`" in ln
                   for ln in dtxt.splitlines()):
            errors.append(
                "campus-doctor 8a counts by `department` but never resolves the "
                "`dean` -> `dean-office` alias in an acting line - a team filed "
                "exactly as registration-block-spec.md instructs is counted by "
                "no reader at all"
            )
    return errors


def check_published_department_enum_parity(pack_name, pack, warnings):
    """Published department enum parity."""
    errors = []
    gen_d = SRC / "tools" / "gen_department_entries.py"
    #     20b. The enum the spec PUBLISHES and the departments the generator
    #     COUNTS must be the same set. Two hand-maintained lists that must agree
    #     is the defect this release exists to close, so it is verified rather
    #     than trusted.
    spec_d = SRC / "templates" / "registration-block-spec.md"
    if spec_d.is_file() and gen_d.is_file():
        m = re.search(r'^\s*"department":\s*"([^"]+)"', spec_d.read_text(encoding="utf-8"), re.M)
        if not m:
            errors.append(
                "registration-block-spec.md has no `department` enum line - "
                "check 20b is not actually running"
            )
        else:
            published = {v.strip() for v in m.group(1).split("|")}
            gtxt = gen_d.read_text(encoding="utf-8")
            emp = re.search(r"^EMP_DEPTS\s*=\s*\[(.*?)\]", gtxt, re.M | re.S)
            counted = set(re.findall(r"[\"']([^\"']+)[\"']", emp.group(1))) if emp else set()
            counted |= {"kernel", "core", "cross"}
            missing = counted - published
            extra = published - counted - {"dean"}   # `dean` is read-only legacy
            if missing:
                errors.append(
                    f"registration-block-spec.md's department enum is missing "
                    f"{sorted(missing)} - the generator counts a department the "
                    f"spec never tells a team plugin it may file under"
                )
            if extra:
                errors.append(
                    f"registration-block-spec.md publishes department(s) "
                    f"{sorted(extra)} that no roster counts - a team filing "
                    f"there is invisible to the org chart"
                )
    return errors


def check_kernel_entry_lockstep(pack_name, pack, warnings):
    """Kernel entry lockstep."""
    errors = []
    plug_version = plugin_version()
    # 21. Every shipping `type: kernel` entry moves in lockstep (v5.1.4,
    #     payload item 6). Atlas folded into the kernel at v5.1.0 and was never
    #     added to update-workspace's stamp-target list, so it froze at its
    #     fold-in version and had already drifted one cut by 5.1.3. The fix is
    #     the spec, not the instance - a hand-stamped entry is a standing gate
    #     run by hand, which is a gate that will be skipped.
    reg_k = SRC / "templates" / "registry.json"
    if reg_k.is_file():
        try:
            kregs = [t for t in json.loads(reg_k.read_text(encoding="utf-8")).get("teams", [])
                     if t.get("type") == "kernel"]
        except json.JSONDecodeError:
            kregs = []
        vers = {t.get("version") for t in kregs}
        if len(vers) > 1:
            errors.append(
                "templates/registry.json ships `type: kernel` entries at "
                f"{len(vers)} different versions {sorted(v for v in vers if v)} - "
                "they all ship in one plugin and have no independent version, so "
                "a divergence means an entry was left out of the stamp"
            )
        if plug_version and vers and vers != {plug_version}:
            errors.append(
                f"templates/registry.json `type: kernel` entries are at "
                f"{sorted(v for v in vers if v)}, plugin manifest is at "
                f"{plug_version} - the shipped kernel records disagree with the "
                f"build they ship in"
            )
        upd_k = SRC / "skills" / "update-workspace" / "SKILL.md"
        if upd_k.is_file():
            body_k = upd_k.read_text(encoding="utf-8")
            mk = re.search(r"\n\s*2\.\s+`\.campus-os/registry\.json`(.*?)\n\s*3\.\s",
                           body_k, re.S)
            blk = mk.group(1) if mk else ""
            if not blk:
                errors.append(
                    "check 21 cannot find update-workspace's stamp target 2 - "
                    "the kernel-stamp scope check is not actually running"
                )
            elif not re.search(r"EVERY entry whose `type` is\s*\n?\s*`kernel`", blk):
                errors.append(
                    "update-workspace's stamp target 2 does not stamp EVERY "
                    "`type: kernel` entry - a target list of team names is only "
                    "correct until the next fold-in, which is exactly how kernel "
                    "`atlas` froze at 5.1.2"
                )
    return errors


def check_founding_departments(pack_name, pack, warnings):
    """Founding departments."""
    errors = []
    # 22. campus-start must DERIVE its department list from the pack (v5.1.5).
    #     Found by the first cold install of 5.1.4. campus-start resolves
    #     pack.json and then ignored `departments[]`, hardcoding "the four staff
    #     departments - Community, Education, Marketing, Sales - no matter what"
    #     while the pack declared five. So `departments/lead-generation/` was
    #     never created, the lead-generation manager shipped pointing at a
    #     dept_dir that did not exist, and the founding contradicted the org
    #     chart - with nothing failing, because lint_managers downgrades a
    #     missing dept_dir to a warning on purpose.
    #
    #     Same one-fact-two-homes class as the seo-team orphan, one layer up:
    #     the READER learned about the new department, the WRITER did not.
    #     Invisible on a campus that upgrades rather than founds.
    #
    #     Scoped to CODE-FENCE-FREE instruction lines and excluding the block
    #     that explains the fix - check 17 and 12b both needed that guard, and
    #     five checks in S223 passed while structurally unable to fail because
    #     their search window included their own rationale.
    start_d = SRC / "skills" / "campus-start" / "SKILL.md"
    if start_d.is_file() and pack.get("departments"):
        stxt = start_d.read_text(encoding="utf-8")
        # EXCLUDE the rationale block, which necessarily quotes the old
        # hardcoded string - but exclude only that block, by delimiter, never a
        # positional cut. Draft 1 cut the file at the marker and so skipped
        # Step 2 entirely, failing a correct tree: the rationale sits in the
        # MIDDLE of the file, not at the end. The false-positive guard caught
        # it, which is exactly the job the guard exists for.
        lines_s = stxt.splitlines()
        skip = set()
        inside = False
        for i, ln in enumerate(lines_s):
            if "`DEPT_LABELS` is RESOLVED" in ln:
                inside = True
            elif inside and ln.startswith("## "):
                inside = False
            if inside:
                skip.add(i)
        labels = {d.replace("-", " ").title() for d in pack["departments"]}
        # A hardcoded list = 3+ department display names on one instruction line.
        for i, ln in enumerate(lines_s, 1):
            if (i - 1) in skip:
                continue
            if sum(1 for L in labels if L in ln) >= 3:
                errors.append(
                    f"campus-start/SKILL.md:{i} hardcodes a department list "
                    f"({ln.strip()[:70]}...) - it must render the pack's "
                    f"departments[]. A typed list silently drops every "
                    f"department a pack adds, exactly as v5.1.4 dropped "
                    f"lead-generation on every founded campus"
                )
                break
        # Require the RENDER TOKEN `{DEPT_LABELS}`, not the bare word - the
        # rationale block writes it in backticks, so a bare-word test would be
        # satisfied by the explanation after the usage was deleted. Same fault
        # the S223 checks kept making, and the reason 20's "is it used" test
        # had to be tightened to the call site rather than the def.
        if stxt.count("{DEPT_LABELS}") < 2:
            errors.append(
                "campus-start/SKILL.md never renders {DEPT_LABELS} - the founding "
                "interview and the department folders would not follow the "
                "pack's departments[]"
            )
        if not re.search(r"one folder per entry in the pack's `departments\[\]`", stxt):
            errors.append(
                "campus-start/SKILL.md does not create one folder per pack "
                "department - a declared manager would ship pointing at a "
                "dept_dir that founding never creates"
            )
    return errors


def check_founding_owner_conversation(pack_name, pack, warnings):
    """Founding owner conversation."""
    errors = []
    start_d = SRC / "skills" / "campus-start" / "SKILL.md"
    # 23. Founding must not write PRE-SUPPLIED context as though the owner said
    #     it (v5.1.5). Found on a real founding run: the interview asserted the
    #     owner's company by name before asking, and traced it to host account
    #     preferences when challenged.
    #
    #     Why it needs a check of its own: the founding's whole quality
    #     mechanism is "push back once on a vague answer", and you cannot push
    #     back on an answer you were handed - nothing looks vague, so nothing
    #     fires. Every other defect in this class is two copies of a fact INSIDE
    #     the campus; this one arrives from outside it, so no file check can
    #     detect the fact itself. What CAN be checked is that the skill carries
    #     the rule.
    if start_d.is_file():
        stxt2 = start_d.read_text(encoding="utf-8")
        if "PRE-SUPPLIED CONTEXT" not in stxt2:
            errors.append(
                "campus-start/SKILL.md has no PRE-SUPPLIED CONTEXT rule - a host "
                "that hands the assistant the owner's business summary defeats "
                "the vague-answer pushback silently, and the campus writes "
                "shared/*.md from words the owner never said"
            )
        else:
            # The three parts must each survive as an ACTING line, not merely be
            # summarised in the heading. A rule a reader can satisfy by quoting
            # its own title is not a rule.
            for needle, why in (
                (r"say in one line what you appear to know and where it came from",
                 "the owner is never told the assistant was pre-briefed"),
                (r"Pre-supplied context is a starting point, never a\s*\n?\s*substitute",
                 "pre-supplied context could stand in for the interview"),
                (r"until the owner has said it in their\s*\n?\s*own words in THIS conversation",
                 "unconfirmed host context reaches shared/*.md and becomes the campus voice"),
            ):
                if not re.search(needle, stxt2):
                    errors.append(
                        f"campus-start/SKILL.md's PRE-SUPPLIED CONTEXT rule is "
                        f"missing its acting line ({needle[:44]}...) - {why}"
                    )
    return errors


def check_department_label_parity(pack_name, pack, warnings):
    """Department label parity."""
    errors = []
    # 24. A department's LABEL has exactly one owner (v5.1.6). Found in the
    #     field: the 5.1.5 founding rendered the pack's display names ("Media
    #     Desk", "Teaching Desk") and campus-doctor rendered the generator's own
    #     dict ("Marketing", "Education") - two vocabularies for the same five
    #     departments, shown to the same owner minutes apart.
    #
    #     The v5.1.4 hardcode in campus-start had been MASKING it: it typed
    #     plain names that happened to match the generator, so the pack's labels
    #     were never shown to anyone and the two owners never met. Deriving the
    #     list (fix 22) did not create the divergence, it revealed it.
    #
    #     Underneath sat a second fault: the generator's dict held "Community"
    #     and "Education" - the EDUCATION PACK's words living in the kernel.
    #     S206 exactly: the kernel hardcoded a taxonomy fitting one business
    #     type, and the fix belongs in the architecture, not the labels.
    gen_l = SRC / "tools" / "gen_department_entries.py"
    if gen_l.is_file():
        ltxt = gen_l.read_text(encoding="utf-8")
        # (a) the kernel default must exist AND stay generic. "Community" and
        #     "Education" in KERNEL_LABEL means a niche leaked back into it.
        mk = re.search(r"^KERNEL_LABEL\s*=\s*\{(.*?)\}", ltxt, re.M | re.S)
        if not mk:
            errors.append(
                "gen_department_entries.py has no KERNEL_LABEL - the generic "
                "default layer is gone, so a pack that declares no display_name "
                "has no label to fall back to"
            )
        else:
            kl = dict(re.findall(r'"([^"]+)":\s*"([^"]+)"', mk.group(1)))
            for dept, niche in (("community", "Community"), ("education", "Education")):
                if kl.get(dept) == niche:
                    errors.append(
                        f"KERNEL_LABEL[{dept!r}] is {niche!r} - that is the "
                        f"education pack's word sitting in the kernel default. "
                        f"The generic layer must read 'Client Support' / "
                        f"'Client Delivery'; the pack overrides it"
                    )
        # (b) the override must actually be applied, as code, at the call site.
        if not (re.search(r"^def resolve_labels\(", ltxt, re.M)
                and re.search(r"=\s*resolve_labels\(", ltxt)):
            errors.append(
                "gen_department_entries.py does not resolve labels through "
                "resolve_labels() - the pack's display_name override is never "
                "applied, so every niche ships the kernel's generic words"
            )
        # (c) campus-start must READ the resolved label, never resolve its own.
        st_l = SRC / "skills" / "campus-start" / "SKILL.md"
        if st_l.is_file():
            sl = st_l.read_text(encoding="utf-8")
            if not re.search(r"`type: department` entries -> each entry's\s*\n?\s*`label` field", sl):
                errors.append(
                    "campus-start/SKILL.md does not render DEPT_LABELS from the "
                    "registry template's `label` field - a second resolver is "
                    "how the founding and the org chart came to show different "
                    "words for the same departments"
                )
            # Scope the MUST-NOT test outside the PARENTHETICAL rationale only -
            # `*(v5.1.6: ... )*` - never the whole ⚠️ block.
            #
            # Draft 1 excluded from the ⚠️ marker to the next heading. But the
            # marker sits on the SAME LINE as the instruction, so the entire
            # rule fell inside the exclusion and this test became structurally
            # unable to fail: negative test N24c reverted campus-start to a
            # second resolver and the gate said OK. Third instance this release
            # of a check whose search window swallowed the line it was meant to
            # police (13a in S223, check 22 draft 1, this). The delimiter must
            # be the rationale itself, not the block that contains it.
            keep, inside_l = [], False
            for ln_l in sl.splitlines():
                if "*(v5.1.6:" in ln_l:
                    inside_l = True
                if not inside_l:
                    keep.append(ln_l)
                if inside_l and ")*" in ln_l:
                    inside_l = False
            # STRUCTURAL, not phrase-matching: campus-start reads the resolved
            # `label`, so it has no legitimate use for `display_name` at all.
            # (`managers[].dept_dir` IS legitimate - fix 22 takes folder paths
            # from it - so the forbidden token is the field, not the array.)
            #
            # Draft 2 matched the English sentence "render each one's
            # `display_name` from `managers[]`" and N24c slipped through by
            # capitalising the first word. **A check a rename - or a capital
            # letter - can satisfy is not a check** (S223). Match the field
            # name, which cannot be paraphrased.
            if "display_name" in "\n".join(keep):
                errors.append(
                    "campus-start/SKILL.md references `display_name` outside its "
                    "rationale - that makes it a SECOND label resolver. It must "
                    "read the already-resolved `label` in templates/registry.json"
                )
        # (c-ii) campus-doctor is the THIRD owner, and v5.1.6 missed it (found
        #     on the 5.1.6 cold install). Its 8a report line hardcoded
        #     "Marketing {m}, Sales {s}, Community {c}, Education {e}, ..." and
        #     the skill never read `label` at all - so a campus shipping
        #     education -> "Teaching" was reported as "Education 3".
        #
        #     The rule this violates was already written down (S223): when a fix
        #     teaches one reader something, ask which OTHER readers of the same
        #     fact need it. v5.1.6's check covered exactly the two files that
        #     had been edited, which is how it passed while a third owner stood
        #     untouched. A hardcoded list also silently drops any department the
        #     pack adds - the same failure as check 22's, one reader over.
        doc_lbl = SRC / "skills" / "campus-doctor" / "SKILL.md"
        if doc_lbl.is_file():
            dl = doc_lbl.read_text(encoding="utf-8")
            if not re.search(r"from the `label` field on\s*\n?\s*its own `type: department` registry entry", dl):
                errors.append(
                    "campus-doctor/SKILL.md does not take department names from "
                    "the registry `label` field - it becomes a THIRD owner of a "
                    "fact the kernel default + pack override already decide, and "
                    "reports the wrong word on every pack that overrides one"
                )
            # Negative half, deliberately NARROW: the old output TEMPLATE must
            # not come back. Scoped outside the *Why (found on...)* rationale,
            # which necessarily quotes it.
            #
            # Draft 1 flagged any line carrying 3+ department names, and failed
            # a correct tree twice - once on the S224 rationale quoting a real
            # past report ("45 employees (Marketing 7, Sales 8, ...)") and once
            # on the sample-output block. Both are legitimate. **A check too
            # broad to survive its own file's history is too broad** (S223), and
            # a check that fails correct trees gets disabled, which is worse
            # than not having it. The positive requirement above is the load-
            # bearing half; this one only catches the specific regression of
            # re-pasting the placeholder template.
            keep_d, inside_d = [], False
            for ln_d in dl.splitlines():
                if "*Why (found on the 5.1.6 cold install):*" in ln_d:
                    inside_d = True
                if not inside_d:
                    keep_d.append(ln_d)
                if inside_d and "check 24 now fails the build" in ln_d:
                    inside_d = False
            if re.search(r"Marketing \{[a-z]\},\s*Sales \{[a-z]\}", "\n".join(keep_d)):
                errors.append(
                    "campus-doctor/SKILL.md has re-introduced the hardcoded "
                    "department-name output template - each name must come from "
                    "that department's `label` in the registry, or every pack "
                    "that renames or adds a department is reported wrongly"
                )

        # (d) PARITY: the labels shipped in the registry template must equal
        #     what resolving default+override produces right now. A generated
        #     file that drifts from its generator is the whole defect class.
        try:
            sys.path.insert(0, str(SRC / "tools"))
            import importlib
            gde = importlib.import_module("gen_department_entries")
            importlib.reload(gde)
            want = gde.resolve_labels(str(SRC / "packs" / pack_name / "pack.json"))
            have = {t["team"]: t.get("label")
                    for t in json.loads((SRC / "templates" / "registry.json")
                                        .read_text(encoding="utf-8")).get("teams", [])
                    if t.get("type") == "department"}
            drift_l = {k: (have.get(k), v) for k, v in want.items() if have.get(k) != v}
            if drift_l:
                errors.append(
                    f"templates/registry.json department labels drift from "
                    f"resolve_labels(): {drift_l} - re-run "
                    f"tools/gen_department_entries.py"
                )
        except Exception as e:                                   # noqa: BLE001
            errors.append(f"check 24 parity could not run: {e}")
    return errors


# Single registry, preserving the historical execution order.
CHECKS = (
    ("NICHE-001", "Manifest shape", check_manifest_shape),
    ("NICHE-002", "Declared domain skills", check_declared_domain_skills),
    ("NICHE-003", "Orphan pack skills", check_orphan_pack_skills),
    ("NICHE-004", "Pack departments", check_pack_departments),
    ("NICHE-005", "Pack version lockstep", check_pack_version_lockstep),
    ("NICHE-005B", "Derived manifest parity", check_derived_manifest_parity),
    ("NICHE-006A", "Registry version lockstep", check_registry_version_lockstep),
    ("NICHE-006B", "Skill version resolution", check_skill_version_resolution),
    ("NICHE-007", "Platform bindings", check_platform_bindings),
    ("NICHE-008", "Founding and migration templates", check_founding_and_migration_templates),
    ("NICHE-008B", "Scaffold directory parity", check_scaffold_directory_parity),
    ("NICHE-009", "Ledger schema parity", check_ledger_schema_parity),
    ("NICHE-007B", "Platform resolver pointer", check_platform_resolver_pointer),
    ("NICHE-010", "Manager lint", check_manager_lint),
    ("NICHE-012A", "Up-to-date comparison", check_up_to_date_comparison),
    ("NICHE-012B", "Version-family routing", check_version_family_routing),
    ("NICHE-012C", "Additions reachability", check_additions_reachability),
    ("NICHE-013", "Context canon table", check_context_canon_table),
    ("NICHE-013A", "Founding and context canon parity", check_founding_and_context_canon_parity),
    ("NICHE-013B", "Context readers and writers", check_context_readers_and_writers),
    ("NICHE-013C", "Context canon pointers", check_context_canon_pointers),
    ("NICHE-014", "Registry top-level keys", check_registry_top_level_keys),
    ("NICHE-015", "Derived org chart", check_derived_org_chart),
    ("NICHE-016", "Instruction version literals", check_instruction_version_literals),
    ("NICHE-017", "Interop emitter and reader", check_interop_emitter_and_reader),
    ("NICHE-018", "Registry writer types", check_registry_writer_types),
    ("NICHE-019", "Registry reader status", check_registry_reader_status),
    ("NICHE-011", "Task system files", check_task_system_files),
    ("NICHE-020", "Derived department rosters", check_derived_department_rosters),
    ("NICHE-020A", "Doctor department alias", check_doctor_department_alias),
    ("NICHE-020B", "Published department enum parity", check_published_department_enum_parity),
    ("NICHE-021", "Kernel entry lockstep", check_kernel_entry_lockstep),
    ("NICHE-022", "Founding departments", check_founding_departments),
    ("NICHE-023", "Founding owner conversation", check_founding_owner_conversation),
    ("NICHE-024", "Department label parity", check_department_label_parity),
)


def check(pack_name: str, warnings: list = None, only=None) -> list:
    if warnings is None:
        warnings = []
    pack, errs = load_pack(pack_name)
    if errs:
        return [f"NICHE-001: {error}" for error in errs]
    errors = []
    for code, title, function in CHECKS:
        if only is None or code in only:
            errors.extend(f"{code}: {error}" for error in function(pack_name, pack, warnings))
    return errors


def assemble(pack_name: str, out_dir: Path) -> list:
    errors = check(pack_name, [])
    if errors:
        return errors
    pack, _ = load_pack(pack_name)
    keep = set(pack.get("domain_skills", []))
    drop = set()
    for pdir in (SRC / "packs").iterdir():
        if pdir.is_dir() and pdir.name != pack_name:
            pj, _ = load_pack(pdir.name)
            if pj:
                drop.update(s for s in pj.get("domain_skills", []) if s not in keep)

    if out_dir.exists():
        return [f"refusing to overwrite existing {out_dir}"]
    shutil.copytree(SRC, out_dir, ignore=shutil.ignore_patterns("*.plugin", "*.zip", ".git"))
    for other in (out_dir / "packs").iterdir():
        if other.is_dir() and other.name != pack_name:
            shutil.rmtree(other)
    for skill in drop:
        for sub in (out_dir / "skills" / skill, out_dir / "commands" / f"{skill}.md"):
            if sub.is_dir():
                shutil.rmtree(sub)
            elif sub.exists():
                sub.unlink()
    print(f"assembled {pack_name} -> {out_dir} (kept {len(keep)} domain skills, dropped {len(drop)})")
    return []


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pack", default="education")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--assemble", metavar="OUT_DIR")
    ap.add_argument("--sync-manifests", action="store_true",
                    help="regenerate the derived Codex manifest from the Claude one")
    ap.add_argument("--list", action="store_true", help="list finding codes and titles")
    ap.add_argument("--only", metavar="CODE[,CODE]", help="run selected checks")
    args = ap.parse_args()
    if args.list:
        for code, title, function in CHECKS:
            print(f"{code} {title}")
        return
    only = None
    if args.only is not None:
        only = {code.strip() for code in args.only.split(",")}
        unknown = only - {row[0] for row in CHECKS}
        if unknown:
            ap.error("unknown finding code(s): " + ", ".join(sorted(unknown)))
        if args.assemble or args.sync_manifests:
            ap.error("--only cannot be combined with --assemble or --sync-manifests")

    if args.sync_manifests:
        errs = sync_manifests()
        if errs:
            for e in errs:
                print(f"FAIL: {e}")
            sys.exit(1)
        print(f"OK: {CODEX_MANIFEST} regenerated from {CLAUDE_MANIFEST}")
        sys.exit(0)

    if not args.check and not args.assemble:
        args.check = True  # default action

    warnings = []
    errors = assemble(args.pack, Path(args.assemble)) if args.assemble else check(args.pack, warnings, only)
    for w in warnings:
        print(f"WARN: {w}")
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        sys.exit(1)
    print(f"OK: pack '{args.pack}' conformant" + ("" if not args.assemble else " and assembled")
          + (f" ({len(warnings)} warning(s))" if warnings else ""))
    sys.exit(0)


if __name__ == "__main__":
    main()
