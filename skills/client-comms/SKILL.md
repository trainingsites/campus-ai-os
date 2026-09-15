---
name: client-comms
description: Write client communications - intake, follow-ups, check-ins, proposals, project updates. Use when user says "write a follow-up for [client]", "client intake email", "check in with [client]", "draft a proposal", or "project update email".
department: community
---

# Client Communications

Write any type of client communication — intake, session follow-ups, check-ins, re-engagement, testimonial requests, proposals, and project updates.

## Setup Required

Kernel preamble §1 applies: `references/kernel-preamble.md`.

## Before You Start

1. Read the resolved `voice` context — must sound like the owner
2. Read the resolved `brand` context — communication style
3. Read the resolved `icp` context — who the clients are
4. Read the resolved `offers` context — services available
5. If client model: read `projects/[client-name]/notes.md` for client context
6. Check the relevant employee's `memory.md` for client history

## Inputs

The user provides:
- **Communication type** — see types below
- **Client name** (if specific)
- **Context** — what happened, what's next, the situation
- **Urgency** (optional) — routine or time-sensitive

## Communication Types

| Type | Purpose | Tone |
|------|---------|------|
| **Intake / Welcome** | New client onboarding | Professional, warm, sets expectations |
| **Session Follow-up** | After a coaching/consulting session | Specific, actionable, prompt |
| **Check-in** | Between sessions — how's progress? | Caring, accountable, supportive |
| **Re-engagement** | Client gone quiet | Direct, value-forward, no guilt |
| **Testimonial Request** | Ask for a case study or review | Grateful, specific, easy to say yes |
| **Proposal** | Pitching a new engagement | Clear scope, confident, outcome-focused |
| **Project Update** | Status report on deliverables | Organized, transparent, next steps clear |

## Steps

### Step 1: Gather Context
- Pull client notes from `projects/[client-name]/` if available
- Review past session notes or memory entries
- Understand where this client is in their journey

### Step 2: Write the Communication

- **Subject line** — 3 options (clear > clever)
- **Opening** — reference something specific to this client
- **Body** — the purpose (keep it focused — 150-300 words)
- **CTA** — one clear next step
- **Sign-off** — matches the owner's professional style

### Step 3: Proposal Format (if applicable)

For proposals, use this structure:
1. **Context** — what they told you they need
2. **Approach** — how you'll solve it
3. **Scope** — what's included (and what isn't)
4. **Investment** — pricing and terms
5. **Next Steps** — how to move forward

## Output

Save to `outputs/YYYY-MM/comms/[client-slug]/` or `projects/[client-name]/`

If an email platform is connected via MCP, offer to create a draft.

## Rules

- Every client communication must reference something specific to THEM
- Never send generic templates — personalize based on available context
- Follow-ups within 24 hours of sessions (prompt the owner if overdue)
- Proposals: lead with their problem, not your credentials
- Match the owner's voice — clients should feel they're hearing from the owner directly
