#!/usr/bin/env python3
"""Seat resolver (Seat Contract). Client comes from host identity, never folder names.

platform: claude-code; seat: m4-claude-code (5.2.4, host binding). Origin: Codex seat-identity-fix, 2026-09-04.

Three modes:
  resolve   python3 -I -B resolve-seat.py --client <claude-cowork|claude-code|codex>
            Observes the host fingerprint (sha256 of the machine's own id: macOS IOPlatformUUID,
            Windows MachineGuid, Linux /etc/machine-id) and matches it against
            .campus-os/seat.json. Exit 0 = resolved; exit 2 = unresolved, caller is a satellite.
  init      python3 -I -B resolve-seat.py --init-seat --primary <client> [--primary <client> ...]
                [--satellite <client> ...] [--clock-owner <client>] [--machine <name>]
            The OWNER declares which apps on this machine are primary (5.3.0). Writes seat.json
            once, from the host (refuses where the fingerprint is not observed, and never
            overwrites an existing seat.json). Founding runs it with the owner's answer.
  issue     python3 -I -B resolve-seat.py --issue-binding --client <clock-owner-client> [--ttl-hours 12]
            Runs ONLY where the fingerprint is observed (Terminal, launchd, Claude Code on the host).
            Writes .campus-os/host-binding.json so a sandboxed session of the clock-owner
            client (a Cowork container cannot read ioreg) can resolve primary lawfully.

Co-primary (Phase 0, 2026-09-11, owner-authorized): every client assigned on THIS installation may
hold role `primary` and write shared state. An unknown fingerprint, an unassigned client, or a
sandbox with no valid binding still resolves satellite. Exactly one client is `clock_owner`: it alone
runs schedules and writes the shared ledger; every other primary keeps its own ledger shard.

Host binding rules (all must hold, checked in resolve()):
  - consulted ONLY when the fingerprint is unavailable; it never overrides a mismatch
  - binding.client == --client, and that client is the clock owner
  - binding.machine_id == seat.json.machine_id
  - issued_at <= now (+ small clock skew), expires_at > now, expires_at - issued_at <= TTL_MAX_HOURS
Result carries "via": "observed" | "host-binding" and "binding_expires" so ledgers can audit it.
Residual risk (recorded, not hidden): a file-only scheme cannot stop a hostile client that can read
seat.json from forging the file. It defends the actual failure class - an honest client that cannot
observe its host - with a short TTL, an explicit issuer line, and an audit trail. Not a security boundary.
"""
import argparse, datetime as dt, hashlib, json, os, re, socket, subprocess, sys
from pathlib import Path

BINDING_FILE = 'host-binding.json'
BINDING_SCHEMA = 1
TTL_DEFAULT_HOURS = 12
TTL_MIN_HOURS = 1
TTL_MAX_HOURS = 24          # a binding longer than this is rejected on read as well as clamped on issue
CLOCK_SKEW = dt.timedelta(minutes=5)
CLIENT_RE = re.compile(r'[a-z0-9-]{1,40}')


def _macos_id():
    try:
        p = subprocess.run(['/usr/sbin/ioreg', '-rd1', '-c', 'IOPlatformExpertDevice'], capture_output=True, text=True, timeout=5, check=True)
        m = re.search(r'"IOPlatformUUID"\s*=\s*"([^"]+)"', p.stdout)
        return m[1] if m else None
    except (OSError, subprocess.SubprocessError):
        return None


def _windows_id():
    try:
        import winreg  # stdlib on Windows only
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Cryptography', 0,
                            winreg.KEY_READ | getattr(winreg, 'KEY_WOW64_64KEY', 0)) as k:
            value, _ = winreg.QueryValueEx(k, 'MachineGuid')
        return value if isinstance(value, str) else None
    except (ImportError, OSError):
        return None


CONTAINER_MARKERS = ('/.dockerenv', '/run/.containerenv')
CONTAINER_CGROUP = re.compile(r'docker|kubepods|containerd|lxc|libpod|podman|garden|buildkit')


def in_container(markers=CONTAINER_MARKERS, cgroup='/proc/1/cgroup', environ=None):
    """True inside a container or sandbox. Cloud and sandboxed AI sessions run Linux containers
    whose own machine id is NOT the owner's computer: observing it would deny them the host
    binding (a binding never overrides a mismatch) and let --init-seat bind seat.json to a
    throwaway container. So a container observes no fingerprint, exactly as on 5.2."""
    environ = os.environ if environ is None else environ
    if environ.get('container'):
        return True
    if any(Path(m).exists() for m in markers):
        return True
    try:
        return bool(CONTAINER_CGROUP.search(Path(cgroup).read_text(encoding='ascii', errors='replace')))
    except OSError:
        return False


def _linux_id(paths=('/etc/machine-id', '/var/lib/dbus/machine-id'), container=None):
    if in_container() if container is None else container:
        return None
    for path in paths:
        try:
            value = Path(path).read_text(encoding='ascii').strip()
        except (OSError, ValueError):
            continue
        if re.fullmatch(r'[0-9a-fA-F]{32}', value):
            return value
    return None


def fingerprint(platform, raw):
    """sha256 of the platform's machine id. macOS hashes the bare UUID exactly as 5.2.x did, so
    every existing seat.json still matches; Windows and Linux ids carry a prefix so ids from two
    platforms can never collide."""
    if not raw:
        return None
    raw = raw.strip().lower()
    if platform == 'darwin':
        return hashlib.sha256(raw.encode()).hexdigest()
    return hashlib.sha256(f'{platform}:{raw}'.encode()).hexdigest()


SCHEMES = {'darwin': 'sha256:macos-ioplatformuuid-lowercase', 'win32': 'sha256:win32-machineguid-lowercase',
           'linux': 'sha256:linux-machine-id-lowercase'}


def current_platform():
    return 'win32' if sys.platform.startswith('win') else 'linux' if sys.platform.startswith('linux') else sys.platform


def machine_id(platform=None):
    platform = platform or current_platform()
    reader = {'darwin': _macos_id, 'win32': _windows_id, 'linux': _linux_id}.get(platform)
    return fingerprint(platform, reader()) if reader else None


def utcnow():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def parse_ts(value):
    if not isinstance(value, str):
        return None
    try:
        t = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None
    return t if t.tzinfo else None


def fmt_ts(t):
    return t.astimezone(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def binding_client(config):
    """The one client allowed to hold a host binding and own the clock.

    Co-primary (Phase 0, 2026-09-11): several clients may resolve `primary`, so "the primary
    client" is no longer a unique key. `clock_owner` names it explicitly. Falls back to the sole
    primary so a pre-co-primary seat.json still resolves exactly as before.
    """
    if not isinstance(config, dict):
        return None
    owner = config.get('clock_owner')
    clients = config.get('clients')
    if not isinstance(clients, dict):
        return None
    if isinstance(owner, str) and isinstance(clients.get(owner), dict) \
            and clients[owner].get('role') == 'primary':
        return owner
    primaries = [k for k, v in clients.items() if isinstance(v, dict) and v.get('role') == 'primary']
    return primaries[0] if len(primaries) == 1 else None


def check_binding(config, client, binding, now=None):
    """Return (ok, reason, expires). Pure function; every rule above is one line here."""
    now = now or utcnow()
    if not isinstance(binding, dict):
        return False, 'no host binding present', None
    if binding.get('schema_version') != BINDING_SCHEMA:
        return False, 'host binding has an unsupported schema', None
    if binding.get('client') != client:
        return False, 'host binding was issued for a different client', None
    if binding_client(config) != client:
        return False, 'host binding names a client that is not the clock owner', None
    if not binding.get('machine_id') or binding.get('machine_id') != config.get('machine_id'):
        return False, 'host binding does not match this installation', None
    issued, expires = parse_ts(binding.get('issued_at')), parse_ts(binding.get('expires_at'))
    if not issued or not expires:
        return False, 'host binding timestamps are malformed', None
    if issued > now + CLOCK_SKEW:
        return False, 'host binding was issued in the future', None
    if expires - issued > dt.timedelta(hours=TTL_MAX_HOURS) + CLOCK_SKEW:
        return False, f'host binding lifetime exceeds {TTL_MAX_HOURS} hours', None
    if expires <= now:
        return False, 'host binding has expired', expires
    return True, 'host binding fresh', expires


def resolve(config, client, observed, binding=None, now=None):
    safe = client if CLIENT_RE.fullmatch(client or '') else 'unknown'
    fallback = 'unassigned-' + safe + '-' + ((observed or 'unavailable')[:12])
    via, binding_expires = 'observed', None

    def result(seat, role, reason, warning=None):
        # Co-primary: role grants writes; owns_clock grants schedules. Only the clock owner keeps
        # the shared ledger, so every other client still appends to its own shard.
        owns_clock = role == 'primary' and client == binding_client(config)
        return dict(client=client, seat=seat, role=role, reason=reason, warning=warning,
                    owns_clock=owns_clock,
                    ledger='dean/.activity.jsonl' if owns_clock else f'dean/.activity.{seat}.jsonl',
                    lane=f'active-work/lanes/{seat}/', via=via,
                    binding_expires=fmt_ts(binding_expires) if binding_expires else None)

    def deny(reason):
        nonlocal via, binding_expires
        via, binding_expires = 'unresolved', None
        return result(fallback, 'satellite', reason, 'Seat identity unresolved: ' + reason + '. Primary writes and schedules are disabled; report this visibly to the owner.')

    if not isinstance(config, dict) or config.get('schema_version') != 2:
        return deny('missing or unsupported seat configuration')
    if not observed:
        ok, why, expires = check_binding(config, client, binding, now)
        if not ok:
            return deny('host machine fingerprint unavailable' + ('' if binding is None else f' ({why})'))
        observed, via, binding_expires = config.get('machine_id'), 'host-binding', expires
    if observed != config.get('machine_id'):
        return deny('host machine fingerprint does not match this installation')
    clients = config.get('clients')
    if not isinstance(clients, dict):
        return deny('invalid client assignments')
    if not any(isinstance(v, dict) and v.get('role') == 'primary' for v in clients.values()):
        return deny('configuration must designate at least one primary client')
    if binding_client(config) is None:
        return deny('configuration must name a clock_owner when more than one client is primary')
    assignment = clients.get(client)
    if not isinstance(assignment, dict):
        return deny('client is not assigned')
    seat, role = assignment.get('seat'), assignment.get('role')
    if role not in ('primary', 'satellite') or not isinstance(seat, str) or not re.fullmatch(r'[a-z0-9-]{1,64}', seat):
        return deny('invalid seat assignment')
    if len([v for v in clients.values() if isinstance(v, dict) and v.get('seat') == seat]) != 1:
        return deny('seat name is assigned to multiple clients')
    reason = 'exact machine fingerprint and client assignment matched' if via == 'observed' else \
        'host binding accepted: fingerprint unavailable here, bound by the host'
    return result(seat, role, reason)


def issue_binding(config, client, observed, ttl_hours, now=None, issuer=None):
    """Return (binding or None, reason). Refuses unless the issuing host IS this installation."""
    now = now or utcnow()
    if not isinstance(config, dict) or config.get('schema_version') != 2 or not config.get('machine_id'):
        return None, 'missing or unsupported seat configuration'
    if not observed:
        return None, 'refused: fingerprint not observed here; issue the binding from the host, not a sandbox'
    if observed != config.get('machine_id'):
        return None, 'refused: this host is not the installation named in seat.json'
    if binding_client(config) != client:
        return None, f'refused: {client!r} is not the clock owner'
    try:
        ttl = float(ttl_hours)
    except (TypeError, ValueError):
        return None, 'refused: --ttl-hours must be a number'
    ttl = max(TTL_MIN_HOURS, min(TTL_MAX_HOURS, ttl))
    seat = config['clients'][client].get('seat')
    return {
        'schema_version': BINDING_SCHEMA, 'client': client, 'machine_id': observed,
        'issued_at': fmt_ts(now), 'expires_at': fmt_ts(now + dt.timedelta(hours=ttl)), 'ttl_hours': ttl,
        'issued_by': issuer or f'host:{seat} (fingerprint observed)',
    }, f'issued for {client} ({seat}), expires {fmt_ts(now + dt.timedelta(hours=ttl))}'


def init_seat(observed, primaries, satellites=(), clock_owner=None, machine=None, platform=None):
    """Build seat.json from the owner's declaration. Returns (config, None) or (None, reason)."""
    if not observed:
        return None, 'refused: machine fingerprint not observed here; run this on the host itself, not in a sandbox'
    primaries, satellites = list(dict.fromkeys(primaries or ())), list(dict.fromkeys(satellites or ()))
    if not primaries:
        return None, 'refused: name at least one primary app (--primary)'
    for c in primaries + satellites:
        if not CLIENT_RE.fullmatch(c):
            return None, f'refused: invalid client name {c!r}'
    if set(primaries) & set(satellites):
        return None, 'refused: an app cannot be both primary and satellite'
    if clock_owner is None:
        if len(primaries) > 1:
            return None, 'refused: with more than one primary, name the one that runs schedules (--clock-owner)'
        clock_owner = primaries[0]
    if clock_owner not in primaries:
        return None, 'refused: the clock owner must be one of the primary apps'
    name = re.sub(r'[^a-z0-9-]+', '-', (machine or socket.gethostname().split('.')[0] or 'this').lower()).strip('-')[:20] or 'this'
    clients = {c: {'seat': f'{name}-{c}'[:64], 'role': 'primary'} for c in primaries}
    clients.update({c: {'seat': f'{name}-{c}'[:64], 'role': 'satellite'} for c in satellites})
    # Top-level seat/role/client name the clock owner's seat: /campus-doctor's seat check and the
    # foreign-write check read them (the same shape the 5.2 seat files carry).
    return {'schema_version': 2, 'seat': clients[clock_owner]['seat'], 'role': 'primary', 'client': clock_owner,
            'machine_id': observed, 'machine_id_scheme': SCHEMES.get(platform or current_platform(), 'sha256:unknown'),
            'clock_owner': clock_owner, 'declared_by': 'owner', 'declared_at': fmt_ts(utcnow()), 'clients': clients}, None


def write_file(path, data, overwrite):
    """Write `data` to `path` without following links (5.2.18 rule). Never writes through a link at
    the file or its folder. A file that does not exist yet is created exclusively and directly (no
    temp file, nothing to delete afterwards); with overwrite=False an existing file is refused.
    Replacing an existing file goes through a random temp name. Returns None or a reason."""
    path = Path(path)
    if path.parent.is_symlink() or path.is_symlink():
        return f'refused: {path.name} or its folder is a link; fix it by hand'
    if not overwrite and path.exists():
        return f'refused: {path.name} already exists; the owner edits it by hand'
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0)
    if not overwrite or not path.exists():
        # 5.3.7: create the file itself, exclusively. O_EXCL fails if it exists (no check-then-write
        # race) and never follows a link, and no temp file is made: an app that may create files
        # but not delete them left `.seat.json.<hex>.tmp` behind on a buyer's first install.
        try:
            fd = os.open(path, flags, 0o600)
        except FileExistsError:
            if not overwrite:
                return f'refused: {path.name} already exists; the owner edits it by hand'
            fd = None                       # it appeared meanwhile: replace it below
        except OSError as exc:
            return f'refused: could not write {path.name}: {exc}'
        if fd is not None:
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as fh:
                    fh.write(data)
                return None
            except OSError as exc:          # a half-written file must not pass for the owner's
                try:
                    os.unlink(path)
                    return f'refused: could not write {path.name}: {exc}'
                except OSError:
                    return (f'refused: could not finish writing {path.name} ({exc}); it is incomplete - '
                            f'delete it by hand, then run this again')
    tmp = path.with_name(f'.{path.name}.{os.urandom(6).hex()}.tmp')
    try:
        fd = os.open(tmp, flags, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            fh.write(data)
        os.replace(tmp, path)               # replace consumes the temp: nothing to delete
    except OSError as exc:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        return f'refused: could not write {path.name}: {exc}'
    return None


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--client', help='Actual host: claude-cowork, claude-code, or codex; never choose by desired role')
    ap.add_argument('--init-seat', action='store_true', help="write seat.json from the owner's declared roles (host only; never overwrites)")
    ap.add_argument('--primary', action='append', default=[], help='with --init-seat: an app the owner makes primary (repeatable)')
    ap.add_argument('--satellite', action='append', default=[], help='with --init-seat: an app that only proposes (repeatable)')
    ap.add_argument('--clock-owner', default=None, help='with --init-seat: the one primary app that runs schedules')
    ap.add_argument('--machine', default=None, help='with --init-seat: short machine name for seat names (default: hostname)')
    ap.add_argument('--seat-file', default=str(Path(__file__).with_name('seat.json')), help=argparse.SUPPRESS)
    ap.add_argument('--binding-file', default=None, help=f'default: {BINDING_FILE} beside seat.json')
    ap.add_argument('--issue-binding', action='store_true', help='write the host binding (host only; refuses in a sandbox)')
    ap.add_argument('--ttl-hours', default=TTL_DEFAULT_HOURS, help=f'binding lifetime, clamped to {TTL_MIN_HOURS}..{TTL_MAX_HOURS} (default {TTL_DEFAULT_HOURS})')
    ap.add_argument('--now', default=None, help=argparse.SUPPRESS)   # fixtures only: ISO-8601 UTC
    args = ap.parse_args()
    seat_file = Path(args.seat_file)
    binding_file = Path(args.binding_file) if args.binding_file else seat_file.with_name(BINDING_FILE)
    config, now = load_json(seat_file), (parse_ts(args.now) if args.now else None)
    if args.now and not now:
        print(json.dumps({'error': '--now must be ISO-8601 with a timezone'})); return 2

    if args.init_seat:
        if seat_file.exists() or seat_file.is_symlink():
            print(json.dumps({'written': False, 'reason': 'refused: seat.json already exists; the owner edits it by hand', 'file': str(seat_file)}, indent=2)); return 2
        seat, reason = init_seat(machine_id(), args.primary, args.satellite, args.clock_owner, args.machine)
        if seat is None:
            print(json.dumps({'written': False, 'reason': reason, 'file': str(seat_file)}, indent=2)); return 2
        why = write_file(seat_file, json.dumps(seat, indent=2) + '\n', overwrite=False)
        if why:
            print(json.dumps({'written': False, 'reason': why, 'file': str(seat_file)}, indent=2)); return 2
        print(json.dumps({'written': True, 'file': str(seat_file), 'seat': seat}, indent=2)); return 0
    if not args.client:
        ap.error('--client is required')

    if args.issue_binding:
        binding, reason = issue_binding(config, args.client, machine_id(), args.ttl_hours, now)
        if binding is None:
            print(json.dumps({'issued': False, 'reason': reason, 'file': str(binding_file)}, indent=2)); return 2
        why = write_file(binding_file, json.dumps(binding, indent=2) + '\n', overwrite=True)
        if why:
            print(json.dumps({'issued': False, 'reason': why, 'file': str(binding_file)}, indent=2)); return 2
        print(json.dumps({'issued': True, 'reason': reason, 'file': str(binding_file), 'binding': binding}, indent=2)); return 0

    output = resolve(config, args.client, machine_id(), load_json(binding_file), now)
    print(json.dumps(output, indent=2))
    return 2 if output['warning'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
