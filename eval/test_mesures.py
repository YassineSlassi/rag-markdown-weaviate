"""Verifie les proprietes des mesures, sans Weaviate et sans charger de modele.

    python eval/test_mesures.py

POURQUOI CE FICHIER
--------------------------------------------------------------------------
Un run d'evaluation coute plusieurs minutes et ses chiffres sont plausibles
quoi qu'il arrive : un nDCG de 0,74 ne dit pas s'il a ete calcule correctement.
Ces cinq assertions, elles, sont verifiables en une seconde sur des donnees
fabriquees dont on connait la reponse.

C'est le garde-fou a relancer apres toute modification de gains_du_classement,
de dcg ou de ndcg_at_k.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from recall_at_k import mesures  # noqa: E402

# Deux annotations de niveaux differents : la reponse exacte et un voisin utile.
PERTINENTS = [
    {"source": "a.md", "pertinence": 2, "extrait": ""},
    {"source": "b.md", "pertinence": 1, "extrait": ""},
]


def faux_resultat(source: str, rank: int) -> dict:
    """Un resultat de search() reduit a ce dont les mesures ont besoin."""
    return {
        "rank": rank,
        "score": 0.5,
        "source": source,
        "text": "peu importe",
        "headers": "",
        "title": "",
    }


def classement(sources: list[str]) -> list[dict]:
    return [faux_resultat(s, i + 1) for i, s in enumerate(sources)]


def main() -> None:
    verdicts: list[bool] = []

    def verifier(ok: bool, libelle: str) -> None:
        verdicts.append(ok)
        print(f"  [{'OK   ' if ok else 'ECHEC'}] {libelle}")

    # Le MEME ensemble de 20 candidats, dans deux ordres opposes. C'est
    # exactement ce que fait --rerank : il ne change pas l'ensemble, l'ordre.
    sources = ["a.md", "b.md"] + [f"z{i}.md" for i in range(18)]
    avant = mesures(classement(sources[::-1]), PERTINENTS, strict=False)
    apres = mesures(classement(sources), PERTINENTS, strict=False)

    print(f"\nMeme vivier de 20 candidats, deux ordres :")
    print(f"  rang du premier exact : {avant['rang']} -> {apres['rang']}")
    print(f"  nDCG@10               : {avant['ndcg'][10]:.4f} -> {apres['ndcg'][10]:.4f}\n")

    # 1. Le temoin de controle de --rerank. Reordonner ne peut pas faire
    #    apparaitre ni disparaitre un document du vivier.
    dans_top20 = lambda m: m["rang"] is not None and m["rang"] <= 20  # noqa: E731
    verifier(
        dans_top20(avant) == dans_top20(apres),
        "recall@20 invariant : le meme ensemble reste le meme ensemble",
    )

    # 2. Le MRR et le nDCG, eux, DOIVENT bouger — sinon ils ne mesureraient
    #    pas le classement.
    verifier(
        avant["rang"] != apres["rang"] and avant["ndcg"][10] < apres["ndcg"][10],
        "MRR et nDCG sensibles a l'ordre",
    )

    # 3. Borne haute : un classement parfait vaut exactement 1, pas 0,999.
    parfait = mesures(classement(["a.md", "b.md"]), PERTINENTS, strict=False)
    verifier(
        abs(parfait["ndcg"][10] - 1.0) < 1e-12,
        f"classement parfait -> nDCG = {parfait['ndcg'][10]:.6f}",
    )

    # 4. Deduplication par source. Sans elle, trois chunks du meme fichier
    #    cumuleraient un gain de 3 x 3 = 9 la ou l'ideal en prevoit 3, et le
    #    nDCG passerait au-dessus de 1 — une valeur qui n'a aucun sens.
    triple = classement(["a.md", "a.md", "a.md", "b.md"])
    m = mesures(triple, PERTINENTS, strict=False)
    verifier(
        m["gains"] == [2, 0, 0, 1] and m["ndcg"][10] <= 1.0 + 1e-12,
        f"dedup par source : gains {m['gains']}, nDCG {m['ndcg'][10]:.6f} (jamais > 1)",
    )

    # 5. Le seuil des mesures binaires. Un voisin de pertinence 1 ne doit pas
    #    compter comme un succes pour recall@k et le MRR, mais doit valoir un
    #    credit partiel au nDCG.
    voisin = mesures(classement(["b.md"]), PERTINENTS, strict=False)
    verifier(
        voisin["rang"] is None and voisin["ndcg"][10] > 0,
        f"voisin seul : rang={voisin['rang']} (aucun succes), "
        f"nDCG={voisin['ndcg'][10]:.4f} (credit partiel)",
    )

    print()
    if all(verdicts):
        print(f"{len(verdicts)}/{len(verdicts)} — toutes les proprietes tiennent.")
    else:
        raise SystemExit(
            f"{verdicts.count(False)}/{len(verdicts)} propriete(s) fausse(s)."
        )


if __name__ == "__main__":
    main()
