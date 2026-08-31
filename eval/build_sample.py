"""Construit un echantillon reproductible du glossaire MDN pour l'evaluation.

    python eval/build_sample.py

Le tirage est fige par SEED : relancer ce script redonne exactement les memes
fiches. C'est indispensable pour qu'une comparaison de reglages de chunking
porte sur le meme corpus.
"""

import json
import random
import shutil
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SOURCE = RACINE / "translated-content" / "files" / "fr" / "glossary"
DESTINATION = RACINE / "eval" / "corpus150"
SELECTION = Path(__file__).parent / "selection.json"

SEED = 20260831
NB_FICHES = 150

# Une fiche trop courte ne porte pas assez de matiere pour une question ;
# une fiche geante est un cas particulier. On borne pour rester representatif.
MIN_CARACTERES = 400
MAX_CARACTERES = 12000


def main() -> None:
    candidats = []
    for dossier in sorted(SOURCE.iterdir()):
        fichier = dossier / "index.md"
        if not fichier.is_file():
            continue
        taille = len(fichier.read_text(encoding="utf-8"))
        if MIN_CARACTERES <= taille <= MAX_CARACTERES:
            candidats.append(dossier.name)

    print(f"{len(candidats)} fiches eligibles sur {len(list(SOURCE.iterdir()))}")

    rng = random.Random(SEED)
    choisies = sorted(rng.sample(candidats, min(NB_FICHES, len(candidats))))

    if DESTINATION.exists():
        shutil.rmtree(DESTINATION)
    DESTINATION.mkdir(parents=True)

    total = 0
    for terme in choisies:
        cible = DESTINATION / terme
        cible.mkdir()
        contenu = (SOURCE / terme / "index.md").read_text(encoding="utf-8")
        (cible / "index.md").write_text(contenu, encoding="utf-8")
        total += len(contenu)

    SELECTION.write_text(
        json.dumps({"seed": SEED, "termes": choisies}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"{len(choisies)} fiches copiees dans {DESTINATION.relative_to(RACINE)}")
    print(f"{total // 1024} Ko au total, ~{total // 4000} chunks attendus")
    print(f"selection enregistree dans {SELECTION.relative_to(RACINE)} (seed={SEED})")


if __name__ == "__main__":
    main()
