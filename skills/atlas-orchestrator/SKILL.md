---
name: atlas-orchestrator
description: >
  Front-and-back brain for the Strategy and Research Team (Atlas). Detects mode
  (connected vs standalone), builds the live capability map, mints the
  correlation run_id, and dispatches every /atlas-* request to the right skill.
  Use when the user runs any /atlas command, says "atlas status", "what tools do
  you see", or starts a strategy/research/reporting cycle.
version: 1.0.0
department: dean-office
---

# atlas-orchestrator — mode, capability map, run_id, dispatch

Atlas is the team you talk to first (Strategy brainstorm + Research → a brief) and report to last (Reporting reads what every team shipped). This skill is the dispatcher; it does no deep work itself.

## CRITICAL DIRECTIVES
- Conversational only. No forms, no dropdowns. One question at a time, echo back.
- Tool-agnostic. Use only Read/Write/Edit/Bash/WebFetch/WebSearch + whatever capability the live session reports. Never assume a named connector. Zero hardcoded paths.
- Atlas never publishes. It plans, brainstorms, researches, and learns — then hands a brief to an execution team.

## Step 1 — Detect mode
Glob for `workspace.json` at the campus root (a real bash `find` — session-loaded context does NOT count). This is the campus marker, and it is host-neutral: do not test for an entry file, whose name differs per platform (see `PLATFORM.md` → `ENTRY_FILE`), and do not assume any particular campus folder name. Exists → **founded campus** (inherit context; see `atlas-setup/references/campus-mode.md`). Absent → the campus has not been founded: tell the owner "Your workspace hasn't been set up yet. Run `/campus-start` first to hire your AI team," and stop.

**Re-detect every run (Spec §5A.8):** never run on stale config. If `atlas/config/niche.md` was written before the campus was founded — or was carried over from the retired standalone `strategy-research-team` plugin — the campus context now wins. Offer to reconcile first ("Campus context found — reconcile your saved research config with it? (recommended)"), which routes to `atlas-setup`'s import path. Campus context is the source of truth; `atlas/config/niche.md` is the lowest-precedence fallback, never the authority.

## Step 2 — Build the live capability map
Check the actual session tool list (not config): search tier (Premium if Firecrawl/Apify present, else Baseline) and which internal buckets are connected (`content-scanner/references/capability-tiers.md`). Report it plainly, e.g. "Premium search (Firecrawl); Revenue + Community connected."

## Step 3 — run_id (Team Interop Spec v1 §4)
Format `{YYYYMMDD}-{slug≤24}-{4char}` (slug = first 24 chars of the topic slug; 4char = lowercase-alphanumeric random). **Worked example: `20260530-ai-operating-system-fo-7f3a`** — no prefix, no dashed date, keep the random suffix. The FIRST skill to touch a topic mints it (Atlas usually is first); everything downstream inherits and preserves it — never re-mint. Pass it to whichever skill runs.

## Step 4 — Dispatch
| Request | Route to |
|---|---|
| `/atlas-setup`, no config | `atlas-setup` |
| `/atlas-think` (brainstorm a topic) | `strategy-council` |
| `/atlas-grill`, "grill me", "interview me on", "extract everything about", "brain-dump" | `grill-me` |
| `/atlas-scan`, `/atlas-validate` | `content-scanner` (quick/validate) |
| `/atlas-daily` | `content-scanner` (daily) → `brief-builder` |
| `/atlas-competitor` | `competitor-analyzer` |
| `/atlas-report` | `outcome-reporter` (calls `results-aggregator`) |
| `/atlas-status` | report config, tier, last scan, brief count, last report (this skill) |

## Step 5 — Handoff location (Spec §5)
Connected → `outputs/{YYYY-MM}/...`. Standalone/peer-to-peer → `./teams-shared/` (briefs/, runs/, reports/). Must work with only `./teams-shared/` present — that's the no-OS guarantee.
