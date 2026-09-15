"""Phase 5.3 check dispatch and diagnostic isolation.
platform: codex; seat: codex
"""
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

KERNEL = Path(os.environ.get('KERNEL_SRC', Path(__file__).resolve().parent.parent)).resolve()
# Recorded from the conformant Phase 5 M4 source before the split.
GOLDEN = b"OK: pack 'education' conformant\n"


class NicheChecks(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='phase5-niche-')
        self.addCleanup(tmp.cleanup)
        self.kernel = Path(tmp.name) / 'kernel'
        shutil.copytree(KERNEL, self.kernel, ignore=shutil.ignore_patterns('tests', '__pycache__', '.git'))
        self.env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        self.tool = self.kernel / 'tools/build_niche.py'

    def cli(self, *args):
        return subprocess.run([sys.executable, str(self.tool), *args], env=self.env,
                              capture_output=True, timeout=30)

    def test_conformant_stdout_matches_pre_split_golden(self):
        p = self.cli('--check')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(p.stdout, GOLDEN)

    def test_enum_mutation_has_only_its_own_code(self):
        # Check 20b owns the DEPARTMENT enum. Type/status were never checked
        # here; changing that scope would add a check, which this split forbids.
        spec = self.kernel / 'templates/registration-block-spec.md'
        before = spec.read_text()
        after, n = re.subn(r'^\s*"department":.*\n', '', before, count=1, flags=re.M)
        self.assertEqual(n, 1)
        spec.write_text(after)
        p = self.cli('--check')
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        failures = [line for line in p.stdout.decode().splitlines() if line.startswith('FAIL:')]
        self.assertEqual(failures, ['FAIL: NICHE-020B: registration-block-spec.md has no `department` enum line - check 20b is not actually running'])
        self.assertEqual(self.cli('--only', 'NICHE-020B').stdout, p.stdout)
        self.assertEqual(self.cli('--only', 'NICHE-001').stdout, GOLDEN)

    def test_list_matches_registry_and_every_check_runs_alone(self):
        spec = importlib.util.spec_from_file_location('phase5_build_niche', self.tool)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        rows = module.CHECKS
        self.assertEqual(len({r[0] for r in rows}), len(rows))
        self.assertEqual(len({r[2] for r in rows}), len(rows))
        p = self.cli('--list')
        self.assertEqual(p.returncode, 0)
        self.assertEqual(p.stdout.decode().splitlines(), [f'{code} {title}' for code, title, fn in rows])
        for code, title, fn in rows:
            with self.subTest(code=code):
                p = self.cli('--only', code)
                self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
                self.assertEqual(p.stdout, GOLDEN)

    def test_only_filters_multiple_independent_failures(self):
        pack = self.kernel / 'packs/education/pack.json'
        data = json.loads(pack.read_text())
        del data['label']
        pack.write_text(json.dumps(data))
        # Check 8b independently detects this missing scaffold.
        start = self.kernel / 'skills/campus-start/SKILL.md'
        start.write_text(start.read_text().replace('atlas/config/', 'atlas/old/'))
        for codes in [('NICHE-001',), ('NICHE-008B',), ('NICHE-001', 'NICHE-008B')]:
            p = self.cli('--only', ','.join(codes))
            self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
            found = re.findall(r'^FAIL: (NICHE-[0-9A-Z]+):', p.stdout.decode(), re.M)
            self.assertEqual(set(found), set(codes))
        self.assertEqual(self.cli('--only', 'NICHE-020B').stdout, GOLDEN)

    def test_invalid_selection_refused_and_assembly_cannot_bypass_gate(self):
        self.assertEqual(self.cli('--only', 'NICHE-999').returncode, 2)
        self.assertEqual(self.cli('--only', '').returncode, 2)
        self.assertEqual(self.cli('--only', 'NICHE-001', '--assemble', str(self.kernel.parent / 'out')).returncode, 2)


if __name__ == '__main__':
    unittest.main()
