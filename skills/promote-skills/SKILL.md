---
name: promote-skills
description: >
  Detect repeated ad-hoc workflows in the activity ledger and draft skill
  candidates for owner review. Use when the owner says "check for skill
  candidates", "promote skills", "find new skills", or "/promote-skills".
  Reads dean/.activity.jsonl, clusters repeated workflows, drafts SKILL.md
  candidates to dean/skill-candidates/. Manual-run only in v3.1 - do not
  create a scheduled task for this skill.
version: 3.1.0
department: kernel
---

# Promote Skills

The self-authoring loop. Watches what the owner repeatedly asks Dean to do without an existing skill, and proposes new skills to capture those workflows. Drafts only - every candidate requires owner approval before promotion.

**v3.1: manual-run only.** Run when the owner asks. Do NOT set up a scheduled task; scheduling is revisited after the first candidate batch proves useful (first approved promotion).

## When to Run

- Owner says: "check for skill candidates", "promote skills", "find new skills", "what should I turn into a skill"
- After a session where multiple ad-hoc workflows ran (offer it, don't auto-run)

## Inputs Required

- **The campus activity ledger(s)** - resolve through `LEDGER_CANON`
  (`.campus-os/ledger-paths.md` on the campus, else `templates/ledger-paths.md`
  in this plugin). The primary seat's ledger is `dean/.activity.jsonl`; each
  satellite seat appends its own `dean/.activity.{seat}.jsonl`. **Read them
  all.** Dean and the department managers append at session end.
- `.campus-os/registry.json` - the team directory (installed teams + previously authored skills, so we don't propose duplicates)
- `dean/skill-candidates/_rejected/*.md` - previously rejected candidates (suppression list)

If no ledger file exists at all, tell the owner: "No activity ledger yet - Dean writes this at session end. Run a few sessions first, then check back."

## Steps

### Step 1: Read the ledger

Read `dean/.activity.jsonl` **and every `dean/.activity.*.jsonl` shard present**, then merge the lines and sort by `ts`. Skip lines that are blank or start with `#` (header comments). Each remaining line is one JSON entry:

```json
{"ts":"2026-07-03T14:22:00Z","session":"S170","seat":"example-seat","skill":"ad-hoc","trigger":"prep my class for tuesday","dept":"education","outcome":"completed","files_touched":3}
```

`seat` names which seat wrote the line. A line without it predates the stamp and
belongs to the primary seat - **attribute it, never drop it.** Clustering does
not partition by seat: two seats repeating the same workflow is still one
pattern worth a skill, and the seat is carried only so the proposal can say
where the work happened.

Filter to entries from the last 30 days where `skill == "ad-hoc"` AND `outcome == "completed"`.

If fewer than 6 ad-hoc entries exist, tell the owner: "Only {N} ad-hoc workflows in the last 30 days. Need at least 3 of the same kind to propose a skill. Check back next week."

### Step 2: Cluster

Cluster the filtered entries using two cheap signals:

1. **Trigger keyword overlap (Jaccard).** Tokenize each trigger (lowercase, drop stopwords: a, an, the, my, for, to, of, on, in, with, this, that, it). Two entries belong to the same cluster if Jaccard similarity >= 0.5.
2. **Tool signature match.** If two entries used the same set of tools/MCPs in roughly the same order (allowing one swap), they reinforce the cluster.

Discard clusters with fewer than 3 members. Three occurrences minimum - two is coincidence, three is a pattern.

### Step 3: Filter against installed skills

For each surviving cluster:

1. Read `.campus-os/registry.json`. Collect every team's `triggers` list and every `type: "authored-skill"` entry.
2. If the cluster's representative trigger phrase matches an installed team's triggers or an authored skill's trigger examples, drop the cluster - the capability exists, it just didn't get invoked by name.
3. Read every `dean/skill-candidates/_rejected/*.md`. If a rejected candidate's `trigger_examples` overlap with the cluster (Jaccard >= 0.5 on any single trigger), drop the cluster - the owner already said no.

### Step 4: Draft candidates

For each surviving cluster, use the `skill-creator` skill as a sub-call. Pass it the cluster's trigger examples (3+ phrases), the tool signature, and a note: "Reverse-engineering this from {N} ad-hoc workflows the owner ran. Propose a skill that captures the pattern." Save to the candidates queue, never straight to a department.

### Step 5: Save candidates

For each candidate, write `dean/skill-candidates/{slug}.md`:

```markdown
---
name: {kebab-case slug}
status: proposed
proposed_date: {today YYYY-MM-DD}
sample_size: {cluster size}
suggested_dept: {best fit - from the departments that exist in this campus, or dean}
trigger_examples:
  - "{example 1}"
  - "{example 2}"
  - "{example 3}"
tool_signature: ["{tool 1}", "{tool 2}"]
---

# {slug}

{Draft SKILL.md body from skill-creator sub-call}
```

Suggested department: read the campus's real structure from `workspace.json` (departments / clients / projects) and pick the best fit from folders that actually exist. Orchestrator-level workflows (status, planning, review) -> `dean`.

### Step 6: Update the daily pulse

Append to `dean/daily/{today YYYY-MM-DD}.md` (create if missing):

```markdown
## Skill Candidates Proposed - {YYYY-MM-DD}

{N} new candidates from your recent work:
- **{slug}** ({sample_size} occurrences) - {one-line description}

Run /review-candidates to see drafts and approve.
```

### Step 7: Report to owner

List each candidate with its sample size and one-line description, then: "These are drafts. Run /review-candidates to see the full SKILL.md for each, then say 'approve {slug}' to promote, or 'reject {slug}' to drop it (rejected candidates won't be re-proposed)."

### Step 8: Stamp the last-run marker

Overwrite `dean/last-promote-run.json` (single record, not a log):

```json
{
  "ts": "{ISO 8601 UTC now}",
  "ledger_entries_scanned": 0,
  "ad_hoc_entries_filtered": 0,
  "clusters_found": 0,
  "candidates_drafted": 0,
  "candidates_suppressed_existing_skill": 0,
  "candidates_suppressed_previously_rejected": 0
}
```

## Rules

- **NEVER promote without explicit owner approval.** Every candidate stays `status: proposed` until the owner says "approve {slug}".
- **NEVER overwrite an existing candidate file.** If `dean/skill-candidates/{slug}.md` exists, increment the slug (`{slug}-2.md`).
- **Don't duplicate installed capability.** Step 3 is mandatory.
- **Don't invent activity.** If the ledger is empty or thin, say so.
- **Cap candidates per run at 5.** Surface the top 5 by sample size; note the rest in `dean/daily/`.
- **No scheduled task** (v3.1 launch decision).

## Edge Cases

- **Ledger malformed (bad JSON line):** skip the line, continue. Don't fail the whole run.
- **skill-creator sub-call fails:** save a stub candidate with frontmatter only and `body_status: pending`. Owner can fill it in or rerun.

## File anchoring (critical)

Kernel preamble §2 applies: `references/kernel-preamble.md`.