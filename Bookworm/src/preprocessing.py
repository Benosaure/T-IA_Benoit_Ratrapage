import re

from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

STOP_WORDS = set(stopwords.words("english"))

lemmatizer = WordNetLemmatizer()
#retiré ce qui precede le marker Sart of et ce qu'il y a apré le marker End of puis retourne le texte
def remove_gutenberg_metadata(text):
    start_marker = "*** START OF"
    end_marker = "*** END OF"

    start = text.find(start_marker)
    end = text.find(end_marker)

    if start != -1:
        start = text.find("\n", start)

    if start != -1 and end != -1:
        return text[start:end]

    return text

#met tout en minuscule et retire les annotation entre crochet []
def basic_clean(text):

    text = text.lower()

    text = re.sub(r"\[.*?\]", "", text)

    text = re.sub(r"\s+", " ", text)

    return text.strip()

#découpe les mots
def tokenize(text):
    return word_tokenize(text)

#retire ce qui n'est pas des mots, ponctuations etc ...
def remove_non_words(tokens):

    return [
        token
        for token in tokens
        if token.isalpha()
    ]

#retire les stopwords ex: the, a, in , of ...
def remove_stopwords(tokens):

    return [
        token 
        for token in tokens
        if token not in STOP_WORDS
    ]

#simplifications des mots a leur mot commun
def lemmatize(tokens):

    lemmatized_tokens = []

    for token in tokens:
        lemmatized_tokens.append(
            lemmatizer.lemmatize(token)
        )

    return lemmatized_tokens

#reunis les mots simplifier qui ce resemble
def preprocess(text):

    text = remove_gutenberg_metadata(text)

    text = basic_clean(text)

    tokens = tokenize(text)

    tokens = remove_non_words(tokens)

    tokens = remove_stopwords(tokens)

    tokens = lemmatize(tokens)

    return tokens