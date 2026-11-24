"""5.3.5: edition record + edition check, seat file on update, Antigravity named as a client.

Field reports (2026-11): a Windows campus updated from 5.2.x still had no seat file; an owner
added Antigravity and nothing told it which name to resolve under; a coach build installed over
an education campus relabelled it with no warning because the campus recorded no edition.
"""
import os
import unittest
from pathlib import Path

KERNEL = Path(os.environ.get("KERNEL_SRC") or Path(__file__).resolve().parents[1])


def read(rel):
    return (KERNEL / rel).read_text(encoding="utf-8")


class EditionRecord(unittest.TestCase):
    def test_founding_writes_the_pack_key(self):
        self.assertIn("`pack` = the plugin's `active_pack`", read("skills/campus-start/SKILL.md"))
        scaffold = read("skills/campus-start/references/scaffold.md")
        self.assertIn("- `pack` - the id of the edition this campus was founded with", scaffold)
        self.assertIn("never a literal", scaffold)

    def test_update_checks_the_edition_before_any_write(self):
        skill = read("skills/update-workspace/SKILL.md")
        self.assertIn("Edition check - first, before any route below and before item 18", skill)
        self.assertLess(skill.index("Edition check"), skill.index("- **No markers:**"))
        self.assertIn("after the Step 0 edition check and the Step 3 snapshot, before item 11", skill)
        self.assertIn("after the Step 0 edition check", read("skills/update-workspace/references/additions.md"))
        self.assertIn("items 11-18", read("skills/update-workspace/references/baseline-items.md"))
        self.assertIn("zero writes", skill)

    def test_readers_of_the_active_pack_defer_to_the_campus_edition(self):
        for rel in ("skills/wiki-ingest/SKILL.md", "skills/wiki-query/SKILL.md", "skills/campus-first-win/SKILL.md"):
            self.assertIn("Edition guard (5.3.5)", read(rel), rel)

    def test_roster_tool_refuses_to_relabel_another_edition(self):
        import json, shutil, subprocess, sys, tempfile
        tool = str(KERNEL / "tools" / "gen_department_entries.py")
        with tempfile.TemporaryDirectory() as d:
            campus = Path(d)
            (campus / ".campus-os").mkdir()
            shutil.copy(KERNEL / "templates" / "registry.json", campus / ".campus-os" / "registry.json")
            before = (campus / ".campus-os" / "registry.json").read_bytes()
            (campus / "workspace.json").write_text(json.dumps({"version": "5.3.4", "pack": "some-other-edition"}))
            p = subprocess.run([sys.executable, "-B", tool, "--campus", str(campus)], capture_output=True, text=True)
            self.assertEqual(p.returncode, 3, p.stdout + p.stderr)
            self.assertIn("REFUSED", p.stdout)
            self.assertEqual((campus / ".campus-os" / "registry.json").read_bytes(), before)
            active = json.loads((KERNEL / "packs" / "active.json").read_text())["active_pack"]
            (campus / "workspace.json").write_text(json.dumps({"version": "5.3.4", "pack": active}))
            p = subprocess.run([sys.executable, "-B", tool, "--campus", str(campus)], capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_additions_define_every_edition_case(self):
        block = read("skills/update-workspace/references/additions.md").split(
            "## v5.3.5 additions")[1].split("## 18 - Kernel kit")[0]
        for phrase in ("packs/active.json", "`pack` absent:",
                       "the labels differ, or cannot be read",
                       "Never assume an edition from the version number", "stop with zero writes",
                       "Never change an existing value", "start a new empty folder"):
            self.assertIn(phrase, block)

    def test_no_edition_id_is_hardcoded_as_the_installed_one(self):
        # the check must read active.json; the only literal is the pre-5.3.5 default
        block = read("skills/update-workspace/references/additions.md").split("## v5.3.5 additions")[1]
        self.assertNotIn("coach", block.split("## 18 - Kernel kit")[0].replace("education, coach and others", ""))


class SeatFileOnUpdate(unittest.TestCase):
    def test_item_17_names_the_seat_step_and_stays_reachable(self):
        skill = read("skills/update-workspace/SKILL.md")
        self.assertIn("write the seat file when the campus has none", skill)
        self.assertIn("11-18", skill)

    def test_seat_step_never_overwrites_and_never_guesses(self):
        block = read("skills/update-workspace/references/additions.md").split("## v5.3.5 additions")[1]
        for phrase in ("--init-seat --primary {client}", "An existing `seat.json` is never rewritten",
                       "Never guess an app", "`not observed`", "python3 -I -B", "`--clock-owner`",
                       "Which one has been your main app here", "`py -3`", "lowercase with hyphens",
                       "this skill never edits `seat.json`"):
            self.assertIn(phrase, block)


class AntigravityClient(unittest.TestCase):
    def test_adapters_tell_antigravity_to_resolve_as_itself(self):
        for rel in ("templates/clients/AGENTS.md", "templates/clients/GEMINI.md"):
            text = read(rel)
            self.assertIn("--client antigravity", text, rel)
        self.assertIn("Never resolve under another app's name", read("templates/clients/AGENTS.md"))
        self.assertIn("never as Gemini", read("templates/clients/GEMINI.md"))

    def test_founding_names_antigravity_and_installs_its_entry_files(self):
        self.assertIn("Antigravity", read("skills/campus-start/references/interview.md"))
        scaffold = read("skills/campus-start/references/scaffold.md")
        self.assertIn("**Antigravity named:**", scaffold)
        self.assertIn("templates/clients/GEMINI.md", scaffold)

    def test_resolver_gives_a_named_satellite_its_own_lane_and_shard(self):
        import importlib.util, json, tempfile
        spec = importlib.util.spec_from_file_location("resolve_seat", KERNEL / "tools" / "resolve-seat.py")
        r = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(r)
        seat, reason = r.init_seat("f" * 64, ["claude-code"], satellites=["antigravity"], machine="desk",
                                   platform="win32")
        self.assertIsNone(reason)
        self.assertEqual(seat["clients"]["antigravity"]["seat"], "desk-antigravity")
        self.assertEqual(seat["clients"]["antigravity"]["role"], "satellite")
        self.assertEqual(seat["clients"]["claude-code"]["role"], "primary")
        self.assertEqual(seat["machine_id_scheme"], "sha256:win32-machineguid-lowercase")
        json.dumps(seat)




class JobCards(unittest.TestCase):
    def test_founding_copies_cards_only_when_the_pack_ships_them(self):
        s = read("skills/campus-start/references/scaffold.md")
        self.assertIn("packs/{active_pack}/job-cards.md", s)
        self.assertIn("only when that file is absent", s)
        self.assertIn("never invent cards", s)
        self.assertIn('copy it\nto `dean/job-cards.md` when absent (`scaffold.md` -> "Job cards")', read("skills/campus-start/SKILL.md"))
        self.assertIn("<!-- campus-os:job-cards -->", read("skills/update-workspace/references/additions.md"))

    def test_fresh_folder_is_not_asked_about_editions(self):
        self.assertIn("Only\nwhen a campus marker exists", read("skills/update-workspace/SKILL.md"))
        self.assertIn("departments the pack does not list are ignored", read("skills/update-workspace/references/additions.md"))

    def test_first_win_and_both_entry_templates_read_a_card_on_demand(self):
        self.assertIn("If `dean/job-cards.md` exists, the first win is the first card", read("skills/campus-first-win/SKILL.md"))
        for rel in ("templates/dean-CLAUDE.md", "templates/dean-CODEX.md"):
            t = read(rel)
            self.assertIn("dean/job-cards.md", t, rel)
            self.assertIn("Nothing on it starts by\n   itself", t, rel)

    def test_update_never_overwrites_the_owners_cards(self):
        block = read("skills/update-workspace/references/additions.md").split("## v5.3.5 additions")[1]
        self.assertIn("never overwrite, merge or reorder it", block)
        self.assertIn("an entry file that already mentions the file is left alone", block)

    @unittest.skipUnless((KERNEL / "packs" / "active.json").is_file() and
                         '"education"' in (KERNEL / "packs" / "active.json").read_text(),
                         "an assembled paid edition carries its own cards by design")
    def test_the_public_kernel_ships_no_cards_of_its_own(self):
        self.assertEqual(sorted(p.name for p in (KERNEL / "packs").glob("*/job-cards.md")), [])



class FirstRunFixes537(unittest.TestCase):
    def _resolver(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("resolve_seat", KERNEL / "tools" / "resolve-seat.py")
        r = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(r)
        return r

    def test_first_seat_write_makes_no_temp_file_and_never_overwrites(self):
        import tempfile
        r = self._resolver()
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "seat.json"
            self.assertIsNone(r.write_file(target, '{"a": 1}', overwrite=False))
            self.assertEqual(sorted(p.name for p in Path(d).iterdir()), ["seat.json"])
            self.assertEqual(target.read_text(encoding="utf-8"), '{"a": 1}')
            self.assertIn("already exists", r.write_file(target, '{"a": 2}', overwrite=False))
            self.assertEqual(target.read_text(encoding="utf-8"), '{"a": 1}')
            self.assertIsNone(r.write_file(target, '{"a": 3}', overwrite=True))
            self.assertEqual(sorted(p.name for p in Path(d).iterdir()), ["seat.json"])
            self.assertEqual(target.read_text(encoding="utf-8"), '{"a": 3}')
            fresh = Path(d) / "host-binding.json"          # overwrite=True on a file that is not there yet
            self.assertIsNone(r.write_file(fresh, "{}", overwrite=True))
            self.assertEqual(sorted(p.name for p in Path(d).iterdir()), ["host-binding.json", "seat.json"])

    def test_first_seat_write_refuses_a_link(self):
        import os, tempfile
        r = self._resolver()
        with tempfile.TemporaryDirectory() as d:
            outside = Path(d) / "outside.json"
            link = Path(d) / "seat.json"
            try:
                os.symlink(outside, link)
            except (OSError, NotImplementedError):
                self.skipTest("no symlinks here")
            self.assertIn("refused", r.write_file(link, "{}", overwrite=False))
            self.assertFalse(outside.exists())

    def test_setup_options_are_shown_even_with_an_answers_file(self):
        self.assertIn("do not\nskip this beat: show all three options", read("skills/campus-start/SKILL.md"))

    def test_cards_file_may_hold_playbooks_and_the_chief_of_staff_knows(self):
        for rel in ("templates/dean-CLAUDE.md", "templates/dean-CODEX.md"):
            flat = read(rel).replace("\n   ", " ")
            self.assertIn("These playbooks are not registered playbooks", flat, rel)
            self.assertIn("do any job a card covers by that card", flat, rel)
        self.assertIn("not a card: never start the first win from it", read("skills/campus-first-win/SKILL.md"))
        self.assertIn("may end with playbooks", read("skills/campus-start/references/scaffold.md"))



class UpdateSafety538(unittest.TestCase):
    """5.3.8: second confirm before an edition switch, explicit-mode org-chart tool, update undo."""

    def test_second_confirm_needs_a_typed_word(self):
        block = read("skills/update-workspace/references/additions.md")
        for phrase in ("Second confirm (5.3.8)", "Type RENAME to go ahead", "Only the word RENAME carries on",
                       "Never offer RENAME as a button", "never a version number"):
            self.assertIn(phrase, block, phrase)
        self.assertIn('part b, "Second confirm"', read("skills/update-workspace/SKILL.md"))

    def test_org_chart_tool_writes_only_with_an_explicit_mode(self):
        import shutil, subprocess, sys, tempfile
        with tempfile.TemporaryDirectory() as d:
            tree = Path(d) / "plugin"
            shutil.copytree(KERNEL, tree, ignore=shutil.ignore_patterns("tests", "__pycache__", ".git"))
            reg = tree / "templates" / "registry.json"
            before = reg.read_bytes()
            tool = str(tree / "tools" / "gen_department_entries.py")
            for args, code in (([], 2), (["--help"], 0), (["-h"], 0), (["--bogus"], 2), (["--campus"], 2),
                               (["--pack"], 2), (["--campus", "--check"], 2)):
                p = subprocess.run([sys.executable, "-B", tool] + args, capture_output=True, text=True)
                self.assertEqual(p.returncode, code, (args, p.stdout, p.stderr))
                self.assertEqual(reg.read_bytes(), before, args)
                self.assertIn("Usage:", p.stdout, args)

    def _campus(self, d):
        import json, shutil
        campus = Path(d) / "campus"
        (campus / ".campus-os").mkdir(parents=True)
        (campus / "dean").mkdir()
        (campus / "workspace.json").write_text(json.dumps({"version": "5.2.11"}))
        shutil.copy(KERNEL / "templates" / "registry.json", campus / ".campus-os" / "registry.json")
        (campus / "dean" / "CLAUDE.md").write_text("owner entry\n")
        (campus / "dean" / "memory.md").write_text("owner memory\n")
        (campus / "dean" / ".activity.jsonl").write_text("{}\n")
        return campus

    def _seal(self, campus):
        name = sorted(p.name for p in (campus / "dean" / "archive" / "update-undo").iterdir())[-1]
        p = self._run("seal", "--campus-root", str(campus), "--snapshot", name)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return name

    def _run(self, *args):
        import subprocess, sys
        return subprocess.run([sys.executable, "-I", "-B", str(KERNEL / "tools" / "update_undo.py")] + list(args),
                              capture_output=True, text=True)

    def test_undo_puts_a_wrong_edition_update_back(self):
        import json, tempfile
        with tempfile.TemporaryDirectory() as d:
            campus = self._campus(d)
            reg_before = (campus / ".campus-os" / "registry.json").read_bytes()
            p = self._run("snapshot", "--campus-root", str(campus))
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            # what a wrong-edition update writes
            (campus / "workspace.json").write_text(json.dumps({"version": "5.3.8", "pack": "coach"}))
            (campus / ".campus-os" / "registry.json").write_text("{}")
            (campus / ".campus-os" / "kernel").mkdir()
            (campus / ".campus-os" / "kernel" / "KIT.json").write_text("{}")
            (campus / ".campus-os" / "seat.json").write_text("{}")
            (campus / "dean" / "job-cards.md").write_text("cards")
            (campus / "dean" / "CLAUDE.md").write_text("owner entry\ninserted block\n")
            (campus / "dean" / "memory.md").write_text("owner memory\nlater note\n")
            p = self._run("undo", "--campus-root", str(campus), "--keep", ".campus-os/seat.json")
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertEqual(json.loads((campus / "workspace.json").read_text()), {"version": "5.2.11"})
            self.assertEqual((campus / ".campus-os" / "registry.json").read_bytes(), reg_before)
            self.assertEqual((campus / "dean" / "CLAUDE.md").read_text(), "owner entry\n")
            self.assertFalse((campus / ".campus-os" / "kernel").exists())
            self.assertFalse((campus / "dean" / "job-cards.md").exists())
            self.assertTrue((campus / ".campus-os" / "seat.json").exists())
            # owner files are never restored, and nothing is deleted
            self.assertIn("later note", (campus / "dean" / "memory.md").read_text())
            self.assertIn("NOT restored", p.stdout)
            snap = next((campus / "dean" / "archive" / "update-undo").iterdir())
            self.assertEqual((snap / "after" / "dean" / "job-cards.md").read_text(), "cards")
            self.assertTrue((snap / "after" / ".campus-os" / "kernel" / "KIT.json").is_file())
            self.assertEqual((snap / "before" / "dean" / ".activity.jsonl").read_text(), "{}\n")
            again = self._run("undo", "--campus-root", str(campus))
            self.assertEqual(again.returncode, 1)
            self.assertIn("NOTHING TO UNDO", again.stdout)

    def test_undo_refuses_links_and_tampered_copies(self):
        import os, tempfile
        with tempfile.TemporaryDirectory() as d:
            campus = self._campus(d)
            self.assertEqual(self._run("snapshot", "--campus-root", str(campus)).returncode, 0)
            snap = next((campus / "dean" / "archive" / "update-undo").iterdir())
            (campus / "workspace.json").write_text("{}")
            (snap / "before" / "workspace.json").write_text("planted")
            p = self._run("undo", "--campus-root", str(campus))
            self.assertEqual(p.returncode, 1)
            self.assertIn("missing or was changed", p.stdout)
            self.assertEqual((campus / "workspace.json").read_text(), "{}")
        with tempfile.TemporaryDirectory() as d:
            campus = self._campus(d)
            outside = Path(d) / "outside.md"
            outside.write_text("keep")
            try:
                os.symlink(outside, campus / "AGENTS.md")
            except (OSError, NotImplementedError):
                self.skipTest("links not available here")
            p = self._run("snapshot", "--campus-root", str(campus))
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)   # a linked entry file is left alone
            self.assertIn("left alone (a link): AGENTS.md", p.stdout)
            (campus / "workspace.json").write_text("{}")
            snap = next((campus / "dean" / "archive" / "update-undo").iterdir())
            os.symlink(Path(d), snap / "after")                       # a planted link out of the campus
            p = self._run("undo", "--campus-root", str(campus))
            self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
            self.assertIn("is a link", p.stdout)
            self.assertEqual((campus / "workspace.json").read_text(), "{}")
            self.assertEqual(outside.read_text(), "keep")

    def test_undo_never_reverts_what_the_owner_changed(self):
        import json, tempfile
        with tempfile.TemporaryDirectory() as d:
            campus = self._campus(d)
            (campus / "dean" / "job-cards.md").write_text("my cards\n")
            (campus / ".campus-os" / "seat.json").write_text("{}")
            self.assertEqual(self._run("snapshot", "--campus-root", str(campus)).returncode, 0)
            # the update: version stamp, an insert into the entry file, a folder
            (campus / "workspace.json").write_text(json.dumps({"version": "5.3.8"}))
            (campus / "dean" / "CLAUDE.md").write_text("owner entry\ninserted\n")
            (campus / "dean" / "skill-candidates").mkdir()
            (campus / "atlas").mkdir(); (campus / "atlas" / "config").mkdir()
            self._seal(campus)
            # afterwards the owner works
            (campus / "dean" / "job-cards.md").write_text("my cards\nmy new card\n")
            (campus / ".campus-os" / "seat.json").write_text('{"added": true}')
            (campus / "dean" / "CLAUDE.md").write_text("owner entry\ninserted\nmy new rule\n")
            (campus / "atlas" / "config" / "mine.md").write_text("mine")
            dry = self._run("undo", "--campus-root", str(campus), "--dry-run")
            self.assertEqual(dry.returncode, 0, dry.stdout + dry.stderr)
            self.assertIn("DRY RUN", dry.stdout)
            self.assertEqual(json.loads((campus / "workspace.json").read_text()), {"version": "5.3.8"})
            p = self._run("undo", "--campus-root", str(campus))
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertEqual((campus / "dean" / "job-cards.md").read_text(), "my cards\nmy new card\n")
            self.assertEqual((campus / ".campus-os" / "seat.json").read_text(), '{"added": true}')
            self.assertTrue((campus / "atlas" / "config" / "mine.md").is_file())
            self.assertFalse((campus / "dean" / "skill-candidates").exists())
            self.assertIn("CHANGED AFTER THE UPDATE", p.stdout)
            self.assertIn("dean/CLAUDE.md", p.stdout.split("CHANGED AFTER THE UPDATE")[1])
            snap = next((campus / "dean" / "archive" / "update-undo").iterdir())
            self.assertIn("my new rule", (snap / "after" / "dean" / "CLAUDE.md").read_text())

    def test_an_update_that_changed_nothing_is_never_undone_over_later_edits(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            campus = self._campus(d)
            self.assertEqual(self._run("snapshot", "--campus-root", str(campus)).returncode, 0)
            self._seal(campus)
            (campus / "dean" / "CLAUDE.md").write_text("owner entry\nedited a week later\n")
            (campus / "workspace.json").write_text('{"version": "5.2.11", "note": "mine"}')
            p = self._run("undo", "--campus-root", str(campus))
            self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
            self.assertIn("NOTHING TO UNDO", p.stdout)
            self.assertIn("edited a week later", (campus / "dean" / "CLAUDE.md").read_text())
            self.assertIn("mine", (campus / "workspace.json").read_text())

    def test_a_damaged_record_does_not_block_the_one_before_it(self):
        import json, tempfile, time
        with tempfile.TemporaryDirectory() as d:
            campus = self._campus(d)
            self.assertEqual(self._run("snapshot", "--campus-root", str(campus)).returncode, 0)
            (campus / "workspace.json").write_text(json.dumps({"version": "5.3.8"}))
            time.sleep(1.1)
            self.assertEqual(self._run("snapshot", "--campus-root", str(campus)).returncode, 0)
            newest = sorted((campus / "dean" / "archive" / "update-undo").iterdir())[-1]
            (newest / "UNDO.json").write_text("{ not json")
            older = sorted((campus / "dean" / "archive" / "update-undo").iterdir())[0].name
            p = self._run("undo", "--campus-root", str(campus))
            self.assertEqual(p.returncode, 1, p.stdout + p.stderr)   # never silently the update before the last
            self.assertIn("this is not the last update", p.stdout)
            self.assertEqual(json.loads((campus / "workspace.json").read_text()), {"version": "5.3.8"})
            p = self._run("undo", "--campus-root", str(campus), "--snapshot", older)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertEqual(json.loads((campus / "workspace.json").read_text()), {"version": "5.2.11"})

    def test_undo_acts_on_the_last_update_only_and_puts_the_old_kit_back(self):
        import json, tempfile, time
        with tempfile.TemporaryDirectory() as d:
            campus = self._campus(d)
            (campus / ".campus-os" / "kernel").mkdir()
            (campus / ".campus-os" / "kernel" / "KIT.json").write_text('{"kernel_version": "5.2.11"}')
            (campus / ".campus-os" / "kernel" / "tool.py").write_text("old")
            # update 1: a real upgrade
            self.assertEqual(self._run("snapshot", "--campus-root", str(campus)).returncode, 0)
            (campus / "workspace.json").write_text(json.dumps({"version": "5.3.8"}))
            (campus / ".campus-os" / "kernel" / "KIT.json").write_text('{"kernel_version": "5.3.8"}')
            (campus / ".campus-os" / "kernel" / "tool.py").write_text("new")
            self._seal(campus)
            time.sleep(1.1)
            # update 2: an up-to-date run that only wrote the seat file
            self.assertEqual(self._run("snapshot", "--campus-root", str(campus)).returncode, 0)
            (campus / ".campus-os" / "seat.json").write_text("{}")
            self._seal(campus)
            # a seal without this run's name, or on the older snapshot, is refused
            self.assertEqual(self._run("seal", "--campus-root", str(campus)).returncode, 1)
            # keeping the seat file leaves the last update with nothing to undo: it must NOT walk back
            p = self._run("undo", "--campus-root", str(campus), "--keep", ".campus-os/seat.json")
            self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
            self.assertIn("NOTHING TO UNDO", p.stdout)
            self.assertIn("run undo again", p.stdout)
            self.assertEqual(json.loads((campus / "workspace.json").read_text()), {"version": "5.3.8"})
            # asked again, it goes back one more, and the old kit returns
            p = self._run("undo", "--campus-root", str(campus))
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertEqual(json.loads((campus / "workspace.json").read_text()), {"version": "5.2.11"})
            self.assertEqual((campus / ".campus-os" / "kernel" / "tool.py").read_text(), "old")
            self.assertIn("5.2.11", (campus / ".campus-os" / "kernel" / "KIT.json").read_text())
            self.assertTrue((campus / ".campus-os" / "seat.json").is_file())

    def test_org_chart_tool_refuses_an_unknown_pack_and_an_unconfirmed_rename(self):
        import json, shutil, subprocess, sys, tempfile
        with tempfile.TemporaryDirectory() as d:
            tree = Path(d) / "plugin"
            shutil.copytree(KERNEL, tree, ignore=shutil.ignore_patterns("tests", "__pycache__", ".git"))
            tool = str(tree / "tools" / "gen_department_entries.py")
            reg = tree / "templates" / "registry.json"
            before = reg.read_bytes()
            p = subprocess.run([sys.executable, "-B", tool, "--pack", "no-such-pack"], capture_output=True, text=True)
            self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
            self.assertEqual(reg.read_bytes(), before)
            # a campus that records no edition, with several department names that would change
            campus = Path(d) / "campus"
            (campus / ".campus-os").mkdir(parents=True)
            (campus / "workspace.json").write_text(json.dumps({"version": "5.2.11"}))
            data = json.loads(before)
            n = 0
            for t in data["teams"]:
                if t.get("type") == "department" and t.get("team") != "dean-office":
                    t["label"] = "Other edition %d" % n
                    n += 1
            self.assertGreater(n, 1)
            (campus / ".campus-os" / "registry.json").write_text(json.dumps(data))
            held = (campus / ".campus-os" / "registry.json").read_bytes()
            p = subprocess.run([sys.executable, "-B", tool, "--campus", str(campus)], capture_output=True, text=True)
            self.assertEqual(p.returncode, 3, p.stdout + p.stderr)
            self.assertIn("type RENAME", p.stdout)
            self.assertEqual((campus / ".campus-os" / "registry.json").read_bytes(), held)
            p = subprocess.run([sys.executable, "-B", tool, "--campus", str(campus), "--confirm-rename", "yes"],
                               capture_output=True, text=True)
            self.assertEqual(p.returncode, 3)
            p = subprocess.run([sys.executable, "-B", tool, "--campus", str(campus), "--confirm-rename", "RENAME"],
                               capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            # one differing name is an owner's own rename: no gate
            data = json.loads(before)
            next(t for t in data["teams"] if t.get("type") == "department")["label"] = "My own name"
            (campus / ".campus-os" / "registry.json").write_text(json.dumps(data))
            p = subprocess.run([sys.executable, "-B", tool, "--campus", str(campus)], capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_update_skill_takes_the_snapshot_and_offers_the_undo(self):
        skill = read("skills/update-workspace/SKILL.md")
        flat = " ".join(skill.split())
        self.assertIn("tools/update_undo.py snapshot --campus-root", flat)
        self.assertIn("`seal`", flat)
        self.assertIn("undo the last update", skill)
        # the undo route is read before the edition check, so a swapped edition cannot block it
        self.assertLess(skill.index('"Undo the last update":'), skill.index("Edition check"))
        self.assertIn("after the Step 0 edition check and the Step 3 snapshot", flat)
        self.assertIn("Steps 1-3 first", flat)
        adds = read("skills/update-workspace/references/additions.md")
        for phrase in ("## Undo (5.3.8, every update)", "this is the only job of the run", "Wait for an explicit go",
                       "--keep .campus-os/seat.json", "did NOT restore", "--dry-run", "do not run the edition check",
                       "STOPPED PARTWAY", "--confirm-rename RENAME", "--snapshot {NAME}",
                       "never go back further on your own", "The two runs always carry the same arguments"):
            self.assertIn(phrase, adds, phrase)


    def test_entry_templates_name_no_pack_and_never_count_cards(self):
        for rel in ("templates/dean-CLAUDE.md", "templates/dean-CODEX.md"):
            t = read(rel)
            flat = " ".join(t.split())
            self.assertNotIn("this build ships the Education pack", t, rel)
            self.assertIn("`packs/active.json` names the one this build ships", flat, rel)
            self.assertIn("Call a card by its name. Never say how many cards there are", flat, rel)

    def test_quickstart_covers_prompts_and_updating(self):
        q = read("QUICKSTART.md")
        for phrase in ("Claude Code will ask before it runs a command", "## Updating a campus you already use",
                       "undo the last update", "a different edition belongs in a new empty folder"):
            self.assertIn(phrase, q, phrase)

if __name__ == "__main__":
    unittest.main()
