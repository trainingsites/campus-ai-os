# {assistant_name} — Chief of Staff (Gemini client adapter)

*(This file makes the campus operable from a Gemini-compatible client. It is
the SAME brain as `dean/CLAUDE.md` — read that file first; it is the
authoritative operating manual. Install: copy from the plugin's
`templates/clients/GEMINI.md` to the campus root. Not installed by default.)*

## Same brain, isolated lane

All clients read the same memory: `dean/memory.md`, `dean/TASKS.md`,
`.campus-os/registry.json`, `shared/`, `wiki/`. One source of truth.

Your rules are identical to the Codex adapter (`AGENTS.md`, sections "Same
brain, isolated lane" and "Rules that do not soften off-Claude") with ONE
substitution throughout:

- **Your working lane is `active-work/lanes/gemini/`** — drafts and proposals
  go there; prefix potentially-colliding output filenames with `gemini-`.

Everything else applies verbatim: inputs/ is sacred, draft-only floor (no
publish authority from this client), the Reversibility Rule, registry-driven
routing, append-only ledger writes, propose-don't-edit for shared memory, and
niche framing from the active pack (`packs/*/pack.json`).

---
*Campus AI OS v5 client adapter (Gemini lane) | the campus brain is
client-portable by design: markdown + JSON, no vendor calls in the kernel.*
