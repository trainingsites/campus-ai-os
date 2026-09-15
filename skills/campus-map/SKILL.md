---
name: campus-map
description: Generate the Campus Map — a self-contained, file-based command-center dashboard for this campus. One dependency-free Node script reads the campus's own files (goals, activity ledger, wiki, outputs, scheduled tasks, briefs, results) and bakes a portable campus-map.html the owner double-clicks in any browser. No server, no database, no connectors. Use when the owner says "campus map", "show my campus map", "build the dashboard", "refresh the map", "open the command center", "where is my dashboard", or after setup completes. The map is private-only; there is no public or shareable build. v3.1 adds the team directory (.campus-os/registry.json) and setup progress (shared/setup-progress.md) as data sources.
version: 3.1.0
department: kernel
---

# Campus Map — File-Based Command Center

Bakes a portable `campus-map.html` dashboard from the campus's own files. It is **tool-agnostic** (reads only files every Campus AI OS install produces) and **WordPress-free**. Re-run it any time to refresh.

## CRITICAL DIRECTIVES

1. **This is an action skill, not a conversation.** Resolve the campus root, run the generator, report the output path. Do not interview the owner.
2. **Never edit the generator** to hardcode a path. The generator is path-agnostic — it is driven entirely by the `CAMPUS_ROOT` environment variable. Always pass it.
3. **Output belongs in the owner's workspace, never the plugin folder.** With `CAMPUS_ROOT` set correctly the generator writes to `$CAMPUS_ROOT/campus-map/`, not the plugin directory.
4. **Tool-agnostic.** This skill uses only Bash + Read. It calls no MCPs.

## Steps

### 1. Resolve the campus root

The campus root is the folder that contains `dean/`, `shared/`, and `outputs/`. Find it by walking up from the current directory:

```bash
DIR="$PWD"
while [ "$DIR" != "/" ]; do
  if [ -f "$DIR/workspace.json" ] || [ -d "$DIR/shared" ]; then echo "$DIR"; break; fi
  DIR="$(dirname "$DIR")"
done
```

Use that path as `CAMPUS_ROOT`. If nothing is found, the current working directory IS the campus root (the owner is sitting in it) — use `$PWD`. If neither `dean/` nor `shared/` exists anywhere, tell the owner this folder is not a Campus AI OS workspace and offer to run `/campus-start` first.

### 2. Check Node is available

```bash
node --version
```

If Node is missing, tell the owner: *"The Campus Map needs Node.js (free, from nodejs.org). Install it, then run /campus-map again."* Stop here — there is no fallback; the generator is a Node script.

### 3. Generate the map

Private build (the owner's full dashboard):

```bash
CAMPUS_ROOT="$CAMPUS_ROOT" node "${CLAUDE_PLUGIN_ROOT}/campus-map/generate.mjs"
```

The map is private-only. `--public` is refused (retired in 5.2.8); never share a generated map. Optional: `--no-remote-fonts` (or `CAMPUS_MAP_OFFLINE=1`) builds with system fonts and no network request.

Optional: tune the hours-saved estimate with `MIN_PER_RUN` (default 35 minutes per agent run):

```bash
CAMPUS_ROOT="$CAMPUS_ROOT" MIN_PER_RUN=45 node "${CLAUDE_PLUGIN_ROOT}/campus-map/generate.mjs"
```

### 4. Report the result

The generator prints the exact output path. Tell the owner where it is and how to open it:

- `$CAMPUS_ROOT/campus-map/campus-map.html` (private; do not share)

Tell them to **double-click the file** (or open it in any browser). It is fully self-contained — it works offline and needs no server. Mention they can re-run `/campus-map` any time to refresh it as the campus does more work.

## What the owner sees

Sidebar-navigated dashboard with: an overview stat band (runs, deliverables, est. hours saved, knowledge pages, departments), operating context (OKRs + this week, from the resolved `goals` context), Intelligence (Atlas briefs), the department grid, a work-done feed, Operations (skill health + scheduled tasks), the Second Brain (wiki), the Team Directory (from `.campus-os/registry.json`) with setup progress (from `shared/setup-progress.md`), Outcomes (what each team shipped, read from `results.json`), and deliverables by type. Dark/light toggle. Linked docs open in a clean inline reader.

## Progressive panels (this is normal)

Any panel with no source data **hides itself**. A campus with no Strategy & Research (Atlas) team simply shows no Intelligence or Outcomes panel — not an error. As the owner installs more teams and does more work, panels light up. A brand-new campus shows a sparse map; that is expected and correct.

## Brand + orchestrator name

The map auto-pulls the campus name, tagline, colors, and heading font from the resolved `brand` context (resolved through `CONTEXT_CANON`, which covers every spelling; neutral defaults if nothing resolves). The orchestrator name is read from `about-me/dean-name.md` if the owner renamed Dean, otherwise it shows "Dean". No configuration needed.
