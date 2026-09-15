# Security

This file states what the Campus AI OS kernel reads, what it writes, what it never does, which inputs it treats as untrusted, and how to report a problem.

## Reporting

Email security reports to james@trainingsites.io with the kernel version (from `.claude-plugin/plugin.json`) and a minimal reproduction in a scratch campus. Do not include real campus data. Fixes ship as a patch release with a Security entry in `CHANGELOG.md` naming the affected versions.

## What the kernel touches

| Surface | Reads | Writes |
|---|---|---|
| Campus workspace (the folder you connect) | Everything under it | Only inside it, by seat rules in `AGENTS.md` |
| Seat ledgers `dean/.activity*.jsonl` | All shards | Only the current seat's own shard |
| `campus-map/` | Ledgers, outputs, wiki, shared | The generated HTML only |
| Connectors (MCP tools) | As granted by the host | As granted by the host, never without an authorized skill step |
| Network | The Campus Map loads Google Fonts (fonts.googleapis.com, fonts.gstatic.com) unless built with `--no-remote-fonts`, which makes no request. The map is private-only; there is no shareable build. | Nothing |

The kernel never reads outside the connected campus folder, never stores credentials, never executes content from campus files, and never sends messages or publishes without an explicit authorization step in the skill that does it.

## Untrusted inputs

Any file another process can write is untrusted. That includes every seat ledger, everything under `outputs/`, `inputs/`, `wiki/`, and any file a connector returned. The trust boundaries are: seat ledgers, campus files, connector responses, and rendered HTML. Code that turns a string from any of these into a file path, an HTML attribute, or an instruction to a model must validate it first. Fixtures under `tests/test_security_*.py` and `tests/test_campus_map_security.py` are the record of the attack classes covered.

## Release integrity

Every release ships as a `.plugin` and a byte-identical `.zip`, with the hash emitted by `tools/package.py` into `campus-ai-os-v{version}.PACKAGE.json`. Compare the archive hash to that file before installing. Released archives are immutable; a fix is always a new version.
