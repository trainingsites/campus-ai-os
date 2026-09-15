---
name: session-capture
description: >
  Persists a strategy or grill session into durable, queryable business memory for the
  Strategy and Research Team (Atlas). Writes a raw running log during the session
  (checkpointed after every answer) and, on completion, a distilled human+machine twin
  (wiki entry + context-record.json) registered in a manifest. Internal skill, called by
  grill-me and strategy-council. The Tier-2 layer is the surface a future MCP-gated
  context service reads.
version: 1.0.0
department: kernel
---

# session-capture — two-tier memory writer

Turns a session into compounding, sellable context. **Two physically separate tiers** — never mix them.

## CRITICAL DIRECTIVES
- **Tier 1 = private factory; Tier 2 = servable product.** Raw logs are never registered as servable. Distilled records carry gate fields.
- **Checkpoint Tier 1 after EVERY answer** — not only at the end. This guards long sessions against context loss.
- **Default Tier-2 `shareable: private`, `gate_tier: internal`** for extracted business knowledge unless the user explicitly marks it shareable. Protects the moat; prevents accidental leaks.
- Tool-agnostic; zero hardcoded paths. Context homes resolve via `CONTEXT_CANON` (`.campus-os/context-files.md`, else the plugin's `templates/context-files.md`) (canon). Use `references/context-record-schema.md` exactly — never fork it.

## Tier 1 — raw running log (during the session)
Write/append to `{campus_root}/strategy-sessions/{YYYY-MM-DD}-{slug}/session-log.md`, where `campus_root` is the directory holding `workspace.json` (fall back to `./strategy-sessions/{...}` if the campus is not founded). Never hard-code a campus folder name. After each answer, append the Q&A pair and refresh the running sections: **discovery notes · key decisions · full Q&A log · open flags**. Stamp the `run_id` (inherit from the orchestrator/council/brief; never re-mint). Marked `private` — this file is the audit trail and the re-grill source; it is never exposed by the future service.

## Tier 2 — distilled twin (on completion)
Write BOTH, per `references/context-record-schema.md`:

1. **Human — wiki entry.** Follow the host `wiki/OPERATIONS.md` conventions (resolve the wiki dir via canon; do not hard-code): pick the page type, write *what was learned* (not a play-by-play), update `wiki/index.md`, append `wiki/log.md`. Cross-check the YT-Wiki index before creating. Link to the Tier-1 `session-log.md`.
2. **Machine — `context-record.json`.** The structured twin a future MCP server serves. Required: `schema_version`, `id` (`ctx-{slug}-{4char}`), `run_id`, `slug`, `type`, `title`, `summary`, `fields{}` (canonical field keys), `shareable`, `gate_tier`, `provenance`, `version`, `created`, `updated`, `raw_log_ref`. Write to the Tier-2 records dir: `{campus_root}/context-records/` (fall back to `./teams-shared/context-records/` if the campus is not founded).
3. **Manifest.** Upsert the record's catalogue entry into `context-records/context-index.json` (create if absent). This is the future service's catalogue — keep it current.

## Routing extracted facts (offer, then confirm)
Offer to route confirmed facts to their canonical homes (`icp.md`, `offers.md`, the manager's own entry file — resolve `ENTRY_FILE` per `PLATFORM.md`, never assume a filename — etc., per the campus orchestrator's memory routing rules) and to update any skill/doc the session exposed as thin. These are real edits to context files — **offer and wait for "yes," never auto-apply.**

## Re-capture
If a record/log already exists for the slug, **extend** it: append to the Tier-1 log, refresh the wiki entry, bump `version`, update `updated`. Never start cold, never duplicate the slug.

## Degrade path
No wiki layer present → still write `context-record.json` + `context-index.json` (the MCP-ready layer must not depend on a wiki) plus a plain `notes.md` in the session folder in place of the wiki entry.
