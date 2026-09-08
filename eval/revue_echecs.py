"""Prepare la revue manuelle des echecs du retriever.

    python eval/revue_echecs.py --questions eval/questions_http.json --collection HttpStress

Produit un fichier Markdown listant, pour chaque question dont le bon fichier
n'arrive pas en 1re position, les documents reellement remontes AVEC leur
definition. Tu peux ainsi juger sans ouvrir un seul fichier.

POURQUOI CE TRAVAIL EN VAUT LA PEINE
--------------------------------------------------------------------------
Un jeu de test bati "a l'aveugle" — en devinant quel fichier repond a une
question — passe forcement a cote de documents aussi valables. On l'a constate :
`middleware` repond aussi bien que `proxy_server` a une question sur les
intermediaires, et `if-unmodified-since` existait sans qu'on le sache.

Ces faux echecs sont pires qu'inutiles : ils font croire a un defaut du
retriever et poussent a "corriger" un composant qui allait bien.

La methode standard s'appelle le POOLING : on rassemble ce que les systemes
remontent reellement, et on juge ces documents-la, au lieu de deviner d'avance.
Ce script en fait la version economique, appliquee la ou ca rapporte.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

import weaviate  # noqa: E402

from rag_pipeline import build_embedder, search  # noqa: E402

BRUIT = re.compile(r"\{\{[^}]*\}\}|<[^>]+>|\[([^\]]*)\]\([^)]*\)|[*`_#>]")


def definition(corpus: Path, source: str, taille: int = 150) -> str:
    """Premiere phrase utile du fichier, pour juger sans l'ouvrir."""
    chemin = corpus / source
    if not chemin.is_file():
        return "(fichier introuvable)"
    texte = chemin.read_text(encoding="utf-8")
    parts = texte.split("---", 2)
    corps = parts[2] if len(parts) >= 3 else texte
    corps = BRUIT.sub(r"\1", corps)
    for ligne in corps.split("\n"):
        ligne = " ".join(ligne.split())
        if len(ligne) > 40:
            return ligne[:taille]
    return "(pas de definition lisible)"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--questions", default="eval/questions.json")
    p.add_argument("--collection", default=None)
    p.add_argument("--k", type=int, default=5)
    p.add_argument("--sortie", default=None)
    args = p.parse_args()

    fichier = RACINE / args.questions
    data = json.loads(fichier.read_text(encoding="utf-8"))
    corpus = RACINE / data["corpus"]
    collection_name = args.collection or data["collection"]
    sortie = Path(args.sortie) if args.sortie else fichier.with_name(
        fichier.stem.replace("questions", "revue") + ".md"
    )

    client = weaviate.connect_to_local()
    try:
        collection = client.collections.get(collection_name)
        embedder = build_embedder()
        lignes = []
        for q in data["questions"]:
            resultats = search(collection, embedder, q["question"], k=args.k)
            # Seuls les pertinents de niveau 2 comptent comme un succes, comme
            # dans recall_at_k. Sans ce filtre, un voisin de niveau 1 de
            # questions_http_v3.json passerait pour la bonne reponse et la
            # revue sous-estimerait silencieusement le nombre d'echecs.
            # `pertinence` absent vaut 2 : les jeux binaires marchent tels quels.
            attendus = {p["source"] for p in q["pertinents"]
                        if int(p.get("pertinence", 2)) >= 2}
            rang = next((r["rank"] for r in resultats if r["source"] in attendus), None)
            if rang != 1:
                lignes.append((q, resultats, rang, attendus))
            print(".", end="", flush=True)
        print()
    finally:
        client.close()

    out = [
        f"# Revue des echecs — {collection_name}",
        "",
        f"{len(lignes)} question(s) sur {len(data['questions'])} dont le fichier",
        "annote n'arrive pas en 1re position.",
        "",
        "Pour chaque document remonte, demande-toi : **repond-il aussi a la",
        "question ?** Si oui, ajoute sa source dans le tableau `pertinents` de",
        f"cette question dans `{args.questions}`.",
        "",
        "Si AUCUN document remonte n'est acceptable et que le fichier annote",
        "reste le seul bon, c'est un vrai echec du retriever : laisse tel quel.",
        "",
        "---",
        "",
    ]

    for q, resultats, rang, attendus in lignes:
        out.append(f"## [{q['id']}] {q['question']}")
        out.append("")
        out.append(f"- **annote** : `{', '.join(sorted(attendus))}`")
        out.append(f"- **rang obtenu** : {rang if rang else f'absent du top-{args.k}'}")
        if q.get("commentaire"):
            out.append(f"- note : {q['commentaire']}")
        out.append("")
        out.append("| # | score | document | definition |")
        out.append("|---|---|---|---|")
        vus = set()
        for r in resultats:
            if r["source"] in vus:
                continue
            vus.add(r["source"])
            marque = " **(annote)**" if r["source"] in attendus else ""
            d = definition(corpus, r["source"]).replace("|", "/")
            out.append(f"| {r['rank']} | {r['score']:.3f} | `{r['source']}`{marque} | {d} |")
        out.append("")

    sortie.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"\n{len(lignes)} echec(s) ecrits dans {sortie.relative_to(RACINE)}")


if __name__ == "__main__":
    main()
