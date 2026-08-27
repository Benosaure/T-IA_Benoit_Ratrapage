#test_bookworm.py — Validation des commandes Bookworm.
#
#Lance tous les modules en isolation avec un texte de test
#(pas de téléchargement réseau requis pour la plupart des tests).
#
#Usage :
#    python test_bookworm.py
#    python test_bookworm.py --live   # inclut un vrai téléchargement (book #11)


import sys
import os
import json
import argparse

sys.path.insert(0, os.path.dirname(__file__))

PASS = "✔"
FAIL = "✘"
SKIP = "–"

results: list[tuple[str, str, str]] = []


def test(name: str, fn):
    try:
        fn()
        results.append((PASS, name, ""))
        print(f"  {PASS}  {name}")
    except Exception as e:
        results.append((FAIL, name, str(e)))
        print(f"  {FAIL}  {name}")
        print(f"       {e}")


SAMPLE = """
*** START OF THE PROJECT GUTENBERG EBOOK ALICE'S ADVENTURES IN WONDERLAND ***

Alice was beginning to get very tired of sitting by her sister on the bank,
and of having nothing to do: once or twice she had peeped into the book her
sister was reading, but it had no pictures or conversations in it, and what
is the use of a book, thought Alice, without pictures or conversations?

So she was considering in her own mind (as well as she could, for the hot
day made her feel very sleepy and stupid), whether the pleasure of making a
daisy-chain would be worth the trouble of getting up and picking the daisies,
when suddenly a White Rabbit with pink eyes ran close by her.

There was nothing so VERY remarkable in that; nor did Alice think it so VERY
much out of the way to hear the Rabbit say to itself, "Oh dear! Oh dear! I
shall be late!" (when she thought it over afterwards, it occurred to her that
she ought to have wondered at this, but at the time it all seemed quite
natural); but when the Rabbit actually TOOK A WATCH OUT OF ITS WAISTCOAT-
POCKET, and looked at it, and then hurried on, Alice started to her feet,
for it flashed across her mind that she had never before seen a rabbit with
either a waistcoat-pocket, or a watch to take out of it, and burning with
curiosity, she ran across the field after it, and fortunately was just in time
to see it pop down a large rabbit-hole under the hedge.

The Mad Hatter and the March Hare were having tea at a long table.
The Queen of Hearts shouted "Off with their heads!"
The Cheshire Cat smiled from his branch in Wonderland Garden.

*** END OF THE PROJECT GUTENBERG EBOOK ALICE'S ADVENTURES IN WONDERLAND ***
"""

def test_preprocessing():
    from src.preprocessing import preprocess
    tokens = preprocess(SAMPLE)
    assert isinstance(tokens, list), "Should return a list"
    assert len(tokens) > 10, f"Expected >10 tokens, got {len(tokens)}"
    assert "gutenberg" not in tokens, "Gutenberg header not cleaned"
    for t in tokens:
        assert t.isalpha(), f"Non-alpha token found: {t!r}"


def test_lexdiv():
    from src.preprocessing import preprocess
    from src.lexdiv import lexical_diversity
    tokens = preprocess(SAMPLE)
    m = lexical_diversity(tokens)
    assert set(m.keys()) == {"tok", "typ", "hap", "ttr", "mwl", "mwf"}
    assert m["tok"] == len(tokens)
    assert 0 < m["ttr"] <= 1.0, f"TTR out of range: {m['ttr']}"
    assert m["mwl"] > 0
    # JSON-serialisable
    json.dumps(m)


def test_topics():
    from src.preprocessing import preprocess
    from src.topics import extract_topics
    tokens = preprocess(SAMPLE)
    topics = extract_topics(tokens)
    assert isinstance(topics, dict)
    assert len(topics) == 4, f"Expected 4 sections, got {len(topics)}"
    for section, words in topics.items():
        assert isinstance(words, list)
        assert len(words) > 0


def test_entities_single():
    """Single-word entities detected."""
    from src.entities import extract_entities
    result = extract_entities(SAMPLE)
    assert "characters" in result
    assert "locations" in result
    assert "compounds" in result
    assert isinstance(result["characters"], list)
    assert isinstance(result["locations"], list)


def test_entities_compounds():
    """Compound entities (White Rabbit, Mad Hatter…) detected."""
    from src.entities import extract_entities
    result = extract_entities(SAMPLE)
    compounds = result["compounds"]
    assert "White Rabbit" in compounds, f"'White Rabbit' not found in {compounds}"
    assert "Mad Hatter" in compounds, f"'Mad Hatter' not found in {compounds}"
    assert "March Hare" in compounds, f"'March Hare' not found in {compounds}"
    assert "Queen of Hearts" in compounds, f"'Queen of Hearts' not found in {compounds}"
    assert "Cheshire Cat" in compounds, f"'Cheshire Cat' not found in {compounds}"


def test_entities_no_gutenberg_noise():
    """Gutenberg metadata words should not appear as entities."""
    from src.entities import extract_entities
    result = extract_entities(SAMPLE)
    all_entities = result["characters"] + result["locations"] + result["compounds"]
    gutenberg_words = {"Gutenberg", "Foundation", "License", "Project"}
    for word in gutenberg_words:
        assert word not in all_entities, f"Gutenberg noise '{word}' found in entities"


def test_summary():
    from src.summary import extract_summary
    summary = extract_summary(SAMPLE, max_sentences=3)
    assert isinstance(summary, str)
    assert len(summary) > 0
    assert "START OF" not in summary
    assert "END OF" not in summary


def test_summary_preserves_order():
    """Returned sentences should be in source order."""
    from src.summary import split_sentences, extract_summary, _word_frequencies, sentence_score
    sentences = split_sentences(SAMPLE.strip())
    summary_text = extract_summary(SAMPLE, max_sentences=3)
    summary_sentences = [s for s in sentences if s in summary_text]
    # Find their positions in original
    indices = [sentences.index(s) for s in summary_sentences if s in sentences]
    assert indices == sorted(indices), "Summary sentences are not in original order"


def test_similarity_cosine():
    """Cosine similarity between identical texts = 1.0."""
    from src.similarity import tf, idf, vectorize, cosine
    texts = [SAMPLE, SAMPLE, "A completely different short text about nothing relevant here."]
    idf_dict = idf(texts)
    v1 = vectorize(SAMPLE, idf_dict)
    v2 = vectorize(SAMPLE, idf_dict)
    score = cosine(v1, v2)
    assert abs(score - 1.0) < 1e-9, f"Expected 1.0, got {score}"


def test_similarity_different():
    """Cosine similarity between very different texts < 0.5."""
    from src.similarity import tf, idf, vectorize, cosine
    text_a = SAMPLE
    text_b = "Mathematics physics quantum mechanics Schrodinger equations differential calculus."
    texts = [text_a, text_b]
    idf_dict = idf(texts)
    v1 = vectorize(text_a, idf_dict)
    v2 = vectorize(text_b, idf_dict)
    score = cosine(v1, v2)
    assert score < 0.5, f"Expected low similarity, got {score}"


def test_similarity_corpus():
    """compute_similarity returns proper structure."""
    from src.similarity import compute_similarity
    corpus = {11: SAMPLE, 99: "A short unrelated document about science and planets and stars."}
    results = compute_similarity(11, SAMPLE, corpus, top_n=5)
    assert isinstance(results, list)
    assert len(results) == 1  
    assert "book_id" in results[0]
    assert "score" in results[0]
    assert 0.0 <= results[0]["score"] <= 1.0


def test_cache_get_or_compute():
    """Cache should return same value on second call without recomputing."""
    import tempfile, os, shutil
    import src.cache as cache_mod
    original_dir = cache_mod.CACHE_DIR

    with tempfile.TemporaryDirectory() as tmpdir:
        cache_mod.CACHE_DIR = tmpdir
        call_count = {"n": 0}

        def expensive():
            call_count["n"] += 1
            return {"value": 42}

        r1 = cache_mod.get_or_compute("test_key", expensive)
        r2 = cache_mod.get_or_compute("test_key", expensive)

        assert r1 == r2 == {"value": 42}
        assert call_count["n"] == 1, f"compute_fn called {call_count['n']} times, expected 1"

    cache_mod.CACHE_DIR = original_dir


def test_display_json():
    """_print_json should produce valid indented JSON."""
    import io
    from contextlib import redirect_stdout
    import bookworm as bw
    data = {"a": 1, "b": [1, 2, 3]}
    buf = io.StringIO()
    with redirect_stdout(buf):
        bw._print_json(data)
    parsed = json.loads(buf.getvalue())
    assert parsed == data
    assert "    " in buf.getvalue(), "Expected indent=4"

def test_live_download():
    """Download book #11 from Project Gutenberg."""
    from src.downloader import get_book
    text = get_book(11)
    assert len(text) > 10000, "Downloaded text too short"
    assert "Alice" in text


def test_live_card():
    """Build a full card for book #11."""
    import shutil
    from src.downloader import get_book
    from src.card import build_card

    cache_file = os.path.join("cache", "card_11.json")
    if os.path.exists(cache_file):
        os.remove(cache_file)

    text = get_book(11)
    card = build_card(11, text)

    assert card["info"]["id"] == "11"
    assert "Alice" in card["info"]["title"]
    assert card["lexdiv"]["tok"] > 10000
    assert len(card["topics"]) == 4
    assert "characters" in card["entities"]
    assert len(card["summary"]) > 100

    card2 = build_card(11, text)
    assert card2 == card, "Card from cache differs from original"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true",
                    help="Include live network tests (downloads book #11)")
    args = ap.parse_args()

    print("\n" + "─" * 56)
    print("  Bookworm — Test Suite")
    print("─" * 56)

    unit_tests = [
        ("preprocessing",            test_preprocessing),
        ("lexdiv",                   test_lexdiv),
        ("topics",                   test_topics),
        ("entities — single tokens", test_entities_single),
        ("entities — compounds",     test_entities_compounds),
        ("entities — no Gutenberg",  test_entities_no_gutenberg_noise),
        ("summary",                  test_summary),
        ("summary — order preserved",test_summary_preserves_order),
        ("similarity — identical=1", test_similarity_cosine),
        ("similarity — different<.5",test_similarity_different),
        ("similarity — corpus API",  test_similarity_corpus),
        ("cache — get_or_compute",   test_cache_get_or_compute),
        ("display — _print_json",    test_display_json),
    ]

    print("\n[ Unit tests ]")
    for name, fn in unit_tests:
        test(name, fn)

    if args.live:
        print("\n[ Live tests — network required ]")
        for name, fn in [
            ("live download book #11", test_live_download),
            ("live full card #11",     test_live_card),
        ]:
            test(name, fn)
    else:
        print(f"\n  {SKIP}  live tests skipped (use --live to enable)")

    passed = sum(1 for r in results if r[0] == PASS)
    failed = sum(1 for r in results if r[0] == FAIL)
    total  = len(results)

    print("\n" + "─" * 56)
    print(f"  Results : {passed}/{total} passed", end="")
    if failed:
        print(f"  —  {failed} FAILED ⚠")
    else:
        print("  — all good ✔")
    print("─" * 56 + "\n")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()