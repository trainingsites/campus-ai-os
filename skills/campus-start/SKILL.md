---
name: campus-start
description: >
  Found a new AI-native business campus in about 5 minutes: hire-an-AI-staff
  frame, renamable chief of staff, four questions one at a time, a workspace
  built to match; niche framing from the active pack. Use when
  the owner says "/campus-start", "set up my campus", "found my campus", or
  when no campus exists.
version: 5.3.8
department: kernel
---

# /campus-start - Found Your Business (about 5 minutes)

A founding moment, not a software install. Scripts and detail:
`interview.md`, `scaffold.md` in this skill's `references/`.

**Platform resolution (do this FIRST):** resolve `PLUGIN_MANIFEST` and
`ENTRY_FILE` per `PLATFORM.md` at the plugin root. **Never hardcode either.**

**Version resolution (second):** `OS_VERSION` = `PLUGIN_MANIFEST` ->
`version`. **Never write a hardcoded version literal.**

**Pack resolution (third):** `ACTIVE_PACK` = `packs/active.json` -> `active_pack`; then `packs/{ACTIVE_PACK}/pack.json` -> `identity`
supplies every niche string; never hardcode a pack name or its strings here.

## Guard - never scaffold over an existing campus

Markers, checked on THIS run: `workspace.json`; a `dean/` entry file (any of
`CLAUDE.md` / `AGENTS.md` / `AGENTS.override.md` / `CODEX.md`); `shared/`
with content; `.campus-os/`. Any present -> offer /update-workspace or
/campus-doctor; NEVER rebuild. Filesystem only; nothing carries over from an
earlier founding.

## Step 0 - The founding frame

Say the pack's `founding_frame` in your own words, all three beats. Do NOT
collect the name here.

## Step 1 - Name me, then offer the fork (once, for BOTH paths)

**Beat 1 - the rename, non-skippable:** ask "Keep Dean, or a name you like
better?" and WAIT; record `assistant_name`; "keep it" IS the confirmation.

**Beat 2 - the fork,** explicit, full first (wording in `interview.md`):
**A) Full onboarding (default)** -> ask only the filing question (Q4), build
the shell (files DEFAULT), run /full-onboarding. **B) Quick start** -> four
questions one at a time, build, seed (SEEDED), First Win. **C) Start from
what I have** -> ask only the filing question (Q4), build the shell (files
DEFAULT), run /campus-intake (it reads the owner's documents, links and AI
memory, writes files as SEEDED, plays them back, asks only the gaps). B and
C are never chosen silently. Answers the owner hands over in a file do not
skip this beat: show all three options, then take the choice the file
names; if it names none, ask.

## Step 1b - Four quick questions (path B), ONE AT A TIME

Ask question 1. Wait. Read it. Then question 2. Push back ONCE on a vague
answer - you cannot push back on an answer you have not seen.

### ⚠️ PRE-SUPPLIED CONTEXT - declare it, never write it unconfirmed

Host-supplied background defeats the pushback silently.

1. **Declare.** Before Q1, if you hold pre-supplied context about this
   business, say in one line what you appear to know and where it came from.
2. **Ask regardless.** Pre-supplied context is a starting point, never a
   substitute.
3. **Never write it unconfirmed.** No pre-supplied fact reaches any shared
   context file, `workspace.json`, or a department file
   until the owner has said it in their own words in THIS conversation.
   Drafted from it, a ladder row is `SEEDED`, never `COMPLETE`.

The questions (wording in `interview.md`): 1 business (`q1`, pushback
`q1_pushback`); 2 what you sell (`q2_examples`); 3 who it's for
(`customer_noun`); 4 filing, asked on BOTH paths: "Your campus always has
the same staff departments - **{DEPT_LABELS}**. Separate question: how
should your FINISHED WORK be filed - by department, client, project, or a
mix?" Sets the filing key only.

⚠️ **`DEPT_LABELS` is RESOLVED, never typed.** Render it from
`templates/registry.json` -> the `type: department` entries -> each entry's
`label` field, skipping `dean-office`; never typed, never from the pack
(build-gate 22, 24).

## Step 2 - Build the campus to match

Common core (notes and exact root entry-file text: `scaffold.md`):

```
{ENTRY_FILE}     (ROOT redirect, per PLATFORM.md)
dean/            {ENTRY_FILE} (from templates/dean-CLAUDE.md), memory.md, TASKS.md, .activity.jsonl
shared/          business.md, voice.md, goals.md, offers.md, audience.md, tools.md,
                 setup-progress.md
.campus-os/      registry.json, model-routing.md, context-files.md, ledger-paths.md,
                 run-id-and-interop.md, resolve-seat.py (from templates/ and tools/), .campus-os/scan/, registration-block-spec.md
                 (MATERIALIZED: tools/materialize_registration_spec.py --campus-root {root})
.campus-os/kernel/  the kernel kit (core tier), written FIRST - the tools above run from it
                 (`scaffold.md` -> "Kernel kit"; Kernel preamble §5)
atlas/config/  active-work/  inputs/  outputs/  wiki/  daily/
```

update-workspace creates the same set (build-gate check 8). Create every
folder, even empty; write and verify the root entry file; never
hand-build the org.

**Departments:** create **one folder per department on the org chart** -
every `type: department` entry behind `{DEPT_LABELS}`, skipping `dean-office`
(path: `managers[].dept_dir` if a manager declares one, else
`departments/{id}/`) with a charter stub. An unstaffed department still gets
its folder; the folders match the org chart exactly. Then confirm, as **its
own turn**: "Starting departments: {DEPT_LABELS} - rename or change any?"
Wait for the answer and apply any rename before Step 2b. **Clients / Projects / Mix:** `clients/_template/`,
`projects/_template/`, or both.

**Job cards.** If the plugin has `packs/{active_pack}/job-cards.md`, copy it
to `dean/job-cards.md` when absent (`scaffold.md` -> "Job cards"). A pack
without one founds as before.

## Step 2b - Which AI apps will work here (its own turn)

Ask once, wording in `interview.md` (Step 2b): which AI apps the owner will
use with this campus on this computer. Then write `.campus-os/seat.json`
from the answer (`scaffold.md` -> "Seat"): THIS app is primary and runs the
schedules; every other app the owner names starts **proposal-only**
(satellite) until the owner promotes it. Never guess an app the owner did
not name. If the seat cannot be written here, say so in one line with the
command to run later; founding still finishes.

`workspace.json` (schema in `scaffold.md`): `assistant_name`; the `business`
OBJECT; `structure` plus EXACTLY the matching filing key; `version` =
`OS_VERSION`; `created`; `pack` = the plugin's `active_pack`. `.campus-os/model-routing.md` only if absent; never
regress a version marker.

## Step 3 - The founding close

"{Name} here - your campus exists. Your campus is on v{OS_VERSION}." A ->
/full-onboarding now; C -> /campus-intake now; B -> /campus-first-win, then the setup ladder; never
nag toward the full sit-down. No tours next. The close asks **exactly one
question** (the next-step offer); the departments question was already its
own turn in Step 2, and the apps question in Step 2b. Name departments only by their `{DEPT_LABELS}` label,
never by folder or id (the `education` department is shown as its label).

## Rules

- Grade-8 language; never "orchestrator", "scaffold", "registry", "kernel".
- **One question per turn, through the close.** Never end a turn with two questions.
- **NEVER BATCH THE FOUNDING QUESTIONS.** One question, one answer, then the
  next - never a form, dialog, or list. Permission-to-batch wording is
  wrong; this rule wins (campus-doctor scans this file).
- ONE pushback per vague answer; ~5 minutes total.
- A confirming answer IS the confirmation.
- The structure choice must visibly change the folders; it can change later.

## File anchoring (critical)

Kernel preamble §2 applies: `references/kernel-preamble.md`.

Kernel preamble §5 applies: `references/kernel-preamble.md`.
