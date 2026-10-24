# TROUBLESHOOTING — sintomi noti e cause

<!-- Tipo: HOW-TO. Sintomo -> causa probabile -> dove guardare. -->

## Il bot non parte

| Sintomo | Causa probabile | Dove guardare |
|---|---|---|
| `RuntimeError: TELEGRAM_TOKEN non impostato` | variabile mancante | `bot.py` (check finale prima di `ApplicationBuilder`) |
| Container parte e muore subito | stesso errore nei log | `docker compose logs botg` |
| `docker-compose` usa un'immagine vecchia | Compose punta a `filippogrande/...:latest`, non builda | `docker-compose.yml`: cambia in `build: .` |

## "Utente non autorizzato"

`is_authorized` controlla `ALLOWED_CHAT_IDS`. Se la variabile e' vuota **tutti** passano;
se e' valorizzata, serve che il tuo user id sia in lista (numerici, separati da virgola).
Guarda `bot.py` -> `is_authorized`.

## Mega: "Nessun file scaricabile trovato"

- `megadl` non e' installato nel container: `download_mega_auto` ritorna `[]`.
- Il `Dockerfile` non installa megatools: installalo tu (host o immagine).
- `mega_helper.py` stampa l'errore in `print` dentro un `except`: guarda i log, non il
  messaggio del bot.

## Reddit: profilo scaricato come post, o viceversa

L'ordine dei pattern conta: `PROFILE_PATTERN` e' ancorato con `$` e `USER_POST_PATTERN`
viene provato **prima** di `PROFILE_PATTERN`, cosi' un post dentro un profilo
(`/user/X/comments/ID`) non viene scambiato per profilo intero. Se un caso non e'
rientrato, guarda `reddit_helper.py` -> `classify_reddit_url` e `download_reddit_auto`.

## Reddit: il watcher non scarica nulla

- `reddit_watch.json` non esiste o e' vuoto -> `reddit_watcher_once` ritorna
  `{"new": 0, "removed": 0}` senza fare nulla.
- `REDDIT_CLIENT_ID`/`REDDIT_CLIENT_SECRET` mancanti -> `areddit` e' `None` e le chiamate
  Reddit falliscono.
- Il watcher gira dentro il bot ma `WATCHER_ENABLED` non e' `true`.

## Duplicati: un file "giusto" e' stato rimosso

La regola e' `_keep_priority`: vince sempre il file dentro `autodownloader/`, altrimenti
il piu' recente per `mtime`. Se hai copie fuori da `autodownloader/`, uno sweep le
considera candidati alla rimozione. Guarda `dedupe_core.py` -> `_keep_priority`, `_is_auto`.

## Lo sweep non trova duplicati che invece esistono

- Il file non ha un'estensione in `VALID_EXTS`: non viene neanche considerato.
- Il DB non ha l'hash: lancia `rehash_files` (comando `/recalculate`) per ricostruirlo.
- Lo sweep e' stato interrotto da un'altra istanza che deteneva `.dedupe.lock`.

## Warning / memory leak sui client Reddit

I client Reddit vanno chiusi esplicitamente dopo ogni run. E' un punto noto del TODO
nel README (`reddit_helper.py`: refactor lazy init/close in tutte le funzioni).

## Il log non compare

- `setup_logging` scrive stdout e `botg.log` in `SAVE_DIR` (rotante, 5 MB x 3).
- Se `SAVE_DIR` non e' scrivibile, il file handler fallisce con un `print` e resta solo
  stdout: guarda i log del container.
- Molti errori passano da `print`/`except` nei helper: non sempre finiscono in `botg.log`.
