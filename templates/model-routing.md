# Model Routing Policy — Campus AI OS v4

*Kernel-native routing policy. Honored by the playbooks runtime via per-stage `model_tier` keys. Owner-editable — but the publish pin below cannot be removed.*

**What this file does:** it tells the playbook runtime which model tier runs each stage. A stage may run on a **lighter worker** (faster, cheaper) for routine work, while judgment, voice, publishing, and money stay on the **full** model. Absence of everything = today's behavior (all `full`).

---

## Tiers on THIS install

| Tier | What it maps to | Availability |
|---|---|---|
| `full` | The session's primary model (the one you're talking to now) | Always available — needs no config |
| `light` | A cheaper engine, in preference order: **`subagent-haiku`** → local model *(only if detected + explicitly enabled)* | Working default: `subagent-haiku` |

**Working default:** `light: subagent-haiku` (a Haiku subagent does the stage's work and returns it for the run).

**Local model:** detect-only, **off by default**. A local endpoint may be noted here as an inert `local_available` flag; enabling it as a `light` target is an explicit owner edit. *(If a local endpoint is detected on your machine, it can be noted here as an inert flag — left OFF by default: `local_available: false`, `local_enabled: false`.)*

---

## The pins (non-negotiable — enforced by the runtime)

Any stage whose output involves one of these **always runs `full`**, regardless of what the playbook contract or this policy says:

1. **voice-carrying copy** — anything written in the owner's brand voice that a reader will see as the owner's words
2. **publishing** — anything that posts, sends, or goes live  🔒 **NON-REMOVABLE** (this pin cannot be deleted by any edit; it is the safety floor)
3. **money** — pricing, charging, checkout, anything touching a transaction
4. **owner-facing judgment** — prioritization, recommendations, decisions the owner acts on

The owner MAY add pins. The owner may NOT remove the **publish** pin. `permission: draft-only` is orthogonal and unchanged — a stage can be pinned `full` and still be draft-only.

---

## Resolution order (first hit wins)

1. Stage's own `model_tier` (in the playbook `loop:` contract)
2. Playbook header `model_tier_default`
3. This policy file's default
4. `full`

A stage that resolves to `light` but matches a pin above is forced to `full`.

## Fallback = escalate, never degrade

If the light engine is unavailable or errors, the stage **runs `full`** and the escalation is **logged** (ledger line carries `tier_requested: light`, `tier_used: full`, `escalated: true`, `escalation_reason: ...`). Never the reverse; never skip a stage; never silently degrade quality.

## Ledger proof

Every playbook stage line in `dean/.activity.jsonl` carries `tier_requested` and `tier_used`, stamped at that stage's completion (per-stage timestamps). A real routed run shows `tier_used: light` on the light stages and `full` on the pinned/full stages.

---

## Job-type → tier map (default)

| Job type | Tier | Why |
|---|---|---|
| extract / summarize / analyze a source | `light` | routine, no voice, owner reviews downstream |
| classify / sort / triage | `light` | mechanical |
| short-form draft (social, discussion starter) | `light` | draft-only, owner reviews before any post |
| package / assemble a run summary | `light` | mechanical composition |
| long-form voice copy (articles, core pieces) | `full` 🔒 voice pin | reader sees it as the owner's words |
| email / send copy | `full` 🔒 voice + publish pins | owner-facing send |
| pricing / offer / checkout copy | `full` 🔒 money pin | transactional |
| prioritization / recommendations | `full` 🔒 judgment pin | owner acts on it |
| anything that publishes/sends/charges | `full` 🔒 publish pin (non-removable) | safety floor |
