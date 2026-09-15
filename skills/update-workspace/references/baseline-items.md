# Baseline items - entry points, items 1-10, entry-file edits, manager pass

Companion to `/update-workspace` Step 0, Step 4 items 1-10 and Step 4b. This
is the v2/v3 material: most campuses skip it, every campus needs it to exist.
Nothing here writes a version literal - `OS_VERSION` is resolved from
`PLUGIN_MANIFEST` per `PLATFORM.md`, and every `{ENTRY_FILE}` that reads or
edits an existing file means the entry file THAT CAMPUS already has (any of
`CLAUDE.md` / `AGENTS.md` / `AGENTS.override.md` / `CODEX.md`, the last a
read-only legacy alias); only item 2b creates one, as `ENTRY_FILE` resolved
for THIS host.

## Entry points (Step 0, Marker < `OS_VERSION`)

Pick the earliest entry point that matches and run from there; every path
then ends with the closing rule (items 11-15 and the `OS_VERSION` stamp).

| `workspace.json` says | Run |
|---|---|
| 4.x or 3.2.x | skip items 1-10 - they already exist |
| 3.1.x | item 10a only (v3.2's additions live in the plugin; no campus files change) |
| 3.0.x | items 7-10 plus Step 4b (manager upgrade) |
| no v3 marker at all (a v2 campus) | everything |

*Why the up-to-date test is a comparison (build-gate check 12):* the branch
once read "workspace.json says 4.1.x -> you're already up to date", which was
true when written and false the moment 5.0.0 shipped. A campus stamped 4.1.4
was told it was current by every 5.0.x plugin it met and never received the
v4 or v5 additions - while reporting success on every run. Same
stale-literal class as the version markers; the gate fails the build if the
test is ever re-hardcoded.

*Why detection is permissive (SOP standing gate (a), founding-vs-migration
parity):* a campus founded from another client has a different entry
filename and is still a campus. Narrow detection would report it as an empty
folder and offer to found a new one on top of an existing business.
`/campus-start`'s guard reads all four, so founding and migration agree on
what counts as "a campus is here".

## Step 3 - safety copy

`dean/archive/pre-v3/{date}/`. Copy named files and folders explicitly (the
entry file, memory.md, TASKS.md, each shared file) - never recursively copy
`dean/` into a destination inside `dean/`, which creates a self-copy loop.

## Items 1-10

1. **`.campus-os/registry.json`** - create from `templates/registry.json`.
   Scan installed team plugins and the campus's department or manager
   folders; add an entry per team found. Anything that predates v3 or can't
   be verified is `status: legacy` - legacy teams keep working exactly as
   before; version `unknown`, triggers empty. Append-only forever after.
2. **`workspace.json`** - create at the campus root. `version` =
   `OS_VERSION`; `structure` read from the folders that actually exist
   (departments, clients, projects, or mix); business facts derived from the
   resolved `identity`, `offers` and `icp` contexts (never re-ask what the
   campus already knows). **Business schema (canonical, nested):**
   `business: {"what": "", "sells_today": "", "audience": ""}`. Normalize
   both shapes: fold old FLAT keys (`business`/`sell`/`audience`) into the
   nested object (`business`->`what`, `sell`->`sells_today`,
   `audience`->`audience`) and drop the flat keys; leave an existing nested
   object alone. Never write a prose placeholder into a business field -
   empty is `""`. **One structure, one key (parity with /campus-start):**
   write EXACTLY the filing key that matches `structure`, holding the folder
   names that exist, and omit the others - `departments: [...]`, or
   `clients: []`, or `projects: []`, or for a mix `departments: [...]` plus
   at least one of `clients: []`/`projects: []`. Never leave an empty
   `departments` key on a clients/projects campus. Folders the owner's files
   mention but that don't exist: record what exists, mention the mismatch,
   never create folders to "fix" it. Assistant name: the name the campus
   already uses; only if none is found, ask once (Dean is the default).
2b. **Root entry-file redirect - create if missing (additive).** If the
   campus root (or the connected folder's root, when the campus is a
   subfolder) has none of the four entry files pointing new sessions at
   `dean/{ENTRY_FILE}`, create the redirect as `ENTRY_FILE` resolved for this
   host (exact content in `skills/campus-start/references/scaffold.md`; assistant name from
   `workspace.json`). If any root entry file already exists with owner
   content, do NOT overwrite - only offer to prepend the redirect block. A
   campus with a different entry filename is not missing one: it was founded
   from another client, which is supported; adding a second for THIS host is
   additive and fine, replacing theirs is not. Pre-v5.0.1 installs are
   missing this file entirely; without it new sessions never load the chief
   of staff.
3. **`dean/{ENTRY_FILE}` - insert, never rebuild.** Compare against the
   kernel template's known sections. Insert ONLY the blocks that are
   missing: the three safety rules, the registry-read line in Start of
   Session, the activity-ledger habit in End of Session.

   | Rule | Marker (present = skip) | Insert where |
   |------|------------------------|--------------|
   | inputs/ write-protection | text covering "inputs/ is read-only" | inside the file-routing / "Where Files Go" section, after the inputs/ line |
   | Reversibility Rule | a "Reversibility" heading or equivalent wording | as its own section near routing rules |
   | One-Page Plan Rule | a "One-Page Plan" heading OR a "PRD-Gate" heading | as its own section after the routing/asks section |

   If an anchor is missing, append the block at the end of the file with a
   one-line HTML comment noting the anchor was missing. **PRD-Gate special
   case:** a "PRD-Gate" section IS the One-Page Plan rule - do not insert a
   duplicate. Offer (don't force) to rename the heading and swap "PRD" for
   "one-page plan" within that section only; default KEEP THEIRS. Never say
   "PRD" in owner-facing language. Existing text is never rewritten. Any
   section the template doesn't know is owner-owned: leave it verbatim. If an
   owner's section conflicts with a kernel block, show both and let them
   pick - default KEEP THEIRS. Semantic equivalence counts as present: if
   the owner's file already covers a block in their own words, under any
   heading, do NOT insert a duplicate. When in doubt, don't insert.
4. **`dean/.activity.jsonl`** - create if missing, header comments only.
5. **`shared/setup-progress.md`** - create, marking the shared files already
   filled in as complete. Include the goals row (voice -> goals -> audience
   -> offers -> tools priority order).
5a. **The goals stub** <!-- context-literal-ok: this step CREATES the file -->
   - create the three-line DEFAULT stub (one number / horizon / this week's
   focus, each a fill-in prompt) ONLY IF absent; never overwrite one the
   owner wrote. Keeps a founded and an upgraded campus at parity on the
   ladder. Named exactly because this step CREATES it: writing is exact,
   reading is permissive - the `ENTRY_FILE` rule.
6. *(v2 only)* Baseline v3 files above complete.
7. **New skill folders** ship with the plugin - nothing to copy; tell the
   owner the new commands exist: /promote-skills, /review-candidates,
   /wiki-query, /campus-map, plus the starter AI employees (/morning-brief,
   /weekly-review, /offer-builder, /build-course, and the rest).
8. **`.campus-os/registration-block-spec.md`** - MATERIALIZE it, never copy
   it (5.2.0 Phase 3.6): `python3 tools/materialize_registration_spec.py
   --campus-root {campus_root}`. Output = `templates/registration-block-spec.md`
   + the owner's `.campus-os/registration-overrides.json` (extra departments,
   owner notes) + a stamp line recording both. If the tool REFUSES because
   the existing copy is hand-edited with no stamp, run it once with
   `--capture-notes` first (it turns the owner's non-template lines into the
   overrides file - report the captured lines in Step 5), then again to
   materialize. This is the spec teams adopt on their own version bumps;
   never retrofit installed teams here.
9. **`dean/skill-candidates/`** - create with `_promoted/` and `_rejected/`
   subfolders if missing (empty is fine).
10. / 10a. Legacy 3.x version markers (`workspace.json` and the campus-ai-os
   registry entry). Superseded: the closing rule stamps `OS_VERSION` on every
   path, so these never write a literal; on a 3.1.x campus this is the
   entire 3.1 -> 3.2 migration.

## Item 11h - the playbook-routing block

Additive insert into `dean/{ENTRY_FILE}`, same insert-missing-block
discipline as item 3. The orchestrator must check `playbooks[]` before
compound work or the playbooks feature never fires on an upgraded campus.

- **Idempotent:** if `<!-- campus-os:playbook-routing -->` is present, SKIP.
- **Semantic equivalence counts:** if the file already says "check the
  playbook registry before compound work" in the owner's words, SKIP.
- **Rename-safe:** anchor to the FILE, never the orchestrator's name; insert
  at the end of the routing section, else append with a one-line HTML
  comment. The block is imperative and names no assistant.
- **Never rewrite** a line of the owner's text. **Log it** in Step 5: "Added
  1 routing rule to your orchestrator file".

```
<!-- campus-os:playbook-routing -->
### Playbooks  -  check before any compound job

Before improvising any multi-step / multi-team job (turn one thing into
many, a weekly reset, any "do X then Y then Z"), check
`.campus-os/registry.json` -> `playbooks[]`. If a registered playbook's
triggers match, RUN it: open `playbooks/{slug}/SKILL.md` and follow the
runtime in `playbooks/README.md` - don't improvise the orchestration.
Mint one run_id, run the stages in order, run each generative stage's
done-check before handoff, respect the cost cap, stop at the human gate
(draft-only floor), then write results.json + one ledger line per stage.
A stage may declare an optional `model_tier` (light|full, default full);
the policy lives in `.campus-os/model-routing.md` and the four pins
(voice, publish, money, owner-judgment) always run full.
```

## Step 4b - department manager upgrades (guided, all managers in one pass)

If the campus has folder-based department managers (a `{dept}-manager/` or
department folder with its own entry file), offer to bring them up to the
current conventions. One guided pass covers all of them, but **each manager
gets its own preview and its own explicit go** - manager entry files are
owner-owned. Additive edits only, per manager:

1. **Start of session:** "Read `.campus-os/registry.json` before any
   pipeline planning" if no equivalent exists.
2. **End of session:** the activity-ledger habit - one JSON line per
   skill/workflow to this seat's ledger per `.campus-os/ledger-paths.md`,
   same format Dean uses (`ts, session, skill, trigger, dept, outcome,
   files_touched`; `skill: "ad-hoc"` when no skill matched).
3. **run_id threading:** inherit the run_id when handed off; mint one when
   starting fresh via the kernel minter (`.campus-os/run-id-and-interop.md`);
   write results.json for deliverable runs to the run directory so
   /atlas-report sees manager work.
4. **Registration block:** append the manager's entry to
   `.campus-os/registry.json` per the registration-block spec (upgrading its
   existing `legacy` stub counts - update in place).

Same discipline as item 3: insert missing blocks only, owner text never
rewritten, semantic equivalence counts as present. Skipping a manager (or
all of them) is a valid choice - record what was skipped in the report.
