---
name: hr-registry
description: Build the workforce roster - one honest list of every AI employee, team, playbook, and scheduled task on this campus. Kernel HR skill. Use for 'build my registry', 'what AI do I have', 'show my workforce', 'inventory my skills', 'roster', or /hr-registry. Reads the canonical registry plus a fresh scan and reports it; it never keeps a second store and never disables, deletes, or moves anything. Read-only and flag-only. Department: dean.
department: kernel
---

# hr-registry (kernel)

**One job:** report the workforce on THIS campus by reading the canonical registry and a fresh
filesystem scan. Read-only and flag-only.

## How the kernel HR registry works

- **The canonical registry is `.campus-os/registry.json`.** hr-registry does NOT build a second
  registry store (the old `ai-hr-team/state/registry-latest.json` is retired). It reads canonical.
- **The scan is a derived, regenerable snapshot** at `.campus-os/scan/latest.json` (prior run rotated
  to `previous.json`). Overwrite freely — never append-only, never a registry.
- **The HTML roster bakes from canonical + scan combined**, written to a dated deliverables dir.

## What changed for "hire, don't install" (2026-09-03, hire-registry-phase1 item 1)

- **`.campus-os/registry.json` carries a top-level pointer key `"hires": ".campus-os/hires/"`.**
  One file per hire (multi-seat friendly) — hr-registry does not build a second store for these
  either; it reads the manifests directly.
- **Hires are reported, never counted as installed.** A hire is a contractor (fetch, read/run,
  discard — see `.campus-os/hires/README.md`), not something on the campus payroll. The roster
  shows them in their own section, separate from `installed_plugins` and `teams[]`.
- **The scan snapshot now carries a `hires[]` array + a `hires` count**, and flags any hire whose
  last security scan verdict wasn't `clear` under `cross_reference.hires_unclear` — the same
  flag-only pattern as `unregistered_installed` and `version_drift`.

## CRITICAL DIRECTIVES
- **Read-only.** Inventories only; changes nothing. Cleanup is `hr-review`'s job, owner-approved.
- **Canonical is the source of truth.** Never write team data anywhere but a human report — the only
  writable artifact is the scan snapshot + the HTML roster. Never edit `.campus-os/registry.json` here.
- **Directional tools, not permissions.** Tool tags are "what a role typically uses," not an audit.

## Run procedure

**1. Refresh the scan.** From the campus root:
```
python3 library/skills/hr-registry/scripts/scan_workforce.py --campus-root .
```
This reads `.campus-os/registry.json` (canonical) + walks the install cache(s) + `scheduled/` +
`library/skills/`, and writes `.campus-os/scan/latest.json` (rotating `previous.json`). Stdlib only,
deterministic, no network, no model call.

**2. Read both truths.** Load `.campus-os/registry.json` (registered teams + playbooks, the org
directory) and `.campus-os/scan/latest.json` (what's actually installed + cross-reference flags).

**3. registry-lint (the done-check).** Assert: `.campus-os/registry.json` is valid JSON with a
`teams[]` array; every team entry has a `team` name; `playbooks[]` (if present) entries carry
`playbook` + `stages` + `recurring`; every manifest under the `hires` pointer that has a top-level
`hire` key is counted once (no duplicates, no manifest silently dropped); the scan's `counts` are
internally consistent — `counts.hires` equals `len(hires[])`. If lint fails, re-run the scan once; if
it still fails, escalate to the owner with the raw error — never hand over a broken roster.

**4. Bake the HTML roster** from canonical + scan into
`outputs/{YYYY-MM}/reports/hr-registry/{run_id}/registry.html` — overview stat band, departments +
employees (expandable: purpose, triggers, command, tools), slash-command reference, playbooks,
scheduled tasks, and a **Hires** section (name, repo, trust tier, what it does, last scan verdict —
labeled as contractors, not staff, so a reader never mistakes a hire for an installed team). Sections
hide when empty. Honor the resolved `brand` context if present
(resolve it through `CONTEXT_CANON`, which already covers every spelling this
campus might use); neutral fallback otherwise. (For a quick text-only run, skip the HTML and summarize inline.)

**5. Summarize for the owner** (scoped to the request): headline counts (teams / playbooks / authored
kernel skills / installed plugins / scheduled / **hires**), then the teams table, then the hires list
(one line each: name, owns, trust tier, scan verdict), then anything already worth a look from the
scan's `cross_reference` (unregistered installs, registered-but-absent plugins, version drift, flagged
schedules, **hires with a non-clear scan verdict**) — but only NAME them. Fixing is `hr-review`.

**6. Emit the back socket.** Write `results.json` (interop 1.0: `schema_version`, `run_id`, `team:
hr-registry`, `generated_at`, `assets[]`) to `outputs/{YYYY-MM}/runs/hr-registry/{run_id}/`. Status
draft. HR is read-only.

## Boundaries
Read-only and flag-only. Names what's stale/duplicated/drifted; never acts. The scan engine is
deterministic standard-library Python.
