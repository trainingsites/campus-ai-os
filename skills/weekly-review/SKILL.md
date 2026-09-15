---
name: weekly-review
description: Structured weekly business review and planning session. Use when user says "weekly review", "let's do a review", "what happened this week", or at the start of a new week.
department: dean-office
---

# Weekly Review

Structured review of the past week and planning for the next. Dean runs this.

## Setup Required

Kernel preamble §1 applies: `references/kernel-preamble.md`.

## Process

### Step 1: Gather Data

Read the past 7 days of daily logs from `memory/logs/`:
- Today's log and the 6 preceding days
- If logs don't exist for some days, note which days are missing

Read the resolved `goals` context for current OKRs / quarterly priorities (read BEFORE memory.md).
Read `memory/MEMORY.md` for curated facts.
Read `dean/memory.md` for what's in flight and waiting.
Read each department's `memory.md` (`content/memory.md`, `marketing/memory.md`, `sales/memory.md`, and the customer department) for recent run logs.

### Step 2: Review Format

Present the review:

```markdown
## Weekly Review: [Week of Mon DD - Sun DD]

### What Happened This Week
- [Key events, decisions, and work completed from logs]
- [Notable accomplishments across the team]
- [Unexpected issues or changes]

### What Each Department Delivered
- **Content Department:** [Summary of content work]
- **Marketing Department:** [Summary of marketing work]
- **Sales Department:** [Summary of sales work — offers, launches, pricing decisions]
- **{Customer Department — Clients/Coaching/Students based on installed delivery type}:** [Summary of their work]

### What Didn't Get Done
- [Tasks that slipped]
- [Why they slipped (if apparent from logs)]

### Patterns & Insights
- [Recurring themes across the week]
- [What's working well — keep doing]
- [What's not working — adjust]

### Next Week's Plan
- **Priority 1:** [Most important thing]
- **Priority 2:** [Second most important]
- **Priority 3:** [Third most important]
- **Carry-over:** [Tasks from this week that roll forward]

### Goals Check
- [Progress against current goals from MEMORY.md]
- [Any goal adjustments needed?]
```

### Step 3: Update Memory

After the review:
1. Update the resolved `goals` context if quarterly OKRs need adjustment based on the review
2. Update `memory/MEMORY.md` with new curated facts if they've changed
3. Update `dean/memory.md` — clear completed items, add new priorities
3. Ask user if any goals need adjustment

## Rules

- Be honest about what didn't get done — don't spin it
- If logs are sparse, note this and suggest better logging habits
- Keep the review concise — scannable in 5 minutes
- The planning section is the most important output — make it actionable
- Save the review to `outputs/YYYY-MM/reports/weekly-review-YYYY-MM-DD.md`
