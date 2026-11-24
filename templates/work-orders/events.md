# Work Order events (Gate B)

**The rule:** a Work Order file holds the *intent*. What *happened* is recorded as events. Views compute status from the events, so nobody hand-edits a status line and nothing guesses status from prose.

## Where events go
Events go into **the writing seat's own activity log**: the file the seat resolver returns (`.campus-os/ledger-paths.md`): the clock owner's shared log, or a seat's own shard `dean/.activity.{seat}.jsonl`.

Each event is an ordinary log line in the existing shape, with two extra fields, `wo_id` and `event`. Existing readers see a normal line (reading is permissive), and no new log file is created. Each seat appends only to its own file, so two apps can never overwrite each other.

```json
{"ts":"2026-09-29T14:02:11Z","seat":"mac-claude-code","platform":"claude-code","session":"<human label>","session_id":"<app chat id>","skill":"work-order","trigger":"<one line: why>","dept":"sales","outcome":"started","files_touched":0,"wo_id":"WO-2026-09-29-01","event":"started"}
```

`skill` is always `work-order`. `outcome` repeats `event`, so older tools that only read `outcome` still show something sensible.

## Event types
| Event | Written when | Extra fields |
|---|---|---|
| `drafted` | the Work Order file is created | `path` |
| `signed` | the owner, the chief of staff (inside the envelope) or a PRD approval signs | `signed_by` |
| `claimed` | a seat takes the job | `until` (ISO time). A claim older than `until` has lapsed. |
| `started` | work begins in a chat | — |
| `decision-needed` | a decision card is raised | `deadline` |
| `decided` | the owner answers, or the default applies at the deadline | `decision`, `by` (`owner` / `default`) |
| `blocked` | a stop rule fires or something blocks | `reason` |
| `change-order` | scope, budget or permissions need to grow | `request` |
| `done` | done-means met; proof in place | `proof` (paths / links) |
| `verified` | the named verifier checked the proof | `verifier`, `passed` (true / false) |
| `closed` | run record filled in, scored | `decision` (keep / change / stop) |
| `run` | *standing only:* one scheduled run finished | `result` (`ok` / `empty` / `failed`) |
| `stopped` | the owner says stop (from any app). Every seat checks the Work Order's status before acting, so a stopped job halts at the next step. `started` resumes it. | `by` (`owner`), `reason` |

## Who can move a job
An event counts only from the log of the seat it names. `signed`, `claimed`, `started`, `decided`, `change-order`, `verified`, `stopped` and `closed` count only from a **primary** seat; a satellite (or an app not assigned in `.campus-os/seat.json`) can report `done`, `blocked`, `decision-needed` and `run`, and its new Work Orders land as proposals in its own lane. `wo.py status` says how many lines it did not count. A campus with no `seat.json` counts every log, as before 5.3.0.

## Status is computed, not written
The latest event wins, with these rules:
- `signed` and nothing after it → **ready to start**
- `claimed` or `started`, still inside `until` → **working** (shows who holds it)
- `decision-needed` without a later `decided` → **needs you**
- `blocked` → **blocked**
- `done` without `verified` → **awaiting verification**
- `verified` with `passed: true` → **finished**
- `verified` with `passed: false` → back to **working**
- `stopped` → **stopped by the owner** (a seat that sees this logs `done` or `blocked` with the state it left things in, then stops)
- `closed` → archived
- *standing:* N `run` events in a row with `result: empty` → the stop rule fires (see its `stop_rules`)

The `status:` line in the file is only a cache, for people reading the file directly. When it disagrees with the events, the events win.

## Writing events
Use the tool rather than hand-writing JSON:

```bash
python3 -I -B .campus-os/kernel/tools/wo.py event WO-2026-09-29-01 started --client claude-code --note "picked up from Ready"
```

Run it from the campus root. It resolves the seat with `.campus-os/resolve-seat.py`, which is read-only, and appends to that seat's log. The other commands: `new quick|full|standing "Title" --dept "<label>" --client <this app>`, `check`, `status`, `status --by-project`, `find <words>`, `list`.
