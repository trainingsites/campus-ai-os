---
name: review-candidates
description: >
  Show pending skill candidates and handle approve/reject from the owner. Use
  when the owner says "review candidates", "show skill candidates",
  "approve {slug}", "reject {slug}", or runs /review-candidates. Reads
  dean/skill-candidates/, displays drafts, promotes approved candidates into
  the right department and registers them in the team directory.
version: 3.1.0
department: kernel
---

# Review Candidates

Owner-facing review surface for skill candidates proposed by `promote-skills`. Show the drafts, take approve/reject decisions, promote approved candidates into the right department's skills folder.

## Inputs Required

- `dean/skill-candidates/*.md` - proposed candidates (status: proposed)
- `.campus-os/registry.json` - the team directory (to register promoted skills)
- `workspace.json` - to resolve the campus's real structure (departments / clients / projects)

If `dean/skill-candidates/` is empty or has no `status: proposed` files: "No candidates pending. Dean writes new ones whenever a workflow gets repeated 3+ times. Run /promote-skills to scan now."

## Mode A - List & Review

Triggered by: "review candidates", "show skill candidates", or no specific slug.

1. List every file in `dean/skill-candidates/*.md` (NOT `_promoted/` or `_rejected/`). Read frontmatter only.
2. Display each candidate: slug, sample size, suggested department, one-line description. End with: 'To see the full draft: "show me {slug}". To decide: "approve {slug}" or "reject {slug}".'
3. On "show me {slug}": display the SKILL.md body verbatim, with a footer noting approve promotes into {suggested_dept}, reject drops permanently.

## Mode B - Approve

Triggered by: "approve {slug}".

### Step 1: Find the candidate

Read `dean/skill-candidates/{slug}.md`. If it doesn't exist, list available candidates and ask which one.

### Step 2: Resolve the target folder

Read frontmatter `suggested_dept`. Map to `{dept-folder}/skills/{slug}/` using the folders that actually exist in this campus (check `workspace.json` structure). `dean` -> `dean/skills/{slug}/`. If the owner contests the department, ask and update.

### Step 3: Confirm with the owner

Show: the slug, target path, triggers, and the three actions (create skill folder + SKILL.md, register in the team directory, move candidate to `_promoted/`). Wait for typed confirmation. Do NOT proceed on assumed-yes.

### Step 4: Promote

On confirm:

1. Create `{dept-folder}/skills/{slug}/SKILL.md` - frontmatter `name:` + `description:` (built from the candidate's trigger_examples), body copied from the candidate file.
2. Register in `.campus-os/registry.json` - APPEND a new entry to `teams` (append-only, never rewrite existing entries):

```json
{
  "team": "{slug}",
  "type": "authored-skill",
  "version": "1.0.0",
  "department": "{dept}",
  "owns": "{one-line description}",
  "triggers": ["{trigger 1}", "{trigger 2}"],
  "permission": "draft-only",
  "source": "promote-skills",
  "promoted": "{today YYYY-MM-DD}"
}
```

3. Move `dean/skill-candidates/{slug}.md` -> `dean/skill-candidates/_promoted/{slug}.md`; update its frontmatter: `status: promoted`, `promoted_date`, `promoted_to`.

### Step 5: Report

Confirm the promotion, list the trigger phrases that will now fire it, and note the owner can refine `{dept-folder}/skills/{slug}/SKILL.md` directly.

## Mode C - Reject

Triggered by: "reject {slug}".

1. Find the candidate (as Mode B Step 1).
2. Confirm: "This moves the candidate to _rejected/. Future /promote-skills runs won't re-propose this trigger pattern. Confirm?"
3. Move `dean/skill-candidates/{slug}.md` -> `dean/skill-candidates/_rejected/{slug}.md`; frontmatter `status: rejected`, `rejected_date`.
4. Report: "Rejected: {slug}. Won't be re-proposed."

## Rules

- **Never promote silently.** Always confirm before writing into a department folder.
- **Never modify or delete an installed skill.** This skill only adds new ones.
- **Never re-promote a rejected candidate.** Suppression is permanent unless the owner manually removes the `_rejected/` file.
- **Registry is append-only.** Add the authored-skill entry; never rewrite or delete existing entries.
- **If the slug already exists** in the registry or any department: stop, tell the owner, suggest a renamed slug.
- **Don't fabricate trigger examples.** Use what's in the candidate frontmatter - real triggers from the ledger.

## Edge Cases

- **"approve all"** - promote each `status: proposed` candidate one at a time, confirming each. No batch-promotion without per-candidate confirmation.
- **Department doesn't exist** - refuse promotion, name the structures that do exist, let the owner pick.

## File anchoring (critical)

Kernel preamble §2 applies: `references/kernel-preamble.md`.