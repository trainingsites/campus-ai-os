# Kernel preamble — the rules every kernel skill runs under (5.2.0 Phase 5.1)

**This file is the ONE owner of the three paragraphs that used to be pasted into skills.** A skill
says `Kernel preamble §N applies: references/kernel-preamble.md` and nothing more; the text lives
here once. Before 5.2.0, fourteen skills carried §1 word-for-word, seven carried §2 in **five
different wordings** (the drift a pasted paragraph always develops), and three carried §3.
Same ownership pattern as `templates/context-files.md`: one home, every reader reads it.

The model reads this file when a skill names it. It is short on purpose.

## §1 Campus present? (the setup check)

If `workspace.json` does not exist in the campus folder, tell the owner: "Your workspace hasn't
been set up yet. Run `/campus-start` first to hire your AI team." — and stop. Nothing below runs
without a campus. (Founding itself, `campus-start`, is the one skill this does not apply to;
`update-workspace` treats `dean/{ENTRY_FILE}` as the campus marker until `workspace.json` exists.)

Resolve every shared-context file through the canon (`.campus-os/context-files.md` on the campus,
else `templates/context-files.md` in the kernel): canonical name → legacy alias → case-insensitive
match. Never hard-code a `shared/*.md` filename. "Read the resolved `icp` context" in a skill means
exactly this resolution.

## §2 Where files go (the campus-folder write rule)

Every file this skill writes goes inside the CAMPUS FOLDER — the connected folder that contains
`workspace.json` (before founding completes: the folder that contains `dean/{ENTRY_FILE}`).
Resolve every path from that root. NEVER write to a session scratchpad, temporary "outputs"
directory, or any path outside the campus folder — in some environments a bare relative
`outputs/` resolves to a temporary location the owner will never see, and the work is effectively
lost. After saving, verify the file exists under the campus root; if it landed anywhere else, move
it into the campus and say so.

Run directories come from the minter (`tools/mint_run_id.py`), never formatted by hand; results go
in the run directory as envelope v1.1 (`schemas/results.schema.json`); the activity line goes to
this seat's ledger per `.campus-os/ledger-paths.md`. The full contract: `.campus-os/run-id-and-interop.md`.

## §3 Starter employee note

This starter employee covers the essentials. A dedicated agent team plugin (deeper skills, run
ledgers, done-checks, interop with your other teams) is available for this role as a paid add-on.
Ask your orchestrator: "what team upgrades exist for this role?" — it will check the plugin
catalog your OS came from.

---

*Owner: this file. A skill that needs to say any of the above says "Kernel preamble §N applies"
and points here. Build gate: no paragraph of eight or more words may appear in three or more
kernel skills (`tests/test_phase5_preamble.py`).*
