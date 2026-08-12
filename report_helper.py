def format_download_report(label, scaricati, duplicati):
    """Ritorna il messaggio di riepilogo post-download."""
    return (
        f"✅ {label} completato\n"
        f"📥 File scaricati: {scaricati}\n"
        f"🗑️ Duplicati rimossi: {duplicati}"
    )