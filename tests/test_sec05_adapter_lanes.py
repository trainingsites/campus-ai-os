"""Campus AI OS 5.3.0 item 2 - SEC-05: adapter lane rules are resolver-driven.

Codex audit of 5.2.5 (SEC-05) + shared-platform evaluation 2026-09-17: the Codex
adapter's lane rules were static, and the contract's ledger_path() chose the
shared ledger by ROLE while tools/resolve-seat.py chooses it by `owns_clock`.
The resolver is the truth. This gate runs the real resolver for a clock-owner
primary, a non-clock primary and a satellite, and fails if the contract
resolvers, the generated contract, the adapter or the ledger docs grant a
satellite or a non-clock primary the shared ledger or shared-output writes.
Kernel-only; runs everywhere.
platform: claude-code; seat: m4-claude-code
"""
import importlib.util
import json
import os
import re
import unittest
from pathlib import Path

KERNEL = Path(os.environ.get("KERNEL_SRC", Path(__file__).resolve().parent.parent)).resolve()
SHARED = "dean/.activity.jsonl"
MACHINE = "a" * 64
CONFIG = {
    "schema_version": 2, "machine_id": MACHINE, "clock_owner": "claude-cowork",
    "clients": {
        "claude-cowork": {"seat": "owner-cowork", "role": "primary"},
        "claude-code": {"seat": "owner-code", "role": "primary"},
        "codex": {"seat": "codex", "role": "satellite"},
    },
}
DOCS = ("templates/clients/AGENTS.md", "templates/ledger-paths.md", "templates/dean-CLAUDE.md",
        "templates/dean-CODEX.md", "contracts/campus-contract.md", "templates/model-routing.md")
# Kernel prose that WRITES a ledger must resolve it, never name the shared file as the target.
WRITE_VERB = re.compile(r"(Log the run to|appends? one (activity-ledger )?line|one activity-ledger line per stage to)[^.]*`?dean/\.activity\.jsonl")


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class AdapterLanes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rs = load(KERNEL / "tools" / "resolve-seat.py", "resolve_seat_sec05")
        cls.out = {c: rs.resolve(CONFIG, c, MACHINE) for c in CONFIG["clients"]}
        cls.contract = json.loads((KERNEL / "contracts" / "campus.json").read_text(encoding="utf-8"))
        cls.resolver = load(KERNEL / "tools" / "contract.py", "contract_sec05").Resolver()
        cls.adapter = (KERNEL / "templates" / "clients" / "AGENTS.md").read_text(encoding="utf-8")

    def test_resolver_decides_by_owns_clock(self):
        owner, peer, sat = self.out["claude-cowork"], self.out["claude-code"], self.out["codex"]
        self.assertEqual((owner["role"], owner["owns_clock"], owner["ledger"]), ("primary", True, SHARED))
        self.assertEqual((peer["role"], peer["owns_clock"]), ("primary", False))
        self.assertEqual(peer["ledger"], "dean/.activity.owner-code.jsonl")
        self.assertEqual((sat["role"], sat["owns_clock"], sat["ledger"]), ("satellite", False, "dean/.activity.codex.jsonl"))
        self.assertIsNone(sat["warning"])

    def test_contract_resolver_matches_actual_resolver(self):
        for client, out in self.out.items():
            got = self.resolver.ledger_path({k: out[k] for k in ("seat", "role", "owns_clock")})
            self.assertEqual(got["ledger"], out["ledger"], f"contract ledger_path disagrees with resolve-seat.py for {client}")

    def test_contract_fails_closed_without_owns_clock(self):
        got = self.resolver.ledger_path({"seat": "owner-code", "role": "primary"})
        self.assertNotEqual(got["ledger"], SHARED, "a primary with no owns_clock was granted the shared ledger")
        for bogus in ("yes", 1, None):
            got = self.resolver.ledger_path({"seat": "owner-code", "role": "primary", "owns_clock": bogus})
            self.assertNotEqual(got["ledger"], SHARED, f"owns_clock={bogus!r} granted the shared ledger")
        got = self.resolver.ledger_path({"seat": "codex", "role": "satellite", "owns_clock": True})
        self.assertNotEqual(got["ledger"], SHARED, "a satellite claiming owns_clock was granted the shared ledger")

    def test_generated_contract_states_the_rule(self):
        seat = self.contract["seat"]
        self.assertEqual(seat["ledger"].get("decided_by"), "owns_clock")
        for key in ("co_primary", "satellite", "unknown"):
            self.assertNotEqual(seat["ledger"][key], SHARED, key)
        rules = " | ".join(seat["rules"])
        self.assertIn("the ledger follows owns_clock, never role", rules)
        self.assertIn("satellites never write shared outputs or primary-owned paths", rules)
        tables = (KERNEL / "contracts" / "campus-contract.md").read_text(encoding="utf-8")
        self.assertIn("Decided by `owns_clock`", tables)

    def test_adapter_is_resolver_driven(self):
        a = self.adapter
        self.assertIn("resolve-seat.py --client codex", a)
        self.assertNotIn("Your working lane is `active-work/lanes/codex/`", a, "static lane rule is back")
        line = next((l for l in a.splitlines() if "dean/.activity.jsonl" in l), "")
        self.assertIn("owns_clock: true", line, "the adapter must tie the shared ledger to owns_clock on the same line")
        self.assertIn("never role", a)

    def test_adapter_satellite_gets_lane_and_shard_only(self):
        rule = next((l for l in self.adapter.splitlines() if l.startswith("4. **Satellites")), "")
        self.assertTrue(rule, "adapter lost its satellite rule")
        self.assertIn("only inside its returned `lane` and its own ledger shard", rule)
        self.assertIn("no `outputs/`", rule)
        for path in self.contract["seat"]["primary_owned_paths"]:
            self.assertIn(f"`{path}`", rule, f"satellite rule does not forbid primary-owned {path}")
        for l in self.adapter.splitlines():
            if re.search(r"satellite", l, re.I) and "outputs/" in l:
                self.assertIn("no `outputs/`", l, f"adapter line may grant a satellite shared outputs: {l}")

    def test_gemini_adapter_follows_the_same_resolver_rules(self):
        g = (KERNEL / "templates" / "clients" / "GEMINI.md").read_text(encoding="utf-8")
        self.assertIn("resolve-seat.py --client gemini", g)
        self.assertNotIn("Your working lane is `active-work/lanes/gemini/`", g, "static lane rule is back")
        self.assertNotIn("propose-don't-edit", g)
        section = re.search(r'sections "(.+?)"', " ".join(g.split())).group(1)
        self.assertIn(f"## {section}", self.adapter, "GEMINI.md cites an AGENTS.md section that does not exist")
        line = next((l for l in g.splitlines() if "resolves as a satellite" in l), "")
        for needle in ("only inside its returned `lane` and its own ledger shard", "never `outputs/` or the shared ledger"):
            self.assertIn(needle, line)

    def test_no_kernel_writer_hardcodes_the_shared_ledger(self):
        hits = []
        for root in ("skills", "playbooks", "templates", "references", "commands"):
            for f in sorted((KERNEL / root).rglob("*.md")):
                for n, l in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                    if WRITE_VERB.search(l) and "clock owner" not in l:
                        hits.append(f"{f.relative_to(KERNEL)}:{n}")
        self.assertEqual(hits, [], "writers must use the ledger their seat resolves to: " + "; ".join(hits))

    def test_docs_never_grant_shared_ledger_by_role(self):
        for rel in DOCS:
            for n, l in enumerate((KERNEL / rel).read_text(encoding="utf-8").splitlines(), 1):
                if SHARED in l and not re.search(r"clock|NEVER hard-code|by literal path|older wording", l):
                    self.fail(f"{rel}:{n} names the shared ledger without tying it to the clock owner: {l.strip()[:120]}")


if __name__ == "__main__":
    unittest.main()
