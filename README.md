# Botg-saving-files

Bot Telegram per il salvataggio automatico di media da Telegram, Reddit, Redgifs e Mega, con deduplicazione e gestione storage su filesystem locale o mount di rete. Supporta esecuzione in Docker e Kubernetes, con watcher Reddit schedulabile (interno o via CronJob).

---

## Scopo del progetto

- Automatizzare il salvataggio di foto, video e altri media ricevuti su Telegram o scaricati da link ricevuti di Reddit, Redgifs, Mega.
- Evitare duplicati tramite hash e database SQLite.
- Consentire l'esecuzione in ambienti containerizzati (Docker/Kubernetes) e su storage di rete.
- Permettere la schedulazione del download periodico da profili Reddit (watcher giornaliero).
- Permettere il download di contenuti anche se il server era offline al momento del messaggio (forse da implementare).

---

## Funzionalità principali

- **Bot Telegram**: riceve media (foto, video, animazioni) e li salva in una directory configurabile.
- **Download da Reddit, Redgifs, Mega**: scarica media da link inviati o da profili monitorati.
- **Deduplicazione**: elimina file duplicati tramite hash, gestendo la persistenza in SQLite (`bot.db`).
- **Watcher Reddit**: può essere eseguito come job giornaliero (interno al bot o via CronJob) per scaricare nuovi media dai profili seguiti (dobbiamo scegliere quale sia il metodo migliore?).
- **Notifica di avvio**: invia un messaggio Telegram a un admin/chat all’avvio del bot.
- **Container-ready**: tutto configurabile via `.env`, pronto per Docker/Kubernetes.

---

## Architettura

- **bot.py**: entrypoint principale, avvia il bot Telegram e (opzionalmente) il watcher Reddit giornaliero.
- **reddit_helper.py**: funzioni per scaricare media da Reddit; watcher one-shot e loop.
- **db_helper.py**: gestione database SQLite per deduplicazione.
- **run_watcher.py**: script per eseguire il watcher Reddit una sola volta (usato da CronJob).
- **k8s/**: manifesti Kubernetes per deploy e CronJob.
- **requirements.txt**: dipendenze Python.

---

## Note tecniche

- **Lazy import e risorse**: le librerie pesanti (yt-dlp, requests, asyncpraw) vengono importate solo quando servono, per ridurre il consumo di RAM a idle.
- **Database**: ogni funzione che accede al DB apre e chiude la connessione in modo sicuro (vedi `db_helper.py`).
- **Watcher Reddit**: può essere schedulato internamente (loop ogni 24h) o esternamente (consigliato per ambienti containerizzati).
- **Chiusura risorse**: i client Reddit vengono chiusi esplicitamente dopo ogni run per evitare warning e memory leak.
- **Kubernetes**: sono forniti manifesti per deploy e CronJob; puoi personalizzare risorse/limiti secondo le tue esigenze.

---

## Comandi utili

- **Controlla RAM/CPU del container**:
  ```bash
  docker stats botg --no-stream
  ```
- **Vedi log**:
  ```bash
  docker logs -f botg
  ```
- **Esegui deduplicazione manuale**:
  ```bash
  docker exec -it botg python -c 'from find_duplicate_helper import find_duplicates; print(find_duplicates("/mnt/truenas-bot"))'
  ```

---

## Best practice

- Usa watcher esterno (CronJob) per massima leggerezza e isolamento.
- Monta la directory di salvataggio su storage persistente (es. volume host o PVC in K8s).
- Proteggi il file `.env` (contiene credenziali sensibili).
- Aggiorna regolarmente le dipendenze (`requirements.txt`).

---

## TODO e miglioramenti possibili

- [ ] Refactor finale di `reddit_helper.py` per lazy init/close client Reddit in tutte le funzioni.
- [ ] Aggiornare i manifesti K8s se cambi la logica di scheduling.
- [ ] (Opzionale) Aggiungere healthcheck e readiness probe per Kubernetes.
- [ ] (Opzionale) Logging strutturato e metriche Prometheus.

---

esempi

## Struttura delle cartelle e deduplicazione

- Tutti i nuovi file scaricati dal bot vengono salvati in una sottocartella `autodownloader/` rispetto alla directory base di salvataggio.
  - Esempio: `/mnt/truenas-bot/autodownloader/Reddit/utente/12345/nomefile.jpg`
- I file già presenti nella root o in altre sottocartelle restano dove sono.
- In caso di duplicati (stesso hash):
  - Se uno dei file è in `autodownloader/` e l'altro fuori, viene sempre mantenuto quello in `autodownloader/` (anche se più nuovo o più vecchio), eliminando l'altro.
  - Se entrambi sono in `autodownloader/` o entrambi fuori, viene mantenuto il primo trovato.
- La deduplicazione batch/manuale ricalcola e aggiorna l'hash di tutti i file, ricostruendo lo stato del database.

### Esempi di path

- autodownloader/reddit/pics/username123/2023-10-15_immagine.jpg
- autodownloader/redgifs/utente456/video1.mp4
- autodownloader/mega/share_di_prova/file.pdf

> I nomi delle cartelle e dei file vengono normalizzati e troncati per garantire portabilità e compatibilità cross-platform.

---

Per domande o suggerimenti: apri una issue su GitHub o contatta l'autore.
