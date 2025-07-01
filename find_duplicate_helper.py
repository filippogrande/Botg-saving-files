import os
import hashlib
import shutil

def find_and_move_duplicates(directory, duplicate_dir="duplicati"):
    """
    Cerca file duplicati (stesso hash) nella directory e sposta i duplicati trovati in una sottocartella.
    Il file "originale" resta nella cartella principale, i successivi vengono spostati e rinominati.
    """
    os.makedirs(os.path.join(directory, duplicate_dir), exist_ok=True)
    hashes = {}
    for fname in os.listdir(directory):
        if fname.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".mov")):
            path = os.path.join(directory, fname)
            try:
                with open(path, 'rb') as f:
                    filehash = hashlib.md5(f.read()).hexdigest()
                if filehash in hashes:
                    # File duplicato trovato, sposta in duplicati/ con nome unico
                    base, ext = os.path.splitext(fname)
                    new_name = f"dup_{base}_{filehash[:6]}{ext}"
                    dest = os.path.join(directory, duplicate_dir, new_name)
                    shutil.move(path, dest)
                    print(f"Spostato duplicato: {fname} -> {dest}")
                    # Per eliminazione automatica futura:
                    # os.remove(dest)
                else:
                    hashes[filehash] = path
            except Exception as e:
                print(f"Errore su {fname}: {e}")
    # Restituisce la lista dei duplicati spostati (opzionale)
    return

def find_duplicates(directory):
    """
    Cerca file duplicati (stesso hash) nella directory e restituisce una lista di tuple (originale, duplicato).
    Non sposta né elimina nulla: la logica di gestione viene demandata al chiamante (es. bot Telegram).
    """
    hashes = {}
    duplicates = []
    for fname in os.listdir(directory):
        if fname.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".mov")):
            path = os.path.join(directory, fname)
            try:
                with open(path, 'rb') as f:
                    filehash = hashlib.md5(f.read()).hexdigest()
                if filehash in hashes:
                    # Trovato duplicato: salva la coppia (originale, duplicato)
                    duplicates.append((hashes[filehash], path))
                else:
                    hashes[filehash] = path
            except Exception as e:
                print(f"Errore su {fname}: {e}")
    return duplicates
