"""Ingestion de fichiers deposes : depot sur disque, lecture, purge ciblee.

Module SANS Streamlit, volontairement. pages/2_Ingestion.py n'y ajoute que
l'affichage, ce qui rend ces fonctions testables hors interface — voir
eval/test_ingestion.py. Meme separation que rag_rerank et rag_generate.

POURQUOI NE PAS APPELER cmd_index()
--------------------------------------------------------------------------
La fonction existe et fait les memes quatre etapes, mais elle est ecrite pour
un terminal : elle `print()` sa progression, leve `SystemExit` sur erreur,
appelle `build_embedder()` au lieu d'un cache, et surtout termine par un
`client.close()` qui detruirait la connexion mise en cache par rag_ui. On
recompose donc les memes fonctions publiques.

POURQUOI LES FICHIERS PASSENT PAR LE DISQUE
--------------------------------------------------------------------------
Streamlit fournit les televersements en memoire, et il serait tentant de les
chunker directement. Deux raisons de ne pas le faire :

1. `source` est la moitie de l'identite d'un chunk — l'UUID vient de
   (source, chunk_index). Il doit etre stable d'une ingestion a l'autre, et un
   chemin relatif a un dossier de depot le garantit.
2. read_markdown() sait deja lire un fichier sans presumer de son encodage,
   retirer un BOM et normaliser les CRLF. Le refaire sur des octets en memoire
   dupliquerait du code deja teste.

Le dossier de depot devient donc la reference : ce qu'il contient est ce qui a
ete indexe, et un fichier renvoye ecrase sa version precedente.
"""

from __future__ import annotations

import re
from pathlib import Path

from langchain_core.documents import Document
from weaviate.classes.query import Filter

from md_metadata import read_markdown

EXTENSIONS = {".md", ".markdown"}

# Weaviate exige un nom de classe commencant par une lettre et compose de
# caracteres alphanumeriques. Un nom avec un tiret ou un espace echoue cote
# serveur avec un message peu parlant : autant le refuser en amont.
NOM_COLLECTION_VALIDE = re.compile(r"[A-Za-z][A-Za-z0-9_]*")


def nom_sur(nom_brut: str) -> str | None:
    """Nom de fichier assaini, ou None si le fichier doit etre refuse.

    Le nom vient du NAVIGATEUR, donc d'une source qu'on ne controle pas. Sans
    ce filtre, un nom comme `..\\..\\autre.md` ecrirait hors du dossier de
    depot. Path(...).name ne garde que le dernier composant, ce qui neutralise
    la traversee ; remplacer d'abord les antislashs par des slashs rend le
    comportement identique partout, et pas seulement sous Windows ou le
    separateur est reconnu nativement.
    """
    nom = Path(nom_brut.replace("\\", "/")).name
    # Tout ce qui n'est ni alphanumerique, ni point, tiret, espace ou
    # parenthese devient un souligne : on ecarte les caracteres interdits par
    # le systeme de fichiers sans rendre le nom meconnaissable.
    nom = re.sub(r"[^A-Za-z0-9._ \-()]", "_", nom).strip()

    if not nom or nom.startswith("."):
        return None
    if Path(nom).suffix.lower() not in EXTENSIONS:
        return None
    return nom


def deposer(fichiers, dossier: Path) -> tuple[list[Path], list[str]]:
    """Ecrit les televersements sur disque. Retourne (chemins ecrits, refuses).

    `fichiers` est une liste d'objets exposant `.name` et `.getvalue()` — ce que
    fournit st.file_uploader, et ce qu'un test peut imiter en trois lignes.

    Les octets sont ecrits TELS QUELS, sans tentative de decodage : c'est
    read_markdown() qui essaiera les encodages a la lecture, et lui sait deja le
    faire. Decoder ici puis reencoder ajouterait une conversion, donc une
    occasion de plus de fabriquer du mojibake.
    """
    dossier.mkdir(parents=True, exist_ok=True)
    ecrits: list[Path] = []
    refuses: list[str] = []

    for fichier in fichiers:
        nom = nom_sur(fichier.name)
        if nom is None:
            refuses.append(fichier.name)
            continue
        chemin = dossier / nom
        chemin.write_bytes(fichier.getvalue())
        ecrits.append(chemin)

    return ecrits, refuses


def charger(chemins: list[Path], racine: Path) -> tuple[list[Document], list[str], dict]:
    """Etage 1, restreint a une liste de fichiers.

    rag_pipeline.load_markdown() lit un DOSSIER entier. Ici on ne veut ingerer
    que les fichiers qui viennent d'etre deposes : reindexer tout le dossier a
    chaque ajout couterait des minutes d'embedding pour rien.

    Retourne aussi les encodages detectes, parce que c'est une information que
    l'utilisateur a interet a voir : un fichier lu en cp1252 alors qu'on le
    croyait en UTF-8 est la source de mojibake la plus courante.
    """
    docs: list[Document] = []
    vides: list[str] = []
    encodages: dict[str, str] = {}

    for chemin in chemins:
        md = read_markdown(chemin, corpus_root=racine)
        encodages[md.doc_meta["source"]] = md.encoding
        if not md.body.strip():
            vides.append(md.doc_meta["source"])
            continue
        docs.append(Document(page_content=md.body, metadata=dict(md.doc_meta)))

    return docs, vides, encodages


def purger(collection, sources: list[str]) -> int:
    """Supprime les chunks des sources listees. Retourne le nombre supprime.

    RESOUT UN BUG DOCUMENTE DANS index_chunks() : l'UUID etant derive de
    (source, chunk_index), reindexer un fichier ECRASE ses chunks un a un. Mais
    si le fichier corrige produit 8 chunks la ou il en produisait 12, les
    chunks 8 a 11 de l'ancienne version SURVIVENT — orphelins, jamais ecrases,
    et toujours renvoyes par les recherches. En CLI la parade est --recreate,
    qui reconstruit toute la collection.

    Ici on fait plus fin : on supprime les chunks des seules sources renvoyees,
    puis on reindexe. Le reste de la collection n'est pas touche.

    Contrepartie assumee : entre la suppression et la reindexation, ces
    documents sont absents de l'index. Si l'embedding echoue au milieu, il faut
    relancer — les fichiers etant sur disque, rien n'est perdu.
    """
    total = 0
    for source in sources:
        resultat = collection.data.delete_many(
            where=Filter.by_property("source").equal(source)
        )
        total += resultat.successful
    return total
