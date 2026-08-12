"""Report sull'attore risolto a partire dai path salvati."""
def _actor_from_path(path):
    parts = path.replace("\\", "/").split("/")
    if "autodownloader" in parts:
        i = parts.index("autodownloader")
        if i + 2 < len(parts):
            # parts[i+1] = sorgente (reddit/redgifs), parts[i+2] = attore
            return parts[i + 1], parts[i + 2]
    return None, None

def format_actor_report_from_paths(result):
    from actor_map import list_actor_mappings
    mappings = list_actor_mappings()
    actor_names = {e.get("actor", "").lower(): e.get("actor")
                   for e in mappings if e.get("actor")}
    found = {}
    for p in (result or []):
        if not isinstance(p, str):
            continue
        _, actor = _actor_from_path(p)
        if actor:
            found[actor] = True
    if not found:
        return None
    lines = []
    for actor in found:
        al = actor.lower()
        if al in actor_names:
            lines.append(f"attore: {actor_names[al]}")
        else:
            lines.append(f"attore: sconosciuto ({actor})")
    return "\n".join(lines)