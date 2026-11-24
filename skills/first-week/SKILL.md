---
name: first-week
description: 5-day guided onboarding tour of your AI team. Use when user says "first week", "getting started", "show me what the team can do", or "onboarding".
department: kernel
---

# First Week — Meet Your AI Team

A 5-day guided tour that teaches you how to work with your AI team. Each day takes 15-30 minutes and exercises a different part of the system.

## Before Starting

Kernel preamble §1 applies: `references/kernel-preamble.md`.

For the owner's basics, read the resolved `identity` context (`shared/business.md` on a founded campus), never `about-me/`.

Read `dean/memory.md` to check if any first-week days have already been completed.

## Day 1: Your Morning Brief

**Theme:** See what Dean knows about your business.

1. Run the `morning-brief` skill
2. Review the output together — does it reflect your business accurately?
3. If anything is off, correct it. Dean writes corrections to the right place.

**Wrap-up:** "Tomorrow your content repurposer gets to work. Bring a piece of raw content."

Log completion to `dean/memory.md`.

## Day 2: Content Repurposing

**Theme:** Give your content repurposer something to work with. Name its department by the registry label of the department whose roster holds `content-repurposer` (kernel preamble §2).

1. Ask the owner for a piece of raw content — a recording transcript, a blog post, a social media thread, or even a rough idea
2. Run `content-repurposer` on it
3. Review the output: social posts, email draft, blog version
4. Ask: "Does this sound like you?" Adjust voice if needed by updating the resolved `voice` context

**Wrap-up:** "Tomorrow your email writer drafts a sequence for one of your offers."

Log completion.

## Day 3: Email Sequence

**Theme:** Put your email writer (`email-sequence`) to work. Name its department by its registry label.

1. Pick one of the owner's offers from the resolved `offers` context
2. Run `email-sequence` — choose a sequence type (nurture, launch, or onboarding)
3. Review the emails — tone, length, structure
4. Refine as needed

**Wrap-up:** "Tomorrow your staff works with the people you serve."

Log completion.

## Day 4: The People You Serve

**Theme:** Exercise the employees who work with your clients, students or members. Find them in `.campus-os/registry.json`: the department rosters that hold `client-comms`, `student-comms`, `session-planner` and `class-manager`. Name each department by its registry label (kernel preamble §2). Ask one question first: "Who do you work with most: clients, students, or coaching members?" Then run the steps below, skipping any whose employee this campus does not have (it is not in the registry) and saying so in one line:

**Clients:**
1. Pick a client (real or example)
2. Run `session-planner` to prep for a session
3. Run `client-comms` to draft a follow-up email

**Students or members:**
1. Run `student-comms` for a welcome sequence
2. Run `community-pulse` for discussion prompts

**Coaching:**
1. Run `session-planner` to prep for a coaching call
2. Run `class-manager` to schedule and prep an upcoming session

**Wrap-up:** "Tomorrow we run a campus playbook — multiple departments working together."

Log completion.

## Day 5: Campus Playbook

**Theme:** See how the campus works together.

1. Read the playbooks in the chief of staff's entry file (`dean/{ENTRY_FILE}`)
2. Pick one that matches current work
3. Run it — Dean coordinates across departments
4. Review the handoffs and final output

**Wrap-up:** Present the full capabilities summary:
- What each department can do (list its employees)
- What campus playbooks are available
- How to give tasks ("just tell me what you need — I'll route it")
- How the system learns (preferences → each department's {ENTRY_FILE}, outcomes → department memory.md)

Log completion. Update `dean/memory.md`: "First week complete."

## Rules

- One day at a time — don't rush through all 5
- Each day should produce real output the owner can use, not demo content
- If the owner wants to skip ahead, let them — but note what was skipped
- Always ask "does this sound like you?" after content generation — voice calibration is ongoing
- Log each day's completion so progress survives across sessions
