---
wo_id: WO-YYYY-MM-DD-NN
title: ""
size: quick
status: draft                      # draft | awaiting-signoff | signed | running | blocked | closed  (a cache — events are the truth)
owner: "the owner"
signed_by: ""                      # the owner | the chief of staff (envelope) | PRD approval
parent_prd: ""                     # path, if this executes a PRD phase
method: ""                         # playbook or SOP followed, by path — never copy its steps here
dept: ""                           # a department label from .campus-os/registry.json
goal: ""                           # the goal number this should move (shared/goals.md)
approval_scope: draft-only         # draft-only | create-drafts | publish-in-approved-workflow | autonomous-recurring
tiers: {}                          # e.g. { draft: full, sort: light, check: tool } — never model names
verifier: ""                       # who checks the proof — ideally another lane or model family
budget: { your_minutes: 0, agent_hours: 0, money_usd: 0 }
stop_rules: ["80% of any budget"]
state: "Drafted. Next: sign-off."
created: YYYY-MM-DD
---

# {title}

1. **Job:** one sentence, what gets done.
2. **Done means:** how you'll check it, including the proof: file, link, count.
3. **Team and tiers:** who does each step, at which tier.
4. **Budget:** your minutes, agent hours, money. Label estimates as estimates.
5. **Can use / can't touch:** what it may read and write, and what's off-limits.
6. **Stop and ask when:** in addition to `stop_rules`.
7. **Deliver to:** where the result lands.
8. **Sign-off:** who signed and the date. The chief of staff may sign only inside the envelope: $0, can be undone, no publish or send, no live-site writes, under 2 sessions.

<!-- If this needs the owner, fill in the decision card instead of asking an open question:
decision: { question: "", options: ["A — …", "B — …"], recommended: "A", default: "A", deadline: YYYY-MM-DD }
Default deadline is 3 business days. Money, publishing, public wording and client matters never take the default. -->
