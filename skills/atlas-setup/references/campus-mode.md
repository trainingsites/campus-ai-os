# Founded-campus (inherit) mode — inherit, don't re-ask

Detection: glob for `workspace.json` at the campus root. That is the campus marker and it is host-neutral — never test for an entry file (its name differs per platform, see `PLATFORM.md` → `ENTRY_FILE`) and never assume a campus folder name. If present, the campus is founded — inherit its context instead of interviewing the owner.

Inherit (never re-ask what the host onboarding already captured). **Resolve every file through `context-files.md`** (canon → alias → case-insensitive) — never hard-code these names:
- `icp` → niche, audience, pain points.
- `offers` → business model + what they create/sell.
- `connections` → tool connections. **Aliases live in `context-files.md` and only there** — this line used to restate them, which made it a second copy that went stale exactly as you would expect (it never learned `tools.md`, the one name founding actually writes).
- `goals` → fuels the Strategy council's mandate.
- `brand` + `voice` → for any branded or on-voice output.

Ask ONE question only: output preferences (what they mostly create).
Then show a confirmation summary and allow edits.

## Handoff location (connected mode)
- Briefs → `outputs/{YYYY-MM}/briefs/` (also mirror to `./teams-shared/briefs/` if peer teams expect it).
- Run ledgers Reporting reads → `outputs/{YYYY-MM}/runs/{team}/{slug}/results.json`.
- Roll-ups → `outputs/{YYYY-MM}/reports/`.

## Where briefs route
Atlas never publishes — it hands a brief to whatever execution team handles the brief's `output_type` (see `output-router`). Routing is by **function category** (content, live-session/presentation, class/course prep, sales/outreach, proposal), not by any named product. The host's orchestration layer dispatches if present; otherwise the user runs the installed team for that category.
