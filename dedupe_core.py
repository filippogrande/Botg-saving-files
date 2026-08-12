"""
Modulo unico di deduplicazione.
- deduplica_file(path, db_dir): per-file, con priorità /autodownloader/ (usato durante i download)
- find_duplicates(directory): sweep ricorsivo che rimuove i duplicati (usato da watcher/cron)
- rehash_files(directory): ricalcola gli hash nel DB (usato da /recalculate)
Tutti condividono la stessa logica di scelta del "file da tenere" (_keep_priority).
"""
import os
from pathlib import Path
import hashlib
import fcntl

from db_helper import (
    ensure_db, insert_file, find_files_by_hash, remove_filepath,
    get_file_entry, update_file_hash,
)

VALID_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".mov")


def file_hash(path):
    """MD5 streaming del file. None in caso di errore."""
    try:
        m = hashlib.md5()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b""):
                m.update(chunk)
        return m.hexdigest()
    except Exception as e:
        print(f"Errore calcolo hash per {path}: {e}")
        return None


def _iter_media(root):
    """Yield dei path dei file media ricorsivamente in root."""
    for r, _dirs, filenames in os.walk(root):
        for fname in filenames:
            if fname.lower().endswith(VALID_EXTS):
                yield os.path.join(r, fname)


def _is_auto(path):
    return 'autodownloader' in Path(os.path.abspath(path)).parts


def _keep_priority(a, b):
    """Ritorna (keep, drop) tra due path duplicati.
    Priorità: chi sta in /autodownloader/ vince; a parità, il più recente (mtime)."""
    a_auto = _is_auto(a)
    b_auto = _is_auto(b)
    if a_auto != b_auto:
        return (a, b) if a_auto else (b, a)
    try:
        return (a, b) if os.path.getmtime(a) >= os.path.getmtime(b) else (b, a)
    except Exception:
        return (a, b)


def _with_lock(db_dir, fn):
    """Esegue fn() con un lock per-directory per evitare corse."""
    lock_path = os.path.join(db_dir, '.dedupe.lock')
    lock_file = None
    try:
        lock_file = open(lock_path, 'w')
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lock_file.close()
            return None  # un'altra istanza gira: sii conservativo
    except Exception:
        lock_file = None
    try:
        return fn()
    finally:
        try:
            if lock_file:
                fcntl.flock(lock_file, fcntl.LOCK_UN)
                lock_file.close()
        except Exception:
            pass


def deduplica_file(path, db_dir=None):
    """Per-file (chiamato durante il download). Ritorna True se tenuto, False se duplicato rimosso."""
    if not os.path.exists(path):
        return False
    db_dir = db_dir or os.path.dirname(path)
    ensure_db(db_dir)
    h = file_hash(path)
    if not h:
        return False

    def _run():
        others = [s for s in find_files_by_hash(db_dir, h)
                  if os.path.abspath(s) != os.path.abspath(path)]
        if not others:
            insert_file(db_dir, path, h)
            return True
        keep, drop = _keep_priority(path, others[0])
        for s in others[1:]:
            keep, _ = _keep_priority(keep, s)
        if drop == path:
            try:
                os.remove(path)
            except Exception:
                pass
            remove_filepath(db_dir, path)
            return False
        for s in others:
            if s != keep:
                try:
                    os.remove(s)
                except Exception:
                    pass
                remove_filepath(db_dir, s)
        insert_file(db_dir, path, h)
        return True

    res = _with_lock(db_dir, _run)
    return res if res is not None else True


def scan_and_clean(root, recheck=False, debug_callback=None):
    """Sweep ricorsivo: rimuove i duplicati usando _keep_priority.
    recheck=True: ricrea le voci DB (upsert) invece di fidarsi di quelle esistenti."""
    def debug(msg):
        print(msg)
        if debug_callback:
            try:
                debug_callback(msg)
            except Exception:
                pass

    ensure_db(root)

    def _run():
        seen = {}  # hash -> keep_path (giro corrente)
        removed = 0
        for path in _iter_media(root):
            h = file_hash(path)
            if not h:
                continue
            if h in seen:
                keep, drop = _keep_priority(seen[h], path)
                if drop == path:
                    try:
                        os.remove(path)
                    except Exception:
                        pass
                    remove_filepath(root, path)
                    removed += 1
                else:
                    try:
                        os.remove(seen[h])
                    except Exception:
                        pass
                    remove_filepath(root, seen[h])
                    removed += 1
                    seen[h] = path
                    _upsert(root, path, h, recheck)
                continue
            others = [s for s in find_files_by_hash(root, h)
                      if os.path.abspath(s) != os.path.abspath(path)]
            if others:
                keep, drop = _keep_priority(path, others[0])
                for s in others[1:]:
                    keep, _ = _keep_priority(keep, s)
                if drop == path:
                    try:
                        os.remove(path)
                    except Exception:
                        pass
                    remove_filepath(root, path)
                    removed += 1
                    seen[h] = keep
                else:
                    for s in others:
                        if s != keep:
                            try:
                                os.remove(s)
                            except Exception:
                                pass
                            remove_filepath(root, s)
                            removed += 1
                    seen[h] = path
                    _upsert(root, path, h, recheck)
                continue
            seen[h] = path
            _upsert(root, path, h, recheck)
        return removed

    removed = _with_lock(root, _run)
    return removed if removed is not None else 0


def _upsert(root, path, h, recheck):
    if recheck:
        remove_filepath(root, path)
    insert_file(root, path, h)


def find_duplicates(directory, debug_callback=None):
    """Sweep che rimuove duplicati. Ritorna il numero di file rimossi."""
    return scan_and_clean(directory, recheck=False, debug_callback=debug_callback)


def rehash_files(directory, debug_callback=None):
    """Ricalcola gli hash nel DB (upsert). Ritorna statistiche per /recalculate."""
    def debug(msg):
        print(msg)
        if debug_callback:
            try:
                debug_callback(msg)
            except Exception:
                pass

    ensure_db(directory)
    updated = inserted = unchanged = errors = 0

    def _run():
        nonlocal updated, inserted, unchanged, errors
        for path in _iter_media(directory):
            h = file_hash(path)
            if not h:
                errors += 1
                continue
            entry = get_file_entry(directory, path)
            if entry:
                if (entry.get('hash') or '') != h:
                    update_file_hash(directory, path, h)
                    updated += 1
                else:
                    unchanged += 1
            else:
                if insert_file(directory, path, h):
                    inserted += 1
                else:
                    errors += 1
        return {"updated": updated, "inserted": inserted,
                "unchanged": unchanged, "errors": errors}

    res = _with_lock(directory, _run)
    return res if res is not None else {"updated": 0, "inserted": 0, "unchanged": 0, "errors": 0}