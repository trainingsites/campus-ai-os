"""5.3.2: a pack build ships no command or roster that points at a skill it dropped.
Found on the first coach build: /plan-lesson survived without lesson-planner, and the coach registry kept
the education rosters (student-comms, class-manager, lesson-planner) as owner additions."""
import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path

KERNEL = Path(os.environ.get('KERNEL_SRC', Path(__file__).resolve().parent.parent)).resolve()


@unittest.skipUnless((KERNEL / 'packs/coach/pack.json').is_file(), 'coach pack not in this tree')
class CoachBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='coach532-')
        cls.out = Path(cls.tmp.name) / 'coach'
        cls.p = subprocess.run([sys.executable, '-I', '-B', str(KERNEL / 'tools/build_niche.py'), '--pack', 'coach',
                                '--assemble', str(cls.out)], cwd=KERNEL, capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_assembles(self):
        self.assertEqual(self.p.returncode, 0, self.p.stdout + self.p.stderr)
        self.assertEqual(json.loads((self.out / 'packs/active.json').read_text())['active_pack'], 'coach')

    def test_no_command_or_roster_points_at_a_missing_skill(self):
        shipped = {p.name for p in (self.out / 'skills').iterdir() if (p / 'SKILL.md').is_file()}
        for gone in ('student-comms', 'class-manager', 'lesson-planner'):
            self.assertNotIn(gone, shipped)
            for cmd in (self.out / 'commands').glob('*.md'):
                self.assertNotIn(f'`{gone}`', cmd.read_text(), cmd.name)
        self.assertFalse((self.out / 'commands/plan-lesson.md').exists())
        reg = json.loads((self.out / 'templates/registry.json').read_text())
        for team in reg['teams']:
            if team.get('type') == 'department':
                for n in (team.get('employees') or []) + (team.get('employees_added') or []):
                    self.assertIn(n, shipped, f"{team.get('label')}: {n}")

    def test_listing_names_the_coaching_practice(self):
        for rel in ('.claude-plugin/plugin.json', '.codex-plugin/plugin.json'):
            text = (self.out / rel).read_text()
            self.assertNotIn('education', text.lower(), rel)
            self.assertIn('coaching practice', text, rel)

    def test_the_build_passes_its_own_gate(self):
        p = subprocess.run([sys.executable, '-I', '-B', str(self.out / 'tools/build_niche.py'), '--check'],
                           cwd=self.out, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)


if __name__ == '__main__':
    unittest.main()
