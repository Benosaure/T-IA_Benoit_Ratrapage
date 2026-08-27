from collections import Counter 
#TOK : conte le nombre total de mots dans le texte.
#ensuite on ajoute un Garde-fou : si le texte est vide (aucun token), on évite
#la division par zéro en renvoyant des valeurs neutres.
#TYP : ensuite on conte le nombre de mots uniques (le vocabulaire du texte).
#set(tokens) supprime les doublons.
#ensuite compte combien de fois chaque mot apparaît.
#Hapax legomena : mots qui n'apparaissent qu'une seule fois.
#Type-Token Ratio : richesse du vocabulaire
#proche de 1 = vocabulaire très varié, proche de 0 = très répétitif.
#MWL : Longueur moyenne d'un mot, en nombre de caractères.
#Mean Word Frequency : fréquence moyenne d'un mot (inverse du TTR).
#on renvoie les 6 métriques demandées, arrondies à 4 décimales
#pour les ratios (plus lisible dans le JSON de sortie).

def lexical_diversity(tokens):

    tok = len(tokens)

    if tok == 0:
        return {"tok": 0, "typ": 0, "hap": 0, "ttr": 0.0, "mwl": 0.0, "mwf": 0.0}

    typ = len(set(tokens))

    frequencies = Counter(tokens)

    hap = sum(
        1
        for count in frequencies.values()
        if count == 1
    )

    ttr = typ / tok

    mwl = (
        sum(len(token) for token in tokens)
        / tok
    )

    mwf = tok / typ

    return {
        "tok": tok,
        "typ": typ,
        "hap": hap,
        "ttr": round(ttr, 4),
        "mwl": round(mwl, 4),
        "mwf": round(mwf, 4)
    }