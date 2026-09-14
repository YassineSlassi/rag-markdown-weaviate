"""Bloc 3 — un .md classique contre un DoclingDocument, sur le meme contenu.

    python bloc3_document.py cours.pdf

La question : qu'est-ce que le DoclingDocument a de plus que le Markdown qu'on
en exporte ? Ce script met les deux cote a cote sur les MEMES elements.
"""

from __future__ import annotations

import json
import logging
import sys
from collections import Counter
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

logging.getLogger().setLevel(logging.ERROR)

# Ce que le Markdown sait dire. Tout le reste est une information que l'export
# Markdown ne peut PAS porter : elle existe dans l'arbre et disparait a l'export.
MARKDOWN_SAIT_DIRE = {"title", "section_header", "text", "list_item", "table", "code"}


def decrire(item) -> list[tuple[str, str]]:
    """Tout ce que le DoclingDocument sait d'un element."""
    champs = [("label", str(item.label))]
    texte = getattr(item, "text", None)
    if texte:
        champs.append(("text", repr(texte[:60])))
    if getattr(item, "level", None) is not None:
        champs.append(("level", str(item.level)))
    if getattr(item, "prov", None):
        p = item.prov[0]
        champs.append(("page_no", str(p.page_no)))
        b = p.bbox
        champs.append(
            ("bbox", f"l={b.l:.0f} t={b.t:.0f} r={b.r:.0f} b={b.b:.0f}")
        )
    champs.append(("self_ref", item.self_ref))
    if getattr(item, "parent", None) is not None:
        champs.append(("parent", item.parent.cref))
    return champs


def main() -> None:
    chemin = Path(sys.argv[1] if len(sys.argv) > 1 else "documents/cours.pdf").resolve()

    options = PdfPipelineOptions()
    options.do_ocr = False  # etabli au bloc 2 : sans effet ici, 3x plus rapide
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
    )
    doc = converter.convert(chemin).document
    markdown = doc.export_to_markdown()

    # =========================================================================
    # 1. LE MEME TITRE, DANS LES DEUX FORMES
    # =========================================================================
    print("=" * 76)
    print("  1. UN TITRE")
    print("=" * 76)
    titre = next(t for t in doc.texts if str(t.label) == "section_header")
    ligne_md = next(
        (l for l in markdown.splitlines() if titre.text[:25] in l and l.startswith("#")),
        "(introuvable)",
    )
    print(f"\n  en Markdown, une seule ligne :\n      {ligne_md[:70]}")
    print("\n  dans le DoclingDocument :")
    for cle, valeur in decrire(titre):
        print(f"      {cle:<10} {valeur}")

    # =========================================================================
    # 2. CE QUE LE MARKDOWN NE SAIT PAS DIRE
    # =========================================================================
    print()
    print("=" * 76)
    print("  2. LES ETIQUETTES QUE LE MARKDOWN NE PEUT PAS PORTER")
    print("=" * 76)
    etiquettes = Counter(str(t.label) for t in doc.texts)
    for etiquette, n in etiquettes.most_common():
        sait = "" if etiquette in MARKDOWN_SAIT_DIRE else "   <- perdu a l'export"
        print(f"      {n:4d}  {etiquette:<18}{sait}")

    perdus = [t for t in doc.texts if str(t.label) not in MARKDOWN_SAIT_DIRE]
    if perdus:
        print("\n  exemple d'element dont l'etiquette disparait :")
        for cle, valeur in decrire(perdus[0]):
            print(f"      {cle:<10} {valeur}")
        print("\n  En Markdown ce sera du texte ordinaire, indistinguable d'un")
        print("  paragraphe. Impossible de le filtrer avant de decouper.")

    # =========================================================================
    # 3. UNE CELLULE FUSIONNEE
    # =========================================================================
    print()
    print("=" * 76)
    print("  3. UNE CELLULE FUSIONNEE")
    print("=" * 76)
    table = doc.tables[0]
    fusionnee = next(
        (c for c in table.data.table_cells if c.col_span > 1), None
    )
    if fusionnee is not None:
        print("\n  dans le DoclingDocument :")
        print(f"      text          {fusionnee.text!r}")
        print(f"      col_span      {fusionnee.col_span}")
        print(f"      row_span      {fusionnee.row_span}")
        print(f"      column_header {fusionnee.column_header}")
        print(f"      lignes {fusionnee.start_row_offset_idx} -> "
              f"{fusionnee.end_row_offset_idx}, colonnes "
              f"{fusionnee.start_col_offset_idx} -> {fusionnee.end_col_offset_idx}")
        print("\n  en Markdown : un tableau n'a droit qu'a UNE ligne d'en-tete,")
        print("  sans fusion. L'export aplatit les deux lignes en les collant :")
        ligne = next(
            (l for l in markdown.splitlines() if fusionnee.text[:20] in l and "|" in l),
            "(introuvable)",
        )
        print(f"      {ligne[:70]}...")

    # =========================================================================
    # 4. L'ALLER-RETOUR
    # =========================================================================
    print()
    print("=" * 76)
    print("  4. CE QUI SE SERIALISE, ET CE QUI SE RECHARGE")
    print("=" * 76)
    dictionnaire = doc.export_to_dict()
    json_texte = json.dumps(dictionnaire, ensure_ascii=False)
    print(f"\n      Markdown : {len(markdown):7d} caracteres")
    print(f"      JSON     : {len(json_texte):7d} caracteres  "
          f"({len(json_texte) / len(markdown):.1f}x plus gros)")
    print("\n  Le JSON se recharge a l'identique, le Markdown non :")

    from docling_core.types.doc.document import DoclingDocument

    recharge = DoclingDocument.model_validate(dictionnaire)
    print(f"      elements de texte apres rechargement : {len(recharge.texts)} "
          f"(contre {len(doc.texts)})")
    print(f"      tableaux                             : {len(recharge.tables)} "
          f"(contre {len(doc.tables)})")
    print("\n  C'est ce qui permet de convertir UNE fois et de re-decouper")
    print("  autant de fois qu'on veut, sans repayer les 30 secondes de vision.")


if __name__ == "__main__":
    main()
