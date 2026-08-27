import os
import requests
import re 

#télécharge un livre en construisent une url avec l'id du livre demander
#fait un try pour savoir si le livre existe dans la base et mettre une erreur si le livre n'existe pas
#la fonction verifi aussi le temp de reponse du server pour ne pas attendre indefiniment si le server ne repond pas
#retourne le texte du livre
def download_book(book_id, timeout=15):

    url = f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt"

    try:
        response = requests.get(url, timeout=timeout)
    except requests.exceptions.RequestException as e:
        raise ConnectionError(
            f"Unable to reach Project Gutenberg for book #{book_id}: {e}"
        ) from e

    if response.status_code != 200:
        raise ValueError(
            f"Book #{book_id} not found on Project Gutenberg "
            f"(HTTP {response.status_code})"
        )

    return response.text
#si le livre est déjà téléchargé le code va le récupéré depuis le dossier books
def load_book(book_id):
    with open(f"books/{book_id}.txt", encoding="utf8") as f:
        return f.read()

#si le livre n'est pas telecharger le code va le sauvegarder
#le code verifi si le dossier books existe et va crée le fifier du livre et l'ouvrire en écriture pour
#inséré le texte du livre dans le fichier crée
def save_book(book_id, text):

    os.makedirs("books", exist_ok=True)

    with open(
        f"books/{book_id}.txt",
        "w",
        encoding="utf-8"
    ) as f:
        f.write(text)

#verifi si le livre demander est déjà telecharger
#si oui retourne le livre depuis le dossier books
#si non lance la fonction download_book puis save_books
def get_book(book_id):
    filepath = f"books/{book_id}.txt"

    if os.path.exists(filepath):
        print(f"Loading local copy of book {book_id}")
        return load_book(book_id)

    print(f"Downloading book {book_id}")

    text = download_book(book_id)

    save_book(book_id, text)

    return text       

#fonction qui permet d'extraires des mot dans le texte pour les mettres dans des catégories
#permet de recupéré le titre, l'auteur, et la catégorie du livre
def extract_metadata(text):

    title = "Unknown"
    author = "Unknown"
    bookshelves = "Children / Young Adult"

    title_match = re.search(r"Title:\s*(.*)", text)
    if title_match:
        title = title_match.group(1).strip()

    author_match = re.search(r"Author:\s*(.*)", text)
    if author_match:
        author = author_match.group(1).strip()

    
    if "Alice" in title:
        bookshelves = "Children / Young Adult"
    elif "Sherlock" in title:
        bookshelves = "Crime / Mystery"
    elif "Dracula" in title:
        bookshelves = "Horror / Fantasy"
    elif "Time Machine" in title:
        bookshelves = "Science Fiction"

    return {
        "title": title,
        "authors": author,
        "bookshelves": bookshelves
    }