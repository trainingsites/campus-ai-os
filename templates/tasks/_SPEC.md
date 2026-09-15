# Task System v2 — the spec

**One file per task. The list is generated.**

This folder is where your campus tracks work. It replaces the single long
`TASKS.md` that every session had to read in full and edit by hand.

---

## The two pieces

| | What it is | Who edits it |
|---|---|---|
| `dean/tasks/{slug}.md` | **One file per task.** Frontmatter = current state. Body = the history. Permanent — never deleted, even when done. | You and your assistant, whenever something changes |
| `dean/TASKS.md` | **A generated index.** Cheap to skim, rebuilt from the task files. | **Nobody.** It is baked. |

Change a task → edit **its file** → rebake the index:

```bash
python3 tools/generate_task_index.py --tasks dean/tasks --out dean/TASKS.md
```

---

## Why the index is generated rather than maintained

A hand-kept summary of a list always drifts from the list. Not sometimes —
always, because updating two things is one more step than updating one, and the
step that gets skipped is the summary.

So the index is *derived*. It cannot disagree with the task files, because it is
thrown away and rebuilt from them. And there is a check that proves it:

```bash
python3 tools/generate_task_index.py --check
```

A mismatch means one of two things, both worth knowing:

- someone edited the index directly — **that edit is about to be lost**, or
- a task changed and nobody rebaked — **the index is lying right now**

Neither is visible by reading the file, which is exactly why it is a check and
not a note asking people to be careful.

---

## Frontmatter

```yaml
---
id: my-task-slug          # matches the filename
title: "Short human title"
stage: queued             # see the stages below
lane: null                # optional grouping
dept: marketing           # optional owning department
status: "One line on where this actually stands"
needs: null               # REQUIRED when stage is waiting-owner
updated: 2026-07-26       # YYYY-MM-DD
external_ref: null        # optional link out
---
```

Everything below the frontmatter is free-form history. Append to it; don't
rewrite it. The body is how a future session learns what was already tried.

---

## The stages

| Stage | Means | Flagged stale after |
|---|---|---|
| `waiting-owner` | Blocked on a human decision. **Must have a `needs:` line saying what.** | 7 days |
| `active` | A session is working it **right now** | 4 days |
| `queued` | Approved, not started | — |
| `blocked` | Stuck on something external | — |
| `done` | Finished. Drops from the index after 7 days; the file lives forever | — |
| `idea` | Captured, not committed to | — |

**`active` goes stale fast on purpose.** "Active" means someone is on it today.
If nothing has touched it in four days it is really `queued`, and work filed
under the wrong stage is work nobody can see.

**`waiting-owner` without `needs:` is a lint error.** A task that says it is
waiting on you but not *what for* makes you reconstruct the question before you
can answer it — which is why it has been sitting there.

---

## What is NOT a task

**Recurring jobs.** They live in `scheduled/`, their runs go to the activity
ledger, and only a *failure* earns a task file.

Filing one task per scheduled run buries real work under machine noise. A weekly
job creates 52 task files a year and not one of them is a decision anyone needs
to make.

---

## The rules worth keeping

1. **Write the change when it happens**, not at the end of the session. A task
   file edited during the work is accurate; one reconstructed at wrap-up is a
   guess.
2. **Never hand-edit the index.** `--check` will catch it, but the edit is gone
   either way.
3. **Task files are permanent.** Done is a stage, not a delete. The history is
   the point — it is what stops the same thing being re-litigated in three
   months.
4. **One task, one file.** If two things can be finished independently, they are
   two tasks.
