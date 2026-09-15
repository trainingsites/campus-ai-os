---
name: competitor-analyzer
description: >
  Deep competitor content audit for the Strategy and Research Team (Atlas) — what
  competitors publish, what's getting engagement, what they're missing, and where the
  user can differentiate. Use for /atlas-competitor, "analyze my competitors", "what
  are competitors publishing", "find competitor gaps".
version: 1.0.0
department: dean-office
---

# competitor-analyzer — audit the field, find the gap

Deep audit of named competitors to surface differentiation opportunities. Feeds findings into `scoring-engine` like the scanner does.

## CRITICAL DIRECTIVES
- Tool-agnostic. Baseline (WebFetch/WebSearch) always works; Firecrawl multi-page crawls and Apify channel pulls light up only if present. Never assume a connector. Zero hardcoded paths.
- If a page returns an empty shell, ask for a paste or skip it — never fabricate competitor data.

## Steps
1. Get the competitor list from the resolved `icp` context (`CONTEXT_CANON` (`.campus-os/context-files.md`, else the plugin's `templates/context-files.md`): canon → alias → case-insensitive) or team-private `atlas/config/niche.md` — never hard-code `shared/icp.md`; accept ad-hoc names the user gives.
2. For each competitor, audit recent content: themes/topics, formats, cadence, and (where visible) engagement signals — comments, view counts, reactions. Premium: multi-page crawl + channel analytics.
3. **Answer-engine cross-check (if available):** ask what ChatGPT/Perplexity/Gemini surface for the niche — note where competitors own the AI answer and where it's open.
4. Identify: saturated topics (avoid), under-served angles (gap), and the differentiation wedge (what the user can own that competitors don't).
5. Hand candidate gap-topics to `scoring-engine`; write a competitor audit report to the reports dir.
6. Report the top 3 differentiation openings, each with one-line evidence. Offer: "Want a brief on any of these? (`/atlas-daily`)"
