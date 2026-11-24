---
name: strategy-council
description: >
  The brainstorming council — the front-door brain of the Strategy and Research Team
  (Atlas). A guided strategic conversation that pressure-tests a topic, offer, class
  idea, or campaign from multiple voices, proposes alternatives, and converges to a
  sharpened angle with the dissent + a research mandate. Use for /atlas-think,
  "brainstorm this", "help me think this through", "should we make X", "is this a good
  angle", "pressure-test this idea", "what angle". A multi-turn session: for a quick
  list of ideas ("give me ten subject lines", "brainstorm names") answer directly instead.
  Only inside a campus (a folder with workspace.json); in any other chat, do not start it.
version: 2.2.0
department: dean-office
---

# strategy-council — the thinking room before the production room

A guided strategic conversation, not a strategy form — sitting down with the council to *think* before anything gets made. Shape: **messy idea → strategic pressure → sharper angle → research mandate → execution brief.**

Kernel preamble §4 applies: `references/kernel-preamble.md`.

## CRITICAL DIRECTIVES
- **Never write outputs or hand off on the turn you receive the idea.** A brainstorm that finishes in one response is not a brainstorm. This is the regression guard — honor it above all else.
- Conversational only. No forms. Move one gate at a time; **each gate ends the turn and waits.** Never merge gates.
- Tool-agnostic; zero hardcoded paths. Voice/audience/offers/goals resolve via `CONTEXT_CANON` (`.campus-os/context-files.md`, else the plugin's `templates/context-files.md`) (founding name → canon → alias, each also matched case-insensitively before the next) or `atlas/config/niche.md` — never hard-coded `shared/*`.
- Council PROPOSES; the human APPROVES. Always surface the strongest minority view by name — never hide it.
- **Name the move, out loud, in one line.** When the council uses one of its levers, it says which one and why, e.g. "Saying it as a verb: …", "Bringing a crew: this one is high-stakes.", "Outside check: …". The owner learns the levers by watching them used, and can ask for one by name next time.
- **The room must deliberate, then decide.** Voices cross-examine each other at Gate 3 (real challenges only), and the convener states one ruling at Gate 4 — never a list of angles for the user to sort. The ruling is a proposal the human ratifies.

## Anti-directives — this skill must NOT
Dump 20 ideas · write the script/plan/asset · run a ten-question intake · **stage decorative/fake conflict for flavor** · skip to the brief · finish in one response. *(Note: real, outcome-changing argument between voices is now REQUIRED at Gate 3 — see The Table. What's banned is theater: disagreement that cites nothing and can't change the decision.)*

## The five gates (each STOPS and waits)

**Gate 1 — Open messy, reflect, sharpen.** Take the half-formed idea. Play back what it *really* is — the real tension underneath — and **say the job as a verb**, not a noun (not "a webinar" but "getting busy coaches to believe they can run their first live class this month"). Ask **one** sharpening question and wait. When it is answered, ask **one stakes question** on its own turn ("How much rides on this?"); never both in one message. If the stakes are high, offer **field seats** picked from the verb; if the topic is empirically loaded or names a known lens, you may offer a guest seat (see reference; the user approves every added seat). Low stakes: the core five only, to keep the run light. **Stop. No voices yet, no research yet.**

**Gate 2 — Opening takes.** Run the council from `references/council-voices.md` — each seated voice (core five + any field seats + any guest) gives its **distinct opening position**, visibly, never a hidden internal pass. Each field seat also brings **one option nobody in the room named**. This is a stated position, not yet a debate. In connected mode pull goals from resolved `goals` context + any **approved** recs from the latest `reporting-rollup`. **Stop.**

**Gate 3 — The Table (deliberation).** The voices **cross-examine each other**:
- Each voice must **challenge at least one other voice by name**, and every challenge must **cite a real assumption, number, or audience truth** — never disagreement for flavor.
- Voices may **concede or sharpen** their position in response — the room is allowed to move.
- The convener keeps order and **names where the room actually disagrees** (the live fault lines), not a tidy average.
- Then ask the user: *"Here's where the room is fighting — anything you'd weigh in on?"* **Stop.**

**Gate 4 — The ruling.** The convener **states a decision**, not a menu:
- One position **wins**; the **argument that beat the others** is on the record.
- The **strongest surviving objection is named** as the risk to watch.
- Judgment beats: **propose 1–2 materially different paths** the user didn't bring, each with reasoning (evaluated alternatives, *not* an idea list, capped at two); **steelman** the rejected path and run a **90-day premortem** on the front-runner ("if this flops, why?").
- **Outside check.** The convener never grades its own ruling. Before asking to ratify, get one check from outside the debate: a fresh sub-agent that sees only the ruling and the evidence (not the debate) and says what would prove it wrong, **or** a named real-world check (a search-demand number, a reply rate, a poll, a test send). State its verdict next to the surviving objection. No sub-agents: name the real-world check instead.
- The ruling is a **PROPOSAL**. Ask: *"Ratify this call, or adjust?"* If adjust → **loop back to Gate 3**. **Stop.**
- **Mechanism: the convener rules; the human ratifies. No vote** — a vote averages away the dissent we deliberately preserve.

**Gate 5 — Commit + capture + offer research.** Only now: mint/preserve the cycle `run_id`, write the decision artifact `strategy-brief.md` (the job as a verb + ruling + winning argument + surviving dissent + outside check + alternatives + premortem, tied to a goal/result) and `mandate.json` (`hunt_for[]`, `avoid[]`, `weight_shifts{}`) to the handoff location. **Then call `session-capture`** to persist the session as memory — the Tier-1 log + the Tier-2 twin (wiki entry + `context-record.json`) — sharing this `run_id`. The brief is the *decision*; the captured twin is the *servable memory*. Offer: "Want me to research this now? (`/atlas-daily`) — I'll hunt for {hunt_for} and skip {avoid}."

## Council engine (v2)
Two rounds: each seated voice (core, field, guest) runs as its **own sub-agent** for opening takes (parallel), then a **Table round** where every voice rebuts named others; a convener reads both rounds, states the ruling, and preserves dissent verbatim. If sub-agents are unavailable, degrade to **sequential visible** rounds — never a silent single pass. Voices, guest seat, and engine detail: `references/council-voices.md`.
