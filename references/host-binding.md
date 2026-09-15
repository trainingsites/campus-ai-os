# Host binding (Seat Contract, 5.2.4)

**What it is.** A short-lived file, `.campus-os/host-binding.json`, that lets a session which cannot read its machine's fingerprint (a sandboxed Cowork container) resolve as the primary seat lawfully. The Seat Contract named this mechanism on 2026-08-28; 5.2.4 is the first kernel that implements it.

**Who issues it.** Only a process that observes the real fingerprint: Terminal, launchd, or Claude Code running on the host. `python3 .campus-os/resolve-seat.py --issue-binding --client <primary-client>` refuses unless the observed fingerprint equals `seat.json.machine_id` and the named client is the configured primary. A sandbox cannot issue its own binding.

**How the resolver uses it.** Consulted only in the fingerprint-unavailable branch. All of these must hold: schema 1, client matches `--client`, that client is the configured primary, `machine_id` matches `seat.json`, `issued_at` is not in the future, lifetime is at most 24 hours, `expires_at` is in the future. Then the normal path runs with every existing invariant (one primary, no double-assigned seat, client assigned). A binding never overrides a fingerprint mismatch. The result carries `"via": "host-binding"`.

**Heartbeat, not chore.** Issue it from a launchd job every 6 hours with a 12-hour TTL (`templates/host-binding-heartbeat.plist`). One missed beat survives; two go dark on purpose. If the Mac is off or the campus unmounted, the binding lapses and sandboxed sessions correctly drop to satellite. campus-doctor check 11d reports hours to expiry so a lapse is one line, not a week of blocked scheduled runs.

**Audit rule.** A session resolved via host-binding writes `"via":"host-binding"` on every ledger line (ledger-paths canon). Observed sessions write nothing extra.

**It never travels.** `.campus-os/host-binding.json` is gitignored and listed under `never_sync` in `sync-manifest.json`. A binding that syncs to a second machine is an accidental forgery, and it defeats the fingerprint check it stands in for.

**Residual risk, stated.** A client that can read the mounted folder can read `seat.json.machine_id` and could forge the file. No file-only scheme stops a deliberately hostile client. This defends the real failure class, an honest client that cannot observe its host, with a short TTL, an explicit issuer line, and an audit trail. It is a liveness and audit mechanism, not an authorization boundary; authorization comes from the fact that only the owner's machine mounts the folder.
