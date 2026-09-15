---
name: social-planner
description: Build content calendars and plan social media. Use when user says "plan my social media", "build a content calendar", "what should I post this week", "social media plan", or "plan my content".
department: marketing
---

# Social Planner

Plan and batch-create social media content for a week or month. Combines calendar planning with content creation.

## Setup Required

Kernel preamble §1 applies: `references/kernel-preamble.md`.

## Before You Start

1. Read the resolved `brand` context and the resolved `voice` context — voice and style
2. Read the resolved `icp` context — who you're reaching
3. Read the resolved `offers` context — what's being sold (informs promotional content)
4. Read the resolved `connections` context (resolve per `CONTEXT_CANON` (`.campus-os/context-files.md`, else the plugin's `templates/context-files.md`): canon → alias → case-insensitive; never hard-code a filename) — check what social platforms are active
5. Check `content/memory.md` — any existing content plans or themes

## Inputs

The user provides:
- **Timeframe:** week or month
- **Content themes or topics** (optional — generate from offers/audience if not provided)
- **Upcoming events, launches, or deadlines** (optional)
- **Posting frequency preference** (optional — default to 3-5x/week)

## Steps

### Step 1: Define Content Mix
Establish the posting ratio:
- **60% Value** — tips, insights, how-tos, lessons learned
- **15% Engagement** — questions, polls, behind-the-scenes, personal stories
- **25% Promotion** — offers, events, testimonials, CTAs

Adjust based on upcoming launches (more promo) or quiet periods (more value).

### Step 2: Build the Calendar

For each posting day, create an entry:

```markdown
### [Day, Date]
- **Platform:** [where to post]
- **Type:** [value / engagement / promo]
- **Topic:** [specific topic]
- **Hook:** [first line / scroll-stopper]
- **CTA:** [what you want them to do]
```

### Step 3: Batch-Create Posts

Write full posts for each calendar entry. Follow platform-specific formats:
- **LinkedIn:** 1000-1300 chars, professional insight, line breaks for readability
- **X / Twitter:** Under 280 chars or thread format
- **Facebook:** Conversational, question-driven
- **Instagram:** Visual-first captions with hashtags

### Step 4: Review and Adjust

Present the calendar and posts. Ask:
- "Does this mix feel right?"
- "Any topics missing?"
- "Anything coming up I should plan around?"

## Output

Save to `outputs/YYYY-MM/social/content-calendar-[timeframe]/`:
- `calendar.md` — The full content calendar
- `posts/` — Individual post files by date

## Rules

- Every post must sound like the owner — check voice profile
- Never repeat the same hook format two days in a row
- Include at least one post per week that ties to a current offer
- If the owner's community platform is connected, include community posts in the calendar
