"""Bloc 2 — ou part le temps, et ce que chaque parametre coute vraiment.

    python bloc2_parametres.py cours.pdf

Le bloc 1 a converti 4 pages en 151 secondes. C'est enorme, et tant qu'on ne
sait pas OU part ce temps, regler des parametres revient a tirer au hasard.

Ce script fait deux choses :
  1. Il active le PROFILAGE. Les `timings` d'un ConversionResult sont vides par
     defaut : Docling ne les collecte que si on le lui demande, parce que
     chronometrer chaque etage coute lui-meme un peu. C'est le seul reglage a
     activer AVANT la conversion et pas via PdfPipelineOptions.
  2. Il compare plusieurs configurations sur le MEME fichier, en mesurant a la
     fois le temps ET ce qu'on perd. Un parametre qui divise le temps par
     trois mais fait disparaitre les tableaux n'est pas un gain.

Meme demarche que le banc d'essai du reranker : on ne discute pas des
parametres, on les mesure.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.datamodel.settings import settings
from docling.document_converter import DocumentConverter, PdfFormatOption

# TableFormer est bavard : il previent pour chaque cellule qu'il a du rattraper.
# On garde ces avertissements pour le bloc 4, ici ils noieraient les mesures.
logging.getLogger("docling").setLevel(logging.ERROR)
logging.getLogger("docling_ibm_models").setLevel(logging.ERROR)

# LE reglage a connaitre : sans lui, resultat.timings reste vide.
settings.debug.profile_pipeline_timings = True


def convertir(chemin: Path, options: PdfPipelineOptions) -> tuple[float, dict]:
    """Convertit et rend (duree, resume de ce qui a ete produit).

    `format_options` est le point d'entree de TOUT le reglage de Docling. La
    cle dit a quel format d'entree les options s'appliquent : un meme
    DocumentConverter peut traiter PDF, DOCX et PPTX avec des reglages
    differents pour chacun. D'ou le dictionnaire plutot qu'un argument simple.
    """
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
    )
    debut = time.perf_counter()
    resultat = converter.convert(chemin)
    duree = time.perf_counter() - debut

    doc = resultat.document
    # Le nombre de CELLULES, pas seulement de tableaux : un tableau reconnu
    # mais vide compterait pareil dans len(doc.tables). C'est la mesure qui
    # dirait si un reglage a degrade la reconnaissance sans la faire echouer.
    cellules = sum(len(t.data.table_cells) for t in doc.tables)
    resume = {
        "statut": str(resultat.status).split(".")[-1],
        "textes": len(doc.texts),
        "tableaux": len(doc.tables),
        "cellules": cellules,
        "markdown": len(doc.export_to_markdown()),
        "timings": {
            nom: sum(t.times) for nom, t in (resultat.timings or {}).items()
        },
    }
    return duree, resume


def main() -> None:
    chemin = Path(sys.argv[1] if len(sys.argv) > 1 else "documents/cours.pdf")
    if not chemin.is_file():
        raise SystemExit(f"Fichier introuvable : {chemin}")

    coeurs = os.cpu_count() or 4
    print(f"{coeurs} coeurs logiques disponibles ; Docling en prend 4 par defaut.\n")

    # -------------------------------------------------------------------------
    # Les configurations a comparer. Chacune ne change QU'UNE chose par rapport
    # a la precedente : c'est ce qui rend la comparaison lisible.
    # -------------------------------------------------------------------------
    def defaut() -> PdfPipelineOptions:
        return PdfPipelineOptions()

    def tableaux_rapides() -> PdfPipelineOptions:
        o = PdfPipelineOptions()
        o.table_structure_options.mode = TableFormerMode.FAST
        return o

    def sans_ocr() -> PdfPipelineOptions:
        o = PdfPipelineOptions()
        o.do_ocr = False
        return o

    def sans_tableaux() -> PdfPipelineOptions:
        o = PdfPipelineOptions()
        o.do_table_structure = False
        return o

    def tous_les_coeurs() -> PdfPipelineOptions:
        o = PdfPipelineOptions()
        o.accelerator_options.num_threads = coeurs
        return o

    configurations = [
        ("defauts", defaut),
        ("tableaux FAST", tableaux_rapides),
        ("sans OCR", sans_ocr),
        ("sans tableaux", sans_tableaux),
        (f"{coeurs} threads", tous_les_coeurs),
    ]

    mesures: list[tuple[str, float, dict]] = []
    for nom, fabrique in configurations:
        print(f"  {nom}...", end=" ", flush=True)
        duree, resume = convertir(chemin, fabrique())
        print(f"{duree:.1f}s")
        mesures.append((nom, duree, resume))

    # -------------------------------------------------------------------------
    # Ou part le temps, sur la configuration par defaut.
    # -------------------------------------------------------------------------
    timings = mesures[0][2]["timings"]
    if timings:
        print("\n" + "=" * 74)
        print("  OU PART LE TEMPS (configuration par defaut)")
        print("-" * 74)
        total = max(timings.values()) if timings else 1.0
        for nom, secondes in sorted(timings.items(), key=lambda kv: -kv[1]):
            part = 100 * secondes / total if total else 0
            barre = "#" * int(part / 3)
            print(f"  {secondes:7.1f}s  {part:5.1f}%  {barre:<34} {nom}")

    # -------------------------------------------------------------------------
    # Le tableau de comparaison. Le temps A COTE de ce qui a ete produit : un
    # gain de temps qui fait tomber `cellules` est une perte deguisee.
    # -------------------------------------------------------------------------
    reference = mesures[0]
    print("\n" + "=" * 74)
    print("  COMPARAISON  (par rapport aux defauts)")
    print("-" * 74)
    print(f"  {'configuration':<16} {'temps':>8} {'gain':>7}  "
          f"{'textes':>7} {'tabl.':>6} {'cell.':>7} {'markdown':>9}")
    for nom, duree, resume in mesures:
        gain = reference[1] / duree if duree else 0
        drapeau = ""
        if resume["cellules"] < reference[2]["cellules"]:
            drapeau = "  <-- PERTE de cellules"
        if resume["tableaux"] < reference[2]["tableaux"]:
            drapeau = "  <-- PERTE de tableaux"
        print(f"  {nom:<16} {duree:7.1f}s {gain:6.2f}x  "
              f"{resume['textes']:7d} {resume['tableaux']:6d} "
              f"{resume['cellules']:7d} {resume['markdown']:9d}{drapeau}")


if __name__ == "__main__":
    main()
