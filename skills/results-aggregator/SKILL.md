---
name: results-aggregator
description: >
  Reads every execution team's results.json ledger (the BACK SOCKET) for the Strategy
  and Research Team (Atlas) and aggregates them by run_id into a roll-up. Internal
  skill, invoked by outcome-reporter. Tolerates pre-spec ledgers.
version: 1.0.0
department: kernel
---

# results-aggregator — read the back socket

Internal. Scans the handoff location for every team's `results.json`, parses them, and groups by `run_id` so one topic's whole journey across teams is one row. It NEVER rewrites another team's ledger — append-only, per-team (Team Interop Spec v1 §3).

## CRITICAL DIRECTIVES
- Tool-agnostic; zero hardcoded paths. Read-only over the ledgers.
- Tolerate pre-spec ledgers: missing `run_id` → mint from slug; missing `schema_version` → assume "1.0". Never fail on an older shape.
- The envelope is ONE file: `schemas/results.schema.json` (v1.1 = `assets[]` + run-level `completion` + optional `bindings[]`). Classify, don't guess: `python3 tools/validate_results.py --campus-root . --json` returns each ledger as `v1.1-valid` / `v1.1-invalid` / `legacy-1.0` / `ledger` / `foreign` / `malformed`. Aggregate `v1.1-*` and `legacy-1.0`; skip `ledger`/`foreign` (job logs, not envelopes); report `malformed` and `v1.1-invalid` counts in one line, never silently.

## Steps
1. Resolve the handoff location: Connected → `outputs/{YYYY-MM}/runs/**/results.json`; standalone/peer → `./teams-shared/runs/**/results.json`. Read both if both exist.
2. Parse each ledger: `run_id`, `team`, `slug`, `assets[]` (type, status, tier, url, optional `performance`), run-level `completion` (three booleans; absent on asset-only 1.0 ledgers — derive nothing, report "no completion"), and `bindings[]` when present (who ran each stage — carry `employee`/`employee_type` into the roll-up so outcomes attach to the employee that produced them).
3. Group by `run_id`. For each topic: list `teams_touched`, count `assets_total` / `assets_published`, and roll up any reported `outcomes` (opens, clicks, attendance, replies, completion, sales).
4. Pull live performance where a connector is present and capability-gated (sales_stats, list_campaigns, course_analytics…); otherwise leave outcomes at user-reported or zero and flag `no-data`.
5. Cross-reference brief score if the matching `brief.json` is on disk (adds `brief_score`).
6. Hand the grouped structure to `outcome-reporter` to verdict and write the roll-up.
