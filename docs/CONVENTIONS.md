# CONVENTIONS — regole del codice e del repo

<!-- Tipo: HOW-TO. Le regole da seguire quando scrivi o modifichi questo repo. -->

## Limiti di forma

- **500 righe per file.** Oltre, il file contiene piu' di una responsabilita': dividilo
  seguendo la coesione semantica, non il conteggio.
- **50 righe per funzione.** Oltre, la funzione fa piu' cose: estrai.
- **Niente fallback silenziosi.** Un `except Exception: pass` (o un `print` al posto di un
  log) nasconde l'errore a chi ci lavora dopo. Logga o rilancia.
- **Niente file usa-e-getta.** Niente `test-fix.txt`, niente `.DS_Store`, niente script
  monouso in root.
- **Niente numeri di riga nei doc.** Le righe si muovono, i simboli no: puntare sempre a
  un nome (`deduplica_file`), mai a `file.py:340`.

## Struttura del codice

- **Un file = una responsabilita'.** Il confine segue la coesione semantica. Se una voce
  della mappa punta a tre file, il confine e' sbagliato.
- **L'entry point assembla, i moduli restanti sono puri.** La mappa punta all'entry point
  (`bot.py`, `run_watcher.py`), non ai moduli interni.
- **Nomi dal dominio, non dalla tecnologia.** `reddit_helper.py`, non `handler_reddit.py`.
- **Wrapper documentati.** `deduplica.py` e `find_duplicate_helper.py` sono re-export verso
  `dedupe_core.py`: se ne aggiungi uno, dichiara a cosa punta e perche' esiste.

## Doc

- I doc stanno in `docs/`, in pochi file consolidati per scope. In root restano solo
  `README.md`, i manifest (`requirements.txt`, `Dockerfile`, `docker-compose.yml`),
  `.gitignore` e le cartelle.
- Un doc e' **uno solo dei quattro tipi**, dichiarato in testa: reference (fatti),
  explanation (come/perche'), how-to (passi), tutorial.
- Un doc che mente e' peggio di nessun doc: si corregge o si cancella **nella stessa PR**.
- **Un solo doc per concetto.** Se `GUIDELINES`, `DEVELOPMENT_GUIDELINES` e `CONVENTIONS`
  dicono la stessa cosa, si consolidano in uno.
- La mappa (`docs/REFERENCE.md`) si aggiorna nella stessa PR che sposta, rinomina o
  divide un simbolo. Nuova area = una riga nuova, non un doc nuovo.
- Niente segreti nei doc: token, `chat_id` e password diventano placeholder.

## Pull request

- Branch + PR, **mai push su `main`**.
- Una PR tocca un concetto, non piu'. Se la PR tocca doc e codice, sono lo stesso
  cambiamento.
- Commit message **conventional**: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`,
  `deps:`, `ci:`.
- Solo documentazione? Dillo nel titolo: `docs: ...`.

## Stile del codice

- Logging centralizzato con `setup_logging` (`log_helper.py`): stdout + `botg.log`
  rotante in `SAVE_DIR`. Nei moduli usa il `logger` del modulo, non `print`.
- Gli errori si loggiano con il modulo come logger, con il contesto (path, id, url).
- Le librerie pesanti (`yt-dlp`, `requests`, `asyncpraw`) si importano dove servono, non
  a top-level, per tenere bassa la RAM a idle. Se aggiungi una dipendenza pesante,
  segui la stessa regola.
- Ogni funzione che apre il DB usa `ensure_db` + `try/finally: conn.close()` (vedi
  `db_helper.py`): non lasciare connessioni aperte.
- Le funzioni che toccano la rete ricevono un timeout e un `stats` opzionale per
  contare i duplicati: mantieni il contratto cosi' i report restano corretti.

## Test

- Il repo non ha test. Se ne aggiungi, vanno accanto al modulo (`<modulo>_test.py`) e
  `pytest` va spostato nelle dipendenze di sviluppo, non in `requirements.txt` runtime.
