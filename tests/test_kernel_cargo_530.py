"""Campus AI OS 5.3.0 item 5 - kernel cargo from the 2026-09-21 hand runs.

(a) QUICKSTART.md was headed "Campus AI OS v4.1" in the public 5.2.9 release: root
    docs carry no version literal in their title (the manifest and workspace.json
    own the version). (b) README.md / QUICKSTART.md said "education business"
    whatever the pack: the business noun now comes from the active pack.
(c) /campus-first-win offered a fixed three; it now also offers the active pack's
    own domain skills, and the education default is unchanged.
Kernel-only; runs everywhere.
platform: claude-code; seat: m4-claude-code
"""
import json
import os
import re
import unittest
from pathlib import Path

KERNEL = Path(os.environ.get("KERNEL_SRC", Path(__file__).resolve().parent.parent)).resolve()
ROOT_DOCS = ("README.md", "QUICKSTART.md", "CODEX-INSTALL.md", "PLATFORM.md", "SECURITY.md", "CODEX-ADAPTER.md")


class KernelCargo(unittest.TestCase):
    def test_root_doc_titles_carry_no_version(self):
        for name in ROOT_DOCS:
            path = KERNEL / name
            if not path.is_file():
                continue
            title = next((l for l in path.read_text(encoding="utf-8").splitlines() if l.startswith("# ")), "")
            self.assertNotRegex(title, r"\bv?\d+\.\d+(\.\d+)?\b", f"{name} title states a version: {title}")

    def test_business_noun_comes_from_the_active_pack(self):
        for name in ("README.md", "QUICKSTART.md"):
            for n, line in enumerate((KERNEL / name).read_text(encoding="utf-8").splitlines(), 1):
                if "education business" in line.lower():
                    self.assertIn("packs/active.json", line, f"{name}:{n} hardcodes the education noun")
            self.assertIn("identity.business_noun", (KERNEL / name).read_text(encoding="utf-8"), name)
        active = json.loads((KERNEL / "packs" / "active.json").read_text(encoding="utf-8"))["active_pack"]
        pack = json.loads((KERNEL / "packs" / active / "pack.json").read_text(encoding="utf-8"))
        self.assertTrue(pack["identity"]["business_noun"])

    def test_first_win_offers_the_packs_own_domain_skills(self):
        text = (KERNEL / "skills" / "campus-first-win" / "SKILL.md").read_text(encoding="utf-8")
        lines = text.splitlines()
        read = next((l for l in lines if l.startswith("**The active pack's own work")), "")
        self.assertIn("`packs/active.json` -> `active_pack`", read)
        self.assertIn("`packs/{active_pack}/pack.json`", read)
        self.assertIn("`domain_skills[]`", read)
        fallback = next((l for l in lines if l.startswith("- If that list is missing or empty")), "")
        self.assertIn("use it unchanged", fallback)
        offer = next((l for l in lines if l.startswith("- Otherwise, offer each installed skill")), "")
        self.assertIn("following that skill's SKILL.md", offer)
        # the education default table is untouched
        for row in ("| community | 5 ready-to-post discussion prompts", "| courses | a complete lesson plan",
                    "| coaching | a session prep pack"):
            self.assertIn(row, text)
        self.assertNotRegex(text, r"packs/(education|professor)/", "first-win must not hardcode a pack folder")

    def test_every_in_tree_pack_resolves_to_a_first_win(self):
        # Apply the written rule to each in-tree pack: education keeps the table; a pack with no
        # domain skills of its own keeps the table; a pack with its own domain skills gets them offered.
        table = {"community-pulse", "lesson-planner", "session-planner"}
        for pdir in sorted(p for p in (KERNEL / "packs").iterdir() if p.is_dir()):
            pack = json.loads((pdir / "pack.json").read_text(encoding="utf-8"))
            own = pack.get("domain_skills") or []
            offers = [] if (not own or table & set(own)) else own[:3]
            for skill in offers:
                self.assertTrue((KERNEL / "skills" / skill / "SKILL.md").is_file(), f"{pdir.name} offers missing {skill}")
            if pdir.name == "education":
                self.assertEqual(offers, [], "education default must stay the fixed table")


if __name__ == "__main__":
    unittest.main()
