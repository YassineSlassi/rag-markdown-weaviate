"""Bloc 2 bis — confirmer le seul resultat qui sortait du bruit, sans mourir.

    python bloc2b_verif_ocr.py cours.pdf

Le bloc 2 a donne cinq mesures dont quatre tiennent dans un mouchoir (0.89x a
1.06x) : indiscernables du bruit sur un seul essai. Une seule est franche :
sans OCR, deux fois plus vite. Trois questions :

  1. L'ecart tient-il sur plusieurs essais ?
  2. Sort-on VRAIMENT le meme document ? On compare les Markdown au SHA : un
     gain de temps qui change le texte n'est pas un gain, c'est un compromis.
  3. Le ralentissement de `sans tableaux` s'explique-t-il par l'OCR qui
     recupere les regions que TableFormer ne reclame plus ? Si oui,
     `sans tableaux + sans OCR` doit passer SOUS `sans OCR` seul.

Chaque conversion tourne dans un sous-processus. Pas par gout de la
complexite : la version precedente de ce script est morte en segmentation
fault, et un segfault n'est pas rattrapable depuis Python. C'est aussi la
bonne architecture pour une ingestion reelle — un PDF pathologique doit
casser sa conversion, pas ton serveur.
"""

from __future__ import annotations

import json
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

ESSAIS = 2
# sys.executable, et surtout pas un chemin en dur : c'est le meme
# interpreteur que celui qui execute ce script, donc le bon venv, sur
# n'importe quelle machine.
PYTHON = sys.executable
OUVRIER = Path(__file__).parent / "ouvrier.py"


def mesurer(chemin: Path, drapeaux: list[str]) -> list[dict]:
    """Lance ESSAIS conversions isolees. Un crash rend un dict d'echec."""
    releves = []
    for _ in range(ESSAIS):
        with tempfile.TemporaryDirectory() as tmp:
            fichier = Path(tmp) / "resume.json"
            proc = subprocess.run(
                [PYTHON, str(OUVRIER), str(chemin), str(fichier), *drapeaux],
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0 or not fichier.is_file():
                # returncode negatif ou 139 : le processus a ete tue par un
                # signal, pas termine par une exception.
                releves.append({"crash": proc.returncode})
            else:
                releves.append(json.loads(fichier.read_text(encoding="utf-8")))
    return releves


def main() -> None:
    chemin = Path(sys.argv[1] if len(sys.argv) > 1 else "documents/cours.pdf").resolve()

    configurations = [
        ("OCR actif (defaut)", []),
        ("OCR desactive", ["--no-ocr"]),
        ("sans tableaux + sans OCR", ["--no-ocr", "--no-tables"]),
    ]

    resultats: dict[str, list[dict]] = {}
    for libelle, drapeaux in configurations:
        print(f"  {libelle:<26}", end=" ", flush=True)
        releves = mesurer(chemin, drapeaux)
        resultats[libelle] = releves
        print(" ".join(
            f"CRASH({r['crash']})" if "crash" in r else f"{r['duree']:.1f}s"
            for r in releves
        ))

    print("\n" + "=" * 72)
    print(f"  {'configuration':<26} {'mediane':>9} {'etendue':>8} "
          f"{'cell.':>6} {'markdown':>9}  sha")
    print("-" * 72)
    medianes: dict[str, float] = {}
    for libelle, releves in resultats.items():
        bons = [r for r in releves if "crash" not in r]
        if not bons:
            print(f"  {libelle:<26}  toutes les tentatives ont crashe")
            continue
        durees = [r["duree"] for r in bons]
        medianes[libelle] = statistics.median(durees)
        r = bons[0]
        print(f"  {libelle:<26} {medianes[libelle]:8.1f}s "
              f"{max(durees) - min(durees):7.1f}s {r['cellules']:6d} "
              f"{r['markdown_len']:9d}  {r['markdown_sha']}")

    # Question 1 et 2.
    avec, sans = "OCR actif (defaut)", "OCR desactive"
    if avec in medianes and sans in medianes:
        print(f"\n  rapport des medianes avec/sans OCR : "
              f"{medianes[avec] / medianes[sans]:.2f}x")
        sha_avec = next(r["markdown_sha"] for r in resultats[avec] if "crash" not in r)
        sha_sans = next(r["markdown_sha"] for r in resultats[sans] if "crash" not in r)
        if sha_avec == sha_sans:
            print("  Markdown IDENTIQUES au caractere pres : sur ce document,")
            print("  l'OCR a coute les deux tiers du temps pour ne rien apporter.")
        else:
            print("  Markdown DIFFERENTS : desactiver l'OCR est un compromis,")
            print("  pas un gain gratuit. A verifier document par document.")

    # Question 3.
    combo = "sans tableaux + sans OCR"
    if combo in medianes and sans in medianes:
        print()
        if medianes[combo] < medianes[sans]:
            print(f"  {combo} ({medianes[combo]:.1f}s) passe SOUS "
                  f"{sans} ({medianes[sans]:.1f}s) :")
            print("  l'hypothese tient, c'est bien l'OCR qui ramassait les")
            print("  regions abandonnees par TableFormer.")
        else:
            print(f"  {combo} ({medianes[combo]:.1f}s) ne passe PAS sous "
                  f"{sans} ({medianes[sans]:.1f}s) :")
            print("  l'hypothese tombe, le ralentissement vient d'ailleurs.")


if __name__ == "__main__":
    main()
