---
name: update-workspace
description: >
  Safely upgrade an existing Campus AI OS campus (any earlier version) to the
  installed version, keeping everything the owner wrote intact. Use when the
  owner says "/update-workspace", "upgrade my campus", "update my campus", or
  when an older campus is detected.
version: 5.2.9
department: kernel
---

# /update-workspace - Upgrade Without Losing Anything

The prime directive: an upgrade can NEVER destroy anything the owner wrote.
This skill only ADDS. It never rewrites, deletes, renames, or "refreshes" an
existing file (exception: item 12e's kernel canons). If a step would break
that rule, stop and ask. Lookup files: this skill's `references/`
(`baseline-items.md`, `additions.md`).

**Platform resolution (do this first):** resolve `PLUGIN_MANIFEST` and
`ENTRY_FILE` per `PLATFORM.md` at the plugin root. **Never hardcode either.**
Detect permissively - any of `CLAUDE.md` / `AGENTS.md` / `AGENTS.override.md`
/ `CODEX.md`. Edit the entry file THAT CAMPUS already has; create a missing
redirect as `ENTRY_FILE`. Never rename the owner's file.

**Version resolution (do this second):** `OS_VERSION` = `PLUGIN_MANIFEST` ->
`version`. Every version written or said is `OS_VERSION`. **Never write a
hardcoded version literal.**

## Step 0 - What's here

The campus root holds a `dean/` entry file (any of the four). Markers: `workspace.json`, that entry
file, `shared/` with content, `.campus-os/`. Route by comparing the campus
marker to `OS_VERSION`:

- **No markers:** fresh folder; offer /campus-start, never build here.
- **Marker == `OS_VERSION`:** "You're already up to date." Offer
  /campus-doctor. The ONLY up-to-date case: a comparison, never a literal.
- **Marker < `OS_VERSION`:** an upgrade is owed. Pick the entry point for
  that marker from `baseline-items.md`.

🔒 **Closing rule - every upgrade path ends the same way, no exceptions.**
Whatever the entry point, finish with additions items 11-16 (idempotent)
and stamp `OS_VERSION`.

📌 Non-default campuses are normal: read names and folders from what exists.

## Steps 1-3 (every run)

1. Ask in one line whether a backup includes this campus folder; if not,
   help them get one.
2. Preview every create and insert with the actual text, zero writes, then
   wait for an explicit go.
3. Copy the entry file, memory.md, TASKS.md and each shared file to
   `dean/archive/pre-v3/{date}/` (never `dean/` recursively into itself);
   restore from it on failure.

## Step 4 - The upgrade (additive only)

**Items 1-10, the v2/v3 baseline** (`baseline-items.md`):
`.campus-os/registry.json` from `templates/registry.json` if absent;
`workspace.json` if absent (`OS_VERSION`, `structure` and filing key from
real folders); a root redirect as `ENTRY_FILE` only when none of the four
exists; missing kernel blocks inserted into `dean/{ENTRY_FILE}` (owner text
never rewritten); ledger header; `shared/setup-progress.md` with the goals
row; goals stub if absent; `dean/skill-candidates/`; item 8,
`.campus-os/registration-block-spec.md`, now item 16.

**Items 11-16 run on every path** (`additions.md`):

11. **v4 additions (every campus, run last).**
    a. Stamp three targets with `OS_VERSION`, resolved at runtime:
       1. `workspace.json` -> `version`
       2. `.campus-os/registry.json` -> **EVERY entry whose `type` is
          `kernel`** - match on `type: kernel` first, then `team`, never on
          team alone; two matches -> stamp NONE and ask.
       3. `.campus-os/registry.json` -> top-level `campus_os_version` (add if
          absent)
    a-ii. Add every top-level key the template has and the campus lacks
       (`campus_os_version`, `updated` = today, `teams`, `playbooks`); never
       touch `_`-prefixed keys.
    b-h. `playbooks[]`, kernel entries to full spec, the `type: systems`
       catalog, each if absent; `.campus-os/scan/`;
       `.campus-os/model-routing.md` from `templates/model-routing.md` if
       absent; folded-in HR skills (tell, never uninstall); the
       playbook-routing block into `dean/{ENTRY_FILE}` under marker
       `<!-- campus-os:playbook-routing -->`.
12. **v5.1 additions (every campus, additive only).** `atlas/config/`;
    `atlas` kernel entry if absent; folded-in Atlas (tell, never uninstall);
    12e: the three kernel canons **overwritten** if present (pure kernel
    content) - `.campus-os/context-files.md` from
    `templates/context-files.md`, `.campus-os/ledger-paths.md` from
    `templates/ledger-paths.md`, `.campus-os/run-id-and-interop.md` from
    `templates/run-id-and-interop.md`; org chart RE-DERIVED by `python3
    tools/gen_department_entries.py --campus {campus_root}` (owner additions
    untouched); stale Atlas guard in the entry file: mention only.
13. **v5.1.8 additions (every campus, additive only).** Append each template
    `type: department` entry the campus lacks (match on type AND team),
    empty roster; the spec enum is item 16's.
14. **v5.1.9 additions (every campus, read-side only).** Run `node
    tools/context-weight.mjs --root {campus_root}`; report its verdict
    (UNKNOWN -> the finding, not a number). Writes nothing.
15. **v5.1.10 additions (every campus, read-side only).** Say once: UNKNOWN
    is a weight band; `context-prune` moves only `[archive-eligible]`
    entries. Writes nothing.
16. **v5.2.0 additions (every campus, additive only).** MATERIALIZE the
    registration spec: `python3 tools/materialize_registration_spec.py
    --campus-root {campus_root}`, `--capture-notes` first when it refuses a
    hand-edited copy.

## Step 4b - Department managers

Per `baseline-items.md`, each manager with its own preview and go; skipping
is valid, record it.

## Never touch

wiki/, memory.md contents, outputs/, inputs/, daily/, department and manager
folders, active-work/, library/, TASKS.md, archives, any owner-written
section. Nothing is deleted or renamed.

## Step 5 - Report; rules

Created, inserted where, safety copy location, staff line before/after,
weight verdict, one next step: /campus-doctor.
Grade-8 words. Preview before write; explicit go before Step 3; running
twice adds nothing twice.

## File anchoring (critical)

Kernel preamble §2 applies: `references/kernel-preamble.md`.
