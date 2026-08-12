import yt_dlp
import os
from datetime import datetime
import requests
import re
import time
from salvataggio import build_path, safe_name
from deduplica import deduplica_file
from actor_map import resolve_actor, is_mapped
from source_helper import write_source

def get_redgifs_creator_from_post(post_url):
    """
    Estrae il nome utente del creator dalla pagina del post Redgifs.
    """
    try:
        page = requests.get(post_url, timeout=10).text
        # Cerca il link al profilo utente nella pagina
        match = re.search(r'https://www\.redgifs\.com/users/([\w\d_-]+)', page)
        if match:
            return match.group(1)
    except Exception as e:
        print(f"Errore estrazione creator Redgifs: {e}")
    return "redgifs"

def download_redgifs_video(video_url, save_dir, prefix=None, stats=None):
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if not prefix or prefix == "redgifs":
            creator = get_redgifs_creator_from_post(video_url)
            prefix = creator or "redgifs"
        prefix_raw = prefix
        prefix = resolve_actor('redgifs', prefix)
        seg2 = 'attore' if is_mapped('redgifs', prefix_raw) else 'Redgifs'
        filename = f"{prefix}_{timestamp}.mp4"
        filepath = build_path(save_dir, seg2, prefix, timestamp, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        ydl_opts = {
            'outtmpl': filepath,
            'format': 'mp4/bestvideo+bestaudio/best',
            'quiet': True,
            'merge_output_format': 'mp4',
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        kept = deduplica_file(filepath, save_dir)
        if kept:
            write_source(filepath, video_url)
            return filepath
        elif stats is not None:
            stats['duplicates'] = stats.get('duplicates', 0) + 1
        return None
    except Exception as e:
        print(f"Errore download video Redgifs: {e}")
        return None

def download_redgifs_image_from_post(post_url, save_dir, prefix=None, stats=None):
    try:
        page = requests.get(post_url, timeout=10).text
        img_match = re.search(r'(https://[\w\d\./_-]+\.(?:jpg|jpeg|png|webp))', page)
        if img_match:
            img_url = img_match.group(1)
            ext_img = os.path.splitext(img_url)[1].split('?')[0]
            if not prefix or prefix == "redgifs_img":
                creator = get_redgifs_creator_from_post(post_url)
                prefix = creator or "redgifs_img"
            prefix_raw = prefix
            prefix = resolve_actor('redgifs', prefix)
            seg2 = 'attore' if is_mapped('redgifs', prefix_raw) else 'Redgifs'
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{prefix}_{timestamp}{ext_img}"
            filepath = build_path(save_dir, seg2, prefix, timestamp, filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            r = requests.get(img_url, timeout=10)
            with open(filepath, 'wb') as f:
                f.write(r.content)
            kept = deduplica_file(filepath, save_dir)
            if kept:
                write_source(filepath, img_url)
                return filepath
            elif stats is not None:
                stats['duplicates'] = stats.get('duplicates', 0) + 1
            return None
        else:
            return None
    except Exception as e:
        print(f"Errore download immagine Redgifs: {e}")
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
    except Exception as e:
        print(f"Errore determinazione tipo post Redgifs: {e}")
        return 'altro'

def download_redgifs_auto(post_url, save_dir, prefix=None, allow_video=True, allow_photo=True, stats=None):
    try:
        tipo = redgifs_post_type(post_url)
        if tipo == 'video' and allow_video:
            return download_redgifs_video(post_url, save_dir, prefix, stats=stats)
        elif tipo == 'foto' and allow_photo:
            return download_redgifs_image_from_post(post_url, save_dir, prefix, stats=stats)
        else:
            return None
    except Exception as e:
        print(f"Errore download auto Redgifs: {e}")
        return None
    
def download_redgifs_profile(username, save_dir, max_posts=None, allow_video=True, allow_photo=True, stats=None):
    user_url = f"https://www.redgifs.com/users/{username}/creations"
    try:
        page = requests.get(user_url, timeout=10).text
        post_links = re.findall(r'https://www\.redgifs\.com/watch/[\w\d_-]+', page)
        post_links = list(dict.fromkeys(post_links))
        if max_posts:
            post_links = post_links[:max_posts]
        results = []
        for post_url in post_links:
            try:
                file_path = download_redgifs_auto(post_url, save_dir, allow_video=allow_video, allow_photo=allow_photo, stats=stats)
                if file_path:
                    results.append(file_path)
                time.sleep(2)
            except Exception as e:
                print(f"Errore download post Redgifs {post_url}: {e}")
        return results
    except Exception as e:
        print(f"Errore download profilo Redgifs: {e}")
        return []