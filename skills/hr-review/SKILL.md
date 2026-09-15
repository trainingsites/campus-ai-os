---
name: hr-review
description: Run the weekly HR review of the AI workforce. Kernel HR skill. Use for 'run the HR review', 'what is stale', 'clean up my workforce', 'what should I retire', or /hr-review. Refreshes the scan, diffs it against last week, and produces a flag-only report: new or removed installs, version drift, unregistered installs, flagged schedules, and weak entries, each with a recommended action you approve. Changes nothing on its own. Manual-run with a one-time suggest-to-schedule. Department: dean.
department: kernel
---

# hr-review (kernel)

**One job:** take a fresh scan, compare it to the last one, and hand the owner a short list of things
worth cleaning up — each a recommendation, never an action. The lifecycle loop that keeps the
workforce from drifting. Sits beside `/campus-doctor`: **doctor = "is it healthy" (format/presence);
hr-review = "is it lean" (quality/staleness).** No overlap.

## CRITICAL DIRECTIVES
- **Flag-only. Draft-first. Nothing is ever deleted, disabled, or moved by this skill.** Every line is
  a recommendation the owner approves before anything happens (Reversibility Rule).
- **Reads the canonical registry + the derived scan.** Never edits `.campus-os/registry.json`.
- **Manual-run only, with suggest-to-schedule.** Runs on request. When it comes back clean, suggest
  ONCE that the owner schedule it weekly (same pattern as promote-skills). It never self-schedules.
- **Coordinate neighbours, don't require them.** On approval, route a fix to a real neighbour skill if
  installed; else hand the owner the manual step. Never hard-require a neighbour.

## Run procedure

**1. Preserve the previous scan, then refresh.** The scanner rotates `latest.json` → `previous.json`
automatically, so simply run `hr-registry` (or the scanner directly):
```
python3 library/skills/hr-registry/scripts/scan_workforce.py --campus-root .
```
If a fresh scan already ran this session, reuse it (the rotation already happened).

**2. Run the diff** (latest vs previous + the canonical registry's quality flags):
```
python3 library/skills/hr-review/scripts/diff_scan.py --campus-root . \
  --out-md outputs/{YYYY-MM}/reports/hr-review/{run_id}/hr-review.md
```
This writes the flag report: newly installed / disappeared since last scan, installed-but-unregistered,
registered-but-absent, version drift, flagged scheduled tasks, and weak entries (teams/playbooks with
no `done_check`). First run has no `previous.json` — the review still works, minus add/remove deltas.

**3. Enrich with outcome data when Atlas is present.** If `/atlas-report` output exists, mark which
playbooks actually produced results vs which are unused, and add an "under-used playbooks" note. If no
Reporting team is installed, skip — do not rebuild reporting.

**4. Present the report to the owner**, grouped as the markdown is, leading with the flag count. Keep
it skimmable. State the recommended action per group (stale schedule → owner retires it; unregistered
install → owner registers or ignores; version drift → owner bumps the registry version on next touch;
weak entry → owner adds a done_check; off-spec/duplicate → route to a retrofit/upgrader team if
installed, else manual).

**5. Get explicit approval before any action.** State what would change, flag irreversible vs
recoverable, wait for an explicit "do it" per item. Only then route the approved fix or hand over the
manual step. HR itself changes nothing.

**6. Suggest-to-schedule (once, on a clean run).** If the report is clean (or after the owner clears
the flags), offer ONCE: "Want me to run this weekly? I can set a scheduled task." Only on a yes.

**7. Emit the back socket.** Write `results.json` (draft, carrying `run_id`) with the `hr-review`
asset; record the done-checks (registry-lint + a valid-diff sanity check) in the run manifest.

## Boundaries
HR proposes; the owner disposes. Produces a report and, on approval, routes work to other teams — it
never publishes, deletes, or disables anything itself.
