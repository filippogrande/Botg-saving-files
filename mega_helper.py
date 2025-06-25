import os
import re
from datetime import datetime
import yt_dlp

def extract_mega_info(mega_url):
    """
    Estrae le informazioni da un link Mega (file_id e key).
    Supporta sia link di file che di cartelle.
    """
    try:
        # Pattern per file: https://mega.nz/file/[file_id]#[key]
        file_pattern = r"https?://mega\.nz/file/([^#]+)#(.+)"
        # Pattern per cartelle: https://mega.nz/folder/[folder_id]#[key] 
        folder_pattern = r"https?://mega\.nz/folder/([^#]+)#(.+)"
        
        file_match = re.match(file_pattern, mega_url)
        folder_match = re.match(folder_pattern, mega_url)
        
        if file_match:
            return "file", file_match.group(1), file_match.group(2)
        elif folder_match:
            return "folder", folder_match.group(1), folder_match.group(2)
        else:
            return None, None, None
    except Exception:
        return None, None, None

def sanitize_filename(filename):
    """
    Rimuove caratteri non validi dai nomi dei file.
    """
    # Rimuove caratteri non validi per i filesystem
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename

def download_mega_file(mega_url, save_dir, custom_prefix=None):
    """
    Scarica un singolo file da Mega usando yt-dlp.
    Restituisce il percorso del file scaricato o None in caso di errore.
    """
    try:
        link_type, file_id, key = extract_mega_info(mega_url)
        if link_type != "file":
            return None
            
        # Crea la directory se non esiste
        os.makedirs(save_dir, exist_ok=True)
        
        # Configura yt-dlp per il download
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if custom_prefix:
            output_template = f"{save_dir}/{custom_prefix}_{timestamp}_%(title)s.%(ext)s"
        else:
            output_template = f"{save_dir}/mega_{timestamp}_%(title)s.%(ext)s"
            
        ydl_opts = {
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                # Estrai informazioni senza scaricare
                info = ydl.extract_info(mega_url, download=False)
                if info:
                    # Ora scarica
                    ydl.download([mega_url])
                    
                    # Trova il file scaricato
                    expected_filename = ydl.prepare_filename(info)
                    if os.path.exists(expected_filename):
                        return expected_filename
            except Exception as e:
                print(f"Errore yt-dlp per file Mega: {e}")
                return None
                    
        return None
        
    except Exception as e:
        print(f"Errore durante il download del file Mega: {e}")
        return None

def download_mega_folder(mega_url, save_dir, custom_prefix=None, preserve_structure=True):
    """
    Scarica una cartella da Mega usando yt-dlp.
    Nota: yt-dlp potrebbe non supportare completamente le cartelle Mega.
    """
    try:
        link_type, folder_id, key = extract_mega_info(mega_url)
        if link_type != "folder":
            return []
            
        # Crea la directory base se non esiste
        os.makedirs(save_dir, exist_ok=True)
        
        # Crea una cartella con timestamp per questo download
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if custom_prefix:
            folder_name = f"{custom_prefix}_mega_folder_{timestamp}"
        else:
            folder_name = f"mega_folder_{timestamp}"
            
        download_folder = os.path.join(save_dir, folder_name)
        os.makedirs(download_folder, exist_ok=True)
        
        ydl_opts = {
            'outtmpl': f"{download_folder}/%(title)s.%(ext)s",
            'quiet': True,
            'no_warnings': True,
        }
        
        downloaded_files = []
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Prova a scaricare la cartella
                ydl.download([mega_url])
                
                # Trova tutti i file scaricati
                for root, dirs, files in os.walk(download_folder):
                    for file in files:
                        file_path = os.path.join(root, file)
                        downloaded_files.append(file_path)
                        
        except Exception as e:
            print(f"yt-dlp non è riuscito a scaricare la cartella Mega: {e}")
            # Le cartelle Mega sono complesse, potrebbe non funzionare sempre
            return []
            
        return downloaded_files
        
    except Exception as e:
        print(f"Errore durante il download della cartella Mega: {e}")
        return []

def download_mega_auto(mega_url, save_dir, custom_prefix=None, preserve_structure=True):
    """
    Determina automaticamente se il link Mega è per un file o una cartella
    e utilizza il metodo di download appropriato.
    """
    try:
        link_type, _, _ = extract_mega_info(mega_url)
        
        if link_type == "file":
            result = download_mega_file(mega_url, save_dir, custom_prefix)
            return [result] if result else []
        elif link_type == "folder":
            return download_mega_folder(mega_url, save_dir, custom_prefix, preserve_structure)
        else:
            print("Link Mega non riconosciuto")
            return []
            
    except Exception as e:
        print(f"Errore nell'auto-download Mega: {e}")
        return []

def is_mega_link(url):
    """
    Verifica se un URL è un link Mega valido.
    """
    mega_pattern = r"https?://mega\.nz/(file|folder)/[^#]+#.+"
    return bool(re.match(mega_pattern, url))
