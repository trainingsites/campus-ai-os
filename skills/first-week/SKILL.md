---
name: first-week
description: 5-day guided onboarding tour of your AI team. Use when user says "first week", "getting started", "show me what the team can do", or "onboarding".
department: kernel
---

# First Week — Meet Your AI Team

A 5-day guided tour that teaches you how to work with your AI team. Each day takes 15-30 minutes and exercises a different part of the system.

## Before Starting

Confirm `/campus-start` has been completed. If `workspace.json` does not exist in the campus folder, or if `about-me/about-me.md` does not exist, tell the owner to run `/campus-start` first.

Read `dean/memory.md` to check if any first-week days have already been completed.

## Day 1: Your Morning Brief

**Theme:** See what Dean knows about your business.

1. Run the `morning-brief` skill
2. Review the output together — does it reflect your business accurately?
3. If anything is off, correct it. Dean writes corrections to the right place.

**Wrap-up:** "Tomorrow we'll put the Content Department to work."

Log completion to `dean/memory.md`.

## Day 2: Content Repurposing

**Theme:** Give the Content Department something to work with.

1. Ask the owner for a piece of raw content — a recording transcript, a blog post, a social media thread, or even a rough idea
2. Run `content-repurposer` on it
3. Review the output: social posts, email draft, blog version
4. Ask: "Does this sound like you?" Adjust voice if needed by updating the resolved `voice` context

**Wrap-up:** "Tomorrow the Marketing Department plans a campaign."

Log completion.

## Day 3: Email Sequence

**Theme:** Put the Marketing Department to work.

1. Pick one of the owner's offers from the resolved `offers` context
2. Run `email-sequence` — choose a sequence type (nurture, launch, or onboarding)
3. Review the emails — tone, length, structure
4. Refine as needed

**Wrap-up:** "Tomorrow we exercise the customer-facing department installed for your delivery type."

Log completion.

## Day 4: Your Customer Department

**Theme:** Exercise the department configured for your delivery type. Read `library/skill-to-department-map.json` (in the plugin root) to find which customer department was installed and which employees live in it.

**If Clients Department (`clients/`) is installed:**
1. Pick a client (real or example)
2. Run `session-planner` to prep for a session
3. Run `client-comms` to draft a follow-up email

**If Students Department (`students/`) is installed:**
1. Run `student-comms` for a welcome sequence
2. Run `community-pulse` for discussion prompts

**If Coaching Department (`coaching/`) is installed:**
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
