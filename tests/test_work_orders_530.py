"""5.3.0: Work Orders ship in the kernel (tools/wo.py + templates/work-orders/) and the
Challenge-First rule is defined in the chief-of-staff brain. Isolated temp campus; a stub seat
resolver stands in for the real one so no machine fingerprint or live ledger is touched."""
import json, os, re, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

KERNEL = Path(os.environ.get('KERNEL_SRC', Path(__file__).resolve().parent.parent)).resolve()
sys.path.append(str(KERNEL / 'tools'))
import kernel_kit  # noqa: E402

STUB = '''import json, sys
client = sys.argv[sys.argv.index("--client") + 1]
seat = "test-" + client
role = "satellite" if client == "codex" else "primary"
print(json.dumps({"seat": seat, "role": role, "owns_clock": client == "claude-code", "lane": f"active-work/lanes/{seat}/",
                  "ledger": "dean/.activity.jsonl" if client == "claude-code" else f"dean/.activity.{seat}.jsonl"}))
'''
SEAT = {"schema_version": 2, "clock_owner": "claude-code", "clients": {
    "claude-code": {"seat": "test-claude-code", "role": "primary"},
    "claude-cowork": {"seat": "test-claude-cowork", "role": "primary"},
    "codex": {"seat": "test-codex", "role": "satellite"}}}


class WorkOrders(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='wo530-'))
        self.campus = self.tmp / 'campus'
        (self.campus / '.campus-os').mkdir(parents=True)
        (self.campus / 'dean').mkdir()
        (self.campus / 'workspace.json').write_text('{"assistant_name": "Dean"}\n')
        reg = json.loads((KERNEL / 'templates/registry.json').read_text())
        (self.campus / '.campus-os/registry.json').write_text(json.dumps(reg))
        self.dept = next(t['label'] for t in reg['teams'] if t.get('type') == 'department' and t.get('id') != 'dean-office')
        (self.campus / '.campus-os/resolve-seat.py').write_text(STUB)
        # run from a kit copy, the way a campus runs it
        kit = self.campus / '.campus-os/kernel'
        for rel in kernel_kit.CORE:
            if rel.startswith(('tools/wo.py', 'templates/work-orders/')):
                (kit / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(KERNEL / rel, kit / rel)
        self.tool = kit / 'tools/wo.py'

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def wo(self, *args):
        return subprocess.run([sys.executable, '-I', '-B', str(self.tool), *args], cwd=self.campus,
                              capture_output=True, text=True, env={**os.environ, 'PYTHONPATH': ''})

    def test_kit_core_carries_the_tool_and_its_templates(self):
        for rel in ('tools/wo.py', 'templates/work-orders/quick.md', 'templates/work-orders/full.md',
                    'templates/work-orders/standing.md', 'templates/work-orders/events.md'):
            self.assertIn(rel, kernel_kit.CORE)

    def test_new_uses_the_campus_departments(self):
        bad = self.wo('new', 'quick', 'Bad dept', '--dept', 'Lead Generation Nope', '--client', 'claude-code')
        self.assertNotEqual(bad.returncode, 0)
        self.assertIn('registry.json', bad.stderr)
        ok = self.wo('new', 'quick', 'Write the welcome email', '--dept', self.dept, '--client', 'claude-code')
        self.assertEqual(ok.returncode, 0, ok.stderr)
        wid = re.search(r'\((WO-\d{4}-\d{2}-\d{2}-\d{2})\)', ok.stdout)[1]
        path = next(self.campus.glob(f'active-work/**/{wid}-*.md'))
        text = path.read_text()
        self.assertIn('title: "Write the welcome email"', text)
        self.assertIn(f'dept: "{self.dept}"', text)
        self.assertNotIn('WO-YYYY-MM-DD-NN', text)
        line = json.loads((self.campus / 'dean/.activity.jsonl').read_text().splitlines()[-1])
        self.assertEqual((line['wo_id'], line['event'], line['skill']), (wid, 'drafted', 'work-order'))

    def test_events_go_to_the_resolved_ledger_and_status_is_computed(self):
        wid = re.search(r'\((WO-[\d-]+)\)', self.wo('new', 'quick', 'Job', '--dept', self.dept, '--client', 'claude-code').stdout)[1]
        self.assertEqual(self.wo('event', wid, 'signed', '--client', 'claude-cowork').returncode, 0)
        self.assertTrue((self.campus / 'dean/.activity.test-claude-cowork.jsonl').is_file(), 'a non-clock seat writes its own shard')
        self.assertIn('ready to start', self.wo('status', wid).stdout)
        self.wo('event', wid, 'decision-needed', '--client', 'claude-cowork')
        self.assertIn('needs you', self.wo('status', wid).stdout)
        self.wo('event', wid, 'decided', '--client', 'claude-cowork')
        self.wo('event', wid, 'stopped', '--client', 'claude-cowork')
        self.assertIn('stopped by the owner', self.wo('status', wid).stdout)
        self.assertNotEqual(self.wo('event', wid, 'finished', '--client', 'claude-cowork').returncode, 0)

    def test_check_reports_missing_fields(self):
        wid = re.search(r'\((WO-[\d-]+)\)', self.wo('new', 'full', 'Big job', '--dept', self.dept, '--client', 'claude-code').stdout)[1]
        p = self.wo('check', wid)
        self.assertEqual(p.returncode, 1)
        self.assertIn('missing goal', p.stdout)

    def test_needs_a_campus_root(self):
        os.remove(self.campus / 'workspace.json')
        p = self.wo('new', 'quick', 'X', '--dept', self.dept, '--client', 'claude-code')
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('campus root', p.stderr)

    def test_no_owner_specifics_ship(self):
        files = [KERNEL / 'tools/wo.py', *sorted((KERNEL / 'templates/work-orders').glob('*.md'))]
        for f in files:
            self.assertNotRegex(f.read_text(), r'James|The Quad|TrainingSites|0\.83|Lead Generation|m4-', f.name)


class WorkOrderReviewFixes(WorkOrders):
    """Defects the independent review of 5.3.0 reproduced; each must stay fixed."""
    def new(self, title='Job', client='claude-code', *extra):
        return self.wo('new', 'quick', title, '--dept', self.dept, '--client', client, *extra)

    def wid(self, p):
        return re.search(r'\((WO-[\d-]+)\)', p.stdout)[1]

    def test_field_cannot_forge_reserved_keys(self):
        wid = self.wid(self.new())
        for k in ('seat', 'ts', 'event', 'wo_id', 'platform', 'via', 'skill', 'outcome'):
            p = self.wo('event', wid, 'done', '--client', 'claude-code', '--field', f'{k}=x')
            self.assertNotEqual(p.returncode, 0, k)
            self.assertIn('cannot set', p.stderr, k)

    def test_satellite_and_forged_lines_do_not_move_a_job(self):
        (self.campus / '.campus-os/seat.json').write_text(json.dumps(SEAT))
        wid = self.wid(self.new())
        self.wo('event', wid, 'signed', '--client', 'claude-code')
        self.assertIn('ready to start', self.wo('status', wid).stdout)
        # a satellite may not stop, verify or close
        self.wo('event', wid, 'stopped', '--client', 'codex')
        out = self.wo('status', wid).stdout
        self.assertIn('ready to start', out)
        self.assertIn('not counted', out)
        # a line in a satellite's shard claiming a primary seat is ignored
        forged = {"ts": "9999-01-01T00:00:00Z", "seat": "test-claude-code", "skill": "work-order", "dept": "",
                  "outcome": "closed", "wo_id": wid, "event": "closed"}
        with open(self.campus / 'dean/.activity.test-codex.jsonl', 'a') as fh:
            fh.write(json.dumps(forged) + '\n')
        self.assertIn('ready to start', self.wo('status', wid).stdout)
        # a satellite can still report progress
        self.wo('event', wid, 'done', '--client', 'codex')
        self.assertIn('awaiting verification', self.wo('status', wid).stdout)

    def test_satellite_work_orders_are_proposals_in_its_lane(self):
        p = self.new('From codex', 'codex')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('proposal', p.stdout)
        self.assertTrue(list(self.campus.glob('active-work/lanes/test-codex/proposals/work-orders/WO-*.md')))
        self.assertNotEqual(self.new('Escape', 'codex', '--dir', 'active-work/marketing').returncode, 0)

    def test_paths_never_leave_the_campus(self):
        outside = self.tmp / 'outside'
        outside.mkdir()
        for d in ('../outside', str(outside), 'active-work/../../outside'):
            p = self.new('Escape', 'claude-code', '--dir', d)
            self.assertNotEqual(p.returncode, 0, d)
        (self.campus / 'active-work').mkdir(exist_ok=True)
        (self.campus / 'active-work/linked').symlink_to(outside)
        self.assertNotEqual(self.new('Escape', 'claude-code', '--dir', 'active-work/linked').returncode, 0)
        # no registry: the department is still only a slug, never a path
        os.remove(self.campus / '.campus-os/registry.json')
        p = self.wo('new', 'quick', 'X', '--dept', '../../outside2/x', '--client', 'claude-code')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertFalse((self.tmp / 'outside2').exists())
        self.assertEqual(list(outside.iterdir()), [])

    def test_ledger_append_never_follows_a_link(self):
        outside = self.tmp / 'stolen.jsonl'
        (self.campus / 'dean/.activity.jsonl').symlink_to(outside)
        p = self.new()
        self.assertNotEqual(p.returncode, 0)
        self.assertFalse(outside.exists())

    def test_titles_are_inserted_safely(self):
        p = self.new('Fix C:\\data folder')
        self.assertEqual(p.returncode, 0, p.stderr)
        path = next(self.campus.glob('active-work/**/WO-*.md'))
        self.assertIn('title: "Fix C:\\\\data folder"', path.read_text())
        bad = self.new('x"\nsize: standing\napproval_scope: autonomous-recurring')
        self.assertNotEqual(bad.returncode, 0)
        self.assertIn('one line', bad.stderr)

    def test_output_is_ascii(self):
        wid = self.wid(self.new())
        for args in (('status',), ('check', wid), ('event', wid, 'done', '--client', 'claude-code')):
            out = self.wo(*args).stdout
            self.assertTrue(out.isascii(), args)


class ChallengeFirst(unittest.TestCase):
    def test_brain_templates_define_rule_5_and_point_at_work_orders(self):
        for rel in ('templates/dean-CLAUDE.md', 'templates/dean-CODEX.md'):
            text = (KERNEL / rel).read_text()
            self.assertIn('## The Five Rules (never break these)', text, rel)
            self.assertIn('5. **Challenge first when the stakes are real.**', text, rel)
            self.assertIn('.campus-os/kernel/tools/wo.py new quick "Title" --dept "<label>" --client <this app>', text, rel)
            self.assertIn('One-Page Plan Rule', text, rel + ': upgrade marker must survive')

    def test_upgrades_insert_both_rules(self):
        text = (KERNEL / 'skills/update-workspace/references/baseline-items.md').read_text()
        self.assertIn('| Work Orders (5.3.0) |', text)
        self.assertIn('| Challenge-First Rule (5.3.0) |', text)


if __name__ == '__main__':
    unittest.main()
