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

import os

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
                r = requests.get(media_url, timeout=20)
                with open(filepath, 'wb') as f:
                    f.write(r.content)
                if deduplica_file(filepath, save_dir):
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
        r = requests.get(media_url, timeout=20)
        with open(filepath, 'wb') as f:
            f.write(r.content)
        if deduplica_file(filepath, save_dir):
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
        r = requests.get(media_url, timeout=20)
        with open(filepath, 'wb') as f:
            f.write(r.content)
        if deduplica_file(filepath, save_dir):
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
        r = requests.get(media_url, timeout=20)
        with open(filepath, 'wb') as f:
            f.write(r.content)
        if deduplica_file(filepath, save_dir):
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
    # Riconoscimento profilo
    profile_pattern = r"https?://(www\.)?reddit\.com/(user|u)/([\w\d_-]+)"
    img_pattern = r"https?://i\.redd\.it/[\w\d]+\.[a-zA-Z0-9]+"
    post_pattern = r"https?://(www\.)?reddit\.com/r/[\w\d_]+/(comments/[\w\d]+/[\w\d_]+|s/[\w\d]+)"
    try:
        if re.match(profile_pattern, url):
            username = re.match(profile_pattern, url).group(3)
            return await download_reddit_profile_media(username, save_dir, max_posts=max_posts)
        elif re.match(img_pattern, url):
            # Immagine diretta
            class Dummy:
                pass
            submission = Dummy()
            submission.url = url
            author = "direct"
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            return download_image(submission, author, timestamp, save_dir)
        elif re.match(post_pattern, url):
            # Post Reddit classico
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
        else:
            return "Link Reddit non riconosciuto o non supportato."
    except Exception as e:
        return f"Errore: {str(e)}"

