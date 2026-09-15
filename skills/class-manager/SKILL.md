---
name: class-manager
description: Full live session lifecycle - schedule, prep, market, and process sessions. Use when user says "prep my class", "schedule a session", "run the waterfall", "process the recording", "class scan", or "session pipeline".
department: education
pack: education
---

# Class Manager

Full lifecycle management for live sessions — classes, workshops, cohorts, and events. Schedule them, prep materials, market them, and process recordings into course content.

## Setup Required

Kernel preamble §1 applies: `references/kernel-preamble.md`.

## Before You Start

1. Read the resolved `icp` context — who the students/attendees are
2. Read the resolved `offers` context — what programs these sessions belong to
3. Read the resolved `voice` context — teaching voice
4. Check the Education Director's `memory.md` for session schedule and history

## Sub-Commands

The user can run specific parts or the full pipeline:

| Command | What It Does |
|---------|-------------|
| `class-manager schedule` | Register a new session |
| `class-manager prep` | Generate pre-session materials |
| `class-manager market` | Create announcement email + community post |
| `class-manager process` | Post-session waterfall (recording → content) |
| `class-manager scan` | Weekly scan: what needs marketing or processing |
| `class-manager` (no sub) | Full pipeline: find → prep → market |

## Schedule a Session

Collect:
- **Title** — what the session is about
- **Date and time** — when it happens
- **Duration** — how long (default: 60 minutes)
- **Format** — live class, workshop, cohort session, office hours
- **Track/Level** — beginner, intermediate, advanced
- **Description** — 2-3 sentence summary
- **Learning outcomes** — what attendees will be able to do

Save to the Education Director's `memory.md` under session schedule.
If a calendar is connected, create the event.

## Prep Materials

Generate all pre-session materials using the `lesson-planner` skill pattern:

1. **Facilitator agenda** — timing, talking points, transitions
2. **Participant handout** — key concepts, frameworks, space for notes
3. **Worksheet** (if applicable) — exercises tied to outcomes
4. **Participant prep message** — what to do/read before the session

Save to `outputs/YYYY-MM/lessons/[session-slug]-prep/`

## Market the Session

Create promotional content:
1. **Announcement email** — date, topic, outcomes, registration link
2. **Community post** — discussion-style announcement for the owner's community
3. **Social post** (optional) — if social platforms are active

Save to `outputs/YYYY-MM/comms/[session-slug]-marketing/`

Mark session as "marketed" in memory.

## Process Recording (Post-Session Waterfall)

After a session ends, process the recording:

```
Recording / Transcript / Notes
        ↓
1. Extract key takeaways, steps, and resources
2. Write a structured lesson (for course or resource library)
3. Draft a community recap + discussion starter
4. Draft a follow-up email for attendees
5. Create a session summary document
        ↓
Mark session as "processed" in memory
```

Save to `outputs/YYYY-MM/lessons/[session-slug]-recap/`

## Weekly Scan

Review all sessions in memory:
- **Upcoming + not marketed** → flag for marketing
- **Completed + not processed** → flag for waterfall processing
- **Upcoming this week** → flag for prep if not yet prepped

Present the scan results and ask what to work on.

## Rules

- Never market a session that hasn't been prepped
- Never process a recording without confirming the session happened
- All materials must match the owner's teaching voice
- Mark marketing and processing status in memory after each step
- If the owner's LMS or community platform is connected, offer to publish directly
