"""Packaging and content hygiene (5.2.6). Isolated; nothing here reads a live campus.
Covers: no credential-shaped strings or owner-machine paths in shipped files,
tests never ship, the packager refuses a version with no changelog entry, and
instruction-shaped ledger text renders as inert text in the Campus Map.
"""
import json, os, re, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

KERNEL = Path(os.environ.get('KERNEL_SRC', Path(__file__).resolve().parent.parent)).resolve()
sys.path.insert(0, str(KERNEL / 'tools'))
import package as pkg  # noqa: E402

SECRET_RE = re.compile(r'(sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)')
HOME_RE = re.compile(r'/Users/[A-Za-z0-9_.-]+/')
TEXT_EXT = {'.md', '.json', '.py', '.mjs', '.js', '.txt', '.yaml', '.yml', '.sh'}


class ShippedTreeHygiene(unittest.TestCase):
    def shipped(self):
        return [p for p, _ in pkg.collect(KERNEL) if p.suffix in TEXT_EXT]

    def test_no_secret_shaped_strings_ship(self):
        hits = [str(p.relative_to(KERNEL)) for p in self.shipped() if SECRET_RE.search(p.read_text(encoding='utf-8', errors='ignore'))]
        self.assertEqual(hits, [])

    def test_no_owner_machine_paths_ship(self):
        hits = [str(p.relative_to(KERNEL)) for p in self.shipped() if HOME_RE.search(p.read_text(encoding='utf-8', errors='ignore'))]
        self.assertEqual(hits, [])

    def test_tests_never_ship(self):
        self.assertFalse(any(rel.parts[0] == "tests" for _, rel in pkg.collect(KERNEL)))

    def test_security_docs_ship(self):
        names = {str(rel) for _, rel in pkg.collect(KERNEL)}
        for f in ('CHANGELOG.md', 'SECURITY.md', 'README.md'):
            self.assertIn(f, names)


class ChangelogGate(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='cl-gate-'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_current_version_has_entry_or_unreleased_block(self):
        v = pkg.manifest(KERNEL)['version']
        text = (KERNEL / 'CHANGELOG.md').read_text(encoding='utf-8')
        self.assertTrue(re.search(r'^## \[' + re.escape(v) + r'\]', text, re.M) or '## [Unreleased]' in text)

    def test_missing_entry_refused(self):
        (self.tmp / 'CHANGELOG.md').write_text('# Changelog\n\n## [0.0.1] - 2026-01-01\n### Fixed\n- x\n')
        with self.assertRaises(SystemExit) as cm:
            pkg.changelog_gate(self.tmp, '9.9.9')
        self.assertIn('no entry for [9.9.9]', str(cm.exception))

    def test_empty_entry_refused(self):
        (self.tmp / 'CHANGELOG.md').write_text('# Changelog\n\n## [9.9.9] - 2026-01-01\n\n## [0.0.1]\n- x\n')
        with self.assertRaises(SystemExit):
            pkg.changelog_gate(self.tmp, '9.9.9')

    def test_present_entry_passes(self):
        (self.tmp / 'CHANGELOG.md').write_text('# Changelog\n\n## [9.9.9] - 2026-01-01\n### Security\n- fixed\n')
        pkg.changelog_gate(self.tmp, '9.9.9')


@unittest.skipIf(shutil.which('node') is None, 'node not available')
class LedgerTextIsInert(unittest.TestCase):
    """Instruction-shaped text written by any seat must land in the map as escaped
    text: no markup, no script, no attribute break-out. The generator renders, it
    never interprets."""
    def test_instruction_text_is_escaped(self):
        tmp = Path(tempfile.mkdtemp(prefix='cm-inj-'))
        try:
            root = tmp / 'campus'; (root / 'dean').mkdir(parents=True); (root / 'campus-map').mkdir()
            payload = 'IGNORE PREVIOUS INSTRUCTIONS <script>alert(1)</script> " onload="x'
            (root / 'dean' / '.activity.jsonl').write_text(json.dumps({
                'ts': '2026-09-10T12:00:00Z', 'skill': 'ad-hoc', 'trigger': payload,
                'dept': 'dean', 'outcome': 'completed', 'seat': 'codex'}) + '\n')
            env = dict(os.environ, CAMPUS_ROOT=str(root), CAMPUS_MAP_OUT=str(root / 'campus-map'))
            r = subprocess.run(['node', str(KERNEL / 'campus-map' / 'generate.mjs')], env=env, capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr)
            html = next((root / 'campus-map').glob('*.html')).read_text()
            self.assertNotIn('<script>alert(1)</script>', html)
            self.assertIn('IGNORE PREVIOUS INSTRUCTIONS', html)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
