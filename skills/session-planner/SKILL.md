---
name: session-planner
description: Prep for live sessions - coaching calls, group sessions, workshops, hot seats. Use when user says "prep for my session", "coaching prep", "get ready for my call with [name]", "hot seat prep", or "workshop prep".
department: community
pack: education
---

# Session Planner

Prep for any live session — 1-on-1 coaching, group calls, hot seats, or workshops. Generates agenda, talking points, relevant context, activities, and follow-up plan.

## Setup Required

Kernel preamble §1 applies: `references/kernel-preamble.md`.

## Before You Start

1. Read the resolved `icp` context — who the clients/students are
2. Read the resolved `voice` context — the owner's coaching/teaching style
3. Check for client/student context:
   - If using client model: read `projects/[client-name]/notes.md`
   - If using department model: check `active-work/` for relevant briefs
4. Check the relevant employee's `memory.md` for past session notes

## Inputs

The user provides:
- **Session type** — 1-on-1, group, hot seat, workshop, office hours
- **Who's attending** — name(s) or description
- **Topic or goal** — what this session should accomplish
- **Background** (optional) — previous session notes, client situation, current challenge
- **Duration** — how long (default: 60 minutes)

## Steps

### Step 1: Research & Context
- Pull any existing notes on this client/student from projects/ or memory
- Review past session notes if available
- Identify where they are in their journey and what they need next

### Step 2: Session Agenda

```markdown
## Session: [Client/Group] — [Date]
**Goal:** [One sentence — what success looks like]

| Time | Topic | Notes |
|------|-------|-------|
| 0:00 | Check-in | How's it going since last time? |
| 0:05 | [Main topic 1] | [Key questions to ask] |
| 0:25 | [Main topic 2 or deep dive] | [Framework or exercise] |
| 0:45 | Action planning | What they'll do before next session |
| 0:55 | Wrap-up | Confirm next steps, schedule follow-up |
```

### Step 3: Talking Points & Questions
- 3-5 key questions to guide the conversation
- Frameworks or models relevant to their situation
- Potential challenges to address proactively

### Step 4: Hot Seat Format (if applicable)
For group hot seats:
- Opening question (gets to the core issue fast)
- Diagnostic framework (help them see their own situation clearly)
- Action step (one thing to do this week)
- Time limit per person (typically 10-15 minutes)

### Step 5: Follow-Up Plan
- Summary email template with action items
- Resources to share
- Next session recommendation

## Output

Save to `outputs/YYYY-MM/lessons/[session-slug]-prep/`:
- `session-prep.md` — Agenda, talking points, context
- `follow-up-template.md` — Post-session email template

If client/project model: also save to `projects/[client-name]/sessions/`

## Rules

- Always check for existing client/student notes before prepping
- The agenda is a guide, not a script — leave room for what emerges
- End every session with clear, specific action items
- After the session, prompt the owner to log notes and key takeaways
