def count_media_by_type(directory):
    """
    Restituisce un dizionario con il conteggio di foto e video nel db.
    """
    # Ensure DB and tables exist before opening a connection to avoid sqlite3.OperationalError
    ensure_db(directory)
    path = get_db_path(directory)
    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        # Estensioni immagini e video
        foto_ext = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
        video_ext = ('.mp4', '.mov')
        cur.execute("SELECT filename FROM files")
        foto = 0
        video = 0
        for (fname,) in cur.fetchall():
            low = fname.lower()
            if low.endswith(foto_ext):
                foto += 1
            elif low.endswith(video_ext):
                video += 1
        return {"foto": foto, "video": video}
    finally:
        conn.close()
import os
import sqlite3
from datetime import datetime

DB_FILENAME = "bot.db"

def get_db_path(directory):
    return os.path.join(directory, DB_FILENAME)

def ensure_db(directory):
    path = get_db_path(directory)
    os.makedirs(directory, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        # Nuova struttura: filepath unico, filename non unico
        cur.execute("""
        CREATE TABLE IF NOT EXISTS files(
            id INTEGER PRIMARY KEY,
            filename TEXT,
            filepath TEXT UNIQUE,
            hash TEXT,
            added_at TEXT
        )
        """)
        # Migrazione: aggiungi colonna filepath se manca
        cur.execute("PRAGMA table_info(files)")
        columns = [row[1] for row in cur.fetchall()]
        if "filepath" not in columns:
            cur.execute("ALTER TABLE files ADD COLUMN filepath TEXT")
            conn.commit()
            # After adding the column, ensure there are no duplicate filepath values
            # before creating a UNIQUE index. If duplicates exist, surface them and
            # skip creating the unique index to avoid IntegrityError.
            try:
                cur.execute("""
                SELECT filepath, COUNT(*) as c FROM files
                WHERE filepath IS NOT NULL
                GROUP BY filepath HAVING c>1
                """)
                dups = cur.fetchall()
                if dups:
                    print(f"Attenzione: trovati {len(dups)} filepath duplicati. Alcuni esempi:")
                    for r in dups[:10]:
                        print(r)
                    # Do not attempt to create unique index to avoid failure; user must
                    # resolve duplicates manually or via a migration script.
                else:
                    try:
                        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_files_filepath_unique ON files(filepath)")
                        conn.commit()
                    except Exception:
                        # If index creation fails for any reason, ignore and continue
                        pass
            except Exception:
                # If the duplicate-check query fails for any reason, skip unique index creation
                pass
        # Abilita WAL per migliori prestazioni concorrenti
        try:
            cur.execute("PRAGMA journal_mode=WAL")
        except Exception:
            pass
        # Crea indice su hash per ricerche più veloci
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_files_hash ON files(hash)")
        except Exception:
            pass
    finally:
        conn.close()

def insert_file(directory, filepath, h):
    """
    Inserisce il file nel db usando il percorso relativo dalla root directory.
    """
    path = get_db_path(directory)
    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        filename = os.path.basename(filepath)
        try:
            cur.execute("INSERT INTO files(filename, filepath, hash, added_at) VALUES (?, ?, ?, ?)",
                        (filename, filepath, h, datetime.utcnow().isoformat()))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # filepath already exists
            return False
    finally:
        conn.close()

def find_files_by_hash(directory, h):
    path = get_db_path(directory)
    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT filepath FROM files WHERE hash = ?", (h,))
        return [r[0] for r in cur.fetchall()]
    finally:
        conn.close()

def remove_filepath(directory, filepath):
    path = get_db_path(directory)
    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM files WHERE filepath = ?", (filepath,))
        conn.commit()
    finally:
        conn.close()
