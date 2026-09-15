---
name: outcome-reporter
description: >
  The Reporting back door of the Strategy and Research Team (Atlas) — tells the user
  what every execution team actually shipped and what worked, and proposes
  human-approved "do more / do less / retire" recommendations that feed the next
  strategy cycle. Use for /atlas-report, "what worked", "how did our content perform".
version: 1.0.0
department: dean-office
---

# outcome-reporter — what worked (the moat)

Turns aggregated ledgers into a human read-back and a roll-up. This is the compounding business-memory layer — the only part of the system that remembers across cycles, so the next brief is smarter, not cold.

## CRITICAL DIRECTIVES
- Conversational, plain-English read-back. Zero hardcoded paths, tool-agnostic.
- **Outcome-biased, not volume.** Rank by results that matter: sales > replies > attendance/completion > clicks > opens. "We made 12 things" is not a result.
- **Human-gated.** Emit recommendations as proposals (`approved: false`). Never auto-rewrite strategy.

## Step 1 — Aggregate
Call `results-aggregator` to get topics grouped by `run_id` with assets + outcomes.

## Step 2 — Verdict each topic
Assign `working | mixed | flat | no-data` from the outcomes (outcome-weighted). `no-data` is honest, not failure — when performance was never reported, say so and name what to connect/report to measure it next time.

## Step 3 — Recommendations
Propose `do more | do less | retire` signals tied to evidence (e.g. "retire — 3 assets, flat across all teams"; "do more — cohort topics drove every reply this month"). Each ships `approved: false` for the human to confirm. Approved recs are what `strategy-council` consumes next cycle.

## Step 4 — Write + report
Write `reporting-rollup.json` + `.md` to the reports dir (`references/rollup-schema.md`). Read back the headline plainly: what shipped, what performed, the top 1–3 recommendations. Offer: "Approve any of these and I'll feed them into your next `/atlas-think`."
