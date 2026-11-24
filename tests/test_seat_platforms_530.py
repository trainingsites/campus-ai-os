"""5.3.0: machine fingerprint on Windows and Linux (GitHub issue #2) and owner-declared seat roles.
Isolated fixtures; nothing here reads a live campus or the real registry.
"""
import hashlib, importlib.util, json, os, subprocess, sys, tempfile, types, unittest
from pathlib import Path
from unittest import mock

KERNEL = Path(os.environ.get('KERNEL_SRC', Path(__file__).resolve().parent.parent)).resolve()
RESOLVER = KERNEL / 'tools' / 'resolve-seat.py'
UUID = '0A1B2C3D-4E5F-6071-8293-A4B5C6D7E8F9'
GUID = '6f1c2a9e-3b4d-4e5f-8a7b-9c0d1e2f3a4b'
LINUX = '0123456789abcdef0123456789abcdef'


def load():
    spec = importlib.util.spec_from_file_location('resolve_seat_530', RESOLVER)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


class Fingerprint(unittest.TestCase):
    def setUp(self):
        self.r = load()

    def test_macos_value_is_unchanged_from_5_2(self):
        # 5.2.x hashed the bare lowercase UUID; every existing seat.json depends on that.
        self.assertEqual(self.r.fingerprint('darwin', UUID), hashlib.sha256(UUID.lower().encode()).hexdigest())

    def test_windows_and_linux_are_prefixed_and_distinct(self):
        w, l = self.r.fingerprint('win32', GUID), self.r.fingerprint('linux', LINUX)
        self.assertEqual(w, hashlib.sha256(f'win32:{GUID}'.encode()).hexdigest())
        self.assertEqual(l, hashlib.sha256(f'linux:{LINUX}'.encode()).hexdigest())
        self.assertNotEqual(self.r.fingerprint('linux', UUID), self.r.fingerprint('darwin', UUID))

    def test_missing_id_gives_none(self):
        for p in ('darwin', 'win32', 'linux'):
            self.assertIsNone(self.r.fingerprint(p, None))
            self.assertIsNone(self.r.fingerprint(p, ''))
        self.assertIsNone(self.r.machine_id('sunos5'))

    def test_linux_reader_uses_first_valid_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad, good = Path(tmp, 'bad'), Path(tmp, 'good')
            bad.write_text('not-an-id\n'); good.write_text(LINUX + '\n')
            self.assertEqual(self.r._linux_id((str(Path(tmp, 'missing')), str(bad), str(good)), container=False), LINUX)
            self.assertIsNone(self.r._linux_id((str(bad),), container=False))

    def test_windows_reader_reads_machine_guid(self):
        class Key:
            def __enter__(self): return self
            def __exit__(self, *a): return False
        fake = types.SimpleNamespace(HKEY_LOCAL_MACHINE=1, KEY_READ=1, KEY_WOW64_64KEY=256,
                                     OpenKey=lambda *a: Key(), QueryValueEx=lambda k, n: (GUID, 1))
        with mock.patch.dict(sys.modules, {'winreg': fake}):
            self.assertEqual(self.r._windows_id(), GUID)
            with mock.patch.object(self.r, '_windows_id', return_value=GUID):
                self.assertEqual(self.r.machine_id('win32'), self.r.fingerprint('win32', GUID))

    def test_windows_reader_without_winreg_is_none(self):
        with mock.patch.dict(sys.modules, {'winreg': None}):
            self.assertIsNone(self.r._windows_id())


class OwnerDeclaredSeat(unittest.TestCase):
    def setUp(self):
        self.r = load(); self.mid = self.r.fingerprint('linux', LINUX)

    def test_single_primary_owns_the_clock_and_resolves(self):
        seat, why = self.r.init_seat(self.mid, ['claude-code'], ['codex'], machine='Studio Mac')
        self.assertIsNone(why)
        self.assertEqual(seat['clock_owner'], 'claude-code')
        self.assertEqual(seat['declared_by'], 'owner')
        self.assertEqual(seat['clients']['codex'], {'seat': 'studio-mac-codex', 'role': 'satellite'})
        # /campus-doctor's seat check reads the top-level seat and role (seat_contract_checks.read_seat)
        self.assertEqual((seat['seat'], seat['role'], seat['client']), ('studio-mac-claude-code', 'primary', 'claude-code'))
        sys.path.append(str(KERNEL / 'tools'))
        import seat_contract_checks
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / '.campus-os').mkdir()
            (Path(tmp) / '.campus-os/seat.json').write_text(json.dumps(seat))
            self.assertEqual(seat_contract_checks.read_seat(Path(tmp))['status'], 'valid')
        out = self.r.resolve(seat, 'claude-code', self.mid)
        self.assertEqual((out['role'], out['owns_clock'], out['warning']), ('primary', True, None))
        sat = self.r.resolve(seat, 'codex', self.mid)
        self.assertEqual((sat['role'], sat['owns_clock']), ('satellite', False))
        self.assertEqual(sat['ledger'], 'dean/.activity.studio-mac-codex.jsonl')

    def test_two_primaries_need_a_named_clock_owner(self):
        seat, why = self.r.init_seat(self.mid, ['claude-code', 'codex'])
        self.assertIsNone(seat); self.assertIn('--clock-owner', why)
        seat, why = self.r.init_seat(self.mid, ['claude-code', 'codex'], clock_owner='codex', machine='m')
        out = self.r.resolve(seat, 'claude-code', self.mid)
        self.assertEqual((out['role'], out['owns_clock'], out['ledger']), ('primary', False, 'dean/.activity.m-claude-code.jsonl'))

    def test_refusals(self):
        self.assertIn('not observed', self.r.init_seat(None, ['claude-code'])[1])
        self.assertIn('at least one primary', self.r.init_seat(self.mid, [])[1])
        self.assertIn('both primary and satellite', self.r.init_seat(self.mid, ['codex'], ['codex'])[1])
        self.assertIn('invalid client', self.r.init_seat(self.mid, ['Bad Name'])[1])
        self.assertIn('must be one of the primary', self.r.init_seat(self.mid, ['codex'], clock_owner='claude-code')[1])

    def test_cli_never_overwrites_an_existing_seat_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            seat_file = Path(tmp, 'seat.json'); seat_file.write_text('{"keep": true}\n')
            p = subprocess.run([sys.executable, '-I', '-B', str(RESOLVER), '--init-seat', '--primary', 'claude-code',
                                '--seat-file', str(seat_file)], capture_output=True, text=True)
            self.assertEqual(p.returncode, 2)
            self.assertIn('already exists', json.loads(p.stdout)['reason'])
            self.assertEqual(seat_file.read_text(), '{"keep": true}\n')

    def test_cli_resolve_still_requires_client(self):
        p = subprocess.run([sys.executable, '-I', '-B', str(RESOLVER)], capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)
        self.assertIn('--client is required', p.stderr)


class ReviewFixes530(unittest.TestCase):
    """Defects found by the independent review of 5.3.0, fixed before release."""
    def setUp(self):
        self.r = load()

    def test_a_container_observes_no_linux_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = Path(tmp, 'id'); good.write_text(LINUX + '\n')
            self.assertIsNone(self.r._linux_id((str(good),), container=True))
            marker = Path(tmp, '.dockerenv'); marker.write_text('')
            cg = Path(tmp, 'cgroup'); cg.write_text('0::/\n')
            self.assertTrue(self.r.in_container(markers=(str(marker),), cgroup=str(cg), environ={}))
            self.assertTrue(self.r.in_container(markers=(), cgroup=str(cg), environ={'container': 'podman'}))
            cg.write_text('12:pids:/kubepods/besteffort/pod1\n')
            self.assertTrue(self.r.in_container(markers=(), cgroup=str(cg), environ={}))
            cg.write_text('0::/user.slice\n')
            self.assertFalse(self.r.in_container(markers=(), cgroup=str(cg), environ={}))

    def test_sandbox_with_valid_binding_still_resolves_via_binding(self):
        # the container observes nothing, so resolve() takes the binding branch exactly as on 5.2
        mid = 'b' * 64
        seat, _ = self.r.init_seat(mid, ['claude-cowork'], machine='m')
        now = self.r.utcnow()
        binding = {'schema_version': 1, 'client': 'claude-cowork', 'machine_id': mid,
                   'issued_at': self.r.fmt_ts(now), 'expires_at': self.r.fmt_ts(now + self.r.dt.timedelta(hours=6))}
        out = self.r.resolve(seat, 'claude-cowork', None, binding, now)
        self.assertEqual((out['role'], out['via']), ('primary', 'host-binding'))

    def test_writer_never_follows_a_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            camp, outside = Path(tmp, '.campus-os'), Path(tmp, 'outside')
            camp.mkdir(); outside.mkdir()
            # old fixed temp name planted as a link: untouched, because the temp name is random
            (camp / 'seat.json.tmp').symlink_to(outside / 'pwned.json')
            self.assertIsNone(self.r.write_file(camp / 'seat.json', '{}\n', overwrite=False))
            self.assertFalse((camp / 'seat.json').is_symlink())
            self.assertFalse((outside / 'pwned.json').exists())
            # a link AT the target is refused, for new files and for overwrites
            (camp / 'host-binding.json').symlink_to(outside / 'b.json')
            self.assertIn('link', self.r.write_file(camp / 'host-binding.json', '{}', overwrite=True))
            self.assertFalse((outside / 'b.json').exists())
            # a linked folder is refused
            linked = Path(tmp, 'linked'); linked.symlink_to(outside)
            self.assertIn('link', self.r.write_file(linked / 'seat.json', '{}', overwrite=False))
            # an existing file is never overwritten
            self.assertIn('already exists', self.r.write_file(camp / 'seat.json', 'x', overwrite=False))
            self.assertEqual((camp / 'seat.json').read_text(), '{}\n')
            self.assertEqual([p.name for p in camp.iterdir() if p.name.endswith('.tmp') and not p.is_symlink()], [])

    def test_resolver_calls_in_docs_run_isolated(self):
        import re as _re
        for rel in ('templates/clients/AGENTS.md', 'templates/clients/GEMINI.md', 'templates/ledger-paths.md',
                    'references/host-binding.md', 'CODEX-INSTALL.md', 'skills/campus-start/references/scaffold.md',
                    'skills/update-workspace/references/additions.md'):
            text = (KERNEL / rel).read_text(encoding='utf-8')
            self.assertEqual(_re.findall(r'python3 (?!-I -B)\S*resolve-seat\.py', text), [], rel)


if __name__ == '__main__':
    unittest.main()
