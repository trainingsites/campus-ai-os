# Manual checks - what the evidence command does not measure

Companion to `/campus-doctor` step 4. These read the campus with ordinary file
reads and a little judgment. Each one is short, framed as an opportunity where
it can be, and never repairs anything without a yes.

## Write test (step 1) - why a fixed filename

On network shares, external volumes and FUSE mounts the delete can fail while
the write succeeds. A random or timestamped name would leave one new orphan
file per doctor run, forever - a health check littering the owner's campus
and then telling them to ignore it. `active-work/.campus-write-test` is
overwritten each run, so the worst case is exactly one harmless dotfile
(v5.0.5, after a v5.0.4 cold-install finding).

## Founding interview still a conversation? (old 2b - kernel self-check)

Read the installed `campus-start/SKILL.md`. It MUST contain the explicit
no-batching rule ("NEVER BATCH THE FOUNDING QUESTIONS") and must NOT contain
wording that reads as permission to ask several founding questions at once
(for example "ask all four ... questions below"). Either condition failing ->
"The founding interview could collapse into a single form. That removes the
pushback on vague answers, which is the only quality check in setup." This is
a product-integrity check on the kernel itself, not on the owner's data:
report it, never try to repair it - a mismatch means the installed package is
wrong and needs a corrected build. *Rationale:* v4 introduced the permissive
wording and it shipped through v5.0.1 because a fresh founding is the only
path that exercises it. Rules that matter ship as code that checks them.

## Setup completeness (old 4)

Read `shared/setup-progress.md` and report EVERY row that is not COMPLETE, in
priority order (voice -> goals -> audience -> offers -> tools), framed as
opportunity:

- `DEFAULT` -> "[--] {File} still default" + one line on what it unlocks
  ("Dean writes better emails once he knows your voice - 60 seconds whenever
  you're ready").
- `SEEDED` or `DRAFTED` -> "[--] {File} seeded from founding - worth
  enriching" (say "fix my {file} file" to correct it in 60 seconds).

COMPLETE rows are not listed. Report all non-COMPLETE rows so nothing hides
(the notebook-QA bug: only voice showed when tools was DEFAULT too). Two or
more rows open -> add: "Want to knock these out in one sitting? Run
/full-onboarding - it does them all and picks up where you left off."

## Recent work where it belongs? (old 6a)

If the ledger shows deliverables recently but `outputs/` inside the campus is
empty, warn: "Recent work may have been saved outside your campus folder -
ask me to find and move it."

## Structure matches? (old 6b)

`workspace.json -> structure` (departments / clients / projects / mix) against
the folders actually present. Flag drift in one line; never create folders to
"fix" it.

## Playbooks registered? (old 8)

`.campus-os/registry.json -> playbooks[]`: each entry has `playbook`,
`stages`, `recurring`, `done_check`. One line: "{N} playbooks registered". A
missing done_check is an opportunity, not an error.

## Unregistered real departments - offer, never force (old 8a-i)

When the staff section reports orphans, or the campus runs working department
folders whose names have no matching `type: department` registry entry, the
org chart is undercounting the owner's REAL staff. That gap is honest, not
broken. Do NOT force the shipped departments on them and NEVER rename theirs.
Offer once, flag-only: "[--] Your org chart isn't counting {N} departments you
already run ({their names}) - say 'register my departments' and I'll add them
under your own names (never mine)." Only on an explicit yes add one
`type: department` entry per real department using THEIR name and a slug
derived from it, assigning the skills already associated with it. Existing
entries are never renamed. Nothing to register -> show nothing here.

## Connections (old 8b) - always shown, opportunity line

Read the `connections` context RESOLVED through `CONTEXT_CANON` (canon name ->
each legacy alias -> case-insensitive match), never a filename typed here.
Report ONE line: "Connections: {N} detected (email OK, community OK ...) -
highest-value missing: {calendar}." Pick the single highest-value missing
connector (calendar and CRM rank high for this audience). **Name the
connector and stop.** Do NOT attach a business outcome, revenue figure or
target - a v5.0.4 cold install produced "the one thing standing between me
and your 10 calls a week"; a number the owner cannot trace is a fabricated
metric, and the first report is the worst place to spend that trust. No
connections file resolves, or it is still DEFAULT -> "Connections: not mapped
yet - tell me what runs your email, community, and calendar and I'll wire
them." `[--]`, never an error. *Rationale (v5.1.1):* this check once named the
file founding writes while the canon called the concept by another alias and
six starter employees read a third name nothing wrote; resolve through the
one owner, never name the file.

## Backup reminder (with the ledger line, old 9)

One line: where their campus folder is and to include it in whatever backup
they already use.

## Installed-but-unregistered teams (old 3, on request)

When the owner asks why a team is missing, compare installed team plugins
against `teams[]`. Unregistered -> offer to add a stub entry from its README.
Registered but not installed -> say so; never delete the entry.
