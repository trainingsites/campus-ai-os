---
wo_id: WO-YYYY-MM-DD-NN
title: ""
size: full
status: draft                      # a cache — events are the truth
owner: "the owner"
signed_by: ""                      # the owner | PRD approval (children within the PRD envelope)
parent_prd: ""
method: ""                         # playbook or SOP by path; its checkpoints are this order's gates (by reference)
dept: ""
goal: ""
approval_scope: draft-only
tiers: {}
verifier: ""
budget: { your_minutes: 0, agent_hours: 0, money_usd: 0 }
stop_rules: ["80% of any budget"]
state: "Drafted. Next: challenge, then sign-off."
created: YYYY-MM-DD
---

# Work Order: {title}

## 1. The job
What gets done and why now. Link the PRD instead of restating it.

## 2. Done means
- [ ] Each check is something you can verify.

**Proof required:** the files, links or counts the verifier will check.

## 3. In and out of scope
**In:**

**Out:**

## 4. Team and tiers
| Step | Who (team by registry name) | Tier | Why |
|---|---|---|---|

**Fallback:** a failed `light` step reruns on `full` and is logged. It never silently downgrades.

## 5. Budgets
| Budget | Planned | Hard cap | Notes |
|---|---|---|---|
| Money / new spend | | | |
| Agent time / usage | | | Estimate. Record the actual if you track it. |
| Clock time | | | |
| **Your time** | | | The budget that matters most |

## 6. Permissions
**Can read:**

**Can write:**

**Never:** publish or send, prices, live-site writes, `.campus-os/` or the plugin, unless explicitly granted here.

## 7. Approval gates
| Gate | The owner gets | The owner decides |
|---|---|---|

## 8. Stop and ask when
- Any budget hits 80%.
- The work would touch anything outside section 6.
- A decision that's the owner's to make: scope, money, public wording.

## 9. Context pack
**Read:**

**Skip:**

## 10. Outputs
| Output | Location |
|---|---|

## 11. Challenge: where this could go wrong
1. The risk, then the fix.

## 12. Decisions for the owner
Use the decision card format: one question, 2 to 3 options with the recommendation first, a default and a deadline.

## 13. Run record (fill in at close)
| | Planned | Actual |
|---|---|---|
| Money | | |
| Agent time / tokens | | *if you track it* |
| Clock time | | |
| Your time | | |
| Tiers → models used | | |
| Change orders | | |
| Done checks passed / verifier | | |
| Goal number moved | expected | observed (source) |

**Worth it?** Compare your time saved against your time spent, at what an hour of your time is worth.
**Decision:** keep / change / stop
**One lesson for next time:**
