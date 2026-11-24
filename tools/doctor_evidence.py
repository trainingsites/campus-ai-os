#!/usr/bin/env python3
"""Deterministic, read-only doctor evidence over the existing campus tools.
platform: codex; seat: codex
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import tempfile

# Kit copies run from .campus-os/kernel/tools, a folder other campus writers can reach (Codex audit F1,
# 5.2.14). Sibling modules are found at the END of the path, so a planted file can never shadow the
# standard library, and Python's bytecode cache points at an unguessable path that does not exist,
# so a planted __pycache__ is never read and nothing is written into the kit. Run as `python3 -I -B`.
NO_CACHE = os.path.join(tempfile.gettempdir(), f"campus-os-nocache-{os.getpid()}-{os.urandom(8).hex()}")
if __name__ == "__main__":  # only when run as a tool; an importing program keeps its own settings
    sys.dont_write_bytecode = True
    sys.pycache_prefix = NO_CACHE
sys.path.append(str(Path(__file__).resolve().parent))
from contract import Resolver, ContractError  # noqa: E402
import kernel_kit  # noqa: E402
import validate_ledger  # noqa: E402

KERNEL = Path(__file__).resolve().parent.parent
# Sub-tools run isolated (no script folder or env on the path), write no bytecode, read none from the kit.
PY_ISOLATED = ['-I', '-B', '-X', f'pycache_prefix={NO_CACHE}']
ORDER = ('workspace', 'version_lockstep', 'kernel_kit', 'registry', 'context_weight', 'results_ledgers',
         'schedules', 'seat_contract', 'fleet_sweep', 'staff', 'context_files', 'stale_work', 'ledger', 'runtime_drift')
# 5.3.7: one clear line when this computer's Python cannot start isolated (a broken install), so the
# sub-tool sections it blocks do not read as campus faults.
PREFLIGHT_LINE = ('Python on this computer cannot start in isolated mode - repair or reinstall Python. '
                  'This is the computer, not your campus')
PREFIX = {'ok': '[OK]', 'opportunity': '[--]', 'needs-decision': '[!!]', 'skipped': '[--]', 'error': '[!!]'}


def section(status, text, **detail):
    return {'status': status, 'detail': detail, 'line': f'{PREFIX[status]} {text}'}


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def stamp(value):
    if not isinstance(value, str):
        raise ValueError('timestamp must be an ISO string')
    parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    return parsed.replace(tzinfo=dt.timezone.utc) if parsed.tzinfo is None else parsed.astimezone(dt.timezone.utc)


class SubtoolError(Exception):
    def __init__(self, name, rc, stderr, stdout=''):
        self.detail = {'tool': name, 'exit_code': rc, 'stderr_tail': stderr[-2000:], 'stdout_tail': stdout[-2000:]}
        super().__init__(f'{name} could not produce usable evidence (exit {rc})')


class Evidence:
    def __init__(self, root, today, window=None, scheduled=None, sweep=False, installed=None, kit_manifest=None, runtime_dirs=()):
        self.root, self.today, self.window = root, today, window
        self.installed, self.kit_manifest = installed or (kit_manifest or {}).get('kernel_version'), kit_manifest
        self.runtime_dirs = list(runtime_dirs or ())
        self.asof = dt.datetime.combine(today, dt.time(), dt.timezone.utc)
        self.scheduled, self.sweep = scheduled, sweep
        self.contract = Resolver()
        self.env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', CAMPUS_ROOT=str(root))
        self.python, self.isolated, self.current, self.blocked = sys.executable, None, None, set()

    def python_isolated(self):
        """Can this interpreter start with -I at all? Checked once, before any sub-tool."""
        if self.isolated is None:
            try:
                p = subprocess.run([self.python, *PY_ISOLATED, '-c', 'import encodings'], env=self.env,
                                   text=True, capture_output=True, timeout=30)
                self.isolated = {'ok': p.returncode == 0, 'exit_code': p.returncode, 'stderr_tail': p.stderr[-2000:]}
            except (OSError, subprocess.TimeoutExpired) as exc:
                self.isolated = {'ok': False, 'exit_code': None, 'stderr_tail': str(exc)[-2000:]}
        return self.isolated

    def tool(self, name, *args, accepted=(0,), stdin='', command=None):
        runtime = shutil.which('node') if name.endswith('.mjs') else self.python
        isolate = [] if name.endswith('.mjs') else PY_ISOLATED
        argv = command or [runtime, *isolate, str(KERNEL / 'tools' / name), *map(str, args)]
        if argv[0] == self.python and '-I' in argv[1:4] and not self.python_isolated()['ok']:
            self.blocked.add(self.current)
            raise SubtoolError(name, self.isolated['exit_code'], self.isolated['stderr_tail'])
        try:
            p = subprocess.run(argv, cwd=self.root, env=self.env, input=stdin,
                               text=True, capture_output=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise SubtoolError(name, None, str(exc)) from exc
        if p.returncode not in accepted:
            raise SubtoolError(name, p.returncode, p.stderr, p.stdout)
        try:
            data = json.loads(p.stdout)
            if not isinstance(data, dict):
                raise ValueError('expected a JSON object')
        except ValueError as exc:
            raise SubtoolError(name, p.returncode, p.stderr, p.stdout) from exc
        return data, p.returncode

    def registry_data(self):
        data = read_json(self.root / '.campus-os/registry.json')
        if not isinstance(data, dict) or not isinstance(data.get('teams'), list):
            raise ValueError('registry must be an object with teams[]')
        return data

    def workspace(self):
        path = self.root / 'workspace.json'
        if not path.is_file():
            return section('needs-decision', 'Workspace is not founded: workspace.json missing', version=None, entries=[])
        data = read_json(path)
        if not isinstance(data, dict):
            raise ValueError('workspace.json must be an object')
        entries = [n for n in self.contract.entry_file('')['read_names'] if (self.root / n).is_file()]
        good = bool(entries and isinstance(data.get('version'), str) and data['version'])
        return section('ok' if good else 'needs-decision',
                       'Workspace and entry file present' if good else 'Workspace version or root entry file is missing',
                       version=data.get('version'), entries=entries)

    def version_lockstep(self):
        workspace = read_json(self.root / 'workspace.json').get('version')
        registry = self.registry_data().get('campus_os_version')
        # The running tool's tree is the installed artifact. Campus markers are
        # read from --campus-root; probe order is supplied by its contract.
        candidates = self.contract.data['hosts']['manifest_candidates']
        manifest = next((KERNEL / rel for rel in candidates if (KERNEL / rel).is_file()), None)
        if manifest is None:
            return section('error', 'Installed manifest cannot be resolved', candidates=candidates)
        installed = self.installed or read_json(manifest).get('version')
        good = isinstance(installed, str) and bool(installed) and workspace == registry == installed
        return section('ok' if good else 'needs-decision',
                       f'Version current (v{installed}) - workspace, registry and installed plugin agree' if good else
                       f'Version homes disagree: workspace {workspace} / registry {registry} / installed {installed}',
                       workspace=workspace, registry=registry, installed=installed, manifest=str(manifest))

    def kernel_kit(self):
        # The campus copy of the kernel tools (.campus-os/kernel/, tools/kernel_kit.py). The expected
        # hashes and version come from the INSTALLED PLUGIN's kit manifest - this tree's when this tool
        # runs from the plugin, else --kit-manifest - never from the campus stamp alone: anyone who can
        # edit a kit file can edit KIT.json too.
        from_kit = KERNEL.resolve() == (self.root / kernel_kit.KIT_DIR).resolve()
        manifest = self.kit_manifest
        if manifest is None and not from_kit and (KERNEL / kernel_kit.MANIFEST).is_file():
            manifest = read_json(KERNEL / kernel_kit.MANIFEST)
        installed = self.installed or (manifest or {}).get('kernel_version') or \
            (None if from_kit else kernel_kit.kernel_version(KERNEL))
        r = kernel_kit.check(self.root, installed, tier='core', manifest=manifest)
        detail = {k: r[k] for k in ('present', 'anchor', 'kernel_version', 'installed_version', 'version',
                                    'missing', 'mismatched', 'unexpected', 'stamp_invalid')}
        if not r['present']:
            return section('opportunity', 'Kernel kit not in the campus yet - /update-workspace copies it', **detail)
        if r['stamp_invalid']:
            return section('needs-decision', 'Kernel kit stamp is unreadable - do not run it; /update-workspace '
                           're-copies the kit', **detail)
        if r['unexpected']:
            return section('needs-decision', f"Kernel kit holds {len(r['unexpected'])} file(s) the plugin does not "
                           "list - do not run it; /update-workspace moves them to .campus-os/kernel-quarantine/ "
                           "and re-checks", **detail)
        if r['missing'] or r['mismatched']:
            return section('needs-decision', f"Kernel kit damaged or changed: {len(r['missing'])} missing, "
                           f"{len(r['mismatched'])} changed - do not run it; /update-workspace re-copies it", **detail)
        if r['version'] == 'stale':
            return section('needs-decision', f"Kernel kit is v{r['kernel_version']}, plugin is v{installed} - "
                           "/update-workspace refreshes it", **detail)
        if r['version'] == 'newer':
            return section('needs-decision', f"Kernel kit says v{r['kernel_version']}, newer than the plugin "
                           f"(v{installed}) - do not run it; update the plugin, or repair the kit if the owner "
                           "says that stamp is wrong", **detail)
        if manifest is None:
            return section('opportunity', 'Kernel kit matches its own stamp only - pass --kit-manifest (the '
                           "plugin's tools/kit-manifest.json) to check it against the installed plugin", **detail)
        return section('ok', f"Kernel kit current (v{r['kernel_version']}), every file present matches the plugin "
                       "and nothing else is in it", **detail)

    def registry(self):
        states = {}
        failures = []
        for key, tool, extra in [('validation', 'validate_registry.py', []),
                                 ('materialization', 'materialize_registration_spec.py', ['--check'])]:
            try:
                data, rc = self.tool(tool, '--campus-root', self.root, *extra, '--json', accepted=(0, 1))
                if key == 'validation':
                    states[key] = {'entries': data['entries'], 'counts': data['counts'],
                                   'failing': len(data['failures'])}
                    if rc or data['failures']:
                        failures.append({'tool': tool, 'exit_code': rc, 'stderr_tail': '',
                                         'failures': data['failures']})
                else:
                    states[key] = data
            except SubtoolError as exc:
                failures.append(exc.detail)
        if failures:
            return section('error', 'Registry checks found errors', **states, errors=failures)
        current = states['materialization']['state'] == 'current'
        return section('ok' if current else 'needs-decision',
                       f"Registry: {states['validation']['entries']} entries; spec {states['materialization']['state']}", **states)

    def context_weight(self):
        if not shutil.which('node'):
            return section('skipped', 'Context weight skipped: Node is unavailable', reason='node-unavailable')
        args = ['--root', self.root, '--today', self.today.isoformat(), '--json']
        if self.window is not None:
            args += ['--window', self.window]
        data, rc = self.tool('context-weight.mjs', *args, accepted=(0, 1, 2))
        data.pop('date', None)  # the as-of date has one home: generated.today
        status = {0: 'ok', 1: 'opportunity', 2: 'needs-decision'}[rc]
        return section(status, f"Startup reads {data['total_tokens']} tokens ({data['band']})", **data)

    def results_ledgers(self):
        try:
            data, rc = self.tool('validate_results.py', '--campus-root', self.root, '--json', accepted=(0, 1))
        except SubtoolError as exc:
            if exc.detail['exit_code'] == 2 and 'no files given' in exc.detail['stderr_tail']:
                return section('skipped', 'No results ledgers found', files=0, counts={}, failing=0)
            raise
        return section('error' if rc else 'ok', f"Results ledgers: {data['files']} files, {data['failing']} failing",
                       files=data['files'], counts=data['counts'], failing=data['failing'])

    def schedules(self):
        if self.scheduled is None:
            return section('skipped', 'Schedule check skipped: no live task list supplied', reason='no-live-task-list')
        # The existing CLI has no --today. Inject its public health helper's
        # supported `now` parameter, then call its unchanged CLI for all logic.
        code = ('import sys, datetime as dt; sys.path.append(sys.argv[1]); '
                'import check_cron_parity as tool; original = tool.assess_health; '
                'now = dt.datetime.fromisoformat(sys.argv[2]); '
                'tool.assess_health = lambda live: original(live, now=now); '
                'sys.argv = [tool.__file__, "--scheduled", sys.argv[3], "--json"]; '
                'raise SystemExit(tool.main())')
        command = [self.python, *PY_ISOLATED, '-c', code, str(KERNEL / 'tools'), self.asof.isoformat(), str(self.root / 'scheduled')]
        data, rc = self.tool('check_cron_parity.py', command=command, stdin=self.scheduled, accepted=(0, 1))
        if data['scheduler']['status'] == 'unavailable':
            return section('skipped', 'Scheduler unavailable on this host', **data)
        health = data['health'] or {}
        return section('needs-decision' if rc else 'opportunity' if data.get('live_only') or health.get('never_run') else 'ok',
                       f"Schedules: {health.get('total', 0)} recurring, {len(health.get('stalled', []))} stalled", **data)

    def seat_contract(self):
        data, rc = self.tool('seat_contract_checks.py', '--campus-root', self.root, '--json', accepted=(0, 1))
        foreign = len(data['foreign_writes'].get('foreign', []))
        stamps = len(data['seat_stamps'].get('findings', []))
        hazards = data['sync_hazards'].get('conflicted_total', 0) + data['sync_hazards'].get('placeholders_total', 0)
        # A campus with no seat.json is the ordinary solo case (evidence-sections: `missing` -> [--]);
        # only invalid / satellite / findings are red. Found on the 5.2.4 cold-install run, 2026-09-09.
        solo = data['seat_resolution']['status'] == 'missing' and not (foreign or stamps or hazards
                                                                        or data['seat_stamps'].get('errors')
                                                                        or data.get('host_binding', {}).get('status') in ('expired', 'invalid'))
        return section('opportunity' if solo else 'needs-decision' if rc else 'ok',
                       f"Seat contract: {data['seat_resolution']['status']}; {foreign} foreign writes, "
                       f"{stamps} stamp findings, {hazards} sync-file hazards", **data)

    def fleet_sweep(self):
        foundry = self.root / 'library/teams/_foundry'
        if not (self.sweep or self.today.day <= 3):
            return section('skipped', 'Fleet sweep skipped: outside monthly window', reason='outside-monthly-window')
        if not (foundry / 'bin/validate-team').is_file():
            return section('skipped', 'Fleet sweep skipped: Foundry unavailable', reason='foundry-unavailable')
        rows = []
        for team in sorted(foundry.parent.iterdir()):
            if not team.is_dir() or team.name.startswith('_') or team.is_symlink():
                continue
            try:
                data, rc = self.tool('validate-team', command=[sys.executable, str(foundry / 'bin/validate-team'),
                                      str(team), '--campus', str(self.root), '--json'], accepted=(0, 2))
                rows.append({'team': team.name, 'pass': data['pass'], 'fails': data['fails'], 'warns': data['warns']})
            except SubtoolError as exc:
                rows.append({'team': team.name, 'error': exc.detail})
        broken = sum(not row.get('pass', False) for row in rows)
        return section('error' if any('error' in row for row in rows) else 'needs-decision' if broken else 'ok',
                       f'Fleet sweep: {len(rows)} teams, {broken} need attention', teams=rows, failing=broken)

    def staff(self):
        registry = self.registry_data()
        entries = registry['teams']
        if any(not isinstance(e, dict) for e in entries):
            raise ValueError('registry teams[] contains a non-object')
        def active(e):
            return self.contract.normalize_status(e.get('status', 'active'))['canonical'] == 'active'
        def kind(e):
            return self.contract.normalize_type(e.get('type', ''))['canonical']
        def department(e):
            value = e.get('department') or e.get('team') or ''
            return self.contract.resolve_department(value)['canonical'] or value
        def names(e, *keys):
            found = set()
            for key in keys:
                for item in e.get(key, []) or []:
                    name = item if isinstance(item, str) else item.get('name') or item.get('skill') or item.get('team')
                    if name:
                        found.add(name)
            return found
        rosters, labels, systems, inactive = {}, {}, set(), set()
        for e in entries:
            if not active(e):
                inactive.add(e.get('team'))
                continue
            if kind(e) == 'department':
                dep = department(e)
                labels[dep] = e.get('label') or dep.replace('-', ' ').title()
                rosters.setdefault(dep, set()).update(names(e, 'employees', 'employees_added'))
            elif kind(e) == 'systems':
                systems.update(names(e, 'systems', 'systems_added'))
        orphans = []
        for e in entries:
            if not active(e) or kind(e) in ('department', 'systems', 'kernel'):
                continue
            dep = department(e)
            if dep not in rosters:
                orphans.append({'team': e.get('team'), 'department': dep})
            elif e.get('team'):
                rosters[dep].add(e['team'])
        rows, seen, duplicates = [], set(), []
        for dep, nameset in rosters.items():
            nameset -= inactive
            duplicates += sorted(nameset & seen)
            unique = nameset - seen
            seen.update(unique)
            rows.append({'department': dep, 'label': labels[dep], 'count': len(unique), 'employees': sorted(unique)})
        playbooks = registry.get('playbooks', []) or []
        return section('needs-decision' if orphans or duplicates else 'ok',
                       f'Your staff: {len(seen)} employees + {len(systems)} campus systems + {len(playbooks)} playbooks',
                       employees=len(seen), campus_systems=len(systems), playbooks=len(playbooks),
                       departments=rows, orphans=orphans, duplicate_memberships=duplicates)

    def context_files(self):
        """5.2.12: a concept held in two files (e.g. a thin icp.md a team wrote beside the
        audience.md founding wrote). Reads resolve to the first in read order; the owner merges."""
        base = self.root / 'shared'
        if not base.is_dir():
            return section('skipped', 'Context files check skipped: shared/ is absent', reason='directory-absent')
        # Only the shadow pair: the file founding wrote AND a separate canonical-name copy.
        # Offers (summary + long-form notes) and voice-inside-brand are intended pairs, not doubles.
        actual = {e.name.lower(): e.name for e in base.iterdir() if e.is_file()}
        doubles = []
        for row in self.contract.files:
            founding, canonical = row.get('founding_writes'), row['canonical']
            if not founding or founding == canonical or row.get('canonical_wins'):
                continue
            if founding.lower() in actual and canonical.lower() in actual:
                doubles.append({'concept': row['concept'], 'read': actual[founding.lower()],
                                'also': [actual[canonical.lower()]]})
        return section('opportunity' if doubles else 'ok',
                       f'Context files: {len(doubles)} concept(s) held in more than one file',
                       count=len(doubles), concepts=doubles)

    def stale_work(self):
        base = self.root / 'active-work'
        if not base.is_dir():
            return section('skipped', 'Stale-work check skipped: active-work is absent', reason='directory-absent')
        cutoff = self.asof - dt.timedelta(days=14)
        old = []
        for path in sorted(base.rglob('*')):
            if path.is_file() and not path.is_symlink():
                modified = dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc)
                if modified < cutoff:
                    old.append({'path': str(path.relative_to(self.root)), 'modified': modified.isoformat()})
        old.sort(key=lambda row: (row['modified'], row['path']))
        return section('opportunity' if old else 'ok', f'Stale work: {len(old)} files older than 14 days',
                       count=len(old), oldest=old[0] if old else None)

    def ledger(self):
        paths = set(self.root.glob(self.contract.seat['ledger']['merge_glob']))
        primary = self.root / self.contract.seat['ledger']['primary']
        if primary.is_file():
            paths.add(primary)
        newest, unstamped, lines, errors = None, 0, 0, []
        # 5.3.0 item 4: one line shape (schemas/ledger-line.schema.json), read-permissive.
        # Legacy lines (no seat, `timestamp`, extra keys) never fail; a present key with the wrong type does.
        schema, shape_errors, legacy = validate_ledger.load_schema(), [], 0
        for path in sorted(paths):
            for n, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
                # Header comment lines are part of every founded ledger
                # ("On read: skip lines starting with #"); every other reader
                # skips them. Found on the 5.2.1 cold-install sign-off, 2026-09-08.
                if not line.strip() or line.lstrip().startswith('#'):
                    continue
                lines += 1
                try:
                    record = json.loads(line)
                    if not isinstance(record, dict):
                        raise ValueError('not an object')
                    unstamped += not bool(record.get('seat'))
                    category, why = validate_ledger.classify(record, schema)
                    legacy += category == 'legacy'
                    if category == 'invalid':
                        shape_errors.append({'file': str(path.relative_to(self.root)), 'line': n, 'errors': why[:3]})
                    if record.get('ts') is not None:
                        value = stamp(record['ts'])
                        newest = max(newest, value) if newest else value
                except (ValueError, TypeError) as exc:
                    errors.append({'file': str(path.relative_to(self.root)), 'line': n, 'error': str(exc)})
        shape = f', {len(shape_errors)} mis-typed' if shape_errors else ''
        return section('error' if errors else 'needs-decision' if shape_errors else
                       'opportunity' if unstamped or newest is None else 'ok',
                       f'Activity ledger: {lines} lines, {unstamped} unstamped{shape}',
                       files=len(paths), lines=lines, newest_ts=newest.isoformat() if newest else None,
                       unstamped_lines=unstamped, legacy_lines=legacy, shape_errors=shape_errors, errors=errors)

    def runtime_drift(self):
        # 5.3.0 item 4: the generalized runtime-vs-canonical drift check (logging PRD decision:
        # it lives in campus-doctor). Reported, never fixed. Host-neutral: the caller names the
        # host's runtime-copy folders with --runtime-dir; without one the section is skipped.
        if not self.runtime_dirs:
            return section('skipped', 'Runtime drift skipped: no runtime-copy folder supplied', reason='no-runtime-dir')
        args = ['--campus-root', self.root, '--json']
        for d in self.runtime_dirs:
            args += ['--runtime-dir', d]
        data, rc = self.tool('check_runtime_drift.py', *args, accepted=(0, 1))
        data['drift_status'] = data.pop('status', None)
        if data['drift_status'] == 'not_applicable':
            return section('skipped', 'Runtime drift skipped: no scheduled/ definitions on this campus', **data)
        drift, unowned = len(data['drift']), len(data['unowned'])
        return section('needs-decision' if drift else 'opportunity' if unowned else 'ok',
                       f"Runtime drift: {data['checked']} runtime copies, {drift} drift from canonical, {unowned} unowned", **data)

    def run(self):
        result = {'generated': {'today': self.today.isoformat()}}
        for name in ORDER:
            self.current = name
            try:
                result[name] = getattr(self, name)()
            except SubtoolError as exc:
                result[name] = section('error', f'{name}: {exc}', **exc.detail)
            except Exception as exc:
                result[name] = section('error', f'{name}: {type(exc).__name__}: {exc}',
                                       error=type(exc).__name__, message=str(exc))
            if name in self.blocked:
                result[name] = section('skipped', f'{name}: not checked (Python cannot start in isolated mode)',
                                       reason='python-isolated-unavailable')
        if self.blocked:  # present only on failure: a healthy run keeps its byte-stable shape
            result['preflight'] = section('error', PREFLIGHT_LINE, python=self.python,
                                          blocked=[n for n in ORDER if n in self.blocked], **self.isolated)
        return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--campus-root', required=True)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--today', type=dt.date.fromisoformat)
    ap.add_argument('--window', type=int, help='context window in tokens (delegated to context-weight)')
    ap.add_argument('--scheduled-json', help='live scheduler response file; - reads stdin; relative paths are campus-relative')
    ap.add_argument('--sweep', action='store_true')
    ap.add_argument('--installed-version', help='installed plugin version, read from its manifest (pass it when running from the campus kit)')
    ap.add_argument('--kit-manifest', help="the installed plugin's tools/kit-manifest.json; '-' reads it from stdin "
                                           '(pass it when running from the campus kit)')
    ap.add_argument('--runtime-dir', action='append', default=[],
                    help="host folder of runtime job copies ({taskId}/SKILL.md); repeatable; campus-relative if relative")
    a = ap.parse_args(argv)
    root = Path(a.campus_root).resolve()
    today = a.today or dt.datetime.now(dt.timezone.utc).date()
    try:
        scheduled = None
        schedule_error = None
        if a.scheduled_json and a.scheduled_json != '-':
            path = Path(a.scheduled_json)
            try:
                scheduled = (path if path.is_absolute() else root / path).read_text(encoding='utf-8-sig')
            except (OSError, UnicodeError) as exc:
                # Carry the read failure into schedules without losing other sections.
                schedule_error = str(exc)
        kit_manifest = None
        if a.kit_manifest:
            if a.kit_manifest == '-' and a.scheduled_json == '-':
                raise SystemExit('FAIL(2): only one of --kit-manifest and --scheduled-json can read stdin')
            try:
                kit_manifest = json.loads(kernel_kit.read_input(a.kit_manifest))
            except (OSError, ValueError) as exc:
                raise SystemExit(f'FAIL(2): --kit-manifest unreadable: {exc}')
        if a.scheduled_json == '-':
            raw = kernel_kit.read_input('-')
            scheduled = raw if raw.strip() else None
        result = Evidence(root, today, a.window, scheduled, a.sweep, a.installed_version, kit_manifest, a.runtime_dir).run()
        if schedule_error:
            result['schedules'] = section('error', 'Schedule input could not be read', stderr_tail=schedule_error[-2000:])
    except ContractError as exc:
        result = {'generated': {'today': today.isoformat()}}
        for name in ORDER:
            result[name] = section('error', f'{name}: {exc}', error='contract-unavailable')
    if a.json:
        print(json.dumps(result, sort_keys=True, indent=2))
    else:
        if 'preflight' in result:
            print(result['preflight']['line'])
        for name in ORDER:
            print(result[name]['line'])
    # SKILL contract: 0 = every section produced evidence and nothing is red; 1 = evidence collected and some
    # lines are red (needs-decision or a section-level error); 2 = the tool itself failed (raised above).
    return 1 if 'preflight' in result or any(result[name]['status'] in ('needs-decision', 'error') for name in ORDER) else 0


if __name__ == '__main__':
    raise SystemExit(main())
