# ARCHITECTURE — come funziona

<!-- Tipo: EXPLANATION. Come funziona e perche'. I fatti "dove" sono in docs/REFERENCE.md. -->

## Panoramica

Un solo processo (`bot.py`) gestisce il bot Telegram e, opzionalmente, un watcher Reddit
interno. I download arrivano da tre vie:

1. **Telegram**: l'utente inoltra o invia media e link. Il bot li riconosce, li scarica, li
   deduplica e risponde con un riepilogo.
2. **Reddit**: un link diretto, oppure il watcher giornaliero che scorre i profili in
   `reddit_watch.json` e scarica i post successivi all'ultimo visto.
3. **Redgifs / Mega**: link riconosciuti dai filtri Telegram e scaricati con `yt-dlp` o
   `megadl`.

Il salvataggio e' sempre sul filesystem, sotto `SAVE_DIR`; la deduplicazione vive in
un SQLite (`bot.db`) nella stessa directory, cosi' bot e CronJob condividono lo stato.

## Flusso di download

```
Telegram update
  -> handler in bot.py (foto/video/GIF o testo con link)
  -> helper di sorgente (reddit_helper / redgifs_helper / mega_helper)
       oppure _save_telegram per i media inoltrati
  -> scaricato su disco
  -> deduplica_file(path, SAVE_DIR)        <- dedupe_core.py
  -> se tenuto: write_source(path, ...)    <- source_helper.py (sidecar .source.txt)
  -> post_download_report(...)             <- report_helper.py + actor_report.py
```

Ogni helper di sorgente segue lo stesso contratto: restituisce la **lista dei path tenuti**
(i duplicati sono gia' stati rimossi) oppure una stringa di stato/errore.
`bot.py` non fa deduplicazione per suo conto: la delega a `deduplica_file`.

### Perche' i path di salvataggio sono tutti in `autodownloader/`

`salvataggio.build_path` impone `<SAVE_DIR>/autodownloader/<sorgente>/<attore>/<id>/<filename>`.
La regola esiste perche' la deduplicazione deve poter decidere "quale copia tenere"
in modo deterministico, e la posizione e' il segnale: un file dentro `autodownloader/`
viene preferito a uno fuori (vedi sotto). I nomi passano da `safe_name`, che mantiene
spazi singoli (es. `Aspen Green`) per compatibilita' con Stash.

### Mappatura attore

Gli username di Reddit/Redgifs vengono risolti in un nome "attore" tramite `actor_map`
(e `actor_map.json` in `SAVE_DIR`). Se lo username non e' mappato, la sorgente finisce
nella cartella `Reddit`/`Redgifs`; se lo e', in `attore/<Nome>`. Questo vale sia per
Reddit (`_source_segment`) sia per Redgifs (`seg2`).

## Deduplicazione (MD5)

Due livelli, entrambi in `dedupe_core.py`:

**1. Per singolo file** — `deduplica_file(path, db_dir)`:

1. calcola l'MD5 (`file_hash`, chunk da 64 KB);
2. cerca nel DB altri filepath con lo stesso hash (`find_files_by_hash`);
3. nessun altro: inserisce e tiene il file;
4. altri presenti: decide chi tenere con `_keep_priority` e rimuove gli altri da disco e dal DB.

**2. Sweep completo** — `scan_and_clean(root)`, esposto come `find_duplicates`:

- ricostruisce la mappa `hash -> path` camminando i media (`_iter_media`, estensioni in
  `VALID_EXTS`), e a ogni collisione applica la stessa `_keep_priority`.
- `rehash_files` ricalcola tutti gli hash e aggiorna il DB (usato da `/recalculate`).

### Regola su chi tenere (`_keep_priority`)

- se solo uno dei due e' dentro `autodownloader/` (`_is_auto`), **vince quello dentro**,
  anche se piu' vecchio;
- altrimenti vince il piu' recente per `mtime`.

E' la regola che rende stabile il comportamento del bot: i file appena scaricati non
vengono mai fatti sparire da uno sweep che trova una copia piu' vecchia fuori da
`autodownloader/`.

### Concorrenza

`_with_lock` prende un lock `fcntl.flock(LOCK_EX | LOCK_NB)` su `.dedupe.lock` nella
directory del DB. Se un'altra istanza gia' detiene il lock, l'operazione ritorna subito
(`None` -> `deduplica_file` ritorna `True`, lo sweep ritorna `0`): nessuna dedup
concorrente sullo stesso DB. E' cio' che permette a bot e CronJob di convivere.

## Forward e riepilogo

Non c'e' "forward" automatico di file verso un'altra chat: il bot **salva e risponde**.
Dopo ogni download `post_download_report` invia due messaggi:

- il riepilogo numerico (`format_download_report`: file scaricati / duplicati rimossi);
- se i path contengono un attore risolvibile, la riga `attore: <nome>`
  (`format_actor_report_from_paths`), oppure `attore: sconosciuto (<cartella>)`.

I download lunghi (profili Reddit/Redgifs) sono preceduti da una conferma
(`pending_download` + `handle_confirm_callback`) per non bloccare l'utente.

## Watcher Reddit

Due modalita', la stessa logica (`reddit_watcher_once`):

- **interna**: `WATCHER_ENABLED=true` avvia `_run_daily_watcher` (loop ogni 24 h) dentro
  `bot.py`;
- **esterna** (consigliata per container): `k8s/watcher-cronjob.yaml` oppure
  `docker compose run --rm watcher`, che eseguono `run_watcher.py` una volta sola.

`run_watcher.py` inizializza il bot Telegram **solo se** esiste
`reddit_notify_user.txt` in `SAVE_DIR` (e invia li' le notifiche). Il watcher aggiorna
`reddit_watch.json` con `last_id` per profilo e riscrive il file a fine passata.

## Perche' i lazy import

Le librerie pesanti (`yt-dlp`, `requests`, `asyncpraw`) sono importate dentro le funzioni
che le usano, non a top-level: il bot resta leggero a idle quando non scarica. Il
controvalore e' che un import rotto si scopre solo a runtime; `bot.py` lo gestisce per
Mega con un `try/except ImportError` che rende `MEGA_AVAILABLE = False`.

## Sicurezza

- `is_authorized` controlla `ALLOWED_CHAT_IDS`: se la variabile e' vuota, **tutti** sono
  autorizzati. In produzione impostarla.
- Il token e le credenziali vivono in `.env` / `environment:` in Compose, mai in un doc.
- `safe_name` e' il confine contro path traversal da nomi di cartella remoti.
- `deduplica_file` e lo sweep rimuovono file **reali** da disco: la regola su chi tenere
  va capita prima di toccare `_keep_priority`.
