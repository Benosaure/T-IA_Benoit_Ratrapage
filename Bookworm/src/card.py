from src.preprocessing import preprocess
from src.lexdiv import lexical_diversity
from src.topics import extract_topics
from src.entities import extract_entities
from src.downloader import extract_metadata
from src.cache import get_or_compute
from src.summary import extract_summary
from src.similarity import similar_titles, load_corpus_from_disk

# appel les fonction des autres fichier python pour les executé et recupéré les donnée et crée une book card avec les données reçu
def build_card(book_id: int, text: str) -> dict:

    def compute() -> dict:
        tokens   = preprocess(text)
        metadata = extract_metadata(text)

        corpus = load_corpus_from_disk()
        corpus[book_id] = text
        similar = similar_titles(book_id, text, corpus, top_n=5)

        return {
            "info": {
                "id":          str(book_id),
                "title":       metadata["title"],
                "authors":     metadata["authors"],
                "bookshelves": metadata["bookshelves"],
            },
            "lexdiv":   lexical_diversity(tokens),
            "topics":   extract_topics(tokens),
            "entities": extract_entities(text),
            "summary":  extract_summary(text, max_sentences=5),
            "similar":  similar,
        }

    return get_or_compute(f"card_{book_id}", compute)