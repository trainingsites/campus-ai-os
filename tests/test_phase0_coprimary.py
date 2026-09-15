"""Co-primary seat model (Phase 0, 2026-09-11). Isolated fixtures; nothing here reads a live campus.

Every client assigned on one installation may resolve `primary`; exactly one is the `clock_owner`,
which alone runs schedules, holds the host binding, and writes the shared ledger. The security
boundary is unchanged: an unknown fingerprint, an unassigned client, or a sandbox without a valid
binding is still a satellite.

platform: claude-code; seat: m4-claude-code
"""
import importlib.util, json, os, subprocess, sys, tempfile, unittest
import datetime as dt
from pathlib import Path

KERNEL = Path(os.environ.get('KERNEL_SRC', Path(__file__).resolve().parent.parent)).resolve()
RESOLVER = KERNEL / 'tools' / 'resolve-seat.py'
CHECKS = KERNEL / 'tools' / 'seat_contract_checks.py'
NOW = dt.datetime(2026, 9, 11, 15, 0, tzinfo=dt.timezone.utc)
MID = 'a' * 64

CO_PRIMARY = {
    'schema_version': 2, 'seat': 'owner', 'role': 'primary', 'client': 'claude-cowork',
    'machine_id': MID, 'clock_owner': 'claude-cowork',
    'clients': {'claude-cowork': {'seat': 'owner', 'role': 'primary'},
                'codex': {'seat': 'codex', 'role': 'primary'},
                'claude-code': {'seat': 'host-code', 'role': 'primary'}},
}
LEGACY = {
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


def binding(client='claude-cowork', mid=MID, issued=NOW - dt.timedelta(hours=1), ttl=12):
    return {'schema_version': 1, 'client': client, 'machine_id': mid,
            'issued_at': ts(issued), 'expires_at': ts(issued + dt.timedelta(hours=ttl)), 'issued_by': 'fixture'}


def cfg_without(key):
    c = json.loads(json.dumps(CO_PRIMARY)); c.pop(key); return c


class Resolve(unittest.TestCase):
    def setUp(self):
        self.r = load()

    def test_every_assigned_client_is_primary(self):
        for client, seat in (('claude-cowork', 'owner'), ('codex', 'codex'), ('claude-code', 'host-code')):
            out = self.r.resolve(CO_PRIMARY, client, MID, None, NOW)
            self.assertEqual((out['role'], out['seat']), ('primary', seat), client)

    def test_only_the_clock_owner_owns_the_clock_and_shared_ledger(self):
        owner = self.r.resolve(CO_PRIMARY, 'claude-cowork', MID, None, NOW)
        self.assertTrue(owner['owns_clock'])
        self.assertEqual(owner['ledger'], 'dean/.activity.jsonl')
        for client, seat in (('codex', 'codex'), ('claude-code', 'host-code')):
            out = self.r.resolve(CO_PRIMARY, client, MID, None, NOW)
            self.assertFalse(out['owns_clock'], client)
            self.assertEqual(out['ledger'], f'dean/.activity.{seat}.jsonl', client)

    def test_lane_is_always_the_seats_own(self):
        out = self.r.resolve(CO_PRIMARY, 'codex', MID, None, NOW)
        self.assertEqual(out['lane'], 'active-work/lanes/codex/')

    # --- the boundary that must not move -------------------------------------------------
    def test_unassigned_client_is_still_satellite(self):
        out = self.r.resolve(CO_PRIMARY, 'chatgpt-desktop', MID, None, NOW)
        self.assertEqual(out['role'], 'satellite'); self.assertIn('not assigned', out['reason'])

    def test_foreign_machine_is_still_satellite(self):
        out = self.r.resolve(CO_PRIMARY, 'codex', 'b' * 64, None, NOW)
        self.assertEqual(out['role'], 'satellite'); self.assertIn('does not match', out['reason'])

    def test_sandbox_without_binding_is_still_satellite(self):
        out = self.r.resolve(CO_PRIMARY, 'claude-cowork', None, None, NOW)
        self.assertEqual((out['role'], out['via']), ('satellite', 'unresolved'))

    def test_binding_only_works_for_the_clock_owner(self):
        ok = self.r.resolve(CO_PRIMARY, 'claude-cowork', None, binding(), NOW)
        self.assertEqual((ok['role'], ok['via'], ok['owns_clock']), ('primary', 'host-binding', True))
        # a co-primary that is NOT the clock owner cannot buy primary with a binding
        no = self.r.resolve(CO_PRIMARY, 'codex', None, binding(client='codex'), NOW)
        self.assertEqual(no['role'], 'satellite')

    def test_expired_binding_still_denies(self):
        stale = binding(issued=NOW - dt.timedelta(hours=30))
        out = self.r.resolve(CO_PRIMARY, 'claude-cowork', None, stale, NOW)
        self.assertEqual(out['role'], 'satellite')

    # --- configuration integrity ---------------------------------------------------------
    def test_co_primary_without_clock_owner_is_refused(self):
        out = self.r.resolve(cfg_without('clock_owner'), 'claude-cowork', MID, None, NOW)
        self.assertEqual(out['role'], 'satellite'); self.assertIn('clock_owner', out['reason'])

    def test_clock_owner_must_name_a_primary_client(self):
        bad = json.loads(json.dumps(CO_PRIMARY)); bad['clock_owner'] = 'nobody'
        out = self.r.resolve(bad, 'claude-cowork', MID, None, NOW)
        self.assertEqual(out['role'], 'satellite')

    def test_no_primary_at_all_is_refused(self):
        bad = json.loads(json.dumps(CO_PRIMARY))
        for v in bad['clients'].values():
            v['role'] = 'satellite'
        out = self.r.resolve(bad, 'claude-cowork', MID, None, NOW)
        self.assertEqual(out['role'], 'satellite'); self.assertIn('at least one primary', out['reason'])

    def test_legacy_single_primary_config_is_unchanged(self):
        owner = self.r.resolve(LEGACY, 'claude-cowork', MID, None, NOW)
        self.assertEqual((owner['role'], owner['owns_clock'], owner['ledger']),
                         ('primary', True, 'dean/.activity.jsonl'))
        sat = self.r.resolve(LEGACY, 'codex', MID, None, NOW)
        self.assertEqual((sat['role'], sat['ledger']), ('satellite', 'dean/.activity.codex.jsonl'))


class DoctorCoPrimary(unittest.TestCase):
    """The doctor must not call a co-primary's legitimate write unresolved attribution,
    and must not tell the owner to delete a valid host binding."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / '.campus-os').mkdir(parents=True)
        (self.root / 'dean' / 'tasks').mkdir(parents=True)
        (self.root / '.campus-os' / 'seat.json').write_text(json.dumps(CO_PRIMARY))
        # The doctor reads the wall clock, not the frozen NOW, so the fixture binding
        # must be issued relative to real time or it silently expires days later (5.2.9).
        self.live = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)
        (self.root / '.campus-os' / 'host-binding.json').write_text(json.dumps(binding(issued=self.live)))

    def tearDown(self):
        self.tmp.cleanup()

    def run_checks(self):
        p = subprocess.run([sys.executable, str(CHECKS), '--campus-root', str(self.root), '--json'],
                           capture_output=True, text=True)
        return p, json.loads(p.stdout)

    def test_binding_for_clock_owner_is_accepted(self):
        _, d = self.run_checks()
        self.assertEqual(d['host_binding']['status'], 'fresh', d['host_binding'].get('why'))

    def test_binding_for_a_non_clock_owner_is_rejected_clearly(self):
        (self.root / '.campus-os' / 'host-binding.json').write_text(json.dumps(binding(client='codex', issued=self.live)))
        _, d = self.run_checks()
        self.assertEqual(d['host_binding']['status'], 'invalid')
        self.assertIn('not the clock owner', d['host_binding']['why'])

    def test_co_primary_seat_stamp_is_not_flagged(self):
        (self.root / 'dean' / 'tasks' / 't1.md').write_text('---\nplatform: codex\nseat: codex\n---\nwork\n')
        _, d = self.run_checks()
        flagged = [u for u in d['foreign_writes']['unresolved'] if u.get('seat') == 'codex']
        self.assertEqual(flagged, [], 'a co-primary seat write must not read as unresolved attribution')

    def test_unknown_seat_stamp_is_still_flagged(self):
        (self.root / 'dean' / 'tasks' / 't2.md').write_text('---\nplatform: other\nseat: stranger\n---\nwork\n')
        _, d = self.run_checks()
        flagged = [u for u in d['foreign_writes']['unresolved'] if u.get('seat') == 'stranger']
        self.assertTrue(flagged, 'an unrecognised seat must still be reported')

    def test_malformed_seat_json_does_not_crash(self):
        for raw in ('[]', 'null', '{oops'):
            (self.root / '.campus-os' / 'seat.json').write_text(raw)
            p, _ = self.run_checks()
            self.assertNotEqual(p.returncode, 0, raw)
            self.assertTrue(p.stdout.strip().startswith('{'), f'must still emit JSON for {raw!r}')


if __name__ == '__main__':
    unittest.main()
