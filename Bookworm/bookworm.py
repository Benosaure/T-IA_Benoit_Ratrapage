import argparse
import json
import sys
#le CLI du projet
from src.downloader import get_book
from src.preprocessing import preprocess
from src.lexdiv import lexical_diversity

#affiche le contenu d'un json
def _print_json(data) -> None:
    print(json.dumps(data, indent=4, ensure_ascii=False))

#affiche une entéte
def _print_header(title: str, book_id: int) -> None:
    width = 52
    print()
    print("─" * width)
    print(f"  {title}  —  book #{book_id}")
    print("─" * width)

#affiche les info de la book card pour l'utilisateur
def _print_card(card: dict) -> None:
    info = card.get("info", {})
    lex  = card.get("lexdiv", {})
    top  = card.get("topics", {})
    ent  = card.get("entities", {})
    summ = card.get("summary", "")
    sim  = card.get("similar", [])

    w = 52
    print()
    print("╔" + "═" * w + "╗")
    print(f"║      {info.get('title', 'Unknown'):<{w - 5}}║")
    print(f"║      {info.get('authors', 'Unknown'):<{w - 5}}║")
    print(f"║      {info.get('bookshelves', ''):<{w - 5}}║")
    print("╠" + "═" * w + "╣")

    print(f"║  {'LEXICAL DIVERSITY':<{w - 2}}║")
    lex_line = (
        f"  tokens={lex.get('tok')}  types={lex.get('typ')}  "
        f"hapax={lex.get('hap')}  TTR={lex.get('ttr')}"
    )
    print(f"║{lex_line:<{w + 1}}║")
    print("╠" + "═" * w + "╣")

    print(f"║  {'TOPICS (top 5 per section)':<{w - 2}}║")
    for section_id, words in top.items():
        line = f"  §{section_id}: {', '.join(words[:5])}"
        print(f"║{line:<{w + 1}}║")
    print("╠" + "═" * w + "╣")

    chars = ent.get("characters", [])
    locs  = ent.get("locations", [])
    print(f"║  {'ENTITIES':<{w - 2}}║")
    print(f"║  {'Characters: ' + ', '.join(chars[:8]):<{w - 1}}║")
    print(f"║  {'Locations:  ' + ', '.join(locs[:6]):<{w - 1}}║")
    print("╠" + "═" * w + "╣")

    print(f"║  {'SUMMARY':<{w - 2}}║")

    words_summ = summ.split()
    line_buf: list[str] = []
    for word in words_summ:
        line_buf.append(word)
        if len(" ".join(line_buf)) > 46:
            print(f"║  {' '.join(line_buf):<{w - 2}}║")
            line_buf = []
    if line_buf:
        print(f"║  {' '.join(line_buf):<{w - 2}}║")
    print("╠" + "═" * w + "╣")

    if sim:
        print(f"║  {'SIMILAR BOOKS':<{w - 2}}║")
        for i, title in enumerate(sim[:5], start=1):
            line = f"  {i}. {title}"
            print(f"║{line:<{w - 1}}║")

    print("╚" + "═" * w + "╝")
    print()

#fonction qui s'occupe d'afficher les erreur
def _err(command: str, exc: Exception) -> None:
    print(f"\n[ERROR] --{command} failed: {exc}", file=sys.stderr)
    sys.exit(1)

#code principale, permet le démarage du projet et execute les autres code en utilisent le book_id donné par l'utilisateur
def main() -> None:
    parser = argparse.ArgumentParser(
        prog="bookworm",
        description="Bookworm — NLP Explorer for Project Gutenberg books",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument("--download",  type=int, metavar="ID",
                        help="Download and cache a Gutenberg book")
    parser.add_argument("--lexdiv",    type=int, metavar="ID",
                        help="Compute lexical diversity metrics")
    parser.add_argument("--topics",    type=int, metavar="ID",
                        help="Extract TF-IDF topics per section")
    parser.add_argument("--entities",  type=int, metavar="ID",
                        help="Extract named entities (characters & locations)")
    parser.add_argument("--summarize", type=int, metavar="ID",
                        help="Extractive summary (top sentences)")
    parser.add_argument("--similar",   type=int, metavar="ID",
                        help="Find similar books in the local corpus")
    parser.add_argument("--card",      type=int, metavar="ID",
                        help="Generate a full book card (all features)")
    parser.add_argument("--raw",       action="store_true",
                        help="Output raw JSON instead of formatted display")

    args = parser.parse_args()

    command_ids = [
        args.download, args.lexdiv, args.topics, args.entities,
        args.summarize, args.similar, args.card,
    ]
    if all(v is None for v in command_ids):
        parser.print_help()
        sys.exit(0)

    if args.download is not None:
        try:
            text = get_book(args.download)
            tokens = preprocess(text)
            _print_header("DOWNLOAD", args.download)
            print(f"  ✔ Book #{args.download} ready")
            print(f"  Tokens : {len(tokens)}")
            print(f"  Preview: {' '.join(tokens[:20])} …")
            print()
        except Exception as e:
            _err("download", e)

    if args.lexdiv is not None:
        try:
            text   = get_book(args.lexdiv)
            tokens = preprocess(text)
            metrics = lexical_diversity(tokens)
            _print_header("LEXICAL DIVERSITY", args.lexdiv)
            _print_json(metrics)
        except Exception as e:
            _err("lexdiv", e)

    if args.topics is not None:
        try:
            from src.topics import extract_topics
            text   = get_book(args.topics)
            tokens = preprocess(text)
            topics = extract_topics(tokens)
            _print_header("TOPICS", args.topics)
            _print_json(topics)
        except Exception as e:
            _err("topics", e)

    if args.entities is not None:
        try:
            from src.entities import extract_entities
            text     = get_book(args.entities)
            entities = extract_entities(text)
            _print_header("ENTITIES", args.entities)
            _print_json(entities)
        except Exception as e:
            _err("entities", e)

    if args.summarize is not None:
        try:
            from src.summary import summarize
            text    = get_book(args.summarize)
            summary = summarize(text, num_sentences=5)
            _print_header("SUMMARY", args.summarize)
            print(summary)
            print()
        except Exception as e:
            _err("summarize", e)

    if args.similar is not None:
        try:
            from src.similarity import similar_titles, load_corpus_from_disk
            text   = get_book(args.similar)
            corpus = load_corpus_from_disk()
            corpus[args.similar] = text   # ensure reference book is in corpus

            titles = similar_titles(args.similar, text, corpus, top_n=5)
            _print_header("SIMILARITY", args.similar)
            if args.raw:
                _print_json(titles)
            elif not titles:
                print("  ⚠ Not enough books in corpus (download more with --download).")
            else:
                for i, title in enumerate(titles, start=1):
                    print(f"  {i}. {title}")
            print()
        except Exception as e:
            _err("similar", e)

    if args.card is not None:
        try:
            from src.card import build_card
            text = get_book(args.card)
            card = build_card(args.card, text)
            _print_header("BOOK CARD", args.card)
            if args.raw:
                _print_json(card)
            else:
                _print_card(card)
        except Exception as e:
            _err("card", e)


if __name__ == "__main__":
    main()