---
name: skill-creator
description: >
  Create a new skill that packages a workflow into a reusable SKILL.md. Use
  when the owner says "create a skill", "make a new skill", "turn this into a
  skill", or asks to build a reusable process. Also called as a sub-step by
  promote-skills to draft candidate bodies.
version: 3.1.0
department: kernel
---

# Skill Creator

Create self-contained skills that package workflows into portable, reusable units.

## Creation Process

### Step 1: Understand the Workflow

Identify: what triggers it, what inputs it needs, what steps it follows (in order), what outputs it produces, what can go wrong. If the workflow was just completed manually, reverse-engineer it: "Let me crystallize what we just did into a reusable skill."

### Step 2: Plan the Skill

| Question | Maps To |
|----------|---------|
| Needs Claude's judgment? | Instructions in SKILL.md |
| Needs reference docs? | `references/` folder |
| Needs output templates? | `references/templates.md` |

### Step 3: Frontmatter

```yaml
---
name: kebab-case-name
description: What it does. Use when the owner says "trigger phrase 1", "trigger phrase 2".
---
```

### Step 4: Body - imperative SOP format

Title, one-sentence purpose, Inputs Required, numbered Steps, Output (what gets produced and where - `outputs/YYYY-MM/{type}/`), Rules (constraints, edge cases, what NOT to do).

**Rules:**
- Keep SKILL.md under 500 words - move detail to `references/`
- Every skill must say where output goes
- Include trigger phrases in the description so Dean can route to it
- Read the campus's voice/brand files from `shared/` before writing content skills

### Step 5: Create the directory

```
{dept-folder}/skills/{skill-name}/
  SKILL.md              # <500 words
  references/           # optional
```

### Step 6: Register and test

Append an entry to `.campus-os/registry.json` (`type: "authored-skill"`, `permission: "draft-only"`, append-only - see review-candidates Step 4 for the shape). Then test: ask naturally without naming the skill - does Dean find it and route correctly?

**When called as a promote-skills sub-step:** return the SKILL.md body only. Do NOT create folders or register - the candidate goes to `dean/skill-candidates/` and registration happens at approval.

## Design Tips

- One skill = one job. If it does two things, make two skills.
- Write for someone who's never done this before.
- Include what NOT to do (common mistakes).

## File anchoring (critical)

Every file goes inside the CAMPUS FOLDER, resolved from the campus root. Never write to a session scratchpad or temporary outputs directory.
