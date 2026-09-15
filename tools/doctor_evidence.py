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

from contract import Resolver, ContractError

KERNEL = Path(__file__).resolve().parent.parent
ORDER = ('workspace', 'version_lockstep', 'registry', 'context_weight', 'results_ledgers',
         'schedules', 'seat_contract', 'fleet_sweep', 'staff', 'stale_work', 'ledger')
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
    def __init__(self, root, today, window=None, scheduled=None, sweep=False):
        self.root, self.today, self.window = root, today, window
        self.asof = dt.datetime.combine(today, dt.time(), dt.timezone.utc)
        self.scheduled, self.sweep = scheduled, sweep
        self.contract = Resolver()
        self.env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', CAMPUS_ROOT=str(root))

    def tool(self, name, *args, accepted=(0,), stdin='', command=None):
        runtime = shutil.which('node') if name.endswith('.mjs') else sys.executable
        argv = command or [runtime, str(KERNEL / 'tools' / name), *map(str, args)]
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
        installed = read_json(manifest).get('version')
        good = isinstance(installed, str) and bool(installed) and workspace == registry == installed
        return section('ok' if good else 'needs-decision',
                       f'Version current (v{installed}) - workspace, registry and installed plugin agree' if good else
                       f'Version homes disagree: workspace {workspace} / registry {registry} / installed {installed}',
                       workspace=workspace, registry=registry, installed=installed, manifest=str(manifest))

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
        code = ('import sys, datetime as dt; sys.path.insert(0, sys.argv[1]); '
                'import check_cron_parity as tool; original = tool.assess_health; '
                'now = dt.datetime.fromisoformat(sys.argv[2]); '
                'tool.assess_health = lambda live: original(live, now=now); '
                'sys.argv = [tool.__file__, "--scheduled", sys.argv[3], "--json"]; '
                'raise SystemExit(tool.main())')
        command = [sys.executable, '-c', code, str(KERNEL / 'tools'), self.asof.isoformat(), str(self.root / 'scheduled')]
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
                    if record.get('ts') is not None:
                        value = stamp(record['ts'])
                        newest = max(newest, value) if newest else value
                except (ValueError, TypeError) as exc:
                    errors.append({'file': str(path.relative_to(self.root)), 'line': n, 'error': str(exc)})
        return section('error' if errors else 'opportunity' if unstamped or newest is None else 'ok',
                       f'Activity ledger: {lines} lines, {unstamped} unstamped',
                       files=len(paths), lines=lines, newest_ts=newest.isoformat() if newest else None,
                       unstamped_lines=unstamped, errors=errors)

    def run(self):
        result = {'generated': {'today': self.today.isoformat()}}
        for name in ORDER:
            try:
                result[name] = getattr(self, name)()
            except SubtoolError as exc:
                result[name] = section('error', f'{name}: {exc}', **exc.detail)
            except Exception as exc:
                result[name] = section('error', f'{name}: {type(exc).__name__}: {exc}',
                                       error=type(exc).__name__, message=str(exc))
        return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--campus-root', required=True)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--today', type=dt.date.fromisoformat)
    ap.add_argument('--window', type=int, help='context window in tokens (delegated to context-weight)')
    ap.add_argument('--scheduled-json', help='live scheduler response file; - reads stdin; relative paths are campus-relative')
    ap.add_argument('--sweep', action='store_true')
    a = ap.parse_args(argv)
    root = Path(a.campus_root).resolve()
    today = a.today or dt.datetime.now(dt.timezone.utc).date()
    try:
        scheduled = None
        schedule_error = None
        if a.scheduled_json and a.scheduled_json != '-':
            path = Path(a.scheduled_json)
            try:
                scheduled = (path if path.is_absolute() else root / path).read_text(encoding='utf-8')
            except (OSError, UnicodeError) as exc:
                # Carry the read failure into schedules without losing other sections.
                schedule_error = str(exc)
        elif a.scheduled_json == '-':
            raw = sys.stdin.read()
            scheduled = raw if raw.strip() else None
        result = Evidence(root, today, a.window, scheduled, a.sweep).run()
        if schedule_error:
            result['schedules'] = section('error', 'Schedule input could not be read', stderr_tail=schedule_error[-2000:])
    except ContractError as exc:
        result = {'generated': {'today': today.isoformat()}}
        for name in ORDER:
            result[name] = section('error', f'{name}: {exc}', error='contract-unavailable')
    if a.json:
        print(json.dumps(result, sort_keys=True, indent=2))
    else:
        for name in ORDER:
            print(result[name]['line'])
    # SKILL contract: 0 = every section produced evidence and nothing is red; 1 = evidence collected and some
    # lines are red (needs-decision or a section-level error); 2 = the tool itself failed (raised above).
    return 1 if any(result[name]['status'] in ('needs-decision', 'error') for name in ORDER) else 0


if __name__ == '__main__':
    raise SystemExit(main())
