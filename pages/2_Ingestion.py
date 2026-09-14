"""Televersement de fichiers Markdown et ingestion dans une collection.

Pilote les etages 1 a 4 de rag_pipeline (lecture, chunking, embedding,
indexation) depuis l'interface au lieu de la CLI.

Cette page ne contient que de l'AFFICHAGE. La logique — assainissement des noms
de fichiers, depot sur disque, lecture, purge ciblee — est dans rag_ingest, qui
n'importe pas Streamlit et se teste donc hors interface. L'en-tete de
rag_ingest.py explique pourquoi les fichiers passent par le disque et pourquoi
cmd_index() n'est pas appele directement.
"""

from __future__ import annotations

import statistics
import time

import streamlit as st

import rag_ingest
import rag_pipeline
import rag_ui

st.set_page_config(page_title="Ingestion", page_icon="📥", layout="wide")

NOUVELLE = "➕ Nouvelle collection…"


# =============================================================================
# BARRE LATERALE
# =============================================================================
st.sidebar.title("📥 Ingestion")
st.sidebar.caption("Markdown → chunks → BGE-M3 → Weaviate")

client = rag_ui.connecter_ou_stopper()
collections = rag_ui.lister_collections(client)

etiquettes = {
    f"{nom}  ({n} chunks)" if n >= 0 else f"{nom}  (illisible)": nom
    for nom, n in collections.items()
}
choix = st.sidebar.selectbox("Collection cible", [NOUVELLE] + list(etiquettes))

if choix == NOUVELLE:
    saisie = st.sidebar.text_input("Nom de la nouvelle collection", value="MonCorpus")
    collection_name = rag_pipeline.normalize_collection_name(saisie)
    if collection_name and not rag_ingest.NOM_COLLECTION_VALIDE.fullmatch(collection_name):
        st.sidebar.error(
            "Lettres, chiffres et souligné uniquement, en commençant par une "
            "lettre. Ni espace, ni tiret, ni accent."
        )
        collection_name = ""
    elif collection_name:
        st.sidebar.caption(f"Sera créée sous le nom `{collection_name}`.")
else:
    collection_name = etiquettes[choix]

st.sidebar.divider()
st.sidebar.caption(
    f"chunk_size {rag_pipeline.CHUNK_SIZE} · overlap {rag_pipeline.CHUNK_OVERLAP} — "
    "valeurs de rag_pipeline, partagées avec la CLI."
)
st.sidebar.divider()
rag_ui.bouton_reconnexion()


# =============================================================================
# CORPS DE LA PAGE
# =============================================================================
st.title("Ingérer des fichiers Markdown")

fichiers = st.file_uploader(
    "Fichiers `.md` ou `.markdown`",
    type=["md", "markdown"],
    accept_multiple_files=True,
    help="Un fichier portant un nom déjà présent écrase sa version précédente, "
         "dans le dossier de dépôt comme dans la collection.",
)

if not fichiers:
    st.info(
        "Dépose un ou plusieurs fichiers Markdown. Ils seront écrits dans "
        "`uploads/<collection>/`, puis lus, découpés, vectorisés et indexés.\n\n"
        "Commence par **Analyser** : le chunking est instantané, l'embedding non."
    )
    st.stop()

if not collection_name:
    st.warning("Choisis une collection cible valide dans la barre latérale.")
    st.stop()

dossier = rag_ui.DOSSIER_UPLOADS / collection_name
taille_totale = sum(len(f.getvalue()) for f in fichiers)
# Sous 1 Ko, un arrondi en kilo-octets afficherait "0 Ko" pour un fichier qui
# existe bel et bien. On change d'unite plutot que d'ajouter des decimales.
taille = (
    f"{taille_totale} o" if taille_totale < 1024
    else f"{taille_totale / 1024:.0f} Ko"
)
st.caption(
    f"{len(fichiers)} fichier(s), {taille}  →  "
    f"`{dossier.relative_to(rag_ui.RACINE).as_posix()}`  →  collection "
    f"`{collection_name}`"
)

colonnes = st.columns(2)
analyser = colonnes[0].button("Analyser (sans vectoriser)", use_container_width=True)
ingerer = colonnes[1].button("Ingérer", type="primary", use_container_width=True)


# --- etapes 1 et 2, communes aux deux boutons --------------------------------
if analyser or ingerer:
    chemins, refuses = rag_ingest.deposer(fichiers, dossier)
    if refuses:
        st.error(
            "**Fichier(s) refusé(s)** — nom inutilisable ou extension non "
            "Markdown : " + ", ".join(f"`{n}`" for n in refuses)
        )
    if not chemins:
        st.stop()

    docs, vides, encodages = rag_ingest.charger(chemins, dossier)
    if vides:
        st.warning(
            "Ignoré(s), corps vide une fois le frontmatter retiré : "
            + ", ".join(f"`{s}`" for s in vides)
        )

    # L'encodage retenu n'est signale que s'il n'est PAS de l'UTF-8 : c'est
    # exactement le cas ou l'utilisateur doit verifier que ses accents ont
    # survecu, et le taire serait laisser passer du mojibake silencieux.
    exotiques = {s: e for s, e in encodages.items() if not e.startswith("utf-8")}
    if exotiques:
        st.warning(
            "**Encodage non UTF-8 détecté**, lu malgré tout — vérifie les "
            "accents dans l'aperçu : "
            + ", ".join(f"`{s}` ({e})" for s, e in exotiques.items())
        )

    if not docs:
        st.error("Aucun document exploitable.")
        st.stop()

    chunks = rag_pipeline.chunk_documents(docs)
    if not chunks:
        st.error("Le chunking n'a produit aucun chunk.")
        st.stop()

    longueurs = [len(c.page_content) for c in chunks]
    mediane = int(statistics.median(longueurs))

    mesures = st.columns(4)
    mesures[0].metric("documents", len(docs))
    mesures[1].metric("chunks", len(chunks))
    mesures[2].metric("médiane", f"{mediane} car.")
    mesures[3].metric(
        "embedding estimé",
        f"{len(chunks) / rag_pipeline.CHUNKS_PER_SECOND / 60:.1f} min",
    )

    # Meme lecture que le --dry-run de la CLI : la mediane dit si le decoupage a
    # mordu. Trop petite, le document est hache ; proche de CHUNK_SIZE, la passe
    # structurelle n'a rien trouve — document sans titres Markdown.
    if mediane < 150:
        st.warning(
            f"Médiane de {mediane} caractères : découpage très fin. Des titres "
            "trop rapprochés produisent des chunks sans contenu utile."
        )
    elif mediane > rag_pipeline.CHUNK_SIZE * 0.9:
        st.warning(
            f"Médiane de {mediane} caractères, proche de CHUNK_SIZE "
            f"({rag_pipeline.CHUNK_SIZE}) : la passe structurelle n'a pas mordu. "
            "Ces fichiers ont-ils des titres Markdown ?"
        )

    with st.expander("Aperçu — 3 chunks tels qu'ils seront vectorisés"):
        pas = max(1, len(chunks) // 3)
        for chunk in chunks[::pas][:3]:
            st.caption(f"`{chunk.metadata['source']}`")
            st.code(rag_pipeline.contextualize(chunk)[:600], language="markdown")

    st.session_state.ingestion_chunks = chunks


# --- etapes 3 et 4, seulement sur "Ingerer" ----------------------------------
if ingerer:
    chunks = st.session_state.ingestion_chunks
    embedder = rag_ui.get_embedder()

    barre = st.progress(0.0, text="Vectorisation...")

    def avancement(faits: int, total: int) -> None:
        """Appele par embed_texts apres chaque lot."""
        barre.progress(faits / total, text=f"Vectorisation — {faits}/{total} chunks")

    debut = time.perf_counter()
    textes = [rag_pipeline.contextualize(chunk) for chunk in chunks]
    vecteurs = rag_pipeline.embed_texts(embedder, textes, on_batch=avancement)
    barre.progress(1.0, text=f"{len(vecteurs)} vecteurs")

    with st.spinner("Indexation dans Weaviate..."):
        collection = rag_pipeline.ensure_collection(client, collection_name)

        # Purge AVANT indexation, sur les seules sources renvoyees.
        sources = sorted({chunk.metadata["source"] for chunk in chunks})
        supprimes = rag_ingest.purger(collection, sources)

        rag_pipeline.index_chunks(collection, chunks, vecteurs)
        total = collection.aggregate.over_all(total_count=True).total_count

    duree = time.perf_counter() - debut

    # Le compteur de collections est en cache 30 s : sans cette purge, la barre
    # laterale afficherait l'ancien total pendant une demi-minute.
    rag_ui.lister_collections.clear()

    st.success(
        f"**{len(chunks)} chunks indexés dans `{collection_name}`** en "
        f"{duree:.0f} s.  La collection contient maintenant {total} objets."
    )
    if supprimes:
        st.caption(
            f"{supprimes} chunk(s) d'une version précédente supprimés avant "
            "réindexation, pour ne pas laisser d'orphelins."
        )
    st.page_link("app.py", label="Interroger cette collection", icon="🔎")
