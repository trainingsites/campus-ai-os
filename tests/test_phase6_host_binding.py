"""Seat Contract host binding (5.2.4). Isolated fixtures; nothing here reads a live campus.
platform: claude-code; seat: m4-claude-code
"""
import importlib.util, json, os, subprocess, sys, tempfile, unittest
import datetime as dt
from pathlib import Path

KERNEL = Path(os.environ.get('KERNEL_SRC', Path(__file__).resolve().parent.parent)).resolve()
RESOLVER = KERNEL / 'tools' / 'resolve-seat.py'
CHECKS = KERNEL / 'tools' / 'seat_contract_checks.py'
NOW = dt.datetime(2026, 9, 9, 15, 0, tzinfo=dt.timezone.utc)
MID = 'a' * 64
CONFIG = {
    'schema_version': 2, 'seat': 'owner', 'role': 'primary', 'client': 'claude-cowork', 'machine_id': MID,
    'clients': {'claude-cowork': {'seat': 'owner', 'role': 'primary'},
                'codex': {'seat': 'codex', 'role': 'satellite'},
                'claude-code': {'seat': 'host-code', 'role': 'satellite'}},
}


def load():
    spec = importlib.util.spec_from_file_location('resolve_seat', RESOLVER)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def ts(t):
    return t.strftime('%Y-%m-%dT%H:%M:%SZ')


def binding(client='claude-cowork', mid=MID, issued=NOW - dt.timedelta(hours=1), ttl=12, schema=1):
    return {'schema_version': schema, 'client': client, 'machine_id': mid,
            'issued_at': ts(issued), 'expires_at': ts(issued + dt.timedelta(hours=ttl)), 'issued_by': 'fixture'}


class ResolveWithBinding(unittest.TestCase):
    def setUp(self):
        self.r = load()

    def test_unavailable_fingerprint_with_fresh_binding_is_primary(self):
        out = self.r.resolve(CONFIG, 'claude-cowork', None, binding(), NOW)
        self.assertEqual((out['role'], out['seat'], out['via'], out['warning']), ('primary', 'owner', 'host-binding', None))
        self.assertEqual(out['ledger'], 'dean/.activity.jsonl')
        self.assertEqual(out['binding_expires'], ts(NOW + dt.timedelta(hours=11)))

    def test_no_binding_still_denies(self):
        out = self.r.resolve(CONFIG, 'claude-cowork', None, None, NOW)
        self.assertEqual((out['role'], out['via']), ('satellite', 'unresolved'))
        self.assertTrue(out['warning'] and out['seat'].startswith('unassigned-claude-cowork-'))

    def test_binding_never_overrides_a_mismatch(self):
        out = self.r.resolve(CONFIG, 'claude-cowork', 'b' * 64, binding(), NOW)
        self.assertEqual(out['role'], 'satellite'); self.assertIn('does not match', out['reason'])

    def test_observed_fingerprint_ignores_binding(self):
        out = self.r.resolve(CONFIG, 'claude-cowork', MID, binding(ttl=999), NOW)
        self.assertEqual((out['role'], out['via']), ('primary', 'observed'))

    def test_binding_rejections(self):
        cases = {
            'other client': binding(client='codex'),
            'other machine': binding(mid='c' * 64),
            'expired': binding(issued=NOW - dt.timedelta(hours=13)),
            'future': binding(issued=NOW + dt.timedelta(hours=1)),
            'too long': binding(ttl=25),
            'bad schema': binding(schema=2),
            'malformed ts': {**binding(), 'expires_at': 'tomorrow'},
            'not a dict': ['x'],
        }
        for name, b in cases.items():
            with self.subTest(name):
                out = self.r.resolve(CONFIG, 'claude-cowork', None, b, NOW)
                self.assertEqual(out['role'], 'satellite'); self.assertTrue(out['warning'])
                self.assertIn('fingerprint unavailable', out['reason'])

    def test_binding_for_satellite_client_is_refused(self):
        # a satellite client on a sandboxed host cannot borrow a primary binding, nor hold its own
        out = self.r.resolve(CONFIG, 'codex', None, binding(client='codex'), NOW)
        self.assertEqual(out['role'], 'satellite'); self.assertIn('not the clock owner', out['reason'])

    def test_binding_re_enters_every_invariant(self):
        two = json.loads(json.dumps(CONFIG)); two['clients']['codex']['role'] = 'primary'
        out = self.r.resolve(two, 'claude-cowork', None, binding(), NOW)
        self.assertEqual(out['role'], 'satellite')


class IssueBinding(unittest.TestCase):
    def setUp(self):
        self.r = load()

    def test_refuses_without_observed_fingerprint(self):
        b, why = self.r.issue_binding(CONFIG, 'claude-cowork', None, 12, NOW)
        self.assertIsNone(b); self.assertIn('sandbox', why)

    def test_refuses_on_other_host_or_non_primary(self):
        self.assertIsNone(self.r.issue_binding(CONFIG, 'claude-cowork', 'b' * 64, 12, NOW)[0])
        self.assertIsNone(self.r.issue_binding(CONFIG, 'codex', MID, 12, NOW)[0])

    def test_ttl_is_clamped_both_ways(self):
        b, _ = self.r.issue_binding(CONFIG, 'claude-cowork', MID, 8760, NOW)
        self.assertEqual(b['expires_at'], ts(NOW + dt.timedelta(hours=24)))
        b, _ = self.r.issue_binding(CONFIG, 'claude-cowork', MID, 0, NOW)
        self.assertEqual(b['expires_at'], ts(NOW + dt.timedelta(hours=1)))
        b, why = self.r.issue_binding(CONFIG, 'claude-cowork', MID, 'lots', NOW)
        self.assertIsNone(b)

    def test_issued_binding_round_trips_through_resolve(self):
        b, _ = self.r.issue_binding(CONFIG, 'claude-cowork', MID, 12, NOW)
        self.assertEqual(b['schema_version'], 1); self.assertIn('owner', b['issued_by'])
        out = self.r.resolve(CONFIG, 'claude-cowork', None, b, NOW + dt.timedelta(hours=11, minutes=59))
        self.assertEqual(out['role'], 'primary')
        out = self.r.resolve(CONFIG, 'claude-cowork', None, b, NOW + dt.timedelta(hours=12))
        self.assertEqual(out['role'], 'satellite')


class Cli(unittest.TestCase):
    """End to end on this machine. The real fingerprint is whatever ioreg says; the fixture
    writes a seat.json that names it, so the observed path is exercised on any Mac and the
    binding path is exercised by pointing --now past expiry."""
    def setUp(self):
        self.r = load(); self.mid = self.r.machine_id()
        self.tmp = tempfile.TemporaryDirectory(prefix='campus-binding-'); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'campus'; (self.root / '.campus-os').mkdir(parents=True)
        cfg = json.loads(json.dumps(CONFIG)); cfg['machine_id'] = self.mid or MID
        (self.root / '.campus-os' / 'seat.json').write_text(json.dumps(cfg))
        self.seat = self.root / '.campus-os' / 'seat.json'
        self.bind = self.root / '.campus-os' / 'host-binding.json'

    def cli(self, *args):
        p = subprocess.run([sys.executable, str(RESOLVER), '--seat-file', str(self.seat), *args], text=True, capture_output=True, timeout=15)
        return p.returncode, json.loads(p.stdout)

    def test_issue_then_resolve_then_lapse(self):
        if not self.mid:
            self.skipTest('no fingerprint on this host (not macOS)')
        rc, out = self.cli('--issue-binding', '--client', 'claude-cowork', '--ttl-hours', '12')
        self.assertEqual(rc, 0); self.assertTrue(out['issued']); self.assertTrue(self.bind.is_file())
        written = json.loads(self.bind.read_text()); self.assertEqual(written['machine_id'], self.mid)
        rc, out = self.cli('--client', 'claude-cowork')
        self.assertEqual((rc, out['role'], out['via']), (0, 'primary', 'observed'))   # host observes: binding unused
        later = ts(dt.datetime.fromisoformat(written['expires_at'].replace('Z', '+00:00')) + dt.timedelta(minutes=1))
        rc, out = self.cli('--client', 'claude-cowork', '--now', later)
        self.assertEqual((rc, out['role']), (0, 'primary'))   # still observed on the host - the lapse only bites a sandbox
        # doctor check 11d sees the lapse
        p = subprocess.run([sys.executable, str(CHECKS), '--campus-root', str(self.root), '--json'], text=True, capture_output=True, timeout=15)
        d = json.loads(p.stdout)['host_binding']; self.assertEqual(d['status'], 'fresh'); self.assertGreater(d['hours_to_expiry'], 11)

    def test_issue_refused_for_non_primary_client(self):
        if not self.mid:
            self.skipTest('no fingerprint on this host (not macOS)')
        rc, out = self.cli('--issue-binding', '--client', 'codex')
        self.assertEqual(rc, 2); self.assertFalse(out['issued']); self.assertFalse(self.bind.exists())

    def test_bad_now_is_an_error(self):
        rc, out = self.cli('--client', 'claude-cowork', '--now', 'yesterday')
        self.assertEqual(rc, 2); self.assertIn('error', out)


class DoctorCheck11d(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='campus-11d-'); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'campus'; (self.root / '.campus-os').mkdir(parents=True)
        (self.root / '.campus-os' / 'seat.json').write_text(json.dumps(CONFIG))

    def run_checks(self):
        p = subprocess.run([sys.executable, str(CHECKS), '--campus-root', str(self.root), '--json'], text=True, capture_output=True, timeout=15)
        q = subprocess.run([sys.executable, str(CHECKS), '--campus-root', str(self.root)], text=True, capture_output=True, timeout=15)
        return p.returncode, json.loads(p.stdout)['host_binding'], q.stdout

    def test_absent_is_silent(self):
        rc, d, text = self.run_checks()
        self.assertEqual(d['status'], 'absent'); self.assertNotIn('Host binding', text)

    def test_fresh_reports_hours(self):
        b = binding(issued=dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1))
        (self.root / '.campus-os' / 'host-binding.json').write_text(json.dumps(b))
        rc, d, text = self.run_checks()
        self.assertEqual(d['status'], 'fresh'); self.assertIn("[OK] Host binding fresh for 'claude-cowork'", text)
        self.assertTrue(10.5 < d['hours_to_expiry'] <= 11.0)

    def test_expired_and_invalid_are_loud(self):
        b = binding(issued=dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=30))
        (self.root / '.campus-os' / 'host-binding.json').write_text(json.dumps(b))
        rc, d, text = self.run_checks()
        self.assertEqual((rc, d['status']), (1, 'expired')); self.assertIn('--issue-binding --client claude-cowork', text)
        (self.root / '.campus-os' / 'host-binding.json').write_text(json.dumps(binding(client='codex')))
        rc, d, text = self.run_checks()
        self.assertEqual((rc, d['status']), (1, 'invalid')); self.assertIn('not the clock owner', d['why'])
        (self.root / '.campus-os' / 'host-binding.json').write_text('{oops')
        rc, d, text = self.run_checks()
        self.assertEqual(d['status'], 'invalid'); self.assertIn('unreadable', d['why'])


class Contract(unittest.TestCase):
    def test_contract_carries_host_binding(self):
        c = json.loads((KERNEL / 'contracts' / 'campus.json').read_text())
        hb = c['seat']['host_binding']
        self.assertEqual(hb['file'], '.campus-os/host-binding.json'); self.assertEqual(hb['ttl_hours_max'], 24)
        self.assertEqual(hb['via_values'], ['observed', 'host-binding', 'unresolved']); self.assertTrue(hb['never_sync'])
        self.assertEqual(c['seat']['resolver'], '.campus-os/resolve-seat.py')
        r = load(); self.assertEqual(r.TTL_MAX_HOURS, hb['ttl_hours_max']); self.assertEqual(r.BINDING_SCHEMA, hb['schema_version'])

    def test_template_and_reference_ship(self):
        plist = (KERNEL / 'templates' / 'host-binding-heartbeat.plist').read_text()
        self.assertIn('--issue-binding', plist); self.assertIn('<integer>21600</integer>', plist)
        self.assertIn('host-side binding', (KERNEL / 'templates' / 'ledger-paths.md').read_text())
        self.assertIn('"via":"host-binding"', (KERNEL / 'templates' / 'ledger-paths.md').read_text())
        self.assertTrue((KERNEL / 'references' / 'host-binding.md').is_file())


if __name__ == '__main__':
    unittest.main()
