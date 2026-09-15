# Campus AI OS for Codex

This is the Codex-native adapter of Campus AI OS (version: see `.codex-plugin/plugin.json`).

## Adapter conventions

- The campus chief-of-staff file is `dean/CODEX.md`.
- Skills use Codex workspace and plugin conventions, including `.codex-plugin/plugin.json` for version resolution.
- Command files are retained as reference prompts; Codex discovers behavior through `skills/*/SKILL.md`.
- The original source archive remains unchanged.

## Start prompts

- `set up my campus`
- `campus-start`
- `run campus-doctor`
- `run my weekly reset`
