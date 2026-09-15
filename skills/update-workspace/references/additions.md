# Additions items 11-15 - rules, idempotency, and why each one exists

Companion to `/update-workspace` Step 4. These run on EVERY upgrade path (the
closing rule), because an additions item some paths skip is one that silently
never runs for the campuses that need it most. Each is additive and
idempotent: a campus that already has it sees a no-op.

## 11 - v4 additions

**a. Version marker, three targets, all `OS_VERSION` resolved at runtime from
`PLUGIN_MANIFEST` - never a hardcoded literal.**

1. `workspace.json` -> `version`.
2. `.campus-os/registry.json` -> EVERY entry whose `type` is `kernel` (today
   `dean`, `campus-ai-os`, `atlas` - but read the type, never this list).
   Match on `type: kernel` first, then on `team`, never on team alone. Two
   entries sharing `team` AND `type: kernel` -> stamp NONE of that pair and
   report it: an ambiguous target is a question for the owner.
3. `.campus-os/registry.json` -> the top-level `campus_os_version` key (add
   it if absent - it usually is on upgraded campuses).

*Why target 2 names a type (v5.1.3, first real upgrade of a live campus):*
the step said "the `campus-ai-os` entry", singular. That campus held two
records under the name - the real `type: kernel` one and a stray
`type: authored-skill` at 1.0.0. Matching by name hit both, quietly promoting
the stray and hiding it from the check that would have flagged it. A bad
read returns nothing; a bad write manufactures a fact. Build-gate check 18
fails the build if this step stops naming a type.

*Why target 2 stamps by TYPE ALONE (v5.1.4):* Atlas folded into the kernel
at v5.1.0 and was never added to the list of names, so the first real
upgrade left kernel `campus-ai-os` at 5.1.3 and kernel `atlas` at 5.1.2. The
run refused to stamp and asked, which was correct. A list of team names
maintained by a person is only correct until the next fold-in; read the
type. Build-gate check 21 fails the build if the shipping `type: kernel`
entries hold more than one version. (This step existed before and STILL
drifted when it hardcoded `5.0.0`: the defense against drift cannot itself be
a hand-maintained literal.)

*Why target 3 (v5.1.1, instance seven of the founding/migration parity
class):* founding writes the registry fresh from the template and gets every
top-level key; migration created the registry only when absent and stamped
targets 1 and 2. Every upgraded campus was permanently missing the key while
every upgrade reported success.

**a-ii. Top-level registry keys - the CLASS, not this one key.** Compare the
top-level keys of `.campus-os/registry.json` against `templates/registry.json`.
Any key the template has and the campus lacks, add with the template's value
(or the resolved value: `campus_os_version` = `OS_VERSION`, `updated` =
today's date - an upgrade IS an update, and a registry that says it was last
touched two versions ago tells the owner something false). Never remove or
overwrite a key the campus has; never touch `_notes` or any `_`-prefixed
commentary key. Today's keys: `campus_os_version`, `updated`, `teams`,
`playbooks`. Build-gate check 14 requires every template key to be named in
the skill, so a new template key fails the build instead of stranding
upgraded campuses (`updated` was the second key it caught, on its first run).

**b. `playbooks[]`** - add if absent, a top-level array sibling to `teams[]`,
with the two canon playbooks that ship in the box
(one-recording-to-a-week-of-content, weekly-reset): fields
playbook/version/department/owns/triggers/done_check/results/permission/
stages/recurring. Never touch existing `teams[]` entries.

**c. Kernel entries to full spec** - upgrade the `dean` and `campus-ai-os`
entries to `type: kernel` with the full field set (owns, triggers,
done_check, results, permission). The doctor validates these like team
entries.

**d. Campus-systems catalog** - add the `type: systems` / `team:
campus-systems` entry from `templates/registry.json` verbatim if absent: the
platform catalog, pure platform content, identical on every install. If a
`type: systems` entry exists, SKIP - never add a second, never edit it. This
is what lets a migrated campus read "20 campus systems" in the doctor's
staff line.

**e. `.campus-os/scan/`** - create the folder (empty); hr-registry writes
latest.json/previous.json here on first run. (Scaffold parity with founding:
build-gate check 8b.)

**f. `.campus-os/model-routing.md`** - copy from `templates/model-routing.md`
if absent: the routing policy (four pins, publish pin non-removable, light
default). Owner edits it to enable Lite mode.

**g. Folded-in workforce governance** - hr-registry, hr-review, hr-recruit,
hr-router ship in this plugin. If a standalone "AI HR Team" plugin is still
installed, say once: "Your HR skills are now built in - you can uninstall the
separate AI HR Team plugin." Never uninstall it yourself; leave its retired
registry entries as-is.

**h. Playbook-routing rule** into `dean/{ENTRY_FILE}` - block, marker and
insertion rules in `baseline-items.md`.

That is the entire 3.2 -> 4.1 migration: additive registry keys, two new
`.campus-os` files, one additive block in the entry file.

## 12 - v5.1 additions

**a. `atlas/config/`** - create (empty). The strategy and research team's
private config lands here as `niche.md` on first `/atlas-setup`; campus
context stays the source of truth. campus-start creates the same folder at
founding - build-gate check 8 enforces the parity (SOP standing gate (a),
the bug class that has bitten six times).

**b. `atlas` registry entry** - if `teams[]` has none, append the
`type: kernel` entry from `templates/registry.json`. Never touch existing
entries.

**c. Folded-in strategy and research** - same pattern as 11g. If a standalone
"Strategy & Research Team" plugin is still installed, say once that it can be
uninstalled. Never uninstall it yourself; leave its entries alone.

**e. The three kernel canons - copy and OVERWRITE if present.** Before
overwriting, diff the campus copy against the template: text the template
never had is OWNER content living in a kernel-owned file (found on the 5.2.2
sign-off: a campus copy of `ledger-paths.md` carried the campus's own
seat-resolver instructions). That is a prime-directive conflict - show the
diff and ask; never overwrite it silently, and tell the owner the text belongs
in their entry file, not in a canon the kernel refreshes. These are the
only files this skill refreshes rather than creates-if-absent, and
deliberately so: they hold no owner data, they are pure kernel content, and
every installed team resolves through the CAMPUS copy, so refreshing them is
what lets a canon fix reach every team without any repackaging. campus-start
writes all three at founding - build-gate check 8 enforces the parity.

- `.campus-os/context-files.md` from `templates/context-files.md` - the
  shared-context canon, one owner of every context filename and alias. *Why
  owed (v5.1.1):* the canon lived inside one skill's references and six
  plugins bundled their own copies; three still listed aliases wrong since
  v4.1.4.
- `.campus-os/ledger-paths.md` from `templates/ledger-paths.md` - the
  activity-ledger canon (Seat Contract Phase 2): which ledger file THIS seat
  writes, which files a reader merges. *Why owed:* 12 shipped teams appended
  the primary ledger by literal path; on a folder-sync transport a satellite
  doing the same is the two-writers-one-file corruption case.
- `.campus-os/run-id-and-interop.md` from `templates/run-id-and-interop.md`
  (5.2.0 Phase 3.5) - run-id minting, one run-directory shape, results
  envelope v1.1, completion-only floor, ledger-lint. Every team's copy is a
  <=5-line delta naming the campus copy. *Why owed:* eleven teams each
  bundled an 86-line copy; they drifted (three run_id shapes, two
  `schema_version`s) and none could be fixed once.

**g. Org chart - RE-DERIVE, do not preserve.** Run `python3
tools/gen_department_entries.py --campus {campus_root}`. The one place an
upgrade regenerates rather than appends, and correctly: the staff-org entries
are DERIVED from the shipped skills' `department:` frontmatter, not
owner-authored. Item 11d creates the catalog only when absent and never
touches `teams[]`, so the roster froze at whatever kernel first wrote it -
every release that added skills left upgraded campuses with a stale roster
while reporting success (measured: "28 employees + 14 campus systems" on an
upgraded campus against "23 + 20" founded, six Atlas internals missing, no
`dean-office` entry). The prime directive holds: `employees[]` is
kernel-derived and regenerated wholesale; `employees_added[]` is owner-added
and never touched (on the first re-derive, names in the old `employees[]`
that are not shipped skills move there automatically); a department the
owner registered under their own name (the doctor's "register my
departments" offer) is preserved untouched - the generator replaces only the
entries it owns; every other `teams[]` entry is untouched. Report before and
after staff lines in Step 5. Idempotent.

**h. Graceful-degradation cleanup** - if `dean/{ENTRY_FILE}` routes to
`/atlas-think` behind a guard like "if the Atlas plugin is installed", the
guard is dead (Atlas ships in the kernel). Mention it once in Step 5 and
offer to drop the condition; never rewrite the owner's text without a yes.

## 13 - v5.1.8 additions

**a. Starter department entries.** For every `type: department` entry in
`templates/registry.json` (today that adds `operations`, `finance`, `people`
- read the template, never this list) that has no `type: department` entry
with the same `team` in the campus registry, append the template's entry
with an empty `employees[]`. Match on type AND team, never name alone (item
11a's lesson). Never touch existing department entries - owner rosters and
pack relabeling stand. *Why on upgrade:* a fresh founding gets these from
the template; every existing campus would not, and a team registered under
one of the new ids would be invisible on the org chart (found on the first
cold install, 2026-08-31). Write-side scaffolding strands every
already-founded campus; this is the read-side half.

**b. Department enum line in the spec copy** - superseded by item 8: the
campus copy is materialized from the template plus
`.campus-os/registration-overrides.json`, so the enum line is always the
template's values followed by the owner's extras. Run the materializer's
`--check`; if not `[OK]`, item 8 already did (or refused with a reason).
*History:* this step once replaced ONE line by hand, which is how the copy
became unreconcilable once type/status lines arrived.

**c.** Report both in Step 5: departments added (or "already present"), enum
line updated (or "already current").

## 14 - v5.1.9 additions (read-side only)

The context budget ships as two tools (`tools/context-weight.mjs`,
`tools/context-prune.mjs`) and the doctor's weight section - all read-side,
reaching every campus the moment the plugin is installed. Run `node
tools/context-weight.mjs --root {campus_root}` and put its one verdict line
in the Step 5 report so the owner leaves the upgrade knowing the number.
AMBER or RED -> say /campus-doctor can propose an archive (propose, never
perform). UNKNOWN (exit 3) -> report the finding line, never restate the
lower bound as the number. *Why no write:* the template's budget line reaches
only newly founded campuses by design; teaching the tool to read every campus
is what reaches the ones that already exist.

## 15 - v5.1.10 additions (read-side only)

The evidence-layer repair (CI-01 to CI-05 from the 5.1.9 cold install) ships
inside `tools/` and the doctor's wording: explicit seat-identity states,
recursive entry-chain measurement with cycle detection, explicit scheduler
states with an always-valid `--json`, unresolved (never misclassified)
historical seat attribution, opt-in archival. Nothing is written. Say once in
Step 5: (a) the weight verdict has a fourth band, UNKNOWN - report the
finding, not the number; (b) `context-prune` moves only entries marked
`[archive-eligible]`, so a campus that relied on age-based proposals sees
"no eligible units" until the owner marks some. Never mark entries for the
owner.

## 16 - v5.2.0 additions (every campus)

**Materialize the registration spec.** `python3
tools/materialize_registration_spec.py --campus-root {campus_root}`: output =
`templates/registration-block-spec.md` + the owner's
`.campus-os/registration-overrides.json` + a stamp line recording both. If it
REFUSES because the campus copy is hand-edited with no stamp, run
`--capture-notes` first (the owner's non-template lines become overrides;
report them in Step 5), then materialize. *Why an additions item (found on the
5.2.2 sign-off, 2026-09-08):* this lived only as baseline item 8, which every
4.x-or-later campus skips - so no upgraded campus ever got a materialized spec
while every upgrade reported success. An additions item some paths skip is one
that never runs for the campuses that need it most; the closing rule now runs
it on every path. Idempotent: a current spec is a no-op.

## v5.2.4 additions (every campus, additive only)

**a. Seat resolver refresh.** Copy `tools/resolve-seat.py` to `.campus-os/resolve-seat.py`, overwriting if present - it is pure kernel code, holds no owner data, and 5.2.4 is the first kernel that ships it (before 5.2.4 the resolver was campus-local, written by the seat-identity fix of 2026-09-04). Back up the campus copy first if it differs. Never copy `seat.json` or `host-binding.json` from anywhere: both are per-installation and never travel.

**b. Host binding, told not done.** If `.campus-os/seat.json` names a primary client that runs sandboxed (Cowork), tell the owner once: issue the binding from the host with `python3 .campus-os/resolve-seat.py --issue-binding --client <primary-client>` and install the heartbeat from `templates/host-binding-heartbeat.plist` (every 6 hours; TTL 12 hours, so one missed beat survives and two go dark on purpose). Add `.campus-os/host-binding.json` to the campus `.gitignore` and to `sync-manifest.json` `never_sync`. This skill never issues a binding itself: issuing requires the fingerprint, and a session that can observe it does not need one.

**c. `ledger-paths.md` canon (12e) now carries the resolver instruction** that campuses had been holding as owner text since the Seat Contract. On refresh the diff against a post-contract campus copy should be empty or additive; if the campus copy carries text the 5.2.4 template lacks, that is still owner content - show and ask.

