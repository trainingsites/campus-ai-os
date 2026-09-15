---
name: email-sequence
description: Write email sequences for any purpose - nurture, launch, onboarding, re-engagement, webinar follow-up. Use when user says "write an email sequence", "create emails for", "launch emails", "nurture sequence", "welcome emails", or "follow-up sequence".
department: marketing
---

# Email Sequence Writer

Write complete email sequences for any business purpose. Multiple frameworks. Ready to send or load into any email platform.

## Setup Required

Kernel preamble §1 applies: `references/kernel-preamble.md`.

## Before You Start

1. Read the resolved `voice` context — emails must sound like the owner
2. Read the resolved `brand` context — communication style
3. Read the resolved `icp` context — who's receiving these emails
4. Read the resolved `offers` context — if the sequence promotes an offer
5. Read the resolved `connections` context (resolve per `CONTEXT_CANON` (`.campus-os/context-files.md`, else the plugin's `templates/context-files.md`): canon → alias → case-insensitive; never hard-code a filename) — check if an email platform is connected

## Inputs

The user provides:
- **Sequence type** — nurture, launch, onboarding, re-engagement, webinar follow-up, cart abandonment
- **What it's for** — the offer, program, event, or goal
- **Number of emails** — default: 3-5 depending on type
- **Audience segment** — who gets this sequence
- **Timing** (optional) — days between emails

## Sequence Types

| Type | Purpose | Typical Length | Tone |
|------|---------|---------------|------|
| **Nurture** | Build trust and demonstrate value | 5-7 emails over 2-3 weeks | Educational, generous |
| **Launch** | Drive sales for a specific offer | 3-5 emails over 5-7 days | Urgency builds gradually |
| **Onboarding** | Welcome new customers/students | 3-4 emails over first week | Warm, action-oriented |
| **Re-engagement** | Win back inactive contacts | 3 emails over 10 days | Direct, value-first |
| **Webinar follow-up** | Convert attendees post-event | 3 emails over 3 days | Recap + offer |
| **Cart abandonment** | Recover incomplete purchases | 2-3 emails over 48 hours | Helpful, not pushy |

## Steps

### Step 1: Map the Sequence
- Define the arc: what emotional state do they start in? Where do you take them?
- Plan each email's job: educate → connect → offer → close
- Set timing between emails

### Step 2: Write Each Email

For each email, provide:
- **Subject line** — 3 options (A/B test ready)
- **Preview text** — 40-90 characters
- **Body** using one of these frameworks:

| Framework | Structure | Best For |
|-----------|-----------|----------|
| **PAS** | Problem → Agitate → Solution | Launch, re-engagement |
| **BAB** | Before → After → Bridge | Nurture, onboarding |
| **Story** | Hook → Narrative → Lesson → CTA | Nurture, trust-building |
| **Direct** | Statement → Proof → CTA | Cart abandonment, final push |
| **Social Proof** | Result → How → Offer | Launch, testimonial-driven |

### Step 3: Review Sequence Flow
- Read all emails back-to-back. Does the arc make sense?
- Does urgency build naturally (not artificially)?
- Is each email valuable on its own, not just a setup for the next?

## Output

Save to `outputs/YYYY-MM/emails/[sequence-name]/`:
- `sequence-plan.md` — Overview: type, audience, timing, arc
- `email-1.md` through `email-N.md` — Individual emails

If an email platform is connected via MCP, offer to create drafts there.

## Rules

- Every email must be valuable standalone — no "just checking in" filler
- Match the owner's voice exactly — check voice profile
- One CTA per email — don't dilute
- Never use fake urgency or manufactured scarcity
- Subject lines: specific > clever. Clear > cute.
