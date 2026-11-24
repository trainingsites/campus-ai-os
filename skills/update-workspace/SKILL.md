---
name: update-workspace
description: >
  Safely upgrade an existing Campus AI OS campus (any earlier version) to the
  installed version, keeping everything the owner wrote intact. Use when the
  owner says "/update-workspace", "upgrade my campus", "update my campus",
  "undo the last update", or when an older campus is detected.
version: 5.3.8
department: kernel
---

# /update-workspace - Upgrade Without Losing Anything

The prime directive: an upgrade can NEVER destroy anything the owner wrote.
This skill only ADDS. It never rewrites, deletes, renames, or "refreshes" an
existing file (exceptions: item 12e's kernel canons; department labels
after the owner types RENAME, part b). If a step would break
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

↩️ **"Undo the last update":** do only `additions.md` -> "Undo". Skip the
edition check and every step below; the undo tool is the same in every
edition, so it runs whichever edition is installed.

The campus root holds a `dean/` entry file (any of the four). Markers: `workspace.json`, that entry
file, `shared/` with content, `.campus-os/`. Route by comparing the campus
marker to `OS_VERSION`:

🛑 **Edition check - first, before any route below and before item 18.** Only
when a campus marker exists (a fresh folder goes straight to "No markers"). Compare the
campus's `workspace.json` -> `pack` with the plugin's `packs/active.json` ->
`active_pack` (`additions.md`, "v5.3.5 additions", part b). Different
editions: stop, zero writes, say so in plain words. Never relabel an
existing campus for another edition. An owner who answers "this edition"
when the names differ is asked once more, with the renames shown, before
anything is written (part b, "Second confirm").

- **No markers:** fresh folder; offer /campus-start, never build here.
- **Marker == `OS_VERSION`:** "You're already up to date." Steps 1-3
  first when anything below will write, then run item 18
  (the kit check; a missing or damaged kit is re-copied) and the v5.3.5
  parts of item 17 (seat file, `pack`, job cards, each only when absent),
  then offer
  /campus-doctor. The ONLY up-to-date case: a comparison, never a literal.
- **Marker < `OS_VERSION`:** an upgrade is owed. Pick the entry point for
  that marker from `baseline-items.md`.

🔒 **Closing rule - every upgrade path ends the same way, no exceptions.**
Whatever the entry point, finish with additions items 11-18 (idempotent)
and stamp `OS_VERSION`.

📌 Non-default campuses are normal: read names and folders from what exists.

## Steps 1-3 (every run)

1. Ask in one line whether a backup includes this campus folder; if not,
   help them get one.
2. Preview every create and insert with the actual text, zero writes, then
   wait for an explicit go.
3. Copy the entry file, memory.md, TASKS.md and each shared file to
   `dean/archive/pre-v3/{date}/` (never `dean/` recursively into itself);
   restore from it on failure. Then take the undo snapshot, before the
   first write of any kind: `python3 -I -B tools/update_undo.py snapshot
   --campus-root {campus_root}` from the plugin root; after the last write,
   `seal` with the name it printed (`additions.md`, "Undo").

## Step 4 - The upgrade (additive only)

**Items 1-10, the v2/v3 baseline** (`baseline-items.md`):
`.campus-os/registry.json` from `templates/registry.json` if absent;
`workspace.json` if absent (`OS_VERSION`, `structure` and filing key from
real folders); a root redirect as `ENTRY_FILE` only when none of the four
exists; missing kernel blocks inserted into `dean/{ENTRY_FILE}` (owner text
never rewritten); ledger header; `shared/setup-progress.md` with the goals
row; goals stub if absent; `dean/skill-candidates/`; item 8,
`.campus-os/registration-block-spec.md`, now item 16.

**Items 11-18 run on every path** (`additions.md`). Item 18 (the kernel
kit) runs FIRST, after the Step 0 edition check and the Step 3 snapshot, before item 11: every later `tools/` command runs from
the kit (Kernel preamble §5).

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
17. **v5.2.4 and v5.2.12 additions (every campus, additive only).** The
    v5.2.4 seat resolver refresh (a-c), then v5.2.12: insert the outside-text
    rule into `dean/{ENTRY_FILE}` under marker
    `<!-- campus-os:outside-text -->` if absent (owner text never rewritten),
    and say once that `tools/resolve_context.py` now finds the campus and its
    context files. The 12e canon refresh already carries the new read order.
    Then v5.3.5: write the seat file when the campus has none (ask which
    apps work here, never guess), and record the campus's edition as
    `workspace.json` -> `pack` when the key is absent; copy the pack's job
    cards to `dean/job-cards.md` when it ships them and the campus has none.
18. **Kernel kit (every campus, kernel-owned files only).** Copy or refresh
    `.campus-os/kernel/` from the plugin's `tools/kit-manifest.json`: the
    `core` tier always, the `on_demand` tier when this run uses one of its
    tools; then `kernel_kit.py check --installed-version {OS_VERSION}`.
    Forward-only: a kit newer than the plugin is never replaced. Steps, the
    Cowork path and the fallback: `additions.md` item 18.

## Step 4b - Department managers

Per `baseline-items.md`, each manager with its own preview and go; skipping
is valid, record it.

## Never touch

wiki/, memory.md contents, outputs/, inputs/, daily/, department and manager
folders, active-work/, library/, TASKS.md, archives, any owner-written
section. Nothing is deleted or renamed (department labels: part b only).

## Step 5 - Report; rules

Created, inserted where, safety copy location, staff line before/after,
weight verdict, the one sentence that says how to undo this update
(`additions.md`, "Undo"), one next step: /campus-doctor.
Grade-8 words. Preview before write; explicit go before Step 3; running
twice adds nothing twice.

## File anchoring (critical)

Kernel preamble §2 applies: `references/kernel-preamble.md`.

Kernel preamble §5 applies: `references/kernel-preamble.md`.
