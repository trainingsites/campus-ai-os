# Team Registration Block — Spec v1.0 (Campus AI OS 3.1)

How a team plugin declares itself to the campus so Dean can route to it, campus-doctor can validate it, and Atlas can read its results. Teams adopt this on their own version bumps — **never forced**.

## Where it lives

One entry appended to `.campus-os/registry.json` -> `teams[]`, written by the team's onboarding skill on first run. The file is **append-only**: add your entry, never rewrite or delete anyone else's. Dedupe by `team` name — if your entry exists, update only your own entry's `version`, `triggers`, and `done_check`.

## Required fields

```json
{
  "team": "kebab-case-team-name",
  "version": "1.2.0",
  "type": "plugin | authored-skill | kernel | department | systems",
  "status": "active | legacy | disabled | retired",
  "department": "marketing | sales | education | community | lead-generation | operations | finance | people | dean-office | kernel | core | cross",
  "owns": "One plain-English line: what this team does.",
  "triggers": ["/command", "natural phrase 1", "natural phrase 2"],
  "done_check": "How the team knows a run is complete (e.g. 'voice-check >= 85', 'results.json emitted', 'owner approved draft').",
  "results": "outputs/{YYYY-MM}/runs/{team}/{slug}/results.json",
  "permission": "draft-only"
}
```

## Field rules

- **team** — must match the plugin's `plugin.json` name.
- **version** — semver, matches the installed plugin version. Update on every bump.
- **department** — the ONE home for "which department does this team belong to." Pick a value from the enum above; **do not also add the team's name to that department's roster in `.campus-os/registry.json`.** The roster is derived from this field at read time (see *Department vocabulary* below). One fact, one home — a team that is written into both drifts out of one of them, which is exactly how `seo-team` came to carry `department: marketing` while missing from Marketing's stored roster.
- **triggers** — at least one; these are what Dean routes on.
- **done_check** — required; a team without one is a weak playbook (hr-review flags it).
- **results** — the canonical run-dir pattern the team writes `results.json` to (interop spec: `schema_version: "1.0"`, `run_id`, `slug`, `team`, `generated_at`, `assets[]`). Standalone installs use `./teams-shared/runs/{team}/{slug}/`.
- **permission** — `draft-only` is the default and floor. Only the owner grants publish authority, by editing this field, explicitly.
- **type** — required since 5.2.0 (was optional). `plugin` for an installed team plugin, `authored-skill` for a skill the campus wrote itself, `kernel` for the three meta records, `department` and `systems` for the org-chart groups `gen_department_entries.py` writes. The enum line in the block above is the ONE home; `tools/validate_registry.py` reads it from there.
- **status** — required since 5.2.0 (was optional). `active` unless the team is `legacy` (pre-v3, exempt from format checks), `disabled` (installed, switched off) or `retired` (gone; keep `retired_on`). Every registry reader that counts or reports consults this field.

Optional: `when` (cadence hints).

> **`type` and `status` became required in 5.2.0 (Phase 2.4).** On the reference campus 23 of 71
> entries had no `type` and 18 had no `status`, so every reader that counted had to guess. The
> doctor and the packager now refuse the guess: `validate_registry.py` fails an entry that lacks
> either, or carries a value outside the enum. Backfill is a one-time stamp, not a migration.

> **`retired` added v5.1.1 — the enum had two definitions.** This spec documented
> `active | legacy | disabled`; `hr-review`'s `diff_scan.py` has always honored
> `retired | legacy | disabled`; and the remediation string it prints recommends
> `retired`. The code and the advice already agreed — only the spec was behind,
> so `retired` is now documented rather than removed. `disabled` was the sole
> value valid in all three. All four are treated identically: an entry carrying
> any of `legacy | disabled | retired` is exempt from format validation and from
> the registered-but-absent flag (it is recorded as intentionally retired
> instead — the fact is kept, the chore is not).

## Department vocabulary (v5.1.4)

Twelve values, three kinds (plus any the owner adds through `.campus-os/registration-overrides.json` — the campus copy of this file is materialized from this template plus those overrides by `tools/materialize_registration_spec.py`, never hand-copied). **Writing is exact; reading is permissive** — the same rule the shared-context canon runs on.

| Value | Kind | Counted as staff? |
|---|---|---|
| `marketing` `sales` `education` `community` `lead-generation` `operations` `finance` `people` | **department** — a sellable department with a manager | yes |
| `dean-office` | **department** — the chief of staff's own bench; free, never sold | yes |
| `kernel` | platform machinery (the campus running itself) | no — reported as "campus systems" |
| `core` `cross` | serves no single department | no |

- **`operations`, `finance`, `people` are new in v5.1.8** — the same pattern as `lead-generation`: empty starter rosters, staffed by teams the owner installs. Added because three of the ten evaluator categories had no id, so Operations/Finance/People teams were piling into `dean-office` — and a team shipping one of the new ids on a pre-5.1.8 campus was silently dropped from the org chart (found on the first cold install, 2026-08-31).
- **`lead-generation` is new in v5.1.4.** It ships with an empty starter roster on purpose: the department exists on the org chart so the diagnosis is honest, and it is staffed by a team the owner installs. *Never sell a department you cannot staff — but still show the unstaffed ones.*
- **`dean` is a LEGACY ALIAS for `dean-office`. Accepted on read, never written.** The org chart has always counted `dean-office`; this spec used to offer `dean`, so an entry filed exactly as the spec instructed was counted by neither reader. Every reader now resolves `dean` → `dean-office` before counting. New entries must be written `dean-office`.
- The three `type: kernel` meta records (`dean`, `campus-ai-os`, `atlas`) keep `department: dean` and are excluded from both counts by their **type**, not by their department. Internal ids are never renamed.

**The roster is derived, never stored twice.** A department's staff is every active entry whose `department` resolves to it, unioned with the kernel-derived `employees[]` list. `employees_added[]` survives only for names that have no registry entry of their own. Build-gate check 20 fails the build if any active entry carries a department no reader can resolve.

## Validation — who checks what

- **campus-doctor** validates presence + format: entry exists for each installed team plugin, required fields present, `permission` set. Reported as "N teams registered / M off-spec". Doctor counts **installed plugins only** — never library archive files (.zip/.plugin) — so shelf copies don't create false positives.
- **hr-review** judges quality and staleness (weak done-checks, stale triggers). No format checks there — no duplication.

## Legacy teams

Entries with `status: "legacy"` (pre-v3 teams recorded during upgrade) are exempt from format validation. They keep working exactly as before and adopt this spec whenever they next bump.
