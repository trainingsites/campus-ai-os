# Playbooks — the runtime home

**What this folder is:** the home for Campus AI OS *playbooks* — the runbooks Dean follows to point employees + tools at a goal and keep going until the output passes a check. They make a playbook *runnable* instead of just a description.

**Registry shape:** `.campus-os/registration-block-spec.md`. `model_tier` is an optional additive extension documented here.

---

## What a playbook is

A playbook is a `SKILL.md` folder carrying a `playbook:` contract block (socket spec Part 1). It declares, in order:

- **trigger** — event / cadence / manual, and the phrase or condition that fires it
- **goal** — objective and checkable ("make it good" is banned)
- **topology** — solo / maker-checker / manager-helpers (a full waterfall is manager-helpers; Dean is the manager)
- **stages** — the ordered waterfall; each stage names the employee/skill, what it `produces`, its one-line `done_check`, and (optionally) its `model_tier`
- **verification** — each stage's `done_check` must pass before the next starts
- **stop_condition** — `done_when` + a required `cost_cap` (runaway guard — a non-technical buyer must never be able to start a 12-hour loop)
- **run_id: required** — minted at run start, threaded through every stage, stamped on every output and ledger line
- **human_gates** — where Dean stops for the owner

A playbook is registered in `.campus-os/registry.json` → `playbooks[]` so Dean can find and route to it.

---

## How Dean runs a playbook

1. **Route in.** Before any compound / multi-team job, Dean checks `playbooks[]` in the registry. If a registered playbook matches the request, Dean runs it instead of improvising. (See the Dean routing rule in `dean/{ENTRY_FILE}`.)
2. **Mint the run_id.** Format: `{playbook-slug}-{YYYYMMDD-HHMMSS}` (e.g. `one-recording-20260706-235500`). One run_id per run, threaded end to end.
3. **Open the run dir.** `outputs/{YYYY-MM}/runs/playbooks/{playbook-slug}/{run_id}/`. Every stage output lands here; `results.json` is written here at the end.
4. **Run the stages in order.** For each stage: resolve its model tier (see below), run the named skill/employee, capture the output into the run dir, then run the stage's `done_check`. A generative stage does not hand off until its done-check passes. Loop up to `cost_cap.max_passes`; if it still fails, take the stage's `fail_action` (default: escalate to the nearest human gate — never ship slop, never silently halt).
5. **Respect the cost cap.** Stop the run if `max_passes` or `max_minutes` is exceeded across the run; escalate to the owner.
6. **Stop at human gates.** Draft-only is the floor. A stage may publish only if the playbook grants it that stage explicitly *and* the owner approved the design — pull a stage out of its approved playbook and it falls back to draft.
7. **Write `results.json` + ledger lines.** Interop schema (below) to the run dir; one activity-ledger line per stage to `dean/.activity.jsonl`, each carrying `run_id`, `tier_requested`, `tier_used`.

---

## run_id + run-dir convention

```
outputs/{YYYY-MM}/runs/playbooks/{playbook-slug}/{run_id}/
├── results.json            ← interop schema 1.0 (run manifest)
├── 01-{stage-slug}.md      ← stage output
├── 02-{stage-slug}.md
└── ...
```

**`results.json` shape** (interop v1.0, additive `stages[]`):

```json
{
  "schema_version": "1.0",
  "run_id": "one-recording-20260706-235500",
  "playbook": "one-recording-to-a-week-of-content",
  "generated_at": "2026-07-06T23:55:00-04:00",
  "goal_met": true,
  "stages": [
    {
      "n": 1, "stage": "extract-brief", "skill": "content-repurposer",
      "produces": "content brief", "model_tier": "light",
      "tier_requested": "light", "tier_used": "light",
      "done_check": "brief names >=3 usable angles", "done_check_passed": true,
      "passes": 1, "asset": "01-extract-brief.md"
    }
  ],
  "assets": [
    {
      "type": "brief", "path": "01-extract-brief.md",
      "status": "draft", "external_ref": null
    },
    { "type": "social-post", "path": "04-social-posts.md", "status": "draft", "external_ref": null }
  ],
  "permission": "draft-only",

  "outcome": {
    "target": "20 replies from the 400-person list",
    "acceptance": "FluentCRM campaign reply count for this send, read 14 days after send"
  }
}
```

### `assets[]` — objects, never bare strings (corrected v5.1.1)

Each asset is an **object**, not a filename string:

| Field | Required | Holds |
|---|---|---|
| `path` | yes | the file, relative to the run dir |
| `type` | yes | what it is (`brief`, `article`, `email`, `social-post`, …) — free-form |
| `status` | yes | one of `draft` \| `published` \| `local` \| `scheduled` \| `sent` |
| `external_ref` | when status is `published`/`scheduled`/`sent` | the opaque stable handle (content id, campaign id, canonical URL) that makes the asset re-findable. `null` while draft or local — **absent is honest, never a failure** |
| `completion` | optional | the self-report done-check signal (Interop v1.1 completion-only line) |

⚠️ **This was a real contract split, and it is exactly the defect class this
release is named for — sitting inside the release's own runtime.** Until
v5.1.1 this file emitted `"assets": ["01-extract-brief.md"]` — bare strings —
while the READER schema (`skills/outcome-reporter/references/rollup-schema.md`)
specified the object form with `status`, `external_ref`, and `completion`, and
has since Interop v1. **One artifact, two shapes, one writer and one reader that
never agreed.** It was reported after the Codex `weekly-reset` run (S222) and
deferred twice as "minor" on the grounds that run-level `permission:
draft-only` conveys the same thing in practice — which is true only while every
asset in a run shares one status, and stops being true the moment a playbook
publishes anything.

**Build-gate check 17 now fails the build if the emitter and the reader
disagree about this shape**, because a parity check between two hand-maintained
contracts is precisely what this release keeps replacing with one owner plus a
loud check.

### `outcome` — RESERVED, OPTIONAL, and INERT in v5.1

`outcome` is the one reserved field on this schema. **It has no consumer, no
check, and no report in v5.1.** Nothing reads it, nothing grades it, nothing
fails without it. It is written now because it is the only fact in this system
that cannot be backfilled: a prediction recorded after the outcome is known is
not a prediction.

**Canonical key: `outcome`, with exactly two subfields, `target` and
`acceptance`.** These words are taken deliberately from the executable-
capability mission contract (`outcome.target` + `acceptance`) so the kernel and
that program share one vocabulary. **Do not introduce a second spelling** —
not `prediction`, not `forecast`, not `expected`, not `goal`. One fact, one
name. If this schema and that program ever disagree on the word, the fix is to
reconcile them, never to carry both.

| Subfield | Holds |
|---|---|
| `target` | what the run was for, stated as a specific claim, **before** committing |
| `acceptance` | the deterministic query that settles it — the tool, the number, the date |

> ⚠️ **Name collision, recorded deliberately.** The activity ledger already has a
> field called `outcome`, and it means something else there: a status enum
> (`completed` | `errored` | `abandoned`) describing whether a stage ran. This
> `outcome` is an object on `results.json` describing what the run was *for*.
> **Two artifacts, same word, different facts** — the same shape as the
> `MANIFEST_PATH` / run-`MANIFEST` collision caught during the v5.0.4 interop
> pass and fixed by renaming. It is kept here only because `outcome.target` +
> `acceptance` is the governing research vocabulary and inventing a synonym
> would be worse. **Never merge or cross-read the two.** If the Phase 1
> alignment reopens the naming, this is the first thing to revisit.

**When it gets written.** The **stakes gate is the prediction gate.** The
Challenge-First rule already separates decisions from routine work: if a run is
worth pushing back on before it happens, it is worth going on record about. A
routine run ships silently with no `outcome` and that is correct — most runs
are not decisions, and an absent `outcome` is never a failure.

**`acceptance` is not optional prose.** A target with no query attached is a
sentence, not a prediction. If the settling query cannot be written at act-time,
do not write a `target` either — write nothing.

**Deliberately NOT built, and why:**

- **No resolution step, no hit/miss bucketing, no score or accuracy
  percentage.** A gamified capability score is forbidden by the governing
  research (§18.13), and the reasoning transfers directly to an orchestrator
  accuracy number. Graded predictions select for hedged, unfalsifiable,
  low-variance calls — an instrument that punishes courage.
- **The orchestrator must never grade itself.** §19.5: the executing agent does
  not issue its own capability verdict. When resolution is eventually built, it
  reads from a deterministic connector query — never from the orchestrator's
  own judgment.
- **Two open questions gate any consumer.** (1) Are outcomes attributable to
  campus actions at all? Unresolved, and load-bearing — if they are not,
  evaluation manufactures false confidence. (2) The Phase 1 vocabulary
  alignment. **Resolve both before anything reads this field.**

**Ledger line per stage** (extends the fixed ledger format additively with two Seam-B fields). Write each line in **compact JSON** (house style, no spaces after `:`/`,`) and **stamp `ts` at the moment that stage completes** — not retroactively at the end of the run. Per-stage timestamps make the tier split visible (you can see light stages finishing faster than full ones).

```json
{"ts":"...","session":"S###","skill":"content-repurposer","trigger":"one-recording-to-a-week-of-content stage 1","dept":"marketing","outcome":"completed","files_touched":1,"run_id":"one-recording-20260706-235500","tier_requested":"light","tier_used":"light"}
```

---

## Model tiers (additive, optional)

Each stage MAY declare `model_tier: light | full`. **Absent = `full`.** Quality never degrades silently — light is always an explicit per-stage opt-in.

- **Resolution order:** stage `model_tier` → playbook header `model_tier_default` → policy file default → `full`. First hit wins.
- **Pin rules (non-negotiable):** any stage whose output involves **voice-carrying copy, publishing, money, or owner-facing judgment** runs `full` regardless of what the contract says. The owner can add pins, never remove the publish pin.
- **Fallback = escalate, never degrade:** if the light engine is unavailable or errors, the stage runs `full` and the escalation is logged. Never the reverse.
- **Ledger proof:** every stage line carries `tier_requested` and `tier_used`, stamped at that stage's completion (per-stage timestamps).

**Resolution order (first hit wins):** stage `model_tier` → playbook `model_tier_default` → policy file default → `full`. A stage that resolves to `light` but matches a pin is forced to `full`.

**Fallback = escalate, never degrade:** if the light engine is unavailable or errors, the stage runs `full` and the ledger line records `tier_requested: light`, `tier_used: full`, `escalated: true`, `escalation_reason`. Never the reverse; never skip.

**Model tiers are honored.** The policy file `.campus-os/model-routing.md` maps `light` to a lighter engine (default `subagent-haiku` — a Haiku subagent does the stage's work and returns it); full/pinned stages run on the session's primary model, and the ledger shows a real `tier_used` split. The four pins (voice-carrying copy, publishing, money, owner-facing judgment) always force `full`; the **publish pin is non-removable**.

---

## Canon playbooks in the box

| Playbook | Trigger | Stages | Recurring |
|---|---|---|---|
| [One Recording → A Week of Content](one-recording-to-a-week-of-content/SKILL.md) | drop a recording/transcript in `inputs/`, "turn this into a week of content" | 6 | no |
| [Weekly Reset](weekly-reset/SKILL.md) | "weekly reset", "it's Monday", scheduled weekly | 3 | yes |

Both are base-only runnable: starter employees only, no paid teams, no connectors required, draft-first.

---

*Part of Campus AI OS v4 — the playbooks runtime.*
