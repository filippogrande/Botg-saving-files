import os
def file_hash(path):
    from deduplica import deduplica_file
    try:
        with open(path, 'rb') as f:
            import hashlib
            return hashlib.md5(f.read()).hexdigest()
    except Exception as e:
        print(f"Errore calcolo hash per {path}: {e}")
        return None

import os
import time
import traceback
import fcntl

def file_hash(path):
    try:
        import hashlib
        m = hashlib.md5()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b""):
                m.update(chunk)
        return m.hexdigest()
    except Exception as e:
        print(f"Errore calcolo hash per {path}: {e}")
        return None


def find_duplicates(directory, debug_callback=None):
    """
    Cerca file duplicati usando il campo hash nel DB.
    Restituisce il numero di duplicati rimossi.
    debug_callback: funzione opzionale per inviare messaggi di debug (es: su Telegram)
    """
    def debug(msg):
        print(msg)
        if debug_callback:
            try:
                debug_callback(msg)
            except Exception:
                pass

    debug(f"[DEBUG] find_duplicates chiamata su: {directory}")

    # Acquire a simple file lock per-directory to avoid concurrent runs
    lock_path = os.path.join(directory, '.dedupe.lock')
    lock_file = None
    try:
        lock_file = open(lock_path, 'w')
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            debug("[DEBUG] Un'altra istanza della deduplica è in esecuzione; esco." )
            lock_file.close()
            return 0
    except Exception as e:
        debug(f"[DEBUG] Impossibile acquisire il lock {lock_path}: {e}")
        # proceed anyway
    VALID_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".mov")
    removed = 0
    files = []
    try:
        for root, dirs, filenames in os.walk(directory):
            for fname in filenames:
                if fname.lower().endswith(VALID_EXTS):
                    files.append(os.path.join(root, fname))
    except Exception as e:
        debug(f"[DEBUG] Errore lettura directory ricorsiva: {e}")

    debug(f"[DEBUG] Trovati {len(files)} file candidati (ricorsivo) nella directory {directory}")
    from db_helper import remove_filepath, insert_file, find_files_by_hash

    total = len(files)
    last_log = time.time()
    last_file = None
    last_phase = None
    stuck_since = None

    for idx, path in enumerate(files, 1):
        fname = os.path.basename(path)
        now = time.time()
        phase = "calcolo hash"
        if last_file == fname and stuck_since and now - stuck_since > 15:
            debug(f"[ATTENZIONE] Bloccato su {fname} ({last_phase}) da oltre 15s!")
            try:
                debug(traceback.format_stack())
            except Exception:
                pass
            stuck_since = now
        if last_file != fname:
            stuck_since = now
        if idx == 1 or idx == total or now - last_log > 5:
            debug(f"Deduplica: {idx}/{total} file (file: {fname}, fase: {phase})")
            last_log = now
        last_file = fname
        last_phase = phase

        # Calcola hash
        h = file_hash(path)
        phase = "verifica hash e DB"
        last_phase = phase
        if not h:
            continue

        # Controlla se esistono altri file con lo stesso hash
        try:
            same = find_files_by_hash(directory, h)
        except Exception as e:
            debug(f"[DEBUG] Errore query DB per hash {h}: {e}")
            same = []

        # Se esiste almeno un altro file con lo stesso hash, rimuovi questo file (è duplicato)
        other_same = [s for s in same if os.path.abspath(s) != os.path.abspath(path)]
        if other_same:
            phase = "rimozione duplicato"
            last_phase = phase
            try:
                os.remove(path)
                removed += 1
                remove_filepath(directory, path)
            except Exception as e:
                debug(f"Errore rimozione file {path}: {e}")
            continue

        # Nessun duplicato trovato: registra/aggiorna il DB per questo filepath
        try:
            remove_filepath(directory, path)
            inserted = insert_file(directory, path, h)
            if not inserted:
                debug(f"[DEBUG] Insert failed for {path} despite remove; possibile race condition")
        except Exception as e:
            debug(f"[DEBUG] Errore inserimento DB per {path}: {e}")

    debug(f"[DEBUG] Fine find_duplicates: rimossi {removed} duplicati")
    try:
        return removed
    finally:
        try:
            if lock_file:
                fcntl.flock(lock_file, fcntl.LOCK_UN)
                lock_file.close()
        except Exception:
            pass
