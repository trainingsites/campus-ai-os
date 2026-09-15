---
name: morning-brief
description: Daily intelligence briefing - what's happening, what to work on, what needs attention. Use when user says "morning brief", "what should I work on", "daily brief", "what's on today", or at the start of a work session.
department: dean-office
---

# Morning Brief

Daily intelligence report. Reviews what's happening, what's due, and recommends what to work on today.

## Setup Required

Kernel preamble §1 applies: `references/kernel-preamble.md`.

## Before You Start

1. Read the resolved `goals` context — current OKRs / priorities. **Read BEFORE memory.md.** Strategic priority informs which tactical items deserve focus today.
2. Read `dean/memory.md` — check "Waiting On You" and active items
3. Read the resolved `offers` context — what's for sale, any active launches
4. Read each department's `memory.md` (`content/memory.md`, `marketing/memory.md`, `sales/memory.md`, and the customer department: `clients/`, `coaching/`, or `students/`) — what's in progress
5. Check `memory/logs/` for yesterday's log (if it exists)
6. Scan `dean/skill-candidates/` — count files where frontmatter `status: proposed`. Skip `_promoted/` and `_rejected/` subfolders.
7. **Self-authoring loop staleness check.** Read `dean/last-promote-run.json` if it exists. Compute days since `ts`. Count lines written after that `ts` across `dean/.activity.jsonl` **and every `dean/.activity.*.jsonl` shard** (canon: `.campus-os/ledger-paths.md`) (skip header `#` lines and blank lines). Mark the loop as **stale** if any of: (a) `last-promote-run.json` is missing, (b) `ts` is more than 7 days old AND there are ≥ 3 new ad-hoc ledger entries since, or (c) `ts` is more than 14 days old regardless. Note this for Step 4.

## Steps

### Step 1: Calendar Check
If a calendar is connected via MCP:
- Pull today's events
- Flag any prep needed for upcoming sessions

If no calendar connected:
- Ask: "Anything on the calendar today I should know about?"

### Step 2: Task Review
Scan all department memory files for:
- Tasks in progress
- Items flagged for follow-up
- Deadlines approaching
- "Waiting On You" items from `dean/memory.md`

### Step 3: Quick Market Scan (Optional)
If the user has configured their niche in the resolved `icp` context:
- Run a quick web search for recent news/trends in their space
- Surface 1-2 relevant items (not a full research report)

### Step 4: Generate the Brief

```markdown
## Morning Brief — [Today's Date]

### Today's Schedule
[Calendar items or "No calendar connected — tell me what's on today"]

### What Needs Your Attention
- [Waiting On You items]
- [Deadlines approaching]
- [Open items from yesterday]

### Skill Candidates Pending Review
*Only show this section if `dean/skill-candidates/` contains 1+ files with `status: proposed`. If zero, omit the entire section — no empty-state line.*

[N] new candidates from your recent work:
- **[slug-1]** ([sample_size] occurrences) — [one-line description from frontmatter]
- **[slug-2]** ([sample_size] occurrences) — [one-line description from frontmatter]

Run `/review-candidates` to see drafts. Approve with "approve {slug}".

### Self-Authoring Loop Status
*Only show this section if Before-You-Start step 7 flagged the loop as stale. If fresh, omit entirely.*

The weekly skill-candidate scan hasn't run recently and your activity ledger has [N] new entries since the last run. Want me to scan for new patterns now? Run `/promote-skills`.

### What Your Departments Are Working On
- **Content Department:** [Status — pulled from `content/memory.md`]
- **Marketing Department:** [Status — pulled from `marketing/memory.md`]
- **Sales Department:** [Status — pulled from `sales/memory.md`]
- **{Customer Department — Clients/Coaching/Students based on installed delivery type}:** [Status — pulled from that department's memory.md]

### Recommended Focus Today
Based on what's in flight and what's due:
1. **[Priority 1]** — why this matters today
2. **[Priority 2]** — why this matters today
3. **[Priority 3]** — if time allows

### Market Pulse (1-2 items)
- [Relevant trend or news in their niche]
```

### Step 5: Save and Prompt

Save the brief to `outputs/YYYY-MM/reports/morning-brief-[date].md`

Ask: "Want me to start on any of these, or is there something else on your mind today?"

## Rules

- Keep it scannable — the owner should digest this in 2 minutes
- Prioritize by impact, not urgency (unless something is actually urgent)
- Don't fabricate tasks — only surface real items from memory and logs
- If logs are empty and no calendar, keep it short: "Nothing in the system yet. What are you working on today?"
- This is a briefing, not a to-do list — include context, not just items
