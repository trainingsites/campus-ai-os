#!/usr/bin/env node
/** Read-only campus contract resolvers. Node >=18; no identity authority.
 * platform: codex; seat: codex
 */
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

export class ContractError extends Error {}
const ownFile = fileURLToPath(import.meta.url);
function contractPath(override) {
  return path.resolve(override || process.env.CAMPUS_CONTRACT ||
    path.join(path.dirname(ownFile), '..', 'contracts', 'campus.json'));
}
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const fullmatch = (rx, value) => {
  const m = typeof value === 'string' ? rx.exec(value) : null;
  return m && m[0] === value ? m : null;
};
// The generated patterns use Python named groups, Unicode decimal digits and
// dot-without-newline. Translate that subset once on load, never per parse.
function pythonRegex(source) {
  return new RegExp(source.replaceAll('(?P<', '(?<').replaceAll('\\d', '\\p{Decimal_Number}')
    .replaceAll('.+', '[^\\n]+'), 'u');
}
function requireShape(value) { if (!value) throw new Error('shape'); }

// Match Python strptime's %Y%m%d%H%M%S%f conversion, including its variable-width
// fields. Fixed slicing would disagree with the existing minter on old IDs.
const stampFields = pythonRegex('^(?<Y>\\d{4})(?<m>1[0-2]|0[1-9]|[1-9])' +
  '(?<d>3[0-1]|[1-2]\\d|0[1-9]|[1-9]| [1-9])(?<H>2[0-3]|[0-1]\\d|\\d| \\d)' +
  '(?<M>[0-5]\\d|\\d)(?<S>6[0-1]|[0-5]\\d|\\d)(?<f>[0-9]{1,6})$');
const decimal = /\p{Decimal_Number}/u;
function decimalNumber(value) {
  return Number([...value].map(char => {
    if (!decimal.test(char)) return char;
    const cp = char.codePointAt(0);
    let start = cp;
    while (start > 0 && decimal.test(String.fromCodePoint(start - 1))) start--;
    return String((cp - start) % 10);
  }).join(''));
}
function stamp(date, time, millis = '000') {
  const m = fullmatch(stampFields, date.replaceAll('-', '') +
    ([...time].length === 4 ? time + '00' : time) + millis);
  if (!m) return null;
  const g = m.groups;
  const [year, month, day, hour, minute, second] = ['Y', 'm', 'd', 'H', 'M', 'S'].map(k => decimalNumber(g[k]));
  if (year < 1 || year > 9999 || second > 59) return null;
  const value = new Date(0);
  value.setUTCFullYear(year, month - 1, day);
  value.setUTCHours(hour, minute, second, Number(g.f.padEnd(6, '0').slice(0, 3)));
  if (value.getUTCFullYear() !== year || value.getUTCMonth() !== month - 1 || value.getUTCDate() !== day) return null;
  return value.toISOString();
}

export class Resolver {
  constructor(override) {
    const filename = contractPath(override);
    try { this.data = JSON.parse(new TextDecoder('utf-8', {fatal: true, ignoreBOM: true}).decode(fs.readFileSync(filename))); }
    catch (e) { throw new ContractError(`${e.code === 'ENOENT' ? 'CONTRACT_MISSING' : 'CONTRACT_UNREADABLE'}: ${filename}`); }
    const c = this.data;
    if (!object(c) || c.contract_version !== '1.0')
      throw new ContractError('CONTRACT_VERSION_UNSUPPORTED: expected contract_version 1.0');
    try {
      this.files = c.context_aliases.files;
      requireShape(Array.isArray(this.files));
      for (const row of this.files) {
        requireShape(['concept', 'canonical', 'founding_writes'].every(k => typeof row[k] === 'string'));
        requireShape(Array.isArray(row.aliases) && row.aliases.every(a => typeof a === 'string'));
      }
      requireShape(JSON.stringify(c.context_aliases.resolution) === JSON.stringify([
        'canonical', 'legacy alias (in listed order)', 'case-insensitive match']));
      this.hosts = c.hosts;
      requireShape(object(this.hosts.clients) && object(this.hosts.entry_file_by_manifest_dir) &&
        Array.isArray(this.hosts.entry_file_read_names));
      for (const client of Object.values(this.hosts.clients))
        requireShape(typeof client.manifest_dir === 'string' && typeof client.entry_file === 'string');
      requireShape(Object.values(this.hosts.entry_file_by_manifest_dir).every(v => typeof v === 'string'));
      this.enums = c.registry_enums.enums;
      for (const key of ['department', 'status', 'type'])
        requireShape(Array.isArray(this.enums[key]) && this.enums[key].every(v => typeof v === 'string'));
      this.aliases = c.registry_enums.legacy_read_aliases.department;
      requireShape(object(this.aliases));
      this.seat = c.seat;
      this.seatRx = pythonRegex(this.seat.seat_id_pattern);
      for (const key of ['primary', 'satellite', 'unknown']) requireShape(typeof this.seat.ledger[key] === 'string');
      requireShape(Array.isArray(this.seat.roles) && typeof this.seat.lane.satellite === 'string');
      this.patterns = Object.entries(c.run_id.patterns).map(([name, source]) => [name, pythonRegex(source)]);
      requireShape(this.patterns.length && this.patterns[0][0] === 'canonical');
      this.segmentRx = pythonRegex(c.run_id.segment_pattern);
      this.dirs = c.run_id.run_dir;
      const pieces = this.dirs.campus.split('{team}');
      requireShape(pieces.length === 2);
      const [prefix, suffix] = pieces;
      requireShape(suffix && this.dirs.playbook.startsWith(prefix) && this.dirs.playbook.endsWith(suffix));
      this.playbookOwner = this.dirs.playbook.slice(prefix.length, -suffix.length);
      requireShape(fullmatch(this.segmentRx, this.playbookOwner) && typeof this.dirs.standalone === 'string');
    } catch (e) { throw new ContractError('CONTRACT_INVALID: required resolver data or regex invalid'); }
  }

  resolve_context(name) {
    let found = null, matched = null;
    for (const mode of ['canonical', 'alias', 'case-insensitive', 'concept']) {
      for (const row of this.files) {
        const names = [row.canonical, ...row.aliases];
        const concepts = [row.concept, ...row.concept.split('/'), ...names.map(n => n.replace(/\.[^.]*$/, ''))];
        const match = mode === 'canonical' ? name === row.canonical : mode === 'alias' ? row.aliases.includes(name) :
          mode === 'case-insensitive' ? names.some(n => n.toLowerCase() === name.toLowerCase()) :
          concepts.some(n => n.trim().toLowerCase() === name.toLowerCase());
        if (match) { found = row; matched = mode; break; }
      }
      if (found) break;
    }
    return {concept: found ? found.concept : null, canonical: found ? found.canonical : null,
      matched_by: matched, founding_writes: found ? found.founding_writes : null,
      read_order: found ? [found.canonical, ...found.aliases] : []};
  }
  resolve_department(value) {
    const canonical = this.enums.department.includes(value) ? value :
      Object.hasOwn(this.aliases, value) ? this.aliases[value] : null;
    const known = this.enums.department.includes(canonical);
    return {value, canonical: known ? canonical : null, legacy_alias: known && value !== canonical, known};
  }
  _normalize(value, kind) {
    if (this.enums[kind].includes(value)) return {value, canonical: value, known: true};
    for (const canonical of this.enums[kind])
      if (value.toLowerCase() === canonical.toLowerCase())
        return {value, canonical, known: true, matched_by: 'case-insensitive'};
    return {value, canonical: null, known: false};
  }
  normalize_status(value) { return this._normalize(value, 'status'); }
  normalize_type(value) { return this._normalize(value, 'type'); }
  entry_file(value) {
    const client = Object.hasOwn(this.hosts.clients, value) ? this.hosts.clients[value] : null;
    const directory = client ? client.manifest_dir : value;
    const entry = Object.hasOwn(this.hosts.entry_file_by_manifest_dir, directory) ? this.hosts.entry_file_by_manifest_dir[directory] : null;
    return {manifest_dir: entry !== null ? directory : null, entry_file: entry, read_names: [...this.hosts.entry_file_read_names]};
  }
  ledger_path(info) {
    const valid = Boolean(object(info) && typeof info.seat === 'string' && fullmatch(this.seatRx, info.seat) && this.seat.roles.includes(info.role));
    const state = valid ? 'valid' : info === null ? 'missing' : 'invalid';
    const role = valid ? info.role : 'satellite', seat = valid ? info.seat : 'unknown';
    const ledger = this.seat.ledger[valid ? role : 'unknown'].replaceAll('{seat}', seat);
    const lane = role === 'satellite' ? this.seat.lane.satellite.replaceAll('{seat}', seat) : null;
    return {state, role, seat, ledger, lane};
  }
  parse_run_id(runId) {
    for (const [name, rx] of this.patterns) {
      const match = fullmatch(rx, runId);
      if (!match) continue;
      const v = match.groups, timestamp = stamp(v.date, v.time, v.millis || '000');
      if (timestamp === null) break;
      const canonical = name === 'canonical';
      return {slug: v.slug || runId, stamp_utc: timestamp, legacy: !canonical, canonical};
    }
    return {slug: runId, stamp_utc: null, legacy: true, canonical: false};
  }
  run_dir(kind, team, slug, runId, standalone) {
    if (!['team', 'playbook'].includes(kind) || typeof standalone !== 'boolean')
      throw new Error('invalid kind or standalone (expected team/playbook and boolean)');
    for (const [label, value] of [['team', team], ['slug', slug], ['run_id', runId]])
      if (typeof value !== 'string' || !fullmatch(this.segmentRx, value) || ['.', '..'].includes(value)) throw new Error(`invalid ${label}`);
    const template = this.dirs[standalone ? 'standalone' : kind === 'playbook' ? 'playbook' : 'campus'];
    const timestamp = this.parse_run_id(runId).stamp_utc;
    if (template.includes('{YYYY-MM}') && timestamp === null) throw new Error('run_id has no timestamp from which to resolve YYYY-MM');
    const values = {'YYYY-MM': timestamp ? timestamp.slice(0, 7) : '',
      team: kind === 'playbook' ? this.playbookOwner : team, slug, run_id: runId};
    return {run_dir: template.replace(/\{([^}]+)\}/g, (_, key) => {
      if (!Object.hasOwn(values, key)) throw new Error(`unknown template field ${key}`);
      return values[key];
    })};
  }
}

const cache = new Map();
function defaultResolver() {
  const filename = contractPath();
  if (!cache.has(filename)) cache.set(filename, new Resolver(filename));
  return cache.get(filename);
}
export const resolve_context = name => defaultResolver().resolve_context(name);
export const resolve_department = value => defaultResolver().resolve_department(value);
export const normalize_status = value => defaultResolver().normalize_status(value);
export const normalize_type = value => defaultResolver().normalize_type(value);
export const entry_file = value => defaultResolver().entry_file(value);
export const ledger_path = value => defaultResolver().ledger_path(value);
export const parse_run_id = value => defaultResolver().parse_run_id(value);
export const run_dir = (...args) => defaultResolver().run_dir(...args);
export const FUNCTIONS = {resolve_context: 1, resolve_department: 1, normalize_status: 1,
  normalize_type: 1, entry_file: 1, ledger_path: 1, parse_run_id: 1, run_dir: 5};

function ascii(text) { return text.replace(/[\u007f-\uffff]/g, c => '\\u' + c.charCodeAt(0).toString(16).padStart(4, '0')); }
function compact(value) {
  if (Array.isArray(value)) return '[' + value.map(compact).join(', ') + ']';
  if (object(value)) return '{' + Object.entries(value).map(([k, v]) => JSON.stringify(k) + ': ' + compact(v)).join(', ') + '}';
  return JSON.stringify(value);
}
export function main(argv = process.argv.slice(2)) {
  try {
    argv = [...argv];
    const positional = [];
    let override = null, pretty = false;
    while (argv.length) {
      const arg = argv.shift();
      if (arg === '--') { positional.push(...argv); break; }
      if (arg === '--json') pretty = true;
      else if (arg === '--contract') {
        if (!argv.length) throw new Error('--contract needs a path');
        override = argv.shift();
      } else if (arg.startsWith('--')) throw new Error(`unknown option: ${arg}`);
      else positional.push(arg);
    }
    const fn = positional.shift();
    if (!Object.hasOwn(FUNCTIONS, fn)) throw new Error('unknown or missing function');
    if (positional.length !== FUNCTIONS[fn]) throw new Error(`${fn} needs ${FUNCTIONS[fn]} argument(s)`);
    if (fn === 'ledger_path') { try { positional[0] = JSON.parse(positional[0]); } catch {} }
    if (fn === 'run_dir') {
      if (!['true', 'false'].includes(positional.at(-1))) throw new Error('standalone must be true or false');
      positional[positional.length - 1] = positional.at(-1) === 'true';
    }
    const result = new Resolver(override)[fn](...positional);
    process.stdout.write(ascii(pretty ? JSON.stringify(result, null, 2) : compact(result)) + '\n');
    return 0;
  } catch (e) {
    process.stderr.write((e instanceof ContractError ? e.message : `USAGE: ${e.message}`) + '\n');
    return e instanceof ContractError ? 2 : 1;
  }
}
if (process.argv[1] && path.resolve(process.argv[1]) === ownFile) process.exitCode = main();
