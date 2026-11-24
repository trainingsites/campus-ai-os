# Campus AI OS  -  Quickstart

**What this is:** the kernel of your AI-staffed business - the kind of business is set by the active niche pack (`packs/active.json` names it; its `identity.business_noun` is the word the campus uses, "education business" in the default pack). A small,
safe chief of staff (Dean), a team directory, and an onboarding that gets you
real work in about 10 minutes - a founding, not a form. Your installed version is in the plugin manifest and `workspace.json`.

## Install (once)

1. Add this plugin. In **Claude Code** (recommended), from an empty folder:
   `/plugin marketplace add trainingsites/campus-ai-os`, then
   `/plugin install campus-ai-os@campus-ai-os`. In the **Claude desktop app**, open its
   plugin settings and upload the downloaded `.plugin` file. In **Codex**, follow
   `CODEX-INSTALL.md`.
2. Create an empty folder for your campus and open it (or connect it) in your session.
3. Say: **/campus-start**

**Claude Code will ask before it runs a command.** Setup, updates and the health check run small
checks that ship inside this plugin. Approve them as they come, or set the permission mode to
allow edits and commands for this session so setup runs without stopping.

## What happens next

- **/campus-start**  -  meet your chief of staff (name them what you like - Dean
  is the default), then pick how to set up:
  - **Full onboarding (the default, ~25-30 min)**  -  a proper sit-down about your
    business, audience, offers, goals, tools, and voice. Every core file ends up
    sounding like you, so your first work comes out sharp.
  - **Quick start (~10 min)**  -  four questions, then real work right now; the rest
    fills in as you go.
- **/full-onboarding**  -  the full sit-down, any time. Resumable and
  non-destructive: it picks up at the first unfinished file and never re-asks
  what you've already done. (Quick-start users run this whenever they're ready.)
- **/campus-first-win**  -  your team produces its first real deliverable
  (community prompts, a lesson plan, or a call prep pack  -  your pick).
- **From then on**  -  just talk to your chief of staff. Setup deepens
  one 60-second question at a time, while real work happens.

## The three rules your team never breaks

1. Your `inputs/` folder is sacred  -  nothing ever changes files there.
2. Nothing irreversible (send / publish / delete / charge) without your "go."
3. Any big build gets a one-page plan you approve first.

## Anytime

- **/campus-doctor**  -  plain-English health check ("is everything OK?").
- **/campus-map**  -  bake a double-click dashboard of your whole campus.
- **/wiki-query**  -  "what do I know about X?" answered from your own wiki.
- **/promote-skills**  -  scan your work diary for repeated workflows and
  propose new skills (drafts only - you approve every one via
  **/review-candidates**).

## Already running Campus AI OS v2?

Install this plugin over your v2 (that's the intended path), open your
existing campus folder, and say **/update-workspace**. The upgrade never
deletes or rewrites anything you or your team wrote  -  your memory, wiki,
and departments stay exactly as they are. It shows you what will change
before changing anything, and reminds you to back up first.

Already on v3.0, v3.1, or v3.2? Say **/update-workspace** - the upgrade is
additive-only, and it can bring your department managers up to current
conventions with a per-manager preview you approve.

## Updating a campus you already use

1. Check that a backup includes your campus folder.
2. Replace the installed plugin with the new one. Use the same edition your campus was set up
   with; a different edition belongs in a new empty folder.
3. Open the campus folder you already use and say **update my campus**.
4. Read the list of changes it shows, then say **go**. It asks which AI apps you use with this
   folder; name the main one.
5. Say **/campus-doctor** to check the result.

Changed your mind? Say **undo the last update**, before you swap or remove the plugin. The
system files go back to how they were, anything the update added is moved into a folder under
`dean/archive/`, and nothing is deleted. Your own notes, tasks and work diary are never touched. Scheduled jobs and connected accounts belong to the app you set them up in; set them
up again if you moved to a different app.

Add-on teams you already own keep working; "legacy" entries in the team
directory adopt the new registration block whenever they next update.
