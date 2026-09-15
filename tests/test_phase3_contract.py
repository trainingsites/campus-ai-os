"""Phase 3.3/3.4: emitted socket schema and producer-to-consumer acceptance.

Stock Python, isolated copies only. KERNEL_SRC / FOUNDRY_SRC override sources.
Optional PHASE3_CONTRACT_EVIDENCE records the acceptance run for release review.
platform: codex; seat: codex
"""
from __future__ import annotations

import hashlib
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
FOUNDRY = Path(os.environ.get('FOUNDRY_SRC', KERNEL.parents[2] / 'library/teams/_foundry')).resolve()
NO_FOUNDRY = 'FOUNDRY_SRC not set and no campus Foundry beside this tree'
KREL = Path('library/plugins/campus-ai-os-v5-src')
FREL = Path('library/teams/_foundry')
SCHEMA = Path('schemas/results.schema.json')


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, doc):
    path.write_text(json.dumps(doc, indent=2) + '\n', encoding='utf-8')


def copy_tree(src, dst):
    return Path(shutil.copytree(src, dst, ignore=shutil.ignore_patterns(
        '.git', '__pycache__', 'node_modules', '.pytest_cache', 'dist')))


def aggregate(campus):
    """results-aggregator steps 1-3: read the producer bytes, group by run_id.

    This acceptance campus contains v1.1-valid envelopes only. Classification
    is asserted separately through validate_results.py before this read.
    No adapter, conversion, completion inference, or write back is permitted.
    """
    grouped = {}
    for path in sorted((campus / 'outputs').glob('**/results.json')):
        doc = read_json(path)
        row = grouped.setdefault(doc['run_id'], {
            'teams_touched': [], 'assets_total': 0, 'assets_published': 0,
            'completion': [], 'bindings': [], 'outcomes': [],
        })
        if doc['team'] not in row['teams_touched']:
            row['teams_touched'].append(doc['team'])
        row['assets_total'] += len(doc.get('assets', []))
        row['assets_published'] += sum(a['status'] == 'published' for a in doc.get('assets', []))
        row['completion'].append({'team': doc['team'], 'completion': doc.get('completion')})
        row['bindings'].extend(doc.get('bindings', []))
        if 'outcome' in doc:
            row['outcomes'].append(doc['outcome'])
        for asset in doc.get('assets', []):
            if 'performance' in asset and asset['performance'] is not None:
                row['outcomes'].append(asset['performance'])
    return grouped


@unittest.skipUnless((FOUNDRY / 'bin/scaffold-team').is_file(), NO_FOUNDRY)
class Phase3Contract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='campus-phase3-contract-')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.campus = self.base / 'campus'
        self.kernel = copy_tree(KERNEL, self.campus / KREL)
        self.foundry = copy_tree(FOUNDRY, self.campus / FREL)
        self.env = dict(os.environ, CAMPUS_ROOT=str(self.campus), PYTHONDONTWRITEBYTECODE='1')
        (self.campus / '.campus-os').mkdir()
        shutil.copy2(self.kernel / 'templates/registration-block-spec.md',
                     self.campus / '.campus-os/registration-block-spec.md')

    def run_tool(self, path, *args, env=None):
        return subprocess.run([sys.executable, str(path), *map(str, args)],
                              cwd=self.campus, env=env or self.env,
                              text=True, capture_output=True, timeout=60)

    def sockets(self, *extra, campus=None, env=None):
        return self.run_tool(self.foundry / 'bin/validate-sockets', '--campus',
                             campus or self.campus, *extra, env=env)

    def good_entry(self):
        return self.foundry / 'tests/fixtures/good-team/registry-entry.json'

    def scaffold(self):
        team = 'contract-team'
        p = self.run_tool(self.foundry / 'bin/scaffold-team', team, '--mission',
                          'produce one draft contract asset', '--campus', self.campus,
                          '--dest', self.campus / 'library/teams')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        root = self.campus / 'library/teams' / team
        # Complete the scaffold's explicit socket TODO, as its next-step says.
        entry = read_json(root / 'registry-entry.json')
        self.assertEqual(entry['produces'][0]['artifact_type'], 'TODO-from-vocabulary')
        entry['produces'] = [{'artifact_type': 'results-ledger', 'output': 'one draft asset',
                              'done_check': 'asset is readable'}]
        write_json(root / 'registry-entry.json', entry)
        skill = (root / 'skills' / team / 'SKILL.md').read_text()
        self.assertTrue('mint-run-id' in skill or 'mint_run_id.py' in skill)
        return team, root

    def produce(self):
        team, root = self.scaffold()
        p = self.run_tool(self.kernel / 'tools/mint_run_id.py', 'mint', 'contract-demo',
                          '--team', team, '--kind', 'team', '--campus-root', self.campus, '--json')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        made = json.loads(p.stdout)
        path = Path(made['run_dir']) / 'results.json'
        doc = read_json(path)
        self.assertEqual(doc['assets'], [])
        self.assertIn('completion', doc)
        asset = path.parent / 'draft.md'
        asset.write_text('A draft produced by the contract fixture.\n', encoding='utf-8')
        binding = {'stage': 'draft', 'employee': team, 'employee_type': 'team',
                   'version': read_json(root / '.claude-plugin/plugin.json')['version'],
                   'reason': 'Scaffolded team owns the requested draft.', 'alternatives': []}
        doc['assets'] = [{'type': 'document', 'path': str(asset.relative_to(self.campus)),
                          'status': 'draft', 'tier': 'local', 'url': None, 'performance': None}]
        doc['completion'] = {'execution_success': True, 'artifact_passed': True, 'owner_approved': False}
        doc['bindings'] = [binding]
        write_json(path, doc)
        return made, path, binding

    def test_producer_consumer_binding_and_negative_twin(self):
        made, path, binding = self.produce()
        before = path.read_bytes()
        p = self.run_tool(self.kernel / 'tools/validate_results.py', '--campus-root', self.campus, '--json')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        classified = json.loads(p.stdout)
        self.assertEqual(classified['counts'], {'v1.1-valid': 1})
        grouped = aggregate(self.campus)
        row = grouped[made['run_id']]
        self.assertEqual(len(grouped), 1)
        self.assertEqual(row['teams_touched'], ['contract-team'])
        self.assertEqual((row['assets_total'], row['assets_published']), (1, 0))
        self.assertEqual(row['bindings'], [binding])
        self.assertEqual(row['completion'][0]['completion'], read_json(path)['completion'])
        self.assertEqual(path.read_bytes(), before, 'consumer changed producer bytes')
        good = self.sockets('--json')
        self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
        self.assertIn(str(path), good.stderr)
        self.assertNotIn('mint-run-id stub', good.stderr)
        self.assertEqual(path.read_bytes(), before)

        doc = read_json(path)
        del doc['completion']
        write_json(path, doc)
        self.assertNotIn('completion', read_json(path))
        bad_bytes = path.read_bytes()
        p = self.run_tool(self.kernel / 'tools/validate_results.py', '--campus-root', self.campus, '--json')
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        negative = json.loads(p.stdout)
        self.assertEqual(negative['counts'], {'v1.1-invalid': 1})
        bad = self.sockets('--json')
        self.assertEqual(bad.returncode, 2, bad.stdout + bad.stderr)
        failures = json.loads(bad.stdout)['fails']
        self.assertEqual(len(failures), 1, failures)
        self.assertIn('results schema:', failures[0])
        self.assertIn("missing required field 'completion'", failures[0])
        self.assertEqual(path.read_bytes(), bad_bytes)
        evidence = os.environ.get('PHASE3_CONTRACT_EVIDENCE')
        if evidence:
            write_json(Path(evidence), {
                'platform': 'codex', 'seat': 'codex', 'run_id': made['run_id'],
                'binding': binding, 'aggregator_grouped': grouped,
                'producer_sha256': hashlib.sha256(before).hexdigest(),
                'consumer_preserved_bytes': True, 'classification': classified,
                'negative_classification': negative, 'negative_socket_errors': failures,
            })

    def test_good_fixture_mints_and_passes_with_warnings(self):
        p = self.sockets('--entry', self.good_entry(), '--json')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        result = json.loads(p.stdout)
        self.assertEqual(set(result), {'entries_checked', 'fails', 'warns', 'pass'})
        self.assertTrue(result['warns'])
        self.assertIn('mint-run-id stub', p.stderr)
        self.assertFalse((self.campus / 'outputs').exists())
        text = self.sockets('--entry', self.good_entry())
        self.assertEqual(text.returncode, 0, text.stdout + text.stderr)
        self.assertIn(f"warnings: {len(result['warns'])}", text.stdout)

    def test_broken_fixture_fails_schema_only(self):
        fixture = self.foundry / 'tests/fixtures/broken-results'
        p = self.run_tool(fixture / 'emit.py', '--campus', self.campus, '--foundry', self.foundry)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        path = Path(p.stdout.strip())
        self.assertNotIn('completion', read_json(path))
        p = self.sockets('--entry', fixture / 'registry-entry.json', '--json')
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        errors = json.loads(p.stdout)['fails']
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("missing required field 'completion'", errors[0])
        self.assertTrue(all('results schema:' in e for e in errors))

    def test_minted_sample_is_validated_from_disk(self):
        minter = self.kernel / 'tools/mint_run_id.py'
        source = minter.read_text()
        self.assertEqual(source.count('"completion": {'), 1)
        minter.write_text(source.replace('"completion": {', '"missing_completion": {'))
        self.assertNotIn('"completion": {', minter.read_text())
        p = self.sockets('--entry', self.good_entry(), '--json')
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn('mint-run-id stub', p.stderr)
        self.assertIn("missing required field 'completion'", ' '.join(json.loads(p.stdout)['fails']))

    def legacy_runs(self, current, versions):
        """Derive old shapes from an emitted run; never read or rewrite live history."""
        paths = []
        for label, version in versions:
            doc = read_json(current)
            doc['schema_version'] = version
            if version is None:
                del doc['schema_version']
            if version == '1.1-completion-only':
                del doc['assets']
            else:
                del doc['completion']
            path = current.parent.parent / ('history-' + label) / 'results.json'
            path.parent.mkdir()
            write_json(path, doc)
            paths.append(path)
        return paths

    def test_legacy_history_warns_and_current_sample_still_fails_on_schema(self):
        _, current, _ = self.produce()
        legacy = self.legacy_runs(current, [('v1', '1.0'), ('profile', '1.1-completion-only')])
        before = {path: path.read_bytes() for path in [current, *legacy]}
        good = self.sockets('--json')
        self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
        result = json.loads(good.stdout)
        self.assertFalse(result['fails'])
        self.assertEqual(len(result['warns']), 2)
        self.assertTrue(all('legacy 1.0, skipped' in w for w in result['warns']))
        self.assertIn(f'results sample (emitted run): {current}', good.stderr)
        self.assertNotIn('mint-run-id stub', good.stderr)
        self.assertEqual({path: path.read_bytes() for path in before}, before)

        doc = read_json(current)
        del doc['completion']
        write_json(current, doc)
        self.assertNotIn('completion', read_json(current))
        bad = self.sockets('--json')
        self.assertEqual(bad.returncode, 2, bad.stdout + bad.stderr)
        result = json.loads(bad.stdout)
        self.assertEqual(len(result['fails']), 1, result)
        self.assertIn("missing required field 'completion'", result['fails'][0])
        self.assertEqual(len(result['warns']), 2)
        self.assertEqual({path: path.read_bytes() for path in legacy},
                         {path: before[path] for path in legacy})

    def test_only_legacy_history_exercises_current_minter(self):
        _, current, _ = self.produce()
        versions = [('v1', '1.0'), ('profile', '1.1-completion-only'),
                    ('missing', None), ('empty', ''), ('unknown', '9.0')]
        legacy = self.legacy_runs(current, versions)
        current.unlink()
        self.assertFalse(current.exists())
        before = {path: path.read_bytes() for path in legacy}
        p = self.sockets('--json')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        result = json.loads(p.stdout)
        self.assertFalse(result['fails'])
        self.assertEqual(len(result['warns']), len(versions))
        self.assertTrue(all('legacy ' in w and ', skipped' in w for w in result['warns']))
        self.assertIn('mint-run-id stub; no current team run available', p.stderr)
        self.assertEqual(set((self.campus / 'outputs').glob('**/results.json')), set(legacy))
        self.assertEqual({path: path.read_bytes() for path in legacy}, before)

    def test_fresh_minter_cannot_claim_legacy_to_bypass_schema(self):
        minter = self.kernel / 'tools/mint_run_id.py'
        source = minter.read_text()
        self.assertEqual(source.count('"schema_version": "1.1"'), 1)
        minter.write_text(source.replace('"schema_version": "1.1"', '"schema_version": "1.0"'))
        self.assertNotIn('"schema_version": "1.1"', minter.read_text())
        p = self.sockets('--entry', self.good_entry(), '--json')
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn('mint-run-id stub', p.stderr)
        self.assertIn('$.schema_version:', ' '.join(json.loads(p.stdout)['fails']))
        self.assertNotIn('legacy 1.0, skipped', p.stderr)

    def test_phrase_checks_warn_never_fail(self):
        root = self.good_entry().parent
        for path in root.glob('skills/*/SKILL.md'):
            text = path.read_text().replace('Install it first, then run me again', 'Set up your campus before proceeding')
            text = text.replace('Never append when an entry already exists', 'Keep exactly one entry per team')
            path.write_text(text)
        self.assertFalse(any('Never append when an entry already exists' in p.read_text()
                             for p in root.glob('skills/*/SKILL.md')))
        p = self.run_tool(self.foundry / 'bin/validate-team', root, '--campus', self.campus, '--json')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        result = json.loads(p.stdout)
        self.assertFalse(result['fails'])
        self.assertTrue(any('no-campus stop rule absent' in w for w in result['warns']))
        self.assertTrue(any('registry dedupe rule absent' in w for w in result['warns']))

    def test_list_types_include_null_and_enforce_nested_constraints(self):
        spec = importlib.util.spec_from_file_location('contract_common', self.foundry / 'bin/_common.py')
        common = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(common)
        schema = {'type': ['object', 'null'], 'required': ['url'],
                  'properties': {'url': {'type': ['string', 'null'], 'pattern': '^https:'}}}
        for good in (None, {'url': None}, {'url': 'https://example.invalid'}):
            self.assertEqual(common.validate_against_schema(good, schema), [])
        for bad in (False, {}, {'url': 7}, {'url': 'wrong'}):
            self.assertTrue(common.validate_against_schema(bad, schema), bad)
        self.assertTrue(common.validate_against_schema([False], {
            'type': ['array', 'null'], 'items': {'type': ['integer', 'null']}}))

    def test_malformed_and_wrong_team_are_not_hidden(self):
        made, path, _ = self.produce()
        original = read_json(path)
        for content, expected in (('{', 'results schema:'), ('[]', 'expected type object'),
                                  (json.dumps(dict(original, team='different-team')), 'expected emitting team')):
            with self.subTest(expected=expected):
                path.write_text(content)
                p = self.sockets('--json')
                self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
                self.assertIn(expected, ' '.join(json.loads(p.stdout)['fails']))

    def test_unknown_socket_remains_error(self):
        entry = self.good_entry()
        data = read_json(entry)
        data['produces'][0]['artifact_type'] = 'unknown-contract-type'
        write_json(entry, data)
        p = self.sockets('--entry', entry, '--json')
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn('unknown artifact_type', ' '.join(json.loads(p.stdout)['fails']))

    def test_missing_schema_fails_loudly(self):
        (self.kernel / SCHEMA).unlink()
        (self.foundry / SCHEMA).unlink()
        p = self.sockets('--entry', self.good_entry(), '--json')
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn('cannot load', ' '.join(json.loads(p.stdout)['fails']))

    def test_schema_resolution_explicit_then_env_then_own_campus(self):
        # Different required fields prove the chosen schema was opened, not just printed.
        for mode in ('explicit', 'env', 'own'):
            with self.subTest(mode=mode):
                external = self.base / ('external-' + mode)
                external.mkdir()
                candidate = external / KREL / SCHEMA
                candidate.parent.mkdir(parents=True)
                doc = read_json(self.kernel / SCHEMA)
                doc['required'].append('probe_' + mode)
                write_json(candidate, doc)
                args = ['--entry', self.good_entry(), '--json']
                env = dict(self.env)
                if mode == 'explicit':
                    args += ['--campus', external]
                    expected = candidate
                elif mode == 'env':
                    env['CAMPUS_ROOT'] = str(external)
                    args += ['--campus', self.base / 'empty']
                    expected = candidate
                else:
                    env.pop('CAMPUS_ROOT', None)
                    args += ['--campus', self.base / 'empty']
                    expected = self.kernel / SCHEMA
                p = self.run_tool(self.foundry / 'bin/validate-sockets', *args, env=env)
                self.assertIn('results schema: ' + str(expected), p.stderr)
                self.assertEqual(p.returncode, 0 if mode == 'own' else 2, p.stdout + p.stderr)
                if mode != 'own':
                    self.assertIn('probe_' + mode, ' '.join(json.loads(p.stdout)['fails']))

    def test_fallback_ignores_decoy_kernel_and_emits_valid_stub(self):
        # Remove the exact owner; leave a decoy plugin with an impossible schema.
        (self.kernel / SCHEMA).unlink()
        (self.kernel / 'tools/mint_run_id.py').unlink()
        decoy = self.campus / 'library/plugins/aaa-decoy/schemas/results.schema.json'
        decoy.parent.mkdir(parents=True)
        write_json(decoy, {'type': 'object', 'required': ['decoy']})
        p = self.sockets('--entry', self.good_entry(), '--json')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn('results schema: ' + str(self.foundry / SCHEMA), p.stderr)
        self.assertNotIn('aaa-decoy', p.stderr)
        self.assertIn('mint-run-id stub', p.stderr)

    def test_invalid_preferred_schema_does_not_silently_fall_back(self):
        (self.kernel / SCHEMA).write_text('{')
        p = self.sockets('--entry', self.good_entry(), '--json')
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn('cannot load', ' '.join(json.loads(p.stdout)['fails']))

    def test_missing_flag_value_is_usage_error(self):
        for flag in ('--campus', '--entry'):
            p = self.run_tool(self.foundry / 'bin/validate-sockets', flag)
            self.assertEqual(p.returncode, 1)
            self.assertIn('needs a value', p.stderr)
            self.assertNotIn('Traceback', p.stderr)


if __name__ == '__main__':
    unittest.main()
