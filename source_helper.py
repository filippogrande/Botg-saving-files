import os
import logging

logger = logging.getLogger(__name__)

def write_source(filepath, source_url, meta=None):
    """Scrive <filepath>.source.txt con URL e (se disponibili) autore/piattaforma/post_id/data.
    Chiamare SOLO se il file è stato mantenuto (non duplicato)."""
    if not filepath or not source_url:
        return
    sidecar = filepath + ".source.txt"
    lines = [f"url: {source_url}"]
    if isinstance(meta, dict):
        if meta.get("author"):
            lines.append(f"autore: {meta['author']}")
        if meta.get("platform"):
            lines.append(f"piattaforma: {meta['platform']}")
        if meta.get("post_id"):
            lines.append(f"post_id: {meta['post_id']}")
        if meta.get("saved_at"):
            lines.append(f"salvato_il: {meta['saved_at']}")
    try:
        with open(sidecar, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        logger.debug("Sidecar scritto: %s", sidecar)
    except Exception as e:
        logger.error("Errore scrittura sidecar %s: %s", sidecar, e)