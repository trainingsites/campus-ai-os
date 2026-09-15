# The Strategy Council — voices, guest seat, and the convener

A formal multi-voice brainstorm run **out loud** across the five gates in `SKILL.md`. One topic in; each voice states a position, the room deliberates at The Table, and the convener rules — one decision PLUS the surviving dissent — never a single flat answer, never a hidden internal pass.

## Real argument vs. theater — the quality bar

Cross-examination at The Table is **required**, not optional. A valid challenge **cites a real assumption, number, or audience truth** and **could change the outcome**. Banned: fake conflict, restating a position louder, disagreement for flavor, or celebrity cosplay. Real disagreement that moves the decision is the product; decorative disagreement is the failure mode.

## The core council (fixed — guarantees coverage)

| Voice | Job | Core question |
|---|---|---|
| The Customer | keep it audience-true | "Does the 45+ buyer actually care? Say it in their words." |
| The Skeptic | kill weak ideas early | "Why won't this work? What's the obvious objection?" |
| The Contrarian / Red-team | break groupthink | "What's the opposite take? Where is everyone wrong?" |
| The Numbers | force outcome-thinking | "What result proves this worked? Is it measurable?" |
| The Brand Voice | keep it on-message | "Does this fit Campus AI OS / the current offer? Tie to a goal." |

These are **functional roles** — keep them seated so a blind spot can't slip through. They are configurable in `atlas/config/niche.md` (add/remove/rename), but the default five always run unless the user changed them.

## The guest seat (optional — the famous-thinker lens)

One **optional** seat added on top of the fixed five to inject a *distinct heuristic* the core voices lack — jobs-to-be-done, the value equation, permission marketing, blue-ocean, etc. This is what produces sharper dissent instead of five blurred "smart advisor" takes.

**Lens, not impersonation — hard rule.** The guest argues *from the framework*, never as the person.
- ✅ "Through a jobs-to-be-done lens, your buyer isn't hiring a video — they're hiring a way to stop feeling behind."
- ❌ "Hi, I'm Clay Christensen, and I think…"

No fabricated quotes, no celebrity cosplay. The heuristic is the value.

**How the seat is filled (at Gate 1):**
- **User names it** — "seat a value-equation lens on this offer."
- **Atlas infers it** — recognize the underlying decision type and *propose* a guest: "this is really a pricing-perception question; want a value-equation lens seated for this one?" The user **approves before it joins.**

**Constraints:** opt-in and gated, never auto-seated silently · **max one or two guests** per session (a scalpel, not a crowd) · favorite lenses persist in `atlas/config/niche.md`.

## Council engine (v2) — sub-agents + convener, two rounds

1. **Opening round (fan-out):** spin up one sub-agent per seated voice (core five + any guest) with a lens-briefing prompt + the framed idea + resolved context (audience/offers/goals/voice). Run in parallel — each produces its opening take.
2. **Table round:** feed every voice's opening take back to the voices; each sub-agent must produce **rebuttals to named others** (real challenges only — see the quality bar above) and may revise its own position. Cap rebuttals so the Table stays sharp: each voice challenges 1–2 others, not all four — depth over volume.
3. **Fan-in (convener):** the convener reads the opening takes **and the rebuttals**, states the **ruling** (winning position + the argument that beat the rest + the surviving named dissent — dissent is never averaged away), and runs the Gate-4 judgment beats.

- **Degrade path:** if sub-agents aren't available, run opening takes then rebuttals **sequentially and visibly** (still gated, still out-loud). Never collapse to a silent single pass.

## Gate-4 judgment beats

- **Propose alternatives:** surface 1–2 *materially different* strategic paths the user didn't bring, each with its reasoning. Evaluated alternatives, **not** an idea list — cap at two.
- **Steelman + premortem:** make the strongest case for the path being rejected, then run a 90-day premortem on the front-runner ("if this flops, why?"). One short paragraph each.

## Output shape (strategy-brief.md, written only at Gate 5)
Add `artifact_type: strategy-decision` to the frontmatter/JSON. Keep the filename `strategy-brief.md` for downstream compatibility; the content is now a decision, not a menu.
- **The decision / ruling** (1–3 sentences) — the position that won.
- **The argument that produced it** — why it beat the alternatives (from The Table).
- **Surviving dissent** — the strongest objection that lost but still stands, named, as the risk to watch.
- **Alternatives considered** — the 1–2 proposed paths + why not.
- **Premortem** — the top failure mode.
- **Research mandate** (mandate.json): `hunt_for[]`, `avoid[]`, `weight_shifts{}`.
- Council PROPOSES; human APPROVES. The ratify gate is the trust feature.
