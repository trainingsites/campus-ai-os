---
name: atlas-setup
description: >
  Conversational onboarding for the Strategy and Research Team (Atlas). Auto-detects
  a host campus and inherits niche/audience/connections (one question only), or runs a
  short standalone interview. Use on first run, when the user says "set up atlas",
  "/atlas-setup", or asks to reconfigure niche, sources, or council voices.
version: 1.0.1
department: dean-office
---

# atlas-setup — two-mode onboarding

## CRITICAL DIRECTIVES
- Conversational only. **No forms, no dropdowns, no pre-filled menus.** Ask one question at a time and echo the answer back before moving on.
- Tool-agnostic. Auto-detect tools from the live session; never ask the user what tools they have, and never tell them to install one. Zero hardcoded paths.
- Never re-ask anything the host campus onboarding already captured.
- **Resolve shared-context filenames through `references/context-files.md` (canon → alias → case-insensitive) — never hard-code `shared/icp.md` etc.**
- **Capture the full identity set** (audience, voice, brand, goals, offers) AND, because Atlas is a research team, **always ask where to research** (sources/communities to prioritize). **Write canonical context files, not a self-contained config.** Team-private settings go in the ONE namespaced file `atlas/config/niche.md` (never a bare `config/niche.md`) — the lowest-precedence fallback, NOT the source of truth.

## Step 1 — Detect mode
Glob for `workspace.json` at the campus root. That is the campus marker, and it is host-neutral — do NOT test for an entry file, whose name differs per platform (`PLATFORM.md` → `ENTRY_FILE`), and do NOT assume any particular campus folder name.

## Step 2A — founded campus (`workspace.json` exists) — the normal path
Follow `references/campus-mode.md`. **Resolve and inherit** context via `references/context-files.md` (canon → alias → case-insensitive): audience from `icp`, business model from `offers`, connections from `connections`, goals from `goals`, brand from `brand`, voice from `voice`. Never hard-code `shared/icp.md` etc. **Inherit what exists; capture only what's missing.** Build the live capability map. Then ask the **two Atlas-specific questions a general campus onboarding won't have captured**, one at a time: (1) "What do you mostly create — videos, blog posts, webinars/classes, social, workshops, or offers?" and (2) "Where should I research — any specific sources/communities to prioritize (subreddits, competitor channels, podcasts, review sites, industry pubs)?" Save both to the team-private `atlas/config/niche.md` (output prefs + `sources`). Show a confirmation summary; allow edits. Do NOT duplicate the inherited shared context — you read it from the resolved location.

## Step 2B — campus not founded (no `workspace.json`)
**Do not run the standalone interview.** Since v5.1 this skill ships inside the kernel, so founding is `/campus-start`'s job and asking these questions here would interview the owner twice for the same facts. Say: *"Your workspace hasn't been set up yet. Run `/campus-start` first to hire your AI team — then I'll pick up the two research questions I still need."* Then stop.

<details>
<summary>Retired standalone interview — kept for reference, do not run</summary>

Auto-detect tools → report tier ("I can see Firecrawl and a CRM — Premium search, Customer data connected"). **First check `./teams-shared/context/` — if canonical files already exist (a peer team set them up), import them and only fill gaps (Spec §5A.5), don't re-ask.** One paragraph welcome, wait for "yes". Then ask, one at a time, echoing each:
1. What's your niche / who do you serve? (→ `icp`)
2. Top 2–3 competitors?
3. Where does your audience hang out?
4. What do you mostly create or sell? (→ `business_model` + `offers`)
5. Brand basics — main colors, fonts, visual style? (→ `brand`; ask because branded outputs use them)
6. Your top goal(s) right now? (→ `goals`; the council uses these)
7. **Where should I research?** Any specific places to prioritize or include — subreddits/communities, competitor channels, podcasts, review sites, industry publications? (→ `sources` in `atlas/config/niche.md`. **Always ask — this is core for a research team.** Auto-detected tools set the *tier*; this sets *where to look*.)
Also capture voice/tone from how they answer (→ `voice`).
Optional: any specific sources to add (subreddits, podcasts, review pages)?

Then write the canonical shared-context files actually filled (`identity`, `icp`, `brand`, `voice`, `goals`, `offers`) using the §5A.7 field keys in `references/context-files.md` — only the files captured (partial-capture honesty; never a half-empty file), then hand answers to `niche-config-builder`.

</details>

## Step 3 — Write the team-private config
Hand the two research answers to `niche-config-builder`, which writes the team-private **`atlas/config/niche.md`** (Atlas-only settings: business_model, council_voices, search_tier, `sources` (where to research)). Write this ONE namespaced file — never a bare top-level `config/niche.md` (that collides with other teams). **The campus's canonical context files are the source of truth; `atlas/config/niche.md` is the lowest-precedence fallback.** The `atlas/config/` directory is scaffolded at founding by `campus-start` and at upgrade by `update-workspace`, so it already exists — do not create the campus structure from here.

## Step 4 — Registry entry

Since v5.1 Atlas ships **inside** the kernel, so it is already present in `templates/registry.json` as a `type: kernel` entry and needs no self-registration — a kernel team does not register itself the way a third-party team does. If an older `type: team` entry named `strategy-research-team` is present from the retired standalone plugin, leave it alone and mention it once; removing another entry is the owner's call, not this skill's. For reference, the registration-block shape a third-party team would use lives in `{campus_root}/.campus-os/registration-block-spec.md`:

```json
{
  "team": "strategy-research-team",
  "type": "plugin",
  "version": "2.2.2",
  "department": "cross",
  "owns": "Front brain — brainstorming council, niche scans, competitor audits, briefs to execution teams, and outcome reporting; includes grill-me context extraction.",
  "triggers": ["/atlas-think", "/atlas-scan", "/atlas-daily", "/atlas-validate", "/atlas-competitor", "/atlas-grill", "/atlas-report"],
  "done_check": "brief.md + brief.json emitted (front socket)",
  "results": "outputs/{YYYY-MM}/runs/strategy-research-team/{slug}/results.json",
  "permission": "draft-only"
}
```

Standalone mode: skip silently — there is no campus registry. If the registry file exists but can't be parsed, leave it untouched and tell the owner to run /campus-doctor.

## Step 5 — Confirm + first-run nudge
Show the full config summary, allow edits, then nudge: "Try `/atlas-think` to brainstorm a topic, or `/atlas-scan` to find opportunities. After an execution team ships, `/atlas-report` tells you what worked."
