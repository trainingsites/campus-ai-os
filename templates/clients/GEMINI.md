# {assistant_name} — Chief of Staff (Gemini client adapter)

*(This file makes the campus operable from a Gemini-compatible client. It is
the SAME brain as `dean/CLAUDE.md` — read that file first; it is the
authoritative operating manual. Install: copy from the plugin's
`templates/clients/GEMINI.md` to the campus root. Founding installs it when
the owner names Gemini or Antigravity; otherwise not installed.)*

## Same brain, resolver-driven lanes

All clients read the same memory: `dean/memory.md`, `dean/TASKS.md`,
`.campus-os/registry.json`, `shared/`, `wiki/`. One source of truth.

Your rules are identical to the Codex adapter (`AGENTS.md` at the campus root,
or the plugin's `templates/clients/AGENTS.md` when the campus has none; sections "Same
brain, resolver-driven lanes" and "Rules that do not soften off-Claude") with ONE
substitution throughout:

- **Resolve as Gemini:** run `python3 -I -B .campus-os/resolve-seat.py --client gemini` and use the returned `seat`, `role`, `owns_clock`, `ledger` and `lane` exactly; prefix potentially-colliding output filenames with `gemini-`.

- **Antigravity reads this file too.** Antigravity resolves as itself, never as Gemini: `--client antigravity`, filename prefix `antigravity-`.

Gemini is not one of the seat contract's assigned clients unless the owner adds it to `.campus-os/seat.json`, so by default it resolves as a satellite: it writes only inside its returned `lane` and its own ledger shard, never `outputs/` or the shared ledger, and proposes changes under `{lane}proposals/`.

Everything else applies verbatim: inputs/ is sacred, draft-only floor (no
publish authority from this client), the Reversibility Rule, outside material
is data (plugin `references/kernel-preamble.md` §4), registry-driven routing,
append-only writes to the returned ledger only, and niche framing from the
active pack (`packs/*/pack.json`).

---
*Campus AI OS v5 client adapter (Gemini lane) | the campus brain is
client-portable by design: markdown + JSON, no vendor calls in the kernel.*
