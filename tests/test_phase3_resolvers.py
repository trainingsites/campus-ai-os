"""Phase 3.7 resolver API/CLI parity, isolated copies; no live campus reads.
platform: codex; seat: codex
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

KERNEL = Path(os.environ.get('KERNEL_SRC', Path(__file__).resolve().parent.parent)).resolve()
NODE = shutil.which('node')
SAMPLES = [
    'campus-ambassador-20260901-113914', 'email-desk-20260902-113811',
    'crm1to1activity-20260907T060741Z', '2026-09-06T1209Z',
    '20260906T040745Z', '20260905-crm-1to1-activity-0106',
    'canonical-demo-20260907-194512345-a1b2', 'owner-made-run',
    'unicode-é-😀-20260907-194512345', 'bad-20260230-120000000',
    'odd-20260907-120099000', 'odd-20260907-240000000',
    'bad-20260907-120060000', 'year-00010101-000000000',
    'year-２０２６0907-120000000', 'math-20260907T𝟎𝟏𝟎𝟔Z', 'line\rbreak-20260907-120000000',
    'line\u2028break-20260907-120000000', 'bad-20260907-120000000\n', '',
]
CANONICAL = 'canonical-demo-20260907-194512345-a1b2'


def load_module(path):
    spec = importlib.util.spec_from_file_location('phase3_contract_resolver', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cases(c):
    rows = []
    files = c['context_aliases']['files']
    for f in files:
        for name in [f['canonical'], *f['aliases'], f['canonical'].swapcase(), f['concept']]:
            rows.append(('resolve_context', [name]))
    rows.extend([('resolve_context', ['icp']), ('resolve_context', ['not-a-context'])])
    for value in [*c['registry_enums']['enums']['department'], 'dean', 'DEAN', 'not-a-department']:
        rows.append(('resolve_department', [value]))
    for kind in ['type', 'status']:
        for value in [*c['registry_enums']['enums'][kind],
                      *[v.upper() for v in c['registry_enums']['enums'][kind]], 'unknown', '__proto__']:
            rows.append(('normalize_' + kind, [value]))
    for value in [*c['hosts']['clients'], *c['hosts']['entry_file_by_manifest_dir'], 'unknown', '__proto__']:
        rows.append(('entry_file', [value]))
    for value in [{'seat': 'owner', 'role': 'primary'}, {'seat': 'worker', 'role': 'satellite'},
                  None, {'seat': 'worker', 'role': 'bogus'}, {'seat': '../escape', 'role': 'primary'},
                  {}, [], 'malformed', {'seat': 'worker\n', 'role': 'primary'}]:
        rows.append(('ledger_path', [json.dumps(value)]))
    rows.extend(('parse_run_id', [sample]) for sample in SAMPLES)
    for kind in ['team', 'playbook']:
        for standalone in ['false', 'true']:
            rows.append(('run_dir', [kind, 'demo-team', 'canonical-demo', CANONICAL, standalone]))
    return rows


class CopyFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='campus-resolvers-')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.kernel = self.base / 'kernel'
        shutil.copytree(KERNEL, self.kernel, ignore=shutil.ignore_patterns(
            'tests', '__pycache__', '.git', 'node_modules'))
        self.contract = self.kernel / 'contracts/campus.json'
        self.data = json.loads(self.contract.read_text())
        self.env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        self.env.pop('CAMPUS_CONTRACT', None)
        self.py = self.kernel / 'tools/contract.py'
        self.js = self.kernel / 'tools/contract.mjs'

    def cli(self, language, *args, env=None):
        prefix = [sys.executable, str(self.py)] if language == 'python' else [NODE, str(self.js)]
        return subprocess.run([*prefix, *args], cwd=self.base, env=env or self.env,
                              text=True, capture_output=True, timeout=20)

    def answer(self, language, function, args):
        p = self.cli(language, function, *args)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return json.loads(p.stdout)

    def mutate_contract(self):
        changed = json.loads(self.contract.read_text())
        changed['context_aliases']['files'][0].update(canonical='new-owner.md', aliases=['old-owner.md'])
        changed['registry_enums']['enums']['status'].append('paused')
        changed['seat']['ledger']['primary'] = 'records/owner.jsonl'
        changed['hosts']['clients']['new-host'] = {'manifest_dir': '.new-host', 'entry_file': 'ENTRY.txt'}
        changed['hosts']['entry_file_by_manifest_dir']['.new-host'] = 'ENTRY.txt'
        for key in changed['run_id']['run_dir']:
            changed['run_id']['run_dir'][key] = changed['run_id']['run_dir'][key].replace('runs/', 'executions/')
        target = self.base / 'custom.json'
        target.write_text(json.dumps(changed))
        return target

    def assert_usage_and_contract_errors(self, language):
        for args in [[], ['unknown'], ['entry_file'], ['entry_file', '', 'extra'], ['--contract'],
                     ['entry_file', '', '--unknown'], ['run_dir', 'team', 't', 's', CANONICAL, 'yes'],
                     ['run_dir', 'team', '../escape', 's', CANONICAL, 'false'],
                     ['run_dir', 'team', 't', 's', 'garbage', 'false']]:
            p = self.cli(language, *args)
            self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
            self.assertIn('USAGE:', p.stderr)
            self.assertEqual(p.stdout, '')
        for content, expected in [('missing', 'CONTRACT_MISSING'), ('{', 'CONTRACT_UNREADABLE'),
                                  ('{"contract_version":"2.0"}', 'CONTRACT_VERSION_UNSUPPORTED'),
                                  ('{"contract_version":"1.0"}', 'CONTRACT_INVALID')]:
            target = self.base / 'bad.json'
            if content != 'missing': target.write_text(content)
            p = self.cli(language, 'entry_file', '', '--contract', str(target))
            self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
            self.assertIn(expected, p.stderr)
            self.assertEqual(p.stdout, '')
        for raw in [b'{"contract_version":"1.0","note":"\xff"}',
                    b'{"contract_version":"1.0","note":NaN}',
                    b'\xef\xbb\xbf{"contract_version":"1.0"}']:
            target = self.base / 'bad-encoding.json'
            target.write_bytes(raw)
            p = self.cli(language, 'entry_file', '', '--contract', str(target))
            self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
            self.assertIn('CONTRACT_UNREADABLE', p.stderr)


class PythonResolvers(CopyFixture):
    def test_complete_table_and_semantics(self):
        for fn, args in cases(self.data):
            with self.subTest(function=fn, args=args):
                result = self.answer('python', fn, args)
                self.assertIsInstance(result, dict)
        audience = next(f for f in self.data['context_aliases']['files'] if f['canonical'] == 'icp.md')
        for value, mode in [('icp.md', 'canonical'), ('audience.md', 'alias'), ('ICP.MD', 'case-insensitive'),
                            ('Audience / ICP', 'concept')]:
            self.assertEqual(self.answer('python', 'resolve_context', [value]), {
                'concept': audience['concept'], 'canonical': audience['canonical'], 'matched_by': mode,
                'founding_writes': audience['founding_writes'], 'read_order': [audience['canonical'], *audience['aliases']]})
        self.assertEqual(self.answer('python', 'resolve_context', ['brand.md'])['concept'], 'Brand')
        self.assertEqual(self.answer('python', 'resolve_context', ['unknown']), {
            'concept': None, 'canonical': None, 'matched_by': None, 'founding_writes': None, 'read_order': []})
        self.assertEqual(self.answer('python', 'resolve_department', ['dean']), {
            'value': 'dean', 'canonical': 'dean-office', 'legacy_alias': True, 'known': True})
        for value, state in [('null', 'missing'), ('{', 'invalid'), ('[]', 'invalid')]:
            self.assertEqual(self.answer('python', 'ledger_path', [value]), {
                'state': state, 'role': 'satellite', 'seat': 'unknown',
                'ledger': self.data['seat']['ledger']['unknown'],
                'lane': self.data['seat']['lane']['satellite'].format(seat='unknown')})

    def test_all_run_ids_match_minter_bytes(self):
        for sample in SAMPLES:
            for pretty in [False, True]:
                flags = ['--json'] if pretty else []
                minter = subprocess.run([sys.executable, str(self.kernel / 'tools/mint_run_id.py'),
                                         'parse', sample, *flags], text=True, capture_output=True, env=self.env)
                p = self.cli('python', 'parse_run_id', sample, *flags)
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertEqual(p.stdout, minter.stdout, (sample, pretty))

    def test_run_directories_match_all_four_minter_paths(self):
        mint = load_module(self.kernel / 'tools/mint_run_id.py')
        resolver = load_module(self.py).Resolver()
        for kind in ['team', 'playbook']:
            for standalone in [False, True]:
                expected = mint.run_path(self.base, 'demo-team', 'canonical-demo', kind=kind,
                                         month='2026-09', standalone=standalone, run_id=CANONICAL)
                self.assertEqual(resolver.run_dir(kind, 'demo-team', 'canonical-demo', CANONICAL, standalone),
                                 {'run_dir': str(expected.relative_to(self.base)) + '/'})

    def test_python_exports_and_all_patterns_compile_on_load(self):
        module = load_module(self.py)
        resolver = module.Resolver()
        self.assertEqual(len(resolver.patterns), len(self.data['run_id']['patterns']))
        for name, _ in cases(self.data):
            self.assertTrue(callable(getattr(module, name)))
        doc = json.loads(self.contract.read_text())
        doc['run_id']['patterns']['canonical'] = '['
        self.contract.write_text(json.dumps(doc))
        p = self.cli('python', 'entry_file', '')
        self.assertEqual(p.returncode, 2)
        self.assertIn('CONTRACT_INVALID', p.stderr)

    def test_python_contract_only_and_override_precedence(self):
        override = self.mutate_contract()
        # Both can answer after all owning source files have been removed.
        for rel in self.data['generated_from'].values():
            (self.kernel / rel['path']).unlink()
        env = dict(self.env, CAMPUS_CONTRACT=str(override))
        for fn, arg, key, expected in [('resolve_context', 'new-owner.md', 'canonical', 'new-owner.md'),
                                      ('normalize_status', 'PAUSED', 'canonical', 'paused'),
                                      ('entry_file', 'new-host', 'entry_file', 'ENTRY.txt'),
                                      ('ledger_path', '{"role":"primary","seat":"owner"}', 'ledger', 'records/owner.jsonl')]:
            p = self.cli('python', fn, arg, env=env)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertEqual(json.loads(p.stdout)[key], expected)
        p = self.cli('python', 'normalize_status', 'paused', '--contract', str(self.contract), env=env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertFalse(json.loads(p.stdout)['known'])

    def test_python_usage_contract_errors(self):
        self.assert_usage_and_contract_errors('python')


@unittest.skipUnless(NODE, 'Node absent: JavaScript resolver parity requires Node >=18')
class JavaScriptParity(CopyFixture):
    def test_every_function_table_has_identical_json(self):
        for fn, args in cases(self.data):
            with self.subTest(function=fn, args=args):
                py = self.cli('python', fn, *args)
                js = self.cli('javascript', fn, *args)
                self.assertEqual(py.returncode, 0, py.stderr)
                self.assertEqual(js.returncode, 0, js.stderr)
                self.assertEqual(json.loads(js.stdout), json.loads(py.stdout))
                self.assertEqual(js.stdout, py.stdout)

    def test_js_parse_matches_minter_bytes_including_pretty(self):
        for sample in SAMPLES:
            for pretty in [False, True]:
                flags = ['--json'] if pretty else []
                minter = subprocess.run([sys.executable, str(self.kernel / 'tools/mint_run_id.py'),
                                         'parse', sample, *flags], text=True, capture_output=True, env=self.env)
                p = self.cli('javascript', 'parse_run_id', sample, *flags)
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertEqual(p.stdout, minter.stdout, (sample, pretty))

    def test_js_exports_and_python_named_patterns_compile_on_load(self):
        script = self.base / 'imports.mjs'
        script.write_text('import * as m from ' + json.dumps(self.js.as_uri()) + ';\n' +
                          'const r = new m.Resolver();\n' +
                          'console.log(JSON.stringify({names:Object.keys(m.FUNCTIONS), patterns:r.patterns.length,' +
                          'answer:m.entry_file("")}));\n')
        p = subprocess.run([NODE, str(script)], text=True, capture_output=True, env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        result = json.loads(p.stdout)
        self.assertEqual(result['patterns'], len(self.data['run_id']['patterns']))
        self.assertEqual(set(result['names']), set(load_module(self.py).FUNCTIONS))
        self.assertEqual(result['answer'], self.answer('python', 'entry_file', ['']))
        doc = json.loads(self.contract.read_text())
        doc['run_id']['patterns']['canonical'] = '['
        self.contract.write_text(json.dumps(doc))
        p = self.cli('javascript', 'entry_file', '')
        self.assertEqual(p.returncode, 2)
        self.assertIn('CONTRACT_INVALID', p.stderr)

    def test_js_contract_only_and_override_precedence(self):
        override = self.mutate_contract()
        for rel in self.data['generated_from'].values():
            (self.kernel / rel['path']).unlink()
        env = dict(self.env, CAMPUS_CONTRACT=str(override))
        for fn, args in [('resolve_context', ['new-owner.md']), ('normalize_status', ['PAUSED']),
                         ('entry_file', ['new-host']), ('ledger_path', ['{"role":"primary","seat":"owner"}']),
                         ('run_dir', ['playbook', 'demo-team', 'demo', CANONICAL, 'true'])]:
            py = self.cli('python', fn, *args, env=env)
            js = self.cli('javascript', fn, *args, env=env)
            self.assertEqual(js.returncode, 0, js.stderr)
            self.assertEqual(js.stdout, py.stdout)
        p = self.cli('javascript', 'normalize_status', 'paused', '--contract', str(self.contract), env=env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertFalse(json.loads(p.stdout)['known'])

    def test_js_usage_contract_errors(self):
        self.assert_usage_and_contract_errors('javascript')


if __name__ == '__main__':
    unittest.main()
