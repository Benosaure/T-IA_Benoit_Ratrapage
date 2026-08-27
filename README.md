# 📚 Bookworm — NLP Explorer for Project Gutenberg

> Analyse, résume et compare des livres du domaine public via une pipeline NLP complète,
> pour transformer de longs textes bruts en « book cards » compactes et exploitables.

---

## Sommaire

- [Architecture du projet](#architecture-du-projet)
- [Installation](#installation)
- [Utilisation](#utilisation)
- [Pipeline NLP en détail](#pipeline-nlp-en-détail)
  - [Prétraitement](#1-prétraitement--preprocessingpy)
  - [Diversité lexicale](#2-diversité-lexicale--lexdivpy)
  - [Topic modeling](#3-topic-modeling--topicspy)
  - [Reconnaissance d'entités](#4-reconnaissance-dentités--entitiespy)
  - [Résumé extractif](#5-résumé-extractif--summarypy)
  - [Similarité entre livres](#6-similarité-entre-livres--similaritypy)
  - [Book card](#7-book-card--cardpy)
  - [Cache](#8-cache--cachepy)
- [Justification des choix méthodologiques](#justification-des-choix-méthodologiques)
- [Corpus de test recommandé](#corpus-de-test-recommandé)

---

## Architecture du projet

```
Bookworm/
│
├── bookworm.py          # Point d'entrée CLI (argparse, affichage, gestion d'erreurs)
├── test_bookworm.py      # Suite de tests (unitaires + option --live)
├── README.md
├── requirements.txt
│
├── books/                # Textes téléchargés (.txt)               [gitignored]
├── cache/                # Résultats JSON mis en cache              [gitignored]
│
└── src/
    ├── __init__.py
    ├── downloader.py     # Téléchargement & extraction métadonnées Gutenberg
    ├── preprocessing.py  # Nettoyage, tokenisation NLTK, lemmatisation WordNet
    ├── lexdiv.py         # Métriques de diversité lexicale (TTR, hapax, MWL…)
    ├── topics.py         # Extraction de thèmes par TF-IDF sectionné
    ├── entities.py       # NER hybride : spaCy + heuristique d'entités composées
    ├── summary.py        # Résumé extractif par fréquence de mots normalisée
    ├── similarity.py     # Similarité cosinus TF-IDF entre livres + cache
    ├── card.py           # Agrégation complète → fiche livre JSON (cachée)
    └── cache.py          # Persistance JSON générique sur disque (get_or_compute)
```

Chaque module est indépendant et testable isolément (voir `test_bookworm.py`), et
`bookworm.py` ne fait qu'orchestrer des appels vers `src/`.

---

## Installation

```bash
git clone <repo>
cd Bookworm
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m nltk.downloader punkt punkt_tab stopwords wordnet
```
Le venv doit être réactivé (`source .venv/bin/activate`) à chaque nouvelle session de terminal avant de lancer `bookworm.py`.
Le modèle spaCy anglais léger (`en_core_web_sm`, ~12 Mo, pas un LLM) est déclaré
directement dans `requirements.txt` et s'installe avec la commande ci-dessus.

**Vérifier l'installation :**

```bash
python test_bookworm.py          # tests unitaires (aucun réseau requis)
python test_bookworm.py --live   # + test de téléchargement réel (book #11)
```

---

## Utilisation

```bash
python bookworm.py --download  <ID>   # Télécharge et met en cache le livre
python bookworm.py --lexdiv    <ID>   # Métriques de diversité lexicale
python bookworm.py --topics    <ID>   # Thèmes TF-IDF (top 10 mots / section)
python bookworm.py --entities  <ID>   # Personnages, lieux, entités composées
python bookworm.py --summarize <ID>   # Résumé extractif (quelques phrases)
python bookworm.py --similar   <ID>   # 5 livres les plus proches (titres)
python bookworm.py --card      <ID>   # Fiche complète (toutes les features)
python bookworm.py --card      <ID> --raw   # Idem, en JSON brut (sans mise en forme)
```

`<ID>` est l'identifiant du livre sur [Project Gutenberg](https://www.gutenberg.org/)
(ex. `11` pour *Alice's Adventures in Wonderland*).

> **Note :** `--similar` nécessite au moins 2 livres présents dans `books/`
> (téléchargez-en plusieurs au préalable avec `--download`).

---

## Pipeline NLP en détail

```
[ Project Gutenberg ]
        │
        ▼
  downloader.py       ← télécharge le .txt brut, le sauvegarde dans books/<id>.txt,
                          extrait titre / auteur(s) / catégorie par regex
        │
        ▼
  preprocessing.py    ← remove_gutenberg_metadata()  : coupe l'en-tête / le pied de
                          page légal Gutenberg
                        basic_clean()                : minuscule, retrait [notes],
                          normalisation des espaces
                        word_tokenize() (NLTK)        : tokenisation
                        remove_non_words()            : ne garde que l'alphabétique
                        remove_stopwords() (NLTK)     : retrait des mots vides
                        lemmatize() (WordNetLemmatizer): réduction à la forme canonique
        │
        ├──▶ lexdiv.py      → TTR, hapax, longueur moyenne des mots (MWL), MWF
        ├──▶ topics.py      → TF-IDF par section narrative (4 sections égales)
        ├──▶ entities.py    → personnages, lieux, entités composées (texte brut)
        ├──▶ summary.py     → résumé extractif (fréquence de mots normalisée)
        └──▶ similarity.py  → vecteurs TF-IDF + cosinus sur tout le corpus local
                │
                ▼
            card.py         → fiche JSON complète (mise en cache sur disque)
```

### 1. Prétraitement — `preprocessing.py`

- **`remove_gutenberg_metadata`** : isole le corps du livre entre les marqueurs
  `*** START OF ... ***` et `*** END OF ... ***`, pour ne jamais analyser le
  boilerplate légal de Gutenberg.
- **`basic_clean`** : mise en minuscule, retrait des annotations entre crochets
  (ex. `[Illustration]`), normalisation des espaces multiples.
- **`tokenize`** : `nltk.word_tokenize`.
- **`remove_non_words`** : ne garde que les tokens purement alphabétiques
  (retire ponctuation, nombres, tirets isolés…).
- **`remove_stopwords`** : retire les mots vides anglais (corpus NLTK).
- **`lemmatize`** : `WordNetLemmatizer`, pour regrouper les variantes
  flexionnelles d'un même mot (*running* → *running* / *ran* → *ran*,
  limité au lemmatiseur de base sans étiquetage POS — voir Limites).

Cette pipeline alimente `lexdiv.py` et `topics.py` (qui ont besoin d'une liste
de tokens nettoyés). `entities.py` et `summary.py` travaillent en revanche sur
le **texte brut** (juste débarrassé du boilerplate Gutenberg), car la casse et
la ponctuation sont indispensables pour la NER et le découpage en phrases.

### 2. Diversité lexicale — `lexdiv.py`

Calcule, pour la liste de tokens prétraités, un dictionnaire :

```json
{
  "tok": 26447,   // nombre total de tokens
  "typ": 2731,    // nombre de tokens uniques (vocabulaire)
  "hap": 1123,    // hapax : mots n'apparaissant qu'une seule fois
  "ttr": 0.1033,  // Type-Token Ratio = typ / tok
  "mwl": 4.312,   // longueur moyenne des mots (Mean Word Length), en caractères
  "mwf": 9.684    // Mean Word Frequency = tok / typ (inverse du TTR)
}
```

Le TTR est une mesure classique mais dépend fortement de la longueur du texte
(il diminue mécaniquement pour les textes longs) — c'est une limite connue,
mentionnée plus bas.

### 3. Topic modeling — `topics.py`

Le livre est découpé en **4 sections narratives** de taille égale
(`split_into_sections`), puis un score **TF-IDF sectionné** est calculé :

```
TF(w, section)  = count(w, section) / |section|
IDF(w)          = log( N_sections / (1 + df(w)) )
score(w)        = TF(w, section) × IDF(w)
```

Pour chaque section, les **10 mots** au score le plus élevé sont renvoyés :

```json
{ "1": [...10 mots...], "2": [...], "3": [...], "4": [...] }
```

L'IDF est calculé *entre les sections d'un même livre* (et non entre plusieurs
livres) : l'objectif est de repérer les mots qui **caractérisent une section
donnée par rapport aux autres**, révélant ainsi la progression thématique du
récit (ex. section 1 = mise en place, section 4 = dénouement).

### 4. Reconnaissance d'entités — `entities.py`

Approche **hybride**, pour rester légère tout en couvrant les entités
multi-mots que les petits modèles NER manquent souvent :

1. **spaCy (`en_core_web_sm`)** identifie les entités `PERSON` → `characters`,
   et `GPE`/`LOC`/`FAC` → `locations`.
2. Une **heuristique de capitalisation** repère en plus les **entités
   composées** (`compounds`) : suites de mots démarrant par une majuscule,
   avec liaisons autorisées (`of`, `the`) pour capter des noms comme
   *"Queen of Hearts"*. La détection s'arrête toujours à une fin de phrase ou
   de ligne, pour ne jamais fusionner deux entités appartenant à des
   contextes différents.
3. Le bruit typique du boilerplate Gutenberg (mots tout en majuscules type
   `GUTENBERG`, `PROJECT`, `LICENSE`, `FOUNDATION`…) est filtré des trois
   listes.

```json
{
  "characters": ["Alice", ...],
  "locations":  ["Wonderland", ...],
  "compounds":  ["White Rabbit", "Mad Hatter", "Queen of Hearts", ...]
}
```

### 5. Résumé extractif — `summary.py`

**Méthode retenue : extractive, par fréquence de mots normalisée**
(proche de l'algorithme historique de Luhn) :

1. Découpage du texte en phrases (regex sur `. ! ?`).
2. Calcul de la fréquence de chaque mot significatif (hors stop-words),
   normalisée par la fréquence maximale : `freq(w) = count(w) / max(count)`.
3. Score de chaque phrase = moyenne des fréquences de ses mots.
4. Les *N* phrases au score le plus élevé sont sélectionnées, puis
   **réordonnées selon leur position d'origine** dans le texte, pour préserver
   la cohérence narrative du résumé final.

**Pourquoi ce choix ?**
- *Rapide et déterministe* : pas d'entraînement, pas de modèle à charger,
  complexité proche de O(n).
- *Aucune dépendance lourde* : respecte la contrainte "pas de gros modèle".
- *Facile à expliquer et déboguer* : chaque phrase du résumé est une phrase
  du texte original (pas d'hallucination possible, contrairement à une
  approche abstractive).

**Limites :**
- Résumé purement lexical, insensible à la cohérence narrative globale
  (une méthode par graphe comme **TextRank** capturerait mieux les relations
  entre phrases).
- Les phrases très courtes ou très longues peuvent être sur/sous-valorisées
  (le score n'est pas pondéré par la position ni la longueur).

**Alternatives envisagées :**
- *TextRank* (graphe de similarité inter-phrases + PageRank) : meilleure
  cohérence, mais plus coûteux (calcul de similarité n×n) et plus complexe
  à justifier/débugger dans le temps imparti.
- *Résumé abstractif (T5/BART "small")* : explicitement écarté car il s'agit
  de modèles transformers, exclus par le cahier des charges ("heavy models…
  are NOT allowed").

### 6. Similarité entre livres — `similarity.py`

**TF-IDF + similarité cosinus**, calculée sur l'ensemble du corpus local
(`books/`) :

```
TF(w, d)       = count(w, d) / |d|
IDF(w)         = log( N / (1 + df(w)) )          -- calculé sur tout le corpus
TF-IDF(w, d)   = TF(w, d) × IDF(w)
cosine(v1, v2) = (v1 · v2) / (||v1|| × ||v2||)
```

- `cosine = 1.0` pour deux documents identiques, `0.0` s'ils ne partagent
  aucun mot.
- Les vecteurs TF-IDF sont mis en cache **en mémoire** (session) et **sur
  disque** (`cache/tfidf_vectors.json`), pour éviter tout recalcul entre deux
  exécutions.
- `compute_similarity(book_id, text, corpus, top_n)` renvoie les résultats
  bruts `[{"book_id": int, "score": float}, ...]` (utile pour les tests et le
  debug interne).
- `similar_titles(book_id, text, corpus, top_n)` résout ces `book_id` en
  **titres** via les métadonnées Gutenberg, pour renvoyer exactement le format
  attendu par la CLI : `["title1", ..., "title5"]`, trié par similarité
  décroissante.

### 7. Book card — `card.py`

Agrège toutes les features précédentes dans une fiche unique :

```json
{
  "info":     {"id": "11", "title": "...", "authors": "...", "bookshelves": "..."},
  "lexdiv":   {"tok": ..., "typ": ..., "hap": ..., "ttr": ..., "mwl": ..., "mwf": ...},
  "topics":   {"1": [...], "2": [...], "3": [...], "4": [...]},
  "entities": {"characters": [...], "locations": [...], "compounds": [...]},
  "summary":  "...",
  "similar":  ["title1", "title2", "title3", "title4", "title5"]
}
```

Le calcul complet est coûteux (NER + TF-IDF sur tout le corpus), il est donc
mis en cache dans `cache/card_<id>.json` via `get_or_compute`.

### 8. Cache — `cache.py`

Utilitaire générique `get_or_compute(key, compute_fn)` : renvoie le résultat
en cache s'il existe, sinon exécute `compute_fn`, sauvegarde le résultat en
JSON indenté dans `cache/<key>.json`, puis le renvoie. Utilisé par `card.py`
et par `similarity.py` pour les vecteurs TF-IDF.

---

## Justification des choix méthodologiques

| Tâche | Choix retenu | Pourquoi | Alternative envisagée |
|---|---|---|---|
| Tokenisation / lemmatisation | NLTK (`word_tokenize`, `WordNetLemmatizer`) | Rapide, sans dépendance lourde, standard pour de l'anglais | spaCy pour tout le pipeline (plus lent, redondant avec NLTK) |
| Topics | TF-IDF sectionné | Simple, interprétable, aucun entraînement | LDA/LSA (bonus listé, plus coûteux et plus difficile à interpréter pour un non-expert) |
| Entités | spaCy `en_core_web_sm` + heuristique de casse | Modèle NER léger + comble ses angles morts sur les entités composées inhabituelles ("White Rabbit") | Modèle NER plus gros (`en_core_web_trf`) : trop lourd, transformer interdit |
| Résumé | Extractif, fréquence normalisée | Rapide, déterministe, pas d'hallucination | TextRank (plus coûteux), abstractif (interdit : modèle lourd) |
| Similarité | TF-IDF + cosinus | Standard, rapide, vecteurs cachables sur disque | `sentence-transformers` (bonus listé, sémantique mais modèle plus lourd) |

---

## Corpus de test recommandé

D'après le brief, le corpus suivant permet de tester `--similar` de façon
pertinente (plusieurs livres par catégorie) :

| ID | Titre | Catégorie |
|----|-------|-----------|
| 11 | Alice's Adventures in Wonderland | Children / Young Adult |
| 12 | Through the Looking-Glass | Children / Young Adult |
| 16 | Peter Pan | Children / Young Adult |
| 55 | The Wonderful Wizard of Oz | Children / Young Adult |
| 113 | The Secret Garden | Children / Young Adult |
| 120 | Treasure Island | Children / Young Adult |
| 236 | The Jungle Book | Children / Young Adult |
| 108 | The Return of Sherlock Holmes | Crime, Mystery & Thriller |
| 834 | The Memoirs of Sherlock Holmes | Crime, Mystery & Thriller |
| 863 | The Mysterious Affair at Styles | Crime, Mystery & Thriller |
| 1661 | The Adventures of Sherlock Holmes | Crime, Mystery & Thriller |
| 61262 | Poirot Investigates | Crime, Mystery & Thriller |
| 69087 | The Murder of Roger Ackroyd | Crime, Mystery & Thriller |
| 70114 | The Big Four | Crime, Mystery & Thriller |
| 35 | The Time Machine | Science-Fiction & Fantasy |
| 36 | The War of the Worlds | Science-Fiction & Fantasy |
| 84 | Frankenstein | Science-Fiction & Fantasy |
| 159 | The Island of Doctor Moreau | Science-Fiction & Fantasy |
| 164 | Twenty Thousand Leagues under the Sea | Science-Fiction & Fantasy |
| 345 | Dracula | Science-Fiction & Fantasy |
| 68283 | The Call of Cthulhu | Science-Fiction & Fantasy |

```bash
for id in 11 12 16 55 113 120 236; do python bookworm.py --download $id; done
python bookworm.py --similar 11
```

---
