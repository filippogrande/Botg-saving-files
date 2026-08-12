import os

def write_source(filepath, source_url):
    """Scrive <filepath>.source.txt contenente l'URL originale.
    Chiamare SOLO se il file è stato mantenuto (non duplicato)."""
    if not filepath or not source_url:
        return
    sidecar = filepath + ".source.txt"
    try:
        with open(sidecar, "w", encoding="utf-8") as f:
            f.write(str(source_url))
    except Exception as e:
        print(f"Errore scrittura sidecar sorgente {sidecar}: {e}")