"""Bloc 1 — la conversion minimale, et ce qu'il y a vraiment dans un DoclingDocument.

    python bloc1_conversion.py cours.pdf

Trois idees a retenir, tout le reste en decoule :

  1. `DocumentConverter` se construit UNE fois et se reutilise. Il charge des
     modeles de vision (layout, TableFormer) : c'est lent au premier appel et
     gratuit ensuite. Le construire dans une boucle serait l'erreur classique.

  2. `convert()` ne rend pas un document mais un `ConversionResult` : le
     document EST dedans, avec a cote le statut, les erreurs et les temps par
     etage. C'est ce qui permet de savoir qu'une conversion a "reussi
     partiellement" au lieu de le decouvrir plus tard dans l'index.

  3. `DoclingDocument` n'est pas du texte, c'est un ARBRE d'elements types.
     Chaque element sait ce qu'il est (titre, paragraphe, tableau, legende) et
     d'ou il vient (page, boite englobante). Le Markdown n'est qu'une
     projection de cet arbre — celle qui jette le plus d'information.
"""

from __future__ import annotations

import sys
import time
from collections import Counter
from pathlib import Path

from docling.document_converter import DocumentConverter


def main() -> None:
    chemin = Path(sys.argv[1] if len(sys.argv) > 1 else "documents/cours.pdf")
    if not chemin.is_file():
        raise SystemExit(f"Fichier introuvable : {chemin}")

    # =========================================================================
    # 1. LA CONVERSION
    # =========================================================================
    # Aucun parametre : on prend le pipeline par defaut. C'est volontaire, on
    # veut d'abord voir ce que Docling fait tout seul avant de regler quoi que
    # ce soit. Les defauts valent : layout OUI, tableaux OUI (mode ACCURATE),
    # OCR OUI mais seulement la ou il manque une couche texte, enrichissements
    # NON (code, formules, images : tous desactives).
    print("Construction du DocumentConverter...")
    debut = time.perf_counter()
    converter = DocumentConverter()
    print(f"  pret en {time.perf_counter() - debut:.1f}s")

    print(f"\nConversion de {chemin.name} ({chemin.stat().st_size / 1024:.0f} Ko)...")
    debut = time.perf_counter()
    resultat = converter.convert(chemin)
    duree = time.perf_counter() - debut
    print(f"  converti en {duree:.1f}s")

    # =========================================================================
    # 2. LE RESULTAT : STATUT, ERREURS, TEMPS PAR ETAGE
    # =========================================================================
    # `status` est une enumeration : SUCCESS, PARTIAL_SUCCESS, FAILURE, SKIPPED.
    # PARTIAL_SUCCESS est le cas vicieux : le document existe, il est
    # exploitable, mais une page a echoue. Sans ce test on indexerait un
    # document ampute sans jamais le savoir.
    print(f"\n  statut  : {resultat.status}")
    if resultat.errors:
        print(f"  erreurs : {len(resultat.errors)}")
        for err in resultat.errors[:3]:
            print(f"      {err}")

    # `timings` dit ou part le temps. C'est la seule facon honnete de decider
    # quoi optimiser : inutile de passer les tableaux en FAST si 90 % du temps
    # est dans l'OCR.
    if resultat.timings:
        print("\n  ou part le temps :")
        for nom, t in sorted(
            resultat.timings.items(), key=lambda kv: -sum(kv[1].times)
        )[:6]:
            total = sum(t.times)
            print(f"      {total:7.2f}s  {nom}  ({len(t.times)} appel(s))")

    doc = resultat.document

    # =========================================================================
    # 3. L'ARBRE : CE QUE DOCLING A COMPRIS
    # =========================================================================
    # Un DoclingDocument range ses elements dans des listes paralleles par
    # nature — `texts`, `tables`, `pictures` — et `body` tient l'ARBRE qui dit
    # dans quel ordre les lire et qui contient quoi.
    print("\n" + "=" * 74)
    print(f"  {len(doc.pages)} pages")
    print(f"  {len(doc.texts)} elements de texte")
    print(f"  {len(doc.tables)} tableaux")
    print(f"  {len(doc.pictures)} images")

    # `label` est LA donnee interessante : c'est le verdict du modele de layout
    # sur chaque region. section_header, text, list_item, caption, formula,
    # code, page_header, page_footer, footnote, title...
    etiquettes = Counter(item.label for item in doc.texts)
    print("\n  ce que le modele de layout a etiquete :")
    for etiquette, n in etiquettes.most_common():
        print(f"      {n:5d}  {etiquette}")

    # =========================================================================
    # 4. PARCOURIR L'ARBRE DANS L'ORDRE DE LECTURE
    # =========================================================================
    # iterate_items() rend des couples (element, profondeur). La profondeur est
    # la hierarchie reconstruite : c'est exactement l'information que ton
    # MarkdownHeaderTextSplitter va chercher dans les `#` d'un fichier .md.
    # `prov` est la provenance : numero de page et boite englobante. C'est ce
    # qui permet de citer "page 7" dans une reponse, ce que ton pipeline
    # Markdown ne peut pas faire aujourd'hui.
    print("\n  les 20 premiers elements dans l'ordre de lecture :")
    for i, (item, niveau) in enumerate(doc.iterate_items()):
        if i >= 20:
            break
        page = item.prov[0].page_no if getattr(item, "prov", None) else "?"
        texte = (getattr(item, "text", "") or "").replace("\n", " ")[:58]
        print(f"      p{page:<3} {'  ' * niveau}[{item.label}] {texte}")

    # =========================================================================
    # 5. L'EXPORT MARKDOWN
    # =========================================================================
    # export_to_markdown() APLATIT l'arbre. Les labels disparaissent, les
    # boites englobantes disparaissent, les numeros de page disparaissent. Il
    # ne reste que des `#` et du texte. C'est suffisant pour ton pipeline
    # actuel — qui lit du Markdown — mais c'est une perte seche, et c'est
    # precisement ce que le bloc 5 remettra en question.
    markdown = doc.export_to_markdown()
    sortie = chemin.with_suffix(".md")
    sortie.write_text(markdown, encoding="utf-8")
    print(f"\n  Markdown : {len(markdown)} caracteres -> {sortie.name}")
    print("\n  les 15 premieres lignes non vides :")
    lignes = [ligne for ligne in markdown.splitlines() if ligne.strip()][:15]
    for ligne in lignes:
        print(f"      {ligne[:70]}")


if __name__ == "__main__":
    main()
