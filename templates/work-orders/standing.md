---
wo_id: WO-YYYY-MM-DD-NN
title: "Standing: {job name}"
size: standing
status: draft                      # a cache — events are the truth
owner: "the owner"
signed_by: ""                      # the owner signs a standing order once
method: "scheduled/{job}.md"       # the job definition — never copied here
dept: ""
goal: ""
approval_scope: draft-only         # most standing jobs stay draft-only or create-drafts
runs_on: ""                        # the clock-owner seat (python3 -I -B .campus-os/resolve-seat.py --client <this app> → owns_clock)
cadence: ""                        # e.g. "daily 02:00" — must match the job's registration
tiers: {}
verifier: ""                       # e.g. "weekly: the chief of staff reads run outputs"
budget: { per_run_agent_minutes: 0, per_week_your_minutes: 0, money_usd: 0 }
stop_rules:
  - "5 empty runs in a row → pause and ask"   # define 'empty' below
  - "2 failed runs in a row → pause and ask"
  - "any run over 2x per_run_agent_minutes → flag"
state: "Drafted. Next: the owner signs once."
created: YYYY-MM-DD
---

# Standing Work Order: {job name}

1. **What it does:** one sentence. Point to `method` and don't restate the steps.
2. **What counts as a run:** the job's own record and the `run` events in the seat logs.
3. **What counts as an *empty* run:** e.g. "nothing new pulled", "0 drafts created".
4. **What counts as a *failed* run:** e.g. "connector declined", "no output file".
5. **Who runs it:** only the `runs_on` seat, the clock owner.
6. **Can use / can't touch:** permissions for every run.
7. **Deliver to:** where each run's output lands.
8. **When a stop rule fires:** the job pauses itself and writes a `blocked` event with the reason. The chief of staff raises a decision card: change the source / change the job / retire it.
9. **Review:** once a month, or when a stop rule fires. Keep / change / retire.

**Signed:** the owner, date.
