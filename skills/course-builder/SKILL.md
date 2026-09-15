---
name: course-builder
description: Design course architecture and write module content. Use when user says "build a course", "create a course on", "design a learning path", "course outline", "write a module", or "curriculum design".
department: education
pack: education
---

# Course Builder

Design complete courses — architecture, modules, lessons, and content. From concept to publish-ready curriculum.

## Setup Required

Kernel preamble §1 applies: `references/kernel-preamble.md`.

## Before You Start

1. Read the resolved `icp` context — who the students are, their level
2. Read the resolved `offers` context — existing programs (avoid overlap)
3. Read the resolved `voice` context — teaching voice
4. Check `content/memory.md` for any existing course context

## Inputs

The user provides ONE of:
- **A topic or learning outcome** → Design from scratch (Mode A)
- **Existing content to organize** — transcripts, notes, recordings → Structure into a course (Mode B)
- **An existing outline to flesh out** → Write the module content (Mode C)

## Mode A: Design from Scratch

### Step 1: Course Blueprint
1. Define the transformation: "Students go from [before] to [after]"
2. Work backwards — what must they HAVE or DO at the end?
3. Break into 3-7 modules, each building on the last
4. Each module gets 2-5 lessons
5. Every lesson produces a named artifact (worksheet, template, project, plan)

### Step 2: Course Architecture

```markdown
## [Course Title]
**Promise:** [One sentence transformation]
**Audience:** [Who this is for — and who it's NOT for]
**Duration:** [Estimated time to complete]

### Module 1: [Title]
**Outcome:** [What they can do after this module]
- Lesson 1.1: [Title] → Produces: [artifact]
- Lesson 1.2: [Title] → Produces: [artifact]

### Module 2: [Title]
...
```

### Step 3: Validate
- Does each module build on the previous?
- Are there any knowledge gaps between lessons?
- Does the final module deliver on the course promise?

## Mode B: Organize Existing Content

### Step 1: Audit the Material
Read all provided content. Identify:
- Topics covered
- Natural groupings
- Gaps that need filling
- Content that's redundant or off-topic

### Step 2: Structure
Organize into modules and lessons following the Mode A architecture format.

### Step 3: Gap Report
List what's missing and needs to be created.

## Mode C: Write Module Content

### Step 1: Read the Outline
Understand the module's place in the overall course.

### Step 2: Write Each Lesson
For each lesson:
- **Opening hook** — why this matters (2-3 sentences)
- **Core content** — the teaching (500-1000 words per lesson)
- **Example** — practical, real-world application
- **Exercise or activity** — what the student does
- **Key takeaway** — one sentence summary

### Step 3: Create Supporting Materials
- Worksheets for practice lessons
- Templates for implementation lessons
- Checklists for process lessons

## Output

Save to `outputs/YYYY-MM/lessons/[course-slug]/`:
- `course-architecture.md` — Full course blueprint
- `module-[N]/` — Content for each module
  - `lesson-[N].md` — Individual lesson content
  - `materials/` — Worksheets, templates, checklists

## Rules

- No filler lessons — every lesson must produce something tangible
- Build sequentially — each lesson should require the previous
- Match the owner's teaching voice
- If the course maps to an offer in offers.md, note the connection
- Publish to the owner's LMS only if connected and confirmed

## Want a full department for this job?

Kernel preamble §3 applies: `references/kernel-preamble.md`.