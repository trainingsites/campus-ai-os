"""5.3.4 Windows field report: isolated-mode preflight and byte-order marks on text input.
platform: claude-code; seat: m4-claude-code
"""
import json
import os
import stat
import subprocess
import sys
import unittest

from test_phase5_evidence import EvidenceFixture, ORDER

BOM = b'\xef\xbb\xbf'
# Sections that run an isolated Python sub-tool on the fixture campus.
DRIVER = '''
import sys
sys.path.insert(0, sys.argv[1])
import doctor_evidence as d
d.sys.executable = sys.argv[2]   # the interpreter the doctor believes it runs on
raise SystemExit(d.main(sys.argv[3:]))
'''


class WindowsField534(EvidenceFixture):
    def run_bytes(self, *argv, stdin=b''):
        return subprocess.run([sys.executable, '-I', '-B', *map(str, argv)], cwd=self.root, env=self.env,
                              input=stdin, capture_output=True, timeout=60)

    def evidence(self, *args, stdin=b''):
        return self.run_bytes(self.kernel / 'tools/doctor_evidence.py', '--campus-root', self.root,
                              '--today', '2026-09-08', '--json', *args, stdin=stdin)

    def manifest(self):
        return (self.kernel / 'tools/kit-manifest.json').read_bytes()

    # --- byte-order mark -------------------------------------------------------------------

    def test_kit_manifest_on_stdin_accepts_a_byte_order_mark(self):
        plain = self.evidence('--kit-manifest', '-', stdin=self.manifest())
        marked = self.evidence('--kit-manifest', '-', stdin=BOM + self.manifest())
        self.assertNotIn(b'unreadable', marked.stderr)
        self.assertNotEqual(marked.returncode, 2, marked.stderr)
        self.assertEqual((marked.returncode, marked.stdout), (plain.returncode, plain.stdout))

    def test_kit_manifest_file_accepts_a_byte_order_mark(self):
        path = self.base / 'manifest-with-mark.json'
        path.write_bytes(BOM + self.manifest())
        plain = self.evidence('--kit-manifest', self.kernel / 'tools/kit-manifest.json')
        marked = self.evidence('--kit-manifest', path)
        self.assertEqual((marked.returncode, marked.stdout), (plain.returncode, plain.stdout))

    def test_schedule_list_on_stdin_accepts_a_byte_order_mark(self):
        live = json.dumps({'tasks': []}).encode()
        plain = self.evidence('--scheduled-json', '-', stdin=live)
        marked = self.evidence('--scheduled-json', '-', stdin=BOM + live)
        self.assertEqual((marked.returncode, marked.stdout), (plain.returncode, plain.stdout))
        self.assertNotIn(b'BOM', marked.stdout)

    def test_kit_check_and_cron_parity_accept_a_byte_order_mark(self):
        kit = [self.kernel / 'tools/kernel_kit.py', 'check', '--campus-root', self.root, '--json', '--manifest', '-']
        plain, marked = self.run_bytes(*kit, stdin=self.manifest()), self.run_bytes(*kit, stdin=BOM + self.manifest())
        self.assertEqual((marked.returncode, marked.stdout), (plain.returncode, plain.stdout))
        self.assertNotIn(b'BOM', marked.stdout + marked.stderr)
        cron = [self.kernel / 'tools/check_cron_parity.py', '--scheduled', self.root / 'scheduled', '--json']
        live = json.dumps({'tasks': []}).encode()
        plain, marked = self.run_bytes(*cron, stdin=live), self.run_bytes(*cron, stdin=BOM + live)
        self.assertEqual((marked.returncode, marked.stdout), (plain.returncode, plain.stdout))
        self.assertNotIn(b'BOM', marked.stdout + marked.stderr)

    # --- isolated-mode preflight -----------------------------------------------------------

    def test_healthy_python_reports_no_preflight(self):
        data = json.loads(self.evidence().stdout)
        self.assertEqual(set(data), {'generated', *ORDER})

    @unittest.skipIf(os.name == 'nt', 'the stand-in interpreter is a shell script')
    def test_python_that_cannot_start_isolated_is_one_clear_line(self):
        fake = self.base / 'broken-python'
        fake.write_text('#!/bin/sh\necho "Fatal Python error: Failed to import encodings module" >&2\nexit 1\n')
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
        base = [sys.executable, '-c', DRIVER, str(self.kernel / 'tools'), str(fake),
                '--campus-root', str(self.root), '--today', '2026-09-08']
        run = lambda *extra: subprocess.run([*base, *extra], cwd=self.root, env=self.env, text=True,
                                            capture_output=True, timeout=60)
        p = run('--json')
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        data = json.loads(p.stdout)
        self.assertEqual(set(data), {'generated', 'preflight', *ORDER})
        pre = data['preflight']
        self.assertEqual(pre['status'], 'error')
        self.assertIn('cannot start in isolated mode', pre['line'])
        self.assertIn('not your campus', pre['line'])
        self.assertIn('Failed to import encodings', pre['detail']['stderr_tail'])
        # the three sections the field report saw red are now "not checked", and nothing else is hidden
        for name in ('registry', 'results_ledgers', 'seat_contract'):
            self.assertIn(name, pre['detail']['blocked'])
        for name in ORDER:
            blocked = name in pre['detail']['blocked']
            self.assertEqual(data[name]['status'] == 'skipped'
                             and data[name]['detail'].get('reason') == 'python-isolated-unavailable', blocked, name)
            if blocked:
                self.assertNotIn('encodings', json.dumps(data[name]))
        self.assertEqual(sum('encodings' in json.dumps(v) for v in data.values()), 1)
        human = run()
        lines = human.stdout.splitlines()
        self.assertEqual(lines[0], pre['line'])
        self.assertEqual(lines[1:], [data[name]['line'] for name in ORDER])


del EvidenceFixture  # its own tests are collected once, from its own module


if __name__ == '__main__':
    unittest.main()
