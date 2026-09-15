# The campus scaffold - files, exact contents, keys, and why they are resolved

Companion to `/campus-start` Step 2 and the resolution rules at the top of
the skill. Founding must produce the same campus that `/update-workspace`
produces (SOP standing gate (a)); build-gate check 8 compares the two skills
file by file and folder by folder.

## Resolution rules - and their history

- **`PLUGIN_MANIFEST` and `ENTRY_FILE`** come from `PLATFORM.md`. The
  manifest directory and the entry filename differ by host (the entry file
  is `CLAUDE.md` on Claude and `AGENTS.md` on Codex, per that file). v5.0.3
  fixed a version literal and replaced it with a manifest-directory literal -
  same class - which `PLUGIN_MANIFEST` closed. Build-gate check 7 fails the
  build on either literal in logic.
- **`OS_VERSION`** = `PLUGIN_MANIFEST` -> `version`. v5.0.2 shipped with
  `5.0.0` hardcoded in four places here and two in update-workspace; a fresh
  install stamped itself 5.0.0 and told the owner so, and update-workspace
  reasons about this marker to choose a migration path. Build-gate check 6b
  fails the build if this skill stops resolving it.
- **`DEPT_LABELS`** = `templates/registry.json` -> the `type: department`
  entries -> each entry's `label` field, in order, skipping `dean-office`
  (the chief of staff's bench is not a department the owner files work
  under). The registry template already holds the label with the pack's
  override applied, so this is one read of one owner. History: until v5.1.5
  the filing question hardcoded four department names while the pack
  declared five, so `departments/lead-generation/` was never created and the
  founding contradicted the org chart - with nothing failing, because a
  missing `dept_dir` is only a lint warning. v5.1.5 derived the list from
  the pack, which made this skill a SECOND label resolver: the founding
  rendered the pack's names ("Media Desk", "Teaching Desk") while
  campus-doctor rendered the generator's ("Marketing", "Education") - two
  vocabularies for the same departments shown to the same owner minutes
  apart. v5.1.6 gave the label one owner. Build-gate check 22 fails the
  build on a typed department list; check 24 fails it if this skill reads
  the pack's display name instead of the registry label.

## The tree

```
{ENTRY_FILE}     workspace ROOT - the session entry point (redirect; exact content below)
dean/            {ENTRY_FILE} (from templates/dean-CLAUDE.md, assistant name applied),
                 memory.md, TASKS.md, .activity.jsonl (header comments)
shared/          business.md (answers 1-3, verbatim where possible), voice.md (DEFAULT),
                 goals.md (DEFAULT 3-line stub), offers.md (seeded from Q2),
                 audience.md (seeded from Q3), tools.md (DEFAULT), setup-progress.md
.campus-os/      registry.json (from templates/registry.json),
                 model-routing.md (from templates/model-routing.md),
                 registration-block-spec.md (MATERIALIZED from
                 templates/registration-block-spec.md by
                 `tools/materialize_registration_spec.py --campus-root {root}` -
                 template + `.campus-os/registration-overrides.json` (none at founding)
                 + a stamp line; never a bare copy, never a pointer - the Foundry,
                 validate_registry and the doctor read this file),
                 context-files.md, ledger-paths.md, run-id-and-interop.md (from
                 templates/ - the shared-context, activity-ledger and run-id canons;
                 every installed team resolves through the CAMPUS copy, so a kernel
                 fix reaches them all without repackaging; update-workspace refreshes
                 the same three),
                 scan/ (empty; hr-registry fills it on first run)
atlas/config/    (empty; the strategy and research team's private config lands
                 here as niche.md on first /atlas-setup)
active-work/  inputs/  outputs/  wiki/  daily/
```

- Create every listed folder even when empty. `wiki/` gets a one-line
  `index.md` stub: "# Wiki - knowledge that compounds. Nothing here yet."
- `dean/.activity.jsonl` starts with exactly these two header lines, then
  the founding itself as the first JSON entry (skill: campus-start,
  outcome: completed):
  `# Campus activity ledger - one JSON line per completed workflow. Append-only.`
  `# On read: skip lines starting with #. Never overwrite or rewrite prior lines.`
- A department charter stub is three lines: a heading, "Owns:" with one
  sentence, and "Status: no team hired yet."
- `.campus-os/registry.json` (copied from the template) already carries the
  staff org - the `type: department` entries with their rosters plus a
  `campus-systems` entry - so the doctor and campus-map derive the staff line
  from the registry in EVERY filing mode. Do not hand-build these. (The
  education pack default reads "23 employees + 20 campus systems + 2
  playbooks"; the counts are always derived, never asserted.)
- The goals file is a three-line DEFAULT stub, not an interview at founding:
  the one number, the horizon, this week's focus, each a fill-in prompt. The
  full goals conversation happens on the setup ladder or in full onboarding.

## The root entry file - exact content

The host reads the entry file at the root of the connected folder; without
it a new session never finds the chief of staff. Its filename is
`ENTRY_FILE` as resolved - write the resolved name, never the literal. Keep
it small: Codex caps its auto-loaded instruction chain at 32 KiB by default
(`project_doc_max_bytes`) and silently truncates past it. The root file is a
redirect, not a brain - the brain lives in `dean/`. Write exactly this,
substituting the chosen assistant name and the resolved `{ENTRY_FILE}`:

```
# ⚡ MANDATORY — Read This First

You are **{assistant_name}**, chief of staff for this campus.

Do not greet. Do not ask questions. Do not wait.

**Do this right now:**

1. Read `dean/{ENTRY_FILE}` — this defines who you are and how you operate
2. Complete its "Start of Session" steps before doing anything else

You are {assistant_name} from the moment this file is read. Every session. No exceptions.
```

After scaffolding, VERIFY the file exists at the campus root (same rule as
`workspace.json`). If the campus root is a subfolder of the connected
folder, the redirect goes at the connected folder's root and points to the
correct relative path. If the owner later runs a second client against this
campus, that client gets its own entry file (`templates/clients/`); both are
valid at once and the doctor accepts any of them. `/campus-doctor` and
`/update-workspace` use this block, verbatim, when they repair a missing
redirect.

## Structure-specific folders

- **Departments:** one folder per entry in the pack's `departments[]`, each
  with a charter stub. The path is the department's `managers[].dept_dir`
  where a manager declares one (a LITERAL declared path, never built as
  `departments/{id}/` - the Manager Layer naming rule) and `departments/{id}/`
  otherwise. Never type a department list. Confirm the set in one line
  ("Starting departments: {DEPT_LABELS} - rename or change any?"). A
  department with no staff yet still gets its folder: the org chart is the
  diagnosis, and an empty department tells the owner what to hire next.
- **Clients:** `clients/` with a `_template/` client folder (brief.md,
  notes.md, deliverables pointer); client work files under `clients/{name}/`.
- **Projects:** `projects/` with a `_template/` project folder.
- **Mix:** departments PLUS `clients/` or `projects/` as named.

## `workspace.json` - keys and rules

- `assistant_name` - the chief-of-staff name.
- `business` - an OBJECT with three string fields, the canonical schema the
  doctor, first-win and update-workspace read: `{"what": "",
  "sells_today": "", "audience": ""}`. Path B fills them from Q1-3. Path A
  writes all three as `""`; full-onboarding fills them when its business /
  offers / audience phases complete (the write-back seam). NEVER write a
  prose placeholder into these fields - empty is `""` or the key absent. A
  machine-read field never holds prose; completeness is tracked only in
  `shared/setup-progress.md`.
- `structure` - the filing choice (`departments` | `clients` | `projects` |
  `mix`) plus EXACTLY the matching filing key holding the folder names that
  exist, the others OMITTED: `departments` -> `"departments": [...]` (the
  pack's ids, or the renamed set); `clients` -> `"clients": []`; `projects`
  -> `"projects": []`; `mix` -> ALWAYS `"departments": [...]` PLUS at least
  one of `"clients": []` / `"projects": []` for the dimension the owner
  actually runs. A mix that writes only `departments` is invalid. Never leave
  an empty `departments` key on a clients/projects campus. Keep the key in
  sync as folders are added or renamed; empty arrays are correct at founding.
  `structure` is the FILING dimension only - the pack's departments always
  exist as the staff org in the registry, whatever the filing choice.
- `version` - `OS_VERSION`, resolved at runtime. Never blank, never a
  literal. On a re-run, never regress a marker already equal to or higher
  than `OS_VERSION`.
- `created` - the date.

## Parity and idempotency with `/update-workspace`

- `.campus-os/model-routing.md` - copied from the template so a fresh campus
  has the routing policy (four pins, including the non-removable publish
  pin) from day one - **only if absent**; never overwrite an owner-edited
  routing file on a re-run.
- `.campus-os/scan/` - create the empty folder.
- The three canons and `atlas/config/` are created here and refreshed or
  created by update-workspace item 12 - build-gate checks 8 and 8b enforce
  that anything one path creates, the other does too.
- In the founding close, state both plainly: "Routing policy created (Lite
  mode ready to switch on)" and "Your campus is on v{OS_VERSION}" - resolved,
  never a hardcoded version.
