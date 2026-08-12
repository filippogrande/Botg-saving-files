import json
import os

def _map_path():
    save_dir = os.environ.get("SAVE_DIR", "/mnt/truenas-bot")
    return os.path.join(save_dir, "actor_map.json")

def load_actor_map():
    try:
        with open(_map_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []

def save_actor_map(mapping_list):
    with open(_map_path(), "w", encoding="utf-8") as f:
        json.dump(mapping_list, f, indent=2, ensure_ascii=False)

def is_mapped(platform, username):
    username = (username or "").strip()
    if not username:
        return False
    key = platform.lower()
    for entry in load_actor_map():
        if entry.get(key, "").strip().lower() == username.lower():
            return True
    return False

def resolve_actor(platform, username):
    username = (username or "").strip()
    if not username:
        return username
    key = platform.lower()
    for entry in load_actor_map():
        if entry.get(key, "").strip().lower() == username.lower():
            return entry.get("actor", username)
    return username

def add_actor_mapping(actor, reddit=None, redgifs=None):
    actor = (actor or "").strip()
    mapping = load_actor_map()
    for e in mapping:
        if e.get("actor", "").strip().lower() == actor.lower():
            if reddit is not None:
                e["reddit"] = reddit
            if redgifs is not None:
                e["redgifs"] = redgifs
            save_actor_map(mapping)
            return e, "merged"
    mapping.append({"actor": actor, "reddit": reddit or "", "redgifs": redgifs or ""})
    save_actor_map(mapping)
    return mapping[-1], "added"

def update_actor_mapping(identifier, actor=None, reddit=None, redgifs=None):
    mapping = load_actor_map()
    if isinstance(identifier, str) and identifier.isdigit():
        idx = int(identifier) - 1
    else:
        idx = None
        for j, e in enumerate(mapping):
            if e.get("actor", "").strip().lower() == str(identifier).strip().lower():
                idx = j
                break
    if idx is None or not (0 <= idx < len(mapping)):
        return None, "not_found"
    e = mapping[idx]
    if actor is not None:
        e["actor"] = actor.strip()
    if reddit is not None:
        e["reddit"] = reddit.strip()
    if redgifs is not None:
        e["redgifs"] = redgifs.strip()
    save_actor_map(mapping)
    return e, "updated"

def remove_actor_mapping(identifier):
    mapping = load_actor_map()
    if isinstance(identifier, str) and identifier.isdigit():
        idx = int(identifier) - 1
    else:
        idx = None
        for j, e in enumerate(mapping):
            if e.get("actor", "").strip().lower() == str(identifier).strip().lower():
                idx = j
                break
    if idx is None or not (0 <= idx < len(mapping)):
        return False
    mapping.pop(idx)
    save_actor_map(mapping)
    return True

def list_actor_mappings():
    return load_actor_map()