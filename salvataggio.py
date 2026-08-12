import os
import re
from typing import Optional

def safe_name(name: str, max_length: int = 128) -> str:
    """
    Normalizza un nome per file o cartella rendendolo sicuro e portabile.
    Rimuove caratteri non validi, collassa spazi/underscore multipli, taglia la lunghezza.
    Gli spazi SINGOLI vengono mantenuti (es. 'Aspen Green') per compatibilità con Stash.
    """
    name = name.strip()
    name = re.sub(r"[\\/:*?\"<>|]", "_", name)  # caratteri illegali filesystem
    name = re.sub(r"\s+", " ", name)             # spazi multipli -> singolo spazio (mantenuto)
    name = re.sub(r"_+", "_", name)              # underscore multipli -> singolo
    name = name[:max_length]
    if not name:
        name = "unnamed"
    return name

def build_path(base_dir: str, source: str, user: Optional[str], media_id: str, filename: str) -> str:
    """
    Costruisce un path normalizzato e portabile per il salvataggio dei file.
    Tutti i file vanno in /autodownloader/... rispetto alla base.
    Esempio: /mnt/truenas-bot/autodownloader/attore/Aspen Green/12345/nomefile.jpg
    """
    parts = [base_dir, "autodownloader", safe_name(source)]
    if user:
        parts.append(safe_name(user))
    parts.append(safe_name(media_id))
    parts.append(safe_name(filename))
    return os.path.join(*parts)