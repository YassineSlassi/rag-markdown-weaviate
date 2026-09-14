"""Verifie l'ingestion de bout en bout, sans Streamlit et sans Weaviate.

    python eval/test_ingestion.py

L'embedding et l'indexation sont volontairement HORS de ce test : ce sont les
etages deja couverts par la CLI, ils coutent des minutes, et ce n'est pas ce
que la page d'ingestion ajoute. Ce qu'elle ajoute, et ce qu'on teste ici, c'est
la chaine depot -> lecture : assainissement d'un nom venu du navigateur,
ecriture sur disque, detection d'encodage, stabilite de `source`.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

import rag_ingest  # noqa: E402
import rag_pipeline  # noqa: E402


class FauxUpload:
    """Imite st.file_uploader : un nom et des octets, rien de plus."""

    def __init__(self, name: str, data: bytes):
        self.name = name
        self._data = data

    def getvalue(self) -> bytes:
        return self._data


MARKDOWN = """\
---
title: Fiche de test
tags: [essai]
---

# Fiche de test

Un paragraphe d'introduction avec des accents : éàçùô.

## Section deux

Le contenu de la deuxième section, assez long pour exister.
"""


def main() -> None:
    verdicts: list[bool] = []

    def verifier(ok: bool, libelle: str) -> None:
        verdicts.append(ok)
        print(f"  [{'OK   ' if ok else 'ECHEC'}] {libelle}")

    # 1. Assainissement des noms. Le nom vient du navigateur : il faut qu'une
    #    traversee de repertoire soit neutralisee, pas seulement signalee.
    print("\nAssainissement des noms de fichiers :")
    cas = [
        ("note.md", "note.md"),
        ("..\\..\\evil.md", "evil.md"),
        ("../../evil.md", "evil.md"),
        ("mon fichier (1).md", "mon fichier (1).md"),
        ("étrange#nom!.md", "_trange_nom_.md"),
        ("script.py", None),
        ("..", None),
        (".cache.md", None),
    ]
    for brut, attendu in cas:
        obtenu = rag_ingest.nom_sur(brut)
        verifier(obtenu == attendu, f"{brut!r:>22} -> {obtenu!r}")

    with tempfile.TemporaryDirectory() as tmp:
        dossier = Path(tmp) / "MonCorpus"

        # 2. Depot : les fichiers valides sont ecrits, les autres refuses.
        print("\nDépôt sur disque :")
        uploads = [
            FauxUpload("fiche.md", MARKDOWN.encode("utf-8")),
            FauxUpload("latin.md", MARKDOWN.encode("cp1252")),
            FauxUpload("..\\..\\echappe.md", MARKDOWN.encode("utf-8")),
            FauxUpload("image.png", b"\x89PNG"),
        ]
        chemins, refuses = rag_ingest.deposer(uploads, dossier)
        verifier(len(chemins) == 3, f"3 fichiers écrits, obtenu {len(chemins)}")
        verifier(refuses == ["image.png"], f"1 refusé : {refuses}")

        # Le point qui compte : le fichier au nom piege est DANS le dossier.
        echappe = dossier / "echappe.md"
        verifier(echappe.is_file(), "le nom avec ..\\.. reste dans le dossier de dépôt")
        verifier(
            all(dossier in c.parents for c in chemins),
            "aucun chemin écrit hors du dossier de dépôt",
        )

        # 3. Lecture : encodages detectes, corps non vide, `source` relatif.
        print("\nLecture :")
        docs, vides, encodages = rag_ingest.charger(chemins, dossier)
        verifier(len(docs) == 3 and not vides, f"{len(docs)} documents, {len(vides)} vides")
        verifier(
            encodages.get("fiche.md", "").startswith("utf-8"),
            f"fiche.md lu en {encodages.get('fiche.md')}",
        )
        verifier(
            not encodages.get("latin.md", "").startswith("utf-8"),
            f"latin.md lu en {encodages.get('latin.md')} (non UTF-8, donc signalé)",
        )

        # `source` relatif au dossier de depot : c'est la moitie de l'identite
        # du chunk. Un chemin absolu rendrait l'index non reproductible.
        sources = sorted(d.metadata["source"] for d in docs)
        verifier(
            sources == ["echappe.md", "fiche.md", "latin.md"],
            f"sources relatives : {sources}",
        )

        # Le frontmatter est bien retire du corps et promu en metadata.
        fiche = next(d for d in docs if d.metadata["source"] == "fiche.md")
        verifier(fiche.metadata["title"] == "Fiche de test", "title lu du frontmatter")
        verifier(not fiche.page_content.startswith("---"), "frontmatter retiré du corps")
        verifier("éàçùô" in fiche.page_content, "accents intacts en UTF-8")

        # 4. Chunking : les chunks portent bien la source, et les index sont
        #    contigus a partir de 0 — c'est ce qui rend l'UUID reproductible.
        print("\nChunking :")
        chunks = rag_pipeline.chunk_documents(docs)
        verifier(len(chunks) >= 3, f"{len(chunks)} chunks produits")
        par_source: dict[str, list[int]] = {}
        for chunk in chunks:
            par_source.setdefault(chunk.metadata["source"], []).append(
                chunk.metadata["chunk_index"]
            )
        verifier(
            all(v == list(range(len(v))) for v in par_source.values()),
            f"chunk_index contigus depuis 0 : "
            f"{ {s: len(v) for s, v in par_source.items()} }",
        )

        # 5. Idempotence du depot : redeposer le meme nom ecrase, sans creer de
        #    doublon. C'est ce qui garantit qu'un fichier corrige remplace
        #    l'ancien au lieu de coexister avec lui.
        print("\nIdempotence :")
        rag_ingest.deposer([FauxUpload("fiche.md", b"# Autre contenu\n")], dossier)
        restants = sorted(p.name for p in dossier.glob("*.md"))
        verifier(
            restants == ["echappe.md", "fiche.md", "latin.md"],
            f"toujours 3 fichiers après redépôt : {restants}",
        )
        verifier(
            (dossier / "fiche.md").read_text(encoding="utf-8").startswith("# Autre"),
            "le contenu a bien été remplacé",
        )

    print()
    if all(verdicts):
        print(f"{len(verdicts)}/{len(verdicts)} — toutes les propriétés tiennent.")
    else:
        raise SystemExit(f"{verdicts.count(False)}/{len(verdicts)} propriété(s) fausse(s).")


if __name__ == "__main__":
    main()
