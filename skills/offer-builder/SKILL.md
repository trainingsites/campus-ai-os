---
name: offer-builder
description: Structure offers, set pricing, and write sales copy. Use when user says "create an offer", "build a product", "pricing strategy", "write a sales page", "product description", or "package this service".
department: sales
---

# Offer Builder

Structure new offers, set pricing, and write product/service descriptions. Output is ready for a sales page, shopping cart, or landing page.

## Setup Required

Kernel preamble §1 applies: `references/kernel-preamble.md`.

## Before You Start

1. Read the resolved `offers` context — existing offer stack (avoid overlap, find upsell paths)
2. Read the resolved `icp` context — who you're selling to, their pain points
3. Read the resolved `brand` context and the resolved `voice` context — sales voice
4. Read the resolved `connections` context (resolve per `CONTEXT_CANON` (`.campus-os/context-files.md`, else the plugin's `templates/context-files.md`): canon → alias → case-insensitive; never hard-code a filename) — check if a shopping cart is connected

## Inputs

The user provides:
- **What they're selling** — course, coaching, service, product, membership, event
- **Who it's for** — target audience segment
- **What it delivers** — the transformation or outcome
- **Price** (optional) — or ask for pricing guidance
- **Format** (optional) — how it's delivered

## Steps

### Step 1: Offer Structure

Define the offer using this framework:

```markdown
## [Offer Name]

**The Promise:** [One sentence — what transformation does the buyer get?]
**Who It's For:** [Specific description — not "everyone"]
**Who It's NOT For:** [Important boundary — builds trust]
**Format:** [How it's delivered — course, 1-on-1, group, done-for-you, etc.]
**Price:** [Amount and structure — one-time, monthly, per-session]
**What's Included:**
- [Component 1 — describe the value, not just the deliverable]
- [Component 2]
- [Component 3]
```

### Step 2: Pricing Strategy

If pricing guidance is requested:
- **Anchor to transformation value** — what's the outcome worth to them?
- **Compare to alternatives** — what would they pay for the DIY approach?
- **Consider the stack** — how does this fit with other offers?

Suggest a pricing structure:
| Model | When to Use |
|-------|-------------|
| One-time | Courses, templates, digital products |
| Monthly | Memberships, ongoing access, subscriptions |
| Per-session | Coaching, consulting, done-for-you |
| Tiered | When different audiences need different access levels |

### Step 3: Sales Copy

Write the product description using this structure:
1. **Hook** — the problem or desire (2-3 sentences)
2. **Agitate** — why their current approach isn't working
3. **Solution** — what this offer does differently
4. **What's Included** — components, not features
5. **Who This Is For / NOT For** — builds trust through honesty
6. **Transformation** — before vs. after
7. **CTA** — clear next step

### Step 4: Update Offers

Add the new offer to the resolved `offers` context so all AI employees know about it.

## Output

Save to `outputs/YYYY-MM/plans/[offer-slug]/`:
- `offer-structure.md` — Full offer breakdown
- `sales-copy.md` — Ready-to-use product description
- `pricing-rationale.md` -> Pricing logic and recommendations

If a shopping cart is connected via MCP, offer to create the product listing there.

## Rules

- Lead with transformation, not features
- Never list individual lessons or sessions in sales copy — describe outcomes
- Use PAS or BAB structure — not feature dumps
- Match the owner's voice — confident but not pushy
- Always update the resolved `offers` context after creating a new offer

## Want a full department for this job?

Kernel preamble §3 applies: `references/kernel-preamble.md`.