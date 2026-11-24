#!/usr/bin/env python3
"""Work Order tool (Campus AI OS 5.3.0): create, check, record events, and show computed status.

Run from the campus root, from the kernel kit:
  python3 -I -B .campus-os/kernel/tools/wo.py new quick|full|standing "Title" --dept "<label>" [--parent-prd PATH] [--dir active-work/x] [--client C]
  python3 -I -B .campus-os/kernel/tools/wo.py check PATH|WO-ID [...]   # validate required fields (exit 1 on errors)
  python3 -I -B .campus-os/kernel/tools/wo.py event WO-ID TYPE --client claude-code|claude-cowork|codex [--note ...] [--field k=v ...]
  python3 -I -B .campus-os/kernel/tools/wo.py status [WO-ID]          # status computed from events (all seats' logs)
  python3 -I -B .campus-os/kernel/tools/wo.py status --by-project     # grouped under their parent PRD, one sentence each
  python3 -I -B .campus-os/kernel/tools/wo.py find <words...>         # search Work Orders + PRDs by id, title, PRD, state
  python3 -I -B .campus-os/kernel/tools/wo.py list                    # every Work Order found (by wo_id frontmatter)

Plain stdlib; works from any app. Departments come from the campus's own `.campus-os/registry.json`.
Events go to the ledger the seat resolver returns (`.campus-os/resolve-seat.py`); this tool never
writes `.campus-os/`. Rules: `templates/work-orders/events.md`. Env WO_LEDGER_DIR overrides where
event lines are appended (tests).
"""
import argparse, datetime as dt, glob, json, os, pathlib, re, subprocess, sys

KERNEL = pathlib.Path(__file__).resolve().parent.parent
TEMPLATES = KERNEL / "templates" / "work-orders"
CAMPUS = pathlib.Path(os.environ.get("CAMPUS_ROOT") or os.getcwd()).resolve()
SEARCH = ["active-work", "outputs"]


def departments():
    """Department labels (and ids) from the campus registry; empty when it cannot be read."""
    try:
        reg = json.loads((CAMPUS / ".campus-os" / "registry.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    teams = reg.get("teams") if isinstance(reg, dict) else None
    out = []
    for e in teams if isinstance(teams, list) else []:
        if isinstance(e, dict) and e.get("type") == "department":
            out += [v for v in (e.get("label"), e.get("id")) if isinstance(v, str) and v]
    return out
SCOPES = ["draft-only", "create-drafts", "publish-in-approved-workflow", "autonomous-recurring"]
EVENTS = ["drafted", "signed", "claimed", "started", "decision-needed", "decided", "blocked", "change-order", "done", "verified", "closed", "run", "stopped"]
PRD_RE = re.compile(r"-PRD\.md$")
REQUIRED = {
    "quick": ["wo_id", "title", "size", "owner", "dept", "goal", "approval_scope", "budget", "stop_rules", "state"],
    "full": ["wo_id", "title", "size", "owner", "dept", "goal", "approval_scope", "verifier", "budget", "stop_rules", "state"],
    "standing": ["wo_id", "title", "size", "owner", "method", "dept", "approval_scope", "runs_on", "cadence", "budget", "stop_rules", "state"],
}
WO_RE = re.compile(r"^WO-\d{4}-\d{2}-\d{2}-\d{2,3}$")
# Events that change who may act or whether the job is done. They count only from a primary seat's own
# log (review of 5.3.0): a satellite reports progress (done, blocked, decision-needed, run) and proposes;
# it never signs, starts, verifies, stops or closes a job.
PRIVILEGED = {"signed", "claimed", "started", "decided", "change-order", "verified", "stopped", "closed"}
BASE_KEYS = {"ts", "seat", "platform", "session", "session_id", "skill", "trigger", "dept", "logged_for",
             "outcome", "files_touched", "wo_id", "event", "via", "client", "role"}
OUTSIDE = "refused: that path leaves the campus or goes through a link"


def safe_path(rel):
    """Campus-relative path -> absolute path inside CAMPUS, refusing absolute paths, '..', and any link
    on the way (5.2.18 rule: writers never follow a link out of the campus)."""
    rel = str(rel).replace("\\", "/")
    parts = [x for x in rel.split("/") if x not in ("", ".")]
    if os.path.isabs(rel) or re.match(r"^[A-Za-z]:", rel) or ".." in parts or not parts:
        sys.exit(OUTSIDE)
    p = CAMPUS
    for part in parts:
        p = p / part
        if p.is_symlink():
            sys.exit(OUTSIDE)
    return p


def make_dirs(path):
    """Create each missing folder from the campus down, refusing a link at any level."""
    rel = path.relative_to(CAMPUS)
    p = CAMPUS
    for part in rel.parts:
        p = p / part
        if p.is_symlink():
            sys.exit(OUTSIDE)
        if not p.exists():
            p.mkdir()


NOFOLLOW = getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)


def create_file(path, text):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | NOFOLLOW, 0o644)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def append_line(path, line):
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | NOFOLLOW, 0o644)
    with os.fdopen(fd, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(line + "\n")


def one_line(name, value):
    if value is not None and ("\n" in value or "\r" in value):
        sys.exit(f"{name} must be one line")
    return value


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    out = {}
    if not m:
        return out
    last = None
    for line in m.group(1).splitlines():
        kv = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if kv:
            last = kv.group(1)
            out[last] = re.sub(r"\s+#.*$", "", kv.group(2)).strip().strip('"').strip("'")
        elif last and re.match(r"^\s+(-|\w)", line):   # indented continuation (YAML list / map)
            out[last] = (out[last] + " " + line.strip()).strip()
    return out


def all_work_orders():
    found = {}
    for base in SEARCH:
        for f in glob.glob(str(CAMPUS / base / "**" / "*.md"), recursive=True):
            if "archive" in pathlib.Path(f).parts:
                continue
            try:
                head = open(f, encoding="utf-8", errors="replace").read(4000)
            except OSError:
                continue
            fm = frontmatter(head)
            if WO_RE.match(fm.get("wo_id", "")):
                found.setdefault(fm["wo_id"], []).append(pathlib.Path(f))
    return found


def next_id():
    today = dt.date.today().isoformat()
    used = [int(k.rsplit("-", 1)[1]) for k in all_work_orders() if k.startswith(f"WO-{today}-")]
    return f"WO-{today}-{(max(used) + 1 if used else 1):02d}"


def seat(client):
    try:
        out = subprocess.run([sys.executable, "-I", "-B", str(CAMPUS / ".campus-os" / "resolve-seat.py"), "--client", client], capture_output=True, text=True, timeout=10).stdout
        return json.loads(out)
    except Exception as e:
        sys.exit(f"could not resolve seat for {client}: {e}")


def resolve_path(ref):
    if WO_RE.match(ref):
        paths = all_work_orders().get(ref)
        if not paths:
            sys.exit(f"{ref}: no Work Order file found")
        if len(paths) > 1:
            print(f"warning: {ref} appears in {len(paths)} files: {[str(p) for p in paths]}")
        return paths[0]
    return pathlib.Path(ref)


def cmd_new(a):
    if not (CAMPUS / "workspace.json").is_file():
        sys.exit("run this from the campus root (the folder with workspace.json)")
    title, dept, prd = one_line("title", a.title), one_line("--dept", a.dept), one_line("--parent-prd", a.parent_prd)
    depts = departments()
    if depts and dept not in depts:
        sys.exit(f"--dept must be a department in .campus-os/registry.json: {sorted(set(depts))}")
    s = seat(a.client)
    dept_slug = re.sub(r"[^a-z0-9]+", "-", dept.lower()).strip("-")[:40] or "general"
    if s.get("role") != "primary" or s.get("warning"):
        # a satellite (or an unresolved app) only writes its own lane: the Work Order is a proposal there
        lane = (s.get("lane") or "").rstrip("/")
        if not lane or (a.dir and not a.dir.replace("\\", "/").strip("/").startswith(lane)):
            sys.exit("refused: this app is a satellite here; it may only propose in its own lane")
        folder = safe_path(a.dir or f"{lane}/proposals/work-orders")
        print(f"note: this app is a satellite, so the Work Order is a proposal in {lane}/ for a primary app to adopt")
    else:
        folder = safe_path(a.dir or f"active-work/{dept_slug}")
    tpl = TEMPLATES / f"{a.size}.md"
    wid = next_id()
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60] or "work-order"
    make_dirs(folder)
    path = folder / f"{wid}-{slug}.md"
    text = tpl.read_text(encoding="utf-8").replace("WO-YYYY-MM-DD-NN", wid).replace("YYYY-MM-DD", dt.date.today().isoformat())
    text = re.sub(r'^title: .*$', lambda m: f'title: {json.dumps(title, ensure_ascii=False)}', text, count=1, flags=re.M)
    text = re.sub(r'^dept: .*$', lambda m: f'dept: {json.dumps(dept, ensure_ascii=False)}', text, count=1, flags=re.M)
    if prd:
        text = re.sub(r'^parent_prd: .*$', lambda m: f'parent_prd: {json.dumps(prd, ensure_ascii=False)}', text, count=1, flags=re.M)
    text = text.replace("{title}", title)
    try:
        create_file(path, text)
    except FileExistsError:
        sys.exit(f"refused: {path.name} already exists")
    except OSError as exc:
        sys.exit(f"refused: could not write {path.name}: {exc}")
    print(f"created {path.relative_to(CAMPUS).as_posix()} ({wid})")
    write_event(wid, "drafted", a.client, "created from template", {"path": path.relative_to(CAMPUS).as_posix()}, s)


def check_file(path):
    errs, warns = [], []
    text = path.read_text(encoding="utf-8", errors="replace")
    head = re.match(r"^---\n(.*?)\n---", text, re.S)
    fm = frontmatter(text)
    size = fm.get("size", "")
    if size not in REQUIRED:
        return [f"size must be quick|full|standing (got {size!r})"], warns
    for k in REQUIRED[size]:
        if not fm.get(k):
            errs.append(f"missing {k}")
    if fm.get("wo_id") and not WO_RE.match(fm["wo_id"]):
        errs.append(f"wo_id {fm['wo_id']!r} is not WO-YYYY-MM-DD-NN")
    depts = departments()
    if fm.get("dept") and depts and fm["dept"] not in depts:
        warns.append(f"dept {fm['dept']!r} is not a department in .campus-os/registry.json")
    if fm.get("approval_scope") and fm["approval_scope"] not in SCOPES:
        errs.append(f"approval_scope must be one of {SCOPES}")
    if re.search(r"\b(claude|gpt|gemini|haiku|opus|sonnet|qwen)[-\w.]*\b", fm.get("tiers", ""), re.I):
        errs.append("tiers must name tiers (full/light/tool), not models")
    head = re.match(r"^---\n(.*?)\n---", text, re.S)
    if "{title}" in text.split("\n## ")[0] or (head and ("WO-YYYY-MM-DD-NN" in head.group(1) or "{job" in head.group(1))):
        errs.append("template placeholders left in")
    fmtext = head.group(1) if head else ""
    if size != "standing" and re.search(r"^decision:", fmtext, re.M) and "deadline" not in fmtext:
        warns.append("decision card without a deadline")
    return errs, warns


def shown(p):
    try:
        return p.resolve().relative_to(CAMPUS).as_posix()
    except ValueError:
        return str(p)


def cmd_check(a):
    bad = 0
    for ref in a.refs:
        p = resolve_path(ref)
        errs, warns = check_file(p)
        tag = "FAIL" if errs else "ok"
        print(f"{tag:4} {shown(p)}")
        for e in errs:
            print(f"     x {e}")
        for w in warns:
            print(f"     ! {w}")
        bad += bool(errs)
    sys.exit(1 if bad else 0)


def write_event(wid, etype, client, note, extra, s=None):
    s = s or seat(client)
    ledger_dir = pathlib.Path(os.environ.get("WO_LEDGER_DIR") or CAMPUS)
    if ledger_dir == CAMPUS:
        ledger = safe_path(s["ledger"])
        make_dirs(ledger.parent)
    else:                                   # tests only
        ledger = ledger_dir / s["ledger"]
        ledger.parent.mkdir(parents=True, exist_ok=True)
    one_line("--note", note)
    line = {"ts": now(), "seat": s["seat"], "platform": client, "session": os.environ.get("CAMPUS_SESSION_LABEL", "work-order"),
            "skill": "work-order", "trigger": note or etype, "dept": "", "logged_for": "write",
            "outcome": etype, "files_touched": 0, "wo_id": wid, "event": etype}
    if os.environ.get("CAMPUS_SESSION_ID"):
        line["session_id"] = os.environ["CAMPUS_SESSION_ID"]
    if s.get("via") in ("host-binding", "unresolved"):
        line["via"] = s["via"]
    clash = sorted(set(extra) & (BASE_KEYS | set(line)))
    if clash:
        sys.exit(f"--field cannot set {', '.join(clash)}: the tool writes those itself")
    line.update(extra)
    try:
        append_line(ledger, json.dumps(line, separators=(",", ":"), ensure_ascii=False))
    except OSError as exc:
        sys.exit(f"refused: could not append to {s['ledger']}: {exc}")
    print(f"{etype} -> {ledger.relative_to(ledger_dir).as_posix()} ({s['seat']})")


def cmd_event(a):
    if not WO_RE.match(a.wo_id):
        sys.exit("wo_id must look like WO-YYYY-MM-DD-NN")
    if a.type not in EVENTS:
        sys.exit(f"event must be one of {EVENTS}")
    extra = {}
    for kv in a.field or []:
        k, _, v = kv.partition("=")
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,40}", k):
            sys.exit(f"--field key {k!r} must be lowercase letters, digits or _")
        extra[k] = {"true": True, "false": False}.get(v, one_line("--field", v))
    write_event(a.wo_id, a.type, a.client, a.note, extra)


def authority():
    """(primary seats, clock-owner seat) from .campus-os/seat.json, or None when the campus has no seat
    file yet (single-app campus before 5.3.0: every log counts, as before)."""
    try:
        cfg = json.loads((CAMPUS / ".campus-os" / "seat.json").read_text(encoding="utf-8"))
        clients = cfg["clients"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    primaries = {v.get("seat") for v in clients.values() if isinstance(v, dict) and v.get("role") == "primary"}
    owner = cfg.get("clock_owner")
    clock = clients.get(owner, {}).get("seat") if isinstance(clients.get(owner), dict) and clients[owner].get("role") == "primary" \
        else (next(iter(primaries)) if len(primaries) == 1 else None)
    return primaries, clock


IGNORED = []


def counts(e, fname, auth):
    """An event counts only from the log of the seat it names; a privileged event only from a primary."""
    if auth is None:
        return True
    primaries, clock = auth
    seat_ = e.get("seat")
    if fname == ".activity.jsonl":
        own = seat_ == clock
    else:
        own = fname == f".activity.{seat_}.jsonl"
    if not own:
        return False
    return e["event"] not in PRIVILEGED or seat_ in primaries


def events():
    base = pathlib.Path(os.environ.get("WO_LEDGER_DIR") or CAMPUS) / "dean"
    auth = authority()
    out = []
    IGNORED.clear()
    for f in base.glob(".activity*.jsonl"):
        for line in f.open(encoding="utf-8", errors="replace"):
            if '"wo_id"' not in line or '"event"' not in line:
                continue
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if not (isinstance(e, dict) and e.get("skill") == "work-order" and e.get("event") in EVENTS and isinstance(e.get("wo_id"), str)):
                continue
            if counts(e, f.name, auth):
                out.append(e)
            else:
                IGNORED.append(e)
    return sorted(out, key=lambda e: e.get("ts", ""))


def compute(evs):
    """Status from events — the rules in work-order-events.md."""
    if not evs:
        return "no events (file status only)", None
    st, holder, empties = None, None, 0
    open_decision = False
    for e in evs:
        t = e["event"]
        if t == "run":
            empties = empties + 1 if e.get("result") == "empty" else 0
            continue
        if t == "decision-needed":
            open_decision = True
        if t == "decided":
            open_decision = False
        if t in ("claimed", "started"):
            holder = e.get("seat")
        st = e
    t = st["event"] if st else "run"
    if open_decision:
        label = "needs you"
    elif t == "signed":
        label = "ready to start"
    elif t in ("claimed", "started", "decided", "change-order"):
        until = st.get("until")
        lapsed = until and until < now()
        label = (f"working ({holder})" if holder else "in progress") + (" - claim lapsed" if lapsed else "")
    elif t == "blocked":
        label = f"blocked: {st.get('reason', st.get('trigger', ''))}"
    elif t == "stopped":
        label = f"stopped by {st.get('by', 'the owner')}"   # `started` after it resumes the job
    elif t == "done":
        label = "awaiting verification"
    elif t == "verified":
        label = "finished" if st.get("passed") in (True, "true") else "verification failed - back to work"
    elif t == "closed":
        label = "closed"
    else:
        label = t
    if empties:
        label += f" | {empties} empty run(s) in a row"
    return label, st.get("ts") if st else None


def cmd_status(a):
    if a.by_project:
        return cmd_by_project(a)
    evs = events()
    wos = all_work_orders()
    ids = [a.wo_id] if a.wo_id else sorted(set(wos) | {e["wo_id"] for e in evs})
    for wid in ids:
        label, ts = compute([e for e in evs if e["wo_id"] == wid])
        title = frontmatter(wos[wid][0].read_text(encoding="utf-8", errors="replace")).get("title", "") if wid in wos else "(no file)"
        print(f"{wid}  {label:32}  {title[:60]}")
    if IGNORED:
        print(f"({len(IGNORED)} event line(s) not counted: written by a satellite, an unassigned app, or into another seat's log)")


# ---- job-level views: find + status --by-project ---------------------------------------------

def doc_title(path):
    """Title of a PRD or any markdown doc: frontmatter title, else first H1, else the file name."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")[:4000]
    except OSError:
        return path.stem
    fm = frontmatter(text)
    if fm.get("title"):
        return fm["title"]
    m = re.search(r"^#\s+(.+)$", text, re.M)
    return re.sub(r"^PRD\s*[—–-]\s*", "", m.group(1)).strip() if m else path.stem


def doc_status_line(path):
    """First status line of a PRD: frontmatter status, else a `Status:` / `**Status:**` line."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")[:6000]
    except OSError:
        return ""
    fm = frontmatter(text)
    if fm.get("status"):
        return fm["status"]
    m = re.search(r"^\**Status:?\**:?\s*(.+)$", text, re.M | re.I)
    return m.group(1).strip() if m else ""


def all_prds():
    out = []
    for base in SEARCH:
        for f in glob.glob(str(CAMPUS / base / "**" / "*-PRD.md"), recursive=True):
            if "/archive/" not in f:
                out.append(pathlib.Path(f))
    return sorted(set(out))


def parent_prd_of(fm):
    """Resolved parent PRD path for a Work Order, or None."""
    ref = (fm.get("parent_prd") or "").strip().strip('"').strip("'")
    if not ref:
        return None
    p = (CAMPUS / ref).resolve()
    return p if p.exists() else None


def work_order_rows():
    """One row per Work Order: id, path, frontmatter, computed label, last event time, parent PRD path."""
    evs = events()
    rows = []
    for wid, paths in sorted(all_work_orders().items()):
        fm = frontmatter(paths[0].read_text(encoding="utf-8", errors="replace"))
        label, ts = compute([e for e in evs if e["wo_id"] == wid])
        rows.append({"id": wid, "path": paths[0], "fm": fm, "label": label, "ts": ts or fm.get("created", ""), "prd": parent_prd_of(fm),
                     "events": [e for e in evs if e["wo_id"] == wid]})
    return rows


def label_class(label):
    """Bucket a computed label for counting."""
    if label.startswith("working") or label.startswith("in progress"):
        return "working"
    if label.startswith("needs you"):
        return "needs_owner"
    if label.startswith("ready to start"):
        return "ready"
    if label.startswith("blocked"):
        return "blocked"
    if label.startswith("stopped"):
        return "stopped"
    if label.startswith("awaiting verification") or label.startswith("verification failed"):
        return "verifying"
    if label.startswith("finished") or label.startswith("closed"):
        return "closed"
    return "backlog"   # drafted / no events


def estimate_hours(row):
    """Estimate: est_agent_hours on the signed event, else budget.agent_hours in the file; None when neither."""
    for e in reversed(row["events"]):
        if e["event"] == "signed" and e.get("est_agent_hours") not in (None, "", "0", 0):
            try:
                return float(e["est_agent_hours"])
            except ValueError:
                pass
    m = re.search(r"agent_hours:\s*([\d.]+)", row["fm"].get("budget", ""))
    if m and float(m.group(1)) > 0:
        return float(m.group(1))
    return None


def project_sentence(rows):
    counts = {}
    seats = set()
    for r in rows:
        c = label_class(r["label"])
        counts[c] = counts.get(c, 0) + 1
        if c == "working":
            m = re.search(r"working \((.+?)\)", r["label"])
            if m:
                seats.add(m.group(1))
    parts = []
    if counts.get("working"):
        parts.append(f"{counts['working']} working" + (f" ({', '.join(sorted(seats))})" if seats else ""))
    for key, word in (("needs_owner", "waiting on you"), ("ready", "ready to start"), ("blocked", "blocked"),
                      ("stopped", "stopped"), ("verifying", "awaiting verification"), ("backlog", "in backlog"), ("closed", "closed")):
        if counts.get(key):
            parts.append(f"{counts[key]} {word}")
    last = max((r["ts"] or "" for r in rows), default="")
    sentence = ", ".join(parts) if parts else "nothing recorded"
    if last:
        sentence += f"; last movement {last[:10]}"
    est = sum(e for e in (estimate_hours(r) for r in rows if label_class(r["label"]) != "closed") if e) or None
    sentence += f"; ~{est:g} agent hours estimated" if est else "; no estimate"
    return sentence + "."


def cmd_by_project(a):
    rows = work_order_rows()
    groups = {}
    for r in rows:
        groups.setdefault(r["prd"], []).append(r)
    ordered = sorted((k for k in groups if k is not None), key=lambda p: doc_title(p).lower())
    if None in groups:
        ordered.append(None)
    for prd in ordered:
        members = groups[prd]
        heading = f"{doc_title(prd)}  ({prd.relative_to(CAMPUS)})" if prd else "Loose jobs (no parent PRD)"
        print(f"\n## {heading}")
        print(f"   {project_sentence(members)}")
        for r in sorted(members, key=lambda r: (label_class(r['label']) == 'closed', r['id'])):
            if label_class(r["label"]) == "closed" and not a.all:
                continue
            print(f"   {r['id']}  {r['label'][:40]:40}  {r['fm'].get('title', '')[:70]}")
    print(f"\n{len(rows)} Work Orders in {len(ordered)} groups.")


def cmd_find(a):
    words = [w.lower() for w in a.words]
    hit = lambda hay: all(w in hay for w in words)
    rows = work_order_rows()
    found = []
    for r in rows:
        prd_title = doc_title(r["prd"]) if r["prd"] else ""
        hay = " ".join([r["id"], r["fm"].get("title", ""), r["fm"].get("state", ""), prd_title, r["path"].stem]).lower()
        if hit(hay):
            found.append((r, prd_title))
    if found:
        print("Work Orders")
        for r, prd_title in found:
            print(f"  {r['id']}  {r['label'][:40]:40}  {r['fm'].get('title', '')[:70]}" + (f"  [PRD: {prd_title[:40]}]" if prd_title else ""))
    prds = [p for p in all_prds() if hit(f"{doc_title(p)} {p.stem} {doc_status_line(p)}".lower())]
    if prds:
        print("PRDs")
        for p in prds:
            n = sum(1 for r in rows if r["prd"] == p)
            print(f"  {doc_title(p)[:60]:60}  {doc_status_line(p)[:50]:50}  {n} WO  {p.relative_to(CAMPUS)}")
    if not found and not prds:
        # Nothing in titles or state lines: fall back to the body text, so the owner's own words for a project still find it.
        def body_hit(path):
            try:
                return hit(path.read_text(encoding="utf-8", errors="replace").lower())
            except OSError:
                return False
        b_wos = [r for r in rows if body_hit(r["path"])]
        b_prds = [p for p in all_prds() if body_hit(p)]
        if b_wos or b_prds:
            print(f"No title matches {' '.join(a.words)!r}. Mentioned inside:")
            for r in b_wos:
                print(f"  {r['id']}  {r['label'][:40]:40}  {r['fm'].get('title', '')[:70]}")
            for p in b_prds:
                n = sum(1 for r in rows if r["prd"] == p)
                print(f"  PRD  {doc_title(p)[:60]:60}  {n} WO  {p.relative_to(CAMPUS)}")
        else:
            print(f"nothing matches {' '.join(a.words)!r}")


def cmd_list(a):
    for wid, paths in sorted(all_work_orders().items()):
        fm = frontmatter(paths[0].read_text(encoding="utf-8", errors="replace"))
        print(f"{wid}  {fm.get('size', '?'):8} {fm.get('status', '')[:28]:28}  {paths[0].relative_to(CAMPUS)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new"); n.add_argument("size", choices=["quick", "full", "standing"]); n.add_argument("title")
    n.add_argument("--dept", required=True, help="a department label from .campus-os/registry.json"); n.add_argument("--parent-prd"); n.add_argument("--dir"); n.add_argument("--client", required=True, help="this app: claude-code, claude-cowork or codex")
    c = sub.add_parser("check"); c.add_argument("refs", nargs="+")
    e = sub.add_parser("event"); e.add_argument("wo_id"); e.add_argument("type"); e.add_argument("--client", required=True)
    e.add_argument("--note"); e.add_argument("--field", action="append")
    s = sub.add_parser("status"); s.add_argument("wo_id", nargs="?")
    s.add_argument("--by-project", action="store_true", help="group under parent PRD, one sentence per project")
    s.add_argument("--all", action="store_true", help="with --by-project: also list closed Work Orders")
    f = sub.add_parser("find"); f.add_argument("words", nargs="+")
    sub.add_parser("list")
    a = ap.parse_args()
    {"new": cmd_new, "check": cmd_check, "event": cmd_event, "status": cmd_status, "list": cmd_list, "find": cmd_find}[a.cmd](a)


if __name__ == "__main__":
    main()
