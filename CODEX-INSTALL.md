# Installing Campus AI OS on Codex

Same package as Claude. One source, two manifests — the skills detect which host
they are on and adapt. Nothing here is a separate build.

Verified against OpenAI's published plugin and AGENTS.md docs on 2026-07-25.
These are living specs; re-check at each major cut.

---

## Install

### The easy way — hand the zip to the agent (PROVEN 2026-07-26)

There is no simple third-party install flow in the Codex/ChatGPT UI. The
"Add marketplace" dialog defaults to a git source and expects a repo.

**So don't fight it. Attach the plugin file you downloaded to a Codex session
and say "install this plugin."** The agent does the rest: extracts it, writes
the local marketplace record, and registers it with Codex. **No unzip, no
commands, no version numbers to type** — you hand it the file and ask.

Verified end to end on a clean machine — the agent extracted to
`~/plugins/campus-ai-os`, registered it in `~/.agents/plugins/marketplace.json`,
and reported `campus-ai-os@personal` installed and enabled at version 5.1.0. <!-- version-literal-ok: historical record of the 2026-07-26 test run, not an instruction -->

**Then start a NEW Codex task** — a running session will not pick up newly
installed skills.

*This is not a workaround, it is the on-brand path: the product's whole premise
is that you ask for outcomes instead of running commands. The install should
work the same way.*

<details>
<summary>Manual routes — only if you can't or won't hand it to the agent</summary>

### From the ChatGPT desktop app (the "Add marketplace" menu)

That dialog defaults to a **git** source, but you don't need a repo — a local
folder is a valid marketplace. Two steps:

1. **Settings → enable Developer mode.** The docs are explicit that this is the
   desktop route: *"Use the ChatGPT desktop app to install and test a local
   plugin"* and *"Open Settings and enable Developer mode."* Without it, local
   sources generally won't be offered.
2. **Point "Add marketplace" at the prepared folder**, not at the zip:

   ```
   Claude-Cowork/library/plugins/codex-marketplace
   ```

   That folder is a complete marketplace root — `.agents/plugins/marketplace.json`
   plus the unpacked plugin under `plugins/campus-ai-os/`. If the source dropdown
   offers *local / path / directory / filesystem*, choose it and give that path.

3. **Restart the desktop app** — *"verify that the plugin appears after you
   restart the ChatGPT desktop app."* It will not show up until you do.

> **If the dropdown only offers git:** that's the signal to use the CLI instead
> (below) — same result, and the CLI explicitly documents local paths. Don't
> force a repo just to satisfy a dropdown.

### From the CLI

```bash
codex plugin marketplace add ~/TrainingSites/Claude-Cowork/library/plugins/codex-marketplace
codex plugin list
codex plugin install campus-ai-os
```

`codex plugin marketplace add ./local-marketplace-root` is documented, so a
local path is a first-class source here.

### Manual (always works)

```bash
# observed layout on a real Codex install (2026-07-26): a BARE ~/plugins,
# not ~/.codex/plugins, with the record in ~/.agents/plugins/
mkdir -p ~/plugins/campus-ai-os
unzip campus-ai-os-v*.zip -d ~/plugins/campus-ai-os      # the zip you downloaded
# then add campus-ai-os to ~/.agents/plugins/marketplace.json
```

</details>

---

Once installed, open the folder you want to be your campus and say
**"set up my campus."**

---

<details>
<summary>Earlier notes on the same two routes</summary>

**Option A — local install (what the docs describe):**

```bash
# 1. unzip the package into your Codex plugin directory
#    ($CODEX_HOME defaults to ~/.codex)
mkdir -p ~/.codex/plugins/campus-ai-os
unzip campus-ai-os-v*.zip -d ~/.codex/plugins/campus-ai-os   # the zip you downloaded

# 2. register it
#    ~/.agents/plugins/marketplace.json  ->  add campus-ai-os to "plugins"
```

**Option B — personal marketplace:**

```bash
codex plugin marketplace add ~/.codex/plugins/campus-ai-os
codex plugin list
```

</details>

---

## Three things that behave differently from Claude

### 1. There are no slash commands

Codex's plugin format has **no `commands/` directory.** Its nearest equivalent —
custom prompts in `~/.codex/prompts` — is local-only, cannot ship inside a
plugin, and is marked deprecated by OpenAI, which points to skills instead.

This package ships 27 commands. **On Codex they do nothing.** The 30 skills
behind them all work — invoke them by name or by intent instead:

| On Claude | On Codex |
|---|---|
| `/campus-start` | "set up my campus" |
| `/campus-doctor` | "run a campus health check" |
| `/hr-review` | "run the HR review" |
| `/update-workspace` | "upgrade my campus" |
| `/campus-map` | "build my campus map" |

Every skill carries trigger phrases in its own description — that is what Codex
routes on. **This is the one real capability gap between the two hosts.**

### 2. Your entry file is `AGENTS.md`, not `CLAUDE.md`

Codex reads `AGENTS.override.md`, then `AGENTS.md`, then any name you have
listed in `project_doc_fallback_filenames`. **`CODEX.md` is not in that chain**
— it comes from an early Codex CLI guide and is a known documentation
inconsistency (openai/codex#1132).

You do not need to do anything: `/campus-start` resolves the correct filename
for the host it is running on and writes `AGENTS.md` here. A campus founded on
Claude and later opened in Codex keeps its `CLAUDE.md` and still works — every
kernel skill accepts any of `CLAUDE.md` / `AGENTS.md` / `AGENTS.override.md` /
`CODEX.md` when *detecting* a campus, and only writes the resolved one.

### 3. Codex truncates long instruction files at 32 KiB

`project_doc_max_bytes` (32 KiB default) caps the **combined** auto-loaded
instruction chain and truncates silently past it. Claude has no published
equivalent.

The campus is built to dodge this: the root entry file is a short redirect, and
the real brain in `dean/` is read *by instruction*, not by auto-discovery. But
if your `dean/` file grows past ~32 KiB and you ever put campus content directly
in the root entry file, it will silently truncate. Raise the cap in
`~/.codex/config.toml` if you need to:

```toml
project_doc_max_bytes = 65536
```

---

## What should work identically

`skills/` · `templates/` · `packs/` · `tools/` port **unchanged** — that is the
substance of the portability claim. Business memory, the wiki, the registry, the
playbooks runtime, and the activity ledger are markdown and JSON with no vendor
calls in the kernel.

What is **Claude-only** and will not work here: scheduled/recurring tasks (the
off-Claude floor is manual runs) and any MCP connector Codex does not support.
Both are the convenience layer, not the brain.

---

## If you are testing this

The open question is not whether it installs — that is already demonstrated.
It is whether it **runs**. Worth reporting back:

1. Did founding produce a sensible campus, and is the root file `AGENTS.md`?
2. Does a health check pass from inside the campus?
3. **Does one full playbook run end to end?** ← this is the actual test
4. Anything that read as broken but wasn't, or worked but shouldn't have

Item 3 is the one that matters. Installing proves packaging; only a real run
proves portability.

---

*Campus AI OS · one source, two hosts · `PLATFORM.md` holds the resolution rules.*
