---
name: output-router
description: >
  Reads a brief's output_type and routes it to the right execution team, or delivers
  the standalone brief with a clear next-step instruction. Internal skill for the
  Strategy and Research Team (Atlas), invoked by brief-builder.
version: 1.0.0
department: kernel
---

# output-router — hand the brief to the right team

Internal. Atlas never publishes; it routes. This skill reads the brief's `output_type` and points the user at the execution team that does the work. It names no specific product — it routes by **function category**, and whatever execution team the user has installed for that category picks up the brief.

## CRITICAL DIRECTIVES
- Tool-agnostic; zero hardcoded paths. Never generate the downstream asset itself in v1.0 — deliver the brief + the next step.
- Preserve the brief's `run_id` end-to-end so Reporting can trace the topic later.
- Do not assume any particular sibling plugin exists. If none is installed for the category, deliver the brief as-is.

## Routing map (output_type → function category)
| output_type | Function category — route to whatever team handles it |
|---|---|
| flywheel, blog_post, social_bundle, newsletter, email_campaign, linkedin_article, short_form | a **content / publishing** team |
| webinar, workshop, presentation, zoom_session | a **live-session / presentation** team |
| course_module, class topic prep | a **class / course prep** team |
| outreach angles, prospect targeting | a **sales / outreach** team |
| proposal positioning | a **proposal** team |
| brief_only, json_export, calendar_block | deliver as-is — no downstream |

## Steps
1. Read `output_type` from the brief and map it to a function category above.
2. **Connected mode (a host campus is present):** surface the recommended category + the brief path; the host's orchestration layer dispatches to the installed team for that category.
3. **Standalone / peer mode:** if a team for that category is installed, tell the user the exact next command and the brief path (e.g. "feed `./teams-shared/briefs/{slug}/brief.json` to your content team"). If none is installed, deliver the brief with: "This brief is ready for {output_type}. To generate the full asset, install a {category} team and point it at this brief."
4. Confirm the brief landed in the handoff location and print its path + `run_id`.
