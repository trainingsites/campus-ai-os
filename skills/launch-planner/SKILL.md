---
name: launch-planner
description: Plan and coordinate a product or service launch. Use when user says "plan a launch", "launch this offer", "I want to launch", "open enrollment", "launch sequence", or "go-to-market plan".
department: sales
---

# Launch Planner

Plan and coordinate a complete product or service launch — timeline, email sequence, social content, community announcement, and pre-launch checklist.

## Setup Required

Kernel preamble §1 applies: `references/kernel-preamble.md`.

## Before You Start

1. Read the resolved `offers` context — what's being launched and current offer stack
2. Read the resolved `icp` context — who you're launching to
3. Read the resolved `brand` context and the resolved `voice` context — voice and messaging
4. Read the resolved `connections` context (resolve per `CONTEXT_CANON` (`.campus-os/context-files.md`, else the plugin's `templates/context-files.md`): canon → alias → case-insensitive; never hard-code a filename) — what platforms are available
5. Check `marketing/memory.md` for any active campaigns

## Inputs

The user provides:
- **What's being launched** — course, coaching program, service, product, event, webinar
- **Launch date** — when it goes live
- **Price** — or pricing structure
- **Audience** — who it's for (specific segment or full list)
- **Constraints** (optional) — budget, time, platform limitations

## Steps

### Step 1: Launch Strategy
Determine launch type:

| Type | Timeline | Best For |
|------|----------|----------|
| **Quick Launch** | 3-5 days | Simple offers, add-ons, time-sensitive |
| **Standard Launch** | 7-14 days | Courses, programs, new services |
| **Event Launch** | 14-21 days | Webinars, live events, cohorts |

### Step 2: Build the Timeline

```markdown
## Launch: [Offer Name]
**Launch date:** [Date]
**Type:** [Quick / Standard / Event]

### Pre-Launch (Week -2 to -1)
- [ ] Finalize offer details and pricing
- [ ] Write sales page copy (→ offer-builder skill)
- [ ] Create email sequence (→ email-sequence skill)
- [ ] Plan social content (→ social-planner skill)
- [ ] Prepare community announcement
- [ ] Set up checkout/payment page

### Launch Week
- **Day -1:** Teaser email + social post
- **Day 0:** Launch email + social blitz + community post
- **Day 1-3:** Value emails (address objections, share proof)
- **Day 5-7:** Last chance / cart close (if applicable)

### Post-Launch
- [ ] Thank buyers + deliver onboarding
- [ ] Review results: opens, clicks, conversions
- [ ] Debrief: what worked, what to change next time
```

### Step 3: Create Launch Assets

Generate or delegate:
1. **Email sequence** — hand off to `email-sequence` skill (launch type, 3-5 emails)
2. **Social content plan** — 5-7 posts across the launch window
3. **Community announcement** — one post for the owner's community
4. **Sales page outline** — if needed, hand off to `offer-builder` skill

### Step 4: Coordination Brief

Write a brief for each department involved:
- **Content Department** → social posts, any content assets needed (employees: content-repurposer, content-scout)
- **Customer Department** (Clients/Coaching/Students per installed delivery type) → student/client onboarding prep
- **Marketing Department** → owns the emails and launch execution (employees: email-sequence, social-planner, launch-planner)

Drop briefs in the appropriate `active-work/{department}/` folders.

## Output

Save to `outputs/YYYY-MM/plans/[launch-slug]/`:
- `launch-plan.md` — Full timeline and checklist
- `launch-emails/` — Email sequence (or reference to email-sequence output)
- `launch-social.md` — Social content plan
- `community-announcement.md` — Community post

## Rules

- Every launch must have a clear deadline — open-ended launches don't convert
- Lead with transformation, not features
- Build urgency gradually — never start at max pressure
- Include a post-launch debrief step — launches that aren't reviewed don't improve
