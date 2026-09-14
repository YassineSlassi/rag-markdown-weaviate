"""Convertit UN pdf et ecrit le resume en JSON. Concu pour etre tue.

    python ouvrier.py cours.pdf resume.json --no-ocr

Ce fichier existe parce qu'une conversion Docling peut faire tomber le
processus par segmentation fault : ce n'est pas une exception Python, aucun
try/except ne l'attrape. La seule parade est de mettre la conversion dans un
processus separe dont on surveille le code de sortie.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sys
import time
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

logging.getLogger("docling").setLevel(logging.ERROR)
logging.getLogger("docling_ibm_models").setLevel(logging.ERROR)

chemin, sortie = Path(sys.argv[1]), Path(sys.argv[2])
options = PdfPipelineOptions()
options.do_ocr = "--no-ocr" not in sys.argv
if "--no-tables" in sys.argv:
    options.do_table_structure = False

converter = DocumentConverter(
    format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
)
debut = time.perf_counter()
resultat = converter.convert(chemin)
duree = time.perf_counter() - debut

doc = resultat.document
markdown = doc.export_to_markdown()
sortie.write_text(
    json.dumps(
        {
            "duree": duree,
            "statut": str(resultat.status).split(".")[-1],
            "textes": len(doc.texts),
            "tableaux": len(doc.tables),
            "cellules": sum(len(t.data.table_cells) for t in doc.tables),
            "markdown_len": len(markdown),
            "markdown_sha": hashlib.sha256(markdown.encode()).hexdigest()[:16],
        }
    ),
    encoding="utf-8",
)
