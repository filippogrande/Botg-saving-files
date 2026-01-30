import os
from salvataggio import build_path, safe_name
from deduplica import deduplica_file
from dotenv import load_dotenv

# Carica .env se presente
load_dotenv()
import requests
import asyncpraw
import re
from datetime import datetime
from redgifs_helper import download_redgifs_auto
import json
import asyncio
import tempfile
import mimetypes
from urllib.parse import urlparse
try:
    import clamd
except Exception:
    clamd = None


# Configurazione Reddit asincrona (legge le credenziali dalle env vars)
REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.environ.get("REDDIT_USER_AGENT", "telegram-bot-reddit")

if REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET:
    try:
        areddit = asyncpraw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT
        )
    except Exception as e:
        print(f"Errore inizializzazione asyncpraw: {e}")
        areddit = None
else:
    areddit = None

WATCH_FILE = "reddit_watch.json"
USER_FILE = "reddit_notify_user.txt"

def download_gallery(submission, author, timestamp, save_dir):
    files = []
    if hasattr(submission, 'gallery_data') and hasattr(submission, 'media_metadata'):
        for idx, item in enumerate(submission.gallery_data['items']):
            try:
                media_id = item['media_id']
                media_url = submission.media_metadata[media_id]['s']['u']
                ext = os.path.splitext(media_url)[1].split('?')[0]
                filename = f"{author}_{submission.id}_{timestamp}_{idx}{ext}"
                filepath = build_path(save_dir, 'Reddit', author, str(submission.id), filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                # Scarica in modo sicuro usando safe_download
                ok = safe_download(media_url, filepath)
                if ok and deduplica_file(filepath, save_dir):
                    files.append(filepath)
            except Exception as e:
                print(f"Errore download gallery item {idx}: {e}")
    return files

def download_image(submission, author, timestamp, save_dir):
    try:
        media_url = submission.url
        ext = os.path.splitext(media_url)[1]
        filename = f"{author}_{submission.id}_{timestamp}{ext}"
        filepath = build_path(save_dir, 'Reddit', author, str(submission.id), filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        ok = safe_download(media_url, filepath)
        if ok and deduplica_file(filepath, save_dir):
            return [filepath]
        return []
    except Exception as e:
        print(f"Errore download immagine: {e}")
        return []

def download_video(submission, author, timestamp, save_dir):
    try:
        media_url = submission.media['reddit_video']['fallback_url']
        ext = ".mp4"
        filename = f"{author}_{submission.id}_{timestamp}{ext}"
        filepath = build_path(save_dir, 'Reddit', author, str(submission.id), filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        ok = safe_download(media_url, filepath)
        if ok and deduplica_file(filepath, save_dir):
            return [filepath]
        return []
    except Exception as e:
        print(f"Errore download video: {e}")
        return []

def download_direct_gif_video(submission, author, timestamp, save_dir):
    try:
        media_url = submission.url
        ext = ".mp4"
        filename = f"{author}_{submission.id}_{timestamp}{ext}"
        filepath = build_path(save_dir, 'Reddit', author, str(submission.id), filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        ok = safe_download(media_url, filepath)
        if ok and deduplica_file(filepath, save_dir):
            return [filepath]
        return []
    except Exception as e:
        print(f"Errore download gif/video diretto: {e}")
        return []

def download_redgifs(submission, save_dir):
    try:
        # Qui si può usare build_path per la cartella, ma download_redgifs_auto gestisce già il path
        file_path = download_redgifs_auto(submission.url, save_dir)
        if file_path:
            return [file_path]
        return []
    except Exception as e:
        print(f"Errore download Redgifs: {e}")
        return []

async def download_reddit_profile_media(username, save_dir, max_posts=None):
    """
    Scarica tutti i media pubblici (immagini, video, gallerie, ecc) da un profilo Reddit usando download_reddit_auto per ogni post.
    Args:
        username (str): username Reddit
        save_dir (str): directory di salvataggio
        max_posts (int, opzionale): massimo numero di post da scaricare
    Returns:
        List[str]: lista dei file scaricati
    """
    os.makedirs(save_dir, exist_ok=True)
    try:
        redditor = await areddit.redditor(username)
        submissions = redditor.submissions.new(limit=max_posts)
        files = []
        async for submission in submissions:
            # Costruisci l'URL canonico del post
            post_url = f"https://www.reddit.com{submission.permalink}" if hasattr(submission, 'permalink') else None
            if post_url:
                result = await download_reddit_auto(post_url, save_dir)
                if isinstance(result, list):
                    files.extend(result)
        # Se non c'è permalink, fallback legacy (poco probabile)
        return files
    except Exception as e:
        return f"Errore: {str(e)}"


def safe_download(url, dest_path, allowed_types_prefixes=('image/', 'video/'), max_size=None):
    """
    Scarica in modo sicuro un URL: valida Content-Type e Content-Length con HEAD,
    scarica in file temporaneo, scansiona con ClamAV se disponibile, poi sposta in destinazione.
    Restituisce True se il file è stato salvato correttamente, False altrimenti.
    """
    tmp_path = None
    try:
        # Config max size
        if max_size is None:
            max_size = int(os.environ.get('MAX_DOWNLOAD_SIZE_BYTES', 500 * 1024 * 1024))

        # HEAD request per verificare tipo e dimensione
        h = requests.head(url, allow_redirects=True, timeout=10)
        ctype = h.headers.get('Content-Type', '') or ''
        clen = int(h.headers.get('Content-Length', 0) or 0)

        # Validazione tipo
        if not any(ctype.startswith(p) for p in allowed_types_prefixes):
            # try to guess from extension as fallback
            parsed = urlparse(url)
            ext = os.path.splitext(parsed.path)[1]
            guessed = mimetypes.guess_type('file'+ext)[0] or ''
            if not any(guessed.startswith(p) for p in allowed_types_prefixes):
                print(f"Tipo non permesso: {ctype} (estensione {ext}) per URL {url}")
                return False

        # Validazione dimensione
        if clen and clen > max_size:
            print(f"File troppo grande ({clen} bytes) per URL {url}")
            return False

        # Scarica in file temporaneo
        tmp_fd, tmp_path = tempfile.mkstemp()
        os.close(tmp_fd)
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            total = 0
            with open(tmp_path, 'wb') as f:
                for chunk in r.iter_content(1024 * 64):
                    if not chunk:
                        continue
                    f.write(chunk)
                    total += len(chunk)
                    if total > max_size:
                        f.close()
                        os.remove(tmp_path)
                        print(f"Download abortito: superato limite dimensione durante lo streaming per {url}")
                        return False

        # Scansione ClamAV (se disponibile)
        scan_result = None
        if clamd:
            try:
                cd = clamd.ClamdUnixSocket()
                scan_result = cd.scan(tmp_path)
            except Exception:
                try:
                    cd = clamd.ClamdNetworkSocket()
                    scan_result = cd.scan(tmp_path)
                except Exception:
                    scan_result = None

        if scan_result:
            # scan_result is dict {path: ('FOUND'/'OK', 'name' or None)}
            res = scan_result.get(tmp_path)
            if res and isinstance(res, tuple) and 'FOUND' in res[0]:
                os.remove(tmp_path)
                print(f"Malware rilevato in {url}: {res}")
                return False

        # Muovi file nella destinazione finale
        os.replace(tmp_path, dest_path)
        os.chmod(dest_path, 0o600)
        return True
    except Exception as e:
        print(f"Errore in safe_download per {url}: {e}")
        try:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        return False

# Funzione per salvare l'user_id Telegram del primo che usa monitora
async def save_notify_user(user_id, save_dir):
    user_path = os.path.join(save_dir, USER_FILE)
    if not os.path.exists(user_path):
        with open(user_path, "w") as f:
            f.write(str(user_id))

# Funzione per leggere l'user_id Telegram
def get_notify_user(save_dir):
    user_path = os.path.join(save_dir, USER_FILE)
    if os.path.exists(user_path):
        with open(user_path, "r") as f:
            return int(f.read().strip())
    return None

# Funzione per aggiungere un profilo da monitorare
async def add_reddit_profile_to_watch(username, save_dir, user_id=None):
    watch_path = os.path.join(save_dir, WATCH_FILE)
    if os.path.exists(watch_path):
        with open(watch_path, "r") as f:
            watch = json.load(f)
    else:
        watch = {}
    # Recupera l'ultimo post attuale
    redditor = await areddit.redditor(username)
    submissions = redditor.submissions.new(limit=1)
    last_id = None
    async for submission in submissions:
        last_id = submission.id
        break
    watch[username] = {"last_id": last_id}
    with open(watch_path, "w") as f:
        json.dump(watch, f)
    # Salva user_id se fornito
    if user_id:
        await save_notify_user(user_id, save_dir)
    return f"Profilo {username} aggiunto al monitoraggio. Ultimo post visto: {last_id}"

# Modifica watcher per inviare log giornaliero
async def reddit_profile_watcher_loop(save_dir, duplicate_handler, bot=None):
    while True:
        now = datetime.now()
        # Calcola i secondi fino a mezzanotte
        next_run = datetime(now.year, now.month, now.day)  # oggi a mezzanotte
        if now > next_run:
            next_run = next_run.replace(day=now.day+1)
        seconds = (next_run - now).total_seconds()
        await asyncio.sleep(seconds)
        # Carica i profili da monitorare
        watch_path = os.path.join(save_dir, WATCH_FILE)
        if not os.path.exists(watch_path):
            continue
        with open(watch_path, "r") as f:
            watch = json.load(f)
        notify_user = get_notify_user(save_dir)
        total_new = 0
        total_removed = 0
        for username, info in watch.items():
            last_id = info.get("last_id")
            try:
                redditor = await areddit.redditor(username)
                submissions = redditor.submissions.new(limit=10)
                new_last_id = last_id
                new_files = []
                async for submission in submissions:
                    if submission.id == last_id:
                        break
                    post_url = f"https://www.reddit.com{submission.permalink}" if hasattr(submission, 'permalink') else None
                    if post_url:
                        result = await download_reddit_auto(post_url, save_dir)
                        if isinstance(result, list):
                            new_files.extend(result)
                    if not new_last_id:
                        new_last_id = submission.id
                # Aggiorna solo se ci sono nuovi post
                if new_files and new_last_id:
                    watch[username]["last_id"] = new_last_id
                total_new += len(new_files)
            except Exception as e:
                print(f"Errore watcher Reddit per {username}: {e}")
        # Deduplica e conta duplicati rimossi
        removed = await duplicate_handler()
        total_removed += removed if removed else 0
        with open(watch_path, "w") as f:
            json.dump(watch, f)
        # Invia log se bot e user_id sono disponibili
        if bot and notify_user:
            msg = f"[Watcher Reddit]\nNuovi file scaricati: {total_new}\nDuplicati eliminati: {total_removed}"
            try:
                await bot.send_message(chat_id=notify_user, text=msg)
            except Exception as e:
                print(f"Errore invio log Telegram: {e}")


async def reddit_watcher_once(save_dir, duplicate_handler, bot=None):
    """
    Esegue una singola iterazione del watcher: controlla tutti i profili in save_dir/reddit_watch.json,
    scarica nuovi post, esegue duplicate_handler e invia il log a Telegram (se bot e notify_user sono forniti).
    """
    watch_path = os.path.join(save_dir, WATCH_FILE)
    if not os.path.exists(watch_path):
        return {"new": 0, "removed": 0}
    with open(watch_path, "r") as f:
        watch = json.load(f)
    notify_user = get_notify_user(save_dir)
    total_new = 0
    total_removed = 0
    for username, info in watch.items():
        last_id = info.get("last_id")
        try:
            redditor = await areddit.redditor(username)
            submissions = redditor.submissions.new(limit=10)
            new_last_id = last_id
            new_files = []
            async for submission in submissions:
                if submission.id == last_id:
                    break
                post_url = f"https://www.reddit.com{submission.permalink}" if hasattr(submission, 'permalink') else None
                if post_url:
                    result = await download_reddit_auto(post_url, save_dir)
                    if isinstance(result, list):
                        new_files.extend(result)
                if not new_last_id:
                    new_last_id = submission.id
            if new_files and new_last_id:
                watch[username]["last_id"] = new_last_id
            total_new += len(new_files)
        except Exception as e:
            print(f"Errore watcher Reddit per {username}: {e}")
    # Esegui deduplication
    removed = await duplicate_handler()
    total_removed += removed if removed else 0
    with open(watch_path, "w") as f:
        json.dump(watch, f)
    if bot and notify_user:
        msg = f"[Watcher Reddit]\nNuovi file scaricati: {total_new}\nDuplicati eliminati: {total_removed}"
        try:
            await bot.send_message(chat_id=notify_user, text=msg)
        except Exception as e:
            print(f"Errore invio log Telegram: {e}")
    return {"new": total_new, "removed": total_removed}

# Modifica download_reddit_auto per passare user_id
async def download_reddit_auto(url, save_dir, max_posts=None, user_id=None):
    """
    Scarica automaticamente i media dal link Reddit fornito (profilo, post, immagine, video, ecc).
    Se il messaggio inizia con 'monitora ', aggiunge il profilo al watcher.
    """
    if url.lower().startswith("monitora "):
        # Estrai username dal link
        m = re.search(r"reddit.com/(user|u)/([\w\d_-]+)", url)
        if m:
            username = m.group(2)
            return await add_reddit_profile_to_watch(username, save_dir, user_id=user_id)
        else:
            return "Link profilo Reddit non valido."
    # Riconoscimento URL: prima i post (inclusi shortlink come /u/<user>/s/<id>), poi immagini dirette, infine profilo
    post_pattern = r"https?://(www\.)?reddit\.com/r/[\w\d_]+/(comments/[\w\d]+/[\w\d_]+|s/[\w\d]+)"
    post_user_short_pattern = r"https?://(www\.)?reddit\.com/(user|u)/[\w\d_-]+/s/[\w\d]+"
    img_pattern = r"https?://i\.redd\.it/[\w\d]+\.[a-zA-Z0-9]+"
    profile_pattern = r"https?://(www\.)?reddit\.com/(user|u)/([\w\d_-]+)(/)?$"
    try:
        if re.match(post_pattern, url) or re.match(post_user_short_pattern, url):
            # Post classico o shortlink a post
            submission = await areddit.submission(url=url)
            author = submission.author.name if submission.author else "unknown"
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            if hasattr(submission, 'is_gallery') and submission.is_gallery:
                return download_gallery(submission, author, timestamp, save_dir)
            elif hasattr(submission, 'post_hint') and submission.post_hint == 'image':
                return download_image(submission, author, timestamp, save_dir)
            elif hasattr(submission, 'is_video') and submission.is_video and submission.media:
                return download_video(submission, author, timestamp, save_dir)
            elif any(submission.url.endswith(ext) for ext in ['.gif', '.gifv', '.webm', '.mp4']):
                return download_direct_gif_video(submission, author, timestamp, save_dir)
            elif submission.media and 'oembed' in submission.media and 'provider_name' in submission.media['oembed'] and submission.media['oembed']['provider_name'].lower() == 'redgifs':
                return download_redgifs(submission, save_dir)
            else:
                return "Nessun media scaricabile trovato nel post Reddit."

        elif re.match(img_pattern, url):
            # Immagine diretta
            class Dummy:
                pass
            submission = Dummy()
            submission.url = url
            author = "direct"
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            return download_image(submission, author, timestamp, save_dir)

        elif re.match(profile_pattern, url):
            username = re.match(profile_pattern, url).group(3)
            return await download_reddit_profile_media(username, save_dir, max_posts=max_posts)
        else:
            return "Link Reddit non riconosciuto o non supportato."
    except Exception as e:
        return f"Errore: {str(e)}"

