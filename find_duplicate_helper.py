import os
import hashlib
import shutil

def find_duplicates(directory):
    """
    Cerca file duplicati (stesso hash) nella directory, elimina i duplicati e restituisce il numero di duplicati rimossi.
    """
    hashes = {}
    removed = 0
    for fname in os.listdir(directory):
        if fname.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".mov")):
            path = os.path.join(directory, fname)
            try:
                with open(path, 'rb') as f:
                    filehash = hashlib.md5(f.read()).hexdigest()
                if filehash in hashes:
                    os.remove(path)
                    removed += 1
                else:
                    hashes[filehash] = path
            except Exception as e:
                print(f"Errore su {fname}: {e}")
    return removed
