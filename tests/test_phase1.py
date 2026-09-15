"""platform: codex; seat: codex. Isolated CLI regressions; no live-campus inputs."""
import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path
KERNEL = Path(os.environ.get('KERNEL_SRC', Path(__file__).resolve().parent.parent)).resolve()
SOURCE = KERNEL
TODAY = '2026-09-05'
class Evidence(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='campus-phase1-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()/'campus'; self.root.mkdir()
        self.put('workspace.json', '{}')
        self.put('AGENTS.md', 'Read `dean/AGENTS.md` first.\n')
        self.put('dean/AGENTS.md', 'Read `dean/CLAUDE.md` first.\n')
        self.put('dean/CLAUDE.md', '# Dean\n## Start of Session\n1. Read `dean/memory.md`.\n')
        self.put('dean/memory.md', '# Memory\n')
    def put(self, name, text):
        p=self.root/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(text.encode()); return p
    def cli(self, tool, *args, stdin=None):
        runtime='node' if tool.endswith('.mjs') else sys.executable
        return subprocess.run([runtime,str(SOURCE/'tools'/tool),*map(str,args)],input=stdin,text=True,capture_output=True,cwd=self.root,timeout=15)
    def weight(self,*args):
        p=self.cli('context-weight.mjs','--root',self.root,'--entry','AGENTS.md','--today',TODAY,'--json',*args)
        return p,json.loads(p.stdout)
    def seat(self,raw):
        if raw is not None:self.put('.campus-os/seat.json',raw)
        p=self.cli('seat_contract_checks.py','--campus-root',self.root,'--json'); return p,json.loads(p.stdout)
    def cron(self,raw):
        p=self.cli('check_cron_parity.py','--scheduled',self.root/'scheduled','--json',stdin=raw); return p,json.loads(p.stdout)
    def prune(self,*args):
        p=self.cli('context-prune.mjs','--root',self.root,'--today',TODAY,'--json',*args); return p,json.loads(p.stdout)
    def test_invalid_seat(self):
        p,x=self.seat('{broken'); self.assertNotEqual(p.returncode,0); self.assertEqual(x['seat_resolution']['status'],'invalid')
    def test_seat_shapes(self):
        for raw in ('[]','null','{}','{"seat":"x","role":"boss"}','{"seat":"../x","role":"primary"}'):
            with self.subTest(raw=raw):
                p,x=self.seat(raw); self.assertNotEqual(p.returncode,0); self.assertEqual(x['seat_resolution']['status'],'invalid')
    def test_missing_seat_unknown(self):
        p,x=self.seat(None); self.assertNotEqual(p.returncode,0); self.assertEqual(x['seat_resolution']['status'],'missing')
    def test_satellite_unresolved(self):
        p,x=self.seat('{"seat":"other","role":"satellite"}'); self.assertNotEqual(p.returncode,0); self.assertEqual(x['foreign_writes']['status'],'unresolved')
    def test_healthy_primary(self):
        self.put('dean/.activity.jsonl','{"seat":"current"}\n')
        p,x=self.seat('{"seat":"current","role":"primary"}'); self.assertEqual(p.returncode,0)
    def test_history_unresolved(self):
        f=self.put('dean/.activity.jsonl','{"seat":"old","date":"2020-01-01"}\n'); before=f.read_bytes()
        p,x=self.seat('{"seat":"current","role":"primary"}')
        self.assertEqual(x['foreign_writes']['foreign'],[]); self.assertTrue(x['foreign_writes']['unresolved']); self.assertEqual(f.read_bytes(),before)
    def test_bad_ledger_not_clean(self):
        self.put('dean/.activity.jsonl','not json\n[]\n')
        p,x=self.seat('{"seat":"current","role":"primary"}'); self.assertNotEqual(p.returncode,0); self.assertTrue(x['seat_stamps']['errors'])
    def test_wrong_shard(self):
        self.put('dean/.activity.other.jsonl','{"seat":"current"}\n'); p,x=self.seat('{"seat":"current","role":"primary"}'); self.assertEqual(p.returncode,1)
    def test_scheduler_error(self):
        p,x=self.cron('{"error":"permission denied"}'); self.assertEqual(p.returncode,2); self.assertEqual(x['scheduler']['status'],'invalid')
    def test_scheduler_no_input(self):
        p,x=self.cron(''); self.assertEqual(p.returncode,2); self.assertEqual(x['scheduler']['status'],'unknown')
    def test_scheduler_unavailable(self):
        p,x=self.cron('{"capability":"unavailable","retrieval":"not_attempted"}'); self.assertEqual(p.returncode,0); self.assertEqual(x['scheduler']['status'],'unavailable')
    def test_scheduler_failed(self):
        p,x=self.cron('{"capability":"available","retrieval":"failed","error":"denied"}'); self.assertEqual(p.returncode,2); self.assertEqual(x['scheduler']['status'],'failed')
    def test_scheduler_empty_compares(self):
        self.put('scheduled/job.md','taskId: job\ncronExpression: 0 7 * * *\n')
        p,x=self.cron('[]'); self.assertEqual(p.returncode,1); self.assertEqual(x['canonical_only'],['job']); self.assertEqual(x['scheduler']['status'],'empty')
    def test_scheduler_empty_no_convention(self):
        p,x=self.cron('[]'); self.assertEqual(p.returncode,0); self.assertEqual(x['scheduler']['status'],'empty'); self.assertFalse(x['parity_applicable'])
    def test_scheduler_malformed_jobs(self):
        for raw in ('[null]','[{"id":"x","cronExpression":3}]','[{"id":"x","enabled":"false","cronExpression":"0 7 * * *"}]','{"tasks":[],"error":"denied"}'):
            with self.subTest(raw=raw):
                p,x=self.cron(raw); self.assertEqual(p.returncode,2)
    def test_recursive_entry(self):
        self.put('dean/memory.md','x'*80000); p,x=self.weight(); self.assertGreaterEqual(x['total_tokens'],20000); self.assertEqual(x['resolution']['status'],'complete')
    def test_cycle_incomplete(self):
        self.put('dean/CLAUDE.md','Read `AGENTS.md` first.\n'); p,x=self.weight(); self.assertEqual(p.returncode,3); self.assertEqual(x['band'],'UNKNOWN'); self.assertIn('ENTRY_CYCLE',[f['code'] for f in x['resolution']['findings']])
    def test_missing_redirect(self):
        self.put('dean/AGENTS.md','Read `missing/CLAUDE.md`.\n'); p,x=self.weight(); self.assertEqual(p.returncode,3); self.assertEqual(x['band'],'UNKNOWN')
    def test_missing_read(self):
        self.put('dean/CLAUDE.md','## Start of Session\nRead `dean/absent.md`.\n'); p,x=self.weight(); self.assertEqual(p.returncode,3)
    def test_root_has_startup(self):
        self.put('AGENTS.md','## Start of Session\nRead `dean/memory.md`.\n'); self.put('dean/memory.md','x'*400); p,x=self.weight(); self.assertTrue(any(f.get('path')==str(self.root/'dean/memory.md') for f in x['files']))
    def test_declared_empty(self):
        self.put('workspace.json','{"startup_reads":[]}'); p,x=self.weight(); self.assertFalse(any(f['role'].startswith('startup read') for f in x['files']))
    def test_canon_precedence_and_fallback(self):
        self.put('workspace.json','{"startup_reads":["shared/audience.md"]}'); self.put('shared/audience.md','alias'); self.put('shared/icp.md','canonical'*100)
        p,x=self.weight(); self.assertTrue(any(f.get('path')==str(self.root/'shared/icp.md') for f in x['files'])); self.assertFalse(any(f.get('path')==str(self.root/'shared/audience.md') for f in x['files']))
    def test_optional_then_mandatory(self):
        self.put('dean/CLAUDE.md','## Start of Session\n1. Read `dean/memory.md` only if needed.\n2. Always read `dean/memory.md`.\n'); p,x=self.weight(); self.assertTrue(any(f.get('path')==str(self.root/'dean/memory.md') for f in x['files']))
    def test_prune_policy_excluded(self):
        self.put('dean/CLAUDE.md','## Start of Session\nRead `dean/memory.md`.\n## Preferences\n- STANDING RULE (2020-01-01): Never publish without approval.\n- 2020-01-01 [archive-eligible] [pinned] Keep this.\n')
        p,x=self.prune(); self.assertEqual(x['files'],[])
    def test_prune_requires_optin(self):
        self.put('dean/memory.md','- 2020-01-01 old decision, no archival authorization.\n'); p,x=self.prune(); self.assertEqual(x['files'],[])
    def test_prune_preserve_bytes(self):
        content='# Memory\r\n\r\n- 2020-01-01 [archive-eligible] completed event.\r\n  detail é\r\n\r\n- Current policy.\r\n'
        f=self.put('dean/memory.md',content); p,x=self.prune(); self.assertEqual(p.returncode,1); self.assertEqual(f.read_bytes(),content.encode()); self.assertFalse((self.root/'dean/archive').exists())
        p,x=self.prune('--apply'); self.assertEqual(p.returncode,0,p.stdout+p.stderr); self.assertIn(b'\r\n\r\n- Current policy.\r\n',f.read_bytes()); archive=self.root/x['files'][0]['archive']; self.assertIn('completed event.\r\n  detail é\r\n'.encode(),archive.read_bytes())
    def test_prune_failure_preserves_source(self):
        f=self.put('dean/memory.md','- 2020-01-01 [archive-eligible] completed.\n'); before=f.read_bytes(); (self.root/'dean/archive/2026-09-memory.md').mkdir(parents=True)
        p,x=self.prune('--apply'); self.assertEqual(p.returncode,2); self.assertEqual(f.read_bytes(),before)
    def test_generated_refused(self):
        self.put('dean/memory.md','# GENERATED Memory\n- 2020-01-01 [archive-eligible] completed.\n'); p,x=self.prune(); self.assertEqual(x['files'],[]); self.assertTrue(x['refused'])
    def test_prune_symlink_escape(self):
        outside=Path(self.tmp.name)/'outside.md'; outside.write_text('- 2020-01-01 [archive-eligible] outside.\n'); f=self.root/'dean/memory.md'; f.unlink(); f.symlink_to(outside); before=outside.read_bytes(); p,x=self.prune('--apply'); self.assertEqual(outside.read_bytes(),before); self.assertTrue(x['refused'] or x.get('errors'))
    def test_healthy_bands(self):
        for size,band,code in ((400,'GREEN',0),(100000,'AMBER',1),(200000,'RED',2)):
            with self.subTest(band=band):
                self.put('dean/memory.md','x'*size); p,x=self.weight(); self.assertEqual(x['band'],band); self.assertEqual(p.returncode,code)
    def test_declared_without_chief(self):
        self.put('AGENTS.md','# Campus\n'); self.put('workspace.json','{"startup_reads":["dean/memory.md"]}')
        p,x=self.weight(); self.assertEqual(p.returncode,0)
    def test_canon_local_override(self):
        self.put('.campus-os/context-files.md','| Audience | `people.md` | `audience.md` |\n'); self.put('shared/people.md','local'); self.put('shared/icp.md','template'); self.put('workspace.json','{"startup_reads":["shared/audience.md"]}')
        p,x=self.weight(); self.assertTrue(any(f.get('path')==str(self.root/'shared/people.md') for f in x['files']))
    def test_workspace_invalid(self):
        for raw in ('null','[]','{broken','{"startup_reads":false}'):
            with self.subTest(raw=raw):
                self.put('workspace.json',raw); p,x=self.weight(); self.assertEqual(p.returncode,3)
    def test_optional_missing_complete(self):
        self.put('dean/CLAUDE.md','## Start of Session\nRead `missing.md` only if needed.\n'); p,x=self.weight(); self.assertEqual(p.returncode,0); self.assertTrue(x['missing'][0]['optional'])
    def test_prune_pinned_section(self):
        self.put('dean/memory.md','## [pinned] Decisions\n- 2020-01-01 [archive-eligible] still active.\n'); p,x=self.prune(); self.assertEqual(x['files'],[])
    def test_prune_internal_symlink(self):
        self.put('dean/real.md','- 2020-01-01 [archive-eligible] protected.\n'); f=self.root/'dean/memory.md'; f.unlink(); f.symlink_to(self.root/'dean/real.md'); before=(self.root/'dean/real.md').read_bytes()
        p,x=self.prune('--apply'); self.assertEqual((self.root/'dean/real.md').read_bytes(),before); self.assertTrue(x['refused'])
    def test_prune_archive_escape(self):
        self.put('dean/memory.md','- 2020-01-01 [archive-eligible] completed.\n'); outside=Path(self.tmp.name)/'archive'; outside.mkdir(); (self.root/'dean/archive').symlink_to(outside,target_is_directory=True); before=(self.root/'dean/memory.md').read_bytes()
        p,x=self.prune('--apply'); self.assertEqual(p.returncode,2); self.assertEqual(list(outside.iterdir()),[]); self.assertEqual((self.root/'dean/memory.md').read_bytes(),before)
    def test_prune_stale_plan_refused(self):
        helper=SOURCE/'tools/prune-write.mjs'
        self.assertTrue(helper.is_file())
        f=self.put('dean/memory.md','original\n')
        script="""import fs from 'node:fs'; import {applyPlan} from HELPER;
const root=process.argv[1], abs=root+'/dean/memory.md';
const plan={abs,archive:'dean/archive/test.md',original:'original\\n',replacement:'replacement\\n',archiveText:'original\\n',moved:['original\\n']};
fs.writeFileSync(abs,'new owner edit\\n'); console.log(JSON.stringify(applyPlan(root,plan)));""".replace('HELPER',json.dumps(helper.as_uri()))
        p=subprocess.run(['node','--input-type=module','-e',script,str(self.root)],text=True,capture_output=True,timeout=15)
        self.assertEqual(p.returncode,0,p.stderr); self.assertFalse(json.loads(p.stdout)['ok']); self.assertEqual(f.read_text(),'new owner edit\n'); self.assertFalse((self.root/'dean/archive').exists())
    def test_scheduler_populated_and_drift(self):
        self.put('scheduled/job.md','taskId: job\ncronExpression: 0 7 * * *\n')
        # Disabled fixtures have no dependence on wall-clock health heuristics.
        for cron,code in (('0 7 * * *',0),('0 8 * * *',1)):
            p,x=self.cron(json.dumps({'capability':'available','retrieval':'success','tasks':[{'id':'job','cronExpression':cron,'enabled':False}]})); self.assertEqual(p.returncode,code); self.assertEqual(x['scheduler']['status'],'populated')
    def test_scheduler_file_missing_json(self):
        p=self.cli('check_cron_parity.py','--json','--live',self.root/'absent.json'); self.assertEqual(p.returncode,2); self.assertEqual(json.loads(p.stdout)['scheduler']['status'],'invalid')
    def test_prune_idempotent(self):
        self.put('dean/memory.md','- 2020-01-01 [archive-eligible] completed.\n'); p,x=self.prune('--apply'); self.assertEqual(p.returncode,0); before=(self.root/'dean/archive/2026-09-memory.md').read_bytes(); p,x=self.prune('--apply'); self.assertEqual(x['files'],[]); self.assertEqual((self.root/'dean/archive/2026-09-memory.md').read_bytes(),before)
    def test_startup_entry_expansion(self):
        self.put('AGENTS.md','## Start of Session\nRead `dean/AGENTS.md`.\n'); self.put('dean/memory.md','x'*80000); p,x=self.weight(); self.assertGreaterEqual(x['total_tokens'],20000); self.assertEqual(x['resolution']['status'],'complete')
    # --- merge-seat additions (m4-claude-code, 2026-09-07): regressions found reviewing the Codex candidate ---
    def test_backreference_not_a_failure(self):
        # "Read root AGENTS.md once" from the chief-of-staff file points back up the chain it came from.
        # Every file on the loop is counted once; the measurement is complete (this campus's real shape).
        self.put('dean/CLAUDE.md','# Dean\n## Start of Session\n1. Read root `AGENTS.md` once.\n2. Read `dean/memory.md`.\n')
        p,x=self.weight(); self.assertEqual(p.returncode,0,p.stdout); self.assertEqual(x['resolution']['status'],'complete')
        self.assertIn('ENTRY_CYCLE',[f['code'] for f in x['resolution']['findings']])
    def test_conditional_read_is_optional(self):
        # The shipped template says: "If `daily/{today}.md` exists, skim it." A fresh campus has no daily note yet.
        self.put('dean/CLAUDE.md','## Start of Session\n1. Read `dean/memory.md`.\n2. If `daily/{today}.md` exists, skim it.\n')
        p,x=self.weight(); self.assertEqual(p.returncode,0,p.stdout); self.assertEqual(x['band'],'GREEN'); self.assertTrue(x['missing'] and (x['missing'][0].get('conditional') or x['missing'][0]['optional']))  # follow-up: absent conditional read is 'conditional', not 'optional'
    def test_declared_rolling_read_absent(self):
        self.put('workspace.json','{"startup_reads":["dean/memory.md","daily/{today}.md"]}')
        p,x=self.weight(); self.assertEqual(p.returncode,0,p.stdout); self.assertEqual(x['resolution']['status'],'complete')
        self.assertTrue(any(m['ref']=='daily/'+TODAY+'.md' and m.get('rolling') for m in x['missing']))
    def test_required_read_still_incomplete(self):
        # The strict path must survive the two relaxations above.
        self.put('dean/CLAUDE.md','## Start of Session\n1. Read `dean/memory.md`.\n2. Read `dean/absent.md`.\n')
        p,x=self.weight(); self.assertEqual(p.returncode,3); self.assertEqual(x['band'],'UNKNOWN')
    def test_seat_missing_line_not_clean(self):
        p=self.cli('seat_contract_checks.py','--campus-root',self.root); self.assertNotEqual(p.returncode,0)
        self.assertIn('[--] Seat identity not declared',p.stdout); self.assertNotIn('[OK] Every seat wrote inside its own lane',p.stdout)
    def test_conditional_read_counted_when_present(self):
        # follow-up (found on the Cowork post-upgrade doctor, 2026-09-07): a conditional read is counted when the file exists
        self.put('dean/CLAUDE.md','## Start of Session\n1. Read `dean/memory.md`.\n2. If `daily/{today}.md` exists, skim it.\n')
        self.put('daily/'+TODAY+'.md','y'*4000)
        p,x=self.weight(); self.assertEqual(p.returncode,0,p.stdout); self.assertTrue(any(f.get('path')==str(self.root/('daily/'+TODAY+'.md')) for f in x['files'])); self.assertGreaterEqual(x['total_tokens'],1000)
if __name__=='__main__':unittest.main(verbosity=2)
