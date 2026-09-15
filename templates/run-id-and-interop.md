# run_id + Interop contract — canonical (Campus AI OS 5.2.0, Phase 3.5)

**This file is the ONE owner of the run-id and back-socket rules every team follows.**
Teams no longer carry their own copy of these rules. Each team's `references/run-id-and-interop.md`
is a ≤5-line *delta* (its run directory, slug rule, legacy id shape, and a pointer to anything
genuinely team-specific) that names this file.

Same ownership pattern as `context-files.md`, `ledger-paths.md` and `registration-block-spec.md`:
the kernel owns the template (`templates/run-id-and-interop.md`), the campus holds the copy
(`.campus-os/run-id-and-interop.md`, written at founding by campus-start and refreshed by
update-workspace), every team reads the campus copy — so a fix here reaches every installed team
without any of them repackaging.

## How to find THIS file
1. `.campus-os/run-id-and-interop.md` on the campus (always present on a founded or upgraded campus).
2. Else `templates/run-id-and-interop.md` inside the installed Campus AI OS plugin.
A team never bundles a third copy. If neither exists the campus is not installed: stop with the
no-campus line ("This team runs on Campus AI OS — it's free. Install it first, then run me again.").

## 1. run_id — minted once, inherited everywhere
- **Mint** with the campus minter: `python3 {kernel}/tools/mint_run_id.py mint <slug> --team <team> --campus-root .`
  (the Foundry's `mint-run-id` is a thin adapter over the same module). Canonical shape:
  `{slug}-{YYYYMMDD-HHMMSSfff}` (UTC, millisecond), plus `-xxxx` only on a same-millisecond collision.
  The model never invents a run_id.
- **Inherit** a `run_id` that arrives on a fed `brief.json` or a playbook-stage input **unchanged**.
  Never re-mint an inherited id. One run_id per run, stamped on every output and on the ledger line.
- **Read permissively.** Older ids (`{team}-{YYYYMMDD-HHMMSS}`, `{YYYYMMDD}-{slug<=24}-{4char}`,
  `…T…Z` stamps) parse via `tools/mint_run_id.py parse` and are never rejected on read. New writes
  use the canonical shape only.

## 2. Run directory — one path builder
`outputs/{YYYY-MM}/runs/{team}/{slug}/{run_id}/` on a campus (playbooks: `runs/playbooks/{slug}/{run_id}/`).
`{slug}` is a short kebab-case name for the run's subject; the team's delta says what the subject is.
The minter creates the directory; drafts, `MANIFEST.json` and `results.json` land in **that** directory.
The registry `results` field (`…/runs/{team}/{slug}/results.json`) names the *prefix*; the run_id level
below it is canonical (Phase 3.5 decision; the aggregator scans `runs/**/results.json`, so both levels read).
Ask `tools/mint_run_id.py path --team T --slug S [--run-id R]` rather than formatting the path yourself.

## 3. results.json — the back socket, envelope v1.1
Canonical definition: `schemas/results.schema.json` in the kernel (byte-identical copy in the Foundry).
Validate or classify with `tools/validate_results.py`. Write shape, every run:

| Field | Value |
|---|---|
| `schema_version` | `"1.1"` |
| `profile` | `"completion-only"` for saleable teams; `"full"` only for owner-side emitters |
| `run_id` / `team` / `slug` | the run's id, the emitting team's registry id, the slug |
| `generated_at` | ISO 8601 with zone (UTC `Z`) |
| `assets[]` | one entry per artifact: `type`, `path`, `status`, `tier`, `url`, `external_ref`, `completion` (optional `performance`, `attribution`) — may be empty |
| `completion` | run-level self-report: `execution_success`, `artifact_passed`, `owner_approved` — three booleans, never inferred from assets |
| `bindings[]` | optional in 5.2.0: `stage`, `employee`, `employee_type`, `version`, `reason`, `alternatives[]`, `outcome` |
| `external_ref`, `permission`, `outcome` | optional, opaque to the envelope |

Append-only and per-team: a team writes its **own** `results.json` in its **own** run directory and never
rewrites another team's ledger. Reporting aggregates; it does not require teams to share a file.

## 4. Completion-only — the honest draft state (saleable teams)
The floor is **draft-first**. On a buyer install every asset is `status: "draft"`, `tier: "local"`,
`url: null`, `external_ref: null`, `attribution: {}`, and `performance` is **absent**. Absent ≠ failure.
Never invent an `external_ref` for a draft — a thing the owner has not published has no stable handle,
and a fabricated one poisons the join key outcome backfill depends on.
- `execution_success` = the run finished. `artifact_passed` = every asset passed its own done-check.
  `owner_approved` = the owner said yes (or a standing grant the owner wrote covered it). Producing a
  draft is success; it is not approval; the two are never collapsed.
- Connector-pulled `performance` and CTA→purchase `attribution` are **owner-side only** — they need the
  buyer's analytics / CRM / payment stack and are never wired into a saleable team.
- Where a team may publish under a grant the owner wrote (per platform, per verb, in that team's config),
  the published asset records `status: "published"` plus the platform's real `external_ref`, and names
  the grant. A bundle ships zero grants.

## 5. MANIFEST.json — run state (resumability)
One per run, in the run directory: `started`, `last_updated`, `status`, `current_step`,
`completed_steps[]` (objects: `skill`, `step_no`, `started`, `ended`, `outcome`), `failed_steps[]`,
`done_checks[]`, `checkpoints[]` (human gates), `config_snapshot`. Internal run state, never a socket.

## 6. Sockets
**Front:** accept owner `raw-input` or a fed `brief.json` / playbook-stage input carrying a `run_id`
(inherit it); never hard-require another team. **Back:** emit `results.json` for `results-aggregator`,
`/atlas-report` and the campus morning brief.

## 7. Ledger-lint — terminal assertion before a run is "done"
1. `run_id` identical everywhere it appears (MANIFEST, every asset, the ledger line).
2. Every asset carries `status` + `tier`; every produced asset has a done-check result.
3. No asset is `published`, `sent` or `scheduled` unless a named owner grant authorized it —
   otherwise the draft-first floor was breached.
4. No orphan artifact on disk missing from `assets[]`.
5. `results.json` classifies `v1.1-valid` (`tools/validate_results.py FILE`).
In draft state `external_ref: null` and `attribution: {}` are correct and are never flagged.

## 8. CTA attribution — a contract, never a vendor literal
Assets that carry a CTA link may carry `attribution: { method, token }` with `token = run_id` and
`method` an opaque, install-resolved adapter string — **only** when the owner has wired a live
attribution surface. No `utm_`, coupon, analytics or vendor name in any skill body. No surface (the
saleable default) → `attribution: {}` and honest absence.

*Source of truth for these rules: this file (kernel-owned). Read contract for pre-v1.1 ledgers:
`wiki/concepts/team-interop-spec-v1.md` (Interop v1 §3–§5, kept as history).*
