# REFERENCE — la mappa del codice

<!-- Tipo: REFERENCE. Specchia la struttura del codice, come una mappa. -->
<!-- Ogni riga: un file reale + un simbolo reale. Nessun numero di riga. -->
<!-- Aggiornata nella stessa PR che sposta qualcosa. -->

## Come si legge

Una riga per cosa ti potrebbe essere chiesto di cambiare. **Richiesta -> file -> entry point.**
Se per trovare il file ti serve altro, la riga e' sbagliata.

Nota sui file wrapper: `deduplica.py`, `find_duplicate_helper.py` e `report_helper.py`
sono wrapper sottili (re-export) verso `dedupe_core.py` e verso se stessi; i call site
importano da li', quindi la mappa punta li'. I simboli veri stanno nel modulo indicato in
"Entry point".

## Entry point e assemblaggio

| Vuoi… | File | Entry point |
|---|---|---|
| Avviare il bot Telegram (polling, handler, watcher interno) | `bot.py` | `app`, `main` |
| Wire registrare un comando o un handler su `app` | `bot.py` | `app.add_handler`, `CommandHandler` |
| Avviare il watcher Reddit una sola volta (CronJob) | `run_watcher.py` | `main` |
| Inizializzare il client Reddit async (lazy, a modulo import) | `reddit_helper.py` | `areddit` |
| Inizializzare il logging (stdout + file rotante) | `log_helper.py` | `setup_logging` |

## Comandi Telegram

| Vuoi… | File | Entry point |
|---|---|---|
| Registrare un comando testuale | `bot.py` | `CommandHandler` (es. `"start"`, `"help"`, `"numeri"`) |
| Gestire l'arrivo di foto/video/GIF da Telegram | `bot.py` | `handle_photo`, `handle_video`, `handle_animation` |
| Salvare un media Telegram in `SAVE_DIR/Telegram/` | `bot.py` | `_save_telegram` |
| Riconoscere e gestire un link Reddit | `bot.py` | `handle_reddit_link` |
| Riconoscere e gestire un link Redgifs | `bot.py` | `handle_redgifs` |
| Riconoscere e gestire un link Mega | `bot.py` | `handle_mega_link` |
| Gestire la conferma/annullamento di un download lungo | `bot.py` | `handle_confirm_callback` |
| Autorizzare o meno un utente | `bot.py` | `is_authorized`, `unauthorized_reply` |
| Comando `/numeri` (conta foto e video) | `bot.py` | `numeri_command` |
| Comando `/Watched` / `/tracked` (profili monitorati) | `bot.py` | `watched_command` |
| Comando `/trovamiduplicati` (dedup manuale) | `bot.py` | `duplicate_check_and_interaction` |
| Comando `/recalculate` (ricalcolo hash) | `bot.py` | `rehash_command` |
| Comando `/mapactor`, `/listmap`, `/editactor`, `/delactor` | `bot.py` | `mapactor_command`, `listmap_command`, `editactor_command`, `delactor_command` |
| Messaggio non riconosciuto | `bot.py` | `handle_unknown` |
| Notifica di avvio al boot | `bot.py` | `_notify_startup` |
| Avvio/stop del watcher interno | `bot.py` | `start_daily_watcher`, `stop_daily_watcher`, `_run_daily_watcher` |

## Download dalle sorgenti

| Vuoi… | File | Entry point |
|---|---|---|
| Dispatch di un link Reddit (post/profilo/immagine) | `reddit_helper.py` | `download_reddit_auto` |
| Classificare un URL Reddit senza rete | `reddit_helper.py` | `classify_reddit_url` |
| Dispatch per tipo di post Reddit | `reddit_helper.py` | `_download_submission` |
| Scaricare una galleria Reddit | `reddit_helper.py` | `download_gallery` |
| Scaricare immagine/video/GIF diretto Reddit | `reddit_helper.py` | `download_image`, `download_video`, `download_direct_gif_video` |
| Scaricare tutti i media di un profilo Reddit | `reddit_helper.py` | `download_reddit_profile_media` |
| I pattern di riconoscimento URL Reddit | `reddit_helper.py` | `PROFILE_PATTERN`, `USER_POST_PATTERN`, `POST_PATTERN`, `IMG_PATTERN` |
| Scaricare da Redgifs (auto: foto o video) | `redgifs_helper.py` | `download_redgifs_auto` |
| Scaricare un video Redgifs (yt-dlp) | `redgifs_helper.py` | `download_redgifs_video` |
| Scaricare una foto Redgifs | `redgifs_helper.py` | `download_redgifs_image_from_post` |
| Determinare se un post Redgifs e' video o foto | `redgifs_helper.py` | `redgifs_post_type` |
| Scaricare un intero profilo Redgifs | `redgifs_helper.py` | `download_redgifs_profile` |
| Eseguire il download Mega via `megadl` | `mega_helper.py` | `download_with_megatools`, `download_mega_auto` |
| Rercare il binario `megadl` nel sistema | `mega_helper.py` | `get_megadl_command` |
| Rercare un link Mega | `mega_helper.py` | `is_mega_link`, `extract_mega_info` |

## Watcher Reddit

| Vuoi… | File | Entry point |
|---|---|---|
| Eseguire una sola passata del watcher | `reddit_helper.py` | `reddit_watcher_once` |
| Loop giornaliero interno del watcher | `reddit_helper.py` | `reddit_profile_watcher_loop` |
| Aggiungere un profilo alla watchlist | `reddit_helper.py` | `add_reddit_profile_to_watch` |
| Leggere/scrivere la watchlist e il destinatario notifiche | `reddit_helper.py` | `WATCH_FILE`, `USER_FILE`, `save_notify_user`, `get_notify_user` |
| Gestire i file di stato del watcher | `reddit_watch.json`, `reddit_notify_user.txt` in `SAVE_DIR` | — |

## Deduplicazione

| Vuoi… | File | Entry point |
|---|---|---|
| Deduplicare un file appena scaricato | `deduplica.py` | `deduplica_file` (wrapper) -> `dedupe_core.py` |
| Implementazione reale della dedup per singolo file | `dedupe_core.py` | `deduplica_file` |
| Regola su quale copia tenere | `dedupe_core.py` | `_keep_priority`, `_is_auto` |
| Calcolare l'hash MD5 di un file | `dedupe_core.py` | `file_hash` |
| Estensioni considerate media | `dedupe_core.py` | `VALID_EXTS` |
| Lock tra processi (bot + CronJob) | `dedupe_core.py` | `_with_lock`, `.dedupe.lock` |
| Sweep completo e rimozione duplicati | `dedupe_core.py` | `scan_and_clean` |
| Interfaccia dello sweep (es. da CLI) | `find_duplicate_helper.py` | `find_duplicates` (wrapper) -> `dedupe_core.py` |
| Ricalcolare tutti gli hash e aggiornare il DB | `find_duplicate_helper.py` | `rehash_files` (wrapper) -> `dedupe_core.py` |
| Logica reale dello sweep / del rehash | `dedupe_core.py` | `scan_and_clean`, `rehash_files` |

## Database SQLite

| Vuoi… | File | Entry point |
|---|---|---|
| Creare/migrare lo schema | `db_helper.py` | `ensure_db` |
| Percorso del DB | `db_helper.py` | `DB_FILENAME`, `get_db_path` |
| Inserire un file | `db_helper.py` | `insert_file` |
| Cercare file con lo stesso hash | `db_helper.py` | `find_files_by_hash` |
| Leggi una entry per filepath | `db_helper.py` | `get_file_entry` |
| Aggiornare l'hash di un file | `db_helper.py` | `update_file_hash` |
| Rimuovere una entry | `db_helper.py` | `remove_filepath` |
| Contare foto e video (per `/numeri`) | `db_helper.py` | `count_media_by_type` |

## Salvataggio e path

| Vuoi… | File | Entry point |
|---|---|---|
| Costruire il path di salvataggio (`autodownloader/...`) | `salvataggio.py` | `build_path` |
| Normalizzare nomi di file/cartelle | `salvataggio.py` | `safe_name` |
| Scrivere il sidecar `.source.txt` | `source_helper.py` | `write_source` |
| File che ha prodotto un download | `<file>.source.txt` accanto al media | — |
| Logica del path nella dedup (cosa e' "autodownloader") | `dedupe_core.py` | `_is_auto` |

## Attore (mappatura username -> nome)

| Vuoi… | File | Entry point |
|---|---|---|
| Risolvere uno username in un nome attore | `actor_map.py` | `resolve_actor` |
| Dire se uno username e' gia' mappato | `actor_map.py` | `is_mapped` |
| Aggiungere/unire una mappatura | `actor_map.py` | `add_actor_mapping` |
| Modificare una mappatura | `actor_map.py` | `update_actor_mapping` |
| Rimuovere una mappatura | `actor_map.py` | `remove_actor_mapping` |
| Elencare le mappature | `actor_map.py` | `list_actor_mappings`, `load_actor_map`, `save_actor_map` |
| Dove vivono le mappature | `actor_map.json` in `SAVE_DIR` | — |
| Report attore nei messaggi post-download | `actor_report.py` | `format_actor_report_from_paths`, `_actor_from_path` |

## Report e messaggi

| Vuoi… | File | Entry point |
|---|---|---|
| Formato del messaggio di riepilogo post-download | `report_helper.py` | `format_download_report` |
| Invio del riepilogo dopo un download | `bot.py` | `post_download_report` |
| Testo del comando `/help` | `bot.py` | `help_command` |

## Configurazione

| Vuoi… | File | Entry point |
|---|---|---|
| Valori di default delle variabili d'ambiente | `.env.example` | — |
| Variabili d'ambiente lette dal codice | `bot.py` (blocchi `os.environ.get`) | `SAVE_DIR`, `ALLOWED_CHAT_IDS`, `WATCHER_ENABLED`, `STARTUP_NOTIFY`, `STARTUP_CHAT_ID`, `TELEGRAM_TOKEN` |
| Credenziali Reddit | `reddit_helper.py` | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT` |

## Deploy e container

| Vuoi… | File | Entry point |
|---|---|---|
| Immagine Docker | `Dockerfile` | `CMD ["python", "bot.py"]` |
| Servizi Docker Compose | `docker-compose.yml` | `botg`, `watcher` |
| Deploy Kubernetes | `k8s/bot-deployment.yaml` | `kind: Deployment` |
| CronJob del watcher | `k8s/watcher-cronjob.yaml` | `kind: CronJob` |
| Installazione megatools sul server | `install_megatools.sh`, `install_megadown.sh` | — |
| Publicazione immagine (CI) | `.github/workflows/docker-publish.yml` | `IMAGE_NAME` |
| Aggiornamento dipendenze (CI) | `.github/dependabot.yml` | `package-ecosystem` |

## Test

| Vuoi… | File |
|---|---|
| Un test | nessuno: il repo non contiene test |

## Limiti noti

<!-- Dove la mappa e' sottile di proposito: un file che contiene piu' di una responsabilita'. -->
<!-- Ogni voce e' uno split pianificato, non una scusa. -->

- `bot.py` (~31 KB, oltre il limite di 500 righe): handler Telegram + assemblaggio + report
  + gestione watcher in un unico file. Va diviso per handler (Telegram / link / attore / dedup),
  non qui: questa PR e' solo documentazione.
- `reddit_helper.py` (~17 KB, oltre il limite di 500 righe): download per tipo di post +
  watcher + watchlist. Da separare in "download" e "watcher".
- `db_helper.py`: la funzione `count_media_by_type` e' definita **prima** degli `import`
  (`os`, `sqlite3`) che usa: funziona perche' le chiamate sono a runtime, ma va spostata
  sotto gli import.
- `mega_helper.py` e `redgifs_helper.py`: ogni errore e' traghettato in un `print` dentro
  un `except Exception` (fallback silenzioso). Da sostituire con `logger.error`.
- `bot.py`: molte chiamate Telegram sono avvolte in `try/except Exception` con risposta
  generica all'utente: errore reale invisibile.
- `requirements.txt`: `pytest` e' una dipendenza di sviluppo messa tra le dipendenze
  runtime.
- `deduplica.py`, `find_duplicate_helper.py`: wrapper di re-export verso `dedupe_core.py`.
  Sono mantenuti perche' i call site (e la documentazione esistente) li importano.
- `install_megatools.sh` e `install_megadown.sh`: identici (stesso contenuto, 2165 byte).
  Duplicato da collassare.
- `.DS_Store` presente in root e in `.github/`: artefatto macOS, assente dal `.gitignore`.
- `Dockerfile`: nessun `megatools`/`megadl`, quindi il download Mega non funziona nel
  container cosi' com'e'. Gli script di installazione sono pensati per il host.
