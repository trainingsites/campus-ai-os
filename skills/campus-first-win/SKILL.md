---
name: campus-first-win
description: >
  Produce the owner's first real deliverable within 10 minutes of install. Picks
  the deliverable by delivery type from workspace.json - community prompts,
  a lesson plan, or a session prep pack - and saves it to outputs/. Use when
  the owner says "/campus-first-win", "show me what you can do", or right after /campus-start.
version: 3.0.0
department: kernel
---

# /campus-first-win  -  Real Work in 5 Minutes

The retention moment. The owner watches their new team produce actual, usable
work before they've configured anything. One deliverable, done well, saved
where they can find it.

## Guard

Requires `workspace.json` (run /campus-start first if missing). Works fine with all
`shared/` files at defaults  -  use the founding answers - `business.what`, `business.sells_today`, `business.audience` (nested `business` object), and `structure` from workspace.json, plus the resolved `identity` context - as context. Any of the business fields may be empty on a quick-path campus that hasn't finished onboarding; fall back to the resolved `identity` context (resolved through `CONTEXT_CANON`, so it finds the file whatever the campus calls it) or ask one question. If they sell nothing yet, the first win is audience-building work (community prompts or a lead-magnet outline).

## Step 1  -  Pick by delivery type (from workspace.json)

| Delivery | Deliverable |
|---|---|
| community | 5 ready-to-post discussion prompts for their topic and audience |
| courses | a complete lesson plan for their next topic (ask which topic - one question) |
| coaching | a session prep pack for their next call (ask who/what - one question) |
| mix | ask: "Which would help most this week?" and offer the three above |

At most ONE question before producing. If the answer is vague, make a sensible
choice and say so.

**Produce the REAL thing, never a sample.** The deliverable must be actual,
usable work the owner can deliver from or post TODAY - never a "sample",
"example", "demo", or "template to show what's possible". Do not label it as
a sample and do not add disclaimers like "swap the topic anytime" or "tell me
your real topic and I'll build the real one". If you don't know the topic,
ASK the one question - asking is always better than producing a demo. The
test: would the owner walk into their next class/call/community and use this
exact file? If not, it's not a first win.

## Step 2  -  Produce

Make it genuinely good  -  specific to their subject and audience, not template
filler. Their words from setup should visibly appear in the work. Length:
enough to use today, short enough to read in 5 minutes.

## Step 3  -  Save + show

1. Save to {campus root}/outputs/{YYYY-MM}/first-win-{slug}.md - the outputs folder INSIDE the campus folder (next to workspace.json), never a session outputs directory.
2. Show the full deliverable in chat.
3. Close the loop, plainly: "That's your team's first piece of work  -  it's
   saved in your outputs folder. You can use it as-is or tell me what to
   change."

## Step 4  -  One forward pointer (not a tour)

Offer exactly one next action, chosen by delivery type  -  e.g. "Want me to draft
the next one, or set this up to happen weekly?" If they take the weekly offer,
that becomes their first scheduled task.

Log the run to dean/.activity.jsonl (skill: "campus-first-win"). If the owner renamed their chief of staff, speak as that name.

## Rules

- Under 10 minutes from install to saved deliverable. That's the promise; if a
  step threatens it, cut the step.
- No configuration talk during the win. Enrichment starts NEXT session.
- Never fake specificity  -  if you don't know their niche's jargon, write plainly
  rather than guessing wrong.

## File anchoring (critical)

Kernel preamble §2 applies: `references/kernel-preamble.md`.