# PLATFORM.md — the two platform facts, resolved once

**Status:** kernel reference. Added v5.1 (payload item 7) after portability leg 1
was proven on Codex.

This file is the **single owner** of the two facts that differ between host
platforms. No skill, script, or template may hardcode either one. If you find
yourself typing `CLAUDE.md` or `.claude-plugin/` into kernel logic, you are
writing the defect this file exists to prevent — and build gate check 7 will
fail the build.

---

## Why this file exists

Campus AI OS v5.0.3 runs on Codex as a native plugin. `skills/`, `templates/`,
`packs/`, and `tools/` ported **unchanged** — the kernel is platform-neutral.
What did not port was the *binding*: ~55 references to a manifest directory and
a workspace entry filename, concentrated in four files.

Those references are the same defect class as the version marker fixed in
5.0.3: **one shared fact, many private copies, no single reader.** The 5.0.3 fix
itself demonstrated the trap — it removed a hardcoded version by adding a
hardcoded manifest path in three skills. Same class, three hours apart.

The rule: **resolve, don't hardcode.** One owner per shared fact, plus a check
that fails loudly.

---

## Fact 1 — `PLUGIN_MANIFEST`

> **Named `PLUGIN_MANIFEST`, not `MANIFEST_PATH`, deliberately.** Interop Spec
> v1.1 already reserves **MANIFEST** for the *run* manifest
> (`MANIFEST.completed_steps[]` in a playbook run dir). Two different manifests
> sharing a name is the ambiguity this file exists to prevent. Do not rename it
> back.

The plugin's own manifest. Resolve by probing this ordered list against the
installed plugin directory and taking the **first that exists**:

| # | Path | Platform |
|---|---|---|
| 1 | `.claude-plugin/plugin.json` | Claude / Claude Code / Cowork — **the OWNER** |
| 2 | `.codex-plugin/plugin.json` | Codex / OpenAI — **derived, never hand-edited** |
| 3 | `plugin.json` | bare / unknown host |
| 4 | `.agents/plugins/marketplace.json` | Codex marketplace record |

**Codex constraint (verified):** *"Only `plugin.json` belongs in `.codex-plugin/`."* Never put
anything else in that directory.

### The Codex manifest is DERIVED, not maintained

`.codex-plugin/plugin.json` is **generated** from `.claude-plugin/plugin.json`
(plus the one documented Codex addition, `"skills": "./skills/"`), and the build
gate verifies byte-for-byte that it still matches.

```bash
python3 tools/build_niche.py --sync-manifests   # regenerate after any manifest edit
```

**Edit the Claude manifest. Never the Codex one.** A hand-kept second manifest
would be two copies of name/version/description with nothing reconciling them —
precisely the defect this file exists to prevent. A parity check between two
hand-maintained files is a smoke alarm; derivation is a fix.

*Earned the hard way:* a hand-forked Codex build (2026-07-25) stamped its
manifest `5.0.3+codex.<timestamp>`. That single hand-edit broke version lockstep
with `pack.json`, the registry template, and three skill frontmatters — **seven
gate failures from one copied value.** Replayed as a negative test; the gate now
catches it and prints the repair command.

Read `version`, `name`, and any other manifest field from **`PLUGIN_MANIFEST`**,
never from a literal.

`OS_VERSION` (established v5.0.3) is now defined as: `PLUGIN_MANIFEST` →
`version`. That is the only change to the version rule — it gains a resolved
source instead of a literal one.

**Precedent:** `skills/hr-registry/scripts/scan_workforce.py` already probed a
list rather than a literal. It was right before the rest of the kernel was; this
file generalises what it was already doing.

---

## Fact 2 — `ENTRY_FILE`

The workspace-root file a new session reads first — the redirect that points at
`dean/{ENTRY_FILE}` and makes the campus exist to a fresh session. Derived from
which manifest was found:

| `PLUGIN_MANIFEST` resolved to | `ENTRY_FILE` |
|---|---|
| `.claude-plugin/` | `CLAUDE.md` |
| `.codex-plugin/` | **`AGENTS.md`** |
| bare / unknown | `CLAUDE.md` (safe default — most installs are Claude) |

**When reading (checking presence, repairing, upgrading):** accept **any** of
`CLAUDE.md`, `AGENTS.md`, `AGENTS.override.md`, `CODEX.md` at the campus root
as a valid entry file. A campus may legitimately carry more than one — an owner
running two clients against the same campus has an entry file per client, which
is supported and correct (see `templates/clients/`).

**When writing (founding, repair):** write `ENTRY_FILE` as resolved above.

**The distinction matters.** Reading narrowly is the live defect this fixes:
campus-doctor check 2a looked only for `CLAUDE.md` and therefore reported a
correct Codex campus as broken. Presence checks are permissive; creation is
specific.

### ⚠️ `AGENTS.md`, not `CODEX.md` — corrected 2026-07-25 against the OpenAI docs

The S217 Codex port used `CODEX.md`, and this file initially followed it. **That
was wrong.** Verified against OpenAI's published discovery order:

1. **Global:** in `CODEX_HOME` (default `~/.codex`) — `AGENTS.override.md`, else `AGENTS.md`.
2. **Project:** from the project root down to the working directory, each
   directory contributes at most one of `AGENTS.override.md` → `AGENTS.md` →
   any name listed in `project_doc_fallback_filenames`.
3. **Merge:** concatenated root-first; files nearer the working directory win.

**`CODEX.md` is not in that chain.** It came from an early Codex CLI prompting
guide and is a known documentation inconsistency (openai/codex issue #1132); the
shipped behaviour is `AGENTS.md`. A campus whose only root entry file is
`CODEX.md` is **never auto-loaded** unless the owner adds it to
`project_doc_fallback_filenames` in `~/.codex/config.toml`.

`CODEX.md` therefore stays on the **read** list as a legacy alias — so the S217
campus keeps working — and is never written.

This also settles the open naming question the other way from expected:
`templates/clients/AGENTS.md` was **right all along**, and the port was the
outlier.

### ⚠️ `project_doc_max_bytes` — a real cap, 32 KiB by default

Codex stops adding instruction files once the **combined** chain reaches
`project_doc_max_bytes` (**32 KiB default**), and truncates. Claude has no
equivalent published cap, so this constraint is Codex-only and easy to miss.

The redirect pattern mostly dodges it: the root entry file is small and points
at `dean/{ENTRY_FILE}`, which is read *by instruction* rather than by
auto-discovery. But two things follow, and they are not optional:

- **Keep the root entry file tiny.** It is a redirect, not a brain. Anything
  bulky belongs in `dean/`.
- **A campus brain can outgrow the cap.** The shipped template
  `templates/dean-CLAUDE.md` is ~8 KB (fine). A mature campus is not — the
  TrainingSites dogfood `dean/CLAUDE.md` measured **35,876 B on 2026-07-25,
  already past 32 KiB.** If an owner ever places campus content directly in the
  auto-discovered chain, it silently truncates. Owners can raise the limit in
  `~/.codex/config.toml`; the kernel should not assume they have.

---

## Rules

1. **Never hardcode either fact in kernel logic.** Resolve at skill start,
   exactly as `OS_VERSION` is resolved.
2. **Prose may name a platform; logic may not.** "Claude reads the root
   CLAUDE.md" in an explanatory sentence is fine. `read .claude-plugin/plugin.json`
   as an instruction is not.
3. **Presence checks accept all known entry files. Creation writes the resolved
   one.**
4. **Adding a platform means adding two rows to this file** — a manifest probe
   entry and an entry-file mapping — and nothing else. If a new platform
   requires edits anywhere else in the kernel, the binding has leaked again and
   the leak is the bug.

---

## Who reads this

| Consumer | Uses |
|---|---|
| `skills/campus-start` | both — resolves `OS_VERSION`, writes the root `ENTRY_FILE` redirect |
| `skills/campus-doctor` | both — check 2a (entry file present) and check 2c (version marker) |
| `skills/update-workspace` | both — `OS_VERSION` for markers, `ENTRY_FILE` for the additive redirect repair |
| `skills/hr-registry/scripts/scan_workforce.py` | `PLUGIN_MANIFEST` probe order |
| `tools/build_niche.py` | `PLUGIN_MANIFEST` for version parity + gate check 7 enforces rule 1 |

---

## Appendix — verified host packaging spec (checked 2026-07-25)

Everything below was read from the vendors' own docs, not inferred. Re-check at
each major cut; these are living specs.

### Codex plugin layout (documented)

```
my-plugin/
  .codex-plugin/
    plugin.json     REQUIRED — the manifest, and the ONLY file allowed here
  skills/
    my-skill/SKILL.md
  hooks/hooks.json  optional
  .app.json         optional — app / connector mappings
  .mcp.json         optional — MCP server configuration
  assets/           optional — icons, logos, screenshots
```

`plugin.json` fields — **required:** `name` (kebab-case), `version`,
`description`. **Optional:** `author`, `homepage`, `repository`, `license`,
`keywords`, `skills`, `mcpServers`, `apps`, `hooks`, `interface`.

Our manifest satisfies all three required fields, and `campus-ai-os` is already
kebab-case. It also carries `interface` (displayName · shortDescription ·
longDescription · developerName · category · capabilities · websiteURL ·
defaultPrompt · brandColor) — that block drives the marketplace listing, and was
adopted from a parallel Codex build that had populated it when this one hadn't.

**Install (local):** copy the plugin folder to `~/.codex/plugins/{name}` and
register it in `~/.agents/plugins/marketplace.json`.
**Marketplace:** `$REPO_ROOT/.agents/plugins/marketplace.json`
(`name` · `interface` · `plugins`); added with
`codex plugin marketplace add <owner/repo | url | path>`.

**No file-count or plugin-size limit is stated** in the docs. (An automated
extraction asserted a 100-file cap; a direct re-read returned *not stated*. It
was not real — do not propagate it.)

**Extra top-level folders are NOT STATED** either way. Ours (`templates/`,
`packs/`, `tools/`, `playbooks/`, `campus-map/`) are undocumented but inert —
skills reach them by relative path, so they travel with the bundle regardless of
whether the host indexes them.

### ⚠️ `commands/` does not port — Claude-only

Codex's documented plugin layout has **no `commands/` directory.** Codex's
equivalent, *custom prompts* (`~/.codex/prompts`, invoked `/prompts:name`), is
**local-only, not shareable via a repo or plugin, and marked deprecated** —
OpenAI's guidance is to use skills instead.

This kernel ships **27 commands** in `commands/`. They do **not** become slash
commands on Codex. The underlying skills all port and remain invocable by name
or implicitly; what is lost is the `/campus-start`-style invocation surface.

**This qualifies the S217 "ported unchanged" claim.** `skills/` did port
unchanged — that part holds. The *command layer* did not, and nothing in the
census measured it because it isn't a `CLAUDE.md` or `.claude-plugin` string.
**Owner decision, not a code fix:** accept the loss, mirror the 27 commands as
thin skills, or ship a Codex-specific invocation note. Logged in
`dean/tasks/campus-os-v5-1-packaging.md` §7.

### Claude plugin layout (for contrast)

`.claude-plugin/plugin.json` + `skills/` + `commands/` — the manifest directory
and the command surface are the two differences that matter.

---

*Campus AI OS kernel reference · one owner per shared fact · rules that matter
ship as code that checks them.*

*Host specs verified 2026-07-25 against `developers.openai.com/plugins/build/plugins`,
`learn.chatgpt.com/docs/build-plugins`, and
`learn.chatgpt.com/docs/agent-configuration/agents-md`.*
