from collections import Counter
import math

# découpe le livre en 4 aprtie, le début , la naration, le coeur du livre la fin du livre
def split_into_sections(tokens, n_sections=4):
    size = max(1, len(tokens) // n_sections)

    sections = [
        tokens[i * size:(i + 1) * size]
        for i in range(n_sections)
    ]

    remaining = tokens[n_sections * size:]

    if remaining:
        sections[-1].extend(remaining)

    return sections

#la fréquance de chaque mot dans les diférantes sections
def compute_tf(section):
    counter = Counter(section)
    total = len(section)

    if total == 0:
        return {}

    return {
        word: count / total
        for word, count in counter.items()
    }

#retires des point au mots dans toutes les section pour bien découper les mot important des sections
# ca permet d'isolé les mot important de la sections
def compute_idf(sections):
    N = len(sections)
    idf = {}

    all_tokens = set(
        token for section in sections for token in set(section)
    )

    for token in all_tokens:
        containing = sum(1 for section in sections if token in section)
        idf[token] = math.log(N / (1 + containing))

    return idf

#renvois les 10mots les plus utilisé de chaques sections
def extract_topics(tokens, n_sections=4, top_n=10):

    sections = split_into_sections(tokens, n_sections)

    idf = compute_idf(sections)

    topics = {}

    for i, section in enumerate(sections, start=1):

        tf = compute_tf(section)

        scores = {}

        for word, tf_value in tf.items():
            scores[word] = tf_value * idf.get(word, 0)

        top_words = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]

        topics[i] = [word for word, _ in top_words]

    return topics