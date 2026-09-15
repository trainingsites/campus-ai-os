#!/usr/bin/env node
/**
 * Context Weight — startup context budget for a campus
 * --------------------------------------------------------------
 * Measures how much of the model's context window the campus spends
 * BEFORE the first question: the entry-file chain plus every file the
 * chief-of-staff entry file instructs be read at the start of a session.
 *
 * Reads the campus's OWN files to decide what counts — never a typed list:
 *   - entry chain: {connected root}/{ENTRY} -> {campus root}/{ENTRY} -> the
 *     chief-of-staff entry the root redirects to (usually dean/{ENTRY})
 *   - startup set: workspace.json -> startup_reads[] when the campus declares
 *     one; otherwise the paths referenced inside that file's "Start of Session"
 *     section. Either way resolved through .campus-os/context-files.md (the
 *     shared-context canon) so a renamed or aliased file is still found
 *
 * Units: TOKENS (estimated), never lines. tok ~= utf-8 BYTES / 4. This
 * reproduces the four per-file figures recorded in the context-budget PRD
 * (2026-09-04) to within +-1 token, so it is the same estimator the PRD
 * used. It is an estimate, not a tokenizer; real counts for English
 * markdown run within a few percent either way. Bytes, not characters:
 * a character count reads ~1-2% lower on prose with em-dashes and emoji.
 *
 * Band = fraction of the window, so it survives model changes:
 *   GREEN <=10% . AMBER 10-20% . RED >20%       (window default 200k)
 *
 * Run:   node tools/context-weight.mjs                (campus root = cwd walk-up)
 *        node tools/context-weight.mjs --root /path/to/campus
 *        node tools/context-weight.mjs --json          (machine output)
 * Flags: --window N   --entry CLAUDE.md|AGENTS.md|AGENTS.override.md|GEMINI.md|CODEX.md
 *        --files a,b  (explicit set, bypasses resolution)   --today YYYY-MM-DD
 * Exit:  0 GREEN . 1 AMBER . 2 RED . 3 incomplete measurement or invalid input
 * Always prints. A missing file is reported at 0 tokens, never skipped in silence.
 * Dependency-free (node:fs, node:path only).
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// ---- args -----------------------------------------------------------------
const argv = process.argv.slice(2);
function flag(name, dflt) {
  const i = argv.indexOf('--' + name);
  if (i < 0) return dflt;
  const v = argv[i + 1];
  return (v === undefined || v.startsWith('--')) ? true : v;
}
const JSON_OUT = argv.includes('--json');
const WINDOW = Number(flag('window', process.env.CONTEXT_WINDOW || 200000));
const FORCE_ENTRY = flag('entry', null);
const EXPLICIT = flag('files', null);
const TODAY = String(flag('today', new Date().toISOString().slice(0, 10)));

// Read-side: accept every entry filename any supported host uses (doctor 2a).
// Writing stays exact elsewhere; this tool never writes.
const ENTRY_NAMES = ['CLAUDE.md', 'AGENTS.override.md', 'AGENTS.md', 'GEMINI.md', 'CODEX.md'];
const BANDS = [
  { name: 'GREEN', max: 0.10, note: 'healthy' },
  { name: 'AMBER', max: 0.20, note: 'archive due' },
  { name: 'RED',   max: Infinity, note: 'startup is eating the session' },
];

// ---- helpers ---------------------------------------------------------------
const exists = p => { try { return fs.statSync(p).isFile(); } catch { return false; } };
const readText = p => { try { return fs.readFileSync(p, 'utf8'); } catch { return null; } };
const tokens = s => Math.round(Buffer.byteLength(s, 'utf8') / 4);
const fmt = n => n.toLocaleString('en-US');
const pct = (n, d) => d ? (100 * n / d) : 0;

function findCampusRoot() {
  const forced = flag('root', process.env.CAMPUS_ROOT || null);
  if (forced) { try { return fs.realpathSync(String(forced)); } catch { return path.resolve(String(forced)); } }
  let dir = process.cwd();
  for (let i = 0; i < 8; i++) {
    if (exists(path.join(dir, 'workspace.json'))) return dir;
    const up = path.dirname(dir);
    if (up === dir) break;
    dir = up;
  }
  return null;
}

// Pick the entry file a session on THIS host would read from a directory.
function entryIn(dir) {
  const order = FORCE_ENTRY ? [String(FORCE_ENTRY)] : ENTRY_NAMES;
  const present = ENTRY_NAMES.filter(n => exists(path.join(dir, n)));
  const chosen = order.find(n => present.includes(n)) || null;
  return { chosen: chosen ? path.join(dir, chosen) : null, present };
}

// ---- shared-context canon (.campus-os/context-files.md) --------------------
// Parses the "Canonical filenames" table: | Concept | `canonical` | `alias`, `alias` |
// Returns [[canonical, ...aliases], ...]. Reading is permissive; first hit wins.
function loadCanon(root) {
  const local = path.join(root, '.campus-os', 'context-files.md');
  const p = exists(local) ? local : path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../templates/context-files.md');
  const t = readText(p);
  if (!t) return { path: null, rows: [] };
  const rows = [];
  for (const ln of t.split(/\r?\n/)) {
    const m = ln.match(/^\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*$/);
    if (!m) continue;
    const names = [];
    for (const cell of [m[2], m[3]]) {
      for (const bt of cell.matchAll(/`([^`]+\.md)`/g)) names.push(bt[1]);
    }
    if (names.length) rows.push(names);
  }
  return { path: p, rows };
}

function resolveViaCanon(root, rel, canon) {
  const dir = path.dirname(rel), base = path.basename(rel);
  // The local canon wins, then its canonical name precedes every alias.
  const row = canon.rows.find(r => r.some(n => n.toLowerCase() === base.toLowerCase()));
  const candidates = row || [base];
  for (const c of candidates) {
    const cand = path.join(root, dir, c);
    if (exists(cand)) return { abs: cand, rel: path.join(dir, c), via: c === base ? null : 'canon' };
  }
  // case-insensitive directory match, last resort
  try {
    const names = fs.readdirSync(path.join(root, dir)).sort();
    const hit = candidates.map(c => names.find(f => c.toLowerCase() === f.toLowerCase())).find(Boolean);
    if (hit) return { abs: path.join(root, dir, hit), rel: path.join(dir, hit), via: 'case' };
  } catch { /* dir absent */ }
  return null;
}

// ---- reference extraction ---------------------------------------------------
const READ_VERB = /\b(read|skim|open|load|check|scan|review|consult)\b/i;
const OPTIONAL  = /\b(on demand|only the one|only if|only when|if needed|when needed|as needed|read only|on-demand|when this session)\b/i;
const MANDATORY = /\b(every session|always|must[- ]reads?)\b/i;   // outranks OPTIONAL on the same item
// "If `daily/{today}.md` exists, skim it." - a read the entry file itself makes conditional
// on the file's presence is optional by definition (v5.1.10: a fresh template campus
// was reporting UNKNOWN because today's daily note does not exist yet).
const CONDITIONAL = /\bif\b[^\n]{0,60}?\b(exists?|is present|present)\b/i;
// Paths whose text carried a date placeholder: they roll daily and are absent until
// the session creates them. Reported when missing, never an unresolved read.
const ROLLING = new Set();

// Backticked path-like strings in a piece of text, placeholders expanded.
function pathsIn(text) {
  const out = [];
  for (const m of text.matchAll(/`([^`\n]+)`/g)) {
    const raw0 = m[1].trim();
    let s = raw0.replace(/\{(today|date|YYYY-MM-DD)[^}]*\}/gi, TODAY); // `{today's date}` first: it holds a space
    if (/\s/.test(s)) continue;                       // commands, prose
    if (s.includes('*')) continue;                    // globs: read on demand, not a file
    if (s.endsWith('/')) continue;                    // directories
    if (s.startsWith('#') || s.startsWith('--')) continue;
    if (/\{ENTRY_FILE\}/i.test(s)) { for (const n of ENTRY_NAMES) out.push(s.replace(/\{ENTRY_FILE\}/gi, n)); continue; }
    if (/[{}]/.test(s)) continue;                     // unresolved placeholder
    if (!/[\/]/.test(s) && !/\.(md|json|jsonl|txt|ya?ml)$/i.test(s)) continue;
    if (s !== raw0) ROLLING.add(s);
    out.push(s);
  }
  return out;
}

// The "Start of Session" section of an entry file, split into items.
// An item = a list line plus its indented continuation lines. Items under a
// sub-heading (### ...) inside the section are conditional elaborations.
function startOfSessionItems(text) {
  const lines = text.split(/\r?\n/);
  let start = -1, level = 0, heading = null;
  for (let i = 0; i < lines.length; i++) {
    const h = lines[i].match(/^(#{1,6})\s+(.*)$/);
    if (h && /\b(start[- ]of[- ]session|session start|startup|every session)\b/i.test(h[2])) { start = i; level = h[1].length; heading = h[2].trim(); break; }
  }
  if (start < 0) return { heading: null, items: [] };
  // A bare paragraph that introduces a list ("Read these four every session:",
  // "Quick-refs - read only the one the session needs:") is the LEAD; the list
  // items under it inherit its verb and its optional/mandatory marking.
  const items = []; let cur = null; let sub = null; let lead = '';
  for (let i = start + 1; i < lines.length; i++) {
    const ln = lines[i];
    const h = ln.match(/^(#{1,6})\s+(.*)$/);
    if (h) { if (h[1].length <= level) break; sub = h[2].trim(); cur = null; lead = ''; continue; }
    if (/^\s*([-*]|\d+[a-z]?\.)\s+/.test(ln)) { cur = { text: ln, sub, lead }; items.push(cur); continue; }
    if (/^\s+\S/.test(ln) && cur) { cur.text += '\n' + ln; continue; }
    if (/^\s*$/.test(ln)) continue;
    cur = { text: ln, sub, lead: '' }; items.push(cur); lead = ln;   // paragraph: an item AND the next list's lead
  }
  return { heading, items };
}
function classify(item) {
  const own = item.text, ctx = item.lead + '\n' + item.text;
  const isRead = READ_VERB.test(ctx);
  const conditional = CONDITIONAL.test(own) && !MANDATORY.test(own);
  const optional = item.sub !== null || (OPTIONAL.test(ctx) && !MANDATORY.test(own));
  // conditional: counted when present (the session reads it), never unresolved when absent
  return { isRead, optional, conditional };
}

// ---- measurement ------------------------------------------------------------
function sections(text) {
  const out = []; let name = '(preamble)', buf = [];
  for (const ln of text.split(/\r?\n/)) {
    const h = ln.match(/^#{1,6}\s+(.*)$/);
    if (h) { out.push({ name, tok: tokens(buf.join('\n')) }); name = h[1].trim(); buf = []; }
    buf.push(ln);
  }
  out.push({ name, tok: tokens(buf.join('\n')) });
  return out;
}
function measure(abs, label, role) {
  const t = readText(abs);
  if (t === null) return { file: label, path: path.resolve(abs), role, tokens: 0, lines: 0, missing: true, largest: null };
  const tok = tokens(t);
  const secs = sections(t);
  const big = secs.reduce((a, b) => (b.tok > a.tok ? b : a), secs[0]);
  return { file: label, path: path.resolve(abs), role, tokens: tok, lines: t.split(/\r?\n/).length, missing: false,
           largest: { name: big.name, tokens: big.tok, pct: Math.round(pct(big.tok, tok)) } };
}

// ---- resolve the startup set -----------------------------------------------
function resolve(root) {
  const notes = [], findings = [];
  // Only findings without severity 'info' make the measurement incomplete.
  const blocking = () => findings.some(f => f.severity !== 'info');
  const canon = loadCanon(root);
  const counted = [], onDemand = [], missing = [];
  const seen = new Map(), visited = new Set(), active = new Set();
  const parent = path.dirname(root);
  const display = p => path.relative(parent, p) || path.basename(p);
  const add = (list, abs, role, via = '') => {
    const id = exists(abs) ? fs.realpathSync(abs) : path.resolve(abs);
    if (seen.has(id)) {
      const old = seen.get(id);
      if (list === counted && onDemand.includes(old)) {
        onDemand.splice(onDemand.indexOf(old), 1); old.role = role; counted.push(old);
      }
      return;
    }
    const measured = measure(id, display(abs) + via, role);
    measured.source_path = path.resolve(abs);
    seen.set(id, measured); list.push(measured);
    if (measured.missing) findings.push({code:'FILE_UNREADABLE', path:id});
  };
  let chief = null, sectionHeading = null;
  const entries = [];
  function visit(file, depth = 0) {
    const id = fs.realpathSync(file);
    // A back-reference to an entry already on the chain ("read the root entry once")
    // is reported, but every file on the loop was counted exactly once, so the
    // measurement stays complete. Only an unresolved read makes it incomplete.
    if (active.has(id)) { findings.push({code:'ENTRY_CYCLE', path:id, severity:'info', detail:'entry chain loops back to a file already counted once'}); return; }
    if (visited.has(id)) return;
    if (depth > 64) { findings.push({code:'ENTRY_DEPTH_LIMIT', path:id}); return; }
    active.add(id); visited.add(id);
    const text = readText(id);
    add(counted, id, 'entry (redirect)');
    if (text === null) { active.delete(id); return; }
    const sos = startOfSessionItems(text);
    entries.push({file:id, sos});
    if (sos.heading) {
      chief = id; sectionHeading = sos.heading;
      seen.get(id).role = 'entry (chief of staff)';
    }
    // Follow mandatory entry reads in startup sections and read directives in
    // pointers. Explanatory paths outside startup sections do not expand scope.
    {
      const refs = (sos.heading
        ? sos.items.filter(item => { const c=classify(item); return c.isRead && !c.optional; }).flatMap(item => pathsIn(item.text))
        : text.split(/\r?\n/).filter(ln => READ_VERB.test(ln) && !OPTIONAL.test(ln)).flatMap(pathsIn))
        .filter(ref => ENTRY_NAMES.includes(path.basename(ref)));
      for (const ref of new Set(refs)) {
        const hit = [path.dirname(id), root, parent].map(base => path.resolve(base, ref)).find(exists);
        if (hit) visit(hit, depth + 1);
        else findings.push({code:'ENTRY_MISSING', path:ref, from:id});
      }
    }
    active.delete(id);
  }
  const ce = entryIn(root), pe = entryIn(parent);
  if (pe.chosen) visit(pe.chosen);
  if (ce.chosen) visit(ce.chosen);
  if (!chief && !blocking()) {
    const de = entryIn(path.join(root, 'dean'));
    if (de.chosen && !visited.has(fs.realpathSync(de.chosen))) {
      notes.push('Root entry did not resolve a startup section; fell back to dean/' + path.basename(de.chosen) + '.');
      visit(de.chosen);
    }
  }
  let declared = null;
  try {
    const w = JSON.parse(fs.readFileSync(path.join(root, 'workspace.json'), 'utf8'));
    if (!w || typeof w !== 'object' || Array.isArray(w)) throw Error('workspace must be an object');
    if ('startup_reads' in w) {
      if (!Array.isArray(w.startup_reads) || w.startup_reads.some(x => typeof x !== 'string' || !x.trim())) throw Error('startup_reads must be an array of paths');
      declared = w.startup_reads;
    }
  } catch (e) { findings.push({code:'WORKSPACE_INVALID', detail:e.message}); }
  function readRef(raw, optional, bases, role, conditional = false) {
    const ref = raw.replace(/\{(today|date|YYYY-MM-DD)[^}]*\}/gi, TODAY);
    const rolling = ref !== raw || ROLLING.has(ref) || conditional;
    const hit = bases.map(base => resolveViaCanon(base, ref, canon)).find(Boolean);
    if (!hit) {
      missing.push({ref, optional, rolling, conditional});
      if (!optional && !rolling) findings.push({code:'STARTUP_READ_MISSING', path:ref});
      return;
    }
    add(optional ? onDemand : counted, hit.abs, role,
      hit.via ? `  (resolved via ${hit.via}: ${ref})` : '');
  }
  if (declared !== null) {
    sectionHeading = 'workspace.json -> startup_reads (declared)';
    for (const ref of declared) readRef(ref, false, [root], 'startup read (declared)');
  } else {
    if (!chief) findings.push({code:'STARTUP_UNRESOLVED', detail:'No "Start of Session" heading resolved'});
    for (const e of entries) for (const item of e.sos.items) {
      const {isRead, optional, conditional} = classify(item);
      if (isRead) for (const ref of pathsIn(item.text)) {
        readRef(ref, optional, [root, path.dirname(e.file), parent], optional ? 'on-demand read' : conditional ? 'startup read (conditional)' : 'startup read', conditional);
      }
    }
  }
  if (!visited.size) findings.push({code:'ENTRY_MISSING', path:root});
  return {canon, counted, onDemand, missing, notes, sectionHeading, chief,
          resolution:{status:blocking() ? 'incomplete' : 'complete', findings}};
}

// ---- main -------------------------------------------------------------------
const root = findCampusRoot();
if (!root) {
  const detail = 'Context weight: could not locate a campus. Pass --root.';
  console.log(JSON_OUT ? JSON.stringify({root:null, band:'UNKNOWN', exit:3, files:[], resolution:{status:'incomplete', findings:[{code:'CAMPUS_MISSING', detail}]}}) : detail);
  process.exit(3);
}

let R;
if (EXPLICIT) {
  const counted = String(EXPLICIT).split(',').map(s => s.trim()).filter(Boolean)
    .map(rel => measure(path.resolve(root, rel), rel, 'explicit'));
  R = { canon: { path: null, rows: [] }, counted, onDemand: [], missing: [], notes: ['Explicit file list (--files); nothing resolved from the entry file.'], sectionHeading: null, chief: null };
} else {
  R = resolve(root);
}
const total = R.counted.reduce((a, f) => a + f.tokens, 0);
const fraction = total / WINDOW;
const incomplete = R.resolution?.status === 'incomplete' || R.counted.some(f => f.missing) || !Number.isFinite(WINDOW) || WINDOW <= 0;
const band = incomplete ? {name:'UNKNOWN', note:'measurement incomplete; total is a lower bound'} : BANDS.find(b => fraction <= b.max);
const exitCode = incomplete ? 3 : band.name === 'GREEN' ? 0 : band.name === 'AMBER' ? 1 : 2;
const campusName = (() => { try { const w = JSON.parse(readText(path.join(root, 'workspace.json')) || '{}'); return (w.business && w.business.name) || w.name || path.basename(root); } catch { return path.basename(root); } })();

if (JSON_OUT) {
  console.log(JSON.stringify({ campus: campusName, root, date: TODAY, window: WINDOW, total_tokens: total,
    fraction: Number(fraction.toFixed(4)), band: band.name, exit: exitCode, section: R.sectionHeading,
    resolution: R.resolution || {status: incomplete ? 'incomplete' : 'complete', findings: []}, files: R.counted, on_demand: R.onDemand, missing: R.missing, notes: R.notes, canon: R.canon.path,
    estimate: 'utf8_bytes/4 (matches PRD per-file figures within 1 token)' }, null, 2));
  process.exit(exitCode);
}

const out = [];
out.push(`Context weight  -  ${campusName}  -  ${TODAY}`);
out.push(`Window ${fmt(WINDOW)} . bands: GREEN <=10% . AMBER 10-20% . RED >20% . tokens ~ utf8 bytes/4 (estimate)`);
if (R.sectionHeading) out.push(`Startup set from: ${R.chief ? path.relative(path.dirname(root), R.chief) : 'workspace.json'} -> "${R.sectionHeading}"`);
out.push('');
out.push('  tokens   lines  file                                          largest section');
for (const f of R.counted) {
  const big = f.missing ? 'MISSING - referenced but not on disk' : `"${f.largest.name.slice(0, 40)}" ${fmt(f.largest.tokens)} (${f.largest.pct}%)`;
  const [name, via] = f.file.split(/\s{2}(?=\(resolved)/);   // keep the canon note on its own line, never truncated
  out.push(`  ${fmt(f.tokens).padStart(6)}  ${String(f.lines).padStart(6)}  ${name.padEnd(44)}  ${big}`);
  if (via) out.push(`  ${''.padStart(16)}${via}`);
}
out.push('  ' + '-'.repeat(6));
out.push(`  ${fmt(total).padStart(6)}  total = ${pct(total, WINDOW).toFixed(1)}% of ${fmt(WINDOW)}  ->  ${band.name} (${band.note})`);
if (R.onDemand.length) {
  out.push('');
  out.push('On-demand reads named in the same section (NOT counted - loaded only when a task needs them):');
  for (const f of R.onDemand) out.push(`  ${fmt(f.tokens).padStart(6)}  ${f.file}`);
}
if (R.missing.length) {
  out.push('');
  out.push('Referenced but not found (counted as 0 - the session will look for these and find nothing):');
  for (const m of R.missing) out.push(`       0  ${m.ref}${m.optional ? '  (on-demand)' : ''}${m.conditional ? '  (conditional: read only if present)' : m.rolling ? '  (date-rolling: absent until the session creates it)' : ''}`);
}
for (const finding of R.resolution?.findings || []) out.push(finding.severity === 'info' ? `note: ${finding.code}: ${finding.path || ''} - ${finding.detail || ''}` : `[!!] ${finding.code}: ${finding.path || finding.detail || ''}`);
if (R.notes.length) { out.push(''); for (const n of R.notes) out.push('note: ' + n); }
console.log(out.join('\n'));
process.exit(exitCode);
