---
name: hr-recruit
description: HR recruit mode - the promote half of the self-authoring loop. Kernel HR skill. Reads the campus activity ledger, clusters repeated ad-hoc workflows, dedupes against the registry, and files skill candidates for owner review. Flag-only: it never authors a skill. Use for 'run recruit', 'hr recruit', 'check for skill candidates', 'what should become a skill', or /hr-recruit. Department: dean.
version: 0.3.0
department: kernel
---

# hr-recruit (kernel) — Hire From Your Own Work History

Your AI staff already did the work — repeatedly, by hand. Recruit finds those repeats in the activity
ledger and proposes each as a new hire (a skill candidate). Nothing is created without owner approval.
This is the promote half of the loop whose capture half is Dean's activity ledger (`dean/.activity.jsonl` for the primary seat, `dean/.activity.{seat}.jsonl` for each satellite).

## Inputs (all canonical kernel paths)
1. **Ledger:** every activity ledger on the campus - the primary
   `dean/.activity.jsonl` plus any satellite shard `dean/.activity.{seat}.jsonl`
   (canon: `.campus-os/ledger-paths.md`). `cluster_ledger.py` merges them for
   you. Skip `#` header lines and malformed JSON.
2. **Dedupe source:** `.campus-os/registry.json` (canonical — teams + playbooks + their triggers).
   Optionally enrich with `.campus-os/scan/latest.json`. No second registry store.
3. **Suppression:** `dean/skill-candidates/_rejected/*.md` (never re-propose) and existing
   `dean/skill-candidates/*.md` (never overwrite — increment the slug).

If the ledger is missing or thin, say so plainly ("Dean writes this at session end — run a few
sessions first"). Never invent activity.

## Steps

**1. Cluster (deterministic helper).**
```
python3 library/skills/hr-recruit/scripts/cluster_ledger.py --campus-root . --days 30 --min-cluster 3
```
This filters to last-30-day `skill=="ad-hoc"` + `outcome=="completed"`, clusters by trigger-keyword
overlap (Jaccard ≥ 0.5), keeps clusters of 3+ (two is coincidence, three is a pattern), dedupes
against installed employees and rejected candidates, and prints proposed candidates + an
`existing_should_have_fired` list. Fewer than ~6 window entries → report thinness and stop.

**2. File candidate briefs** for each returned candidate at `dean/skill-candidates/{slug}.md` —
**frontmatter + a short plain-language summary only. Do NOT write the SKILL.md body** (authoring is
skill-creator's job, and only after approval). Frontmatter: `name`, `status: proposed`,
`proposed_date`, `sample_size`, `suggested_dept`, `trigger_examples` (3+), `tool_signature`,
`source: hr-recruit`, `body_status: pending`. Never overwrite an existing candidate (the helper
already increments the slug).

**3. Surface "should have fired" misses.** For each `existing_should_have_fired` entry, tell the
owner: "existing skill `{name}` should have fired but didn't — check its trigger phrasing." This is a
free trigger-tuning signal, not a new candidate.

**4. Report.** List filed candidates (slug, occurrences, one-liner), remind the owner: "approve
{slug}" hands the brief to skill-creator (via `/review-candidates`); "reject {slug}" moves it to
`_rejected/` and it won't be re-proposed. Cap 5 per run; note overflow.

**5. Emit the back socket.** Append `hr-recruit-candidates` to `results.json` under the run_id:
`external_ref: null`, `attribution: {}`, `completion: { signal: "done_check", status: "complete",
candidates_filed: N, clusters_dropped_as_duplicates: M }`.

## Rules
- **Flag-only.** HR proposes; it never authors, edits, or installs a skill.
- **Owner approval gates everything.** Candidates stay `status: proposed` until `/review-candidates`.
- **Honest thinness.** Small ledger → small report. No padding.
- **Canonical registry is the dedupe truth.** Say which dedupe source was used if the registry was
  unavailable.
