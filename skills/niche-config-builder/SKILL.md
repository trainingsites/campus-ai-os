---
name: niche-config-builder
description: >
  Composes atlas/config/niche.md for the Strategy and Research Team (Atlas) from the
  answers atlas-setup collected (standalone mode only). Internal skill — invoked by
  atlas-setup, not directly by the user.
version: 1.0.0
department: kernel
---

# niche-config-builder — compose atlas/config/niche.md (standalone only)

Internal. Turns the `atlas-setup` standalone interview answers into a clean `atlas/config/niche.md`.

## CRITICAL DIRECTIVES
- Tool-agnostic; zero hardcoded paths. Write only inside the plugin's config dir (`atlas/config/niche.md`).
- connected mode never calls this — that mode reads the resolved shared context instead.
- This composes ONLY the team-private `atlas/config/niche.md` (Atlas settings + lowest-precedence fallback). The canonical shared-context files (`identity/icp/brand/voice/goals/offers`) are written by `atlas-setup` and are the source of truth — never duplicate them here.

## Steps
1. Take the collected answers: niche, competitors, audience hangouts, what they create/sell, and **`sources` — where to research** (specific subreddits/communities, competitor channels, podcasts, review sites, industry pubs). Atlas always *asks* for `sources`, but if the user skips it, record `sources: []` (partial-capture honesty) — `content-scanner` falls back to the always-on set. Never block on a blank answer.
2. Map "what they create/sell" → `business_model` (courses | coaching | services | events | ecommerce).
3. Read the live capability map → fill `search_tier` and `internal_buckets` with ONLY what was detected.
4. Default `council_voices: [skeptic, customer, contrarian, numbers, brand_voice]` and `handoff_dir: ./teams-shared`.
5. Write `atlas/config/niche.md` using `../atlas-setup/references/config-template.md`. Echo the result back for confirmation; allow edits.
