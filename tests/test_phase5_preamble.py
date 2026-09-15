"""Campus AI OS 5.2.0 Phase 5.1 - the shared kernel preamble replaces pasted blocks.

Plan proof: shingle scan -> 0 blocks in 3+ skills. Kernel-only; runs everywhere.
platform: claude-code; seat: m4-claude-code
"""
import os
import re
import unittest
from pathlib import Path

KERNEL = Path(os.environ.get("KERNEL_SRC", Path(__file__).resolve().parent.parent)).resolve()
PREAMBLE = KERNEL / "references" / "kernel-preamble.md"
POINTER = re.compile(r"^Kernel preamble §([123]) applies: `references/kernel-preamble\.md`\.$")
OLD_STARTS = ("If `workspace.json` does not exist",
              "Every file this skill writes goes inside the CAMPUS FOLDER",
              "This starter employee covers the essentials")


def paragraphs(path):
    txt = path.read_text(encoding="utf-8")
    body = txt.split("\n---", 2)[-1] if txt.startswith("---") else txt
    return [" ".join(p.split()) for p in re.split(r"\n\s*\n", body)]


class Preamble(unittest.TestCase):
    def skills(self):
        return sorted(KERNEL.glob("skills/*/SKILL.md"))

    def test_preamble_exists_with_three_sections(self):
        text = PREAMBLE.read_text(encoding="utf-8")
        for h in ("## §1", "## §2", "## §3"):
            self.assertIn(h, text)
        for needle in ("workspace.json", "Run `/campus-start` first", "CAMPUS FOLDER", "session scratchpad",
                       "This starter employee covers the essentials", ".campus-os/context-files.md"):
            self.assertIn(needle, text, needle)

    def test_no_paragraph_shared_by_three_or_more_skills(self):
        seen = {}
        for f in self.skills():
            for p in paragraphs(f):
                if len(p.split()) >= 8 and not p.startswith("#"):
                    seen.setdefault(p, set()).add(f.parent.name)
        shared = {p: s for p, s in seen.items() if len(s) >= 3}
        self.assertEqual(shared, {}, "pasted block(s) shared by 3+ skills: " +
                         "; ".join(f"{sorted(s)} -> {p[:80]}" for p, s in shared.items()))

    def test_old_blocks_are_gone_and_pointers_are_short(self):
        pointers = 0
        for f in self.skills():
            for p in paragraphs(f):
                for s in OLD_STARTS:
                    self.assertFalse(p.startswith(s), f"{f.parent.name} still carries the pasted block: {s}")
                if p.startswith("Kernel preamble"):
                    self.assertRegex(p, POINTER, f"{f.parent.name}: malformed pointer")
                    self.assertLessEqual(len(p.split()), 7, "pointer must stay under the shingle width")
                    pointers += 1
        self.assertGreaterEqual(pointers, 20, "expected the pointers in the 21 skills that carried the blocks")

    def test_pointer_target_ships(self):
        self.assertTrue(PREAMBLE.is_file())
        # package.py ships everything under the tree except EXCLUDE_DIRS; references/ is not excluded
        pkg = (KERNEL / "tools" / "package.py").read_text(encoding="utf-8")
        self.assertNotIn('"references"', pkg.split("EXCLUDE_DIRS")[1].split("\n")[0])


if __name__ == "__main__":
    unittest.main()
