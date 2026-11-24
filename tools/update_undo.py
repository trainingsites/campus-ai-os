#!/usr/bin/env python3
"""Snapshot a campus before /update-workspace writes, and undo that update afterwards.

5.3.8. Field report (2026-11-23): an owner answered the edition question wrong, the update
relabelled the departments and recorded the wrong edition, and there was no way back. The safety
copy held some files, missed the work diary, and nothing listed what the update had created.

  snapshot --campus-root PATH   before any write: copy the files an update may change, and
                                record which files and folders an update may create are absent
  seal     --campus-root PATH --snapshot NAME
                                after the last write: record what the update left, so a later
                                undo can tell the update's changes from the owner's
  undo     --campus-root PATH   put back what the update changed and move what it created into
                                the snapshot's `after/` folder (moved, never deleted)
           --dry-run            print what undo would do and change nothing
  list     --campus-root PATH   the snapshots this campus holds

What undo does to each kind of file:
- KERNEL files (version marker, registry, kernel reference files): restored.
- ENTRY files (the chief of staff entry file on any host; an update only inserts into them): restored, and
  flagged when they changed after the update, because that change is the owner's.
- CREATE-ONLY files (job cards, seat file, setup progress; an update never rewrites an existing
  one): moved away only when the update created them. An existing one is never touched.
- FOLDERS an update may create: moved away only when the update created them and they are still
  empty of anything else. The kernel kit is kernel-owned and is moved away whenever it changed.
- OWNER files (memory, tasks, work diaries): copied for safety, never restored.
With a seal, a file the update did not change is left alone whatever happened to it since.

Rules: stdlib only. Never follows a link, never writes outside the campus root. Nothing is
deleted. If undo stops partway it says what is done and what is not, and can be run again.

Undo acts on the newest update only. It never walks back to an older one in the same run.

Exit: 0 done, 1 nothing to do or a refusal (nothing changed), 2 a bad option, 3 stopped partway.
"""
import argparse
import re
import datetime
import hashlib
import json
import os
import shutil
import sys

SNAP_DIR = "dean/archive/update-undo"
RECORD = "UNDO.json"

KERNEL_FILES = (
    ".campus-os/registry.json",
    ".campus-os/context-files.md",
    ".campus-os/ledger-paths.md",
    ".campus-os/run-id-and-interop.md",
    ".campus-os/resolve-seat.py",
    ".campus-os/registration-block-spec.md",
    ".campus-os/registration-overrides.json",
    ".campus-os/model-routing.md",
    "workspace.json",  # last: the version marker flips back only when everything else is done
)
# Every host's entry filename is listed, so no one host is assumed (PLATFORM.md).
ENTRY_NAMES = ("CLAUDE.md", "AGENTS.md", "AGENTS.override.md", "CODEX.md")  # platform-literal-ok
ENTRY_FILES = tuple("dean/" + n for n in ENTRY_NAMES) + ENTRY_NAMES + ("GEMINI.md",)
CREATE_ONLY = (
    "dean/job-cards.md", ".campus-os/seat.json", ".campus-os/host-binding.json", "shared/setup-progress.md",
)
KIT_DIR = ".campus-os/kernel"
KIT_STAMP = KIT_DIR + "/KIT.json"
CREATED_DIRS = (".campus-os/scan", "atlas/config", "dean/skill-candidates")
OWNER_FILES = ("dean/memory.md", "dean/TASKS.md", "dean/.activity.jsonl")
MANAGED_FILES = KERNEL_FILES + ENTRY_FILES + CREATE_ONLY
MANAGED_DIRS = (KIT_DIR,) + CREATED_DIRS


class Refused(Exception):
    pass


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def safe(root, rel):
    """Absolute path for rel under root. Refuses an unsafe name or a link anywhere on the way."""
    cur = root
    for part in rel.replace("\\", "/").split("/"):
        if part in ("", ".", ".."):
            raise Refused("unsafe path %r." % rel)
        cur = os.path.join(cur, part)
        if os.path.islink(cur):
            raise Refused("%s is a link; this tool never follows one." % os.path.relpath(cur, root).replace(os.sep, "/"))
    return cur


def is_link_on_path(root, rel):
    try:
        safe(root, rel)
        return False
    except Refused:
        return True


def state(root, rel):
    """'link', None (absent) or the file's sha256."""
    if is_link_on_path(root, rel):
        return "link"
    p = os.path.join(root, *rel.split("/"))
    return sha(p) if os.path.isfile(p) else None


def owner_files(root):
    found = list(OWNER_FILES)
    dean = os.path.join(root, "dean")
    if os.path.isdir(dean) and not os.path.islink(dean):
        for name in sorted(os.listdir(dean)):
            if name.startswith(".activity.") and name.endswith(".jsonl"):
                found.append("dean/" + name)
    return found


def campus_root(arg):
    root = os.path.abspath(arg)
    if not os.path.isdir(root) or os.path.islink(root):
        raise Refused("%s is not a folder." % arg)
    if not any(os.path.exists(os.path.join(root, m)) for m in ("workspace.json", ".campus-os", "dean")):
        raise Refused("%s does not look like a campus (no workspace.json, .campus-os or dean folder)." % arg)
    return root


def read_record(root, name):
    """The snapshot's record, or None when it is missing, unreadable or not one this tool wrote."""
    try:
        path = os.path.join(safe(root, SNAP_DIR + "/" + name), RECORD)
        if os.path.islink(path):
            return None
        rec = json.load(open(path, encoding="utf-8"))
    except (Refused, OSError, ValueError):
        return None
    if not isinstance(rec, dict) or rec.get("format") != 2:
        return None
    for key in ("files", "dirs", "owner_files"):
        if not isinstance(rec.get(key), dict):
            return None
    if set(rec["files"]) - set(MANAGED_FILES) or set(rec["dirs"]) - set(MANAGED_DIRS):
        return None
    if any(v is not None and not isinstance(v, str) for v in rec["files"].values()):
        return None
    if any(not isinstance(v, bool) for v in rec["dirs"].values()):
        return None
    if rec.get("sealed") is not None and not isinstance(rec.get("sealed"), dict):
        return None
    return rec


def write_record(root, name, rec):
    path = os.path.join(safe(root, SNAP_DIR + "/" + name), RECORD)
    tmp = path + ".new"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def snapshot_names(root):
    try:
        base = safe(root, SNAP_DIR)
    except Refused:
        return []
    if not os.path.isdir(base):
        return []
    return sorted(n for n in os.listdir(base)
                  if re.fullmatch(r"\d{8}T\d{6}Z", n) and os.path.isdir(os.path.join(base, n)))


def open_snapshots(root):
    """(names still open newest last, names whose record cannot be read)."""
    good, bad = [], []
    for name in snapshot_names(root):
        rec = read_record(root, name)
        if rec is None:
            bad.append(name)
        elif not rec.get("undone"):
            good.append(name)
    return good, bad


def cmd_snapshot(root):
    stamp = now()
    snap_rel = SNAP_DIR + "/" + stamp
    snap = safe(root, snap_rel)
    if os.path.exists(snap):
        raise Refused("a snapshot named %s already exists; wait a second and run again." % stamp)
    rec = {"tool": "update_undo", "format": 2, "taken": stamp, "files": {}, "dirs": {}, "owner_files": {},
           "links": [], "kit": None, "sealed": None, "undone": None}
    try:
        ws = json.load(open(os.path.join(root, "workspace.json"), encoding="utf-8"))
        rec["version_before"], rec["pack_before"] = ws.get("version"), ws.get("pack")
    except (OSError, ValueError, AttributeError):
        rec["version_before"] = rec["pack_before"] = None
    # Decide everything before the first write, so a refusal leaves no partial folder.
    copies = []
    for rel in MANAGED_FILES:
        st = state(root, rel)
        if st == "link":
            rec["links"].append(rel)  # a linked file is left alone, by snapshot and by undo
            continue
        rec["files"][rel] = st
        if st:
            copies.append(rel)
    for rel in owner_files(root):
        st = state(root, rel)
        if st == "link":
            continue
        rec["owner_files"][rel] = st
        if st:
            copies.append(rel)
    for rel in MANAGED_DIRS:
        if is_link_on_path(root, rel):
            rec["links"].append(rel)
            continue
        rec["dirs"][rel] = os.path.isdir(os.path.join(root, *rel.split("/")))
    if KIT_DIR in rec["dirs"]:
        st = state(root, KIT_STAMP)
        rec["kit"] = st if st != "link" else None
    if rec["dirs"].get(KIT_DIR):
        # The kit is kernel-owned and an update overwrites it, so the old one is saved whole.
        kit = os.path.join(root, *KIT_DIR.split("/"))
        for base, dirs, files in os.walk(kit):
            dirs[:] = [x for x in dirs if not os.path.islink(os.path.join(base, x)) and x != "__pycache__"]
            for f in files:
                full = os.path.join(base, f)
                if not os.path.islink(full):
                    copies.append(os.path.relpath(full, root).replace(os.sep, "/"))
    try:
        os.makedirs(os.path.join(snap, "before"))
        for rel in copies:
            dst = os.path.join(snap, "before", *rel.split("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(os.path.join(root, *rel.split("/")), dst)
        with open(os.path.join(snap, RECORD), "x", encoding="utf-8") as f:
            json.dump(rec, f, indent=2)
            f.write("\n")
    except OSError as e:
        shutil.rmtree(snap, ignore_errors=True)  # this run's own half-made folder, nothing of the owner's
        raise Refused("the snapshot could not be written (%s)." % e)
    print("SNAPSHOT %s" % stamp)
    print("  copied %d files to %s/before" % (len(copies), snap_rel))
    for rel in rec["links"]:
        print("  left alone (a link): %s" % rel)
    print("  after the last write of this update, run: seal --campus-root <campus> --snapshot %s" % stamp)
    return 0


def cmd_seal(root, name):
    # The name is required: a seal must land on the snapshot THIS run took, never on one an
    # earlier run left behind.
    good, _ = open_snapshots(root)
    if not name:
        raise Refused("seal needs --snapshot NAME, the name this run's snapshot printed.")
    if name not in good:
        raise Refused("no open snapshot named %s." % name)
    if name != good[-1]:
        raise Refused("snapshot %s is not the newest one; a newer update has started since." % name)
    rec = read_record(root, name)
    if rec.get("sealed"):
        raise Refused("snapshot %s is already sealed." % name)
    rec["sealed"] = {"at": now(), "files": {rel: state(root, rel) for rel in rec["files"]},
                     "kit": state(root, KIT_STAMP) if KIT_DIR in rec["dirs"] else None}
    changed = sorted(rel for rel, was in rec["files"].items() if rec["sealed"]["files"][rel] != was)
    write_record(root, name, rec)
    print("SEALED %s" % name)
    print("  this update changed or created %d managed files" % len(changed))
    print('  to undo it later, the owner says: "undo the last update"')
    return 0


def plan(root, name, rec, keep):
    """What undo would do. Raises Refused before anything is changed."""
    snap_rel = SNAP_DIR + "/" + name
    sealed = (rec.get("sealed") or {}).get("files")
    acts = {"restore": [], "remove": [], "remove_dirs": [], "left": [], "yours": []}
    for rel in ENTRY_FILES + CREATE_ONLY + KERNEL_FILES:  # this order ends with workspace.json
        if rel not in rec["files"] or rel in keep:
            continue
        was = rec["files"][rel]
        cur = state(root, rel)
        if cur == "link":
            acts["left"].append((rel, "is a link now"))
            continue
        if isinstance(sealed, dict) and sealed.get(rel, was) == was:
            continue  # the update did not change this file; whatever happened since is not ours to undo
        if cur == was:
            continue
        changed_since = isinstance(sealed, dict) and cur != sealed.get(rel)
        if was is None:
            if rel == "workspace.json" and not isinstance(sealed, dict):
                raise Refused("the record says workspace.json did not exist, and the update was never sealed.")
            if rel in ENTRY_FILES + KERNEL_FILES and rel != "workspace.json" and not isinstance(sealed, dict) \
                    and rec.get("version_before"):
                acts["left"].append((rel, "the record says it did not exist, which an update of a %s campus does not explain"
                                     % rec["version_before"]))
                continue
            acts["remove"].append(rel)
            if changed_since or (sealed is None and rel in CREATE_ONLY):
                acts["yours"].append(rel)
            continue
        if rel in CREATE_ONLY:
            acts["left"].append((rel, "an update never rewrites it, so the change is yours"))
            continue
        saved = safe(root, snap_rel + "/before/" + rel)
        if not os.path.isfile(saved) or sha(saved) != was:
            raise Refused("the saved copy of %s is missing or was changed." % rel)
        acts["restore"].append(rel)
        if changed_since or (sealed is None and rel in ENTRY_FILES):
            acts["yours"].append(rel)
    for rel in MANAGED_DIRS:
        if rel not in rec["dirs"] or rel in keep:
            continue
        if is_link_on_path(root, rel):
            acts["left"].append((rel, "is a link now"))
            continue
        cur = os.path.join(root, *rel.split("/"))
        if not os.path.isdir(cur):
            continue
        if rel == KIT_DIR:
            kit_sealed = (rec.get("sealed") or {}).get("kit", "unsealed") if rec.get("sealed") else "unsealed"
            if kit_sealed != "unsealed" and kit_sealed == rec.get("kit") and rec["dirs"][rel]:
                continue  # the update left the kit as it was
            if not rec["dirs"][rel] or state(root, KIT_STAMP) != rec.get("kit"):
                acts["remove_dirs"].append(rel)  # kernel-owned; the saved one, if any, is put back
        elif not rec["dirs"][rel]:
            if any(files for _, _, files in os.walk(cur)):
                acts["left"].append((rel, "the update created it, but it now holds files"))
            else:
                acts["remove_dirs"].append(rel)
    for rel in acts["restore"] + acts["remove"] + acts["remove_dirs"]:
        safe(root, snap_rel + "/after/" + rel)
    return acts


def free_name(path):
    if not os.path.lexists(path):
        return path
    n = 2
    while os.path.lexists("%s.%d" % (path, n)):
        n += 1
    return "%s.%d" % (path, n)


def move_to_after(root, name, rel):
    dst = free_name(safe(root, SNAP_DIR + "/" + name + "/after/" + rel))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.move(os.path.join(root, *rel.split("/")), dst)


def show(acts, name, dry):
    word = ("would restore", "would move away") if dry else ("restored   ", "moved away ")
    for rel in acts["restore"]:
        print("  %s  %s" % (word[0], rel))
    for rel in acts["remove"] + acts["remove_dirs"]:
        print("  %s  %s" % (word[1], rel))
    if KIT_DIR in acts["remove_dirs"]:
        print("  the kernel kit belongs to the plugin: the one saved before the update %s put back,"
              % ("would be" if dry else "is"))
        print("  or, when the campus had none, the next update copies one in")
    for rel, why in acts["left"]:
        print("  left as it is  %s (%s)" % (rel, why))
    if acts["yours"]:
        print("  CHANGED AFTER THE UPDATE, so they may hold your own edits:")
        for rel in acts["yours"]:
            print("    %s" % rel)
        print("  your newer copies %s in %s/%s/after" % ("would be" if dry else "are", SNAP_DIR, name))


def cmd_undo(root, stamp, keep, dry):
    good, bad = open_snapshots(root)
    for name in bad:
        print("  skipped snapshot %s: its record cannot be read" % name)
    if not good:
        print("NOTHING TO UNDO: no update on record changed this campus.")
        return 1
    if stamp is None:
        newer_bad = [n for n in bad if n > good[-1]]
        if newer_bad:
            raise Refused("snapshot %s is newer and its record cannot be read, so this is not the last update. "
                          "To go back to the one before it, run undo with --snapshot %s." % (newer_bad[-1], good[-1]))
        stamp = good[-1]
    if stamp not in good:
        raise Refused("no open snapshot named %s. Open snapshots here: %s." % (stamp, ", ".join(good)))
    if good[-1] != stamp:
        raise Refused("snapshot %s is not the newest one still open (%s is). Undo the newest first." % (stamp, good[-1]))
    name = stamp
    rec = read_record(root, name)
    acts = plan(root, name, rec, keep)
    if not (acts["restore"] or acts["remove"] or acts["remove_dirs"]):
        # Never walk back to an older update in the same run: the owner asked about the last one.
        older = good[-2] if len(good) > 1 else None
        if dry:
            print("NOTHING TO UNDO: the last update (snapshot %s) changed nothing%s." % (
                name, " that is not being kept" if keep else ""))
        else:
            rec["undone"] = now()
            rec["undo_report"] = {"nothing_to_undo": True, "kept": sorted(keep)}
            write_record(root, name, rec)
            print("NOTHING TO UNDO: the last update (snapshot %s) changed nothing%s. It is now closed." % (
                name, " that is not being kept" if keep else ""))
        if older:
            orec = read_record(root, older) or {}
            print("  the update before it was taken %s, from version %s. To go back to that one too, run undo again." % (
                older, orec.get("version_before") or "unknown"))
        return 1

    if dry:
        print("DRY RUN for snapshot %s (taken %s): nothing was changed" % (name, rec.get("taken")))
        print("  version would go back to %s; edition record to %s" % (
            rec.get("version_before") or "what it was", rec.get("pack_before") or "not recorded"))
        show(acts, name, True)
        return 0

    done = {"restore": [], "remove": [], "remove_dirs": [], "left": acts["left"], "yours": acts["yours"]}
    try:
        for rel in acts["remove"]:
            move_to_after(root, name, rel); done["remove"].append(rel)
        for rel in acts["remove_dirs"]:
            move_to_after(root, name, rel)
            if rel == KIT_DIR:
                saved_kit = safe(root, SNAP_DIR + "/" + name + "/before/" + KIT_DIR)
                if os.path.isdir(saved_kit):
                    shutil.copytree(saved_kit, os.path.join(root, *KIT_DIR.split("/")))
            done["remove_dirs"].append(rel)
        for rel in acts["restore"]:
            dst = os.path.join(root, *rel.split("/"))
            if os.path.lexists(dst):
                move_to_after(root, name, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(safe(root, SNAP_DIR + "/" + name + "/before/" + rel), dst)
            done["restore"].append(rel)
    except OSError as e:
        todo = [r for k in ("remove", "remove_dirs", "restore") for r in acts[k] if r not in done[k]]
        print("STOPPED PARTWAY through snapshot %s: %s" % (name, e))
        show(done, name, False)
        print("  NOT done yet: " + ", ".join(todo))
        print("  nothing was deleted. Close any app that has these files open, then run undo again.")
        return 3
    rec["undone"] = now()
    rec["undo_report"] = {"restored": done["restore"], "moved_away": done["remove"] + done["remove_dirs"],
                          "left": [r for r, _ in acts["left"]], "kept": sorted(keep)}
    write_record(root, name, rec)
    print("UNDONE snapshot %s" % name)
    print("  version back to %s; edition record back to %s" % (
        rec.get("version_before") or "what it was", rec.get("pack_before") or "not recorded"))
    show(done, name, False)
    for rel in sorted(keep):
        print("  kept            %s" % rel)
    changed = [rel for rel, was in sorted(rec["owner_files"].items()) if state(root, rel) not in (was, "link")]
    if changed:
        print("  NOT restored (yours; the update or you wrote in them since): " + ", ".join(changed))
        print("  their earlier copies are in %s/%s/before" % (SNAP_DIR, name))
    print("  NOT undone by this tool: changes an update made inside department or manager folders,")
    print("  and files it added under shared/. They are listed in the update's own report.")
    return 0


def cmd_list(root):
    names = snapshot_names(root)
    if not names:
        print("no update snapshots")
        return 1
    good, _ = open_snapshots(root)
    for name in names:
        rec = read_record(root, name)
        if rec is None:
            print("%s  record cannot be read" % name)
            continue
        status = ("undone " + rec["undone"]) if rec.get("undone") else (
            "can be undone" if good and name == good[-1] else "older; undo the newer ones first")
        print("%s  version_before=%s  pack_before=%s  %s  %s" % (
            name, rec.get("version_before"), rec.get("pack_before"),
            "sealed" if rec.get("sealed") else "not sealed", status))
    return 0


def main():
    ap = argparse.ArgumentParser(description="Snapshot a campus before an update, and undo that update.")
    ap.add_argument("command", choices=("snapshot", "seal", "undo", "list"))
    ap.add_argument("--campus-root", required=True)
    ap.add_argument("--snapshot", help="seal: required, the name snapshot printed. undo: default is the newest")
    ap.add_argument("--keep", action="append", default=[],
                    help="undo: leave this file or folder as it is now (repeatable), e.g. .campus-os/seat.json")
    ap.add_argument("--dry-run", action="store_true", help="undo: print the plan and change nothing")
    a = ap.parse_args()
    keep = set(k.replace("\\", "/").strip("/") for k in a.keep)
    bad = keep - set(MANAGED_FILES) - set(MANAGED_DIRS)
    if bad:
        print("REFUSED: --keep names something this tool does not manage: %s. Nothing was changed." % ", ".join(sorted(bad)))
        sys.exit(2)
    try:
        root = campus_root(a.campus_root)
        if a.command == "snapshot":
            sys.exit(cmd_snapshot(root))
        if a.command == "seal":
            sys.exit(cmd_seal(root, a.snapshot))
        if a.command == "undo":
            sys.exit(cmd_undo(root, a.snapshot, keep, a.dry_run))
        sys.exit(cmd_list(root))
    except Refused as e:
        # Every Refused is raised before the first change of a command.
        print("REFUSED: %s Nothing was changed." % e)
        sys.exit(1)


if __name__ == "__main__":
    main()
