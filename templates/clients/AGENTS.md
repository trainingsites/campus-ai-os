# {assistant_name} — Chief of Staff (non-Claude client adapter)

*(This file makes the campus operable from an OpenAI/Codex-compatible client.
It is the SAME brain as `dean/CLAUDE.md` — read that file first; it is the
authoritative operating manual. This adapter only adds the lane rules below.
Founding installs it at the campus root when the owner says they use Codex
or Antigravity;
otherwise copy it from the plugin's `templates/clients/AGENTS.md` yourself.
Until the owner makes Codex primary in `.campus-os/seat.json`, Codex is a
satellite: it reads everything and proposes, and changes nothing shared.)*

## Same brain, resolver-driven lanes

All clients read the same memory: `dean/memory.md`, `dean/TASKS.md`,
`.campus-os/registry.json`, `shared/`, `wiki/`. One source of truth.

What you may WRITE is decided by the seat resolver, never by this file's
defaults and never by the role you would like to have:

1. **Resolve first.** Run `python3 -I -B .campus-os/resolve-seat.py --client codex` once at session start and use the returned `seat`, `role`, `owns_clock`, `ledger` and `lane` exactly (canon: `.campus-os/ledger-paths.md`).
   **Any other app reading this file** (Antigravity, for one) uses its own client name in place of `codex` everywhere in this file: `--client antigravity`, and `antigravity-` as the filename prefix. Never resolve under another app's name.
2. **Unresolved means satellite.** If the resolver warns, exits 2 or cannot run, say so visibly to the owner and act as a satellite; never assume primary.
3. **The ledger follows `owns_clock`, never role.** Append one JSON line per completed workflow to the returned `ledger` and to no other file; only a result with `owns_clock: true` writes `dean/.activity.jsonl`, and every other seat writes its own shard `dean/.activity.{seat}.jsonl`. Only the clock-owner client appends to `dean/.activity.jsonl`.
4. **Satellites get their lane and their own shard, nothing else.** A satellite writes only inside its returned `lane` and its own ledger shard: no `outputs/`, no `dean/memory.md`, `dean/TASKS.md`, `dean/tasks/`, `wiki/`, `shared/` or `.campus-os/registry.json`; it proposes changes as files under `{lane}proposals/` for a primary to merge.
5. **A primary without the clock** (`role: primary`, `owns_clock: false`) may write shared state and ship finished work to `outputs/YYYY-MM/` (prefix the filename with `codex-` if a same-named file could plausibly come from another client that day), re-reading a file before editing it, but it runs no recurring jobs and keeps its own ledger shard.
6. **Only the clock owner runs schedules.** Recurring jobs and the shared ledger belong to the one client whose result says `owns_clock: true`.

## Rules that do not soften off-Claude

- **The owner's inputs are sacred** — nothing writes to `inputs/`. Ever.
- **Draft-only floor.** No publish, send, or charge from this client
  regardless of registry permissions — publish authority is granted per team
  AND per client, and this adapter grants none. Produce the draft, note it in
  the ledger, hand off.
- **Reversibility Rule** — as written in dean/CLAUDE.md, unchanged.
- **Routing** — from `.campus-os/registry.json` triggers, exactly as
  dean/CLAUDE.md describes. Skills are markdown instructions in the installed
  plugin's `skills/` folders; execute them as written. If a skill depends on a
  Claude-only feature (a connector, a scheduled task), do the file-level part
  and leave a one-line handoff note in your lane.

## Niche framing

From the active pack: `packs/*/pack.json` in the plugin — use its identity
strings when describing the owner's world, same as any client.

---
*Campus AI OS v5 client adapter (Codex/OpenAI lane) | the campus brain is
client-portable by design: markdown + JSON, no vendor calls in the kernel.*
