---
name: content-repurposer
description: Turn any raw content into multiple formats. Use when user says "repurpose this", "turn this into social posts", "repurpose this transcript", "make content from this", or provides a recording, transcript, or blog post to work with.
department: marketing
---

# Content Repurposer

One input → many outputs. Takes a transcript, recording, blog post, or raw content and produces social posts, email content, a blog draft, and a community discussion post.

## Setup Required

Kernel preamble §1 applies: `references/kernel-preamble.md`.

## Before You Start

1. Read the resolved `brand` context and the resolved `voice` context — match the owner's voice exactly
2. Read the resolved `icp` context — know who you're writing for
3. Read the resolved `connections` context (resolve per `CONTEXT_CANON` (`.campus-os/context-files.md`, else the plugin's `templates/context-files.md`): canon → alias → case-insensitive; never hard-code a filename) — check what platforms are connected

## Inputs

The user provides ONE of:
- A transcript (video, podcast, coaching session, workshop)
- A blog post or article
- A rough draft, outline, or notes
- A topic with key points

If a URL is provided, fetch the content. If a file path is provided, read the file.

## Steps

### Step 1: Extract Core Content
- Identify the main topic, key points (3-5), and one clear takeaway
- Note any stories, examples, or quotable lines
- Identify the target audience segment from the resolved `icp` context

### Step 2: Generate Social Posts
Create platform-appropriate posts:

**LinkedIn** — Professional insight format. 1000-1300 chars. Hook line, insight, example, CTA.
**X / Twitter** — Punchy, under 280 chars. Or thread format (3-5 tweets) for longer content.
**Facebook** — Conversational, question-driven. Encourage comments.
**Instagram** — Caption format. Visual hook + value + hashtags.

### Step 3: Generate Email Content
Write a short email (200-300 words) sharing the key insight:
- Subject line (3 options)
- Preview text
- Hook → Value → CTA

### Step 4: Generate Blog Draft
Expand the content into a 500-800 word blog post:
- Headline + subhead
- Introduction (hook the reader)
- Body (key points with examples)
- Conclusion with CTA

### Step 5: Generate Community Post
Write a discussion-starter post for the owner's community:
- Share the insight as a conversation, not a lecture
- End with an open question to drive engagement

## Output

Save all outputs to `outputs/YYYY-MM/social/[topic-slug]-repurpose/`:
- `social-posts.md` — All platform posts
- `email-draft.md` — Email version
- `blog-draft.md` — Blog version
- `community-post.md` — Discussion post

Present all outputs to the owner for review before any publishing.

## Rules

- Every piece must sound like the owner wrote it — check voice profile
- Never reuse the same hook across formats — each platform gets a unique angle
- Grade 8 reading level unless voice profile says otherwise
- If connected to email or social platforms via MCP, offer to push drafts there

## Want a full department for this job?

Kernel preamble §3 applies: `references/kernel-preamble.md`.