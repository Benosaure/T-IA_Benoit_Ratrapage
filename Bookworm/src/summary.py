import re
from collections import Counter

_STOPWORDS = {
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your",
    "yours", "yourself", "yourselves", "he", "him", "his", "himself", "she",
    "her", "hers", "herself", "it", "its", "itself", "they", "them", "their",
    "theirs", "themselves", "what", "which", "who", "whom", "this", "that",
    "these", "those", "am", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "having", "do", "does", "did", "doing", "a", "an",
    "the", "and", "but", "if", "or", "because", "as", "until", "while", "of",
    "at", "by", "for", "with", "about", "against", "between", "into", "through",
    "during", "before", "after", "above", "below", "to", "from", "up", "down",
    "in", "out", "on", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "both",
    "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "so", "than", "too", "very", "s", "t", "can", "will",
    "just", "don", "should", "now", "d", "ll", "m", "o", "re", "ve", "y",
    "ain", "couldn", "didn", "doesn", "hadn", "hasn", "haven", "isn", "let",
    "mustn", "shan", "shouldn", "wasn", "weren", "won", "wouldn",
}

_SENTENCE_RE = re.compile(r'(?<=[.!?])\s+')

_GUTENBERG_START_RE = re.compile(r"\*\*\*\s*START OF.*?\*\*\*", re.IGNORECASE | re.DOTALL)
_GUTENBERG_END_RE = re.compile(r"\*\*\*\s*END OF.*", re.IGNORECASE | re.DOTALL)

#retire le boilerplate du texte
#texte legale 
def _strip_gutenberg_boilerplate(text: str) -> str:
    text = _GUTENBERG_START_RE.sub("", text)
    text = _GUTENBERG_END_RE.sub("", text)
    return text.strip()

#decoupe le texte en phrase 
def split_sentences(text: str) -> list[str]:
    text = _strip_gutenberg_boilerplate(text)
    raw = _SENTENCE_RE.split(text.strip())
    return [s.strip() for s in raw if s.strip()]

#met les ot en minuscules, retire la ponctuation, et les stopwords
def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"\b[a-zA-Z]+\b", text.lower())
    return [t for t in tokens if t not in _STOPWORDS]

#retourne la fréquance des mot normalisé sans les stopword
def _word_frequencies(text: str) -> dict[str, float]:
    counts = Counter(_tokenize(text))
    if not counts:
        return {}
    max_freq = max(counts.values())
    return {word: freq / max_freq for word, freq in counts.items()}

#Attribuez un score à une phrase en faisant la moyenne de la fréquence de ses mots sans stopword
def sentence_score(sentence: str, freq: dict[str, float]) -> float:
    words = _tokenize(sentence)
    if not words:
        return 0.0
    return sum(freq.get(w, 0.0) for w in words) / len(words)

#Renvoie un résumé de *max_sentences* phrases dans leur ordre d'origine. 
#Les phrases sont classées selon un score de fréquence des mots ; les N premières sont conservées et
#réassemblées dans l'ordre de leur apparition dans le texte source.
def extract_summary(text: str, max_sentences: int = 3) -> str:
    text = _strip_gutenberg_boilerplate(text)
    sentences = split_sentences(text)
    if not sentences:
        return ""
    if len(sentences) <= max_sentences:
        return " ".join(sentences)

    freq = _word_frequencies(text)
    scored = [(i, sentence_score(s, freq)) for i, s in enumerate(sentences)]
    top_indices = sorted(
        i for i, _ in sorted(scored, key=lambda x: x[1], reverse=True)[:max_sentences]
    )
    return " ".join(sentences[i] for i in top_indices)

def summarize(text: str, num_sentences: int = 5) -> str:
    return extract_summary(text, max_sentences=num_sentences)

if __name__ == "__main__":
    sample = """
    Alice was beginning to get very tired of sitting by her sister.
    Suddenly a White Rabbit ran past her.
    She followed it down the rabbit hole.
    """
    print(extract_summary(sample))