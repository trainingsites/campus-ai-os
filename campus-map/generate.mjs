#!/usr/bin/env node
/**
 * Campus Map — generator (v3.1)
 * --------------------------------------------------------------
 * Reads the file-based campus (no WordPress, no database) and bakes a
 * self-contained, visually compelling dashboard into campus-map.html.
 *
 * Layers (all plain files — tool-agnostic):
 *   - shared/brand-style.md  → brand (name, tagline, colors, fonts)  [auto-detected]
 *   - shared/goals.md        → operating context (OKRs + this week)
 *   - outputs (month) briefs/ → Atlas intelligence (what to work on)
 *   - dean/.activity*.jsonl  → work done (agent runs, all seats) + file links
 *   - .campus-os/registry.json → team directory (v3.1)
 *   - shared/setup-progress.md  → setup progress (v3.1)
 *   - outputs (month) <type> → deliverables (+ folder links)
 *   - wiki/ + wiki/log.md    → second brain (knowledge + recently learned)
 *   - outputs (month) reports/reporting-rollup.json → Atlas outcomes
 *
 * Run:    node campus-map/generate.mjs            (full, private)
 * Out:    campus-map/campus-map.html
 * Dependency-free. Re-run anytime to refresh.
 */

import fs from 'node:fs';
import crypto from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = process.env.CAMPUS_ROOT || path.resolve(__dirname, '..'); // campus workspace root
// Output lands in a `campus-map/` folder under the campus ROOT (NOT the script/plugin dir),
// so the dashboard's relative `../outputs`, `../wiki` links resolve and the buyer can find it.
// When run from James's own campus (CAMPUS_ROOT unset) this is the same campus-map/ folder as before.
const OUT_DIR = process.env.CAMPUS_MAP_OUT || path.join(ROOT, 'campus-map');
const MIN_PER_RUN = Number(process.env.MIN_PER_RUN || 35);
// 5.2.8: the Campus Map is private-only. The public/sales-demo build was
// retired by owner decision after the 5.2.5 security audit; a private map is
// never shared, so nothing here needs a "safe for strangers" mode.
if (process.argv.includes('--public') || process.env.PUBLIC === '1') {
  console.error('Campus Map: --public was retired in 5.2.8. The map is private-only; build without the flag.');
  process.exit(2);
}
// Remote fonts are the page's only network request (SEC-07). Off whenever the
// owner asks; the page falls back to system fonts.
const REMOTE_FONTS = !process.argv.includes('--no-remote-fonts') && process.env.CAMPUS_MAP_OFFLINE !== '1';

const DEPTS = {
  dean:      { name: 'Dean — Chief Orchestrator', short: 'Dean', icon: '⚙️', accent: '#0B4F6C' },
  marketing: { name: 'Marketing',  short: 'Marketing',  icon: '📣', accent: '#0B4F6C' },
  education: { name: 'Education',   short: 'Education',   icon: '🎓', accent: '#20BF55' },
  community: { name: 'Community',   short: 'Community',   icon: '👥', accent: '#6EC1E4' },
  sales:     { name: 'Sales',       short: 'Sales',       icon: '💼', accent: '#0E8C40' },
};
const DEPT_ORDER = ['marketing', 'education', 'community', 'sales'];

// ---- helpers -------------------------------------------------------------
function titleCase(s) { return String(s).replace(/[-_]/g, ' ').replace(/\b\w/g, c => c.toUpperCase()); }
// strip a date prefix (YYYY-MM-DD- or YYYYMMDD-) and a trailing -hex4 run suffix, then title-case
function cleanLabel(s) { return titleCase(String(s).replace(/^\d{4}-\d{2}-\d{2}-/, '').replace(/^\d{8}-/, '').replace(/-[0-9a-f]{4}$/i, '')); }

const PATH_ROOTS = /^(outputs|active-work|wiki|library|dean|shared|monitoring|inputs|daily|marketing-manager|sales-manager|education-manager|community-manager)\b/;
// Ledger paths are untrusted input (any seat, any tool can write them). A
// link is only emitted when it is a plain relative path under a known campus
// root with no traversal segments, no absolute/UNC form, no URL scheme, and no
// control characters. Anything else drops to "no link" rather than "best effort".
function relHref(p) {
  if (!p || typeof p !== 'string') return '';
  let s = p.trim().replace(/^\.\//, '').replace(/^Claude-Cowork\//, '');
  if (!s || /[\x00-\x1f\x7f]/.test(s)) return '';
  if (/^[a-z][a-z0-9+.-]*:/i.test(s) || /^[\/\\]/.test(s) || /^[a-z]:/i.test(s)) return '';
  s = s.replace(/\\/g, '/');
  const segs = s.split('/');
  if (segs.some(seg => seg === '' || seg === '.' || seg === '..')) return '';
  if (segs.length < 2) return '';
  if (!PATH_ROOTS.test(s)) return '';
  return '../' + s;
}
// Resolve a relHref() result to an absolute path, then prove the real file
// (symlinks followed) still lives under the campus root. Returns '' otherwise.
function safeDocPath(relH) {
  if (!relH || !relH.startsWith('../')) return '';
  const rootReal = fs.realpathSync(ROOT);
  const abs = path.resolve(ROOT, relH.slice(3));
  if (!abs.startsWith(path.resolve(ROOT) + path.sep) && !abs.startsWith(rootReal + path.sep)) return '';
  let real; try { real = fs.realpathSync(abs); } catch { return ''; }
  if (!real.startsWith(rootReal + path.sep)) return '';
  let st; try { st = fs.statSync(real); } catch { return ''; }
  if (!st.isFile()) return '';
  return real;
}

// ---- inline document viewer: pre-render linked md/json/txt to clean HTML --
const DOCS = {};
let docSeq = 0;
function escHtml(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;'); }
// Markdown link targets come from files any seat can write. Only relative
// paths and http(s)/mailto URLs survive; javascript:, data:, vbscript: and
// anything with control characters render as plain text instead of a link.
function safeMdHref(h) {
  const s = String(h).trim();
  if (!s || /[\x00-\x20\x7f]/.test(s)) return '';
  const m = s.match(/^([a-z][a-z0-9+.-]*):/i);
  if (m && !/^(https?|mailto)$/i.test(m[1])) return '';
  if (/^\/\//.test(s)) return '';
  return s;
}
function mdInline(s) {
  return s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
          .replace(/(^|[^*])\*([^*]+)\*/g, '$1<em>$2</em>')
          .replace(/`([^`]+)`/g, '<code>$1</code>')
          .replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, txt, href) => { const h = safeMdHref(href); return h ? '<a href="' + h + '" rel="noopener">' + txt + '</a>' : txt; });
}
function mdToHtml(md) {
  const lines = md.split(/\r?\n/); const out = []; let inCode = false, inList = false;
  for (const ln of lines) {
    if (/^```/.test(ln)) { if (inCode) { out.push('</code></pre>'); inCode = false; } else { if (inList) { out.push('</ul>'); inList = false; } out.push('<pre><code>'); inCode = true; } continue; }
    if (inCode) { out.push(escHtml(ln)); continue; }
    if (/^\s*$/.test(ln)) { if (inList) { out.push('</ul>'); inList = false; } continue; }
    const h = ln.match(/^(#{1,6})\s+(.*)$/);
    if (h) { if (inList) { out.push('</ul>'); inList = false; } const lv = h[1].length; out.push('<h' + lv + '>' + mdInline(escHtml(h[2])) + '</h' + lv + '>'); continue; }
    const li = ln.match(/^\s*[-*]\s+(.*)$/);
    if (li) { if (!inList) { out.push('<ul>'); inList = true; } out.push('<li>' + mdInline(escHtml(li[1])) + '</li>'); continue; }
    if (inList) { out.push('</ul>'); inList = false; }
    out.push('<p>' + mdInline(escHtml(ln)) + '</p>');
  }
  if (inList) out.push('</ul>'); if (inCode) out.push('</code></pre>');
  return out.join('\n');
}
function addDoc(relH, title) {
  if (!relH || !/\.(md|json|txt)$/i.test(relH)) return '';
  const abs = safeDocPath(relH);
  if (!abs) return '';
  let raw; try { raw = fs.readFileSync(abs, 'utf8'); } catch { return ''; }
  if (raw.length > 80000) raw = raw.slice(0, 80000) + '\n\n…(truncated — use “open raw file” for the rest)';
  const ext = (relH.match(/\.(\w+)$/) || [])[1].toLowerCase();
  let html;
  if (ext === 'json') { let p; try { p = JSON.stringify(JSON.parse(raw), null, 2); } catch { p = raw; } html = '<pre class="doc-json">' + escHtml(p) + '</pre>'; }
  else if (ext === 'md') html = mdToHtml(raw);
  else html = '<pre>' + escHtml(raw) + '</pre>';
  const id = 'd' + (++docSeq);
  DOCS[id] = { title: title || path.basename(relH), html, href: relH };
  return id;
}

// Seat Contract Phase 2: the primary seat writes dean/.activity.jsonl; each
// satellite seat writes its own dean/.activity.{seat}.jsonl. Reading is
// permissive — merge every shard present — so the map shows the whole campus's
// work, not just the primary's. Canon: .campus-os/ledger-paths.md.
function ledgerFiles() {
  const dir = path.join(ROOT, 'dean');
  const primary = path.join(dir, '.activity.jsonl');
  const files = fs.existsSync(primary) ? [primary] : [];
  if (fs.existsSync(dir)) {
    for (const f of fs.readdirSync(dir).sort()) {
      if (f.startsWith('.activity.') && f.endsWith('.jsonl') && f !== '.activity.jsonl') {
        files.push(path.join(dir, f));
      }
    }
  }
  return files;
}

function readLedger() {
  const out = [];
  const files = ledgerFiles();
  for (const p of files) {
  // A line with no `seat` predates the stamp and belongs to the primary seat.
  const shard = path.basename(p);
  const defaultSeat = shard === '.activity.jsonl' ? 'primary'
    : shard.slice('.activity.'.length, -'.jsonl'.length);
  for (const raw of fs.readFileSync(p, 'utf8').split('\n')) {
    const line = raw.trim();
    if (!line || line.startsWith('#')) continue;
    let o; try { o = JSON.parse(line); } catch { continue; }
    const ts = o.ts || o.timestamp || o.date || null;
    const skill = o.skill || 'ad-hoc';
    let dept = (o.dept || '').toLowerCase();
    if (!dept || !DEPTS[dept]) dept = inferDept(skill, o.trigger || o.action || '');
    const rawOutcome = (o.outcome || o.status || '').toString().toLowerCase();
    const ok = /complete|success|done/.test(rawOutcome) || rawOutcome === '';
    const text = o.trigger || o.action || (o.outputs && o.outputs.report) ||
      (Array.isArray(o.artifacts) && o.artifacts.join(', ')) || skill;
    let href = '';
    if (o.outputs && typeof o.outputs.report === 'string') href = relHref(o.outputs.report);
    if (!href && typeof o.output === 'string') href = relHref(o.output);
    if (!href && Array.isArray(o.files_touched)) for (const f of o.files_touched) { href = relHref(f); if (href) break; }
    if (!href && Array.isArray(o.artifacts)) for (const a of o.artifacts) { href = relHref(a); if (href) break; }
    out.push({ ts, date: ts ? ts.slice(0, 10) : '', skill, dept, ok, text: String(text), href,
      seat: o.seat || defaultSeat });
  }
  }
  // Sort ONLY when shards were actually merged. A single-seat campus must come
  // out byte-identical to the pre-shard reader — the file's own order is the
  // record, and re-sorting it would be a behavior change disguised as a fix.
  // (Caught by the false-positive guard: two same-day entries swapped.)
  if (files.length > 1) out.sort((a, b) => String(a.ts || '').localeCompare(String(b.ts || '')));
  return out;
}

function inferDept(skill, text) {
  // Keyword map is pack-flavored (education-pack defaults). Pack-supplied
  // keyword maps are a v5.1 candidate; unmatched work falls to 'dean' safely.
  const s = (skill + ' ' + text).toLowerCase();
  if (/community|ambassador|member|discussion|feed/.test(s)) return 'community';
  if (/course|lesson|class|teach|education|prep|3p|present/.test(s)) return 'education';
  if (/sales|proposal|offer|outbound|cart|pricing|crm/.test(s)) return 'sales';
  if (/youtube|title|social|content|newsletter|email|tam|flywheel|marketing/.test(s)) return 'marketing';
  return 'dean';
}

function scanOutputs() {
  const base = path.join(ROOT, 'outputs');
  const byType = {}; const byMonth = {}; const typeLatest = {}; let total = 0;
  if (!fs.existsSync(base)) return { byType, byMonth, typeLatest, total };
  for (const month of fs.readdirSync(base)) {
    if (!/^\d{4}-\d{2}$/.test(month)) continue;
    const mdir = path.join(base, month);
    if (!fs.statSync(mdir).isDirectory()) continue;
    let mCount = 0;
    for (const type of fs.readdirSync(mdir)) {
      const tdir = path.join(mdir, type);
      let st; try { st = fs.statSync(tdir); } catch { continue; }
      if (!st.isDirectory()) continue;
      const n = countFiles(tdir);
      if (n === 0) continue;
      byType[type] = (byType[type] || 0) + n;
      if (!typeLatest[type] || month > typeLatest[type]) typeLatest[type] = month;
      mCount += n; total += n;
    }
    if (mCount) byMonth[month] = mCount;
  }
  return { byType, byMonth, typeLatest, total };
}

function countFiles(dir, depth = 0) {
  let n = 0;
  let entries; try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return 0; }
  for (const e of entries) {
    if (e.name.startsWith('.')) continue;
    if (e.isFile()) n++;
    else if (e.isDirectory() && depth < 2) n += countFiles(path.join(dir, e.name), depth + 1);
  }
  return n;
}

// ---- brand: shared/brand-style.md (auto-detected, falls back to defaults) -
function parseBrand() {
  const out = {
    name: 'Your Campus', tagline: 'One person. A full AI team.',
    colors: { navy: '#0B4F6C', green: '#20BF55', sky: '#6EC1E4' },
    headingFont: 'Comfortaa', bodyFont: 'Roboto',
    fontImport: 'https://fonts.googleapis.com/css2?family=Comfortaa:wght@400;500;700&family=Roboto:wght@400;500;700&display=swap',
  };
  const candidates = ['brand-style.md', 'BRAND.md'];
  for (const file of candidates) {
    const p = path.join(ROOT, 'shared', file);
    if (!fs.existsSync(p)) continue;
    const t = fs.readFileSync(p, 'utf8');
    const g = re => { const m = t.match(re); return m ? m[1].trim().replace(/^["']|["']$/g, '') : null; };
    out.name = g(/brand_name:\s*(.+)/) || out.name;
    out.tagline = g(/tagline:\s*(.+)/) || out.tagline;
    out.colors.navy = g(/primary:\s*"?(#[0-9a-fA-F]{6})/) || out.colors.navy;
    out.colors.green = g(/success:\s*"?(#[0-9a-fA-F]{6})/) || out.colors.green;
    out.colors.sky = g(/highlight:\s*"?(#[0-9a-fA-F]{6})/) || out.colors.sky;
    out.headingFont = g(/font_heading:\s*"?([^"\n]+)/) || out.headingFont;
    out.bodyFont = g(/font_body:\s*"?([^"\n]+)/) || out.bodyFont;
    out.fontImport = g(/font_import:\s*"?(https:[^"\n]+)/) || out.fontImport;
    break; // first match wins
  }
  // shared/brand-style.md is owner-editable and therefore untrusted for markup.
  // Names are escaped at the sink; CSS/URL fields must match a narrow grammar
  // or fall back to the default (never a best-effort interpolation).
  const FONT_OK = /^[A-Za-z0-9][A-Za-z0-9 _-]{0,39}$/;
  if (!FONT_OK.test(out.headingFont)) out.headingFont = 'Comfortaa';
  if (!FONT_OK.test(out.bodyFont)) out.bodyFont = 'Roboto';
  if (!/^https:\/\/fonts\.googleapis\.com\/css2?\?[A-Za-z0-9=;:@,&+%._-]+$/.test(out.fontImport)) {
    out.fontImport = 'https://fonts.googleapis.com/css2?family=Comfortaa:wght@400;500;700&family=Roboto:wght@400;500;700&display=swap';
  }
  out.name = String(out.name).slice(0, 120);
  out.tagline = String(out.tagline).slice(0, 200);
  out.logo = String(out.name).replace(/^https?:\/\//, '').charAt(0).toUpperCase() || 'C';
  return out;
}

// ---- orchestrator name: about-me/dean-name.md (buyer may rename "Dean") ----
function parseOrchestratorName() {
  const p = path.join(ROOT, 'about-me', 'dean-name.md');
  if (!fs.existsSync(p)) return 'Dean';
  let raw; try { raw = fs.readFileSync(p, 'utf8'); } catch { return 'Dean'; }
  // accept either a `name:`/`dean_name:` field or the first plain, non-heading line
  const field = raw.match(/^\s*(?:dean_name|orchestrator|name)\s*:\s*(.+)$/im);
  if (field) return field[1].trim().replace(/^["']|["']$/g, '') || 'Dean';
  for (const ln of raw.split(/\r?\n/)) {
    const t = ln.trim();
    if (!t || t.startsWith('#') || t.startsWith('-') || t.startsWith('>') || t.startsWith('|')) continue;
    return t.replace(/^["']|["']$/g, '');
  }
  return 'Dean';
}

// ---- context: shared/goals.md (OKRs + This Week's Focus) -----------------
function parseGoals() {
  const p = path.join(ROOT, 'shared', 'goals.md');
  if (!fs.existsSync(p)) return null;
  const txt = fs.readFileSync(p, 'utf8');
  const okrs = [];
  const re = /^\|\s*(\d)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(.+?)\s*\|\s*$/gm;
  let m;
  while ((m = re.exec(txt))) {
    const status = m[4];
    const emoji = (status.match(/🟢|🟡|🔴|⚪/) || [''])[0];
    const state = emoji === '🟢' ? 'green' : emoji === '🟡' ? 'amber' : emoji === '🔴' ? 'red' : 'gray';
    okrs.push({ n: m[1], objective: m[2].trim(), state, text: status.replace(/🟢|🟡|🔴|⚪/g, '').trim() });
  }
  let mode = '', items = [], week = '';
  const fIdx = txt.indexOf("## This Week's Focus");
  if (fIdx >= 0) {
    const next = txt.indexOf('\n## ', fIdx + 5);
    const sec = txt.slice(fIdx, next > 0 ? next : txt.length);
    const wk = sec.match(/\*Week of ([^*]+)\*/); if (wk) week = wk[1].trim();
    const md = sec.match(/\*\*Mode:\s*([^*]+)\*\*/); if (md) mode = md[1].trim();
    const bullets = sec.match(/^- \[[ x]\] (.+)$/gm) || [];
    items = bullets.map(b => {
      const t = b.replace(/^- \[[ x]\] /, '');
      const bm = t.match(/^\*\*(.+?)\*\*\s*[—-]\s*(.+)$/);
      return bm ? { title: bm[1].trim(), desc: bm[2].trim() }
                : { title: t.replace(/\*\*/g, '').replace(/—.*/, '').trim(), desc: '' };
    });
  }
  return { okrs, focus: { mode, items, week } };
}

// ---- knowledge: wiki/ ----------------------------------------------------
function scanWiki() {
  const base = path.join(ROOT, 'wiki');
  if (!fs.existsSync(base)) return null;
  const byCat = {}; let total = 0;
  for (const d of fs.readdirSync(base)) {
    const dir = path.join(base, d);
    let st; try { st = fs.statSync(dir); } catch { continue; }
    if (!st.isDirectory()) continue;
    const n = countFiles(dir);
    if (n > 0) { byCat[d] = n; total += n; }
  }
  if (total === 0) return null; // empty wiki → hide the Second Brain panel (progressive)
  const learned = [];
  const logp = path.join(base, 'log.md');
  if (fs.existsSync(logp)) {
    for (const ln of fs.readFileSync(logp, 'utf8').split('\n')) {
      const m = ln.match(/^##\s*\[(\d{4}-\d{2}-\d{2})\]\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(.+)$/);
      if (m) learned.push({ date: m[1], dept: m[2].trim(), title: m[4].trim() });
    }
  }
  learned.reverse();
  return { total, byCat, learned: learned.slice(0, 8) };
}

// ---- intelligence: outputs/*/briefs/ (Atlas front) -----------------------
function scanBriefs() {
  const base = path.join(ROOT, 'outputs');
  if (!fs.existsSync(base)) return [];
  const seen = {};
  for (const month of fs.readdirSync(base)) {
    const bdir = path.join(base, month, 'briefs');
    let st; try { st = fs.statSync(bdir); } catch { continue; }
    if (!st.isDirectory()) continue;
    for (const f of fs.readdirSync(bdir)) {
      if (!/\.(md|json)$/.test(f)) continue;
      const slug = f.replace(/\.(md|json)$/, '').replace(/-(strategy-brief|council-brief|mandate|brief)$/i, '');
      const date = (slug.match(/(\d{4}-\d{2}-\d{2})/) || [null, month])[1] || month;
      let title = slug.replace(/^\d{4}-\d{2}-\d{2}-?/, '').replace(/^\d{8}-/, '')
        .replace(/-[0-9a-f]{4}$/i, '').replace(/[-_]/g, ' ').trim();
      if (!title) continue;
      title = title.replace(/\b\w/g, c => c.toUpperCase());
      const key = slug.toLowerCase();
      const href = '../outputs/' + month + '/briefs/' + f;
      const prefMd = /\.md$/.test(f);
      if (!seen[key] || date > seen[key].date || (prefMd && !seen[key].md)) seen[key] = { date, title, href, md: prefMd };
    }
  }
  return Object.values(seen).sort((a, b) => b.date.localeCompare(a.date)).slice(0, 6)
    .map(b => ({ date: b.date, title: b.title, href: b.href }));
}

// ---- outcomes: raw results.json back-sockets (Atlas-independent) ----------
// Reads every team's results.json directly (Team Interop Spec back socket) so the
// panel reflects ALL shipped work, not a stale pre-aggregated roll-up. When an Atlas
// reporting-rollup.json exists, rows are ENRICHED with brief score + recommendation
// by run_id — but the roll-up is no longer required for the panel to populate.
function findResultsFiles(base) {
  const out = [];
  (function walk(dir, depth) {
    let ents; try { ents = fs.readdirSync(dir, { withFileTypes: true }); } catch { return; }
    for (const e of ents) {
      if (e.name.startsWith('.')) continue;
      const fp = path.join(dir, e.name);
      if (e.isFile()) { if (e.name === 'results.json') out.push(fp); }
      else if (e.isDirectory() && depth < 6) walk(fp, depth + 1);
    }
  })(base, 0);
  return out;
}
function readReporting() {
  const base = path.join(ROOT, 'outputs');
  if (!fs.existsSync(base)) return null;

  // optional enrichment + a "view report" link if Atlas left a roll-up
  const rollup = {}; let generated = '', rollupHref = '';
  for (const month of fs.readdirSync(base).sort()) {
    const p = path.join(base, month, 'reports', 'reporting-rollup.json');
    if (!fs.existsSync(p)) continue;
    try {
      const j = JSON.parse(fs.readFileSync(p, 'utf8'));
      (j.topics || []).forEach(t => { if (t.run_id) rollup[t.run_id] = t; });
      generated = j.generated || generated;
      rollupHref = '../outputs/' + month + '/reports/reporting-rollup.json';
    } catch { /* ignore malformed roll-up */ }
  }

  const files = findResultsFiles(base);
  if (!files.length && !Object.keys(rollup).length) return null;

  const rows = []; const seen = {};
  for (const fp of files) {
    let j; try { j = JSON.parse(fs.readFileSync(fp, 'utf8')); } catch { continue; }
    const runId = j.run_id || '';
    const assets = Array.isArray(j.assets) ? j.assets : [];
    const total = assets.length;
    if (!j.slug && !runId && total === 0) continue; // skip identity-less stub ledgers
    if (runId) { if (seen[runId]) continue; seen[runId] = 1; }
    const pub = assets.filter(a => /publish|live|sent|scheduled/i.test(String(a.status || ''))).length;
    const r = rollup[runId];
    const score = (r && r.brief_score != null) ? r.brief_score : '—';
    const signal = (r && r.recommendation && r.recommendation.signal) || (pub > 0 ? 'shipped' : 'staged');
    rows.push({
      label: cleanLabel(j.slug || runId || 'run'),
      teams: j.team ? titleCase(j.team) : ((r && (r.teams_touched || []).map(titleCase).join(', ')) || '—'),
      score, assets: pub + '/' + total, signal,
      date: (j.generated_at || '').slice(0, 10),
    });
  }
  // include roll-up topics that have no results.json on disk (don't lose history)
  for (const runId in rollup) {
    if (seen[runId]) continue;
    const t = rollup[runId];
    rows.push({
      label: cleanLabel(t.slug || runId), teams: (t.teams_touched || []).map(titleCase).join(', ') || '—',
      score: (t.brief_score == null ? '—' : t.brief_score),
      assets: (t.assets_published || 0) + '/' + (t.assets_total || 0),
      signal: (t.recommendation && t.recommendation.signal) || t.verdict || '—', date: '',
    });
  }
  rows.sort((a, b) => (b.date || '').localeCompare(a.date || ''));
  return { present: true, generated, count: rows.length, rows: rows.slice(0, 12), href: rollupHref };
}


// ---- team directory: .campus-os/registry.json (v3.1) ----------------------
function readTeamDirectory() {
  const p = path.join(ROOT, '.campus-os', 'registry.json');
  if (!fs.existsSync(p)) return null;
  let j; try { j = JSON.parse(fs.readFileSync(p, 'utf8')); } catch { return null; }
  const teams = Array.isArray(j.teams) ? j.teams : [];
  if (!teams.length) return null;
  return teams.map(t => ({
    name: String(t.team || t.name || 'unknown'),
    type: String(t.type || (t.source === 'kernel' ? 'kernel' : 'team')),
    status: String(t.status || 'active'),
    version: String(t.version || ''),
    owns: String(t.owns || t.purpose || ''),
    triggers: Array.isArray(t.triggers) ? t.triggers.slice(0, 3) : [],
  }));
}

// ---- staff org headcount: .campus-os/registry.json (v4.1) -----------------
// Employees = sum of type:department employees[] + any team entry's matching
// department field (de-duped). Campus systems = type:systems systems[] length.
function readStaffOrg() {
  const p = path.join(ROOT, '.campus-os', 'registry.json');
  if (!fs.existsSync(p)) return null;
  let j; try { j = JSON.parse(fs.readFileSync(p, 'utf8')); } catch { return null; }
  const teams = Array.isArray(j.teams) ? j.teams : [];
  // Departments derive from the registry's own type:department entries (any
  // niche pack's roster counts). The fixed list is only a fallback for older
  // registries that predate department records (education-pack defaults).
  const deptEntries = teams.filter(t => t.type === 'department');
  const EMP = deptEntries.length
    ? deptEntries.map(t => String(t.department || t.team))
    : ['marketing', 'sales', 'community', 'education', 'dean-office'];
  const FALLBACK_LBL = { marketing: 'Marketing', sales: 'Sales', community: 'Community', education: 'Education', 'dean-office': "Dean's office" };
  const LBL = {}; EMP.forEach(d => { LBL[d] = FALLBACK_LBL[d] || d; });
  deptEntries.forEach(t => { const d = String(t.department || t.team); if (t.label) LBL[d] = String(t.label); });
  const seen = new Set(); const byDept = {}; EMP.forEach(d => { byDept[d] = 0; });
  teams.forEach(t => {
    if (t.type === 'department' && Array.isArray(t.employees)) {
      const d = t.department || t.team;
      t.employees.forEach(n => { if (!seen.has(n)) { seen.add(n); if (byDept[d] != null) byDept[d]++; } });
    }
  });
  teams.forEach(t => {
    if (t.type === 'department' || t.type === 'systems' || t.type === 'kernel') return;
    const d = t.department, n = t.team || t.name;
    if (byDept[d] != null && n && !seen.has(n)) { seen.add(n); byDept[d]++; }
  });
  let employees = 0; EMP.forEach(d => { employees += byDept[d]; });
  const sysEntry = teams.find(t => t.type === 'systems');
  const systems = sysEntry && Array.isArray(sysEntry.systems) ? sysEntry.systems.length : 0;
  const playbooks = Array.isArray(j.playbooks) ? j.playbooks.length : 0;
  if (!employees && !systems) return null;
  const parts = EMP.filter(d => byDept[d] > 0).map(d => LBL[d] + ' ' + byDept[d]);
  return { employees, systems, playbooks, parts,
           line: employees + ' employees + ' + systems + ' campus systems + ' + playbooks + ' playbooks' };
}

// ---- setup progress: shared/setup-progress.md (v3.1) ----------------------
function readSetupProgress() {
  const p = path.join(ROOT, 'shared', 'setup-progress.md');
  if (!fs.existsSync(p)) return null;
  const t = fs.readFileSync(p, 'utf8');
  let done = 0, total = 0;
  for (const ln of t.split('\n')) {
    const m = ln.match(/^\s*[-*]\s*\[( |x|X)\]/);
    if (!m) continue;
    total++; if (m[1].toLowerCase() === 'x') done++;
  }
  if (!total) return null;
  return { done, total, pct: Math.round((done / total) * 100) };
}

// ---- scheduled task registry: scheduled/*.md (no WordPress) ---------------
function scanScheduled(ledger) {
  const dir = path.join(ROOT, 'scheduled');
  if (!fs.existsSync(dir)) return [];
  const items = [];
  for (const f of fs.readdirSync(dir)) {
    if (!/\.md$/.test(f)) continue;
    const slug = f.replace(/\.md$/, '');
    if (slug.toLowerCase() === 'readme') continue;
    let last = '', ok = true, found = false;
    for (const r of ledger) {
      const rs = (r.skill || '').toLowerCase();
      if (rs === slug || (slug.length > 5 && rs.indexOf(slug) >= 0) || (rs.length > 5 && slug.indexOf(rs) >= 0)) {
        if (r.date > last) { last = r.date; ok = r.ok; found = true; }
      }
    }
    items.push({ name: titleCase(slug), last, state: found ? (ok ? 'green' : 'red') : 'idle' });
  }
  return items.sort((a, b) => (b.last || '').localeCompare(a.last || ''));
}

// ---- build the data ------------------------------------------------------
const brand = parseBrand();
const orchestrator = parseOrchestratorName();
const ledger = readLedger();
const outputs = scanOutputs();

const deptStats = {};
for (const k of Object.keys(DEPTS)) deptStats[k] = { runs: 0, skills: {}, last: '' };
for (const r of ledger) {
  const d = deptStats[r.dept] || deptStats.dean;
  d.runs++;
  const sk = r.skill === 'ad-hoc' ? 'Ad-hoc workflow' : titleCase(r.skill.split(':').pop());
  d.skills[sk] = (d.skills[sk] || 0) + 1;
  if (r.ts && r.ts > d.last) d.last = r.ts;
}

const totalRuns = ledger.length || 1;
const departments = DEPT_ORDER.map(k => {
  const meta = DEPTS[k]; const st = deptStats[k];
  const skills = Object.entries(st.skills).sort((a, b) => b[1] - a[1]).slice(0, 5)
    .map(([name, count]) => ({ name, count }));
  return {
    key: k, name: meta.name, short: meta.short, icon: meta.icon, accent: meta.accent,
    runs: st.runs, deliverables: Math.round(outputs.total * (st.runs / totalRuns)),
    skills, lastActive: st.last ? st.last.slice(0, 10) : '—',
  };
});

const dates = ledger.map(r => r.date).filter(Boolean).sort();
const span = dates.length ? dates[0] + ' → ' + dates[dates.length - 1] : '';

const feed = [...ledger].reverse().slice(0, 22).map(r => ({
  date: r.date, deptName: DEPTS[r.dept] ? DEPTS[r.dept].short : 'Dean',
  accent: DEPTS[r.dept] ? DEPTS[r.dept].accent : '#0B4F6C',
  text: r.text.length > 150 ? r.text.slice(0, 147) + '…' : r.text, ok: r.ok, href: r.href,
}));

const deliverables = Object.entries(outputs.byType).sort((a, b) => b[1] - a[1]).map(([type, count]) => ({
  type: titleCase(type), count,
  href: outputs.typeLatest[type] ? '../outputs/' + outputs.typeLatest[type] + '/' + type : '',
}));

let context = parseGoals();
const knowledge = scanWiki();
const intelligence = scanBriefs();
const outcomes = readReporting();
const sharedDir = path.join(ROOT, 'shared');
const sharedFiles = fs.existsSync(sharedDir) ? fs.readdirSync(sharedDir).filter(f => f.endsWith('.md')).length : 0;

// pre-render linked text/json files into a clean inline viewer
intelligence.forEach(b => { b.doc = addDoc(b.href, b.title); });
feed.forEach(x => { if (x.href) x.doc = addDoc(x.href, x.text); });
if (outcomes && outcomes.href) outcomes.doc = addDoc(outcomes.href, 'Atlas reporting roll-up');

// ---- operations: skill health, this-week, scheduled registry (file-based) -
const healthMap = {};
for (const r of ledger) {
  const k = r.skill === 'ad-hoc' ? 'Ad-hoc workflow' : titleCase(r.skill.split(':').pop());
  const h = healthMap[k] || (healthMap[k] = { runs: 0, ok: 0 });
  h.runs++; if (r.ok) h.ok++;
}
const skillHealth = Object.entries(healthMap).sort((a, b) => b[1].runs - a[1].runs).slice(0, 10)
  .map(([name, h]) => { const rate = h.ok / h.runs; return { name, runs: h.runs, issues: h.runs - h.ok, state: rate >= 0.9 ? 'green' : rate >= 0.6 ? 'amber' : 'red' }; });

const days = []; const byDay = {};
for (let i = 6; i >= 0; i--) { const d = new Date(Date.now() - i * 864e5).toISOString().slice(0, 10); days.push(d); byDay[d] = 0; }
const wkCut = days[0]; const wk = { runs: 0, ok: 0, issues: 0, byDept: {} };
for (const r of ledger) {
  if (r.date && r.date >= wkCut) {
    wk.runs++; if (r.ok) wk.ok++; else wk.issues++;
    wk.byDept[r.dept] = (wk.byDept[r.dept] || 0) + 1;
    if (byDay[r.date] != null) byDay[r.date]++;
  }
}
const busiest = Object.entries(wk.byDept).sort((a, b) => b[1] - a[1])[0];
const week = {
  runs: wk.runs, ok: wk.ok, issues: wk.issues,
  busiest: busiest ? DEPTS[busiest[0]].short + ' (' + busiest[1] + ')' : '—',
  byDay: days.map(d => ({ date: d, count: byDay[d] })),
};
const scheduled = scanScheduled(ledger);
const directory = readTeamDirectory();
const staff = readStaffOrg();
const setupProgress = readSetupProgress();

const data = {
  campus: { name: brand.name, orchestrator, tagline: brand.tagline,
            logo: brand.logo, generatedAt: new Date().toISOString() },
  totals: {
    runs: ledger.length, deliverables: outputs.total,
    hoursSaved: Math.round((ledger.length * MIN_PER_RUN) / 60),
    departments: DEPT_ORDER.filter(k => deptStats[k].runs > 0).length,
    knowledgePages: knowledge ? knowledge.total : 0, sharedFiles, minPerRun: MIN_PER_RUN, span,
  },
  outputsHref: '../outputs',
  context, intelligence, departments, feed, knowledge, outcomes, deliverables,
  skillHealth, week, scheduled, directory, staff, setupProgress, docs: DOCS,
};

// ---- render --------------------------------------------------------------
function renderHTML(DATA_JSON, b) {
  const script = '\nconst DATA = ' + DATA_JSON.replace(/</g, '\\u003c') + ';\n' + CLIENT_JS + '\n';
  const scriptHash = 'sha256-' + crypto.createHash('sha256').update(script, 'utf8').digest('base64');
  // Only the generator's own inline script may run; any markup that slips into
  // the page from campus data is inert under this policy. The doc viewer window
  // (about:blank) inherits it from its opener.
  const csp = "default-src 'none'; script-src '" + scriptHash + "'; style-src 'unsafe-inline'" +
    (REMOTE_FONTS ? " https://fonts.googleapis.com; font-src https://fonts.gstatic.com" : '') +
    "; img-src data:; base-uri 'none'; form-action 'none'; object-src 'none'";
  const fonts = REMOTE_FONTS
    ? '<link rel="preconnect" href="https://fonts.googleapis.com">\n' +
      '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n' +
      '<link href="' + escHtml(b.fontImport) + '" rel="stylesheet">\n'
    : '';
  const overrides =
    ':root{--navy:' + b.colors.navy + ';--green:' + b.colors.green + ';--sky:' + b.colors.sky + ';}' +
    "body{font-family:'" + b.bodyFont + "',system-ui,sans-serif}" +
    "h1,h2,h3,.cm-num,.cm-kcat b,.cm-card-nums b,.cm-bar-num,.cm-panel-h,.cm-logo,.cm-side-name{font-family:'" + b.headingFont + "',system-ui,sans-serif}";
  return '<!doctype html>\n<html lang="en" data-theme="dark">\n<head>\n' +
    '<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n' +
    '<meta http-equiv="Content-Security-Policy" content="' + csp + '">\n' +
    '<title>Campus Map — ' + escHtml(b.name) + '</title>\n' + fonts +
    '<style>\n' + CSS + '\n</style>\n<style>' + overrides + '</style>\n' +
    '</head>\n<body>\n<aside id="cm-side"></aside>\n<main id="cm-main"></main>\n' +
    '<script>' + script + '</script>\n</body>\n</html>\n';
}

const CSS = `
:root{ --navy:#0B4F6C; --green:#20BF55; --sky:#6EC1E4; --mist:#F0F7FB; --ink:#1c2b33; }
html{scroll-behavior:smooth}
html[data-theme=dark]{ --bg1:#06222f; --bg2:#0b3142; --panel:rgba(255,255,255,.05); --panel2:rgba(255,255,255,.08);
  --side:#072733; --txt:#eaf4f8; --mut:#8fb4c4; --line:rgba(255,255,255,.10); --shadow:0 18px 50px rgba(0,0,0,.40); }
html[data-theme=light]{ --bg1:#eef6fb; --bg2:#dcebf6; --panel:#ffffff; --panel2:#f3f9fc;
  --side:#ffffff; --txt:#13313f; --mut:#5d7d8b; --line:#dce8ef; --shadow:0 14px 38px rgba(11,79,108,.10); }
*{box-sizing:border-box;margin:0;padding:0}
body{ color:var(--txt); background:radial-gradient(1200px 700px at 60% -10%, var(--bg2), var(--bg1)) fixed; min-height:100vh; line-height:1.45; }
h1,h2,h3{font-weight:700;letter-spacing:-.5px}
a{color:inherit}

/* sidebar */
#cm-side{position:fixed;top:0;left:0;width:232px;height:100vh;overflow:auto;padding:22px 16px;
  background:var(--side);border-right:1px solid var(--line);display:flex;flex-direction:column;gap:20px;z-index:10}
.cm-side-brand{display:flex;gap:12px;align-items:center}
.cm-logo{width:46px;height:46px;border-radius:13px;display:grid;place-items:center;font-weight:700;font-size:22px;color:#fff;
  background:linear-gradient(135deg,var(--navy),var(--green));flex:none}
.cm-side-name{font-size:17px;font-weight:700;line-height:1.1}
.cm-side-kicker{font-size:10px;letter-spacing:2.5px;color:var(--mut);margin-top:2px}
.cm-nav{display:flex;flex-direction:column;gap:2px}
.cm-nav a{display:flex;gap:11px;align-items:center;padding:9px 11px;border-radius:10px;color:var(--mut);
  text-decoration:none;font-size:13.5px;cursor:pointer;transition:.15s}
.cm-nav a:hover{background:var(--panel2);color:var(--txt)}
.cm-nav a.active{background:color-mix(in srgb,var(--green) 16%,transparent);color:var(--txt);font-weight:600}
.cm-nav-icon{width:18px;text-align:center;font-size:14px;opacity:.85}
.cm-side-foot{margin-top:auto;display:flex;flex-direction:column;gap:2px;border-top:1px solid var(--line);padding-top:12px}
.cm-side-foot a{display:flex;gap:11px;align-items:center;padding:8px 11px;border-radius:10px;color:var(--mut);
  text-decoration:none;font-size:13px;cursor:pointer}
.cm-side-foot a:hover{background:var(--panel2);color:var(--txt)}

/* main */
#cm-main{margin-left:232px;max-width:1180px;padding:26px 30px 70px}
.cm-top{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;margin-bottom:24px}
.cm-top h1{font-size:30px}
.cm-top .cm-sub{color:var(--mut);font-size:13px;margin-top:3px}
.cm-section{margin:30px 0;scroll-margin-top:18px}
.cm-h2{display:flex;align-items:baseline;gap:10px;font-weight:700;font-size:20px;margin-bottom:15px}
.cm-h2 small{font-weight:400;color:var(--mut);font-size:13px}
.cm-h2 a{color:var(--sky);font-size:12px;text-decoration:none;margin-left:auto}
.cm-h2 .dot{width:11px;height:11px;border-radius:50%;background:var(--navy);align-self:center}
.cm-h2 .dot.green{background:var(--green)} .cm-h2 .dot.sky{background:var(--sky)}

/* stat band */
.cm-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(168px,1fr));gap:14px}
.cm-stat{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:18px 20px;box-shadow:var(--shadow);position:relative;overflow:hidden}
.cm-stat::after{content:'';position:absolute;inset:0 0 auto 0;height:3px;background:linear-gradient(90deg,var(--green),var(--sky))}
.cm-num{font-weight:700;font-size:38px;color:var(--green);line-height:1}
.cm-stat-label{font-weight:700;margin-top:6px;font-size:14px}
.cm-stat-sub{color:var(--mut);font-size:12px;margin-top:2px}

/* two-column + panels */
.cm-two{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.cm-panel{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:18px 20px;box-shadow:var(--shadow)}
.cm-panel-h{font-weight:700;font-size:15px;margin-bottom:12px}
.cm-panel-h small{font-weight:400;color:var(--mut)}
.cm-mode{font-size:14px;background:color-mix(in srgb,var(--green) 12%,transparent);border-left:3px solid var(--green);border-radius:8px;padding:9px 12px;margin-bottom:12px}
.cm-focus{list-style:none;display:flex;flex-direction:column;gap:9px}
.cm-focus li{font-size:13px;padding-left:18px;position:relative}
.cm-focus li::before{content:'';position:absolute;left:0;top:6px;width:8px;height:8px;border-radius:2px;background:var(--sky)}
.cm-focus b{display:block} .cm-focus span{color:var(--mut);font-size:12px}
.cm-okrs{list-style:none;display:flex;flex-direction:column;gap:11px}
.cm-okrs .okr{display:flex;gap:11px;align-items:flex-start;font-size:13px}
.okr-dot{width:12px;height:12px;border-radius:50%;margin-top:3px;flex:none;background:currentColor;box-shadow:0 0 0 4px color-mix(in srgb,currentColor 18%,transparent)}
.okr-green{color:#20BF55} .okr-amber{color:#E8A317} .okr-red{color:#E2574C} .okr-gray{color:#8aa}
.cm-okrs .okr b{color:var(--txt)} .cm-okrs .okr span{display:block;color:var(--mut);font-size:12px}

/* intelligence */
.cm-intel{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px}
.cm-intel-row{display:flex;gap:12px;align-items:center;background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--sky);border-radius:12px;padding:12px 14px;text-decoration:none}
.cm-intel-row:hover{border-color:var(--sky)}
.cm-intel-icon{color:var(--sky);font-size:18px}
.cm-intel-body b{display:block;font-size:13px} .cm-intel-body span{font-size:11px;color:var(--mut)}

/* dept grid */
.cm-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}
.cm-card{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:18px;box-shadow:var(--shadow);position:relative;overflow:hidden;transition:transform .18s,border-color .18s}
.cm-card::before{content:'';position:absolute;inset:0 0 auto 0;height:4px;background:var(--accent)}
.cm-card:hover{transform:translateY(-4px);border-color:var(--accent)}
.cm-card-top{display:flex;gap:12px;align-items:center;margin-bottom:14px}
.cm-ico{width:42px;height:42px;border-radius:12px;display:grid;place-items:center;font-size:22px;background:color-mix(in srgb,var(--accent) 18%,transparent)}
.cm-card h3{font-size:18px} .cm-card-meta{color:var(--mut);font-size:11px}
.cm-card-nums{display:flex;gap:18px;margin-bottom:14px}
.cm-card-nums b{font-size:24px;color:var(--accent);display:block;line-height:1}
.cm-card-nums span{font-size:11px;color:var(--mut)}
.cm-card-skilllab{font-size:10px;letter-spacing:1.5px;color:var(--mut);text-transform:uppercase;margin-bottom:6px}
.cm-skills{list-style:none;font-size:13px}
.cm-skills li{display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px dashed var(--line)}
.cm-skills li:last-child{border-bottom:none} .cm-skills b{color:var(--accent)} .cm-skills .muted{color:var(--mut);font-style:italic}

/* feed */
.cm-feed{display:flex;flex-direction:column;gap:8px}
.cm-row{display:grid;grid-template-columns:84px 96px 1fr 22px;align-items:center;gap:12px;background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:12px;padding:11px 14px;font-size:14px;text-decoration:none;color:var(--txt)}
a.cm-row:hover{border-color:var(--accent);background:var(--panel2)}
.cm-row-date{color:var(--mut);font-size:12px;font-variant-numeric:tabular-nums}
.cm-chip{color:#fff;font-size:11px;font-weight:700;text-align:center;border-radius:999px;padding:3px 8px;white-space:nowrap}
.cm-row-link{color:var(--sky);text-align:center;font-weight:700;text-decoration:none}
.cm-row-ok{color:var(--green);text-align:center;font-weight:700}

/* second brain */
.cm-kcats{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
.cm-kcat{background:var(--panel2);border:1px solid var(--line);border-radius:12px;padding:12px;text-align:center}
.cm-kcat b{font-size:26px;color:var(--green);display:block;line-height:1}
.cm-kcat span{font-size:11px;color:var(--mut);text-transform:capitalize}
.cm-learned{list-style:none;display:flex;flex-direction:column;gap:8px;max-height:240px;overflow:auto}
.cm-learned li{display:flex;gap:10px;font-size:12px;align-items:baseline}
.cm-learned-t{color:var(--txt)}

/* outcomes */
.cm-out{display:flex;flex-direction:column;gap:6px}
.cm-out-row{display:grid;grid-template-columns:2fr 1.3fr 56px 64px 92px;align-items:center;gap:10px;background:var(--panel);border:1px solid var(--line);border-radius:11px;padding:10px 14px;font-size:13px}
.cm-out-head{background:transparent;border:none;color:var(--mut);font-size:11px;letter-spacing:1px;text-transform:uppercase;padding-bottom:2px}
.cm-out-row b{color:var(--txt)} .cm-mut{color:var(--mut)}
.cm-sig{font-size:11px;font-weight:700;text-align:center;border-radius:999px;padding:3px 8px}
.cm-sig-good{background:color-mix(in srgb,var(--green) 22%,transparent);color:var(--green)}
.cm-sig-bad{background:color-mix(in srgb,#E2574C 22%,transparent);color:#E2574C}
.cm-sig-mid{background:var(--panel2);color:var(--mut)}

/* bars */
.cm-bars{display:grid;gap:10px}
.cm-bar{display:grid;grid-template-columns:130px 1fr 44px;align-items:center;gap:12px}
.cm-bar-label{font-size:13px;color:var(--mut);text-decoration:none}
a.cm-bar-label{color:var(--sky);cursor:pointer}
a.cm-bar-label:hover{text-decoration:underline}
a.cm-row,a.cm-intel-row{cursor:pointer}
.cm-bar-track{height:12px;background:var(--panel2);border:1px solid var(--line);border-radius:999px;overflow:hidden}
.cm-bar-fill{height:100%;background:linear-gradient(90deg,var(--navy),var(--green));border-radius:999px;transition:width 1s cubic-bezier(.2,.8,.2,1)}
.cm-bar-num{font-weight:700;text-align:right;font-size:15px}

.cm-foot{margin-top:40px;padding-top:18px;border-top:1px solid var(--line);color:var(--mut);font-size:12px}
.cm-foot code{background:var(--panel2);border:1px solid var(--line);border-radius:6px;padding:2px 7px;color:var(--txt)}

/* operations */
.cm-week{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:16px 20px;box-shadow:var(--shadow);display:flex;justify-content:space-between;align-items:center;gap:18px;margin-bottom:16px;flex-wrap:wrap}
.cm-week-stats{display:flex;gap:28px}
.cm-week-stats b{font-size:24px;display:block;line-height:1;color:var(--green)} .cm-week-stats span{font-size:11px;color:var(--mut)}
.cm-spark{display:flex;align-items:flex-end;gap:5px;height:46px}
.cm-spark-bar{width:16px;height:100%;display:flex;align-items:flex-end}
.cm-spark-bar span{display:block;width:100%;background:linear-gradient(180deg,var(--sky),var(--navy));border-radius:3px;min-height:3px}
.cm-sched{list-style:none;display:flex;flex-direction:column;gap:7px;max-height:300px;overflow:auto}
.cm-sched li{display:grid;grid-template-columns:14px 1fr auto;gap:9px;align-items:center;font-size:12.5px}
.sch-name{color:var(--txt)} .sch-last{color:var(--mut);font-size:11px;font-variant-numeric:tabular-nums}
.sch-green{color:#20BF55} .sch-red{color:#E2574C} .sch-idle{color:#7d97a3}
.cm-placeholder{margin-top:14px;border:1px dashed var(--line);border-radius:14px;padding:16px;color:var(--mut);font-size:13px;text-align:center;background:color-mix(in srgb,var(--sky) 6%,transparent)}

@media(max-width:900px){
  #cm-side{position:static;width:auto;height:auto;flex-direction:column;border-right:none;border-bottom:1px solid var(--line)}
  #cm-main{margin-left:0;padding:22px 18px 60px}
  .cm-nav{flex-direction:row;flex-wrap:wrap} .cm-side-foot{margin-top:8px}
  .cm-grid{grid-template-columns:repeat(2,1fr)} .cm-two{grid-template-columns:1fr}
  .cm-row{grid-template-columns:70px 1fr 20px} .cm-row .cm-chip{display:none}
  .cm-out-row{grid-template-columns:1.6fr 56px 86px}
  .cm-out-row span:nth-child(2),.cm-out-row span:nth-child(4){display:none}
}
@media(max-width:480px){ .cm-grid{grid-template-columns:1fr} .cm-top h1{font-size:24px} }
`;

const CLIENT_JS = `
(function(){
  var D = DATA;
  var main = document.getElementById('cm-main');
  var side = document.getElementById('cm-side');
  var app = main;
  var NAV = [];
  function e(tag, cls, html){ var n=document.createElement(tag); if(cls)n.className=cls; if(html!=null)n.innerHTML=html; return n; }
  function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
  function linkAttrs(href, doc){ return 'href="'+esc(href)+'" target="_blank" rel="noopener" title="'+esc(href)+'"'+(doc?' data-doc="'+doc+'"':''); }
  function mkSection(id,icon,label,dotcls,small,headExtra){
    var s=e('section','cm-section'); s.id=id;
    s.innerHTML='<div class="cm-h2"><span class="dot'+(dotcls?' '+dotcls:'')+'"></span>'+label+(small?'<small>'+small+'</small>':'')+(headExtra||'')+'</div>';
    NAV.push({id:id,icon:icon,label:label});
    return s;
  }

  // top bar
  var gen = new Date(D.campus.generatedAt);
  var top = e('div','cm-top');
  top.innerHTML = '<div><h1>Campus Map</h1><div class="cm-sub">'+esc(D.campus.tagline)+'</div></div>'+
    '<div class="cm-sub">updated '+gen.toLocaleDateString()+' '+gen.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})+'</div>';
  main.appendChild(top);

  // overview / stat band
  var ov = e('section','cm-section'); ov.id='overview'; NAV.push({id:'overview',icon:'&#9678;',label:'Overview'});
  var band = e('div','cm-stats');
  [ {k:'runs',label:'Agent runs',sub:'work the team has done'},
    {k:'deliverables',label:'Deliverables produced',sub:'real files created'},
    {k:'hoursSaved',label:'Hours saved',sub:'est. @ '+D.totals.minPerRun+' min/run'},
    {k:'knowledgePages',label:'Knowledge pages',sub:D.totals.sharedFiles+' context files'},
    {k:'departments',label:'Departments live',sub:'working for you'} ].forEach(function(s){
    var c=e('div','cm-stat');
    c.innerHTML='<div class="cm-num" data-to="'+D.totals[s.k]+'">0</div><div class="cm-stat-label">'+s.label+'</div><div class="cm-stat-sub">'+s.sub+'</div>';
    band.appendChild(c);
  });
  ov.appendChild(band); main.appendChild(ov);

  // operating context
  if(D.context){
    var ctx=mkSection('context','&#9671;','Operating context',null,'what the campus is working toward');
    var two=e('div','cm-two'); var f=D.context.focus||{};
    var fitems=(f.items||[]).map(function(it){ return '<li><b>'+esc(it.title)+'</b>'+(it.desc?'<span>'+esc(it.desc)+'</span>':'')+'</li>'; }).join('');
    var fc=e('div','cm-panel');
    fc.innerHTML='<div class="cm-panel-h">This week'+(f.week?' &middot; <small>'+esc(f.week)+'</small>':'')+'</div>'+(f.mode?'<div class="cm-mode">'+esc(f.mode)+'</div>':'')+'<ul class="cm-focus">'+(fitems||'<li>&mdash;</li>')+'</ul>';
    two.appendChild(fc);
    var okrs=(D.context.okrs||[]).map(function(o){ return '<li class="okr okr-'+o.state+'"><span class="okr-dot"></span><div><b>'+esc(o.objective)+'</b>'+(o.text?'<span>'+esc(o.text)+'</span>':'')+'</div></li>'; }).join('');
    var oc=e('div','cm-panel'); oc.innerHTML='<div class="cm-panel-h">Objectives &amp; key results</div><ul class="cm-okrs">'+(okrs||'<li>&mdash;</li>')+'</ul>';
    two.appendChild(oc); ctx.appendChild(two); main.appendChild(ctx);
  }

  // intelligence
  if(D.intelligence && D.intelligence.length){
    var intel=mkSection('intelligence','&#10022;','Intelligence','sky','Atlas &middot; what to work on next');
    var il=e('div','cm-intel');
    il.innerHTML = D.intelligence.map(function(b){
      var inner='<span class="cm-intel-icon">&#10022;</span><div class="cm-intel-body"><b>'+esc(b.title)+'</b><span>'+esc(b.date)+(b.href?' &middot; open brief &#8599;':'')+'</span></div>';
      return b.href ? '<a class="cm-intel-row" '+linkAttrs(b.href,b.doc)+'>'+inner+'</a>'
                    : '<div class="cm-intel-row">'+inner+'</div>';
    }).join('');
    intel.appendChild(il); main.appendChild(intel);
  }

  // departments
  var orgSub = (D.staff && D.staff.line) ? esc(D.staff.line) + (D.staff.parts && D.staff.parts.length ? ' &middot; ' + esc(D.staff.parts.join(', ')) : '') : 'the team you are getting';
  var org=mkSection('departments','&#9636;','Your campus',null,orgSub);
  var grid=e('div','cm-grid');
  D.departments.forEach(function(d){
    var skills=d.skills.map(function(s){ return '<li><span>'+esc(s.name)+'</span><b>'+s.count+'</b></li>'; }).join('') || '<li class="muted">warming up...</li>';
    var card=e('article','cm-card'); card.style.setProperty('--accent',d.accent);
    card.innerHTML='<div class="cm-card-top"><span class="cm-ico">'+d.icon+'</span><div><h3>'+esc(d.short)+'</h3><div class="cm-card-meta">last active '+esc(d.lastActive)+'</div></div></div>'+
      '<div class="cm-card-nums"><div><b>'+d.runs+'</b><span>runs</span></div><div><b>'+d.deliverables+'</b><span>deliverables</span></div></div>'+
      '<div class="cm-card-skilllab">Agents at work</div><ul class="cm-skills">'+skills+'</ul>';
    grid.appendChild(card);
  });
  org.appendChild(grid); main.appendChild(org);

  // work done
  var wf=mkSection('work','&#10003;','Work done','green','proof &mdash; the latest the team shipped');
  var feed=e('div','cm-feed');
  feed.innerHTML = D.feed.map(function(x){
    var inner='<div class="cm-row-date">'+esc(x.date)+'</div><div class="cm-chip" style="background:'+x.accent+'">'+esc(x.deptName)+'</div>'+
      '<div class="cm-row-text">'+esc(x.text)+'</div>'+(x.href?'<div class="cm-row-link">&#8599;</div>':'<div class="cm-row-ok">'+(x.ok?'&#10003;':'&#8226;')+'</div>');
    var style='--accent:'+x.accent;
    return x.href ? '<a class="cm-row" style="'+style+'" '+linkAttrs(x.href,x.doc)+'>'+inner+'</a>'
                  : '<div class="cm-row" style="'+style+'">'+inner+'</div>';
  }).join('');
  wf.appendChild(feed); main.appendChild(wf);

  // operations: this week + skill health + scheduled tasks (was Mission Control)
  var ops=mkSection('ops','&#9881;','Operations',null,'health, cadence &amp; scheduled work &middot; no WordPress');
  var wk=D.week||{byDay:[]};
  var mx=Math.max.apply(null,(wk.byDay||[]).map(function(x){return x.count;}).concat([1]));
  var spark=(wk.byDay||[]).map(function(d){ var hh=Math.max(Math.round((d.count/mx)*100),4); return '<div class="cm-spark-bar" title="'+d.date+': '+d.count+'"><span style="height:'+hh+'%"></span></div>'; }).join('');
  var strip=e('div','cm-week');
  strip.innerHTML='<div class="cm-week-stats"><div><b>'+(wk.runs||0)+'</b><span>runs &middot; 7d</span></div><div><b>'+(wk.ok||0)+'</b><span>completed</span></div><div><b>'+(wk.issues||0)+'</b><span>issues</span></div><div><b>'+esc(wk.busiest||'—')+'</b><span>busiest</span></div></div><div class="cm-spark">'+spark+'</div>';
  ops.appendChild(strip);
  var two3=e('div','cm-two');
  var hl=(D.skillHealth||[]).map(function(s){ return '<li class="okr okr-'+s.state+'"><span class="okr-dot"></span><div><b>'+esc(s.name)+'</b><span>'+s.runs+' runs'+(s.issues?' &middot; '+s.issues+' issue'+(s.issues>1?'s':''):' &middot; clean')+'</span></div></li>'; }).join('');
  var hc=e('div','cm-panel'); hc.innerHTML='<div class="cm-panel-h">Skill health <small>top by volume</small></div><ul class="cm-okrs">'+(hl||'<li>&mdash;</li>')+'</ul>'; two3.appendChild(hc);
  var sc=(D.scheduled||[]).map(function(t){ return '<li class="sch-'+t.state+'"><span class="okr-dot"></span><span class="sch-name">'+esc(t.name)+'</span><span class="sch-last">'+esc(t.last||'idle')+'</span></li>'; }).join('');
  var stc=e('div','cm-panel'); stc.innerHTML='<div class="cm-panel-h">Scheduled tasks <small>'+(D.scheduled?D.scheduled.length:0)+' registered</small></div><ul class="cm-sched">'+(sc||'<li>&mdash;</li>')+'</ul>'; two3.appendChild(stc);
  ops.appendChild(two3);
  var kb=e('div','cm-placeholder'); kb.innerHTML='&#9636; Task pipeline &mdash; connect a task tool (FluentBoards, Notion, ClickUp) to light up your kanban &amp; &ldquo;done this week&rdquo; here.';
  ops.appendChild(kb);
  main.appendChild(ops);

  // team directory (v3.1) — who's on staff, from .campus-os/registry.json
  if(D.directory && D.directory.length){
    var teamCount = D.directory.filter(function(t){ return t.type!=='department' && t.type!=='systems'; }).length;
    var sub = teamCount + ' teams registered';
    if(D.setupProgress){ sub += ' &middot; setup ' + D.setupProgress.pct + '% complete (' + D.setupProgress.done + '/' + D.setupProgress.total + ')'; }
    var dir=mkSection('directory','&#9670;','Team directory','sky',sub);
    var dl=e('div','cm-feed');
    dl.innerHTML = D.directory.map(function(t){
      var st = t.status==='active' ? '&#10003; active' : esc(t.status);
      var trig = t.triggers.length ? ' &middot; ' + esc(t.triggers.join(', ')) : '';
      return '<div class="cm-row" style="--accent:var(--sky)"><div class="cm-row-date">'+esc(t.version||'&mdash;')+'</div>'+
        '<div class="cm-chip" style="background:var(--sky)">'+esc(t.type)+'</div>'+
        '<div class="cm-row-text"><b>'+esc(t.name)+'</b>'+(t.owns?' &mdash; '+esc(t.owns):'')+trig+'</div>'+
        '<div class="cm-row-ok">'+st+'</div></div>';
    }).join('');
    dir.appendChild(dl); main.appendChild(dir);
  }

  // second brain
  if(D.knowledge){
    var kn=mkSection('brain','&#9672;','Second brain','green',D.knowledge.total+' pages your campus has learned');
    var two2=e('div','cm-two');
    var cats=Object.keys(D.knowledge.byCat).map(function(c){ return '<div class="cm-kcat"><b>'+D.knowledge.byCat[c]+'</b><span>'+esc(c)+'</span></div>'; }).join('');
    var cc=e('div','cm-panel'); cc.innerHTML='<div class="cm-panel-h">Knowledge base</div><div class="cm-kcats">'+cats+'</div>'; two2.appendChild(cc);
    var learned=(D.knowledge.learned||[]).map(function(l){ return '<li><span class="cm-row-date">'+esc(l.date)+'</span><span class="cm-learned-t">'+esc(l.title)+'</span></li>'; }).join('');
    var lc=e('div','cm-panel'); lc.innerHTML='<div class="cm-panel-h">Recently learned</div><ul class="cm-learned">'+(learned||'<li>&mdash;</li>')+'</ul>'; two2.appendChild(lc);
    kn.appendChild(two2); main.appendChild(kn);
  }

  // outcomes
  if(D.outcomes && D.outcomes.rows && D.outcomes.rows.length){
    var extra=D.outcomes.href?'<a '+linkAttrs(D.outcomes.href,D.outcomes.doc)+'>view report &#8599;</a>':'';
    var oc2=mkSection('outcomes','&#9650;','Outcomes',null,'what each team shipped &middot; from results.json'+(D.outcomes.generated?' &middot; scored '+esc(D.outcomes.generated):''),extra);
    var tbl=e('div','cm-out');
    tbl.innerHTML='<div class="cm-out-row cm-out-head"><span>Initiative</span><span>Teams</span><span>Score</span><span>Assets</span><span>Signal</span></div>';
    D.outcomes.rows.forEach(function(r){
      var sig=(r.signal||'').toLowerCase();
      var cls=(sig.indexOf('more')>=0||sig.indexOf('ship')>=0||sig.indexOf('publish')>=0||sig.indexOf('live')>=0)?'good':((sig.indexOf('less')>=0||sig.indexOf('retire')>=0||sig.indexOf('drop')>=0)?'bad':'mid');
      var row=e('div','cm-out-row');
      row.innerHTML='<span><b>'+esc(r.label)+'</b></span><span class="cm-mut">'+esc(r.teams||'—')+'</span><span>'+esc(String(r.score))+'</span><span class="cm-mut">'+esc(r.assets)+'</span><span class="cm-sig cm-sig-'+cls+'">'+esc(r.signal)+'</span>';
      tbl.appendChild(row);
    });
    oc2.appendChild(tbl); main.appendChild(oc2);
  }

  // deliverables
  if(D.deliverables.length){
    var dl=mkSection('deliverables','&#9638;','What it makes',null,'deliverables by type &middot; click to open the folder');
    var max=D.deliverables[0].count||1; var bars=e('div','cm-bars');
    D.deliverables.forEach(function(d){
      var pct=Math.round((d.count/max)*100);
      var label=d.href?'<a class="cm-bar-label" '+linkAttrs(d.href,'')+'>'+esc(d.type)+' &#8599;</a>':'<div class="cm-bar-label">'+esc(d.type)+'</div>';
      var b=e('div','cm-bar');
      b.innerHTML=label+'<div class="cm-bar-track"><div class="cm-bar-fill" style="width:0%" data-w="'+pct+'"></div></div><div class="cm-bar-num">'+d.count+'</div>';
      bars.appendChild(b);
    });
    dl.appendChild(bars); main.appendChild(dl);
  }

  // footer
  var foot=e('footer','cm-foot');
  foot.innerHTML='The Campus Map &middot; orchestrated by '+esc(D.campus.orchestrator||'Dean')+' &middot; '+esc(D.totals.span)+' &nbsp;&middot;&nbsp; refresh: re-run <code>/campus-map</code>';
  main.appendChild(foot);

  // ---- sidebar ----
  var brandHtml='<div class="cm-side-brand"><div class="cm-logo">'+esc(D.campus.logo)+'</div><div><div class="cm-side-name">'+esc(D.campus.name)+'</div><div class="cm-side-kicker">AGENTIC OS</div></div></div>';
  var navHtml='<nav class="cm-nav">'+NAV.map(function(n){ return '<a data-target="'+n.id+'" role="link" tabindex="0"><span class="cm-nav-icon">'+n.icon+'</span>'+n.label+'</a>'; }).join('')+'</nav>';
  var footHtml='<div class="cm-side-foot"><a href="'+esc(D.outputsHref)+'" target="_blank" rel="noopener"><span class="cm-nav-icon">&#9635;</span>Vault overview</a><a id="cm-refresh"><span class="cm-nav-icon">&#8635;</span>Refresh</a><a id="cm-theme"><span class="cm-nav-icon">&#9680;</span>Theme</a></div>';
  side.innerHTML=brandHtml+navHtml+footHtml;

  document.getElementById('cm-theme').addEventListener('click',function(){
    var h=document.documentElement; h.setAttribute('data-theme', h.getAttribute('data-theme')==='dark'?'light':'dark');
  });
  document.getElementById('cm-refresh').addEventListener('click',function(){
    alert('Refresh your Campus Map:\\n\\n  Re-run the /campus-map skill\\n  (or from the campus folder: node campus-map/generate.mjs)');
  });

  // clean reading view for linked text/json files (opens a new tab)
  function openDoc(id){
    var d=DATA.docs&&DATA.docs[id]; if(!d) return false;
    var w=window.open('','_blank'); if(!w) return false;
    var css='body{font-family:Georgia,serif;max-width:768px;margin:0 auto;padding:38px 24px 80px;line-height:1.65;color:#1c2b33;background:#fbfcfd}'+
      'h1,h2,h3,h4{font-family:system-ui,sans-serif;line-height:1.25;color:#0B4F6C}h1{font-size:26px}h2{font-size:21px;margin-top:1.5em}h3{font-size:17px}'+
      'p{margin:.7em 0}ul{padding-left:22px}a{color:#0B4F6C}'+
      'code{background:#eef3f6;padding:2px 5px;border-radius:4px;font-size:.9em}'+
      'pre{background:#0b3142;color:#eaf4f8;padding:16px;border-radius:10px;overflow:auto;font-size:13px;line-height:1.5}pre code{background:none;color:inherit;padding:0}'+
      '.doc-bar{font-family:system-ui,sans-serif;font-size:12px;color:#5d7d8b;border-bottom:1px solid #e2ebf0;padding-bottom:10px;margin-bottom:24px;display:flex;justify-content:space-between;gap:12px}';
    w.document.write('<!doctype html><html><head><meta charset="utf-8"><title>'+esc(d.title)+'</title><style>'+css+'</style></head><body>'+
      '<div class="doc-bar"><span>'+esc(d.title)+'</span><a href="'+esc(d.href)+'" target="_blank" rel="noopener">open raw file &#8599;</a></div>'+d.html+'</body></html>');
    w.document.close(); return true;
  }
  document.addEventListener('click',function(ev){
    var a=ev.target.closest?ev.target.closest('[data-doc]'):null; if(!a) return;
    if(openDoc(a.getAttribute('data-doc'))) ev.preventDefault();
  });

  // in-page sidebar nav (no real href, so no browser/preview link interception)
  function gotoNav(id){ var el=document.getElementById(id); if(el) el.scrollIntoView({behavior:'smooth',block:'start'}); }
  document.addEventListener('click',function(ev){
    var a=ev.target.closest?ev.target.closest('.cm-nav a[data-target]'):null; if(!a) return;
    gotoNav(a.getAttribute('data-target'));
  });
  document.addEventListener('keydown',function(ev){
    if(ev.key!=='Enter'&&ev.key!==' ') return;
    var a=ev.target.closest?ev.target.closest('.cm-nav a[data-target]'):null; if(!a) return;
    ev.preventDefault(); gotoNav(a.getAttribute('data-target'));
  });

  // scroll-spy
  var links={}; document.querySelectorAll('.cm-nav a').forEach(function(a){ links[a.getAttribute('data-target')]=a; });
  if('IntersectionObserver' in window){
    var io=new IntersectionObserver(function(ents){
      ents.forEach(function(en){ if(en.isIntersecting){ for(var k in links) links[k].classList.remove('active'); var l=links[en.target.id]; if(l)l.classList.add('active'); } });
    },{rootMargin:'-20% 0px -70% 0px'});
    NAV.forEach(function(n){ var el=document.getElementById(n.id); if(el)io.observe(el); });
  }

  // animations
  document.querySelectorAll('.cm-num').forEach(function(n){
    var to=+n.getAttribute('data-to')||0,t0=null,dur=900;
    function step(ts){ if(!t0)t0=ts; var p=Math.min((ts-t0)/dur,1); n.textContent=Math.round(p*to).toLocaleString(); if(p<1)requestAnimationFrame(step); }
    requestAnimationFrame(step);
  });
  setTimeout(function(){ document.querySelectorAll('.cm-bar-fill').forEach(function(f){ f.style.width=f.getAttribute('data-w')+'%'; }); },200);
})();
`;

// ---- write ---------------------------------------------------------------
const html = renderHTML(JSON.stringify(data), brand);
fs.mkdirSync(OUT_DIR, { recursive: true });
const OUT_FILE = path.join(OUT_DIR, 'campus-map.html');
fs.writeFileSync(OUT_FILE, html, 'utf8');
console.log('Campus Map written: (private)', '→', OUT_FILE);
console.log('  orchestrator:', orchestrator, '| brand:', brand.name, '| heading:', brand.headingFont, '| navy', brand.colors.navy);
console.log('  ' + data.totals.runs + ' runs · ' + data.totals.deliverables + ' deliverables · ~' +
  data.totals.hoursSaved + 'h · ' + data.totals.knowledgePages + ' wiki pages');
