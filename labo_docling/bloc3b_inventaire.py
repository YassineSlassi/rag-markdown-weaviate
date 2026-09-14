"""Bloc 3 bis — voir les 33 elements un par un, au lieu de les compter.

    python bloc3b_inventaire.py cours.pdf

Au passage, ce script met en pratique l'aller-retour JSON du bloc 3 : la
premiere execution convertit (30 s) et ecrit cours.docling.json ; les
suivantes rechargent le fichier et sont instantanees. C'est exactement ce
qu'il faudra faire dans une vraie ingestion : payer la vision UNE fois.
"""

from __future__ import annotations

import json
import logging
import sys
from collections import Counter
from pathlib import Path

from docling_core.types.doc.document import DoclingDocument

logging.getLogger().setLevel(logging.ERROR)


def obtenir(chemin: Path) -> DoclingDocument:
    cache = chemin.with_suffix(".docling.json")
    if cache.is_file():
        print(f"  rechargé depuis {cache.name} (pas de conversion)\n")
        return DoclingDocument.model_validate(
            json.loads(cache.read_text(encoding="utf-8"))
        )

    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    options = PdfPipelineOptions()
    options.do_ocr = False
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
    )
    print("  conversion en cours...")
    doc = converter.convert(chemin).document
    cache.write_text(
        json.dumps(doc.export_to_dict(), ensure_ascii=False), encoding="utf-8"
    )
    print(f"  converti, et mis en cache dans {cache.name}\n")
    return doc


def main() -> None:
    chemin = Path(sys.argv[1] if len(sys.argv) > 1 else "documents/cours.pdf").resolve()
    doc = obtenir(chemin)

    # -------------------------------------------------------------------------
    # Les 33 elements de doc.texts, un par un.
    # -------------------------------------------------------------------------
    print("=" * 78)
    print(f"  doc.texts — {len(doc.texts)} elements")
    print("=" * 78)
    for i, item in enumerate(doc.texts):
        page = item.prov[0].page_no if item.prov else "?"
        texte = (item.text or "").replace("\n", " ")
        print(f"  {i:3d}  p{page}  {str(item.label):<15} {texte[:52]!r}")

    # -------------------------------------------------------------------------
    # Les autres listes. Les tableaux ne sont PAS dans doc.texts.
    # -------------------------------------------------------------------------
    print()
    print("=" * 78)
    print("  LES AUTRES LISTES DU DOCUMENT")
    print("=" * 78)
    print(f"  doc.tables   : {len(doc.tables)} elements")
    for i, t in enumerate(doc.tables):
        page = t.prov[0].page_no if t.prov else "?"
        print(f"      {i}  p{page}  {t.data.num_rows}x{t.data.num_cols}, "
              f"{len(t.data.table_cells)} cellules")
    print(f"  doc.pictures : {len(doc.pictures)} elements")
    print(f"  doc.groups   : {len(doc.groups)} elements")
    for g in doc.groups:
        print(f"      {str(g.label):<12} {len(g.children)} enfants")

    # -------------------------------------------------------------------------
    # Le total reel, toutes listes confondues.
    # -------------------------------------------------------------------------
    print()
    print("=" * 78)
    print("  CE QUE COMPTAIT LE TABLEAU DU BLOC 3")
    print("=" * 78)
    for etiquette, n in Counter(str(t.label) for t in doc.texts).most_common():
        print(f"      {n:4d}  {etiquette}")
    print(f"      ----")
    print(f"      {len(doc.texts):4d}  total de doc.texts")
    print(f"\n  ... plus {len(doc.tables)} tableaux, qui vivent dans doc.tables")
    print(f"  et n'apparaissaient donc PAS dans ce decompte.")


if __name__ == "__main__":
    main()
