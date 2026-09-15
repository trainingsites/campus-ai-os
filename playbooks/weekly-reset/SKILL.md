---
name: weekly-reset
description: The Monday reset — review last week, set this week's priorities, and plan the week's social in one pass. Use when the owner says "weekly reset", "run my weekly reset", "it's Monday, set me up for the week", or when a scheduled weekly task fires. A recurring, scheduled-task-compatible playbook that turns three starter employees into one habit.
---

# Playbook — Weekly Reset

**The recurring habit.** Once a week, Dean runs the same three-step reset: review the week that ended, surface this week's priorities, and plan the week's social from those priorities. It demonstrates a **recurring, scheduled-task-compatible** playbook — the same contract as the flagship, wired to a cadence trigger instead of an event.

Dean runs this. Read `playbooks/README.md` (the runtime) once before your first playbook run.

---

## The playbook contract

```yaml
playbook:
  name: "Weekly Reset"
  slug: weekly-reset
  version: "1.0.0"
  trigger:
    type: cadence          # event | cadence | manual
    on: "weekly (owner's Monday) OR on demand: 'weekly reset' / 'it's Monday'"
  goal: >                  # objective + checkable
    Three review-ready artifacts that set up the week: a weekly review of the last 7 days,
    a prioritized this-week focus list mapped to the OKRs, and a week of planned social built
    from those priorities. All saved to the run dir, run_id stamped, nothing published.
  topology: manager-helpers
  model_tier_default: full
  reads_context:
    - the resolved `goals` context
    - the resolved `brand` context
    - the resolved `voice` context
    - the resolved `icp` context
  stages:
    - n: 1
      stage: weekly-review
      skill: weekly-review
      produces: "review of the last 7 days — what shipped, what stalled, what carries over"
      model_tier: light              # summarization over the campus's own logs — safe light
      done_check: "review names last-week outcomes AND lists explicit carry-over items"
      fail_action: escalate-to-james
    - n: 2
      stage: week-priorities
      skill: morning-brief           # priorities pass, weekly scope
      produces: "this-week priority list, each item mapped to an OKR"
      model_tier: full               # owner-facing judgment (what to focus on) — pinned full
      done_check: "3-7 priorities, each tagged to an OKR from the resolved `goals` context; flags off-OKR work"
      fail_action: escalate-to-james
    - n: 3
      stage: social-plan
      skill: social-planner
      produces: "a week of planned social built from this week's priorities"
      model_tier: light              # short-form drafts run light; owner reviews before any post
      done_check: "one post slot per active platform, each tied to a this-week priority; draft-only"
      fail_action: ship-with-flag
  verification: "each stage's done_check must pass before the next starts (stage 3 may ship-with-flag)"
  stop_condition:
    done_when: "review + priorities + social plan in the run dir + results.json written"
    cost_cap: { max_passes: 2, max_minutes: 15 }   # REQUIRED runaway guard
  run_id: required
  recurring: true
  permission: draft-only          # FLOOR. No stage is granted publish.
  human_gates:
    - "The owner approves the playbook design before first run"
    - "The owner reviews the priority list + social plan before anything is scheduled"
```

---

## How Dean executes it

**1. Mint the run_id and open the run dir.**
- `run_id = weekly-reset-{YYYYMMDD-HHMMSS}`
- run dir: `outputs/{YYYY-MM}/runs/playbooks/weekly-reset/{run_id}/`

**2. Load context once** (the `reads_context` list). the resolved `goals` context is the spine — stages 2 and 3 map to it.

**3. Run the three stages in order.** For each: resolve the tier, run the skill, write `0N-{stage}.md` in the run dir, run the `done_check`, loop to `cost_cap.max_passes`, then take the `fail_action`.

- **Stage 1 — weekly-review** (light): run `weekly-review` over the last 7 days of campus logs. Check: names outcomes + lists carry-over.
- **Stage 2 — week-priorities** (full): run `morning-brief` in weekly-priority scope. 3–7 priorities, each mapped to an OKR; flag anything that maps to no OKR. Check: OKR tags present.
- **Stage 3 — social-plan** (light): run `social-planner` to build the week's social from those priorities. Check: one slot per active platform, each tied to a priority; draft-only.

**4. Stop condition + gate.** When the three artifacts + `results.json` exist, STOP. Present the priority list + social plan to the owner. Publish/schedule nothing.

**Scheduling note (recurring:true):** this playbook is scheduled-task compatible. When wired to a weekly scheduled task, the task prompt must carry the standard guards — "Never write to `inputs/`" and "draft-only; stop at the human gate." The scheduled run produces the same run dir + `results.json`; the owner reviews on Monday.

**Tier note:** light stages run on the lighter engine from `.campus-os/model-routing.md`; the judgment stage (2, priorities) is pinned `full`. The ledger records `tier_requested`/`tier_used` per stage.
