---
name: campus-doctor
description: >
  Plain-English health check for the campus. Verifies the workspace is mounted
  and writable, setup files, team registry, setup completeness, stale work, and
  that the activity ledger is alive, and that the Seat Contract holds (seat
  lanes, seat stamps, sync hazards). Reads one deterministic evidence command.
  Use when the owner says "/campus-doctor", "health check",
  "something's not working", or "is everything ok".
version: 5.3.8
department: kernel
---

# /campus-doctor - Is Everything OK?

One report card for someone who has never opened a terminal, every problem
with a one-line fix. The doctor **explains evidence**; it never gathers it by
hand. Lookup files: this skill's own `references/` folder
(`references/kernel-preamble.md` is at the plugin root).

**Platform resolution (do this first):** resolve `PLUGIN_MANIFEST` and
`ENTRY_FILE` per `PLATFORM.md` at the plugin root. **Never hardcode either.**
Presence checks accept any known entry file; a repair writes the resolved one.

**Context resolution (do this first too):** resolve `CONTEXT_CANON` -
`.campus-os/context-files.md` on the campus, else `templates/context-files.md`
in this plugin. Resolve a context file in the canon's read order (founding name ->
canon -> aliases), each also matched case-insensitively before the next. **Never type a `shared/*.md` filename
into a check that READS one.**

## Procedure

1. **Write test.** Write `active-work/.campus-write-test` (always this fixed
   name), then delete it. A failed WRITE is the only
   failure: "Claude can't see your campus folder. Reconnect it: [folder icon]
   in the sidebar -> choose your campus folder." A failed delete still passes.

2. **Gather the evidence in one command**, run from the campus kit
   (Kernel preamble §5), from the campus root, in the shell that can see the
   campus folder. First make sure the kit is current and has the `on_demand`
   tier: `update-workspace/references/additions.md` item 18 steps a-c with
   `--tier all` (copy only what is missing or changed). Read-only and
   byte-stable:

   ```
   python3 -I -B .campus-os/kernel/tools/doctor_evidence.py --campus-root . --json --kit-manifest -
   ```

   with the plugin's `tools/kit-manifest.json` (read with file tools) on
   stdin: the `kernel_kit` line is then checked against the plugin, not
   against the kit's own stamp. Run only a kit that passed §0's check first:
   a changed or `newer` kit is never run.
   No kit and no way to copy one, but this shell sees the plugin: run the
   plugin's `tools/doctor_evidence.py` instead and say so.

   **On Windows** the command is usually `python` (or `py -3`), not
   `python3`. Pass the manifest as a file path (`--kit-manifest PATH`) when
   the shell cannot pipe it cleanly; a byte-order mark on the pipe is accepted.

   Add `--scheduled-json PATH` (or `-` with the list on stdin) when THIS host
   can list its scheduled jobs, using the envelope in `evidence-sections.md`;
   **never call a scheduler API from this skill.** Add `--sweep` when the owner says "sweep
   the fleet". Add `--runtime-dir PATH` (repeatable) for each folder where THIS host keeps its runtime job copies (`{taskId}/SKILL.md`), when you know it.

   **Exit codes.** `0`: every section produced evidence. `1`: evidence was
   collected and **some lines are red** - read the JSON and report it; this
   is a campus finding, not a tool fault. `2`, or no JSON on stdout: **the
   tool itself failed** - say so, show its last stderr lines, and do not
   invent numbers.

   **Python that cannot start isolated.** When the JSON carries a `preflight`
   entry, or the command dies with `Failed to import encodings`, say that one
   line first and plainly: Python on this computer cannot start in isolated
   mode, so repair or reinstall Python. It is the computer, not the campus.
   The sections it blocked read `[--] not checked`. Never drop `-I` to get
   past it.

3. **Explain the fourteen sections in order**, one line each - never fold two
   sections into one line (5.2.12: `context_files` was merged into the stale-work line). Start from each
   section's `line`; use `detail` for the fix. Status -> prefix: `ok` ->
   `[OK]`; `opportunity` or `skipped` -> `[--]`; `needs-decision` or `error`
   -> `[!!]`. Rules per section: `evidence-sections.md`.

   | Section | Meaning |
   |---|---|
   | `workspace` | `workspace.json` + root entry file present; missing -> offer /campus-start |
   | `kernel_kit` | the campus copy of the kernel tools: present, every file checks, same version as the plugin; missing or stale -> /update-workspace; newer than the plugin -> update the plugin |
   | `version_lockstep` | all three agree; installed ABOVE both records -> an upgrade is owed: offer /update-workspace, never a bare stamp; records disagree with each other -> offer "stamp the version" |
   | `registry` | registry validates; spec copy current per `materialize_registration_spec.py --check` |
   | `context_weight` | startup tokens and band; AMBER/RED -> propose the prune tool, never run it unasked |
   | `results_ledgers` | results envelopes validate; failures counted and named, never edited - a team's `results.json` is that team's record |
   | `schedules` | recurring jobs firing; enabled-but-silent is THE finding; skipped when no list given |
   | `seat_contract` | seat identity, foreign writes, missing stamps, sync hazards |
   | `fleet_sweep` | monthly Foundry sweep; skipped outside the window or without a Foundry |
   | `staff` | org chart: employees + campus systems + playbooks, per-department; orphans loud |
   | `context_files` | a concept held in two files (e.g. `icp.md` beside `audience.md`); the first in read order is the one every skill reads; offer to merge, never merge unasked |
   | `stale_work` | active-work files over 14 days old |
   | `ledger` | newest entry across every ledger shard; unstamped lines; mis-typed lines against the one line shape |
   | `runtime_drift` | each runtime job copy vs its canonical `scheduled/` file; drift is reported, never fixed; skipped without `--runtime-dir` |

   Staff-line rules the tool applies and you must not undo:
   it RESOLVES `dean` to `dean-office` before matching;
   it SKIPS every entry whose `status` is `retired`, `legacy`, or `disabled`;
   each department name comes from the `label` field on its own `type: department` registry entry;
   the breakdown adds up to the headline; an empty department shows as `0`;
   a team under a department with no entry is a loud `[!!]` line, never a silent drop.

4. **Run the manual checks** the tool cannot see (`manual-checks.md`):
   founding interview still a conversation - the installed
   `campus-start/SKILL.md` MUST contain "NEVER BATCH THE FOUNDING QUESTIONS"
   and must NOT contain wording that permits asking several founding
   questions at once (report, never repair); setup completeness from the setup-progress rows; recent work in
   `outputs/`; structure matches the folders; playbooks registered;
   unregistered real departments (offer, never force); connections line
   (resolved context - name the connector and stop); backup reminder.

5. **Report** per `report-format.md`: header, one line per finding, `[OK]`
   fine / `[--]` opportunity / `[!!]` needs a decision or fix, then at most
   ONE suggested next action.

## Rules

- Plain English; no file paths in summary lines.
- Never auto-fix anything destructive; offer, then wait. Repairs correct
  records only; real migration is /update-workspace.
- Never report a number the owner cannot trace to the evidence.
- Never edit a team's `results.json`, not even to "fix" a failing one: only the team that made
  the run writes it, and its timestamps and completion answers cannot be known after the fact.
  Name the file and the missing fields, and say which team to update or re-run.
- Suggest a weekly scheduled run once, when everything is first green.

## File anchoring (critical)

Kernel preamble §2 applies: `references/kernel-preamble.md`.

Kernel preamble §5 applies: `references/kernel-preamble.md`.
