---
name: wiki-ingest
description: |
  Add source material to your business wiki. Triggers when the owner says
  "add this to my wiki", "remember this", "ingest this transcript", "wiki this",
  or runs /wiki-ingest. Reads source files (transcripts, articles, notes, briefs)
  and updates or creates wiki pages in the right category. Extracts what was
  LEARNED, not what happened. Updates the index and appends to the log.
user-invocable: true
department: dean-office
---

# Wiki Ingest — Teach Your Team Something New

This skill takes raw source material (transcripts, articles, meeting notes, research, the owner's own notes) and turns it into structured, growing knowledge in the `wiki/` folder. Future sessions read from this accumulated knowledge instead of starting from scratch.

The wiki follows the Karpathy LLM Wiki pattern: **synthesis happens at ingest time, not at query time.** When new material arrives, you do the hard work of organizing and cross-referencing. Future queries are fast because they read pre-organized knowledge.

---

## When to Trigger

- Owner says "add this to my wiki", "remember this", "ingest this", "wiki this"
- Owner runs `/wiki-ingest`
- Owner drops a file into `inputs/` and asks you to process it
- Owner says "what was learned this session — add it to the wiki"

---

## The Categories (FIXED at runtime — do not invent new ones)

**The category list comes from the active pack, not from this file.** Read `packs/{active_pack}/pack.json` → `wiki_taxonomy` before routing anything. Each entry gives a `category` (the folder name) and `what` (what belongs in it).

The rule is unchanged and absolute: **the list you read is the complete list.** Every page belongs to exactly one category on it. If you can't classify something into one of them, it doesn't belong in the wiki. Never create a folder that isn't on the list.

Why it lives in the pack: taxonomy is niche identity. A coaching business needs `clients` and `offers`; a business that builds and ships products also needs `projects`. A new niche declares its own list in its pack manifest — zero kernel edits.

**Fallback (no pack, or pack declares no `wiki_taxonomy`):** use these six — `clients` · `concepts` · `offers` · `decisions` · `market` · `operations`. Same rule applies: fixed, do not invent.

**Precedence when two categories fit** — the active pack may override this in `_wiki_taxonomy_notes`; otherwise: the decision goes to `decisions/` and the reusable framework it produced goes to `concepts/`; a thing that is for sale goes to `offers/` and its build history stays in `projects/`; a standing system goes to `operations/` rather than `projects/`.

---

## Process

### Phase 1 — Identify the Source

Determine what's being ingested:

1. If the owner pasted text directly → that's the source
2. If the owner referenced a file → read it (typically in `inputs/` or wherever they pointed)
3. If the owner said "what we learned this session" → use the current conversation as the source

Capture:
- **Source description:** one line ("Coaching call transcript — Sarah J, 2026-04-30")
- **Source location:** file path if applicable, or "session conversation" if not

### Phase 2 — Read the Existing Wiki

Before deciding what to write, read what already exists:

1. Read `wiki/index.md` — this lists every existing wiki page with a one-line description
2. Identify which existing pages are likely relevant to this source

**Critical:** Updates beat creates. If a page already exists for this client/concept/offer/topic, you UPDATE it. You do not create a new page. The wiki is small at first — grow it carefully.

### Phase 3 — Extract What Was LEARNED

This is the hardest step and the one that makes the wiki valuable. Read the source and pull out:

**What goes in the wiki:**
- New facts about a client, partner, or market entity
- A new concept, framework, or principle the owner articulated
- A business decision and its reasoning
- A pattern observed (in a client, in the market, in operations)
- Something that worked or didn't work, with the evidence

**What does NOT go in the wiki (skip these):**
- What happened today (that's a session log, not knowledge)
- Tasks completed (those go in employee memory.md)
- Operational state ("we're in week 2 of the launch") — that's memory.md territory
- The full transcript (raw material lives in inputs/, not wiki/)
- Generic content (anything you could read in any business book)

The test: *"Will this still be useful in 6 months when the specific session is forgotten?"* If yes, it's wiki-worthy. If no, skip it.

### Phase 4 — Route to Categories

For each piece of extracted knowledge, decide which category from the active pack's `wiki_taxonomy` it belongs to. One source often produces updates to multiple pages across multiple categories.

**Examples:**

A coaching call transcript with Sarah J might produce:
- Update to `wiki/clients/sarah-j.md` (her current state, what she's working on)
- Update to `wiki/concepts/identity-shift-framework.md` (the owner used a framework — capture the refinement)
- New page `wiki/decisions/sarah-j-pivot-to-group.md` (decision to move her to group coaching)

A blog post about pricing strategy might produce:
- New page `wiki/concepts/value-based-pricing.md` (the principle)
- Update to `wiki/market/pricing-trends-2026.md` (industry context)

A meeting recording with a partner might produce:
- New page `wiki/clients/[partner-name].md` (entity page for that partner)
- Update to `wiki/decisions/partnership-strategy.md` (a decision was made)

### Phase 5 — Write or Update Pages

For each page that needs touching:

#### If the page does NOT exist (CREATE):

Use this frontmatter:

```yaml
---
title: [Clear page title — what this page is about]
category: [one category from the active pack's wiki_taxonomy]
created: [today's date YYYY-MM-DD]
updated: [today's date YYYY-MM-DD]
sources:
  - [Source description] — [date]
---
```

Body structure:

```markdown
# [Title]

[One-paragraph summary of what this page covers]

## Key Points

- [Bullet — the main thing to know]
- [Bullet — supporting fact]
- [Bullet — pattern or insight]

## Detail

[Longer prose section if needed — the full thinking]

## Related

- [[other-page-name]] — [why it's related]
- [[another-page-name]] — [connection]

## Sources

- [Source description] — [date] — [what came from this source]
```

#### If the page DOES exist (UPDATE):

1. Read the current page
2. Update the `updated:` field in frontmatter to today's date
3. Add the new source to the `sources:` list in frontmatter
4. Add or refine content in the relevant section — do NOT just append; integrate
5. If the new information contradicts existing content, add a `## Updated [date]` section explaining the change rather than silently overwriting
6. Update or add cross-references in the `## Related` section
7. Append a line to the `## Sources` section at the bottom

**Cross-references:** Use `[[page-name]]` syntax. The page-name is the filename without `.md` and without the category prefix. E.g., `[[sarah-j]]` not `[[clients/sarah-j.md]]`.

### Phase 6 — Update the Index

Read `wiki/index.md`. For each page you created or significantly updated:

- If created: add a new line under the right category section: `- [page-name](category/page-name.md) — [one-line description]`
- If updated and the description changed: update the existing line
- If updated and description still fits: leave the index line alone

Sort entries alphabetically within each category section.

### Phase 7 — Append to the Log

Append one line per page touched to `wiki/log.md`:

```
## [YYYY-MM-DD] [category] | [action] | [page name]
- Source: [source description]
- [One sentence summary of what was added/changed]
```

Where `action` is one of: `created`, `updated`, `merged`, `cross-referenced`.

### Phase 8 — Report Back

Tell the owner what changed. Be brief:

```
Wiki updated.

Created:
  - [[clients/sarah-j]] — client entity page

Updated:
  - [[concepts/identity-shift-framework]] — refined with Sarah's session example
  - [[decisions/group-coaching-pivot]] — added Sarah's case as supporting evidence

Index and log updated. Source: [source description]
```

If a page was NOT created when the owner expected one (because the content didn't pass the "useful in 6 months" test), tell them and explain briefly:

```
I didn't create a page for [topic] because it looked like operational state
rather than accumulating knowledge. If you want it preserved anyway, tell me
and I'll create it.
```

---

## Rules

1. **Six categories only.** Never invent a new category. If something doesn't fit, push back to the owner before forcing it.
2. **Updates beat creates.** Read `wiki/index.md` first. Always.
3. **Knowledge, not events.** Extract what was learned, not what happened.
4. **Never overwrite owner edits.** If a page contains a `<!-- PROTECTED -->` block, never modify content inside that block. Add new content outside it.
5. **Sources are sacred.** Every wiki page must list its sources. Provenance is non-negotiable.
6. **Updates change the `updated:` field.** Always. Even small refinements.
7. **The index is mandatory.** No page exists in the wiki unless it's in `wiki/index.md`.
8. **Append-only log.** Never edit or delete `wiki/log.md` entries. New events go on top of the existing log.
9. **One source can produce multiple page updates.** This is normal. A coaching call usually touches 2-4 pages.
10. **Don't dump the transcript.** Raw material stays in `inputs/`. The wiki contains the synthesis, not the raw text.

---

## Edge Cases

- **First-ever ingest (wiki is empty):** Read `wiki/README.md` first if it exists. Then proceed normally — most early ingests will be CREATEs.
- **Source spans many topics:** Don't try to capture everything. Pick the 2-4 highest-value updates and ingest those. The owner can re-run `/wiki-ingest` on the same source later if they want more.
- **Owner says "ingest this" but the source isn't clear:** Ask: "What's the source — a file path, pasted text, or our current conversation?"
- **A page would be created but it's clearly a one-time event:** Skip it. Tell the owner why.
- **Multiple clients mentioned in one source:** Update each client's page. One source, multiple page updates is normal.
- **Source contradicts existing wiki content:** Don't silently overwrite. Add an `## Updated [date]` section to the affected page explaining the change with both versions visible. The owner can then decide which is correct.
- **Wiki has grown past 100 pages and updates are getting slow:** Mention to the owner that v1.2 will introduce per-category indexes. For now, keep going — the flat index is fine up to ~200 pages.
