# AGENTS.md — Botg-saving-files

<!-- Radice della mappa. Leggi questo file prima, ogni volta. Max ~150 righe. -->
<!-- Tutto cio' che non serve per OGNI task vive a un link di distanza. -->

## Cos'e'

Bot Telegram che scarica media (Telegram, Reddit, Redgifs, Mega), li salva in `SAVE_DIR`
sotto `autodownloader/<sorgente>/<attore>/<id>/`, li deduplica per hash MD5 con un
DB SQLite e fa forward di quanto scaricato. Watcher Reddit schedulabile (interno o CronJob).

- Stack: Python 3.11, `python-telegram-bot`, `asyncpraw`, `yt-dlp`, `requests`, `aiosqlite`, SQLite.
- Deploy: Docker (image `filippogrande/botg-saving-files`), Kubernetes (`k8s/`), Compose in root.
- Storage: `SAVE_DIR` (default `/mnt/truenas-bot`) + `bot.db` SQLite nella stessa directory.

## Comandi

<!-- Solo quelli non ovvi. Uno strumento non nominato qui non viene usato. -->

| Azione | Comando |
|---|---|
| Avvio in locale | `python bot.py` (richiede `TELEGRAM_TOKEN`) |
| Build + avvio | `docker compose up -d --build` |
| Log del bot | `docker compose logs -f botg` |
| Watcher una sola run | `docker compose run --rm watcher` |
| Deduplica manuale | `docker exec -it botg python -c 'from find_duplicate_helper import find_duplicates; print(find_duplicates("/mnt/truenas-bot"))'` |
| Ricalcolo hash | `docker exec -it botg python -c 'from find_duplicate_helper import rehash_files; print(rehash_files("/mnt/truenas-bot"))'` |
| Dipendenze | `pip install -r requirements.txt` |

## Indice — richiesta -> dove

<!-- LA MAPPA. Una riga per richiesta, non per area. Nessun numero di riga. Nessun elenco di directory. -->

| Vuoi… | Apri |
|---|---|
| Sapere come funziona / perche' una scelta e' stata fatta | `docs/ARCHITECTURE.md` |
| Conoscere le regole del codice prima di scriverne | `docs/CONVENTIONS.md` |
| Trovare una funzione o un comando del bot | `docs/REFERENCE.md` |
| Installare, avviare, schedulare il watcher | `docs/OPERATIONS.md` |
| Capire un errore o un sintomo noto | `docs/TROUBLESHOOTING.md` |
| Sapere quali variabili d'ambiente esistono | `docs/OPERATIONS.md#variabili-dambiente` |
| Cambiare il path di salvataggio | `docs/REFERENCE.md#salvataggio-e-path` |
| Cambiare la regola di deduplicazione | `docs/REFERENCE.md#deduplicazione` |
| Cambiare i comandi Telegram | `docs/REFERENCE.md#comandi-telegram` |
| Cambiare i manifesti di deploy | `docs/OPERATIONS.md#deploy` |
| Aumentare il limite di righe di un file | `docs/REFERENCE.md#limiti-noti` |

## Documenti

| Doc | Tipo | Stato | A cosa serve |
|---|---|---|---|
| `docs/REFERENCE.md` | reference | ACTIVE 2026-10-24 | la mappa: richiesta -> file -> entry point |
| `docs/ARCHITECTURE.md` | explanation | ACTIVE 2026-10-24 | flussi di download, dedup MD5, forward, scelte |
| `docs/CONVENTIONS.md` | how-to | ACTIVE 2026-10-24 | regole di codice e di repo |
| `docs/OPERATIONS.md` | how-to | ACTIVE 2026-10-24 | comandi, installazione, variabili, deploy |
| `docs/TROUBLESHOOTING.md` | how-to | ACTIVE 2026-10-24 | sintomi noti e cause |

## Regole

- Branch + PR, mai push su `main`.
- I doc (indice incluso) si aggiornano nella **stessa PR** che li invalida.
- Limiti: 500 righe/file, 50 righe/funzione, niente fallback silenziosi, niente file usa-e-getta.
- Una PR tocca un concetto, non piu'. Commit conventional (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`, `deps:`).
- Onesta' della mappa: una riga che nomina un path o un simbolo sbagliato si corregge subito, non si annota.
