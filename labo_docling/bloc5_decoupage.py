"""Bloc 5 — les decoupeurs de Docling, contre la passe en deux temps du projet.

    python labo_docling/bloc5_decoupage.py labo_docling/documents/cours.pdf

L'inventaire du bloc 3 bis a montre le probleme : un element `text` n'est PAS
un paragraphe. Sur le cobaye, une phrase etait coupee en 4 elements (un par
ligne a l'ecran), et des cellules de tableau s'etaient echappees en elements
isoles ('92', 'virtuel'). Un chunk par element donnerait des chunks
inexploitables.

Docling fournit deux decoupeurs pour recoller tout ca :

  HierarchicalChunker — suit l'ARBRE. Un chunk par groupe structurel, sans
                        aucune limite de taille. Il recolle les elements
                        voisins d'une meme section, et rend un tableau ENTIER
                        en un seul chunk.

  HybridChunker       — le precedent, plus deux passes :
                        1. il DECOUPE ce qui depasse la limite de jetons du
                           modele d'embedding ;
                        2. il FUSIONNE les chunks voisins trop petits
                           (merge_peers).

La nuance qui compte : la limite est comptee avec le tokenizer du modele
d'embedding, pas en caracteres. C'est la difference avec CHUNK_SIZE de
rag_pipeline, qui compte des caracteres et ne peut donc que viser large.
"""

from __future__ import annotations

import json
import logging
import statistics
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from docling_core.types.doc.document import DoclingDocument  # noqa: E402

logging.getLogger().setLevel(logging.ERROR)

# Le tokenizer du modele d'embedding du projet. C'est LUI qui arbitre la taille
# des chunks — en JETONS, pas en caracteres, ce qui est toute la difference
# avec CHUNK_SIZE de rag_pipeline.
#
# Attention a ne pas se tromper de raison. BGE-M3 accepte 8192 jetons
# (verifie : sentence_bert_config.json, max_seq_length 8192), donc la
# troncature n'est PAS la contrainte qui mord. La vraie raison est celle que
# rag_pipeline.py documente deja : un chunk large dilue son vecteur sur
# plusieurs idees, et retrouve moins bien.
#
# On aligne donc le budget sur le CHUNK_SIZE du projet pour que la comparaison
# soit honnete. Mesure sur ce corpus : 2,93 caracteres par jeton en francais,
# donc 1000 caracteres ~ 340 jetons. On essaie les deux budgets pour voir ce
# que le parametre change.
MODELE = "BAAI/bge-m3"
BUDGETS = [340, 512]


def obtenir(chemin: Path) -> DoclingDocument:
    """Recharge le cache JSON s'il existe, convertit sinon.

    Illustre l'aller-retour du bloc 3 : convertir coute 30 s, recharger est
    instantane, et le document recharge est stric­tement le meme.
    """
    cache = chemin.with_suffix(".docling.json")
    if cache.is_file():
        print(f"  document rechargé depuis {cache.name}\n")
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
    print("  conversion (30 s environ)...")
    doc = converter.convert(chemin).document
    cache.write_text(
        json.dumps(doc.export_to_dict(), ensure_ascii=False), encoding="utf-8"
    )
    print(f"  converti, mis en cache dans {cache.name}\n")
    return doc


def resumer(nom: str, chunks: list, contextualiser, tokenizer=None) -> dict:
    """Les mesures qui disent si un decoupage est exploitable.

    La MEDIANE dit si le decoupage a mordu — meme lecture que le --dry-run de
    la CLI. Le nombre de chunks MINUSCULES (< 80 caracteres) est l'indicateur
    qui compte ici : ce sont les '92' et les 'Michigan.', ceux qu'aucun
    embedding ne saura rattraper.
    """
    textes = [contextualiser(c) for c in chunks]
    longueurs = [len(t) for t in textes]
    # Le maximum en JETONS est la seule facon de verifier qu'un budget a bien
    # ete respecte : compter des caracteres ne le dit pas.
    jetons_max = (
        max(len(tokenizer.encode(t)) for t in textes)
        if tokenizer is not None and textes
        else 0
    )
    return {
        "nom": nom,
        "n": len(chunks),
        "mediane": int(statistics.median(longueurs)) if longueurs else 0,
        "mini": min(longueurs) if longueurs else 0,
        "maxi": max(longueurs) if longueurs else 0,
        "jetons_max": jetons_max,
        "minuscules": sum(1 for n in longueurs if n < 80),
        "textes": textes,
        "chunks": chunks,
    }


def main() -> None:
    defaut = RACINE / "labo_docling" / "documents" / "cours.pdf"
    chemin = Path(sys.argv[1]) if len(sys.argv) > 1 else defaut
    doc = obtenir(chemin.resolve())

    from docling.chunking import HierarchicalChunker, HybridChunker
    from docling_core.transforms.chunker.tokenizer.huggingface import (
        HuggingFaceTokenizer,
    )
    from transformers import AutoTokenizer

    resultats = []
    brut = AutoTokenizer.from_pretrained(MODELE)

    # -------------------------------------------------------------------------
    # 0. Le temoin : un chunk par element de l'arbre, sans rien recoller.
    #    C'est ce qu'on obtiendrait "naivement", et c'est le repere qui rend
    #    les deux decoupeurs lisibles.
    # -------------------------------------------------------------------------
    naifs = [t for t in doc.texts if (t.text or "").strip()]
    resultats.append(
        resumer("naif (1 element = 1 chunk)", naifs, lambda t: t.text, brut)
    )

    # -------------------------------------------------------------------------
    # 1. HierarchicalChunker : suit l'arbre, aucune limite de taille.
    # -------------------------------------------------------------------------
    hierarchique = HierarchicalChunker()
    chunks_h = list(hierarchique.chunk(doc))
    resultats.append(
        resumer("HierarchicalChunker", chunks_h, hierarchique.contextualize, brut)
    )

    # -------------------------------------------------------------------------
    # 2. HybridChunker : decoupe ce qui deborde, fusionne ce qui est trop petit.
    # -------------------------------------------------------------------------
    hybride = None
    for budget in BUDGETS:
        hybride = HybridChunker(
            tokenizer=HuggingFaceTokenizer(tokenizer=brut, max_tokens=budget),
            merge_peers=True,
        )
        chunks_y = list(hybride.chunk(doc))
        resultats.append(
            resumer(
                f"HybridChunker ({budget} jetons)",
                chunks_y,
                hybride.contextualize,
                brut,
            )
        )

    # -------------------------------------------------------------------------
    # Le tableau de comparaison.
    # -------------------------------------------------------------------------
    print("=" * 78)
    print("  TROIS DECOUPAGES DU MEME DOCUMENT")
    print("-" * 78)
    print(f"  {'':<28} {'chunks':>7} {'médiane':>8} {'mini':>6} "
          f"{'maxi':>6} {'jetons max':>11} {'< 80 car.':>10}")
    for r in resultats:
        print(f"  {r['nom']:<28} {r['n']:7d} {r['mediane']:8d} {r['mini']:6d} "
              f"{r['maxi']:6d} {r['jetons_max']:11d} {r['minuscules']:10d}")

    # -------------------------------------------------------------------------
    # contextualize() : le fil d'Ariane, exactement comme dans rag_pipeline.
    # -------------------------------------------------------------------------
    print()
    print("=" * 78)
    print("  contextualize() — le meme principe que dans rag_pipeline")
    print("-" * 78)
    exemple = chunks_y[min(3, len(chunks_y) - 1)]
    print("\n  chunk.text brut :")
    print(f"      {exemple.text[:150]!r}")
    print("\n  hybride.contextualize(chunk) — les titres sont recolles devant :")
    print(f"      {hybride.contextualize(exemple)[:150]!r}")
    print(f"\n  chunk.meta.headings : {exemple.meta.headings}")

    # La provenance survit au decoupage : chaque chunk sait de quelles pages il
    # vient. C'est ce qu'un pipeline Markdown ne peut pas offrir.
    pages = sorted({
        p.page_no
        for item in exemple.meta.doc_items
        for p in (item.prov or [])
    })
    print(f"  pages d'origine     : {pages}")

    # -------------------------------------------------------------------------
    # Les tableaux : entiers, ou disperses ?
    # -------------------------------------------------------------------------
    print()
    print("=" * 78)
    print("  UN TABLEAU, APRES DECOUPAGE")
    print("-" * 78)
    avec_table = next(
        (c for c in chunks_y
         if any(str(i.label) == "table" for i in c.meta.doc_items)),
        None,
    )
    if avec_table is not None:
        texte = hybride.contextualize(avec_table)
        print(f"\n  {len(texte)} caractères, titres : {avec_table.meta.headings}")
        print("  début du chunk :\n")
        for ligne in texte.splitlines()[:6]:
            print(f"      {ligne[:72]}")
    else:
        print("\n  aucun chunk ne porte de tableau.")

    # -------------------------------------------------------------------------
    # Les plus petits chunks produits, pour juger sur pieces.
    # -------------------------------------------------------------------------
    print()
    print("=" * 78)
    print("  LES 5 PLUS PETITS CHUNKS DE CHAQUE METHODE")
    print("-" * 78)
    for r in resultats:
        print(f"\n  {r['nom']}")
        for texte in sorted(r["textes"], key=len)[:5]:
            print(f"      {len(texte):4d} car.  {texte[:58]!r}")


if __name__ == "__main__":
    main()
