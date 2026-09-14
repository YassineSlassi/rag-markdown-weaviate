"""Bloc 4 — l'etage des tableaux, et ses deux reglages.

    python bloc4_tableaux.py cours.pdf

Reconstruire un tableau depuis un PDF se fait en DEUX temps, et chaque temps a
son reglage. C'est la seule chose a retenir de ce bloc :

  temps 1 — TableFormer regarde l'IMAGE de la zone et predit une grille :
            combien de lignes, combien de colonnes, ou sont les fusions.
            Reglage : `mode` = ACCURATE (defaut) ou FAST.

  temps 2 — on range le VRAI texte du PDF dans cette grille.
            Reglage : `do_cell_matching` = True (defaut) ou False.

            True  : on prend le texte exact du PDF et on le met dans la case
                    predite. Texte fidele, mais si la grille predite deborde,
                    du texte etranger se fait aspirer dedans.
            False : on garde le texte que TableFormer a lui-meme lu sur
                    l'image. Pas de debordement, mais le texte vient d'un
                    modele de vision, donc faillible.

L'OCR est coupe ici : le bloc 2 a montre qu'il ne change rien sur ce document
et coute les deux tiers du temps.
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.document_converter import DocumentConverter, PdfFormatOption

logging.getLogger("docling").setLevel(logging.ERROR)


class Compteur(logging.Handler):
    """Compte les cellules que TableFormer n'a pas su placer.

    Leur nombre est LA mesure de la qualite de l'appariement : une cellule
    orpheline est un morceau de texte pour lequel la grille predite n'avait
    pas de case, et qu'on a range dans la ligne la plus proche faute de mieux.
    """

    def __init__(self) -> None:
        super().__init__()
        self.orphelines = 0

    def emit(self, record: logging.LogRecord) -> None:
        if "Orphan pdf_cell" in record.getMessage():
            self.orphelines += 1


# Le logger s'appelle "MatchingPostProcessor", pas "docling_ibm_models". On se
# branche donc sur la RACINE, qui voit passer tous les enregistrements, et on
# filtre sur le message. Deviner un nom de logger est une erreur MUETTE : le
# compteur reste a zero et on conclut qu'il n'y a pas de probleme.
compteur = Compteur()
logging.getLogger().addHandler(compteur)
logging.getLogger().setLevel(logging.WARNING)


def lignes(table, combien: int = 3) -> list[list[str]]:
    """Les `combien` premieres lignes du tableau, cellule par cellule.

    Une cellule qui s'etale sur plusieurs colonnes est annotee : c'est souvent
    la qu'est le probleme, une ligne de titre fusionnee que TableFormer a cru
    faire partie du tableau.
    """
    sortie = []
    for r in range(min(combien, table.data.num_rows)):
        cellules = [c for c in table.data.table_cells if c.start_row_offset_idx == r]
        cellules.sort(key=lambda c: c.start_col_offset_idx)
        sortie.append([
            repr(c.text) + (f"   <- s'etale sur {c.col_span} colonnes" if c.col_span > 1 else "")
            for c in cellules
        ])
    return sortie


def essayer(chemin: Path, mode: TableFormerMode, matching: bool) -> dict:
    options = PdfPipelineOptions()
    options.do_ocr = False
    options.table_structure_options.mode = mode
    options.table_structure_options.do_cell_matching = matching

    compteur.orphelines = 0
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
    )
    debut = time.perf_counter()
    doc = converter.convert(chemin).document
    return {
        "duree": time.perf_counter() - debut,
        "orphelines": compteur.orphelines,
        "tables": [
            {
                "dim": f"{t.data.num_rows}x{t.data.num_cols}",
                "cellules": len(t.data.table_cells),
                "lignes": lignes(t),
            }
            for t in doc.tables
        ],
    }


def main() -> None:
    chemin = Path(sys.argv[1] if len(sys.argv) > 1 else "documents/cours.pdf").resolve()

    configurations = [
        ("ACCURATE + matching (defaut)", TableFormerMode.ACCURATE, True),
        ("ACCURATE sans matching", TableFormerMode.ACCURATE, False),
        ("FAST + matching", TableFormerMode.FAST, True),
    ]

    resultats = []
    for libelle, mode, matching in configurations:
        r = essayer(chemin, mode, matching)
        resultats.append((libelle, r))
        print(f"  {libelle:<30} {r['duree']:5.1f}s   "
              f"{r['orphelines']:3d} cellules orphelines")

    print()
    print("=" * 78)
    print("  DIMENSIONS DES 5 TABLEAUX")
    print("-" * 78)
    for libelle, r in resultats:
        dims = "  ".join(f"{t['dim']:>7}" for t in r["tables"])
        print(f"  {libelle:<30} {dims}")

    print()
    print("=" * 78)
    print("  LES 3 PREMIERES LIGNES DU TABLEAU 1 - celui qui a avale son titre")
    print("-" * 78)
    for libelle, r in resultats:
        print()
        print(f"  {libelle}")
        for i, ligne in enumerate(r["tables"][0]["lignes"]):
            print(f"      ligne {i} :")
            for cellule in ligne:
                print(f"          {cellule[:80]}")


if __name__ == "__main__":
    main()
