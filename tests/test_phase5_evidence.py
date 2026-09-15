"""Phase 5.2 read-only evidence and deterministic fixture proof.
platform: codex; seat: codex
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

KERNEL = Path(os.environ.get('KERNEL_SRC', Path(__file__).resolve().parent.parent)).resolve()
ORDER = ('workspace', 'version_lockstep', 'registry', 'context_weight', 'results_ledgers',
         'schedules', 'seat_contract', 'fleet_sweep', 'staff', 'stale_work', 'ledger')


class EvidenceFixture(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='phase5-evidence-')
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.kernel = self.base / 'kernel'
        shutil.copytree(KERNEL, self.kernel, ignore=shutil.ignore_patterns('tests', '__pycache__', '.git'))
        self.root = self.base / 'campus'
        for rel in ('.campus-os', 'dean', 'active-work', 'scheduled'):
            (self.root / rel).mkdir(parents=True, exist_ok=True)
        self.env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', CAMPUS_ROOT=str(self.root))
        self.env.pop('CAMPUS_CONTRACT', None)
        template = json.loads((self.kernel / 'templates/registry.json').read_text())
        self.write('workspace.json', {'version': template['campus_os_version'], 'startup_reads': ['AGENTS.md']})
        (self.root / 'AGENTS.md').write_text('Read dean/AGENTS.md.\n')
        shutil.copy2(self.kernel / 'templates/dean-CLAUDE.md', self.root / 'dean/AGENTS.md')
        template['teams'] += [dict(team=name, type='plugin', version='1.0.0', status='active', department='dean',
                                   owns='Fixture', triggers=['fixture'], done_check='done',
                                   results='outputs/{YYYY-MM}/runs/' + name + '/{slug}/results.json', permission='draft-only')
                              for name in ('fixture-one', 'fixture-two')]
        self.write('.campus-os/registry.json', template)
        self.write('.campus-os/seat.json', {'seat': 'fixture-owner', 'role': 'primary'})
        p = subprocess.run([sys.executable, str(self.kernel / 'tools/materialize_registration_spec.py'),
                            '--campus-root', str(self.root)], env=self.env, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.write('outputs/legacy/results.json', {'schema_version': '1.0', 'run_id': 'legacy', 'assets': []})
        self.write('outputs/current/results.json', {'schema_version': '1.1', 'run_id': 'fixture-20260908-120000000',
                   'team': 'fixture-one', 'generated_at': '2026-09-08T12:00:00Z', 'assets': [],
                   'completion': {'execution_success': True, 'artifact_passed': True, 'owner_approved': False}})
        (self.root / 'dean/.activity.jsonl').write_text(json.dumps({'ts': '2026-09-07T12:00:00Z', 'seat': 'fixture-owner'}) + '\n')
        (self.root / 'dean/.activity.fixture.jsonl').write_text(json.dumps({'ts': '2026-09-08T12:00:00Z'}) + '\n')
        old = self.root / 'active-work/old.md'
        old.write_text('Old draft\n')
        os.utime(old, (1700000000, 1700000000))

    def write(self, rel, data):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))

    def run_evidence(self, *args, json_output=True, stdin='', env=None):
        return subprocess.run([sys.executable, str(self.kernel / 'tools/doctor_evidence.py'),
                               '--campus-root', str(self.root), '--today', '2026-09-08',
                               *(['--json'] if json_output else []), *args],
                              env=env or self.env, input=stdin, text=True, capture_output=True, timeout=30)

    def test_byte_stable_all_sections_read_only_and_counts(self):
        def snapshot():
            return {str(p.relative_to(self.base)): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
                    for p in self.base.rglob('*') if p.is_file()}
        before = snapshot()
        first, second = self.run_evidence(), self.run_evidence()
        self.assertEqual(first.returncode, 1, first.stdout + first.stderr)   # 1: fixture campus is red by design (unstamped shard line); SKILL exit contract
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(before, snapshot())
        data = json.loads(first.stdout)
        self.assertEqual(set(data), {'generated', *ORDER})
        self.assertEqual(data['generated'], {'today': '2026-09-08'})
        self.assertEqual(first.stdout, json.dumps(data, sort_keys=True, indent=2) + '\n')
        for name in ORDER:
            self.assertEqual(set(data[name]), {'status', 'detail', 'line'})
        for name in ('workspace', 'version_lockstep', 'registry', 'results_ledgers', 'staff'):
            self.assertEqual(data[name]['status'], 'ok', data[name])
        self.assertEqual(data['results_ledgers']['detail']['counts'], {'legacy-1.0': 1, 'v1.1-valid': 1})
        self.assertNotIn('rows', data['results_ledgers']['detail'])
        staff = data['staff']['detail']
        dean = next(d for d in staff['departments'] if d['department'] == 'dean-office')
        self.assertTrue({'fixture-one', 'fixture-two'} <= set(dean['employees']))
        self.assertEqual(staff['employees'], sum(d['count'] for d in staff['departments']))
        self.assertEqual(data['stale_work']['detail']['count'], 1)
        self.assertEqual(data['ledger']['detail']['unstamped_lines'], 1)
        self.assertEqual(data['ledger']['detail']['newest_ts'], '2026-09-08T12:00:00+00:00')
        human = self.run_evidence(json_output=False)
        self.assertEqual(human.stdout, ''.join(data[name]['line'] + '\n' for name in ORDER))

    def test_founded_ledger_header_comments_are_not_errors(self):
        # campus-start writes two '# ...' header lines before the first JSON entry
        # (found on the 5.2.1 cold install: the doctor flagged a fresh diary as broken).
        (self.root / 'dean/.activity.jsonl').write_text(
            '# Campus activity ledger - one JSON line per completed workflow. Append-only.\n'
            '# On read: skip lines starting with #. Never overwrite or rewrite prior lines.\n'
            + json.dumps({'ts': '2026-09-08T12:00:00Z', 'seat': 'fixture-owner', 'skill': 'campus-start'}) + '\n')
        data = json.loads(self.run_evidence().stdout)['ledger']
        self.assertNotEqual(data['status'], 'error', data)
        self.assertEqual(data['detail']['errors'], [])
        self.assertEqual(data['detail']['lines'], 2)  # the primary entry + the shard entry, headers uncounted

    def test_node_absent_skipped(self):
        p = self.run_evidence(env=dict(self.env, PATH=''))
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)   # 1: fixture campus is red by design (unstamped shard line); SKILL exit contract
        self.assertEqual(json.loads(p.stdout)['context_weight']['status'], 'skipped')

    def test_broken_registry_isolated_with_stderr(self):
        (self.root / '.campus-os/registry.json').write_text('{broken')
        p = self.run_evidence()
        self.assertEqual(p.returncode, 1)
        data = json.loads(p.stdout)
        self.assertEqual(data['registry']['status'], 'error')
        self.assertTrue(data['registry']['detail']['errors'][0]['stderr_tail'])
        self.assertEqual(set(data), {'generated', *ORDER})
        self.assertEqual(data['results_ledgers']['status'], 'ok')

    def test_scheduler_input_file_stdin_and_fixed_health_clock(self):
        live = json.dumps({'tasks': [{'id': 'daily', 'enabled': True, 'cronExpression': '0 12 * * *',
                                    'lastRunAt': '2026-09-07T12:00:00Z'}]})
        (self.root / 'live.json').write_text(live)
        first = self.run_evidence('--scheduled-json', '-', stdin=live)
        second = self.run_evidence('--scheduled-json', 'live.json')
        self.assertEqual(first.stdout, second.stdout)
        data = json.loads(first.stdout)['schedules']
        self.assertNotEqual(data['status'], 'error', data)
        self.assertEqual(data['detail']['health']['stalled'], [])
        invalid = json.loads(self.run_evidence('--scheduled-json', '-', stdin='{broken').stdout)
        self.assertEqual(invalid['schedules']['status'], 'error')
        self.assertIn('stderr_tail', invalid['schedules']['detail'])
        self.assertEqual(invalid['workspace']['status'], 'ok')

    def test_open_silent_stdin_without_flag_completes_and_skips_schedules(self):
        # Keep stdin open through wait(); communicate() would close it and hide D1.
        # Files avoid a full stdout pipe becoming an unrelated cause of blocking.
        with tempfile.TemporaryFile(mode='w+') as out, tempfile.TemporaryFile(mode='w+') as err:
            process = subprocess.Popen(
                [sys.executable, str(self.kernel / 'tools/doctor_evidence.py'),
                 '--campus-root', str(self.root), '--today', '2026-09-08', '--json'],
                env=self.env, stdin=subprocess.PIPE, stdout=out, stderr=err, text=True)
            try:
                process.wait(timeout=10)
                self.assertFalse(process.stdin.closed)
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)
                process.stdin.close()
            out.seek(0)
            err.seek(0)
            output, errors = out.read(), err.read()
        self.assertEqual(process.returncode, 1, output + errors)   # 1: fixture campus is red by design (unstamped shard line); SKILL exit contract
        self.assertEqual(json.loads(output)['schedules']['status'], 'skipped')

    def test_monthly_sweep_and_explicit_override(self):
        foundry = self.root / 'library/teams/_foundry/bin'
        foundry.mkdir(parents=True)
        (foundry.parent.parent / 'demo').mkdir()
        # Stub only the Foundry process boundary; verify no distribution profile.
        (foundry / 'validate-team').write_text('import sys,json\nassert "--profile" not in sys.argv\n'
                                             'print(json.dumps({"pass":True,"fails":[],"warns":[]}))\n')
        self.assertEqual(json.loads(self.run_evidence().stdout)['fleet_sweep']['status'], 'skipped')
        for args in [('--sweep',), ('--today', '2026-09-02')]:
            data = json.loads(self.run_evidence(*args).stdout)['fleet_sweep']
            self.assertEqual(data['status'], 'ok', data)
            self.assertEqual([t['team'] for t in data['detail']['teams']], ['demo'])


if __name__ == '__main__':
    unittest.main()



# 5.2.4 cold-install findings (Cowork, 2026-09-09): a fresh campus with no seat.json must not open on a red
# line, and the exit code must follow the SKILL contract (1 = some line is red). Attached to EvidenceFixture so
# the shared setUp is reused without discovery running the inherited tests twice.
def _run_json(self):
    p = self.run_evidence('--today', '2026-09-08')
    return p.returncode, json.loads(p.stdout)

def test_missing_seat_is_opportunity_not_red(self):
    (self.root / '.campus-os/seat.json').unlink()
    (self.root / 'dean/.activity.fixture.jsonl').unlink()          # the shard's unstamped line is a real finding; remove it
    rc, out = _run_json(self)
    self.assertEqual(out['seat_contract']['status'], 'opportunity', out['seat_contract']['line'])
    self.assertTrue(out['seat_contract']['line'].startswith('[--]'))

def test_exit_one_when_a_line_is_red(self):
    rc, out = _run_json(self)                                       # fixture shard carries an unstamped line -> red
    self.assertEqual(out['seat_contract']['status'], 'needs-decision')
    self.assertEqual(rc, 1)

def test_exit_zero_when_nothing_is_red(self):
    (self.root / 'dean/.activity.fixture.jsonl').unlink()
    rc, out = _run_json(self)
    reds = [n for n, v in out.items() if isinstance(v, dict) and v.get('status') in ('needs-decision', 'error')]
    self.assertEqual(reds, [], reds); self.assertEqual(rc, 0)

EvidenceFixture.test_missing_seat_is_opportunity_not_red = test_missing_seat_is_opportunity_not_red
EvidenceFixture.test_exit_one_when_a_line_is_red = test_exit_one_when_a_line_is_red
EvidenceFixture.test_exit_zero_when_nothing_is_red = test_exit_zero_when_nothing_is_red
