# atlas/config/niche.md template (team-private settings)

Write this ONE namespaced file at `atlas/config/niche.md` — never a bare top-level `config/niche.md` (collides with other teams). It holds Atlas-only settings + is the lowest-precedence context fallback. Shared context (identity/icp/brand/voice/goals/offers) is NOT written here — it goes to the canonical files (`references/context-files.md`).

```markdown
---
mode: standalone
business_model: courses|coaching|services|events|ecommerce
search_tier: premium|baseline
internal_buckets: [revenue, customer, community, courses, content, calendar]   # only those detected live
council_voices: [skeptic, customer, contrarian, numbers, brand_voice]
sources:                         # WHERE to research — always captured for a research team
  - {specific subreddit / community}
  - {competitor channel}
  - {podcast / review site / industry pub}
handoff_dir: ./teams-shared
created: YYYY-MM-DD
---

# Niche
{one paragraph}

## Audience
{who, where they hang out}

## Competitors (top 2-3)
- {name} — {url}

## What I create / sell
{maps to output_type defaults}

## Where to research (sources)
{the sources captured at onboarding — subreddits, communities, competitor channels, podcasts, review pages, trade pubs. Drives which sources content-scanner prioritizes.}
```

Connected mode also writes `atlas/config/niche.md` for the two Atlas-specific answers (output prefs + `sources`); it does NOT duplicate the inherited shared context — that's read from the resolved location.
