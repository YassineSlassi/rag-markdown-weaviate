"""Mesure la qualite du retriever sur un jeu de questions annotees.

    python eval/recall_at_k.py
    python eval/recall_at_k.py --k 20 --strict

QUATRE SORTIES, ET ELLES NE DISENT PAS LA MEME CHOSE
--------------------------------------------------------------------------
recall@k : sur quelle proportion de questions au moins un passage pertinent
           apparait dans les k premiers resultats. C'est la mesure qui
           repond a "est-ce que le bon document remonte ?".

MRR      : moyenne de 1/rang du premier resultat pertinent. Deux retrievers
           peuvent avoir le meme recall@5 alors que l'un place la reponse en
           1re position et l'autre en 5e. Le MRR les separe, le recall non.

nDCG@k   : lit TOUT le classement et pondere chaque position. Seule des trois
           a exploiter les niveaux de pertinence, et seule a voir au-dela du
           premier succes. Sur un jeu binaire a reponse unique elle vaut
           1/log2(r+1), donc redondante avec le MRR : c'est ce qui a motive
           les annotations graduees de questions_http_v3.json.

echecs   : la liste des questions ratees, avec ce qui est remonte a la place.
           C'est la seule sortie qui t'apprend QUOI corriger. Un chiffre
           global dit qu'il y a un probleme, jamais lequel.

--rerank : compare deux classements DANS LE MEME RUN. Le retriever remonte k
--------   candidats, puis le cross-encodeur les reordonne ; on mesure les
           deux ordres sur les memes candidats. Faire deux runs separes
           mesurerait la meme chose, mais rien ne garantirait que les viviers
           soient identiques, et ca paierait l'embedding deux fois.

           Le reranker ne cherche rien : il reordonne. Donc recall@k a la
           profondeur maximale est mathematiquement INVARIANT, et le script le
           verifie. Si cette ligne signale un ecart, c'est un bug, pas un gain.

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
from math import log2
import sys
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

import weaviate  # noqa: E402

from rag_pipeline import build_embedder, search  # noqa: E402

QUESTIONS = Path(__file__).parent / "questions.json"
SEUILS = (1, 3, 5, 10, 20)
SEUILS_NDCG = (5, 10)

# Niveaux de pertinence attendus dans le champ `pertinence` des annotations :
#   2 = repond exactement a la question
#   1 = voisin utile (meme famille, eclaire, mais n'est pas la reponse)
#   0 = non pertinent, jamais annote
# Un champ absent vaut 2, pour que les jeux binaires existants marchent tels quels.
PERTINENCE_EXACTE = 2


def normaliser(texte: str) -> str:
    return " ".join(texte.split())


def gains_du_classement(resultats: list[dict], pertinents: list[dict],
                        strict: bool) -> list[int]:
    """Niveau de pertinence de chaque resultat, dans l'ordre du classement.

    DEDUPLICATION PAR SOURCE, et c'est essentiel : un meme fichier fournit
    plusieurs chunks, qui remontent souvent ensemble. Sans deduplication, le
    gain serait compte trois fois et le DCG depasserait l'ideal — un nDCG
    superieur a 1, donc absurde. On credite le PREMIER chunk de chaque source
    et on met 0 aux suivants : la pertinence appartient au document, pas au
    nombre de ses morceaux.
    """
    niveaux = {
        p["source"]: int(p.get("pertinence", PERTINENCE_EXACTE)) for p in pertinents
    }
    extraits = {p["source"]: p.get("extrait", "") for p in pertinents}

    gains: list[int] = []
    deja_credite: set[str] = set()

    for resultat in resultats:
        source = resultat["source"]
        niveau = niveaux.get(source, 0)

        if niveau and source in deja_credite:
            niveau = 0
        elif niveau and strict and extraits.get(source):
            if normaliser(extraits[source]) not in normaliser(resultat["text"]):
                niveau = 0

        if niveau:
            deja_credite.add(source)
        gains.append(niveau)

    return gains


def dcg(gains: list[int]) -> float:
    """Gain cumule actualise, avec le gain exponentiel 2^p - 1 (convention TREC).

    L'exponentielle creuse l'ecart voulu : un document exact (p=2) vaut 3, un
    voisin (p=1) vaut 1. Un systeme qui inverse les deux est donc lourdement
    penalise, ce qu'un gain lineaire ne ferait pas.
    """
    return sum((2 ** g - 1) / log2(i + 2) for i, g in enumerate(gains))


def ndcg_at_k(gains: list[int], pertinents: list[dict], k: int) -> float:
    """DCG@k rapporte au DCG du classement IDEAL.

    Le classement ideal place tous les documents annotes par pertinence
    decroissante. Diviser par lui rend la mesure comparable d'une question a
    l'autre, y compris quand elles n'ont pas le meme nombre de bonnes reponses.
    """
    ideal = sorted(
        (int(p.get("pertinence", PERTINENCE_EXACTE)) for p in pertinents),
        reverse=True,
    )[:k]
    parfait = dcg(ideal)
    if parfait == 0:
        return 0.0
    return dcg(gains[:k]) / parfait


def rang_du_premier_exact(gains: list[int]) -> int | None:
    """Rang (1-base) du premier document de pertinence MAXIMALE, ou None.

    Seuille volontairement a PERTINENCE_EXACTE : recall@k et MRR sont des
    mesures binaires, et compter les voisins de pertinence 1 les gonflerait
    artificiellement. Un systeme qui remonte 401 en premier pour une question
    portant sur 407 ne doit pas etre credite d'un succes au rang 1.
    """
    for i, g in enumerate(gains, start=1):
        if g >= PERTINENCE_EXACTE:
            return i
    return None


def mesures(resultats: list[dict], pertinents: list[dict], strict: bool) -> dict:
    """Toutes les mesures d'UN classement, pour UNE question.

    Regroupees dans une fonction parce que --rerank les calcule deux fois sur
    les memes candidats : une fois dans l'ordre du retriever, une fois dans
    l'ordre du cross-encodeur. Dupliquer ces quatre lignes serait le meilleur
    moyen de faire diverger les deux mesures sans s'en apercevoir.
    """
    gains = gains_du_classement(resultats, pertinents, strict)
    return {
        "gains": gains,
        "rang": rang_du_premier_exact(gains),
        "ndcg": {k: ndcg_at_k(gains, pertinents, k) for k in SEUILS_NDCG},
        "resultats": resultats,
    }


def tableau(groupes: list[tuple[str, list[dict]]], cle: str, titre: str) -> dict:
    """Affiche le tableau recall/MRR/nDCG et retourne les moyennes par groupe.

    `cle` designe le classement lu dans chaque ligne : "avant" (retriever) ou
    "apres" (reranker). Retourner les moyennes permet d'en faire la difference
    sans les recalculer.
    """
    entete = "  ".join(f"@{k:<4}" for k in SEUILS)
    ndcg_entete = "  ".join(f"nDCG@{k:<2}" for k in SEUILS_NDCG)
    print(f"\n{titre}")
    print(f"{'':16} {entete}   MRR    {ndcg_entete}    n")
    print("-" * 82)

    moyennes = {}
    for nom, groupe in groupes:
        if not groupe:
            continue
        m = {}
        cellules = []
        for k in SEUILS:
            rangs = [l[cle]["rang"] for l in groupe]
            trouves = sum(1 for r in rangs if r is not None and r <= k)
            m[f"@{k}"] = trouves / len(groupe)
            cellules.append(f"{m[f'@{k}']:.2f} ")
        m["mrr"] = sum(1 / l[cle]["rang"] for l in groupe if l[cle]["rang"]) / len(groupe)
        for k in SEUILS_NDCG:
            m[f"ndcg@{k}"] = sum(l[cle]["ndcg"][k] for l in groupe) / len(groupe)
        ndcgs = "   ".join(f"{m[f'ndcg@{k}']:.3f}" for k in SEUILS_NDCG)
        print(f"{nom:16} {'  '.join(cellules)}  {m['mrr']:.3f}   {ndcgs}  {len(groupe):>4}")
        moyennes[nom] = m
    return moyennes


def tableau_delta(avant: dict, apres: dict, k_max: int) -> None:
    """Difference apres - avant, avec le temoin de controle en evidence."""
    colonnes = [f"@{k}" for k in SEUILS] + ["mrr"] + [f"ndcg@{k}" for k in SEUILS_NDCG]
    largeurs = {c: max(len(c), 6) for c in colonnes}

    print("\nDELTA  (reranker - retriever ; positif = le reranker fait mieux)")
    print(f"{'':16} " + " ".join(f"{c:>{largeurs[c]}}" for c in colonnes))
    print("-" * 82)
    for nom in avant:
        cellules = []
        for c in colonnes:
            d = apres[nom][c] - avant[nom][c]
            texte = f"{d:+.3f}" if abs(d) > 1e-12 else "  .   "
            cellules.append(f"{texte:>{largeurs[c]}}")
        print(f"{nom:16} " + " ".join(cellules))

    # Le temoin de controle. Meme ensemble de candidats, ordre different : le
    # recall a la profondeur du vivier ne PEUT pas bouger.
    ecart = abs(apres["TOUTES"][f"@{k_max}"] - avant["TOUTES"][f"@{k_max}"])
    if ecart < 1e-12:
        print(f"\n  temoin de controle : recall@{k_max} inchangé, comme attendu "
              f"(même vivier, ordre différent).")
    else:
        print(f"\n  ANOMALIE : recall@{k_max} a bougé de {ecart:.4f}. Le reranker "
              f"ne peut pas changer l'ensemble des candidats — c'est un bug.")


def main() -> None:
    parser = argparse.ArgumentParser(description="recall@k du retriever")
    parser.add_argument("--k", type=int, default=max(SEUILS),
                        help="profondeur maximale interrogee")
    parser.add_argument("--strict", action="store_true",
                        help="exiger aussi l'extrait annote, pas seulement le fichier")
    parser.add_argument("--collection", type=str, default=None)
    parser.add_argument("--questions", type=str, default=None,
                        help="autre jeu de questions (defaut : eval/questions.json)")
    parser.add_argument("--rerank", action="store_true",
                        help="mesure aussi le classement reordonne par cross-encodeur, "
                             "et affiche les deux tableaux plus leur difference")
    parser.add_argument("--rerank-modele", type=str, default=None,
                        help="autre cross-encodeur (defaut : BAAI/bge-reranker-v2-m3 ; "
                             "BAAI/bge-reranker-base est 3,4x plus rapide et un peu moins bon)")
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

        reranker = None
        modele_rerank = None
        if args.rerank:
            import rag_rerank

            modele_rerank = args.rerank_modele or rag_rerank.RERANK_MODEL
            reranker = rag_rerank.build_reranker(modele_rerank)

        print(f"\n{len(questions)} questions  |  collection {collection_name}"
              f"  |  {'strict' if args.strict else 'correspondance au fichier'}"
              f"{'  |  + rerank' if args.rerank else ''}\n")

        lignes = []
        chrono_rerank = 0.0
        for q in questions:
            resultats = search(collection, embedder, q["question"], k=args.k)
            ligne = {"q": q, "avant": mesures(resultats, q["pertinents"], args.strict)}

            if reranker is not None:
                debut = time.perf_counter()
                # top_n=None : on garde les k candidats, seulement reordonnes.
                # C'est ce qui rend recall@k invariant et donc verifiable.
                reordonnes = rag_rerank.rerank(reranker, q["question"], resultats)
                chrono_rerank += time.perf_counter() - debut
                ligne["apres"] = mesures(reordonnes, q["pertinents"], args.strict)

            lignes.append(ligne)
            print(".", end="", flush=True)
        print("\n")
    finally:
        client.close()

    # ---- resultats globaux et par type -----------------------------------
    types = sorted({q["type"] for q in questions})
    groupes = [("TOUTES", lignes)] + [
        (t.upper(), [l for l in lignes if l["q"]["type"] == t]) for t in types
    ]

    if args.rerank:
        moy_avant = tableau(groupes, "avant", f"RETRIEVER SEUL  —  BGE-M3, {args.k} candidats")
        moy_apres = tableau(groupes, "apres", f"+ RERANKER  —  {modele_rerank}")
        tableau_delta(moy_avant, moy_apres, args.k)
        n = len(lignes)
        print(f"  coût du reranking : {chrono_rerank:.0f}s pour {n} questions, soit "
              f"{chrono_rerank / n:.2f}s par question "
              f"({chrono_rerank / (n * args.k) * 1000:.0f} ms par candidat)")
    else:
        tableau(groupes, "avant", f"RETRIEVER  —  BGE-M3, {args.k} candidats")

    # Le classement dont on analyse ensuite les rangs et les echecs : celui du
    # systeme complet quand le reranker est en place, sinon celui du retriever.
    cle = "apres" if args.rerank else "avant"

    # ---- distribution des rangs ------------------------------------------
    # Quand le recall sature a 1.00 des @3, c'est ici que reste l'information :
    # une question resolue au rang 4 est un quasi-echec que le recall@5 masque.
    print("\nRang du premier resultat pertinent :")
    compte: dict[str, int] = {}
    for l in lignes:
        rang_cle = str(l[cle]["rang"]) if l[cle]["rang"] else f">{args.k}"
        compte[rang_cle] = compte.get(rang_cle, 0) + 1
    for rang_cle in sorted(compte, key=lambda c: (c.startswith(">"), int(c.lstrip(">")))):
        barre = "#" * compte[rang_cle]
        print(f"  rang {rang_cle:>4} : {compte[rang_cle]:>3}  {barre}")

    # ---- echecs ----------------------------------------------------------
    # Seuil a 1 et non a 5 : sur un corpus ou tout remonte dans le top-3, seul
    # le rang 1 discrimine encore.
    echecs = [l for l in lignes if l[cle]["rang"] is None or l[cle]["rang"] > 1]
    print(f"\n{len(echecs)} question(s) dont le bon fichier n'est PAS en 1re position :")
    for l in echecs:
        q = l["q"]
        exacts = [p["source"] for p in q["pertinents"]
                  if int(p.get("pertinence", PERTINENCE_EXACTE)) >= PERTINENCE_EXACTE]
        rang = l[cle]["rang"] or f"absent du top-{args.k}"
        mouvement = ""
        if args.rerank:
            # Le rang AVANT reranking, pour distinguer les echecs que le
            # reranker a laisses passer de ceux qu'il a lui-meme crees.
            avant = l["avant"]["rang"] or f">{args.k}"
            mouvement = f"   [retriever : rang {avant}]"
        print(f"\n  [{q['id']}] {q['question']}")
        print(f"        attendu : {', '.join(exacts)}   (rang {rang}){mouvement}")
        print("        remonte :")
        for r in l[cle]["resultats"][:3]:
            note = r.get("score_rerank", r["score"])
            print(f"          {r['rank']}. {note:.4f}  {r['source']}")

    if args.rerank:
        # Bilan du reranking sur le seul rang qui discrimine encore ici.
        gagnees = [l for l in lignes
                   if l["apres"]["rang"] == 1 and l["avant"]["rang"] != 1]
        perdues = [l for l in lignes
                   if l["avant"]["rang"] == 1 and l["apres"]["rang"] != 1]
        print(f"\nEffet du reranking sur le rang 1 :")
        print(f"  {len(gagnees)} gagnée(s) : {', '.join(l['q']['id'] for l in gagnees) or '-'}")
        print(f"  {len(perdues)} perdue(s) : {', '.join(l['q']['id'] for l in perdues) or '-'}")


if __name__ == "__main__":
    main()
