
#entities.py — Reconnaissance d'entités nommées (NER) pour Bookworm.
#
#Approche hybride :
#  1. spaCy (en_core_web_sm) pour les entités PERSON / GPE / LOC / FAC
#     -> alimente "characters" et "locations".
#  2. Un post-traitement heuristique (séquences de mots capitalisés,
#     avec liaisons "of"/"the" autorisées : "Queen of Hearts") détecte
#     les entités composées ("White Rabbit", "Mad Hatter"...) que le
#     petit modèle spaCy manque souvent -> alimente "compounds".
#
#Le bruit provenant de l'en-tête / pied de page Project Gutenberg
#(mots tout en majuscules type "GUTENBERG", "PROJECT", "LICENSE"...)
#est filtré des trois listes.


import re
from collections import Counter

import spacy

nlp = spacy.load("en_core_web_sm")

# Mots-clés typiques du boilerplate Project Gutenberg à exclure des résultats.
_GUTENBERG_NOISE = {
    "gutenberg", "project", "foundation", "license", "ebook", "etext",
    "trademark", "archive",
}

# Mots de tête à retirer d'un groupe capitalisé ("The Mad Hatter" -> "Mad Hatter").
_LEADING_DROP = {
    "the", "a", "an", "this", "that", "these", "those", "so", "but",
    "and", "oh", "there", "when", "if", "it", "as", "for", "he", "she",
}

# Mots de liaison autorisés à l'intérieur d'une entité composée
# ("Queen of Hearts", "King of the Hill"...).
_GLUE_WORDS = {"of", "the"}

# Un "mot capitalisé" au sens strict : Majuscule + minuscules (exclut les
# mots TOUT EN MAJUSCULES du boilerplate Gutenberg).
_CAP_WORD_RE = re.compile(r"^[A-Z][a-z]+$")
_TOKEN_RE = re.compile(r"[A-Za-z']+")

#retire les mot parasite comme: "Gutenberg", "Project", "Foundation", "License"
def _is_noise(word: str) -> bool:
    return word.lower().strip("'s") in _GUTENBERG_NOISE

#defini tout ce qui est le texte au debut avent le livre
_GUTENBERG_START_RE = re.compile(r"\*\*\*\s*START OF.*?\*\*\*", re.IGNORECASE | re.DOTALL)
#defini tout ce qui est le texte a la fin apré le livre
_GUTENBERG_END_RE = re.compile(r"\*\*\*\s*END OF.*", re.IGNORECASE | re.DOTALL)

#utilise les présédante variable pour retiré l'entéte et fin du texte avec les mentions légales pour ne retourné que le texte du livre
def _strip_gutenberg_boilerplate(text: str) -> str:
    match = _GUTENBERG_START_RE.search(text)
    if match:
        text = text[match.end():]
    text = _GUTENBERG_END_RE.sub("", text)
    return text.strip()

#expretion régulière pour détecter les . ? !
_SENTENCE_BREAK_RE = re.compile(r"[.!?\n]")

#une fonction qui essaye de récupéré dans le texte les entité composé
#losque un mot commence par une majuscule suivi de minuscule le code lis la suite et cherche si le prochain mot est pareille
#si oui continu jusqua ne plus en trouver et si au moin deux mot on été trouver de cette manière sauvegarde le tout en temp que mot composé
#regarde aussi si des mots de ponctuation suivent le premier mot par exemple : the, of
# exemple : Queen of Hearts, White Rabbit
#il ne faut pas que une ponctuation de fin de phrase ( . ! ?) ne vienne intérféré car cela voudrais dire que la suite fait partie d'une autre phrase
def _extract_compounds(text: str) -> list[str]:
    matches = list(_TOKEN_RE.finditer(text))
    counter: Counter = Counter()
    n = len(matches)
    i = 0

    def _gap_breaks_sentence(end, start):
        return bool(_SENTENCE_BREAK_RE.search(text, end, start))

    while i < n:
        tok = matches[i].group()
        if _CAP_WORD_RE.match(tok):
            run = [tok]
            prev_end = matches[i].end()
            j = i + 1
            while j < n:
                nxt = matches[j].group()
                gap_breaks = _gap_breaks_sentence(prev_end, matches[j].start())
                if not gap_breaks and _CAP_WORD_RE.match(nxt):
                    run.append(nxt)
                    prev_end = matches[j].end()
                    j += 1
                elif (
                    not gap_breaks
                    and nxt.lower() in _GLUE_WORDS
                    and j + 1 < n
                    and _CAP_WORD_RE.match(matches[j + 1].group())
                    and not _gap_breaks_sentence(matches[j].end(), matches[j + 1].start())
                ):
                    run.append(nxt.lower())
                    run.append(matches[j + 1].group())
                    prev_end = matches[j + 1].end()
                    j += 2
                else:
                    break

            while run and run[0].lower() in _LEADING_DROP:
                run = run[1:]
            while run and run[-1].lower() in _GLUE_WORDS:
                run = run[:-1]

            cap_words = [w for w in run if w[0].isupper()]
            if len(cap_words) >= 2 and not any(_is_noise(w) for w in run):
                counter[" ".join(run)] += 1

            i = j
        else:
            i += 1

    return sorted(counter.keys())

#utilise spacy pour extraire les lieu, les entités et les presonage du texte
def extract_entities(text: str, min_frequency: int = 1) -> dict:

    text = _strip_gutenberg_boilerplate(text)
    doc = nlp(text)

    characters: Counter = Counter()
    locations: Counter = Counter()

    for ent in doc.ents:
        name = ent.text.strip()

        # On ignore le bruit Gutenberg (mots tout en majuscules, etc.)
        if not name or name.isupper() or _is_noise(name):
            continue

        if ent.label_ == "PERSON":
            characters[name] += 1
        elif ent.label_ in {"GPE", "LOC", "FAC"}:
            locations[name] += 1

    compounds = _extract_compounds(text)

    return {
        "characters": sorted(
            name for name, count in characters.items() if count >= min_frequency
        ),
        "locations": sorted(
            place for place, count in locations.items() if count >= min_frequency
        ),
        "compounds": compounds,
    }
