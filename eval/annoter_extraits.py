"""Verifie les annotations et remplit le champ `extrait` de questions.json.

    python eval/annoter_extraits.py

Deux garanties apportees :
  1. chaque `source` annotee existe reellement dans le corpus ;
  2. chaque `extrait` est un fragment VERIFIE present dans le fichier source.

Le second point compte : un extrait ecrit a la main qui ne correspond a rien
ferait echouer toutes les questions concernees, et on croirait a tort que le
retriever est mauvais. On ne fait donc jamais confiance a une ancre non verifiee.
"""

import json
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
QUESTIONS = Path(__file__).parent / "questions.json"

# Un bon extrait est du texte simple : ni macro MDN, ni balise HTML, ni lien
# Markdown, ni code. Ces elements survivent mal au chunking et a un eventuel
# nettoyage, donc une ancre qui en contient serait fragile.
INTERDIT = re.compile(r"\{\{|<|\[|`|\|")

MIN_LONGUEUR = 45
MAX_LONGUEUR = 130


def corps_du_fichier(chemin: Path) -> str:
    texte = chemin.read_text(encoding="utf-8")
    parts = texte.split("---", 2)
    return parts[2] if len(parts) >= 3 else texte


def choisir_extrait(corps: str) -> str:
    """Rend le premier fragment de texte simple assez long pour ancrer."""
    for phrase in re.split(r"(?<=[.!?])\s+", corps):
        phrase = " ".join(phrase.split())
        if INTERDIT.search(phrase):
            continue
        if MIN_LONGUEUR <= len(phrase) <= MAX_LONGUEUR:
            return phrase
        if len(phrase) > MAX_LONGUEUR:
            # Trop longue : on coupe a la derniere espace avant la limite,
            # pour ne pas terminer au milieu d'un mot.
            coupe = phrase[:MAX_LONGUEUR].rsplit(" ", 1)[0]
            if len(coupe) >= MIN_LONGUEUR:
                return coupe
    return ""


def main() -> None:
    import sys

    fichier = Path(sys.argv[1]) if len(sys.argv) > 1 else QUESTIONS
    data = json.loads(fichier.read_text(encoding="utf-8"))
    corpus = RACINE / data["corpus"]

    manquants, sans_ancre, ok = [], [], 0

    for q in data["questions"]:
        for pertinent in q["pertinents"]:
            chemin = corpus / pertinent["source"]
            if not chemin.is_file():
                manquants.append((q["id"], pertinent["source"]))
                continue

            corps = corps_du_fichier(chemin)
            extrait = choisir_extrait(corps)

            # Verification finale : l'ancre DOIT se retrouver dans le fichier,
            # espaces normalises comme le fera le comparateur a l'evaluation.
            normalise = " ".join(corps.split())
            if extrait and extrait in normalise:
                pertinent["extrait"] = extrait
                ok += 1
            else:
                pertinent["extrait"] = ""
                sans_ancre.append((q["id"], pertinent["source"]))

    fichier.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    total = sum(len(q["pertinents"]) for q in data["questions"])
    print(f"{len(data['questions'])} questions, {total} annotations")
    print(f"  ancres verifiees : {ok}")
    print(f"  sans ancre (correspondance au fichier seul) : {len(sans_ancre)}")

    if manquants:
        print("\n  FICHIERS ANNOTES INTROUVABLES — a corriger :")
        for qid, source in manquants:
            print(f"    {qid} -> {source}")
    else:
        print("\n  toutes les sources annotees existent dans le corpus")

    if sans_ancre:
        print("\n  pas de fragment simple assez long (le fichier est court ou")
        print("  trop dense en macros) — la correspondance se fera au fichier :")
        for qid, source in sans_ancre:
            print(f"    {qid} -> {source}")


if __name__ == "__main__":
    main()
