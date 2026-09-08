"""Ajoute des niveaux de pertinence gradues au jeu de questions HTTP.

    python eval/graduer_pertinence.py

POURQUOI GRADUER
--------------------------------------------------------------------------
Avec une seule bonne reponse binaire par question, le nDCG vaut 1/log2(r+1)
et le MRR vaut 1/r : deux lectures du meme signal, la profondeur de l'unique
bonne reponse. Le nDCG n'apporte alors rien que le MRR ne dise deja.

Avec des niveaux, le nDCG mesure ce que le MRR ne peut pas voir : le systeme
a-t-il place la MEILLEURE reponse au-dessus de la simplement acceptable ?

    2 = repond exactement a la question
    1 = voisin utile : meme famille, eclaire le sujet, mais n'est pas la
        reponse demandee (407 pour une question sur 401, if-unmodified-since
        pour une question sur if-modified-since...)
    0 = non pertinent, jamais annote

Le seuil de recall@k et du MRR reste a 2, sinon ajouter des voisins gonflerait
ces deux mesures au lieu de les affiner.

Chaque voisin ci-dessous a ete choisi apres relecture de la fiche concernee,
pas de memoire. Le script verifie ensuite que chaque fichier existe.
"""

import json
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SOURCE = Path(__file__).parent / "questions_http_v2.json"
CIBLE = Path(__file__).parent / "questions_http_v3.json"

S = "status/{}/index.md".format
H = "headers/{}/index.md".format
C = "headers/content-security-policy/{}/index.md".format

# Voisins de pertinence 1, par identifiant de question.
VOISINS: dict[str, list[str]] = {
    # --- statuts : familles confusables ---
    "st01": [S(407), S(511)],                 # 401 : meme manque, mais proxy / reseau
    "st02": [S(401), S(511)],                 # 407 : idem cote serveur d'origine
    "st03": [S(401)],                         # 403 : la fiche dit "similaire a 401 sauf que"
    "st04": [S(401), S(407)],                 # 511
    "st05": [S(410)],                         # 404 : absence sans duree / absence permanente
    "st06": [S(404)],                         # 410
    "st07": [S(301), S(307)],                 # 308 : permanent / methode preservee
    "st08": [S(308)],                         # 301 : l'autre redirection definitive
    "st09": [S(302), S(308)],                 # 307 : l'autre temporaire / l'autre preservant
    "st10": [S(302)],                         # 303
    "st11": [S(406), S(506)],                 # 300 : negociation de contenu
    "st12": [S(412)],                         # 304 : l'autre issue d'une conditionnelle
    "st13": [S(504), S(500)],                 # 502 : passerelle
    "st14": [S(502), S(408)],                 # 504 : passerelle / delai
    "st15": [S(502), S(504)],                 # 503
    "st16": [S(428), S(304)],                 # 412 : preconditions
    "st17": [S(412)],                         # 428
    "st18": [S(503)],                         # 429 : surcharge
    "st19": [S(413), S(414)],                 # 431 : "trop grand"
    "st20": [S(413), S(431)],                 # 414
    "st21": [S(409), S(424)],                 # 423 : WebDAV
    "st22": [S(501)],                         # 405 : methode non prise en charge
    "st23": [S(405)],                         # 501
    "st24": [S(102)],                         # 202 : traitement en cours
    "st25": [S(205), S(200)],                 # 204
    "st26": [S(204)],                         # 205
    "st27": [S(416), S(200)],                 # 206 : plages
    "st28": [H("early-data")],                # 425 : l'en-tete associe

    # --- le carre de l'authentification ---
    "au01": [H("proxy-authorization")],
    "au02": [H("authorization")],
    "au03": [H("proxy-authenticate"), H("authorization")],
    "au04": [H("www-authenticate"), H("proxy-authorization")],

    # --- conditionnels et plages ---
    "co01": [H("if-none-match"), H("etag")],
    "co02": [H("if-match"), H("etag")],
    "co03": [H("if-unmodified-since"), H("last-modified")],
    "co04": [H("if-modified-since"), H("last-modified")],
    "co05": [H("range"), H("if-match")],
    "co06": [H("if-modified-since"), H("etag")],
    "co07": [H("if-none-match"), H("last-modified")],
    "co08": [H("content-range"), H("accept-ranges"), H("if-range")],
    "co09": [H("range"), H("accept-ranges")],
    "co10": [H("range"), H("content-range")],

    # --- cache ---
    "ca01": [H("expires"), H("pragma")],
    "ca02": [H("cache-control"), H("age")],
    "ca03": [H("cache-control"), H("expires")],
    "ca04": [H("no-vary-search"), H("cache-control")],
    "ca05": [H("cache-control")],
    "ca06": [H("vary")],

    # --- CORS : requete preliminaire contre reponse ---
    "cr01": [H("origin")],
    "cr02": [H("access-control-request-method"), H("allow")],
    "cr03": [H("access-control-request-headers"), H("access-control-expose-headers")],
    "cr04": [H("access-control-allow-methods")],
    "cr05": [H("access-control-allow-headers")],
    "cr06": [H("access-control-allow-origin")],
    "cr07": [H("access-control-allow-headers")],
    "cr08": [H("access-control-request-method")],
    "cr09": [H("access-control-allow-origin"), H("referer")],

    # --- famille Content-* et negociation ---
    "cn01": [H("content-type")],
    "cn02": [H("accept-encoding"), H("content-type")],
    "cn03": [H("accept-language")],
    "cn04": [H("content-range")],
    "cn05": [H("location"), H("content-type")],
    "cn06": [H("repr-digest"), H("etag")],
    "cn07": [H("content-type"), H("accept-patch"), H("accept-post")],
    "cn08": [H("content-encoding")],
    "cn09": [H("content-language")],
    "cn10": [H("accept-post"), H("accept")],

    # --- directives CSP, dont les triplets ---
    "cs01": [C("script-src"), C("style-src")],
    "cs02": [C("script-src-elem"), C("script-src-attr"), C("default-src")],
    "cs03": [C("script-src"), C("script-src-elem")],
    "cs04": [C("script-src"), C("script-src-attr")],
    "cs05": [C("style-src"), C("style-src-elem")],
    "cs06": [C("default-src")],
    "cs07": [C("frame-src"), H("x-frame-options")],
    "cs08": [C("default-src")],
    "cs09": [C("default-src")],
    "cs10": [C("block-all-mixed-content")],
    "cs11": [],   # report-to est deja annote ; report-uri passera en 1, cf. plus bas

    # --- paires ancien / nouveau nom ---
    "ob01": [H("content-security-policy")],
    "ob02": [H("permissions-policy")],
    "ob03": [H("integrity-policy")],
    "ob04": [H("report-to")],
    "ob05": [H("device-memory")],
    "ob06": [H("dpr"), H("content-dpr")],

    # --- divers ---
    "di01": [S(503), S(429)],
    "di02": [S(405), H("access-control-allow-methods")],
    "di03": [H("cookie")],
    "di04": [H("content-type")],
    "di05": [C("frame-ancestors")],
    "di06": [S(101), S(426), H("connection")],
    "di07": [H("forwarded")],
    "di08": [H("max-forwards"), H("host")],
    "di09": [H("referrer-policy"), H("origin")],
    "di10": [H("referer")],
    "di11": [],   # idempotency-key n'a pas de voisin franc dans ce corpus
    "di12": [H("origin"), H("alt-used")],
}

# Cas particulier : la question cs11 annotait deux directives a egalite, alors
# que report-uri est le predecesseur obsolete de report-to. On les hierarchise.
RETROGRADER = {"cs11": {C("report-uri"): 1}}


def main() -> None:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    corpus = RACINE / data["corpus"]

    manquants: list[tuple[str, str]] = []
    n_ajoutes = 0

    for q in data["questions"]:
        qid = q["id"]
        deja = {p["source"] for p in q["pertinents"]}

        # Les sources deja presentes sont la reponse exacte, sauf retrogradation.
        for p in q["pertinents"]:
            p["pertinence"] = RETROGRADER.get(qid, {}).get(p["source"], 2)

        for source in VOISINS.get(qid, []):
            if source in deja:
                continue
            if not (corpus / source).is_file():
                manquants.append((qid, source))
                continue
            q["pertinents"].append({"source": source, "pertinence": 1, "extrait": ""})
            n_ajoutes += 1

    data["note"] = (
        "Version 3 : niveaux de pertinence gradues, ajoutes a la v2 par "
        "graduer_pertinence.py apres relecture du corpus. 2 = repond exactement, "
        "1 = voisin utile de la meme famille. Le recall@k et le MRR seuillent a 2 ; "
        "seul le nDCG exploite les niveaux."
    )
    data["pertinence"] = {
        "2": "repond exactement a la question",
        "1": "voisin utile : meme famille, eclaire le sujet, mais n'est pas la reponse",
        "0": "non pertinent, jamais annote",
    }

    CIBLE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    total = sum(len(q["pertinents"]) for q in data["questions"])
    n2 = sum(1 for q in data["questions"] for p in q["pertinents"] if p["pertinence"] == 2)
    n1 = sum(1 for q in data["questions"] for p in q["pertinents"] if p["pertinence"] == 1)
    sans_voisin = [q["id"] for q in data["questions"]
                   if all(p["pertinence"] == 2 for p in q["pertinents"])]

    print(f"{len(data['questions'])} questions, {total} annotations")
    print(f"  pertinence 2 (exacte) : {n2}")
    print(f"  pertinence 1 (voisin) : {n1}   ({n_ajoutes} ajoutees)")
    print(f"  questions sans voisin : {len(sans_voisin)}  {sans_voisin}")

    if manquants:
        print("\n  FICHIERS INTROUVABLES — voisins ignores :")
        for qid, source in manquants:
            print(f"    {qid} -> {source}")
    else:
        print("\n  tous les voisins annotes existent dans le corpus")

    print(f"\necrit dans {CIBLE.relative_to(RACINE)}")


if __name__ == "__main__":
    main()
