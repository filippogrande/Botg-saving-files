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
    # Scarta entry completamente vuote
    cleaned = [e for e in mapping_list
               if any((e.get(k, "") or "").strip() for k in ("actor", "reddit", "redgifs"))]
    with open(_map_path(), "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2, ensure_ascii=False)

def _norm(v):
    return (v or "").strip().lower()

def _find_existing(actor=None, reddit=None, redgifs=None):
    """Indice della prima entry che matcha su UNA QUALSIASI colonna popolata (case-insensitive)."""
    mapping = load_actor_map()
    for i, e in enumerate(mapping):
        if actor and _norm(e.get("actor")) == _norm(actor):
            return i
        if reddit and _norm(e.get("reddit")) == _norm(reddit):
            return i
        if redgifs and _norm(e.get("redgifs")) == _norm(redgifs):
            return i
    return None

def add_actor_mapping(actor, reddit=None, redgifs=None):
    """Aggiunge, oppure fa MERGE in una entry esistente (match su qualsiasi colonna popolata).
    Risultato: uno username non finisce mai su due attori -> le 3 colonne restano univoche."""
    actor = (actor or "").strip()
    reddit = (reddit or "").strip()
    redgifs = (redgifs or "").strip()
    idx = _find_existing(actor or None, reddit or None, redgifs or None)
    mapping = load_actor_map()
    if idx is not None:
        e = mapping[idx]
        if actor:
            e["actor"] = actor
        if reddit:
            e["reddit"] = reddit
        if redgifs:
            e["redgifs"] = redgifs
        save_actor_map(mapping)
        return e, "merged"
    mapping.append({"actor": actor, "reddit": reddit, "redgifs": redgifs})
    save_actor_map(mapping)
    return mapping[-1], "added"

def _resolve_index(identifier, mapping):
    if isinstance(identifier, int):
        i = identifier - 1
    elif isinstance(identifier, str) and identifier.isdigit():
        i = int(identifier) - 1
    else:
        for j, e in enumerate(mapping):
            if _norm(e.get("actor")) == _norm(identifier):
                return j
        return None
    return i if 0 <= i < len(mapping) else None

def update_actor_mapping(identifier, actor=None, reddit=None, redgifs=None):
    """identifier: indice 1-based o nome attore. Corregge i campi di una entry esistente."""
    mapping = load_actor_map()
    idx = _resolve_index(identifier, mapping)
    if idx is None:
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
    idx = _resolve_index(identifier, mapping)
    if idx is None:
        return False
    mapping.pop(idx)
    save_actor_map(mapping)
    return True

def list_actor_mappings():
    return load_actor_map()

def resolve_actor(platform, username):
    username = (username or "").strip()
    if not username:
        return username
    key = platform.lower()
    for entry in load_actor_map():
        if _norm(entry.get(key)) == _norm(username):
            return entry.get("actor", username)
    return username