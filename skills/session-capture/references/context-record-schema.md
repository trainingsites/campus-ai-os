# context-record schema + manifest (Tier-2, MCP-ready)

The Tier-2 layer is the **only** surface a future MCP-gated context service exposes. It mirrors Atlas's existing human+machine twin pattern (brief.md / brief.json). Tier-1 raw logs are never part of this layer.

## `context-record.json` — one per distilled session/item

```json
{
  "schema_version": "1.0",
  "id": "ctx-{slug}-{4char}",
  "run_id": "{shared with brief/council when present, else minted by orchestrator}",
  "slug": "string (lowercase-hyphenated, ≤60)",
  "type": "process | business-knowledge | offer | audience | decision",
  "title": "string",
  "summary": "1–3 sentences — what this record holds",
  "fields": { "...canonical field keys per CONTEXT_CANON (.campus-os/context-files.md, else templates/context-files.md)..." },
  "open_flags": ["string — what's still unknown / who to ask"],
  "shareable": "public | licensed | private",
  "gate_tier": "free | paid | internal",
  "provenance": "grill-me | strategy-council | wiki-ingest",
  "version": 1,
  "created": "ISO 8601",
  "updated": "ISO 8601",
  "wiki_ref": "{path to the distilled wiki entry, or notes.md in degrade mode}",
  "raw_log_ref": "strategy-sessions/{YYYY-MM-DD}-{slug}/session-log.md"
}
```

### Field rules
- `id`: `ctx-` + slug + 4-char suffix (lowercase hex). Stable for the life of the record; survives version bumps.
- `type`: drives where extracted `fields` are routed (audience→icp.md, offer→offers.md, process/decision→wiki page).
- `shareable` / `gate_tier`: **written from day one** so the future MCP server can gate without a migration. **Default `private` / `internal`** for `business-knowledge` and `process` records unless the user explicitly opts in. The server returns a record only when the caller's tier clears `gate_tier` AND `shareable != private`.
- `version`: bump on every re-capture of the same slug; `updated` follows.
- `fields`: use the exact canonical field keys (icp.md → `primary_audience`, `pains[]`, …; offers.md → `offers[]`{name,price,promise,url_or_id}; etc.). Never invent keys.

## `context-index.json` — the catalogue (the future service's index)

```json
{
  "schema_version": "1.0",
  "updated": "ISO 8601",
  "records": [
    { "id": "ctx-...", "slug": "...", "type": "...", "title": "...",
      "shareable": "public|licensed|private", "gate_tier": "free|paid|internal",
      "version": 1, "updated": "ISO 8601", "path": "context-records/{id}.json" }
  ]
}
```

- Upsert by `id` on every completion/re-capture (match existing → replace its entry; else append). Never duplicate an `id`.
- Refresh top-level `updated`.

## Locations (resolve by mode; never hard-code an absolute path)
| Tier | Host campus | Standalone / peer |
|---|---|---|
| Tier-1 raw log | `{campus_root}/strategy-sessions/{date}-{slug}/session-log.md` | `./strategy-sessions/{date}-{slug}/session-log.md` |
| Tier-2 records + manifest | `{campus_root}/context-records/` | `./teams-shared/context-records/` |
| Tier-2 wiki entry | campus `wiki/` (canon-resolved) | `notes.md` in the session folder (degrade) |

`campus_root` = the directory holding `workspace.json`. Never hard-code a campus folder name.

## Future MCP service (deferred — context only, do not build here)
A later server reads `context-index.json` + the `{id}.json` records, filters by `shareable`/`gate_tier`, authenticates the caller, and exposes `list_context` / `get_context(id)` / `query_context(topic)`. Raw Tier-1 logs are never served. Because the gate fields + manifest exist now, the server is additive — no re-architecture.
