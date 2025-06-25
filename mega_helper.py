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

def check_megatools_installed():
    """
    Verifica se megatools è installato nel sistema.
    """
    try:
        result = subprocess.run(['megadl', '--version'], capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def download_with_megatools(mega_url, save_dir, custom_prefix=None):
    """
    Usa megatools per scaricare da Mega.
    """
    try:
        if not check_megatools_installed():
            print("megatools non è installato")
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
        
        # Esegui megadl (parte di megatools)
        cmd = ['megadl', '--path', temp_dir, mega_url]
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

def download_with_gdown(mega_url, save_dir, custom_prefix=None):
    """
    Prova a usare gdown se il link è compatibile.
    """
    try:
        # Verifica se gdown è disponibile
        import gdown
        
        link_type, file_id, key = extract_mega_info(mega_url)
        if link_type != "file":
            return []
            
        # Crea la directory se non esiste
        os.makedirs(save_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if custom_prefix:
            filename = f"{save_dir}/{custom_prefix}_{timestamp}_mega_file"
        else:
            filename = f"{save_dir}/mega_{timestamp}_file"
        
        # Prova a scaricare con gdown (funziona solo con alcuni link)
        output = gdown.download(mega_url, filename, quiet=False)
        
        if output and os.path.exists(output) and os.path.getsize(output) > 0:
            return [output]
        else:
            if os.path.exists(filename):
                os.remove(filename)
            return []
            
    except ImportError:
        print("gdown non disponibile")
        return []
    except Exception as e:
        print(f"Errore con gdown: {e}")
        return []

def download_mega_file(mega_url, save_dir, custom_prefix=None):
    """
    Scarica un singolo file da Mega usando vari metodi.
    """
    try:
        # Prova prima con megatools
        result = download_with_megatools(mega_url, save_dir, custom_prefix)
        if result:
            return result[0] if len(result) == 1 else result[0]
            
        # Fallback con gdown
        result = download_with_gdown(mega_url, save_dir, custom_prefix)
        if result:
            return result[0]
            
        return None
        
    except Exception as e:
        print(f"Errore durante il download del file Mega: {e}")
        return None

def download_mega_folder(mega_url, save_dir, custom_prefix=None, preserve_structure=True):
    """
    Scarica una cartella completa da Mega.
    """
    try:
        # Per le cartelle usiamo solo megatools
        result = download_with_megatools(mega_url, save_dir, custom_prefix)
        return result
        
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

# Alias per compatibilità
check_megadown_installed = check_megatools_installed

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
