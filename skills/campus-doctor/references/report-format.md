# Report format - the shape of the doctor's output

Companion to `/campus-doctor` step 5. One header, one line per finding, one
next action. The evidence command's `line` values are the base text; the
doctor rewrites them for a reader who has never opened a terminal.

```
Campus Health  -  {date}

[OK] Workspace connected and writable
[OK] Setup file present (v{OS_VERSION})
[OK] Version current (v{OS_VERSION})  -  workspace, registry and installed plugin agree
[!!] 2 teams installed but not registered: {names}  -  say "register them" and I'll fix it
[--] Voice file still default  -  Dean guesses your tone until this is filled (60 sec)
[--] Goals file still default  -  set the one number and this week's focus (60 sec)
[--] Tools file still default  -  tell me what runs your email + community
[OK] No stale work
[--] Startup reads 26,400 tokens (13% of the window)  -  archive due. Heaviest: memory (18,900, mostly "Recent sessions")  -  say "show me what to archive" and I'll propose it
[OK] 0 teams registered / 0 off-spec  -  add-on teams register themselves when installed
[OK] Registration spec current
[--] Fleet sweep (monthly): 14 teams, 5 with errors  -  seo-team 1 · copy-team 10 · campus-ambassador 7 · offer-team 22 · tech-advisor-team 1; each is that team's next-cut work
[OK] Your staff: 23 employees + 20 campus systems + 2 playbooks  -  {label} {n}, {label} {n}, ... in registry order
[--] Your org chart isn't counting 4 departments you run (Coaching Delivery, Client Success, Education, Marketing/Sales)  -  say "register my departments" and I'll add them under your names
[--] Connections: 2 detected (email OK, community OK)  -  highest-value missing: calendar
[OK] Recurring work: 3 scheduled jobs  -  3 running, 0 switched off
[!!] Work diary last written 12 days ago  -  I'll catch it up at the end of this session
[OK] Every seat wrote inside its own lane
[!!] 3 work diary lines don't say which seat wrote them  -  e.g. dean/.activity.jsonl line 242
[OK] No sync hazards
```

The staff line's department names come from each entry's `label` in the
registry (see `evidence-sections.md`); the placeholders above are placeholders,
not a template to paste. The counts in the example are illustrative and never
asserted.

## Legend and rules

- `[OK]` fine · `[--]` opportunity · `[!!]` needs a decision or fix.
- Every `[!!]` and `[--]` carries its one-line fix or the question that
  unblocks it. Fixes may name a file; summary lines do not.
- End with at most ONE suggested next action, never a list of chores. When
  everything is green for the first time, that action is "run this weekly as
  a scheduled task".
- Skipped sections print their one skipped line only when the skip is worth
  knowing (no scheduler list supplied, Node absent, no Foundry); the monthly
  sweep outside its window prints nothing.
- A tool failure (`error` from a sub-tool, or exit 2 from the evidence
  command) is reported as a tool problem on that line - "I couldn't measure
  {thing}: {stderr tail}" - and never as a campus finding. Never invent the
  missing number.
- Never auto-fix anything destructive; offer, then wait. Record repairs
  (version stamp, spec refresh, entry-file redirect, department entries) are
  the only repairs this skill performs, each on an explicit yes.
