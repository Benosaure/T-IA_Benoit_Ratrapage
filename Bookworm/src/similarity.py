import math
import json
import os
from collections import Counter
#calculateur du tf-idf

_CACHE_DIR = "cache"
_VECTORS_CACHE_FILE = os.path.join(_CACHE_DIR, "tfidf_vectors.json")

_vector_cache: dict[int, dict[str, float]] = {}
_idf_cache: dict[str, float] | None = None
#met en minuscule les token alphabetique
def _tokenize(text: str) -> list[str]:
    import re
    return re.findall(r"\b[a-z]+\b", text.lower())

#calcule la frécance des mots dans le total des mots
def tf(text: str) -> dict[str, float]:
    words = _tokenize(text)
    if not words:
        return {}
    count = Counter(words)
    total = len(words)
    return {w: c / total for w, c in count.items()}

#calcule l'idf qui est la rareté d'un mot dans le document
def idf(corpus: list[str]) -> dict[str, float]:
    global _idf_cache
    if _idf_cache is not None:
        return _idf_cache

    N = len(corpus)
    all_words: set[str] = set()
    for doc in corpus:
        all_words.update(_tokenize(doc))

    idf_dict: dict[str, float] = {}
    for word in all_words:
        df = sum(1 for doc in corpus if word in _tokenize(doc))
        idf_dict[word] = math.log(N / (1 + df))

    _idf_cache = idf_dict
    return idf_dict

#prend la valeur tf d'un texte et met un score au mot dans le texte avec les valeur IDF
#le code va prendre un mot et va calculé la frécance dans le texte TF et le multipli par la rareté IDF pour lui attribué un score
def vectorize(text: str, idf_dict: dict[str, float]) -> dict[str, float]:
    tf_dict = tf(text)
    return {
        word: tf_dict.get(word, 0.0) * idf_dict.get(word, 0.0)
        for word in idf_dict
        if tf_dict.get(word, 0.0) > 0  
    }

#permet de vectoriser deux livre et les comparé pour savoir a quel point les livres ce resemble niveau vocabulaire
#ex: deux livre de sience fiction aurons deux vecteur proche
#on utilise un produit scalaire pour calculé la proximité des deux valeur tf-idf qui sont des vecteur,
#plus la valeur s'approche de 1 plus le livre est similaire
def cosine(v1: dict[str, float], v2: dict[str, float]) -> float:
    """Cosine similarity between two sparse TF-IDF vectors."""
    common_keys = set(v1) & set(v2)
    dot = sum(v1[k] * v2[k] for k in common_keys)

    norm1 = math.sqrt(sum(val ** 2 for val in v1.values()))
    norm2 = math.sqrt(sum(val ** 2 for val in v2.values()))

    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0

    return dot / (norm1 * norm2)

#charge des TF-IDF sauvegarder dans le dossier cache python
def _load_disk_cache() -> dict[str, dict[str, float]]:
    if not os.path.exists(_VECTORS_CACHE_FILE):
        return {}
    try:
        with open(_VECTORS_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

#sauvegarde un TF-IDF dans le cache python
def _save_disk_cache(data: dict[str, dict[str, float]]) -> None:
    os.makedirs(_CACHE_DIR, exist_ok=True)
    with open(_VECTORS_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)

#retourne le vecteur TF-IDF d'un livre
#si il est déjà disponible dans la variable du code python le recupére dans ce dernier, 
#si non appel load_disk pour le recupéré dans le cache
#si le tf-idf n'est pas dans le cache on le vectorise et on le met dnas le cache et la varible
def get_vector(book_id: int, text: str, idf_dict: dict[str, float]) -> dict[str, float]:
    key = str(book_id)

    if book_id in _vector_cache:
        return _vector_cache[book_id]

    disk = _load_disk_cache()
    if key in disk:
        vec = disk[key]
        _vector_cache[book_id] = vec
        return vec

    vec = vectorize(text, idf_dict)
    _vector_cache[book_id] = vec
    disk[key] = vec
    _save_disk_cache(disk)
    return vec

#la fonction qui va calculé la similarité entre deux livre
#verifi si il existe au moin deux livre dans les livres sauvegarder
#sinon si il n'y a que un livre dans le corpus renvoi du vide
#recupére les vecteur tf-idf du livre demander avec get_vector 
#et les compare avec ceux des autres livres 
#utilise cosine pour comparé les tf-idf de chaque livre et stok les book_id avec leur score
#ensuite trie les livre par leur score en ordre décroisent et ne garde que le premier et le retourne
def compute_similarity(
    book_id: int,
    text: str,
    corpus: dict[int, str],
    top_n: int = 5,
) -> list[dict]:
    if len(corpus) < 2:
        return []

    global _idf_cache
    _idf_cache = None

    all_texts = list(corpus.values())
    idf_dict = idf(all_texts)

    ref_vec = get_vector(book_id, text, idf_dict)

    results: list[dict] = []
    for other_id, other_text in corpus.items():
        if other_id == book_id:
            continue
        other_vec = get_vector(other_id, other_text, idf_dict)
        score = cosine(ref_vec, other_vec)
        results.append({"book_id": other_id, "score": round(score, 4)})

    return sorted(results, key=lambda x: x["score"], reverse=True)[:top_n]

#appel compute_similarity et recupére les titres des livre 
#pour afficher a l'utilisateur des données lisible
def similar_titles(
    book_id: int,
    text: str,
    corpus: dict[int, str],
    top_n: int = 5,
) -> list[str]:
    from src.downloader import extract_metadata

    results = compute_similarity(book_id, text, corpus, top_n=top_n)
    titles: list[str] = []
    for r in results:
        other_text = corpus.get(r["book_id"], "")
        meta = extract_metadata(other_text)
        titles.append(meta.get("title", f"book #{r['book_id']}"))
    return titles

#charge tout les .txt d dossier books/
#renvois une liste {book_id: text}
def load_corpus_from_disk(books_dir: str = "books") -> dict[int, str]:
    corpus: dict[int, str] = {}
    if not os.path.isdir(books_dir):
        return corpus
    for filename in os.listdir(books_dir):
        if filename.endswith(".txt"):
            try:
                book_id = int(filename.replace(".txt", ""))
                with open(os.path.join(books_dir, filename), "r", encoding="utf-8") as f:
                    corpus[book_id] = f.read()
            except (ValueError, OSError):
                continue
    return corpus