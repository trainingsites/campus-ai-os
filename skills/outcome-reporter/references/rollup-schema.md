# reporting-rollup schema — back socket roll-up (Team Interop Spec v1)

Reporting reads every execution team's `results.json` (append-only, per-team) and aggregates — keyed by run_id so one topic's whole journey is one row. It never rewrites another team's ledger.

## results.json (what Reporting READS, emitted by each execution team)

**Canonical definition: `schemas/results.schema.json` (envelope v1.1).** This block is a reading aid; the schema file wins. Validate/classify with `tools/validate_results.py`.
```json
{ "schema_version":"1.1","profile":"completion-only|full","run_id":"minted by tools/mint_run_id.py, same id as the driving brief","slug":"","team":"<emitting team's own slug>",
  "generated_at":"ISO 8601 with zone","external_ref":null,"permission":"draft-only",
  "assets":[{"type":"","path":"","status":"draft|published|local|scheduled|sent|skipped|failed","tier":"native|browser|local","url":"","external_ref":null,"completion":{},"performance":{}}],
  "completion":{"execution_success":false,"artifact_passed":false,"owner_approved":false},
  "bindings":[{"stage":"","employee":"","employee_type":"kernel|team|playbook|hire|owner","version":"","reason":"","alternatives":[],"outcome":null}],
  "outcome":null }
```
Read side (Interop spec §6): `schema_version` `"1.0"`, missing, or the legacy `"1.1-completion-only"` are **legacy-1.0** ledgers — asset-only or completion-only — and are aggregated, never failed. Run-level `completion` is the run's self-report; asset-level `completion` never overrides it. `bindings[]` (5.2.0 R2) says who ran each stage; carry it into the roll-up so outcomes attach to the employee.

> **Completion-only emitters (Interop v1.1, spec ref S155).** Saleable teams emit on the **completion-only** line: each asset carries `external_ref` (the re-findable handle, null while draft/local) + a self-report `completion` done-check, and **omits `performance`** (the opens/clicks/views/engagement/conversions bag) because that needs the buyer's analytics/CRM connectors. **Absent `performance` from a completion-only team is honest owner-side absence, never failure** — read its `completion` signal for the "did it get produced/published" outcome, and pull live `performance` only on the owner's own install where a connector is capability-gated present (Step 4 below). A v1 reader that ignores `external_ref`/`completion` still conforms (additive).

## reporting-rollup.json (what Reporting WRITES)
```json
{ "schema_version":"1.0","period":"YYYY-Www","generated_at":"ISO 8601",
  "topics":[{ "run_id":"","slug":"","brief_score":"0-100|null","teams_touched":[],
    "assets_total":0,"assets_published":0,
    "outcomes":{"opens":0,"clicks":0,"attendance":0,"replies":0,"completion":0,"sales":0},
    "verdict":"working|mixed|flat|no-data" }],
  "recommendations":[{"signal":"do more|do less|retire","topic_or_pattern":"","evidence":"","approved":false}] }
```

## Rules
- Outcome-biased: rank sales > replies > attendance/completion > clicks > opens. Volume is not a result.
- `no-data` is honest, not failure — say "connect/report X to measure this."
- Recommendations ship `approved:false` — human gate. Strategy consumes only approved ones.
- Tolerate pre-spec ledgers (e.g. an older execution team): missing run_id → mint from slug; missing schema_version → assume "1.0".
