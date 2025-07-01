import os
import requests
import asyncpraw
import re
from datetime import datetime
from redgifs_helper import download_redgifs_auto

# Configurazione Reddit asincrona (le credenziali devono essere le stesse di bot.py)
areddit = asyncpraw.Reddit(
    client_id="zwBi1I4DMCFI0QM_meFqJQ",
    client_secret="1x-jhTKVAyGAJ79ztZwaYab-c7JJLQ",
    user_agent="telegram-bot-reddit"
)

def download_gallery(submission, author, timestamp, save_dir):
    files = []
    if hasattr(submission, 'gallery_data') and hasattr(submission, 'media_metadata'):
        for idx, item in enumerate(submission.gallery_data['items']):
            media_id = item['media_id']
            media_url = submission.media_metadata[media_id]['s']['u']
            ext = os.path.splitext(media_url)[1].split('?')[0]
            filename = f"{save_dir}/{author}_{submission.id}_{timestamp}_{idx}{ext}"
            r = requests.get(media_url, timeout=20)
            with open(filename, 'wb') as f:
                f.write(r.content)
            files.append(filename)
    return files

def download_image(submission, author, timestamp, save_dir):
    media_url = submission.url
    ext = os.path.splitext(media_url)[1]
    filename = f"{save_dir}/{author}_{submission.id}_{timestamp}{ext}"
    r = requests.get(media_url, timeout=20)
    with open(filename, 'wb') as f:
        f.write(r.content)
    return [filename]

def download_video(submission, author, timestamp, save_dir):
    media_url = submission.media['reddit_video']['fallback_url']
    ext = ".mp4"
    filename = f"{save_dir}/{author}_{submission.id}_{timestamp}{ext}"
    r = requests.get(media_url, timeout=20)
    with open(filename, 'wb') as f:
        f.write(r.content)
    return [filename]

def download_direct_gif_video(submission, author, timestamp, save_dir):
    media_url = submission.url
    ext = ".mp4"
    filename = f"{save_dir}/{author}_{submission.id}_{timestamp}{ext}"
    r = requests.get(media_url, timeout=20)
    with open(filename, 'wb') as f:
        f.write(r.content)
    return [filename]

def download_redgifs(submission, save_dir):
    # Usa l'helper già esistente, ritorna lista o stringa
    file_path = download_redgifs_auto(submission.url, save_dir)
    if file_path:
        return [file_path]
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

async def download_reddit_auto(url, save_dir, max_posts=None):
    """
    Scarica automaticamente i media dal link Reddit fornito (profilo, post, immagine, video, ecc).
    Args:
        url (str): link Reddit (profilo, post, immagine, ecc)
        save_dir (str): directory di salvataggio
        max_posts (int, opzionale): solo per profili, massimo numero di post
    Returns:
        List[str] o str: lista file scaricati o messaggio di errore
    """
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

