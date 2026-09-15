#!/usr/bin/env python3
"""Read-only campus contract resolvers. Stock Python; no campus identity authority.

Use Resolver(path) for an explicit contract or the module-level functions for
CAMPUS_CONTRACT / the contract beside this tool's own tree.
platform: codex; seat: codex
"""
from __future__ import annotations
import datetime as dt
from functools import lru_cache
import json
import os
from pathlib import Path
import re
import sys


class ContractError(Exception):
    pass


def _require(value):
    if not value:
        raise ValueError('shape')


def _invalid_constant(value):
    raise ValueError(f'invalid JSON constant: {value}')


def contract_path(override=None):
    return Path(override or os.environ.get('CAMPUS_CONTRACT') or
                Path(__file__).resolve().parent.parent / 'contracts/campus.json').resolve()


class Resolver:
    def __init__(self, path=None):
        path = contract_path(path)
        try:
            self.data = json.loads(path.read_text(encoding='utf-8'), parse_constant=_invalid_constant)
        except FileNotFoundError as exc:
            raise ContractError(f'CONTRACT_MISSING: {path}') from exc
        except (OSError, ValueError, UnicodeError) as exc:
            raise ContractError(f'CONTRACT_UNREADABLE: {path}') from exc
        c = self.data
        if not isinstance(c, dict) or c.get('contract_version') != '1.0':
            raise ContractError('CONTRACT_VERSION_UNSUPPORTED: expected contract_version 1.0')
        try:
            self.files = c['context_aliases']['files']
            _require(isinstance(self.files, list))
            for row in self.files:
                _require(isinstance(row['concept'], str) and isinstance(row['canonical'], str))
                _require(isinstance(row['founding_writes'], str))
                _require(isinstance(row['aliases'], list) and all(isinstance(a, str) for a in row['aliases']))
            _require(c['context_aliases']['resolution'] == [
                'canonical', 'legacy alias (in listed order)', 'case-insensitive match'])
            self.hosts = c['hosts']
            _require(isinstance(self.hosts['clients'], dict))
            _require(isinstance(self.hosts['entry_file_by_manifest_dir'], dict))
            _require(isinstance(self.hosts['entry_file_read_names'], list))
            for client in self.hosts['clients'].values():
                _require(isinstance(client['manifest_dir'], str) and isinstance(client['entry_file'], str))
            _require(all(isinstance(v, str) for v in self.hosts['entry_file_by_manifest_dir'].values()))
            self.enums = c['registry_enums']['enums']
            for key in ('department', 'status', 'type'):
                _require(isinstance(self.enums[key], list) and all(isinstance(v, str) for v in self.enums[key]))
            self.aliases = c['registry_enums']['legacy_read_aliases']['department']
            _require(isinstance(self.aliases, dict))
            self.seat = c['seat']
            self.seat_rx = re.compile(self.seat['seat_id_pattern'])
            for key in ('primary', 'satellite', 'unknown'):
                _require(isinstance(self.seat['ledger'][key], str))
            _require(isinstance(self.seat['roles'], list) and isinstance(self.seat['lane']['satellite'], str))
            self.patterns = [(name, re.compile(source)) for name, source in c['run_id']['patterns'].items()]
            _require(self.patterns and self.patterns[0][0] == 'canonical')
            self.segment_rx = re.compile(c['run_id']['segment_pattern'])
            self.dirs = c['run_id']['run_dir']
            prefix, suffix = self.dirs['campus'].split('{team}')
            playbook = self.dirs['playbook']
            _require(playbook.startswith(prefix) and playbook.endswith(suffix) and suffix)
            self.playbook_owner = playbook[len(prefix):-len(suffix)]
            _require(self.segment_rx.fullmatch(self.playbook_owner))
            _require(isinstance(self.dirs['standalone'], str))
        except (KeyError, TypeError, ValueError, AttributeError, re.error) as exc:
            raise ContractError('CONTRACT_INVALID: required resolver data or regex invalid') from exc

    def resolve_context(self, name):
        found = None
        matched = None
        # Global passes: a canonical filename wins over another concept's alias.
        for mode in ('canonical', 'alias', 'case-insensitive', 'concept'):
            for row in self.files:
                names = [row['canonical'], *row['aliases']]
                concepts = [row['concept'], *row['concept'].split('/')]
                concepts += [n.rsplit('.', 1)[0] for n in names]
                match = (name == row['canonical'] if mode == 'canonical' else
                         name in row['aliases'] if mode == 'alias' else
                         name.lower() in [n.lower() for n in names] if mode == 'case-insensitive' else
                         name.lower() in [n.strip().lower() for n in concepts])
                if match:
                    found, matched = row, mode
                    break
            if found:
                break
        return {'concept': found['concept'] if found else None,
                'canonical': found['canonical'] if found else None, 'matched_by': matched,
                'founding_writes': found['founding_writes'] if found else None,
                'read_order': [found['canonical'], *found['aliases']] if found else []}

    def resolve_department(self, value):
        canonical = value if value in self.enums['department'] else self.aliases.get(value)
        known = canonical in self.enums['department']
        return {'value': value, 'canonical': canonical if known else None,
                'legacy_alias': known and value != canonical, 'known': known}

    def _normalize(self, value, kind):
        if value in self.enums[kind]:
            return {'value': value, 'canonical': value, 'known': True}
        for canonical in self.enums[kind]:
            if value.lower() == canonical.lower():
                return {'value': value, 'canonical': canonical, 'known': True,
                        'matched_by': 'case-insensitive'}
        return {'value': value, 'canonical': None, 'known': False}

    def normalize_status(self, value):
        return self._normalize(value, 'status')

    def normalize_type(self, value):
        return self._normalize(value, 'type')

    def entry_file(self, value):
        client = self.hosts['clients'].get(value)
        directory = client['manifest_dir'] if client else value
        entry = self.hosts['entry_file_by_manifest_dir'].get(directory)
        return {'manifest_dir': directory if entry is not None else None,
                'entry_file': entry, 'read_names': list(self.hosts['entry_file_read_names'])}

    def ledger_path(self, info):
        valid = (isinstance(info, dict) and isinstance(info.get('seat'), str) and
                 bool(self.seat_rx.fullmatch(info['seat'])) and info.get('role') in self.seat['roles'])
        state = 'valid' if valid else 'missing' if info is None else 'invalid'
        role, seat = (info['role'], info['seat']) if valid else ('satellite', 'unknown')
        ledger = self.seat['ledger'][role if valid else 'unknown'].format(seat=seat)
        lane = self.seat['lane']['satellite'].format(seat=seat) if role == 'satellite' else None
        return {'state': state, 'role': role, 'seat': seat, 'ledger': ledger, 'lane': lane}

    def parse_run_id(self, run_id):
        for name, rx in self.patterns:
            match = rx.fullmatch(run_id)
            if not match:
                continue
            values = match.groupdict()
            date = values['date'].replace('-', '')
            time = values['time'] + ('00' if len(values['time']) == 4 else '')
            try:
                stamp = dt.datetime.strptime(date + time + (values.get('millis') or '000'),
                                             '%Y%m%d%H%M%S%f').replace(tzinfo=dt.timezone.utc)
            except ValueError:
                break
            canonical = name == 'canonical'
            return {'slug': values.get('slug') or run_id,
                    'stamp_utc': stamp.isoformat(timespec='milliseconds').replace('+00:00', 'Z'),
                    'legacy': not canonical, 'canonical': canonical}
        return {'slug': run_id, 'stamp_utc': None, 'legacy': True, 'canonical': False}

    def run_dir(self, kind, team, slug, run_id, standalone):
        if kind not in ('team', 'playbook') or not isinstance(standalone, bool):
            raise ValueError('invalid kind or standalone (expected team/playbook and boolean)')
        for label, value in [('team', team), ('slug', slug), ('run_id', run_id)]:
            if not isinstance(value, str) or not self.segment_rx.fullmatch(value) or value in ('.', '..'):
                raise ValueError(f'invalid {label}')
        template = self.dirs['standalone' if standalone else 'playbook' if kind == 'playbook' else 'campus']
        stamp = self.parse_run_id(run_id)['stamp_utc']
        if '{YYYY-MM}' in template and stamp is None:
            raise ValueError('run_id has no timestamp from which to resolve YYYY-MM')
        values = {'YYYY-MM': stamp[:7] if stamp else '', 'team': self.playbook_owner if kind == 'playbook' else team,
                  'slug': slug, 'run_id': run_id}
        return {'run_dir': template.format_map(values)}


@lru_cache(maxsize=8)
def _load(path):
    return Resolver(path)


def _default():
    return _load(str(contract_path()))


def resolve_context(name): return _default().resolve_context(name)
def resolve_department(value): return _default().resolve_department(value)
def normalize_status(value): return _default().normalize_status(value)
def normalize_type(value): return _default().normalize_type(value)
def entry_file(value): return _default().entry_file(value)
def ledger_path(info): return _default().ledger_path(info)
def parse_run_id(value): return _default().parse_run_id(value)
def run_dir(kind, team, slug, run_id, standalone): return _default().run_dir(kind, team, slug, run_id, standalone)

FUNCTIONS = {'resolve_context': 1, 'resolve_department': 1, 'normalize_status': 1,
             'normalize_type': 1, 'entry_file': 1, 'ledger_path': 1, 'parse_run_id': 1, 'run_dir': 5}


def main(argv=None):
    try:
        argv = list(sys.argv[1:] if argv is None else argv)
        positional, override, pretty = [], None, False
        while argv:
            arg = argv.pop(0)
            if arg == '--':
                positional.extend(argv)
                break
            if arg == '--json':
                pretty = True
            elif arg == '--contract':
                if not argv:
                    raise ValueError('--contract needs a path')
                override = argv.pop(0)
            elif arg.startswith('--'):
                raise ValueError(f'unknown option: {arg}')
            else:
                positional.append(arg)
        if not positional or positional[0] not in FUNCTIONS:
            raise ValueError('unknown or missing function')
        function, *args = positional
        if len(args) != FUNCTIONS[function]:
            raise ValueError(f'{function} needs {FUNCTIONS[function]} argument(s)')
        if function == 'ledger_path':
            try: args[0] = json.loads(args[0])
            except ValueError: pass  # malformed seat content is an invalid seat, not CLI failure
        if function == 'run_dir':
            if args[-1] not in ('true', 'false'):
                raise ValueError('standalone must be true or false')
            args[-1] = args[-1] == 'true'
        result = getattr(Resolver(override), function)(*args)
        print(json.dumps(result, indent=2) if pretty else json.dumps(result))
        return 0
    except ContractError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (ValueError, TypeError) as exc:
        print(f'USAGE: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
