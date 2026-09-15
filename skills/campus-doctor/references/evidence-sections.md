# Evidence sections - what `tools/doctor_evidence.py` measures and how to explain it

Companion to `/campus-doctor` step 3. One deterministic, read-only command
(5.2.0 Phase 5.2) replaced the five tool calls and the hand reasoning the
doctor used to do. This file holds the per-section rules, the fix to offer,
and the history behind each one, keyed by the section name in the JSON.

## Running it

```
python3 tools/doctor_evidence.py --campus-root {campus_root} --json
       [--today YYYY-MM-DD] [--window N] [--scheduled-json PATH|-] [--sweep]
```

- `--today` pins the as-of date (default: today, UTC). Same campus + same
  `--today` = byte-identical JSON; the kernel fixture proves it.
- `--window N` is the context window in tokens, passed to the weight tool
  (default 200k). The band is a fraction of the window, so it survives a model
  change without a re-decision.
- `--scheduled-json PATH` is the host's live task list; `-` reads it from
  stdin and is the ONLY way stdin is read (an open pipe with no flag never
  blocks). Relative paths are campus-relative.
- `--sweep` forces the fleet sweep outside the monthly window.
- JSON shape: `generated.today` plus eleven sections, each
  `{status, detail, line}`. Statuses: `ok`, `opportunity`, `needs-decision`,
  `skipped`, `error`. Without `--json` the tool prints each section's `line`
  in check order - the same lines the report shows.
- Exit `0`: every section produced evidence. Exit `1`: at least one section
  is `error` - evidence collected, some lines red; report them. Exit `2` or
  no JSON: the tool failed (usage, or the contract could not load). Only the
  last case is a tool fault.
- Every sub-tool failure lands in its own section as `error` with the
  sub-tool's `stderr_tail`; the other sections still emit. Report the failing
  section as a tool problem for that one line, not as a campus fault.

## Crosswalk from the pre-5.2.0 check numbers

| Section | Old check(s) | Section | Old check(s) |
|---|---|---|---|
| `workspace` | 1 (partly), 2, 2a | `seat_contract` | 11, 11a-c |
| `version_lockstep` | 2c, 2d | `fleet_sweep` | 7c |
| `registry` | 3, 7, 7b | `staff` | 8a |
| `context_weight` | 5a | `stale_work` | 5 |
| `results_ledgers` | new (Phase 3.1) | `ledger` | 9 |
| `schedules` | 10 | manual (see `manual-checks.md`) | 1 write test, 2b, 4, 6a, 6b, 8, 8a-i, 8b, backup line |

Other kernel files still cite the old numbers (tools comments, PLATFORM.md,
update-workspace). They mean the row above.

## `workspace` (old 2, 2a)

Reads `workspace.json` and looks for a root entry file using the contract's
read names (any of `CLAUDE.md` / `AGENTS.md` / `AGENTS.override.md` /
`CODEX.md` - Codex's real chain is `AGENTS.override.md` then `AGENTS.md`;
`CODEX.md` is a legacy alias, read but never written). `detail.entries` names
the file(s) found.

- `needs-decision`, no `workspace.json` -> "Your workspace hasn't been set up
  yet" and offer /campus-start.
- `needs-decision`, version or entry file missing -> the entry file is why "my
  assistant doesn't act like my chief of staff in new chats". Offer the
  one-line repair: write the redirect as `ENTRY_FILE` resolved for THIS host
  (exact content in `skills/campus-start/references/scaffold.md`,
  assistant name from `workspace.json`). A repair, not a rebuild: never touch `dean/{ENTRY_FILE}`.
- A campus driven by a non-Claude client correctly has a different entry
  filename; one driven by two clients correctly has more than one. *Rationale
  (v5.1): the old check hardcoded one name and reported a correct Codex
  campus as broken.* Presence reads permissively; creation writes one name.

## `version_lockstep` (old 2c, 2d)

Three homes: `workspace.json -> version`, `.campus-os/registry.json ->
campus_os_version`, installed `PLUGIN_MANIFEST -> version` (resolved by the
contract's manifest probe order). All equal -> `[OK] Version current (v{x})`.

- Installed ABOVE both records -> the plugin was upgraded and the campus was
  not: "Your campus is recorded as v{marker} but you're running v{installed}
  - run /update-workspace to bring it up." Offer ONLY /update-workspace; its
  closing rule stamps both records after the additions run. **Never offer a
  bare stamp here**: a stamped-but-not-upgraded campus reads as current and
  update-workspace then skips its additions forever (the stranded-campus
  class, build-gate check 12). Found on the 5.2.0 sign-off run, 2026-09-08.
- The two campus records disagree with EACH OTHER (an earlier upgrade
  stamped one home and not the other) -> offer "stamp the version": align
  the lagging record to the installed plugin. Records only, migrates nothing.
- Installed LOWER than the records -> the owner downgraded; report, change
  nothing.
- `error`, manifest unresolved -> the plugin tree is damaged; report as a tool
  fault for this line.
- *Rationale:* v5.0.2 hardcoded `5.0.0` in seven places and a fresh install
  stamped itself 5.0.0; `tools/package.py --check-lockstep` refuses to cut a
  tree whose homes disagree. This is the same fact checked after install,
  where upgrades stamp one home at a time.

## `registry` (old 3, 7, 7b)

Runs `validate_registry.py --json` (entries, counts, failures) and
`materialize_registration_spec.py --check --json` (spec state).

- Validation failures -> `error`; name the teams from `detail.errors`. Each is
  that team's next-cut work ("their next update adds it"), not a campus
  fault. `type: department` and `type: systems` entries are directory records,
  validated lightly, never off-spec; `type: kernel` entries are validated
  fully; `status: legacy` is exempt.
- Spec `current` -> ok. `stale` (predates the installed kernel, or the
  overrides changed) -> offer "refresh the spec": the same tool, a
  records-only rewrite that keeps every override. `hand-edited` (no stamp) ->
  offer "capture my spec notes" (`--capture-notes` turns the owner's lines
  into overrides, then materializes; owner canon is never clobbered).
  `missing` -> `[!!]`; /update-workspace writes it. Never compare the two
  spec files byte-for-byte: overrides are the owner's, not drift.
- Installed teams the registry does not know (and vice versa) are still found
  by hand in `manual-checks.md` when the owner asks; offer a stub entry from
  the plugin's README, never write one unasked.

## `context_weight` (old 5a)

Runs `node tools/context-weight.mjs --root {campus_root} --json` (skipped
when Node is absent - say so in one line, never guess a number). Report the
tool's verdict line as written, plus the heaviest file and its largest
section, on EVERY run - the owner should watch the number climb.

- GREEN (<=10% of the window) -> `[OK] Startup reads {N} tokens ({P}%)`.
- AMBER (10-20%) -> `[--] ... archive due. Heaviest: {file} ({tokens}, mostly
  "{section}")`. RED (>20%) -> `[!!] ... a fifth of every session is gone
  before your first question.`
- UNKNOWN (tool exit 3, `error` here) -> report the finding line and the
  lower-bound total as a lower bound, never as the number.
- The ONE next action for AMBER/RED is the prune tool, offered as a PROPOSAL:
  `node tools/context-prune.mjs --root {campus_root}` (no `--apply`) shows
  what it would move - `[archive-eligible]` entries only, to an archive beside
  the source, pointer left in place. `[pinned]` entries, standing rules, and
  anything under a `[pinned]` heading never move whatever their age. "No
  eligible units" is correct, not a defect. Only on an explicit yes run
  `--apply`; it archives first, verifies byte-for-byte, then rewrites.
  **Never trim the owner's memory unasked; never propose a bare delete.** A
  file the prune tool refuses (a generated one) is reported as-is.
- The tool counts whatever THIS campus reads (`workspace.json ->
  startup_reads[]`, else the entry file's "Start of Session" paths, every
  entry name accepted, context names resolved through the canon). *Why
  tokens, not lines:* a 249-line memory file of long rows costs ~100,000
  tokens and passed the old line test; a check whose unit cannot see the
  defect cannot fail.

## `results_ledgers` (Phase 3.1)

Runs `validate_results.py --json`: how many `results.json` envelopes exist,
counts by schema version, how many fail. `error` when any fails - name the
count; the run directory is that team's problem, not the campus's.
`skipped` when the campus has none yet.

## `schedules` (old 10)

Runs `check_cron_parity.py` with the host's live task list, pinned to the
as-of date. The envelope you hand it: `{"capability":"available",
"retrieval":"success","tasks":[...]}` when the host listed its jobs (an empty
list is a real answer); `{"capability":"available","retrieval":"failed",
"error":"..."}` when the listing failed; `{"capability":"unavailable",
"retrieval":"not_attempted"}` when this host has no scheduler. A bare task
array is accepted. **Say what you know, never what you assume.**

- No flag -> `skipped: no live task list supplied`. Never report that as a
  healthy campus. Scheduler `unavailable` -> `skipped`, say nothing (a
  different platform, not a broken campus). A failed read -> `[!!] Couldn't
  read your scheduled jobs - {detail}`; never "no scheduler".
- **Layer 1, every campus:** `[OK] Recurring work: {N} scheduled jobs - {E}
  running, {D} switched off`. Enabled but not firing past 3x its expected gap
  -> `[!!]` (THE finding: silent failure); merely late says nothing. Enabled
  but never run once -> `[--]`.
- **Layer 2, only if `scheduled/*.md` exist:** drift ("{task} is set to
  {live} but your campus says {canonical}") -> `[!!]`, offered as a QUESTION
  ("which one is right?"), never a repair; defined but never registered ->
  `[!!]`; registered but undocumented -> `[--]`, one line. No `scheduled/`
  folder -> show NOTHING from layer 2 and never suggest the habit. Report
  against the owner's structure, never toward ours.

## `seat_contract` (old 11)

Runs `seat_contract_checks.py --json`. Report its lines as written; all from
files alone (no git, no host API).

- **Seat identity first.** `valid`, `missing`, `invalid`, `unresolved`. Only
  a valid PRIMARY seat proves clean ownership. `missing` -> `[--] Seat
  identity not declared - ownership can't be verified. Fine on a single
  machine; declare it before a second client or machine shares this folder.`
  `invalid` -> `[!!]` with the detail; fix that one file. A declared
  satellite -> `[!!]` nothing is proven. Silence about ownership is never
  proof of it.
- **Foreign writes** (`[!!]` only where provable: a seat-X line inside
  `dean/.activity.Y.jsonl`). A stamp that merely differs from today's primary
  is `OWNERSHIP_HISTORY_UNKNOWN` -> `[!!] Ownership check incomplete: {N}
  record(s)...` - never a violation, never advice to move or delete history.
  Unknown lane folder -> `[--]`. Malformed ledger lines -> `[!!] {N}
  unreadable or invalid ledger record(s); diary check incomplete`.
- **Missing seat stamp** -> `[!!]`, self-anchoring: once any line in a file
  carries `seat`, every later line must; earlier lines are legacy and never
  flagged.
- **Sync hazards** -> `[!!]`: conflicted-copy files, `.icloud` placeholders,
  a git repo inside a cloud-sync root. Editor locks (`.~lock.*`) and Dropbox
  partials (`.sb-*`) are deliberately NOT hazards (S272 false-positive guard).
- A single-seat campus with a valid seat.json and no sync folder gets zero
  findings and one line saying so. Never nag a healthy solo campus toward
  machinery it does not need.

## `fleet_sweep` (old 7c, monthly)

Runs the Foundry's `validate-team` over every installed team source under
`library/teams/*/` (never shelf archives, no `--profile`) on the first three
days of a month or with `--sweep`. Otherwise `skipped` - print nothing; the
sweep is an evidence line, not a nag. No Foundry -> `[--] Fleet sweep skipped
- no Foundry on this campus`, nothing else. When it ran, print one table
(team · pass · errors · warnings · first error) then `[OK] Fleet sweep: {N}
teams, {P} conformant` or `[--] ... {F} with errors - each is that team's
next-cut work, not a campus fault`. *Why monthly:* the August 2026 audit found
nine teams off-spec that every daily check had passed.

## `staff` (old 8a)

Derived from `.campus-os/registry.json` alone. Employees = the union of
`employees[]` and `employees_added[]` across every `type: department` entry
(whatever this pack labels them, including any department the owner
registered under their own name) plus every ACTIVE `teams[]` entry filed
under one of those departments, de-duplicated by name. Campus systems = the
`type: systems` entry's `systems[]` (+ `systems_added[]`). Playbooks =
`playbooks[]`. Kernel meta entries are excluded by TYPE, never renamed.

Report ONE line: "Your staff: {E} employees + {S} campus systems + {P}
playbooks" and the per-department breakdown from `detail.departments`
(`label` in registry order; Title Case of the id only where an entry has no
label). Rules the tool already applied, kept here so nobody reintroduces the
old defects: `dean` resolves to `dean-office` (spec vocabulary vs counter
vocabulary, v5.1.4); `retired`/`legacy`/`disabled` entries are skipped
(v5.1.3, the reader that was never taught status); the breakdown sums to the
headline (v5.1.3, "45 employees" that added to 43); an unstaffed department
shows as 0 (the org chart is the diagnosis); a team whose department has no
entry is in `detail.orphans` -> `[!!] {team} is registered under
'{department}', which this campus has no department entry for - say "repair
departments" and I'll add the missing entry from the shipped template`
(v5.1.8). Duplicate memberships are listed the same way. Never type a
department name or list into the skill: a typed list drops every department a
pack adds (v5.1.7), and the doctor was once the THIRD owner of the label
(v5.1.6, "Education 3" on a campus whose registry said "Teaching"). Counts
are never asserted from an example; a grown campus or another pack reads
differently and that is correct. Shown in every filing mode.

## `stale_work` (old 5)

Files under `active-work/` modified more than 14 days before the as-of date;
`detail.oldest` names one. `[--]`, one line.

## `ledger` (old 9)

Merges the primary `dean/.activity.jsonl` and every `dean/.activity.*.jsonl`
shard per the contract's ledger paths; the newest `ts` across ALL of them
wins - a campus whose only active seat is a satellite is alive. Report:
newest entry age (older than 7 days -> "Your campus stopped keeping its work
diary - future skill suggestions depend on it"), unstamped lines (`[--]`,
name the count), malformed lines (`error`). Add the backup reminder from
`manual-checks.md` on this line.
