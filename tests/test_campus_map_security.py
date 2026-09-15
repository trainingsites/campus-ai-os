"""Campus Map generator hardening (5.2.6). Isolated fixtures; nothing here reads a live campus.
Covers: ledger path traversal out of the campus root, symlink escape, and stored
XSS through markdown link targets rendered into the inline document viewer.
"""
import json, os, shutil, subprocess, tempfile, unittest
from pathlib import Path

KERNEL = Path(os.environ.get('KERNEL_SRC', Path(__file__).resolve().parent.parent)).resolve()
GEN = KERNEL / 'campus-map' / 'generate.mjs'
CANARY = 'CANARY-OUTSIDE-CAMPUS-ROOT'


def ledger_line(output, trigger):
    return json.dumps({'ts': '2026-09-10T12:00:00Z', 'session': 'audit', 'skill': 'ad-hoc',
                       'trigger': trigger, 'dept': 'dean', 'outcome': 'completed',
                       'output': output, 'seat': 'codex'})


@unittest.skipIf(shutil.which('node') is None, 'node not available')
class CampusMapSecurity(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='cm-sec-'))
        self.root = self.tmp / 'campus'
        (self.root / 'dean').mkdir(parents=True)
        (self.root / 'outputs').mkdir()
        (self.root / 'campus-map').mkdir()
        (self.tmp / 'secret.txt').write_text(CANARY + '\n')
        (self.root / 'outputs' / 'xss.md').write_text(
            '# Safe test fixture\n\n'
            '[hover test](x" onmouseover="location=\'https://example.com\')\n'
            '[js](javascript:alert(1))\n'
            '[ok](https://example.com/page)\n'
            '[rel](outputs/other.md)\n')
        os.symlink(self.tmp / 'secret.txt', self.root / 'outputs' / 'link.txt')
        (self.root / 'dean' / '.activity.jsonl').write_text('\n'.join([
            ledger_line('outputs/../../secret.txt', 'path traversal'),
            ledger_line('outputs/link.txt', 'symlink escape'),
            ledger_line('outputs\\..\\..\\secret.txt', 'backslash traversal'),
            ledger_line('/etc/hosts', 'absolute path'),
            ledger_line('outputs/xss.md', 'stored xss'),
        ]) + '\n')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def build(self, public=False):
        env = dict(os.environ, CAMPUS_ROOT=str(self.root), CAMPUS_MAP_OUT=str(self.root / 'campus-map'))
        args = ['node', str(GEN)] + (['--public'] if public else [])
        r = subprocess.run(args, env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        htmls = list((self.root / 'campus-map').glob('*.html'))
        self.assertEqual(len(htmls), 1, htmls)
        return htmls[0].read_text()

    def test_no_file_outside_root_is_embedded(self):
        html = self.build()
        self.assertNotIn(CANARY, html)
        self.assertNotIn('secret.txt', html)
        self.assertNotIn('/etc/hosts', html)

    def test_markdown_links_are_sanitized(self):
        html = self.build()
        self.assertNotIn('onmouseover', html)
        self.assertNotIn('javascript:', html)
        self.assertIn('https://example.com/page', html)
        self.assertIn('href=\\"outputs/other.md\\"', html)
        self.assertIn('hover test', html)  # text survives, the link does not

    def test_public_flag_is_refused(self):
        env = dict(os.environ, CAMPUS_ROOT=str(self.root), CAMPUS_MAP_OUT=str(self.root / 'campus-map'))
        r = subprocess.run(['node', str(GEN), '--public'], env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 2)
        self.assertIn('retired', r.stderr)
        self.assertEqual(list((self.root / 'campus-map').glob('*.html')), [])


if __name__ == '__main__':
    unittest.main()


@unittest.skipIf(shutil.which('node') is None, 'node not available')
class PrivateOnlyAndBrandSinks(unittest.TestCase):
    """5.2.8: the map is private-only - no public output can be produced at all;
    brand, orchestrator, and ledger fields cannot become markup (SEC-03); offline
    builds make no network request (SEC-07); every build carries a CSP."""
    C = 'CONFIDENTIAL-CANARY-ACME-7741'

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='cm-pub-'))
        r = self.root = self.tmp / 'campus'
        for d in ('dean', 'outputs/2026-09/briefs', 'outputs/2026-09/reports', 'wiki/concepts', 'shared', 'about-me', 'campus-map', 'scheduled'):
            (r / d).mkdir(parents=True)
        C = self.C
        (r / 'dean' / '.activity.jsonl').write_text(json.dumps({
            'ts': '2026-09-10T12:00:00Z', 'skill': 'ad-hoc', 'trigger': 'private client result ' + C + '-LEDGER',
            'dept': 'dean', 'outcome': 'completed', 'output': 'outputs/2026-09/reports/r.md', 'seat': 'codex'}) + '\n')
        (r / 'outputs/2026-09/reports/r.md').write_text('# report ' + C + '-DOC\n')
        (r / 'outputs/2026-09/briefs/2026-09-10-b.md').write_text('# ' + C + '-BRIEF\n')
        (r / 'outputs/2026-09/reports/reporting-rollup.json').write_text(json.dumps({
            'generated': '2026-09-10', 'results': [{'slug': C + '-RESULT', 'score': 1, 'assets': 1, 'signal': 'more'}]}))
        (r / 'wiki/concepts/w.md').write_text('---\ntitle: "' + C + '-WIKI"\n---\nx\n')
        (r / 'wiki/log.md').write_text('- 2026-09-10 ' + C + '-LEARNED\n')
        (r / 'shared/goals.md').write_text('# goals\n\n## OKRs\n- O1: ' + C + '-OKR\n\n## Focus\n- ' + C + '-FOCUS\n')
        (r / 'scheduled' / (C.lower() + '-sched.md')).write_text('cronExpression: 0 0 * * *\n')
        (r / 'shared/brand-style.md').write_text(
            'brand_name: "</title><script>window.__CAMPUS_MAP_BRAND_XSS__=1</script><title>"\n'
            'tagline: "x<img src=x onerror=alert(1)>"\n'
            'font_heading: "Comfortaa;} body{background:url(javascript:1)}"\n'
            'font_body: "Roboto\'</style><script>alert(3)</script>"\n'
            'font_import: "https://evil.example/x.css"\n')
        (r / 'about-me/dean-name.md').write_text('name: "<svg onload=alert(2)>"\n')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def build(self, *flags):
        env = dict(os.environ, CAMPUS_ROOT=str(self.root), CAMPUS_MAP_OUT=str(self.root / 'campus-map'))
        r = subprocess.run(['node', str(GEN), *flags], env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return (self.root / 'campus-map' / 'campus-map.html').read_text()

    def test_no_public_output_can_be_produced(self):
        env = dict(os.environ, CAMPUS_ROOT=str(self.root), CAMPUS_MAP_OUT=str(self.root / 'campus-map'))
        for extra in ({'PUBLIC': '1'}, {}):
            args = ['node', str(GEN)] + ([] if extra else ['--public'])
            r = subprocess.run(args, env=dict(env, **extra), capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 2, r.stderr)
        self.assertEqual(list((self.root / 'campus-map').glob('*public*')), [])

    def test_brand_and_orchestrator_fields_are_inert(self):
        for flags in ((), ('--no-remote-fonts',)):
            html = self.build(*flags)
            self.assertNotIn('__CAMPUS_MAP_BRAND_XSS__=1</script>', html)
            self.assertNotIn('<img src=x onerror', html)
            self.assertNotIn('<svg onload', html)
            self.assertNotIn('url(javascript', html)
            self.assertNotIn('</style><script>alert(3)', html)
            self.assertNotIn('evil.example', html)
            self.assertIn('&lt;/title&gt;', html)

    def test_offline_build_makes_no_network_request_and_every_build_has_csp(self):
        priv = self.build(); off = self.build('--no-remote-fonts')
        self.assertNotIn('fonts.googleapis', off)
        self.assertNotIn('fonts.gstatic', off)
        self.assertIn('fonts.googleapis', priv)
        for h in (priv, off):
            self.assertIn('Content-Security-Policy', h)
            self.assertRegex(h, r"script-src 'sha256-[A-Za-z0-9+/=]+'")
