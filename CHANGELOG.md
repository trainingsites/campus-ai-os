# Changelog

All notable changes to the Campus AI OS kernel. Format follows Keep a Changelog; versions follow Semantic Versioning (security fixes are patch releases). Released entries are never rewritten; corrections go in a later entry. The packaged artifact hash for every release is in the sibling `campus-ai-os-v{version}.PACKAGE.json`, never retyped here.

## [Unreleased]

## [5.3.8] - 2026-11-23

5.3.7 was packaged but never released.

Two update runs of 5.3.6 on older campuses, one of them over a campus founded with another edition, and the first real run of 5.3.7 from an empty folder.

### Fixed

- **One wrong answer could rename a campus for another edition.** When the department names do not match the plugin's edition and the owner says the campus was set up with this edition anyway, the update now shows every rename and asks once more. Only the typed word RENAME carries on.
- **The org-chart tool wrote when asked for its options.** `tools/gen_department_entries.py` run bare, with `--help` or with an unknown option rewrote the plugin's own registry template. Every write now needs an explicit mode; anything else prints the usage and writes nothing. An unknown pack name is refused, and a campus that records no edition is not renamed without `--confirm-rename RENAME`.
- **The different-edition message no longer names a version** of the other edition.
- **Dean's instructions named the Education pack in every edition.** The entry-file templates now point at `packs/active.json` instead of naming one pack.
- **Job cards are named, never counted.** The Chief of Staff calls a card by its name and never says how many there are; they are the owner's default job cards, a starting set.

### Added

- **Quickstart: permission prompts and updating.** One paragraph on why Claude Code asks before running the plugin's checks, and the steps to update a campus already in use.
- **Undo for an update.** `tools/update_undo.py` takes a snapshot before the first write and a seal after the last. On "undo the last update" it shows what it would do, then puts the system files back and moves what the update created into the snapshot folder. Nothing is deleted. It never restores over the owner's job cards, seat file, memory, task list or work diaries, flags any entry file that changed after the update, and works whichever edition is installed.

## [5.3.7] - 2026-11-23

5.3.6 was packaged but never released.

First real run of 5.3.6 from an empty folder, start to finish.

### Fixed
- **Setup no longer leaves a temp file behind.** Writing the seat file for the first time made a temporary file and then removed it; an app that may create files but not remove them left `.seat.json.<letters>.tmp` in `.campus-os/`. The first write now creates the file directly.
- **The three setup options are always shown,** including when the owner hands over their answers in a file. The choice is taken from the file only after the options are on screen.

### Changed
- **A pack's job cards file may end with playbooks:** named sets of cards that run together, in order. The chief of staff looks for a named playbook there before the registry's playbooks, and the first win never starts from the playbooks section. The chief of staff now reads the cards once a session, the first time work is asked for, and does any job a card covers by that card's rules; in 5.3.6 it opened the file only when a card was named, so a plainly worded request skipped the card. Nothing on the cards starts by itself.

## [5.3.6] - 2026-11-23 (packaged, not released)

Fixes from an independent review of the 5.3.5 cut, made before either was released. 5.3.5 was packaged but never released; its notes below still describe the release, with these corrections.

### Fixed
- **The edition check runs before anything is copied.** It now comes first in `/update-workspace`, ahead of the kit copy, and the roster tool refuses in code to relabel a campus recorded as another edition. `/wiki-ingest`, `/wiki-query` and the first win also read the campus's edition, so the wiki categories no longer switch outside an update.
- **A campus with no recorded edition is recognised by its department names,** never assumed from its version; when they differ the owner is asked once.
- **The seat step asks which app is the main one** when the owner names more than one, so running the update from a second app can't take the schedules away from the first. It also covers the Windows command name, the host-binding note, lowercase app names, and a named app's entry file on any update.
- The older-campus entry points end with items 11-18 (one line still said 11-15).

## [5.3.5] - 2026-11-23 (packaged, not released)

5.3.4 was packaged but never released.

Two owner field reports: a Windows campus with a second AI app, and a coach build put on top of an education campus.

### Added
- **The campus records its edition.** Founding writes `pack` into `workspace.json`, read from the plugin, and an older campus gets the key on its first update.
- **Antigravity is a named app.** The founding question offers it as an example, founding installs its entry files (`AGENTS.md` and `GEMINI.md`) when the owner names it, and both adapters tell it to resolve under its own name (`--client antigravity`), so it starts proposal-only like any other second app.

- **Job cards.** A pack can ship `job-cards.md`: one card per job the owner hands over, with what it needs, its rules, what done looks like and where the result lands. Founding copies it to `dean/job-cards.md`, the first win is the first card, and the chief of staff reads a card only when that job is asked for. The copy belongs to the owner; no update overwrites it. A pack without cards behaves as before.

### Fixed
- **An update no longer switches a campus to another edition without saying so.** `/update-workspace` compares the campus's edition with the installed plugin's before it writes anything. When they differ it stops, changes nothing, and tells the owner the two ways forward: reinstall the edition the campus was founded with, or start the new edition in an empty folder. Before this, a coach build installed over an education campus relabelled its departments and changed its wiki categories with no warning.
- **An update writes the seat file when a campus has none.** A campus founded before 5.3.0 had no `.campus-os/seat.json`, so every app resolved as unassigned even after the Windows and Linux fix in 5.3.0. The update now asks which apps work in the folder and writes the file; an existing seat file is never rewritten.

### Changed
- **Coach pack: owner-visible wording says "department" and "campus".** Seventeen phrases in `packs/coach/pack.json` (rule notes, one default rationale, one memory category) said "desk" or "office"; cross-department rules now name the coach department (Client Care, Content & Visibility). Wording only: no rule, level, stage or schedule changed.

## [5.3.4] - 2026-11-12

5.3.3 was packaged but never released. Windows field report (a campus on Windows 11, Python 3.14, PowerShell 5.1).

### Fixed
- **A broken Python reads as a broken Python, not a broken campus.** `/campus-doctor` checks once that Python can start in isolated mode before it runs its sub-checks. When it cannot (a damaged install; on Windows it shows as `Failed to import encodings`), the report says so in one line and marks the checks it could not run as not checked, instead of three red campus errors.
- **A byte-order mark no longer stops the doctor.** Windows PowerShell 5.1 puts one in front of text it pipes to a program. The kit manifest and the schedule list are now read with or without it, piped or from a file (`doctor_evidence.py`, `kernel_kit.py`, `check_cron_parity.py`).

### Changed
- The doctor skill and the Kernel preamble say what to type on Windows (`python` or `py -3`) and to pass the manifest as a file path when the shell cannot pipe it.

## [5.3.3] - 2026-11-10

### Fixed
- The pack assembler regenerates a niche build's contract and kit manifest after it edits the build, so the build passes its own packaging gate. Found cutting the first coach build; 5.3.2 was packaged but never released.

## [5.3.2] - 2026-11-10 (packaged, not released)

First coach build. Assembling the coach pack showed that a niche build could keep commands and staff entries for skills it does not ship. 5.3.1 was packaged but never released.

### Fixed
- **A niche build ships nothing that points at a missing skill.** The pack assembler drops a command that names a dropped skill even when the file is named differently (`/plan-lesson` went with `lesson-planner`), filters department rosters down to the skills the build ships, and refuses to finish if a command or roster still names a dropped skill.
- The plugin listing in a niche build names that pack's business (a coach build says "coaching practice", not "education business").
- `/first-week`, `/campus-first-win` and the launch planner skip a step whose employee the campus does not have, instead of sending the owner to a skill that is not there.

### Builds
- `campus-ai-os` (education, the default) and a separate coach build assembled from `packs/coach`.

## [5.3.1] - 2026-11-10 (packaged, not released)

Fixes from an independent review of the 5.3.0 cut, made before either was published. 5.3.0 was packaged but never released; its notes below still describe the release, with these corrections.

### Security
- **Cloud and sandboxed sessions keep the host binding.** Inside a container (Docker, Podman, Kubernetes and similar, or a `container` environment variable) the resolver observes no Linux fingerprint, as on 5.2. In 5.3.0 a sandbox read its own throwaway machine id, so a valid host binding was denied, and `--init-seat` could bind `seat.json` to the container.
- **Seat and host-binding files are written without following links.** A random temporary name, no write through a link at the file or its folder, and `--init-seat` can no longer overwrite a `seat.json` that appears mid-write.
- **Work Orders can't be forged or moved by a satellite.** `wo.py event --field` cannot set the seat, time, event or any key the tool writes. An event counts only from the log of the seat it names; signing, starting, claiming, deciding, changing, verifying, stopping and closing count only from a primary seat. A satellite's new Work Order is saved as a proposal in its own lane. `wo.py status` says how many lines it did not count.
- **Work Order paths stay inside the campus.** `--dir` and the department can't escape the campus or pass through a link, and the ledger append never follows a link.
- **Every documented resolver call runs isolated** (`python3 -I -B`), so a planted module beside the resolver never loads.

### Fixed
- The kernel kit carries `schemas/ledger-line.schema.json`, so the doctor's ledger section and the writer self-check work from the kit.
- The ledger line shape accepts what the resolver writes (`via: unresolved`, null `run_id` and tier). An older `via` word reads as legacy, never as a failure; new lines are still checked strictly.
- `wo.py`: titles with backslashes or quotes are inserted safely, multi-line values are refused, files are read and written as UTF-8 and output is plain ASCII (Windows), and archive folders are skipped on every platform.
- Founding path C and `/import-ai-memory` check the seat before writing shared files (a satellite proposes in its lane), say accurately that files are read in the chat and sent nowhere else, and the brain's rule 1 names their one exception: creating a new file in `inputs/intake/`.

## [5.3.0] - 2026-11-10 (packaged, not released)

Security work carried from the 5.3 train, the fixes from a customer's first-install field report (2026-11-09), GitHub issue #2, and two tools proven on the maintainer's own campus. WO-2026-09-30-10.

### Security
- **SEC-05: write rights come from the seat resolver, never from a file's defaults.** The shared activity ledger follows `owns_clock`, never role: the contract's `ledger_path()` (Python and JS) fails closed, the generated contract states the rule, and the Codex and Gemini adapters give a satellite only its own lane and ledger shard. No kernel writer names the shared ledger by literal path. Gate: `tests/test_sec05_adapter_lanes.py` runs the real resolver for a clock-owner primary, a non-clock primary and a satellite.
- **A second AI app starts proposal-only.** Founding now asks which AI apps will work with the campus and writes `.campus-os/seat.json` from the answer: the founding app is primary and runs the schedules; every other app is a satellite until the owner promotes it. Before this, founding wrote no seat file, so every app on a new campus resolved as an unassigned satellite.
- New kit tools follow the 5.2.15 rule (sibling imports at the end of the path, no bytecode written into the kit).

### Added
- **Seat fingerprint on Windows and Linux (GitHub issue #2).** `resolve-seat.py` reads Windows `MachineGuid` and Linux `/etc/machine-id`; the macOS value is unchanged, so existing seat files keep matching. New owner mode `--init-seat --primary <app> [--satellite <app>] [--clock-owner <app>]` writes `seat.json` once and never overwrites one.
- **Founding path C, "start from what you already have".** `/campus-intake` reads the owner's documents, links and AI memory, writes context files as SEEDED, plays them back, then asks only about the gaps. `/import-ai-memory` gets what ChatGPT or Claude already knows about the owner. Neither sends anything anywhere on its own; files are read in the chat like anything else the owner shares.
- **Work Orders.** `tools/wo.py` plus `templates/work-orders/`: a non-routine build gets a Work Order (job, done means, budget, permissions, stop rules) and its status is computed from events in each seat's own ledger. Departments come from the campus registry. In the kernel kit, so it runs from `.campus-os/kernel/tools/wo.py`.
- **Challenge-First rule** (rule 5 in the chief-of-staff brain): push back once before a price change, a new offer, a new build or anything hard to undo.
- **Coach pack** (`packs/coach/`): the Professional Coach niche manifest, conformant and assemblable. The education pack stays the default.
- **One ledger line shape** for registered and ad-hoc runs: `schemas/ledger-line.schema.json` and `tools/validate_ledger.py` (read-permissive, `--write` strict). Ad-hoc turns log only on an output, a write or a decision. Optional keys reserved for model routing: `provider`, `model`, `tokens_in`, `tokens_out`, `cost`; optional `skill_version`.
- **/campus-doctor** gains a fourteenth section, `runtime_drift` (`tools/check_runtime_drift.py`): each runtime copy of a scheduled job is compared with its `scheduled/` file and drift is reported, never fixed. The ledger section reports mis-typed lines.
- PURPOSE line on kernel playbooks and on promoted skills.
- `/campus-first-win` also offers the active pack's own domain skills.

### Changed
- The task-board tool (`generate_task_index.py`) is copied at founding (kit core), and the task spec's commands point at the path that exists in a campus.
- Install docs lead with Claude Code (`/plugin marketplace add trainingsites/campus-ai-os`) and no longer name a fixed desktop-app menu path. `SECURITY.md` says where the release hash record lives and how to check it on macOS, Linux and Windows. `CODEX-INSTALL.md` explains seats for Codex and Claude on one campus.
- Narrower triggers: the morning brief alone answers "what should I work on"; the strategy council is for real pressure-tests, not a quick idea list, and only inside a campus; the kernel's skill builder says it builds campus skills.
- The chief-of-staff brain's rule 3 is now "One-Page Plan Rule (a Work Order)"; `/update-workspace` inserts the Work Order line and the Challenge-First rule into existing brains.

### Fixed
- `QUICKSTART.md` was headed "v4.1"; root-doc titles are version-neutral, and README and QUICKSTART name the business through the active pack.
- `dean-CODEX.md`'s ledger example used "team" for the dept field.
- Removed the maintainer's own folder names and a machine path from buyer-facing docs.

### Upgrade notes
- `/update-workspace` refreshes the kernel kit (it now carries `wo.py` and the Work Order templates) and inserts the two brain rules.
- A campus with no `seat.json`: run once in a terminal in the campus folder, naming the app that runs schedules: `python3 -I -B .campus-os/resolve-seat.py --init-seat --primary claude-code`. Add `--satellite codex` if Codex also works there.
- Using Codex on an older campus: copy the plugin's `templates/clients/AGENTS.md` to the campus root again so it carries the resolver-driven lane rules.

### Install compatibility
- **Claude (Claude Code, Claude desktop app):** no manifest change and no new install step.
- **Codex:** the `.codex-plugin` manifest is regenerated from the Claude one; the adapter text changed (see Upgrade notes).
- **Gemini:** the adapter follows the same resolver rules; Gemini support is still not claimed.

## [5.2.18] - 2026-10-22

Repairs the four findings of the Codex audit of the public 5.2.17 repository and release (`outputs/2026-10/reports/2026-10-22-campus-ai-os-github-audit.md`, WO-2026-10-22-04; WO-2026-10-20-06).

### Security
- **Runtime writers stay inside the campus (audit F1, P1).** The run-ID minter, the registration-spec writer and the Campus Map followed a planted link out of the campus: `outputs` linked elsewhere put a run (and every draft written into it) outside; a dangling link at the spec created the outside target; a linked `campus-map/` overwrote an outside file. Now:
  - the minter creates the run directory one folder at a time, refuses any link on the way down (the standalone path too), and checks that the result resolves inside the campus; its `results.json` is still opened exclusively;
  - the spec writer (and `--capture-notes`) refuses a link anywhere from the campus root to the file, and writes a fresh temp file renamed into place, which also replaces a read-only copy without the old chmod;
  - the Campus Map refuses a link on the way down to its output folder under the campus, and writes a fresh temp file renamed into place, so a link at the file itself is replaced, never written through (custom output folders get the second guard).

### Fixed
- **Developer install route (audit F2, P1).** The README's `/plugin marketplace add trainingsites/campus-ai-os` (Claude Code) and Codex "Add marketplace" pointed at a repo with no marketplace catalog. The kernel tree now carries `.claude-plugin/marketplace.json` and `.agents/plugins/marketplace.json`, both named `campus-ai-os` with the root plugin as source; Codex CLI 0.163 registers the repo as a marketplace. The buyer's `.plugin`/`.zip` leaves both catalogs out.
- **An edit under an intact stamp is no longer called current (audit F3, P2).** The spec stamp now records the body's sha256; `--check` reports a body that changed after generation as hand-edited, a refresh refuses until the edits are captured as overrides, and the replaced copy is kept as `registration-block-spec.md.bak-{UTC}`. Older stamps without a body hash are compared against a fresh render from the same inputs, or backed up when that cannot be rebuilt.
- **The Cowork kit rule matches the checker (audit F4, P2).** Canon §0 required every manifest file, but founding copies the core tier only, so a healthy new campus failed the written rule. Now: every core file required, on-demand files optional unless the tool about to run is one of them, any present file must match, any unlisted entry fails, the same as `kernel_kit.py check`.

### Added
- `tests/test_containment_5218.py` (14): links at `outputs`, deeper in the run path and at `teams-shared` refused with nothing written outside; a dangling spec link and a linked `.campus-os` refused; stamped edits seen, refresh refused, then captured and backed up; an old stamp still checked; Campus Map folder and file links; the cloud rule and the checker agree on core-only, full and changed kits; both catalogs valid and absent from the buyer file. Mutation-checked: each fix removed makes its fixtures fail.

## [5.2.17] - 2026-10-22

Carries all of 5.2.16 (kernel kit, the Codex F1 repair, the campus finder) plus one fix found while the 5.2.16 audit was under way (WO-2026-10-20-06).

### Security
- **Quarantine never follows a link out of the campus.** The F1 repair added a quarantine for unlisted kit files under `.campus-os/kernel-quarantine/`. If `kernel-quarantine` was a planted link, `install --repair` followed it and moved the unlisted files outside the campus, into a folder and under file names the planter chose. A file of their choosing could land anywhere the owner can write. Now the quarantine refuses a link at `.campus-os` or `kernel-quarantine` and moves nothing; each run creates a fresh folder `{UTC stamp}-{12 hex}` that must not already exist; it only moves into folders it just created; it never replaces an existing entry.

### Added
- Fixtures: a planted quarantine link is refused with nothing moved outside and the file left for the owner (the check still flags it); every quarantine gets a fresh, unguessable folder. Mutation-checked: without the link checks, the first fixture fails.

## [5.2.16] - 2026-10-22 (never published: superseded by 5.2.17 during its audit)

Carries all of 5.2.15 (the Codex audit F1 repair) plus one campus-finder fix, folded in before 5.2.15 was audited, on the owner's call (WO-2026-10-20-06).

### Fixed
- **The campus is found when the host opens the folder above it.** The campus rule only walked up from the working folder. The owner's Cowork mounts `TrainingSites/` while the campus is the child `TrainingSites/Claude-Cowork/`, so `resolve_context.py --find-campus` found nothing from the mount (exit 3), and every team that followed the rule said "install Campus OS first" (reported by the Email Desk session, 2026-10-22). Now, when nothing above is a campus, the finder accepts exactly one campus among the start folder's children: real folders only, hidden folders and links skipped, one level down. Two or more child campuses are never guessed between: `--find-campus` exits 3 and lists them (`several_campuses`), and a concept lookup refuses until the owner picks. A campus above still wins. `--json` now says how it was found (`here`, `above`, `child`). The one owner of the rule, `templates/context-files.md` ("Campus rule"), says the same.

### Added
- `tests/test_campus_finder_5216.py`: the mount-above layout, two children refused, a campus above wins, hidden and linked children ignored, only one level down.

### Known gaps
- `context-weight.mjs` and `/campus-map` keep their own walk-up (the doctor passes `--root`); teams that run with `--campus-root .` from the mount folder should `cd` into the campus first (Email Desk 1.0.2 does).

## [5.2.15] - 2026-10-22 (never published: superseded by 5.2.16 before its audit)

Repairs the one release blocker from the Codex audit of the packaged 5.2.14 artifact (`outputs/2026-10/reports/2026-10-22-campus-ai-os-v5.2.14-codex-audit.md`). 5.2.14 was never published; this release carries all of its kernel-kit work (see the [5.2.14] entry) plus the fix below (WO-2026-10-20-06).

### Security
- **The kit runs only the bytes it checked (audit F1).** The 5.2.14 check compared the files the plugin lists but accepted anything else in the kit, and kit tools import from their own folder. A campus writer could add a stdlib-named module (`tools/secrets.py`) or a bytecode cache stamped to match a real source (`tools/__pycache__/contract.*.pyc`); the plugin-anchored check still said OK, and the minter or the doctor then ran the planted code. Now:
  - `kernel_kit.py check` fails on any file, cache folder or link in the kit that the manifest does not list (`unexpected`), and checks every on-demand file that is present, not only the core tier.
  - Kit tools run as `python3 -I -B` (canon §0, preamble §5, every documented command): the kit folder is never searched before the standard library, and no bytecode is written into the kit.
  - The two tools that import their siblings (`doctor_evidence.py`, `resolve_context.py`) put the kit folder at the end of the import path and, when run as tools, point Python's bytecode cache at an unguessable path that does not exist, so a planted `__pycache__` is never read. The doctor runs its sub-tools the same way (`-I -B -X pycache_prefix=…`).
  - `install` (and `--repair`) moves unlisted files and caches to `.campus-os/kernel-quarantine/{UTC stamp}/` before copying (moved, never deleted) and reports them; a link inside the kit is refused for the owner to remove.
  - The Cowork inline check in canon §0 lists every file and link in the kit (links as `LINK`), so an extra file or a cache fails it there too.
- The doctor's `kernel_kit` line fails on unlisted files and on an unreadable stamp, and its OK wording now says what was checked: "every file present matches the plugin and nothing else is in it" (audit observation 1).
- A malformed `KIT.json` (non-string paths, wrong types) is reported as `stamp_invalid` instead of raising; duplicate paths are checked once; a path outside the kit is reported as changed, never read.

### Added
- Fixtures for both audit probes and for repair: an unlisted module fails the anchored check and does not run under the documented command; a planted cache fails the check and is not loaded by the doctor or the campus finder even if the check is skipped; repair quarantines both and the kit checks clean again; a changed on-demand file fails a core check; a malformed stamp is reported. Mutation-checked: without the cache redirect the doctor runs the planted cache; without the unexpected-file rule both probes pass the check; without quarantine repair leaves the payload.

### Corrections to the [5.2.14] entry
- Its "Known gaps" line "Not yet proven in a live Cowork session" is out of date: the live Cowork gate passed on 2026-10-22 (fresh campus founded with the kit, byte-identical to the manifest; the owner's campus upgraded 5.2.13 -> 5.2.14). 5.2.14 was never published.

## [5.2.14] - 2026-10-21 (never published: failed the Codex artifact audit, F1; superseded by 5.2.15)

The kernel kit: kernel tools now run from a copy inside the campus, so they work in cloud Cowork (WO-2026-10-20-06; James chose option A, 2026-10-21). Test build on the branch; publish only after the Cowork release gate.

### Fixed
- **Kernel tools could not reach the campus in cloud Cowork.** Cowork runs the installed plugin in a cloud container that cannot see the campus; the campus is mounted in a separate device shell with Python but no plugin. Sessions typed run_ids by hand with round placeholder times (`…-000000000`) and skipped every validator, and `/campus-doctor` could not run (Email Desk tests, 2026-10-20 and 2026-10-21). The kernel now keeps a **kernel kit** in the campus, `.campus-os/kernel/`: a mirror of the tools a campus needs in the plugin's own folder layout, stamped with `KIT.json` (kit version + sha256 per file). The tools find their files relative to themselves, so they need no changes. Same pattern as the campus copy of `resolve-seat.py`.
- `tools/doctor_evidence.py` imports its sibling tools under `python3 -I` (isolated mode left the script folder off `sys.path`).
- `/campus-doctor` never edits a team's `results.json`. On the 5.2.14 Cowork test it "fixed" a failing Email Desk file by stamping its own time as `generated_at` and guessing all three completion answers. It now names the file, the missing fields and the owning team, and offers to update or re-run that team.

### Security
- **The kit is checked against the plugin, never against itself** (security review of this branch, 2026-10-21). Anyone who can write the campus (a shared folder, another team, an AI session following injected text) could edit a kit tool and recompute its hash in `KIT.json`; a check that trusts the campus stamp would pass it. `kernel_kit.py check --manifest` takes the expected hashes and version from the installed plugin's `tools/kit-manifest.json`; the doctor anchors on it (this tree's when run from the plugin, `--kit-manifest` when run from the kit) and reports a kit that matched only its own stamp as unchecked, never `ok`. In Cowork the canon has the model hash the kit with its own inline command, not a kit tool, and compare with the manifest it read from the plugin. A changed or `newer` kit is never run; a planted newer stamp no longer blocks repair forever (`install --repair`, on the owner's go).
- **`install` never writes through a symlink.** A planted link at `.campus-os`, the kit folder, a subfolder or a kit file is refused, every write goes to a fresh file renamed into place, and nothing lands outside `.campus-os/kernel/`. `check` counts a kit file that is a symlink as changed.

### Added
- **`tools/kernel_kit.py`** - the one owner of the kit list (`core`, `on_demand`, `plugin_only`, `maintainer_only`); `manifest` (writes/checks `tools/kit-manifest.json`), `check` (file-by-file sha256, and `current` / `stale` / `newer` against the installed plugin), `install` (where one shell sees plugin and campus). Forward-only: a newer kit is never replaced by an older one.
- **Where kernel tools run, defined once:** `templates/run-id-and-interop.md` §0 (the campus copy reaches every installed team, so no team repackages) defines `{kernel}` = `.campus-os/kernel`, the check before first use, and the by-hand fallback (real UTC time, never a placeholder; `run_id_minted_by: "hand"`). Kernel preamble §5 points kernel skills at it.
- `/campus-start` writes the core kit first (file-tool copy where the plugin cannot see the campus); `/update-workspace` item 18 copies or refreshes it on every path, the up-to-date path included; `/campus-doctor` runs from the kit with `--installed-version` and gains a thirteenth section, `kernel_kit`.
- `tools/package.py` refuses to package with a stale `tools/kit-manifest.json`; build gate 8b requires both founding and upgrade to create `.campus-os/kernel/`; `tests/test_kernel_kit.py` runs the kit with the plugin tree deleted and fails when any skill, canon or contract names a `tools/` script that no kit list accounts for.

### Known gaps
- `tools/gen_department_entries.py` (item 12e's org-chart re-derive) reads the whole niche pack and stays plugin-only; where no shell sees the plugin, the re-derive is skipped and said.
- `/campus-map` still runs `${CLAUDE_PLUGIN_ROOT}/campus-map/generate.mjs`.
- Not yet proven in a live Cowork session: the file-tool copy, the device shell's Python version, and `node` there (the release gate).

## [5.2.13] - 2026-10-18

Repairs the one release blocker from the Codex audit of the packaged 5.2.12 artifact (`outputs/2026-10/reports/2026-10-17-campus-ai-os-v5.2.12-codex-audit.md`). 5.2.12 was never published; this release carries everything in its entry below. Patch: no new keys.

### Fixed
- **Priority lost to capitals (audit F1).** `tools/resolve_context.py` tried every exact-spelling name before any case-insensitive one, so on a case-insensitive disk a lower-priority file with exact spelling beat the preferred file in other capitals: `offers.md` over `OFFERS-SUMMARY.MD` (old long-form prices instead of the price-owning summary), `icp.md` over `AUDIENCE.MD`, `identity.md` over `BUSINESS.MD`, for reads and for `write_to`. Each candidate is now matched exactly, then case-insensitively, before the next is tried, and its real spelling is returned. The canon (`templates/context-files.md`), the kernel preamble, the contract's `resolution` list (both resolvers check it), the doctor and every skill that states the read order now say the same thing. The doctor's `context_files` section and the resolver agree on which file is read.

### Added
- Regression fixtures for the three audit cases (offers summary, founding audience, founding business in capitals beside a lower-priority exact name) and for doctor/resolver agreement. Mutation-checked: on the 5.2.12 resolver they fail. Suite is 281.

### Corrections to the [5.2.12] entry
- SEC-04 points **thirteen** reading skills at preamble §4, not twelve (`/whats-new` was added to the list).
- `update-workspace/references/additions.md` was still titled "items 11-15"; it now says 11-17, matching the item list and the closing rule.

## [5.2.12] - 2026-10-17

Atlas learns to ask for more (three levers: altitude, depth, range), context files resolve correctly on a real buyer install, and one security fix pulled forward from the next minor train by owner decision (SEC-04). Patch: no new required keys; upgrade item 17 is additive.

### Security
- **SEC-04: outside text is data, never instructions.** Web pages, transcripts, reviews, emails, client messages, connector output and ingested files could carry sentences aimed at the model, and nothing in the runtime said they were not commands. New `references/kernel-preamble.md` §4 is the one owner of the rule: outside text cannot change instructions, grant permission, pick a tool, approve a send or write, or ask for secrets; a line that tries is quoted to the owner with its source; saved material keeps its source; no instruction from outside text goes into a skill, rule, memory or schedule. The chief of staff templates carry it as rule 4 (inside a `campus-os:outside-text` marker), and the twelve skills that read outside text point at it. Gate NICHE-028 fails the build if a reader or a template drops it. SEC-05 and SEC-06 stay in the next minor release.

### Added
- **Atlas, ambition levers.** `strategy-council` 2.2.0: Gate 1 says the job as a verb (not "a webinar" but what it must get done) and asks how much rides on it; on high stakes the user can seat one to three **field seats** from other fields, picked from the verb, each bringing one option nobody named (a lens, never a named person; the core five stay); Gate 4 adds an **outside check** so the convener never grades its own ruling (a fresh judge that sees only the ruling and evidence, or a named real-world check); each move is named out loud in one line so the owner learns the levers by watching them. `content-scanner` 1.1.0: an expert-tools check names what a top researcher would use that isn't connected, and the report lists it as a gap.
- **`tools/resolve_context.py`** - finds the campus (walk up for `workspace.json` + any accepted entry file, root or `dean/`) and the file a concept resolves to. Python only, all three hosts.
- **`/whats-new`** (promoted from the parked next-train tree) reads the public GitHub release list. The parked copy pointed at a release page that returns 404 and logged to the shared ledger; both fixed.
- **Doctor `context_files` section** - reports a concept held in two files (the founding file plus a separate canonical-name copy, e.g. `audience.md` + `icp.md`) and offers a merge. Intended pairs (offers summary + notes) are not reported.
- Gate NICHE-013D - fails the build if a kernel skill routes a write to `icp.md` / `identity.md` / `icp-summary.md` or requires `about-me/`.
- `tests/test_kernel_cargo_5212.py` - fresh-folder campus (not named `Claude-Cowork`, `AGENTS.md` entry) resolving all seven concepts, shadow and price-authority cases, both gates, the Atlas levers and SEC-04. Suite is 279.

### Fixed
- **Context files on a real install.** The canon tried the canonical name first, so a thin `icp.md` / `identity.md` written later hid the full `audience.md` / `business.md` from founding. Read order is now founding name first (offers keeps `offers-summary.md` first: it owns every price); `contracts/campus.json` carries `read_order` per concept and both resolvers return it. The contract no longer claims founding writes `brand.md` (nothing does). `grill-me` and `session-capture` route facts to the resolved file, never a new `icp.md`. `first-week` stopped requiring `about-me/about-me.md`, which nothing writes, so it no longer sends every founded owner back to `/campus-start`; `wiki-query` and the map read `workspace.json` `assistant_name` instead of `about-me/`. The campus copy of the canon is refreshed on upgrade (12e), so installed teams pick up the new order without repackaging.
- **Upgrade steps that never ran.** The v5.2.4 seat-resolver refresh had no numbered item in `/update-workspace`, so the closing rule never named it. Item 17 runs it and the 5.2.12 additions on every path.
- **Founding matched only part of the org chart** (found on the 5.2.12 cold test). Founding made one folder per entry in the pack's `departments[]`, which lists only the departments the pack staffs, so Operations, Finance and People sat on the org chart with no folder; the close said "five of the eight" and the doctor flagged the folders. Founding now makes one folder per department on the org chart (every `type: department` entry except Dean's office), and gate NICHE-022 fails the build if a pack department has no org-chart entry. The close also bundled the department-rename question with the next-step offer; the rename is now its own turn and the close asks one question. Owner-facing text names a department only by its registry label (the close had said "Education" for the department labelled Teaching), and `/full-onboarding` no longer carries a typed five-department list.
- **Skills still spoke the v3 org.** Eight kernel files named a "Content Department" and a "Customer Department" (Clients / Coaching / Students) that no campus has had since the staff departments arrived; `morning-brief`, `weekly-review`, `launch-planner`, `course-builder`, `lesson-planner` and `social-planner` read `content/memory.md`, `marketing/memory.md` or `sales/memory.md`, paths no founded campus has, so the morning brief could never see department work; `first-week` Day 4 read a `library/skill-to-department-map.json` that does not exist. Kernel preamble §2 now defines departments once (the org chart, by label, folder per `dept_dir` or `departments/{id}/`), every one of those skills reads through it, and gate NICHE-029 fails the build on a typed department name or a v3 department path.
- **No staging archives in the campus.** The cold install left a `campus.tgz` the model had used to stage the scaffold; on a host where campus files can be created but not deleted, it could not be removed. Kernel preamble §2: write each file at its final path, never through an archive or temp copy.
- The council's Gate 1 asked the sharpening and stakes questions in one message; the stakes question is now its own turn.
- `/campus-doctor` reports every evidence section. It was told to explain "eleven" sections and had no rule for the new `context_files` one, so the line was dropped; a fixture now ties the count and the per-section rules to the tool's section list.
- `tools/mint_run_id.py` filed a run under the wall-clock month instead of the month of the `now` it was given; a fixture pinned to September began failing on 1 October.

### Changed
- Dean templates (`templates/dean-CLAUDE.md`, `templates/dean-CODEX.md`): End of Session now opens with a save-as-you-go rule. Decisions, open items and things worth keeping go to `daily/{today}.md` (and `wiki/` when they compound) the moment they happen, not only at wrap-up, because most sessions end without one. Found on the owner's own campus 2026-10-13 (WO-2026-10-13-01). Needs the Cowork release gate before it ships.

## [5.2.11] - 2026-09-23

Repairs the one release blocker from the Codex re-audit of the packaged 5.2.10 artifact, and carries the pack-neutral wording the first niche builds need. Patch: no new keys, no migration beyond the version marker.

### Fixed
- **Write instructions still sent a co-primary to the shared ledger.** An assigned Claude Code or Codex client resolves `role: primary` with `owns_clock: false`, but the sanctioned team-plugin wording in `templates/ledger-paths.md`, `/campus-first-win` and `/full-onboarding` told it to append to `dean/.activity.jsonl`. They, and the same wording in `hr-recruit`, `promote-skills`, `templates/model-routing.md`, `playbooks/README.md` and the one-recording playbook, now name the ledger the seat resolves to; only the clock owner writes the shared file. Team plugins cut earlier keep the old phrase until their next release; `ledger-paths.md` says how to read it.
- `QUICKSTART.md` was headed "Campus AI OS v4.1", also in the public 5.2.9 release. Root doc titles no longer carry a version.
- `README.md` and `QUICKSTART.md` said "education business" whatever the pack; the business noun now comes from the active pack.

### Changed
- `/campus-first-win` also offers the active pack's own domain skills when the pack declares any beyond the three defaults; the education default is unchanged.

### Added
- `tests/test_ledger_writers_5211.py` - runs the real resolver for a non-clock primary and fails if any shipped instruction writes the shared ledger without the clock-owner qualifier.
- `tests/test_kernel_cargo_5211.py` - doc titles, pack-neutral business noun, first-win pack skills.

## [5.2.10] - 2026-09-20

Co-primary reaches every written contract, and the minimum pack plumbing a second niche pack needs. Additive: every new `pack.json` key is optional, a campus founded on 5.2.9 needs no migration beyond the version marker, and the education build assembles file-identical to the source tree.

### Fixed
- **Co-primary had not reached every contract.** The resolver sends a primary client that is not the clock owner to its own ledger shard, but `templates/ledger-paths.md` still said "Primary: `dean/.activity.jsonl`", the generated contract listed `claude-code` and `codex` as satellite by default, and the brain templates and the Codex adapter told every client to append to the shared ledger. All now say one thing: append only to the ledger `resolve-seat.py` returns; only the `clock_owner` client writes the shared ledger. `contracts/campus.json` gains `seat.ledger.clock_owner`, `co_primary` and `write_rule`; `seat.ledger.primary` keeps its value because readers resolve the shared ledger by that key. The remaining Codex lane rules stay with SEC-05.
- **A second in-tree pack failed NICHE-024 by design.** `templates/registry.json` is one derived file; the label-parity check compared it against whichever pack was being checked. It now belongs to the active pack. A non-active pack's registry template is derived when that pack is assembled, by the same generator, so no second copy is stored.
- `tools/build_niche.py --check` and `tools/gen_department_entries.py` defaulted to the literal `education`. Both now default to the active pack.

### Added
- **`packs/active.json`** - one pointer, `{"active_pack": "..."}`, naming the pack this tree is built for. `campus-start`, its interview reference, `wiki-ingest` and `wiki-query` resolve the pack through it; `--assemble` rewrites it for the pack being built.
- **`shared_skills[]`** (optional, `pack.json`) - a pack borrows another pack's domain skills. `--assemble` keeps them; ownership is read from the skill's own `pack:` tag, so it still resolves after the owning pack's folder is removed.
- **`hires[]`** (optional, `pack.json`) - a pack may carry pre-vetted hire manifests in the `.campus-os/hires/*.json` shape. Key and gate only; routing to a hire is not part of this release.
- Gate checks **NICHE-025** (active pack pointer; no skill spells a pack folder), **NICHE-026** (shared skills) and **NICHE-027** (pack hires: full 40-character pin, https repo, license, never above `draft-only`).
- `tests/test_phase7_pack_plumbing.py` - 17 fixtures: contract and template parity with the resolver, the pointer, a second in-tree pack, per-pack registry derivation, the file-identical round trip for the active pack, borrowed-skill survival, and hire-manifest rejection cases.
- `packs/professor/pack.json` declares `shared_skills` and an empty `hires`.
- `README.md` links to the public repository.

## [5.2.9] - 2026-09-14

First release prepared for public GitHub distribution (`trainingsites/campus-ai-os`). Scope is the co-primary seat model only; SEC-04/05/06 ride a dedicated security train at 5.3.0 or later by owner decision (2026-09-13).

### Fixed
- `tests/test_phase0_coprimary.py` doctor fixtures issued their host binding against the frozen fixture clock while the doctor reads wall-clock time, so the suite began failing on its own three days after 5.2.8. The two doctor fixtures now issue the binding relative to real time; resolver fixtures keep the frozen clock.

### Changed
- **Co-primary seats.** A campus may now designate more than one client `primary` in `seat.json`, so an owner can work from any installed client and finish the job there — closing tasks, writing memory and wiki — instead of filing a proposal for another seat to merge. Single-primary campuses are unaffected: a `seat.json` with one primary and no `clock_owner` resolves exactly as before.
- **`clock_owner` names the single scheduling seat.** One campus, one clock is preserved by configuration rather than by role: `clock_owner` is the one client that runs recurring jobs, holds the host binding, and writes the shared ledger `dean/.activity.jsonl`. Every other primary appends to its own shard. The resolver returns `owns_clock` so a client can tell the difference. A co-primary `seat.json` without a valid `clock_owner` is refused and the caller stays satellite.
- **Doctor is co-primary aware.** Check 11a treats a stamp from any configured primary seat as expected instead of unresolved attribution, while an unrecognised seat is still reported. Check 11d validates the host binding against the clock owner; previously a co-primary config made it advise deleting a valid binding.

### Security
- Unchanged boundary, re-proven by fixture: an unknown machine fingerprint, an unassigned client, a sandbox with no binding, an expired binding, and a binding issued for a client that is not the clock owner all still resolve satellite. Co-primary widens who may write on one recognised installation; it does not widen what counts as recognised.

### Added
- `tests/test_phase0_coprimary.py` — 17 fixtures covering co-primary resolution, clock ownership, ledger routing, the unchanged satellite boundary, config integrity, legacy single-primary behaviour, and the two doctor checks. Suite is 226 tests.

## [5.2.8] - 2026-09-11

### Removed
- **Campus Map public/sales-demo build.** By owner decision after the 5.2.5 security audit, the map is private-only. `--public` (and `PUBLIC=1`) now exit with code 2 and a message; no `campus-map-public.html` can be produced. The 5.2.7 deny-by-default public schema is retired with it. A private map is never shared, so no "safe for strangers" mode exists to get wrong.

### Changed
- `campus-map` skill and command describe the map as private-only and document `--no-remote-fonts` / `CAMPUS_MAP_OFFLINE=1` for a no-network build. CSP and brand-field validation from 5.2.7 remain on every build.

### Security
- Nothing new. 5.2.6 and 5.2.7 closed every finding in the Campus Map generator; 5.2.8 removes the public output path so the SEC-01 class cannot recur. Still open from the audit, for a later train: SEC-04 (untrusted-content section in the instruction chain), SEC-05 (Codex adapter lane rules), SEC-06 (signed release provenance).

## [5.2.7] - 2026-09-11

### Security
- **Campus Map `--public` build now denies by default (SEC-01).** A public map carried raw ledger text and the full bodies of every linked document, brief and report. It now carries aggregates and kernel labels only: no ledger text, file paths, document bodies, brief or wiki titles, result rows, OKR or focus text, and no documents are read at all in public mode. Affects 5.0.0 through 5.2.6.
- **Brand and orchestrator fields could become markup (SEC-03 remainder).** `brand_name` reached `<title>` unescaped and font fields reached CSS unvalidated. The title is escaped, font names and the font import URL must match a narrow grammar or fall back to defaults, and remaining client-side sinks (staff line, scheduled last-run) are escaped. Affects 5.0.0 through 5.2.6.
- **Content Security Policy on every generated map.** Only the generator's own inline script (by hash) may run; styles inline; no other origins.
- **No network request from public builds (SEC-07).** Public maps and `--no-remote-fonts` (or `CAMPUS_MAP_OFFLINE=1`) builds load no web fonts. Private builds still load Google Fonts by default and say so in `SECURITY.md`.

### Added
- Fixtures: public-build canary across ledger, outputs, briefs, results, wiki, goals, scheduled and brand sources; malicious brand and orchestrator fields; CSP and no-network assertions.

## [5.2.6] - 2026-09-10

### Security
- **Campus Map generator: path traversal and symlink escape out of the campus root.** A ledger `output` path such as `outputs/../../secret.txt` passed the root check and its contents were inlined into the generated map, including `--public` builds. Paths are now rejected on any `..`, empty segment, URL scheme, absolute or drive form, or control character, and every document read is proven by real path to live under the campus root as a regular file. Affects 5.0.0 through 5.2.5. Reported by the Codex security audit of the 5.2.5 archive.
- **Campus Map inline viewer: stored XSS through markdown link targets.** Quote characters were not escaped and link targets were emitted verbatim, so a crafted link in any linked markdown file became a live event handler. Quotes are now escaped and link targets are limited to relative paths and http(s)/mailto. Affects 5.0.0 through 5.2.5. Same report.

### Added
- `CHANGELOG.md`, `SECURITY.md`, `README.md` ship with the kernel.
- Fixtures `test_campus_map_security.py` and `test_security_packaging.py`; the packager refuses to cut without a changelog entry for the version.

## [5.2.5] - 2026-09-09
### Fixed
- Doctor: a missing `seat.json` reports as not-applicable rather than red; exit code 1 whenever any line is red, per the skill contract. Found by the Cowork 5.2.4 cold install. <!-- version-literal-ok -->

## [5.2.4] - 2026-09-09
### Added
- Host binding for seat resolution; offers canon; ledger-paths promotion.

## [5.2.3] - 2026-09-08
### Fixed
- Registration spec is materialized on every upgrade path, not only the baseline path. Owner content in a kernel canon now shows the diff and asks rather than overwriting.

## [5.2.2] - 2026-09-08
### Fixed
- Doctor evidence ledger section skips `#` header comment lines.

## [5.2.1] - 2026-09-08
### Fixed
- Doctor version-lockstep check routes an owed upgrade to `/update-workspace` instead of a bare stamp.

## [5.2.0] - 2026-09-08
### Changed
- Single kernel tree; version lockstep across ten homes enforced by the packager; Codex manifest derived from the Claude manifest; machine-readable contract regenerated at cut.
