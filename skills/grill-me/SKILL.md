---
name: grill-me
description: >
  Deep-extraction interview for the Strategy and Research Team (Atlas). Relentlessly
  interviews the user one question at a time until everything in their head about a
  process, offer, decision, or whole business is captured as reusable context — then
  persists it via session-capture. Use for /atlas-grill, "grill me", "grill me about X",
  "interview me on", "extract everything about", "I want to brain-dump", "understand my
  whole {business/process/offer}".
version: 1.0.0
department: dean-office
---

# grill-me — interview me until there are no gaps

The extraction engine for the business-memory moat. Where the council *converges one idea to a choice*, grill-me does the opposite: **exhaustively pulls what's in your head into structured, reusable context.** Adapted from Matt Pocock's grill-me; capture pattern per Nate Herk.

## CRITICAL DIRECTIVES
- **One question at a time. Ask → get the answer → ask the next. Never batch, never form-dump.**
- **For each question, offer your recommended answer** the user can accept or override (lowers effort, speeds the grill).
- **Context-first — collect as much as possible, ask as little as needed.** Before asking, check what's already known (resolved `shared/*` via `CONTEXT_CANON` (`.campus-os/context-files.md`, else the plugin's `templates/context-files.md`), the `wiki/` index, `dean/memory.md`, connected tools). If the answer is already on file, **state it and confirm** instead of asking cold.
- **Relentless until shared understanding.** Keep going (5 questions or 50) walking each branch of the decision tree, resolving dependencies in order, until there are no holes. Propose when you think it's complete; **the user decides when to stop.**
- **Never fabricate. Flag instead.** When the user doesn't know something (it lives with another person/tool/file), record an **open flag** ("get X from Y, then re-grill") rather than guessing.
- Tool-agnostic; zero hardcoded paths.

## Step 1 — Frame the target
Name what we're extracting (a process, an offer, a launch, "the whole business"). Inherit the `run_id` if one exists (council/brief); else have the orchestrator mint one. Immediately call `session-capture` to open the Tier-1 log so nothing is lost from question one.

## Step 2 — Explore before asking
Pull everything already captured on this target from resolved context, wiki, memory, and connected tools. Summarize what you already know back to the user and confirm it. Only the gaps become questions.

## Step 3 — Grill the decision tree
Walk branch by branch. One question, your recommended answer, their response. **After every answer, checkpoint to the Tier-1 log via `session-capture`** (discovery notes · key decisions · Q&A log · open flags). Follow dependencies — don't jump randomly. Surface open flags as they arise.

## Step 4 — Confirm completion
When branches bottom out and you and the user share the same understanding, say so and ask to wrap. If gaps remain that only an external source can fill, list the open flags and what to fetch.

## Step 5 — Persist + route (via session-capture)
Trigger the Tier-2 twin: the distilled **wiki entry** + the **`context-record.json`** (gate fields default `private`/`internal`) + manifest upsert. Then **offer** to route confirmed facts to their canonical homes (`icp.md`, `offers.md`, the manager's own entry file — resolve `ENTRY_FILE` per `PLATFORM.md`, never assume a filename) and to update any skill/doc the grill exposed as thin (e.g., "your packaging skill is missing this nuance — update it?"). Offer and wait — never auto-apply.

## Re-grill
"Grill me again on {slug} — here's what changed" loads the prior log + record and **extends** it (version bumped), never starts cold.
