"""Mesure la qualite du retriever sur un jeu de questions annotees.

    python eval/recall_at_k.py
    python eval/recall_at_k.py --k 20 --strict

TROIS MESURES, ET ELLES NE DISENT PAS LA MEME CHOSE
--------------------------------------------------------------------------
recall@k : sur quelle proportion de questions au moins un passage pertinent
           apparait dans les k premiers resultats. C'est la mesure qui
           repond a "est-ce que le bon document remonte ?".

MRR      : moyenne de 1/rang du premier resultat pertinent. Deux retrievers
           peuvent avoir le meme recall@5 alors que l'un place la reponse en
           1re position et l'autre en 5e. Le MRR les separe, le recall non.

echecs   : la liste des questions ratees, avec ce qui est remonte a la place.
           C'est la seule sortie qui t'apprend QUOI corriger. Un chiffre
           global dit qu'il y a un probleme, jamais lequel.

POURQUOI LA CORRESPONDANCE SE FAIT AU FICHIER
--------------------------------------------------------------------------
Dans ce corpus, un fichier = un concept. N'importe quel chunk de
`base64/index.md` est une reponse legitime a "qu'est-ce que Base64 ?", qu'il
contienne la definition ou un exemple. Exiger en plus un extrait precis
(--strict) produirait des echecs artificiels : le bon fichier remonte, mais
pas le paragraphe exact qu'on avait annote.

--strict existe pour les corpus ou un fichier couvre plusieurs sujets. Sur
celui-ci, il mesure autre chose que ce qu'on cherche.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

import weaviate  # noqa: E402

from rag_pipeline import build_embedder, search  # noqa: E402

QUESTIONS = Path(__file__).parent / "questions.json"
SEUILS = (1, 3, 5, 10, 20)


def normaliser(texte: str) -> str:
    return " ".join(texte.split())


def rang_du_premier_pertinent(resultats: list[dict], pertinents: list[dict],
                              strict: bool) -> int | None:
    """Rang (1-base) du premier resultat pertinent, ou None si aucun."""
    for resultat in resultats:
        for attendu in pertinents:
            if resultat["source"] != attendu["source"]:
                continue
            if not strict or not attendu.get("extrait"):
                return resultat["rank"]
            if normaliser(attendu["extrait"]) in normaliser(resultat["text"]):
                return resultat["rank"]
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="recall@k du retriever")
    parser.add_argument("--k", type=int, default=max(SEUILS),
                        help="profondeur maximale interrogee")
    parser.add_argument("--strict", action="store_true",
                        help="exiger aussi l'extrait annote, pas seulement le fichier")
    parser.add_argument("--collection", type=str, default=None)
    parser.add_argument("--questions", type=str, default=None,
                        help="autre jeu de questions (defaut : eval/questions.json)")
    args = parser.parse_args()

    fichier = Path(args.questions) if args.questions else QUESTIONS
    data = json.loads(fichier.read_text(encoding="utf-8"))
    questions = data["questions"]
    collection_name = args.collection or data["collection"]

    client = weaviate.connect_to_local()
    try:
        if not client.collections.exists(collection_name):
            raise SystemExit(
                f"La collection {collection_name} n'existe pas.\n"
                f"  python rag_pipeline.py index --corpus {data['corpus']} "
                f"--collection {collection_name}"
            )
        collection = client.collections.get(collection_name)
        embedder = build_embedder()

        print(f"\n{len(questions)} questions  |  collection {collection_name}"
              f"  |  {'strict' if args.strict else 'correspondance au fichier'}\n")

        lignes = []
        for q in questions:
            resultats = search(collection, embedder, q["question"], k=args.k)
            rang = rang_du_premier_pertinent(resultats, q["pertinents"], args.strict)
            lignes.append({"q": q, "rang": rang, "resultats": resultats})
            print(".", end="", flush=True)
        print("\n")
    finally:
        client.close()

    # ---- resultats globaux et par type -----------------------------------
    types = sorted({q["type"] for q in questions})
    groupes = [("TOUTES", lignes)] + [
        (t.upper(), [l for l in lignes if l["q"]["type"] == t]) for t in types
    ]

    entete = "  ".join(f"@{k:<4}" for k in SEUILS)
    print(f"{'':14} {entete}   MRR     n")
    print("-" * 62)
    for nom, groupe in groupes:
        if not groupe:
            continue
        cellules = []
        for k in SEUILS:
            trouves = sum(1 for l in groupe if l["rang"] is not None and l["rang"] <= k)
            cellules.append(f"{trouves / len(groupe):.2f} ")
        mrr = sum(1 / l["rang"] for l in groupe if l["rang"]) / len(groupe)
        print(f"{nom:14} {'  '.join(cellules)}  {mrr:.3f}  {len(groupe):>4}")

    # ---- distribution des rangs ------------------------------------------
    # Quand le recall sature a 1.00 des @3, c'est ici que reste l'information :
    # une question resolue au rang 4 est un quasi-echec que le recall@5 masque.
    print("\nRang du premier resultat pertinent :")
    compte: dict[str, int] = {}
    for l in lignes:
        cle = str(l["rang"]) if l["rang"] else f">{args.k}"
        compte[cle] = compte.get(cle, 0) + 1
    for cle in sorted(compte, key=lambda c: (c.startswith(">"), int(c.lstrip(">")))):
        barre = "#" * compte[cle]
        print(f"  rang {cle:>4} : {compte[cle]:>3}  {barre}")

    # ---- echecs ----------------------------------------------------------
    # Seuil a 1 et non a 5 : sur un corpus ou tout remonte dans le top-3, seul
    # le rang 1 discrimine encore.
    echecs = [l for l in lignes if l["rang"] is None or l["rang"] > 1]
    print(f"\n{len(echecs)} question(s) dont le bon fichier n'est PAS en 1re position :")
    for l in echecs:
        q = l["q"]
        attendu = ", ".join(p["source"] for p in q["pertinents"])
        rang = l["rang"] if l["rang"] else "absent du top-%d" % args.k
        print(f"\n  [{q['id']}] {q['question']}")
        print(f"        attendu : {attendu}   (rang {rang})")
        print("        remonte :")
        for r in l["resultats"][:3]:
            print(f"          {r['rank']}. {r['score']:.3f}  {r['source']}")


if __name__ == "__main__":
    main()
