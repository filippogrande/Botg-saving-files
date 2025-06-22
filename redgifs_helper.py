import yt_dlp
import os
from datetime import datetime
import requests
import re
import time

def download_redgifs_video(video_url, save_dir, prefix=None):
    """
    Scarica un video Redgifs dato il link e salva il file in save_dir.
    Restituisce il percorso del file scaricato o None in caso di errore.
    """
    try:
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        prefix = prefix or "redgifs"
        filename = f"{save_dir}/{prefix}_{timestamp}.mp4"
        ydl_opts = {
            'outtmpl': filename,
            'format': 'mp4/bestvideo+bestaudio/best',
            'quiet': True,
            'merge_output_format': 'mp4',
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        return filename
    except Exception as e:
        return None

def download_redgifs_image_from_post(post_url, save_dir, prefix=None):
    """
    Scarica l'immagine statica (jpg/png/webp) da un singolo post Redgifs, se presente.
    Restituisce il percorso del file scaricato o None se non trovata.
    """
    try:
        page = requests.get(post_url, timeout=10).text
        img_match = re.search(r'(https://[\w\d\./_-]+\.(?:jpg|jpeg|png|webp))', page)
        if img_match:
            img_url = img_match.group(1)
            ext_img = os.path.splitext(img_url)[1].split('?')[0]
            prefix = prefix or "redgifs_img"
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{save_dir}/{prefix}_{timestamp}{ext_img}"
            r = requests.get(img_url, timeout=10)
            with open(filename, 'wb') as f:
                f.write(r.content)
            return filename
        else:
            return None
    except Exception:
        return None

def redgifs_post_type(post_url):
    """
    Dato un link di post Redgifs, restituisce 'video' se contiene un video,
    'foto' se contiene una immagine statica, 'altro' altrimenti.
    """
    try:
        page = requests.get(post_url, timeout=10).text
        # Cerca prima video mp4
        video_match = re.search(r'(https://[\w\d\./_-]+\.mp4)', page)
        if video_match:
            return 'video'
        # Poi cerca immagine statica
        img_match = re.search(r'(https://[\w\d\./_-]+\.(?:jpg|jpeg|png|webp))', page)
        if img_match:
            return 'foto'
        return 'altro'
    except Exception:
        return 'altro'

def download_redgifs_auto(post_url, save_dir, prefix=None, allow_video=True, allow_photo=True):
    """
    Gestisce un link Redgifs: determina se è video o foto e chiama il downloader giusto.
    Puoi bloccare il download di video o foto con allow_video/allow_photo.
    Restituisce il percorso del file scaricato o None.
    """
    tipo = redgifs_post_type(post_url)
    if tipo == 'video' and allow_video:
        return download_redgifs_video(post_url, save_dir, prefix)
    elif tipo == 'foto' and allow_photo:
        return download_redgifs_image_from_post(post_url, save_dir, prefix)
    else:
        return None

def download_redgifs_profile(username, save_dir, max_posts=None, allow_video=True, allow_photo=True):
    """
    Scarica tutti i post (video/foto) di un profilo Redgifs.
    Se max_posts è impostato, scarica solo i primi N post trovati.
    Puoi limitare a solo video o solo foto con allow_video/allow_photo.
    Restituisce una lista di file scaricati.
    """
    user_url = f"https://www.redgifs.com/users/{username}/creations"
    try:
        page = requests.get(user_url, timeout=10).text
        post_links = re.findall(r'https://www\.redgifs\.com/watch/[\w\d_-]+', page)
        post_links = list(dict.fromkeys(post_links))  # Rimuove duplicati
        if max_posts:
            post_links = post_links[:max_posts]
        results = []
        for post_url in post_links:
            file_path = download_redgifs_auto(post_url, save_dir, allow_video=allow_video, allow_photo=allow_photo)
            if file_path:
                results.append(file_path)
            time.sleep(2)  # Delay tra i download per evitare anti-DDoS
        return results
    except Exception as e:
        return []
