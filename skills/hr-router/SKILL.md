---
name: hr-router
description: Set up Lite mode - a routing policy so routine steps run on a lighter engine while judgment, voice, and anything published stay on the full model. Kernel HR skill, optional and advanced. Use for 'set up Lite mode', 'run things lighter', 'model routing', or /hr-router. Writes an owner-approved policy; never rewires other teams. Local-model offload appears only if a local endpoint is detected, and is off by default. Department: dean.
department: kernel
---

# hr-router (kernel)

**One job:** write a clear, owner-approved policy for which job types run on a lighter worker, and
record whether a local model is available to offload to. A *policy artifact*, not an automatic
rewiring of the workforce.

## Model routing note

In Campus AI OS v4 the routing policy is **kernel-native**: the file is `.campus-os/model-routing.md`
and it is honored by the playbook runtime via per-stage `model_tier` keys (resolution order: stage
`model_tier` → playbook `model_tier_default` → this policy file → `full`). This skill writes and
updates that policy; the playbook runtime reads it and records `tier_requested`/`tier_used` per stage.

## CRITICAL DIRECTIVES
- **Optional + advanced.** Most owners never need this. Offer it; never push it. Lead with **speed +
  staying within limits**, NEVER cost savings.
- **The split is a hard rule (the pins, non-negotiable).** Summarize / sort / classify / extract /
  rough-draft may go to the lighter worker; **voice-carrying copy, publishing, money, and owner-facing
  judgment always stay on the full model**, and a lighter worker's draft never goes live untouched.
  The owner may add pins, never remove the publish pin.
- **Fallback = escalate, never degrade.** If the light engine is down or missing, the stage runs full
  and the escalation is logged. Never the reverse; never skip.
- **Local offload is detection-gated and silent.** It appears ONLY if a local endpoint is detected;
  if none is found, never mention it. Enabling it is an explicit owner edit.
- **Policy, not rewiring.** HR writes the rule; the owner turns it on.

## Run procedure

**1. Detect tiers.** Check whether the stack exposes more than one model tier. If only one exists, say
Lite mode isn't available on this machine — don't fake it. Probe for a local model endpoint; found →
note `local_available: true` once; not found → stay silent.

**2. Build the job-type → tier map** from the hard-rule table (routine middle-layer → light; all
judgment/voice/publish → full). Show it to the owner.

**3. Carry the scheduled-runtime caveat.** A local endpoint reachable interactively may be unreachable
in a scheduled run; scheduled runs do local preprocessing via a small native pre-processor, and every
offload step degrades to full inline if the lighter worker is down — it never fails the run.

**4. Write the policy.** Write `.campus-os/model-routing.md` (kernel path) with: the four default pins
(voice / publish / money / owner-judgment = full), the job-type → tier map, and `light:
subagent-haiku` as the working default. **Get the owner's explicit go before enabling Lite mode** —
turning it on is the owner's call.

**5. Emit the back socket.** Append a `model-routing` asset to `results.json` (draft, carrying
`run_id`). Done-check = `policy-present` (the file exists and names a tier for every job type).

## Boundaries
HR writes the routing rule; the owner approves and enables it. Changes no other team's configuration.
Degrades cleanly: no second tier → Lite mode simply unavailable; no local endpoint → offload invisible.
Tool-agnostic — names a "local model endpoint" as a detection target, never a specific vendor.
