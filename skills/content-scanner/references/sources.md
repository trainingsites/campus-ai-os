# Research sources — always-on + capability-gated

## Always on (no config, baseline tier)
Google SERP (WebSearch) · Reddit (keyword) · YouTube (search) · Quora / People-Also-Ask · competitor sites (top 3, WebFetch) · YouTube comment mining (top ~50 on competitor videos) · 1–3★ review mining (Udemy/Coursera/Amazon/Google Business).

## Premium auto-detected (Firecrawl/Apify present)
Deep Reddit crawls (Apify actor) · YouTube channel analytics (Apify) · multi-page competitor crawls (Firecrawl).

## NEW capability-gated sources (light up ONLY if the tool/data is present in the live session — never assume, never prompt to install)
| Source | Why | Tier (default → premium) |
|---|---|---|
| Sales & support mining (TOP priority) | first-party pain data — your own calls/tickets/DMs | inbox + CRM → Fireflies/Gong transcripts |
| Voice-of-customer (primary) | ask the list directly via poll/survey | manual poll → Typeform/Pollfish |
| Trend & seasonality | timing — rising vs dying | Google Trends (free) → Exploding Topics/Glimpse |
| Social listening (real) | conversation volume, not just search | hashtag scans → Brandwatch/Sprout |
| SEO keyword + volume | demand numbers (volume/difficulty) | — → Ahrefs/Semrush |
| Answer-engine monitoring (AEO) | what ChatGPT/Perplexity/Gemini say about the niche | manual prompts → Profound/Peec |

Source WEIGHTS shift by `business_model` (courses/coaching/services/events/ecommerce) — see capability-tiers.md.
