import os
import re
import subprocess
from datetime import datetime
import shutil
from salvataggio import build_path, safe_name
from deduplica import deduplica_file

def extract_mega_info(mega_url):
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
    except Exception as e:
        print(f"Errore estrazione info Mega: {e}")
        return None, None, None

def sanitize_filename(filename):
    try:
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename
    except Exception as e:
        print(f"Errore sanitizzazione filename: {e}")
        return filename

def check_megatools_installed():
    try:
        return get_megadl_command() is not None
    except Exception as e:
        print(f"Errore verifica megatools: {e}")
        return False

def get_megadl_command():
    possible_paths = ['megadl', '/usr/bin/megadl', '/usr/local/bin/megadl']
    for path in possible_paths:
        try:
            result = subprocess.run([path, '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                return path
        except Exception as e:
            continue
    return None

def download_with_megatools(mega_url, save_dir, custom_prefix=None):
    try:
        megadl_cmd = get_megadl_command()
        if not megadl_cmd:
            print("megatools non trovato nel sistema")
            return []
        os.makedirs(save_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        prefix = custom_prefix or "mega"
        temp_dir = build_path(save_dir, 'Mega', prefix, timestamp, "temp")
        os.makedirs(temp_dir, exist_ok=True)
        cmd = [megadl_cmd, '--path', temp_dir, mega_url]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        except subprocess.TimeoutExpired:
            print("Timeout durante il download Mega")
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            return []
        downloaded_files = []
        if result.returncode == 0:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    try:
                        src_path = os.path.join(root, file)
                        rel_path = os.path.relpath(src_path, temp_dir)
                        sanitized_name = safe_name(rel_path)
                        filename = f"{prefix}_{timestamp}_{sanitized_name}"
                        final_path = build_path(save_dir, 'Mega', prefix, timestamp, filename)
                        os.makedirs(os.path.dirname(final_path), exist_ok=True)
                        shutil.move(src_path, final_path)
                        if deduplica_file(final_path, save_dir):
                            downloaded_files.append(final_path)
                    except Exception as e:
                        print(f"Errore spostamento file Mega: {e}")
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            return downloaded_files
        else:
            print(f"Errore megatools: {result.stderr}")
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            return []
    except Exception as e:
        print(f"Errore durante il download con megatools: {e}")
        return []

def download_mega_auto(mega_url, save_dir, custom_prefix=None, preserve_structure=True):
    try:
        return download_with_megatools(mega_url, save_dir, custom_prefix)
    except Exception as e:
        print(f"Errore nell'auto-download Mega: {e}")
        return []

def is_mega_link(url):
    try:
        mega_pattern = r"https?://mega\.nz/(file|folder)/[^#]+#.+"
        return bool(re.match(mega_pattern, url))
    except Exception as e:
        print(f"Errore verifica link Mega: {e}")
        return False
