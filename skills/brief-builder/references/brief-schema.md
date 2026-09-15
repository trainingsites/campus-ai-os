# brief.json schema — front socket (Team Interop Spec v1)

Two files written together: `brief.md` (human) + `brief.json` (machine, authoritative). Conforms to Team Interop Spec v1. Do NOT fork this — every execution team read this shape.

## Required spine (never remove/rename)
```json
{
  "schema_version": "1.0",
  "run_id": "REQUIRED — {YYYYMMDD}-{slug-short}-{4char}, see orchestrator",
  "slug": "lowercase-hyphenated, <=60",
  "output_type": "flywheel|youtube_script|social_bundle|blog_post|newsletter|email_campaign|linkedin_article|webinar|workshop|zoom_session|presentation|podcast|short_form|course_module|brief_only|json_export|calendar_block",
  "brief_type": "content_source|content_idea",
  "scan_type": "standalone|fed",
  "niche": "from config, or '' standalone",
  "status": "idea",
  "created": "YYYY-MM-DD",
  "updated": "YYYY-MM-DD",
  "source": { "type": "article|transcript|recording|video|research_brief|user_input", "title": "", "url_or_path": "", "duration": "" },
  "hook": "one-line",
  "primary_audience": "",
  "tags": ["portable plain strings — never platform term IDs/category codes"]
}
```

## Scoring block (fed mode only; null standalone)
```json
{ "score": "0-100 or null", "label": "or null",
  "signal_breakdown": { "demand":"n/40+evidence|null","gap":"n/30|null","timing":"n/20|null","fit":"n/10|null","multiplier":"1.0x|null" } }
```

## Production payload (per output_type — writer lanes require the first three)
```json
{ "content_structure": {"intro":{},"body":{},"conclusion":{}},
  "key_messages": [{"message":"","timestamp_range":"","why_it_matters":""}],
  "quotable_moments": [{"quote":"","timestamp":"","context":""}],
  "cover_points": [], "offer_connection": "", "format_suggestion": "",
  "content_type": "tutorial|story|case_study|opinion|mixed", "skill_level": "beginner|intermediate|advanced",
  "sources": [] }
```

## Rules
- `run_id` + `schema_version` REQUIRED on every brief.
- `tags` portable plain strings only; the consuming team maps to its real categories at publish.
- Writer-lane briefs need key_messages + quotable_moments + content_structure; a thin fed brief is enriched, never failed.
- `brief.md` mirrors the json; json is authoritative. Lifecycle: idea → validated → in_production → published.
