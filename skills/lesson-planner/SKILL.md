---
name: lesson-planner
description: Create lesson plans with objectives, activities, and materials. Use when user says "plan a lesson", "create a lesson plan", "prep a class", "build a worksheet", or "design a learning activity".
department: education
pack: education
---

# Lesson Planner

Create complete lesson plans with learning objectives, activities, materials, and optional worksheets/handouts.

## Setup Required

Kernel preamble §1 applies: `references/kernel-preamble.md`.

## Before You Start

1. Read the resolved `icp` context — who the learners are, their level
2. Read the resolved `brand` context and the resolved `voice` context — teaching voice
3. Check `content/memory.md` for any existing curriculum context

## Inputs

The user provides:
- **Topic** — what the lesson covers
- **Duration** — how long the session is (default: 60 minutes)
- **Format** — live class, workshop, recorded lesson, self-paced module
- **Audience level** — beginner, intermediate, advanced (or infer from audience.md)
- **Desired outcomes** — what students should be able to DO after (optional)

## Steps

### Step 1: Define Learning Objectives
Write 2-4 measurable objectives using action verbs:
- "By the end of this lesson, you will be able to [verb] [outcome]"
- Bloom's taxonomy: create > evaluate > analyze > apply > understand > remember

### Step 2: Build the Agenda

| Time | Segment | Activity |
|------|---------|----------|
| 0:00 | Opening | Hook + context setting (why this matters) |
| 0:05 | Core Content 1 | [Teaching block — concept + example] |
| 0:20 | Practice | [Hands-on activity or exercise] |
| 0:35 | Core Content 2 | [Second teaching block — build on first] |
| 0:50 | Q&A + Wrap | Review key takeaways, assign next steps |

Adjust timing based on actual duration.

### Step 3: Design Activities
For each practice segment:
- **Activity name and type** (individual, group, demonstration)
- **Instructions** — clear step-by-step for participants
- **Duration** — how long
- **Materials needed** — what participants need
- **Debrief** — how to wrap up and extract learning

### Step 4: Create Materials (Optional)
If requested, generate:
- **Worksheet** — exercises that reinforce the learning objectives
- **Handout** — key concepts, frameworks, and reference material
- **Participant prep** — what students should do/read before the session

### Step 5: Write Follow-Up Plan
- Key resources to share after the session
- Action items for students
- Follow-up email draft (if requested)

## Output

Save to `outputs/YYYY-MM/lessons/[topic-slug]/`:
- `lesson-plan.md` — Full lesson plan with agenda and activities
- `worksheet.md` — Student worksheet (if created)
- `handout.md` — Reference handout (if created)
- `follow-up.md` — Post-session action items and resources

## Rules

- Every lesson must have at least one hands-on activity — no lecture-only plans
- Tie every activity back to a learning objective
- Use practical, real-world examples from the owner's niche
- Match the owner's teaching voice from voice-profile.md
