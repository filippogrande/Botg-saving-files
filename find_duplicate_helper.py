import os
import hashlib
import json

HASH_FILE = "hashes.json"


def load_hashes(directory):
    path = os.path.join(directory, HASH_FILE)
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_hashes(directory, hashes):
    path = os.path.join(directory, HASH_FILE)
    try:
        with open(path, "w") as f:
            json.dump(hashes, f)
    except Exception as e:
        print(f"Errore salvataggio hashes: {e}")

def file_hash(path):
    try:
        with open(path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception as e:
        print(f"Errore calcolo hash per {path}: {e}")
        return None

def find_duplicates(directory):
    """
    Cerca file duplicati (stesso hash) nella directory, elimina i duplicati e aggiorna hashes.json.
    Restituisce il numero di duplicati rimossi.
    """
    hashes = load_hashes(directory)  # {filename: hash}
    hash_to_file = {}
    removed = 0
    files = [f for f in os.listdir(directory) if f.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".mov"))]
    for fname in files:
        path = os.path.join(directory, fname)
        try:
            # Se già in hashes, riusa hash
            if fname in hashes:
                h = hashes[fname]
            else:
                h = file_hash(path)
                if h:
                    hashes[fname] = h
            if not h:
                continue
            # Se già presente un file con stesso hash (ma nome diverso), elimina il duplicato
            if h in hash_to_file:
                os.remove(path)
                removed += 1
                if fname in hashes:
                    del hashes[fname]
            else:
                hash_to_file[h] = fname
        except Exception as e:
            print(f"Errore su {fname}: {e}")
    # Rimuovi dal dizionario hash i file che non esistono più
    for fname in list(hashes.keys()):
        if fname not in files:
            del hashes[fname]
    try:
        save_hashes(directory, hashes)
    except Exception as e:
        print(f"Errore salvataggio hashes finale: {e}")
    return removed
