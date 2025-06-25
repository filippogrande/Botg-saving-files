import os
import re
import subprocess
from datetime import datetime
import shutil

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

def get_megadl_command():
    """
    Trova il path corretto per megadl.
    """
    # Prova vari path possibili
    possible_paths = ['megadl', '/usr/bin/megadl', '/usr/local/bin/megadl']
    
    for path in possible_paths:
        try:
            result = subprocess.run([path, '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                return path
        except:
            continue
    
    return None

def check_megatools_installed():
    """
    Verifica se megatools è installato nel sistema.
    """
    return get_megadl_command() is not None

def download_with_megatools(mega_url, save_dir, custom_prefix=None):
    """
    Usa megatools per scaricare da Mega.
    """
    try:
        megadl_cmd = get_megadl_command()
        if not megadl_cmd:
            print("megatools non trovato nel sistema")
            return []
            
        # Crea la directory se non esiste
        os.makedirs(save_dir, exist_ok=True)
        
        # Crea una directory temporanea per il download
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if custom_prefix:
            temp_dir = os.path.join(save_dir, f"{custom_prefix}_temp_{timestamp}")
        else:
            temp_dir = os.path.join(save_dir, f"mega_temp_{timestamp}")
            
        os.makedirs(temp_dir, exist_ok=True)
        
        # Esegui megadl con il path corretto
        cmd = [megadl_cmd, '--path', temp_dir, mega_url]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        downloaded_files = []
        
        if result.returncode == 0:
            # Trova tutti i file scaricati
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    src_path = os.path.join(root, file)
                    
                    # Calcola il percorso relativo per mantenere la struttura
                    rel_path = os.path.relpath(src_path, temp_dir)
                    
                    # Sanitizza il nome del file
                    sanitized_name = sanitize_filename(rel_path)
                    
                    # Crea il nome finale del file
                    if custom_prefix:
                        final_name = f"{custom_prefix}_{timestamp}_{sanitized_name}"
                    else:
                        final_name = f"mega_{timestamp}_{sanitized_name}"
                    
                    final_path = os.path.join(save_dir, final_name)
                    
                    # Crea le directory se necessario
                    os.makedirs(os.path.dirname(final_path), exist_ok=True)
                    
                    # Sposta il file
                    shutil.move(src_path, final_path)
                    downloaded_files.append(final_path)
            
            # Rimuovi la directory temporanea
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                
            return downloaded_files
        else:
            print(f"Errore megatools: {result.stderr}")
            # Rimuovi la directory temporanea in caso di errore
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            return []
            
    except subprocess.TimeoutExpired:
        print("Timeout durante il download Mega")
        return []
    except Exception as e:
        print(f"Errore durante il download con megatools: {e}")
        return []

def download_mega_auto(mega_url, save_dir, custom_prefix=None, preserve_structure=True):
    """
    Scarica da Mega usando solo megatools (funziona sia per file che cartelle).
    """
    try:
        return download_with_megatools(mega_url, save_dir, custom_prefix)
    except Exception as e:
        print(f"Errore nell'auto-download Mega: {e}")
        return []

def is_mega_link(url):
    """
    Verifica se un URL è un link Mega valido.
    """
    mega_pattern = r"https?://mega\.nz/(file|folder)/[^#]+#.+"
    return bool(re.match(mega_pattern, url))
