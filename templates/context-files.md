# Shared-context files — canonical names, fields, resolution (Team Interop Spec v1 §5A)

**This file is the ONE owner of every shared-context filename on this campus.**
Skills NEVER hard-code `shared/icp.md` etc. They resolve a context file through
this canon: **founding name → canonical name → legacy alias, each matched
case-insensitively before the next is tried** (5.2.13; see the resolution
algorithm below). An OS rename or case
difference must not break inherit.

## How to find THIS file (canon resolution) — added v5.1.1

Resolve `CONTEXT_CANON` in this order, first hit wins:

1. **`{campus_root}/.campus-os/context-files.md`** — the campus's own copy,
   written by `/campus-start` at founding and by `/update-workspace` on upgrade.
   **This one wins.** It is refreshed by the kernel on every upgrade, so a fix
   here reaches every installed team without any of them repackaging.
2. **`templates/context-files.md` in the plugin that is running** — the source
   the campus copy is made from, and the fallback in peer / pre-founding mode
   where no campus exists yet.

*Why this exists.* Before v5.1.1 this canon was a file bundled inside one
skill's `references/`, and **six shipped plugins each carried their own copy**
(campus-ai-os, 3p-teaching-system, course-lab, copy-team, offer-team,
prep-agents-team). They drifted exactly as two hand-maintained copies of a fact
always do — three of them still listed aliases that had been wrong since v4.1.4.
Correcting the canon therefore cost six repackages, which is why it never
happened. Same pattern as `registration-block-spec.md`: the kernel owns the
template, the campus holds the copy, every reader reads the campus copy.
*A parity check between hand-maintained files is a smoke alarm; one owner is a
fix.*

## Canonical filenames (and legacy aliases to accept on read)
| Concept | Canonical | Legacy aliases (accept on read) |
|---|---|---|
| Owner/business basics | `identity.md` | `business.md` (**what founding actually writes** — list it first); may also be inside the campus entry file — resolve `ENTRY_FILE` per `PLATFORM.md`, never assume a filename |
| Audience / ICP | `icp.md` | `audience.md` (**what founding actually writes** — list it first), `icp-summary.md` |
| Brand | `brand.md` | `BRAND.md`, `brand-style.md` |
| Voice / tone | `voice.md` (**what founding actually writes**) | `voice-profile.md`, else inside `brand.md` |
| Goals / OKRs | `goals.md` (**what founding actually writes**) | — |
| Offers | `offers-summary.md` (**owns every price** — one summary, one owner; **canonical wins**) | `offers.md` (**what founding actually writes** — list it first; the long-form offer notes, never the price authority) |
| Tool/connection map | `connections.md` | `tools.md` (**what founding actually writes** — list it first), `campus-connections.md`, `SYSTEMS.md` (MCP Health table) |

⚠️ **Do not "tidy" `tools.md`, `business.md`, or `audience.md` out of those
rows — they are the names `campus-start` actually writes.** Build-gate check 13a
fails the build if founding writes a `shared/` file this canon has never heard
of, because that is a reader finding nothing on a campus that is perfectly
healthy.

**The three instances this rule was written from (v5.1.1):**

| Founding writes | Canon called it | Consequence before the fix |
|---|---|---|
| `shared/tools.md` | `connections.md` | six starter employees (social-planner, offer-builder, community-pulse, launch-planner, content-repurposer, email-sequence) read a **third** name, `campus-connections.md`, that no path has ever written — since v4.1.4 |
| `shared/business.md` | `identity.md` | `identity` resolved to nothing on every founded campus |
| `shared/audience.md` | `icp.md` | `icp` resolved to nothing, so Atlas's inherit step would re-ask a correctly-founded campus for its audience |

⚠️ **`icp.md` is the canonical name and NOTHING WRITES IT.** Both founding paths
write `shared/audience.md`. Before v5.1.1, **14 kernel files and 23 files across
9 other plugins read `shared/icp.md` directly** and therefore found nothing on
every correctly-founded campus. It stayed invisible for one reason worth
remembering: the campus it was developed on predates the founding convention and
holds the *canonical* names by hand — so every one of those readers worked
perfectly there and only there. **Read-side defects hide on the developer's own
campus when the developer upgrades rather than founds.**

One fact, several names, and the name that exists on disk was the one nobody
listed. These aliases are the read-side repair: they need no migration and reach
every campus the moment the plugin is installed. `setup-progress.md` is
deliberately absent — it is setup state, not business context, and no skill
resolves it as a concept.

**Resolution algorithm (per concept, 5.2.13):** try `{dir}/{founding name}` →
`{dir}/{canonical}` → each remaining alias in listed order. Each name is
matched against the real directory listing, exact spelling first and then
case-insensitively, **before the next name is tried**, and the file's real
spelling is returned. First hit wins. Absent = "not captured yet." (5.2.12 ran
all exact names before any case-insensitive one, so `offers.md` beat
`OFFERS-SUMMARY.MD` and `icp.md` beat `AUDIENCE.MD` - priority lost to
capitals. Codex audit F1.) The machine form
of this order is `read_order` on each row of `contracts/campus.json`;
`{kernel}/tools/resolve_context.py` applies it.

- **Why founding first.** Before 5.2.12 the canonical name was tried first. A
  team that "wrote if missing" a thin `icp.md` or `identity.md` beside the full
  `audience.md` / `business.md` from founding then won every read, and the
  owner's real answers were never read again. The file the owner's own setup
  wrote is the fullest one, so it is read first.
- **Exception: a row marked canonical wins.** Offers keeps `offers-summary.md`
  first, because it owns every price. `offers.md` is the long-form notes.
- **Brand has no founding name.** Nothing at founding writes a brand file, so
  its order starts at the canonical name.

**Write rule.** A skill writes into the file a concept already resolves to (on a
founded campus, append a section there). It never creates a second name for a
concept that already resolves. Only when nothing resolves does it create the
founding name (or the canonical name where there is no founding name).

**Campus rule (one owner for detection).** A folder is a campus when it holds
`workspace.json` and an accepted entry file (`CLAUDE.md`, `AGENTS.md`,
`AGENTS.override.md` or `CODEX.md`) either at the root or in `dean/`. Find it by
walking up from the working folder; if nothing above is a campus, accept exactly one campus among its children
(one level down, real folders only, hidden folders and links skipped). Hosts often open the folder above the
campus (Cowork mounting `MyBusiness/` for `MyBusiness/Campus/`). Two or more child campuses:
never pick one - list them and ask the owner, then use that folder. Never test for a fixed folder name such as
`Claude-Cowork/`, and never for one entry-file name alone: the owner names the
folder, and the entry file differs per host. `python3 -I -B {kernel}/tools/resolve_context.py
--find-campus` prints the root (`{kernel}` = the campus kit, `.campus-os/kernel`; rules in
`.campus-os/run-id-and-interop.md` §0).

## Where the dir is (§5A.3)
- Founded campus: `{campus_root}/shared/` — resolve `campus_root` as the directory holding `workspace.json`. Never hard-code a campus folder name; the owner chose it.
- Peer / pre-founding: `./teams-shared/context/`
Same filenames either way; only the parent dir differs (resolved by §5 detection).

## Read precedence (§5A.4) — stop at first hit
1. Campus `{campus_root}/shared/{name}` (the campus wins)
2. `./teams-shared/context/{name}` (peer shared)
3. Team-private `atlas/config/niche.md` (Atlas-only settings — last resort)

## Canonical FIELD keys (§5A.7) — write these exact keys; migration must be a copy, not a guess
- `identity.md`: `owner_name`, `business_name`, `one_liner`, `what_they_create`
- `icp.md`: `primary_audience`, `segments[]`, `pains[]`, `desires[]`, `language[]`, `buying_triggers[]`
- `brand.md`: `colors[]`, `fonts[]`, `logo_refs[]`, `visual_style`, `do[]`, `dont[]`
- `voice.md`: `tone`, `reading_level`, `signature_phrases[]`, `banned_words[]`, `examples[]`
- `goals.md`: `objectives[]` (each `objective`, `key_results[]`), `current_focus`
- `offers.md`: `offers[]` (each `name`, `price`, `promise`, `url_or_id`)

Write ONLY the files you actually filled (§5A.6) — never a half-empty file.

## For team plugins that still bundle their own copy

Your bundled copy is now a **fallback**, not the truth. On a founded campus,
read `{campus_root}/.campus-os/context-files.md` first — it is maintained by the
kernel and will be newer than anything you shipped. Adopt this on your next
version bump; nothing forces it, and nothing breaks until you do.
