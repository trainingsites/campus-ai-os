---
name: scoring-engine
description: >
  Scores and ranks research opportunities 0-100 for the Strategy and Research Team
  (Atlas) across four signals — demand, gap, timing, fit — plus an internal-data
  multiplier. Internal skill, invoked by content-scanner and competitor-analyzer.
version: 1.0.0
department: kernel
---

# scoring-engine — score 0–100, rank

Internal. Turns the scanner's signal evidence into a defensible 0–100 score so the best opportunities rise.

## CRITICAL DIRECTIVES
- Tool-agnostic; no external calls of its own — it scores what the scanner gathered. Zero hardcoded paths.
- Be honest about thin evidence: a signal with no data scores low, not blank-high.

## Scoring model
| Signal | Max | Reads |
|---|---|---|
| Demand | 40 | how many are asking, search/comment/review volume, recency |
| Gap | 30 | saturation — is this answered well already, or missing? |
| Timing | 20 | rising vs flat vs dying; seasonal/news hook |
| Fit | 10 | matches audience + an offer/goal |
| **Multiplier** | ×1.0–1.5 | +0.5 split across connected internal buckets whose data corroborates the topic (`../content-scanner/references/capability-tiers.md`) |

`score = (demand + gap + timing + fit) × multiplier`, capped at 100.

## Output
For each topic: the 0–100 score, a one-line `label`, and the `signal_breakdown` (n/40, n/30, n/20, n/10, multiplier + note) — exactly the shape `brief-builder` writes into the brief's scoring block. Rank descending. In standalone-with-no-scan situations the breakdown stays null (there was nothing to score against).
