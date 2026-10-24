# Botg-saving-files

Bot Telegram che salva automaticamente media da Telegram, Reddit, Redgifs e Mega, con
deduplicazione MD5 (SQLite) e gestione dello storage su filesystem locale o mount di rete.
Eseguibile in Docker, Docker Compose o Kubernetes, con watcher Reddit schedulabile
(interno o via CronJob).

## Avvio rapido

```bash
cp .env.example .env       # compila TELEGRAM_TOKEN e le altre variabili
docker compose up -d --build
```

Oppure in locale: `pip install -r requirements.txt && python bot.py`.

Vedi `docs/OPERATIONS.md` per i dettagli (variabili, watcher, deploy, megatools).

## Indice

| Vuoi… | Apri |
|---|---|
| Trovare una funzione, un comando, un simbolo | [`docs/REFERENCE.md`](docs/REFERENCE.md) |
| Capire come funziona (flussi, dedup, forward) | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| Conoscere le regole prima di scrivere codice | [`docs/CONVENTIONS.md`](docs/CONVENTIONS.md) |
| Installare, avviare, schedulare | [`docs/OPERATIONS.md`](docs/OPERATIONS.md) |
| Risolvere un errore | [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) |

## Struttura

- **`bot.py`** — entry point: bot Telegram (handler, comandi) e watcher interno opzionale.
- **`reddit_helper.py`** — download da Reddit (post, gallerie, video, profili) + watcher.
- **`redgifs_helper.py`** — download da Redgifs (foto/video/profili) via `yt-dlp`.
- **`mega_helper.py`** — download da Mega via `megadl`.
- **`dedupe_core.py`** — deduplicazione MD5 e sweep; `deduplica.py` e
  `find_duplicate_helper.py` sono i wrapper usati dai call site.
- **`db_helper.py`** — schema e query del DB SQLite (`bot.db` in `SAVE_DIR`).
- **`salvataggio.py`**, **`source_helper.py`**, **`actor_map.py`**, **`actor_report.py`**,
  **`report_helper.py`**, **`log_helper.py`** — path normalizzati, sidecar `.source.txt`,
  mappatura attore, report e logging.
- **`k8s/`**, **`Dockerfile`**, **`docker-compose.yml`**, **`.github/`** — deploy e CI.

La mappa completa richiesta -> file -> entry point e' in
[`docs/REFERENCE.md`](docs/REFERENCE.md).
