# OPERATIONS — comandi, installazione, avvio

<!-- Tipo: HOW-TO. Passi per un obiettivo concreto. -->

## Prerequisiti

- Python 3.11+
- `TELEGRAM_TOKEN` (bot creato con @BotFather)
- Per i download Mega: `megadl` (megatools) installato **sull'host** o nel container
- Per i download Reddit: `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` (opzionali, per
  profili e watcher); i singoli link post funzionano anche senza

## Variabili d'ambiente

Valori di default in `.env.example`. Il codice legge queste variabili con `os.environ.get`.

| Variabile | Default | A cosa serve |
|---|---|---|
| `TELEGRAM_TOKEN` | — (obbligatoria) | token del bot; se manca `bot.py` solleva `RuntimeError` |
| `SAVE_DIR` | `/mnt/truenas-bot` | radice di salvataggio (i media finiscono in `SAVE_DIR/autodownloader/...`) |
| `ALLOWED_CHAT_IDS` | vuota = tutti autorizzati | lista di user id Telegram autorizzati, separati da virgola |
| `WATCHER_ENABLED` | `false` | se vero, avvia il watcher interno (loop 24 h) |
| `STARTUP_NOTIFY` | `false` | se vero, invia la notifica di avvio |
| `STARTUP_CHAT_ID` | vuota | chat id che riceve la notifica di avvio |
| `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` | vuoti | credenziali Reddit (profili e watcher) |
| `REDDIT_USER_AGENT` | `telegram-bot-reddit` | user agent per Reddit |

I valori accettati per i booleani sono `1`/`true`/`yes` (case-insensitive).

## Avvio in locale

```bash
pip install -r requirements.txt
cp .env.example .env      # poi compila i valori reali
python bot.py
```

`bot.py` chiude in errore se `TELEGRAM_TOKEN` manca: e' voluto, non un bug.

## Avvio con Docker Compose

`docker-compose.yml` porta gia' tutte le variabili: non serve un `.env`.

1. Apri `docker-compose.yml` e sostituisci `REPLACE_WITH_YOUR_TELEGRAM_TOKEN`.
2. Scegli l'immagine: il file usa `filippogrande/botg-saving-files:latest` (pubblicata da CI).
   Per buildare in locale, cambia `image:` in `build: .`.
3. Compila le credenziali Reddit solo se usi profili/watcher.

```bash
docker compose up -d --build
docker compose logs -f botg
```

Servizi:

- `botg` — costruisce dal `Dockerfile` e avvia `python bot.py` (polling).
- `watcher` — esegue **una** volta `python run_watcher.py` e termina
  (`restart: "no"`).

Il volume `./salvataggi:/mnt/truenas-bot` monta la cartella `salvataggi` in root come
storage persistente. Cambia il path host a piacere, lasciando invariato quello del
container se non cambi `SAVE_DIR`.

Comandi utili:

```bash
# Watcher manuale senza avviare il servizio watcher
docker compose run --rm watcher

# Deduplica manuale
docker exec -it botg python -c 'from find_duplicate_helper import find_duplicates; print(find_duplicates("/mnt/truenas-bot"))'

# Ricalcolo hash
docker exec -it botg python -c 'from find_duplicate_helper import rehash_files; print(rehash_files("/mnt/truenas-bot"))'

# Stop
docker compose down
```

## Schedulare il watcher

Due strade, la logica e' la stessa:

- **Esterna (consigliata)**: CronJob Kubernetes (`k8s/watcher-cronjob.yaml`, ore 02:00) o
  `docker compose run --rm watcher` da crontab host.
- **Interna**: `WATCHER_ENABLED=true` in Compose/`.env`.

L'esterna e' piu' leggera: il bot non tiene un loop in memoria.

## Mega: installare megatools

`megadl` **non** e' nel `Dockerfile`. Per far funzionare Mega:

- **sull'host**: `bash install_megatools.sh` (prova apt, poi snap, poi compilazione);
- **nel container**: aggiungi l'installazione di `megatools` al `Dockerfile`, oppure usa un
  servizio separato che esegue `megadl` sull'host.

Senza `megadl`, `download_mega_auto` ritorna una lista vuota e il bot risponde
"Nessun file scaricabile trovato".

## Comandi del bot

| Comando | Effetto |
|---|---|
| `/start`, `/hello`, `/help` | messaggi di base e help |
| `/numeri` | conta foto e video presenti nel DB |
| `/trovamiduplicati` | sweep con conferma: rimuove i duplicati |
| `/recalculate` | ricalcola gli hash e aggiorna il DB |
| `/mapactor <nome> [reddit:user] [redgifs:user]` | crea/unisce una mappatura attore |
| `/listmap` | elenca le mappature con indice |
| `/editactor <num> [actor:Nome] [reddit:user] [redgifs:user]` | modifica una mappatura |
| `/delactor <num>` | rimuove una mappatura |
| `/Watched`, `/tracked` | profili Reddit monitorati + destinatario notifiche |

Inviare un media (foto/video/GIF) lo salva in `SAVE_DIR/Telegram/`. Inviare un link
Reddit/Redgifs/Mega avvia il download; per i profili chiede conferma.

## Aggiornare le dipendenze

Dependabot apre PR settimanali (`.github/dependabot.yml`): `pip` su `requirements.txt`,
`docker` sul `Dockerfile` e su `docker-compose.yml`, `github-actions` sulle workflow.
Revisiona e mergi le PR di dipendenze, poi rebuilda l'immagine.

## Deploy

### Docker (CI)

`.github/workflows/docker-publish.yml` costruisce e pubblica
`filippogrande/botg-saving-files` su `linux/amd64` e `linux/arm64` a ogni push su `main`
(piu' `workflow_dispatch`). Il tag e' `latest` (o il tag git se il push e' un tag,
altrimenti `sha-<short>`); su rami non-`main` il tag e' `alpha-<branch>-sha-<short>`.

### Kubernetes

Due manifesti, immagine `yourregistry/botg-saving-files:latest` (da aggiornare al tuo
registry):

- `k8s/bot-deployment.yaml` — `Deployment` con replica 1, env `SAVE_DIR`, volume
  `/mnt/truenas-bot` da PVC `save-dir-pvc`;
- `k8s/watcher-cronjob.yaml` — `CronJob` `0 2 * * *` che esegue `python run_watcher.py`,
  stesso volume.

Entrambi riferiscono la PVC `save-dir-pvc`: va creata a parte (non e' nel repo). Non
sono previsti healthcheck/readiness probe.

### Container: comandi rapidi

```bash
docker stats botg --no-stream     # RAM/CPU
docker logs -f botg               # log in streaming
```

## Note di sicurezza

- **Mai** committare `.env` o il token reale: usa il segnaposto e `env_file`/Docker
  secrets.
- Se `ALLOWED_CHAT_IDS` resta vuota, chiunque scriva al bot e' autorizzato: impostala in
  produzione.
- Proteggi `SAVE_DIR`: contiene media scaricati e il DB.

## Miglioramenti pianificati

Dal vecchio README, non ancora implementati:

- **Download offline**: gestire i messaggi arrivati mentre il server era spento. Non e'
  implementato.
- **Logging strutturato e metriche Prometheus**: oggi il logging e' testuale (stdout +
  `botg.log`) e molte errori finiscono in `print`, non nel log.
- **Healthcheck / readiness probe** per Kubernetes (vedi `docs/REFERENCE.md#limiti-noti`).
- **Refactor di `reddit_helper.py`**: lazy init/close del client Reddit in tutte le
  funzioni (vedi `docs/REFERENCE.md#limiti-noti`).
