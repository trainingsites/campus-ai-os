# Activity-ledger paths — canonical names, seats, resolution (Seat Contract, Phase 2)

**This file is the ONE owner of every activity-ledger path on this campus.**
Skills and teams NEVER hard-code `dean/.activity.jsonl` as the file they write.
They resolve their ledger through this canon: **read your seat → write your
seat's file → read every seat's file.**

Same ownership pattern as `context-files.md` and `registration-block-spec.md`:
the kernel owns the template, the campus holds the copy, every reader reads the
campus copy — so a fix here reaches every installed team without any of them
repackaging.

## How to find THIS file (canon resolution)

Resolve `LEDGER_CANON` in this order, first hit wins:

1. **`{campus_root}/.campus-os/ledger-paths.md`** — the campus's own copy,
   written by `/campus-start` at founding and refreshed by `/update-workspace`
   on upgrade. **This one wins.**
2. **`templates/ledger-paths.md` in the plugin that is running** — the source
   the campus copy is made from, and the fallback in peer / pre-founding mode
   where no campus exists yet.

## Resolving your seat

Run `python3 {campus_root}/.campus-os/resolve-seat.py --client <actual-client>` once at startup, using the client identified by the host: `claude-cowork`, `claude-code`, or `codex`. Use the returned `seat`, `role`, `ledger`, `lane`, and `via`. Do not select a client to obtain a desired role. The resolver checks a stable machine fingerprint against the explicit client assignment; `mounted_at`, home-directory names, and model names never establish identity. Top-level `seat`/`role` in seat.json describe the primary owner for legacy metadata, not every caller.

If the resolver reports a warning, exits 2, or cannot run, visibly report the identity failure and operate as an unassigned satellite; never silently assume primary. If the host cannot expose its machine identity (for example a sandboxed Cowork container), primary access requires a verified host-side binding: `.campus-os/host-binding.json`, issued only where the fingerprint is observed by `resolve-seat.py --issue-binding --client <primary-client>`, short-lived (default 12 hours, never more than 24), and consulted only when the fingerprint is unavailable. A binding never overrides a fingerprint mismatch; do not substitute the configured fingerprint as if it were observed. No directory-path fallback is allowed.

Primary: `dean/.activity.jsonl`. Satellite: use the returned `ledger` exactly. Missing configuration never grants primary access.

## The write rule — exact

Append one JSON line to **your own** ledger file. Never append another seat's
file. Every line you write carries `"seat"`:

```json
{"ts":"2026-08-30T14:22:00Z","session":"S271","seat":"{seat}","skill":"ad-hoc","trigger":"...","dept":"dean","outcome":"completed","files_touched":3}
```

**`{seat}` is a placeholder — substitute the value you resolved from `.campus-os/seat.json` above. Never copy a literal seat name out of this example; a hardcoded seat makes every ledger line lie about which machine did the work.**

`seat` is the field this canon requires. A session the resolver returned with `"via": "host-binding"` also writes `"via":"host-binding"` on every line, so audit can tell bound sessions from observed ones. Everything else in the line is
unchanged from the shape kernel readers have always parsed.

## The read rule — permissive

A reader of "the campus activity ledger" reads **all** of these and merges:

1. `dean/.activity.jsonl` — the primary ledger
2. `dean/.activity.*.jsonl` — every satellite shard present (glob; there may be none)

Skip blank lines and lines starting with `#` (header comments) in every file.
Sort the merged set by `ts`. A line with no `seat` field predates the stamp and
belongs to the primary seat — **attribute it to primary, never drop it, and
never retro-edit the file.** Ledgers are append-only.

## Why sharding exists

One file with two writers is the corruption case. Under git it survives
(append-only + union merge); on a folder-sync transport — Drive, iCloud,
Dropbox — two clients appending the same file produce a conflicted copy and
silent line loss. One file per seat makes concurrent writes structurally safe on
every transport, and the read-side merge above means nothing downstream notices.

## For team plugins

Resolve the ledger through the campus copy of this file. Until you do, the
sanctioned phrasing (enforced by `validate-team`) is:

> Log one line to the campus activity ledger for your seat (primary seat:
> `dean/.activity.jsonl`; satellite seats: `dean/.activity.{seat}.jsonl`), with `run_id`.

**Disclosed residual (Seat Contract Phase 0, 2026-08-28):** teams shipped before
this canon write `dean/.activity.jsonl` by literal path. That is correct on a
single-primary campus and harmless under git. A **satellite seat on a
folder-sync transport must not run a ledger-writing team** until that team
adopts the phrasing above. Existing teams adopt at their next version cut.
