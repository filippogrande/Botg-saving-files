import os
from pathlib import Path
import hashlib
from db_helper import ensure_db, insert_file, find_files_by_hash, remove_filepath


def init_db_all():
    """
    Inizializza il database SQLite nelle directory di salvataggio principali.
    Chiamare questa funzione esplicitamente dall'app al momento opportuno.
    """
    base_dirs = [
        os.environ.get("SAVE_DIR", "/mnt/truenas-bot"),
        os.environ.get("REDDIT_SAVE_DIR"),
        os.environ.get("MEGA_SAVE_DIR"),
        os.environ.get("REDGIFS_SAVE_DIR"),
    ]
    for d in base_dirs:
        if d:
            ensure_db(d)


def deduplica_file(path, db_dir=None):
    """
    Controlla se il file è duplicato tramite hash e database SQLite.
    Se duplicato, elimina il file e restituisce False.
    Se nuovo, lo registra e restituisce True.
    """
    if not os.path.exists(path):
        return False
    db_dir = db_dir or os.path.dirname(path)
    try:
        m = hashlib.md5()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b""):
                m.update(chunk)
        h = m.hexdigest()
    except Exception as e:
        print(f"Errore calcolo hash per {path}: {e}")
        return False

    # Assicurati che il DB della directory esista
    try:
        ensure_db(db_dir)
    except Exception:
        pass

    # Optional per-directory lock to avoid races
    lock_file = None
    try:
        import fcntl
        lock_path = os.path.join(db_dir, '.dedupe.lock')
        lock_file = open(lock_path, 'w')
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            # another dedupe is running; be conservative: keep file
            lock_file.close()
            return True
    except Exception:
        lock_file = None

    result = True
    try:
        inserted = insert_file(db_dir, path, h)
        if not inserted:
            same = find_files_by_hash(db_dir, h)
            # Se ci sono altri file con lo stesso hash, scegli comportamento:
            # - Se esiste almeno un file in /autodownloader/, preferirlo e rimuovere gli altri
            # - Altrimenti rimuovere il file corrente (più recente)
            # Use Path.parts for cross-platform detection of autodownloader directory
            autodownloader_files = [os.path.abspath(s) for s in same if 'autodownloader' in Path(os.path.abspath(s)).parts]
            current_is_auto = 'autodownloader' in Path(os.path.abspath(path)).parts
            if autodownloader_files:
                for s in same:
                    full_s = os.path.abspath(s)
                    if 'autodownloader' not in Path(full_s).parts:
                        try:
                            os.remove(full_s)
                        except Exception as e:
                            print(f"Errore rimozione duplicato {full_s}: {e}")
                        finally:
                            # Ensure DB cleanup happens regardless of filesystem remove success
                            try:
                                remove_filepath(db_dir, full_s)
                            except Exception as e:
                                print(f"Errore rimozione dal DB per {full_s}: {e}")
                if not current_is_auto:
                    try:
                        os.remove(path)
                    except Exception as e:
                        print(f"Errore rimozione duplicato {path}: {e}")
                    finally:
                        try:
                            remove_filepath(db_dir, path)
                        except Exception as e:
                            print(f"Errore rimozione dal DB per {path}: {e}")
                    result = False
            else:
                try:
                    os.remove(path)
                except Exception as e:
                    print(f"Errore rimozione duplicato {path}: {e}")
                finally:
                    try:
                        remove_filepath(db_dir, path)
                    except Exception as e:
                        print(f"Errore rimozione dal DB per {path}: {e}")
                result = False
        else:
            result = True
    finally:
        try:
            if lock_file:
                import fcntl
                fcntl.flock(lock_file, fcntl.LOCK_UN)
                lock_file.close()
        except Exception:
            pass

    return result
