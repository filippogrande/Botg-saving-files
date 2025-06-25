import os
import re
from mega import Mega
from datetime import datetime
import shutil
from urllib.parse import urlparse, parse_qs

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
    Scarica un singolo file da Mega.
    Restituisce il percorso del file scaricato o None in caso di errore.
    """
    try:
        link_type, file_id, key = extract_mega_info(mega_url)
        if link_type != "file":
            return None
            
        mega = Mega()
        m = mega.login()
        
        # Crea la directory se non esiste
        os.makedirs(save_dir, exist_ok=True)
        
        # Scarica il file in una directory temporanea
        temp_dir = os.path.join(save_dir, "temp_mega_download")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Download del file
        file_info = m.download_url(mega_url, temp_dir)
        
        if file_info:
            # Ottieni il nome del file originale
            original_filename = os.path.basename(file_info)
            sanitized_filename = sanitize_filename(original_filename)
            
            # Crea il nome finale del file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            if custom_prefix:
                final_filename = f"{custom_prefix}_{timestamp}_{sanitized_filename}"
            else:
                final_filename = f"mega_{timestamp}_{sanitized_filename}"
                
            final_path = os.path.join(save_dir, final_filename)
            
            # Sposta il file dalla directory temporanea
            shutil.move(file_info, final_path)
            
            # Rimuovi la directory temporanea
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                
            return final_path
        else:
            # Rimuovi la directory temporanea in caso di errore
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            return None
            
    except Exception as e:
        print(f"Errore durante il download del file Mega: {e}")
        # Pulisci in caso di errore
        temp_dir = os.path.join(save_dir, "temp_mega_download")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return None

def download_mega_folder(mega_url, save_dir, custom_prefix=None, preserve_structure=True):
    """
    Scarica una cartella completa da Mega mantenendo la struttura delle directory.
    Restituisce una lista di file scaricati.
    """
    try:
        link_type, folder_id, key = extract_mega_info(mega_url)
        if link_type != "folder":
            return []
            
        mega = Mega()
        m = mega.login()
        
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
        
        downloaded_files = []
        
        if preserve_structure:
            # Scarica mantenendo la struttura delle cartelle
            files_info = m.download_url(mega_url, download_folder)
            
            # Se è un singolo file, files_info sarà una stringa
            if isinstance(files_info, str):
                downloaded_files.append(files_info)
            # Se sono multiple cartelle/file, sarà una lista o dict
            elif isinstance(files_info, (list, dict)):
                if isinstance(files_info, list):
                    downloaded_files.extend(files_info)
                else:
                    # Esplora ricorsivamente la struttura scaricata
                    for root, dirs, files in os.walk(download_folder):
                        for file in files:
                            file_path = os.path.join(root, file)
                            downloaded_files.append(file_path)
            else:
                # Fallback: esplora la cartella scaricata
                for root, dirs, files in os.walk(download_folder):
                    for file in files:
                        file_path = os.path.join(root, file)
                        downloaded_files.append(file_path)
        else:
            # Scarica tutti i file nella cartella principale (struttura piatta)
            files_info = m.download_url(mega_url, download_folder)
            if files_info:
                if isinstance(files_info, str):
                    downloaded_files.append(files_info)
                elif isinstance(files_info, list):
                    downloaded_files.extend(files_info)
                    
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
