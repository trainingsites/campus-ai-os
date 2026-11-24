"""5.3.0: fixes from the first-install field report (2026-11-09). Each test names the report item it guards."""
import json, os, re, subprocess, sys, unittest
from pathlib import Path

KERNEL = Path(os.environ.get('KERNEL_SRC', Path(__file__).resolve().parent.parent)).resolve()
sys.path.append(str(KERNEL / 'tools'))
import kernel_kit  # noqa: E402


def read(rel):
    return (KERNEL / rel).read_text(encoding='utf-8')


class FieldReport530(unittest.TestCase):
    def test_item1_install_docs_lead_with_claude_code_and_no_fixed_menu_path(self):
        for rel in ('README.md', 'QUICKSTART.md'):
            text = read(rel)
            self.assertIn('/plugin marketplace add trainingsites/campus-ai-os', text, rel)
            self.assertNotRegex(text, r'Settings\s*(->|,|→)\s*Plugins', rel)

    def test_item2_security_says_where_the_hash_record_lives(self):
        text = read('SECURITY.md')
        self.assertIn('attached to each GitHub release', text)
        self.assertIn('certutil -hashfile', text)

    def test_item3_coach_pack_ships_and_passes_the_pack_gate(self):
        pack = json.loads(read('packs/coach/pack.json'))
        self.assertEqual(pack['pack'], 'coach')
        self.assertEqual(pack['domain_skills'], [], 'paid coach skills stay out of the free tree')
        p = subprocess.run([sys.executable, '-I', '-B', str(KERNEL / 'tools/build_niche.py'), '--check', '--pack', 'coach'],
                           cwd=KERNEL, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_item4_founding_offers_path_c_and_imports_stay_seeded(self):
        skill = read('skills/campus-start/SKILL.md')
        self.assertNotIn('No third path', skill)
        self.assertIn('/campus-intake', skill)
        interview = read('skills/campus-start/references/interview.md')
        self.assertIn('**C) Start from what you already have', interview)
        self.assertIn('written SEEDED, never DRAFTED', interview)
        intake = read('skills/campus-intake/SKILL.md')
        self.assertIn('**Mark each written file SEEDED**', intake)

    def test_item4_imports_never_send_anything_off_the_machine(self):
        for rel in ('skills/campus-intake/SKILL.md', 'skills/import-ai-memory/SKILL.md'):
            text = read(rel)
            self.assertNotRegex(text, r'(?i)\bPOST\b|trainingsites\.io|/go/register', rel)
            self.assertNotIn('dean/.activity.jsonl', text, rel + ': ledger must resolve by seat')
            self.assertIn('Kernel preamble §4 applies', text, rel)
            self.assertTrue((KERNEL / 'commands' / (Path(rel).parent.name + '.md')).is_file(), rel)

    def test_items5_6_founding_writes_the_seat_and_other_apps_start_as_satellites(self):
        skill = read('skills/campus-start/SKILL.md')
        self.assertIn('## Step 2b - Which AI apps will work here', skill)
        self.assertIn('proposal-only', skill)
        scaffold = read('skills/campus-start/references/scaffold.md')
        self.assertIn('resolve-seat.py --init-seat --primary {client}', scaffold)
        self.assertIn('templates/clients/AGENTS.md', scaffold)
        self.assertNotIn('Not installed by default', read('templates/clients/AGENTS.md'))
        self.assertIn('### 4. Using Codex and Claude on the same campus', read('CODEX-INSTALL.md'))

    def test_item7_task_index_tool_is_founding_copied_and_spec_path_exists_in_a_campus(self):
        self.assertIn('tools/generate_task_index.py', kernel_kit.CORE)
        spec = read('templates/tasks/_SPEC.md')
        self.assertNotRegex(spec, r'python3 tools/generate_task_index\.py')
        self.assertIn('.campus-os/kernel/tools/generate_task_index.py', spec)

    def test_item7_overlapping_triggers_are_narrowed(self):
        registry = read('templates/registry.json')
        self.assertNotIn('"what should I work on"', registry, 'morning-brief owns this phrase')
        self.assertIn('answer directly instead', read('skills/strategy-council/SKILL.md'))
        for rel in ('skills/strategy-council/SKILL.md', 'skills/morning-brief/SKILL.md'):
            self.assertIn('Only inside a campus', read(rel), rel)
        self.assertIn('Campus skill builder', read('skills/skill-creator/SKILL.md'))

    def test_no_hardcoded_command_or_skill_counts_in_codex_install(self):
        self.assertNotRegex(read('CODEX-INSTALL.md'), r'ships \d+ commands|The \d+ skills')

    def test_review_import_path_is_honest_and_seat_aware(self):
        for rel in ('skills/campus-intake/SKILL.md', 'skills/import-ai-memory/SKILL.md'):
            text = read(rel)
            self.assertNotRegex(text, r'(?i)nothing (gets|is) uploaded|leaves the machine', rel)
            self.assertIn('resolve your seat first', text.lower(), rel)
        for rel in ('templates/dean-CLAUDE.md', 'templates/dean-CODEX.md'):
            self.assertIn('may CREATE a new file in\n   `inputs/intake/`', read(rel), rel)

    def test_kit_carries_the_ledger_schema_the_doctor_reads(self):
        self.assertIn('schemas/ledger-line.schema.json', kernel_kit.ON_DEMAND + kernel_kit.CORE)
        schema = json.loads(read('schemas/ledger-line.schema.json'))
        self.assertIn('unresolved', schema['properties']['via']['enum'], 'the resolver also writes via: unresolved')
        for key in ('via', 'run_id', 'tier_used'):
            self.assertIn('null', schema['properties'][key]['type'], key)


if __name__ == '__main__':
    unittest.main()
