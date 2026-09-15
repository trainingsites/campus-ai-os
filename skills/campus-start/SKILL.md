---
name: campus-start
description: >
  Found a new AI-native business campus in about 5 minutes: hire-an-AI-staff
  frame, renamable chief of staff, four questions one at a time, a workspace
  built to match; niche framing from the active pack (Education). Use when
  the owner says "/campus-start", "set up my campus", "found my campus", or
  when no campus exists.
version: 5.2.9
department: kernel
---

# /campus-start - Found Your Business (about 5 minutes)

A founding moment, not a software install. Scripts and detail:
`interview.md`, `scaffold.md` in this skill's `references/`.

**Platform resolution (do this FIRST):** resolve `PLUGIN_MANIFEST` and
`ENTRY_FILE` per `PLATFORM.md` at the plugin root. **Never hardcode either.**

**Version resolution (second):** `OS_VERSION` = `PLUGIN_MANIFEST` ->
`version`. **Never write a hardcoded version literal.**

**Pack resolution (third):** `packs/education/pack.json` -> `identity`
supplies every niche string; never hardcode them here.

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
questions one at a time, build, seed (SEEDED), First Win. No third path; B
is never chosen silently.

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
atlas/config/  active-work/  inputs/  outputs/  wiki/  daily/
```

update-workspace creates the same set (build-gate check 8). Create every
folder, even empty; write and verify the root entry file; never
hand-build the org.

**Departments:** create **one folder per entry in the pack's `departments[]`**
(path: `managers[].dept_dir` if declared, else `departments/{id}/`) with a
charter stub; confirm: "Starting departments: {DEPT_LABELS} - rename or
change any?" An unstaffed department
still gets its folder. **Clients / Projects / Mix:** `clients/_template/`,
`projects/_template/`, or both.

`workspace.json` (schema in `scaffold.md`): `assistant_name`; the `business`
OBJECT; `structure` plus EXACTLY the matching filing key; `version` =
`OS_VERSION`; `created`. `.campus-os/model-routing.md` only if absent; never
regress a version marker.

## Step 3 - The founding close

"{Name} here - your campus exists. Your campus is on v{OS_VERSION}." A ->
/full-onboarding now; B -> /campus-first-win, then the setup ladder; never
nag toward the full sit-down. No tours next.

## Rules

- Grade-8 language; never "orchestrator", "scaffold", "registry", "kernel".
- **NEVER BATCH THE FOUNDING QUESTIONS.** One question, one answer, then the
  next - never a form, dialog, or list. Permission-to-batch wording is
  wrong; this rule wins (campus-doctor scans this file).
- ONE pushback per vague answer; ~5 minutes total.
- A confirming answer IS the confirmation.
- The structure choice must visibly change the folders; it can change later.

## File anchoring (critical)

Kernel preamble §2 applies: `references/kernel-preamble.md`.
