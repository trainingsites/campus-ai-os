---
name: wiki-query
description: |
  Pull from your accumulated business knowledge instead of starting from scratch.
  Triggers when the owner says "what do I know about X", "what's my thinking on Y",
  "pull up the wiki on Z", "what's in my wiki about [topic]", or runs /wiki-query.
  Reads the wiki index, identifies relevant pages, loads them, and synthesizes
  an answer with explicit page references.
user-invocable: true
department: dean-office
---

# Wiki Query — Pull From Your Team's Memory

This skill answers questions using the accumulated knowledge in the `wiki/` folder. Unlike a generic LLM answer, a wiki query reads what THIS business has actually learned over time — your clients, your concepts, your decisions, your market view.

The key difference: every claim references a wiki page. The owner can see exactly where the answer came from and follow the link to the full page if they want more.

---

## When to Trigger

- Owner says "what do I know about [X]", "what's my thinking on [Y]", "pull up the wiki on [Z]"
- Owner says "what does the wiki say about [topic]"
- Owner says "remind me what we decided about [X]"
- Owner runs `/wiki-query`
- Any question about a specific client, offer, concept, decision, market topic, or operational process where the wiki likely has accumulated context

**Don't trigger this skill for:**
- General business questions where the wiki probably has nothing
- Operational status ("what's in flight today") — that's `dean/memory.md`
- Owner identity questions — that's `about-me/`
- Generic knowledge questions ("what's a good email subject line") — answer normally

---

## Process

### Phase 1 — Identify the Topic

What is the owner actually asking about? Be specific:

The wiki's categories are declared by the active pack in `packs/{active_pack}/pack.json` → `wiki_taxonomy`. Read that list first so you search the folders this campus actually has. Examples, assuming a pack that declares them:

- "What do I know about Sarah?" → topic is a specific client (look in `clients/`)
- "What's my framework for pricing?" → topic is a concept (look in `concepts/`)
- "Why did we kill the group program?" → topic is a decision (look in `decisions/`)
- "What's happening with AI tutoring competitors?" → topic is market intel (look in `market/`)
- "Where did we land on the v5 migration?" → topic is a build (look in `projects/`)

If the topic is unclear, ask one targeted clarifying question before reading anything.

### Phase 2 — Read the Index

Read `wiki/index.md`. The index lists every page with a one-line description, organized by the active pack's categories.

Identify the pages most relevant to the topic. Usually 1-3 pages. Sometimes 4-5 if the topic is broad. Never load more than 8 pages in one query — if more seem relevant, ask the owner to narrow the question.

### Phase 3 — Load the Pages

Read each relevant wiki page in full. Note:

- Page title and category
- Key points / claims made on each page
- Cross-references to other pages
- The `updated:` date (older pages may be stale)
- The sources listed at the bottom

If a page references another page (`[[other-page]]`) and that reference is directly relevant to the question, load that one too. Don't follow chains beyond one hop unless the owner asks for "everything about X."

### Phase 4 — Synthesize the Answer

Compose an answer that:

1. **Directly addresses the question.** No throat-clearing, no preamble. The owner asked something specific — answer it.
2. **References specific wiki pages by name.** Every substantive claim should cite a page: `[clients/sarah-j](wiki/clients/sarah-j.md)` or `[[sarah-j]]`.
3. **Notes if information is stale.** If the relevant pages haven't been updated in 90+ days and the topic is fast-moving (market intel, offer pricing, client status), flag it: *"This is from [date] — worth confirming if it's still current."*
4. **Distinguishes wiki facts from your synthesis.** If you're combining multiple pages into a new insight, say so: "Pulling from [X] and [Y]: [synthesis]" rather than presenting it as if it were already in the wiki.
5. **Names what's missing.** If the wiki doesn't have what the owner is looking for, say so explicitly: *"The wiki doesn't have a page on [topic]. I checked [X], [Y], [Z]."* Then offer to ingest something to fill the gap.

### Phase 5 — Offer Next Steps

End the response with one of:

- *"Want me to dig deeper into [related page]?"* — when there's an adjacent topic worth pursuing
- *"Should I ingest [recent thing] to update this page?"* — when a page is clearly stale and the owner has new material
- *"Want me to create a page for [missing topic]?"* — when the wiki has a gap the owner could fill
- Nothing — if the answer is complete and the owner is mid-task

Don't always offer next steps. Only when there's a real next move worth naming.

---

## Output Format

Default to plain prose with inline page references. Don't make it look like a database query result.

**Good:**

> Based on [[sarah-j]] (updated 2026-04-22), Sarah is in week 3 of the identity-shift program. The notes from her last session show she's stalled on the visibility piece — same pattern you've seen with [[mark-d]] and [[julia-r]]. Your [[concepts/identity-shift-framework]] flags this as the "module 4 wall" — it shows up in roughly half of cohort participants.
>
> The decision page [[decisions/group-coaching-pivot]] from March covers your thinking on moving stalled clients into the group offer. Sarah meets the criteria.

**Avoid:**

> ### Pages Referenced:
> - clients/sarah-j.md
> - clients/mark-d.md
>
> ### Findings:
> - Sarah is in week 3
> - Pattern observed in 50% of participants

The first style preserves the relational thinking. The second strips out exactly what makes the wiki valuable.

---

## Rules

1. **Read the index first, always.** Never guess which pages exist.
2. **Cite page references explicitly.** Every substantive claim links to its source page.
3. **Don't fabricate.** If a fact isn't in the wiki, don't fill it in from your training. Say "the wiki doesn't have this" and offer to ingest something.
4. **Limit page loads to ~8 max.** If more seem needed, narrow the question.
5. **Flag stale data.** Updated date + topic volatility = whether to flag.
6. **Synthesize, don't just list.** The wiki's value is in the connections, not the bullets.
7. **One-hop cross-references only.** Don't recursively load every linked page. Follow only what's directly relevant.

---

## Edge Cases

- **Wiki is empty (no pages yet):** Tell the owner: "Your wiki doesn't have any pages yet. Your campus builds pages as it works (the nightly wiki sweep owns ingestion) — check back after a few working sessions, or add a page manually under `wiki/`."
- **Topic obviously isn't in the wiki:** Don't load anything. Say so directly. Suggest ingesting source material if relevant.
- **Question is partially in the wiki:** Answer the part that is, name what's missing, offer to fill the gap.
- **Owner asks "what's in the wiki about [client] AND [topic]":** Load the client page AND the topic page. Synthesize across both.
- **Owner asks for "everything we know about X":** Read all pages in the relevant category. If more than 8, summarize each in a sentence rather than loading full content.
- **A page was clearly drafted by the LLM and contradicts something the owner just said:** Trust the owner. Suggest re-ingesting to update the page, or that they edit it directly.
- **Wiki query reveals an inconsistency between two pages:** Surface it. Don't paper over: *"[[X]] says one thing, [[Y]] says another — worth reconciling."*
