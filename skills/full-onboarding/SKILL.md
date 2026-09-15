---
name: full-onboarding
description: >
  The full sit-down setup for a campus - about 25-30 minutes. Interviews the
  owner about their business, audience, offers, goals, tools, and voice, and
  turns each answer into a real working file (not a form dump). This is the
  DEFAULT path offered at first run (option A of the fork), and the re-entry
  path any time later. Use when the owner says "/full-onboarding", "full
  onboarding", "do the full setup", "set up everything properly", "finish my
  setup", "let's do the whole thing", or picks the full option at the fork.
  Resumable and non-destructive: on a campus that's already partly set up it
  picks up at the first file that isn't done and never re-asks what's already
  drafted or confirmed.
version: 5.0.0
department: kernel
---

# /full-onboarding - The Full Sit-Down (about 25-30 min)

The payoff path. By the end, every core file sounds like the owner and lands
in the right place - so the first real work comes out sharp, not generic. This
is the same enrichment engine the campus uses one question at a time; here it
runs all the way through in one sitting.

## Guard + resume (read this before asking anything)

Requires a campus (`workspace.json` present). If missing, run /campus-start first.

Read `shared/setup-progress.md` and check the status of each core file. Then
run ONLY the phases whose file isn't done, in the sequence below:

- **COMPLETE** -> skip silently. Never re-ask.
- **DRAFTED** -> skip. It already has real content built from the owner's
  answer; corrections happen later via "fix my {file} file", not here. If the
  owner explicitly wants to redo it, that's fine - otherwise leave it.
- **SEEDED** -> the raw answer is on file but never expanded. Do NOT re-interview.
  Generative-expand the existing raw answer into a full DRAFTED file (per
  "Generative seeding" below), then mark it DRAFTED.
- **DEFAULT** -> run the phase: ask, then generative-seed to DRAFTED.

Open by telling the owner what's already done and what's left, in one line:
"You've already got audience and offers drafted - we just need goals, tools,
and voice. About 10 minutes. Ready?" A fresh campus (everything DEFAULT) runs
all six phases (~25-30 min).

## The phases (in order)

Each phase: ask the question(s), push back ONCE on a vague answer (unskippable,
capped at one follow-up per question), then expand the answer into the file and
mark it DRAFTED. If a phase drags past its share of the time, bank what you
have (mark the file SEEDED), say "I've got enough to start - we can sharpen
this later", and move on. Never blow the ~30-minute ceiling.

1. **Business + org chart** (ported from the org-chart pattern; 4-department
   Dean model is the reference the owner maps against).
   - Ask: "What does your business actually do - who do you serve and what do
     they get?" and "Walk me through a typical week - all the work, not just
     the client-facing delivery." (Word the delivery example in the active
     pack's terms - `packs/*/pack.json`; education pack: "not just the
     teaching.") (Skip whatever /campus-start already captured; don't re-ask.)
   - **Departments always exist.** The staff org (Marketing, Sales, Community,
     Education, and Dean's office - five `type: department` entries, plus the
     campus-systems record) is already in `.campus-os/registry.json` from
     founding (the template ships them with their rosters) - just confirm
     they're present. Never hand-build or duplicate them. That's how employees
     are grouped, no matter the filing choice.
   - **Filing question (this is the structure question, reworded):** "How should
     finished work be filed - by department, by client, by project, or a mix?"
     Write the matching filing key(s) in `workspace.json`: `departments[]` for
     departments, `clients[]` for clients, `projects[]` for projects, and for a
     mix ALWAYS `departments[]` PLUS at least one of `clients[]`/`projects[]`
     (only the dimensions actually used). Create the matching filing folders.
     The staff org is separate and always present.
   - Write: `shared/business.md` DRAFTED.
   - **Record (write-back seam):** in the SAME step, set `workspace.json`
     `business.what` to the one-line essence of the business. Real value, never
     a placeholder (see "Write-back to workspace.json" below).
2. **Audience** (ported from the audience-builder pattern).
   - Ask, together: best customer (the one who gets real results); what they're
     trying to accomplish; what they already tried that failed; and - most
     important - how they describe the problem in their OWN words.
   - Expand into the full briefing: Who I Serve / Segments / Demographics /
     Pain Points / Their Language / Buying Triggers / How the assistant uses
     this / Red Flags (assumptions to verify against real data - the data-
     validation step survives here as red flags, not a blocking sub-interview).
   - Write: `shared/audience.md` DRAFTED.
   - **Record (write-back seam):** in the SAME step, set `workspace.json`
     `business.audience` to the one-line audience essence.
3. **Offers.**
   - Ask: what they sell now + rough price points; what's next to launch.
   - Expand into an offer sheet (each offer: who it's for, what it is, price,
     what it replaces/upgrades).
   - Write: `shared/offers.md` DRAFTED.
   - **Record (write-back seam):** in the SAME step, set `workspace.json`
     `business.sells_today` to the one-line summary of what they sell now.
4. **Goals.**
   - Ask: the one number that matters most; by when (horizon); this week's focus.
   - Expand into the goals file (the one number + horizon + this week + one line
     on why it matters).
   - Write: `shared/goals.md` DRAFTED.
5. **Tools** (detect first, then confirm - don't interrogate).
   - FIRST detect connected MCPs / connectors available this session. Then
     CONFIRM rather than ask cold: "I can see Gmail - what runs your list? your
     community? your calendar?" Fill gaps with light questions only.
   - Expand into the tools map (what's connected, what each runs, what's still
     missing and worth adding).
   - Write: `shared/tools.md` DRAFTED.
6. **Voice** (offer now-or-later; later is legitimate).
   - Say plainly: voice comes out best from real writing samples. "Paste 2-3
     things you've written - an email, a post - and I'll learn how you sound.
     Or we skip this and I match your tone as we work." If they defer, LEAVE
     `shared/voice.md` at DEFAULT on the ladder (do not fake a voice from
     nothing).
   - If done now, expand samples into the voice profile. Write `shared/voice.md`
     DRAFTED.

## Generative seeding (every file this skill writes)

- A raw answer is RAW MATERIAL, never the file content. Expand each answer into
  the file's full structure using the owner's actual words and quotes.
- Every drafted file opens with exactly this invitation (swap {file} for the
  file's plain name): "Boss's draft, built from what you told me at setup. Some
  of this will be wrong - say 'fix my {file} file' and we'll correct it in 60
  seconds." (Use the assistant's actual name, not literally "Boss", if renamed.)
- Set status DRAFTED (owner hasn't confirmed yet). Update `shared/setup-progress.md`
  after each file: DEFAULT -> SEEDED -> DRAFTED -> COMPLETE. This skill takes
  files to DRAFTED; only the owner's confirmation makes a file COMPLETE.

## Write-back to workspace.json (canonical record)

The shared/*.md files are the human-readable drafts; `workspace.json` is the
machine-read record other skills consult. They must not drift - a completed
onboarding whose workspace.json still reads empty is the v4.1.0 QA defect this
seam fixes.

- **Canonical schema (nested, do not change):** workspace.json carries
  `"business": {"what": "...", "sells_today": "...", "audience": "..."}` - the
  same shape /campus-start seeds and /update-workspace normalizes. Do NOT write
  flat top-level `business`/`sell`/`audience` string keys.
- **The seam:** as each of the business (`what`), offers (`sells_today`), and
  audience (`audience`) phases completes, write its one-line essence into the
  matching `business.*` field IN THE SAME step as the shared-file write - one
  canonical write per field, not a scattered afterthought.
- **Never a placeholder.** If a phase is skipped or banked, leave that field
  `""` - never "(fill in later)" or any prose sentinel. Empty means empty;
  completeness lives only in `shared/setup-progress.md`.
- **Re-entry:** on a resumed run, only write fields whose phase you actually run
  this time; never blank out a field the owner already has.

## Close -> First Win

When the run's phases are done, hand straight to /campus-first-win, and NAME the
payoff out loud: "Here's the difference 20 minutes bought us - this first piece
is going to sound like you and speak to your people, not a template." The win
runs on the enriched context.

## Rules

- Grade-8 language. Never say "orchestrator", "scaffold", "registry", "kernel"
  to the owner.
- One pushback per vague answer, then accept and move on. Respect the ~30-min
  ceiling; bank and move if a phase drags.
- Non-destructive: never overwrite a COMPLETE or DRAFTED file, never re-ask
  what's already answered. Skipping voice (or any phase) is a valid choice -
  say what's left on the ladder at the end.
- Log the run to `dean/.activity.jsonl` (skill: "full-onboarding"). Speak as
  the assistant's chosen name.

## File anchoring (critical)

Kernel preamble §2 applies: `references/kernel-preamble.md`.