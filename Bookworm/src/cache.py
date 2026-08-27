import os
import json

CACHE_DIR = "cache"

#récupère le path pour le .json de cache
def _get_path(key):
    return os.path.join(CACHE_DIR, f"{key}.json")

#ouvre en édition le .json du cache
def load_cache(key):
    path = _get_path(key)

    if not os.path.exists(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

#insére les donnée dans le json
def save_cache(key, data):
    os.makedirs(CACHE_DIR, exist_ok=True)

    path = _get_path(key)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

#verifi si le cache existe
#si oui sauvegarde le contenu
#si non le crée avec les donnée mis dans la fonction
def get_or_compute(key, compute_fn):

    cached = load_cache(key)

    if cached is not None:
        return cached

    result = compute_fn()

    save_cache(key, result)

    return result