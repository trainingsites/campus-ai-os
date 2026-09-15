---
name: content-scanner
description: >
  Core research engine for the Strategy and Research Team (Atlas). Scans the niche
  across always-on and capability-gated sources, extracts demand/gap/timing signals,
  and surfaces scored opportunities. Use for /atlas-scan (quick), /atlas-daily (full),
  and /atlas-validate (test one topic). Runs at whatever tier the live session allows.
version: 1.0.0
department: dean-office
---

# content-scanner — find the evidence

Discovers and signal-extracts content/strategy opportunities. Hands ranked findings to `scoring-engine`, then `brief-builder`.

## CRITICAL DIRECTIVES
- Tool-agnostic. Baseline tier (WebSearch + WebFetch) always works; premium and internal sources light up ONLY if detected live. Never assume a connector; never prompt to install one.
- Zero hardcoded paths. If a fetch returns an empty shell, ask for a paste — never fabricate findings.
- Respect a research mandate if one exists (`strategy-council` may have written `mandate.json` with `hunt_for`/`avoid`).

## Step 1 — Mode & inputs
- `/atlas-scan` (quick): top 3 opportunities, ~2 min. `/atlas-daily` (full): top opportunities + full signal detail. `/atlas-validate [topic]`: test one specific topic.
- Read niche/business_model/competitors from the resolved context (`CONTEXT_CANON` (`.campus-os/context-files.md`, else the plugin's `templates/context-files.md`): `icp`, `offers`) or team-private `atlas/config/niche.md` — never hard-code `shared/*`. Load any `mandate.json`.

## Step 2 — Pull sources (see `references/sources.md`)
Always on: Google SERP, Reddit, YouTube, Quora/PAA, top-3 competitor sites, YouTube comment mining, 1–3★ review mining. Premium (if present): deep Reddit/YouTube via Apify, multi-page crawls via Firecrawl. NEW capability-gated (only if the tool/data is live): sales & support mining (top signal), voice-of-customer polls, trend/seasonality, social listening, SEO volume, answer-engine (AEO) monitoring. **Prioritize the user's configured `sources` (where to research) from `atlas/config/niche.md`** — include and weight those first, then fill with the always-on set. Weight by `business_model`.

## Step 3 — Extract signals
For each candidate topic capture evidence for the four signals: **demand** (who's asking, volume), **gap** (saturation/what's missing), **timing** (rising/seasonal), **fit** (matches audience + offers). Note which internal buckets apply (`references/capability-tiers.md`) for the 1.5× multiplier. Check the already-covered guard (`published-content.md` / Content bucket).

## Step 4 — Hand off
Pass candidates + evidence to `scoring-engine`. For `/atlas-daily`, continue to `brief-builder` for the top picks. For `/atlas-validate`, return one topic's signal read + a go / refine / skip call.

## Step 5 — Report
Write a scan report to the handoff location's reports dir. List ranked opportunities with one-line evidence each. Offer: "Want briefs built for the top picks? (`/atlas-daily`)"
