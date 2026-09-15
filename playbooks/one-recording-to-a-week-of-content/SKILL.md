---
name: one-recording-to-a-week-of-content
description: Turn ONE recording, transcript, or set of notes into a full week of marketing — a content brief, a core piece, an announcement email, three social posts, and a community discussion post. Use when the owner drops a recording/transcript/notes in inputs/ and says "turn this into a week of content", "repurpose this into everything", "one recording to a week", or runs the playbook by name. The transformation showcase — one input in, a week of drafts out.
---

# Playbook — One Recording → A Week of Content

**The showcase.** The owner drops one source (a call recording, a webinar transcript, a YouTube transcript, or raw notes) into `inputs/`, runs this playbook, and gets a week of ready-to-review marketing in the owner's voice. Six stages, all starter employees, no paid teams, no connectors required, draft-first. The ledger shows a real light/full tier split.

Dean runs this. Read `playbooks/README.md` (the runtime) once before your first playbook run.

---

## The playbook contract

```yaml
playbook:
  name: "One Recording → A Week of Content"
  slug: one-recording-to-a-week-of-content
  version: "1.0.0"
  trigger:
    type: event            # event | cadence | manual
    on: "owner drops a recording/transcript/notes in inputs/ and asks to turn it into a week of content"
  goal: >                  # objective + checkable, not "make it good"
    From ONE source, five review-ready drafts in the owner's voice: a content brief
    (>=3 usable angles), one core piece (>=600 words, on-brand), one announcement email
    (single CTA), three platform-native social posts, and one community discussion post
    (ends in an open question). All saved to the run dir, run_id stamped, nothing published.
  topology: manager-helpers   # Dean is the manager; each stage is a starter employee
  model_tier_default: full    # explicit; individual stages opt down to light below
  # Concepts, not filenames. Resolve each through CONTEXT_CANON
  # (.campus-os/context-files.md, else templates/context-files.md):
  # canon -> alias -> case-insensitive. Naming files here is how connections.md
  # came to be listed on a campus where founding writes tools.md and nothing else.
  reads_context:              # every stage stays on-voice / on-ICP without re-briefing
    - brand
    - voice
    - icp
    - offers
    - connections
  stages:
    - n: 1
      stage: extract-brief
      skill: content-repurposer      # intake/analysis pass
      produces: "content brief — core message, >=3 angles, key quotes, audience takeaways"
      model_tier: light              # analysis/extraction — safe to run lighter
      done_check: "brief names >=3 usable angles AND >=2 verbatim quotes from the source"
      fail_action: escalate-to-james
    - n: 2
      stage: core-piece
      skill: content-repurposer      # generation pass
      produces: "one core piece (blog draft or long-form post), >=600 words, owner voice"
      model_tier: full               # voice-carrying long-form — pinned full
      done_check: "on-brand voice + >=600 words + one clear reader takeaway (no invented facts)"
      fail_action: escalate-to-james
    - n: 3
      stage: announcement-email
      skill: email-sequence          # single announcement email
      produces: "one announcement email — subject options + body, single CTA"
      model_tier: full               # voice-carrying + owner-facing send copy — pinned full
      done_check: "exactly one CTA + subject line present + links to the core piece; draft-only"
      fail_action: escalate-to-james
    - n: 4
      stage: social-posts
      skill: social-planner          # three platform-native posts
      produces: "3 social posts (platform-native), each with a hook + the week's theme"
      model_tier: light              # short-form drafts run light; owner reviews before any post
      done_check: "3 distinct posts, each <=1 idea, each carries a hook; no duplicate angles"
      fail_action: ship-with-flag    # low-stakes generative — flag for owner review, don't block
    - n: 5
      stage: community-post
      skill: community-pulse         # one discussion starter
      produces: "1 community discussion post that invites replies"
      model_tier: light
      done_check: "post ends in an open question AND ties to the source's core message"
      fail_action: ship-with-flag
    - n: 6
      stage: package-and-ledger
      skill: kernel                  # Dean packages the run
      produces: "results.json + per-stage ledger lines (run_id + tier fields)"
      model_tier: light
      done_check: "results.json is schema-valid AND one ledger line exists per generative stage"
      fail_action: escalate-to-james
  verification: "each stage's done_check must pass before the next stage starts (stages 4/5 may ship-with-flag)"
  stop_condition:
    done_when: "5 drafts in the run dir + results.json written + ledger lines appended"
    cost_cap: { max_passes: 3, max_minutes: 20 }   # REQUIRED runaway guard
  run_id: required
  permission: draft-only          # FLOOR. No stage in this playbook is granted publish.
  human_gates:
    - "The owner approves the playbook design before first run"
    - "The owner reviews the week of drafts before anything is scheduled or sent"
```

---

## How Dean executes it

**0. Preconditions.** A source file exists in `inputs/` (transcript, recording transcript, or notes). Never write to `inputs/` — copy anything you must mutate into the run dir first. If no source is present, ask the owner which file to use.

**1. Mint the run_id and open the run dir.**
- `run_id = one-recording-{YYYYMMDD-HHMMSS}`
- run dir: `outputs/{YYYY-MM}/runs/playbooks/one-recording-to-a-week-of-content/{run_id}/`

**2. Load context once** (the `reads_context` list). Every downstream stage inherits it — do not re-brief per stage.

**3. Run the six stages in order.** For each: resolve the tier (stage `model_tier` → header default → policy → `full`; pins in `README.md` override), run the skill, write the output as `0N-{stage}.md` in the run dir, then run the stage's `done_check`. A generative stage does not hand off until its done-check passes; loop to `cost_cap.max_passes`, then take its `fail_action`.

- **Stage 1 — extract-brief** (light): run `content-repurposer` in analysis mode over the source. Output the brief. Check: ≥3 angles + ≥2 verbatim quotes.
- **Stage 2 — core-piece** (full): run `content-repurposer` generation using the brief. One core long-form piece in the owner's voice. Check: on-brand + ≥600 words + one takeaway.
- **Stage 3 — announcement-email** (full): run `email-sequence` for a single announcement email pointing at the core piece. Check: one CTA + subject + link; draft-only.
- **Stage 4 — social-posts** (light): run `social-planner` for 3 platform-native posts on the week's theme. Check: 3 distinct, single-idea, hooked posts.
- **Stage 5 — community-post** (light): run `community-pulse` for one discussion starter. Check: ends in an open question, ties to the core message.
- **Stage 6 — package-and-ledger** (light): Dean writes `results.json` (interop 1.0 shape in `README.md`) and appends one line per generative stage to `dean/.activity.jsonl`, each carrying `run_id`, `tier_requested`, `tier_used`.

**4. Stop condition + gate.** When the 5 drafts + `results.json` + ledger lines exist, STOP. Present the week of drafts to the owner for review. Publish nothing — no stage here carries a publish grant.

**Tier note:** the light stages (1 extract, 4 social, 5 community, 6 package) run on the lighter engine from `.campus-os/model-routing.md` (`light: subagent-haiku`); the full stages (2 core piece, 3 email) run on the primary model — both pinned `full` by the voice/publish pins. The ledger records a real `tier_used` split with per-stage timestamps; if the light engine is down, the stage escalates to full and logs it.
