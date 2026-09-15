---
name: brief-builder
description: >
  Builds the spec-conformant Content Brief (brief.md + brief.json) for the Strategy
  and Research Team (Atlas) from top-scored topics. This brief is the FRONT SOCKET
  every execution team reads. Internal skill, invoked by content-scanner/atlas-daily.
version: 1.0.0
department: kernel
---

# brief-builder — emit the front socket

Produces a **Content Brief** (`.md` + `.json`) that conforms to **Team Interop Spec v1**. Every execution team reads this — it must be complete and portable.

## CRITICAL DIRECTIVES
- **Emit `brief.json` (machine source of truth) AND `brief.md` — never only the markdown.** Write both to the **briefs location**: `./teams-shared/briefs/{slug}/` standalone, `outputs/{YYYY-MM}/briefs/{slug}/` under a host campus. **Never inside a run folder.** (This is the #1 interop bug — the whole point of Atlas is the `brief.json` other teams read.)
- **Do not invent a format.** Use `references/brief-schema.md` exactly. It is the shared brief family every execution team reads — never fork it.
- `run_id` + `schema_version` are REQUIRED on every brief. run_id is the §4 format, worked example `20260530-ai-operating-system-fo-7f3a`.
- Tool-agnostic; zero hardcoded paths. Voice/audience resolve via `CONTEXT_CANON` (`.campus-os/context-files.md`, else the plugin's `templates/context-files.md`) (canon), never hard-coded `shared/*`.

## Step 1 — Inputs
Take the top-scored topic(s) from `scoring-engine` plus the scanner's signal evidence and any `mandate.json`. Get the `run_id` from `atlas-orchestrator` (worked example `20260530-ai-operating-system-fo-7f3a`; inherit if present, never re-mint).

## Step 2 — Choose output_type
Map the topic + business_model defaults to one of the 16 output types (youtube_script, social_bundle, blog_post, webinar, workshop, presentation, course_module, email_campaign, brief_only, …). If the user already named a target team/format, honor it.

## Step 3 — Build the object
Fill the required spine + scoring block (from `scoring-engine`; null in pure standalone) + production payload. For writer/teaching lanes, ensure `key_messages`, `quotable_moments`, and `content_structure` are present (enrich from sources if thin). `tags` = portable plain strings only.

## Step 4 — Write both files
Generate a `slug` (lowercase, hyphenated, ≤60; append -2/-3 on collision). Write to the handoff location:
- Connected → `outputs/{YYYY-MM}/briefs/{slug}/brief.{md,json}` (mirror to `./teams-shared/briefs/{slug}/` if peer teams expect it).
- Standalone/peer → `./teams-shared/briefs/{slug}/brief.{md,json}`.
Set `status: idea`, today's dates, `schema_version: "1.0"`, and the inherited `run_id`.

## Step 5 — Route
Hand to `output-router`: deliver the brief and tell the user which execution team to run next (or generate the standalone brief if no downstream team is installed).
