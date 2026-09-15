# MOVED — this is a pointer, never a copy

The shared-context canon now lives at **`templates/context-files.md`** in this
plugin, and is scaffolded onto every campus as
**`{campus_root}/.campus-os/context-files.md`** by both `/campus-start` and
`/update-workspace`.

**Resolve `CONTEXT_CANON` in this order, first hit wins:**

1. `{campus_root}/.campus-os/context-files.md` — the campus copy. **This wins.**
2. `templates/context-files.md` in the running plugin — the source of that copy,
   and the fallback in peer / pre-founding mode.

## Why this file still exists

It is a **pointer, not a second copy** — higher layers point down, they never
duplicate. Anything still referencing the old path
(`../atlas-setup/references/context-files.md`) lands here and is redirected
rather than silently reading a stale table. That matters because five other
shipped plugins bundle their own copy of this canon and reference paths like
this one; they adopt the campus copy on their own version bumps, never forced.

**Do not restore the alias table here.** A second rendering of the canon is the
exact defect the move was made to close — this file previously carried an alias
list that had been wrong since v4.1.4, and a duplicate of it in
`campus-mode.md` had gone stale in the same way. Build-gate check 13b fails the
build if the table reappears anywhere but the owner.
