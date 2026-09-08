"""Interface graphique du pipeline RAG.

    streamlit run app.py

CE QU'IL FAUT COMPRENDRE DE STREAMLIT AVANT DE LIRE LA SUITE
--------------------------------------------------------------------------
Streamlit REEXECUTE ce fichier de haut en bas a chaque interaction. Bouger un
curseur, cocher une case, taper une lettre : le script repart de la ligne 1.

C'est confortable pour ecrire l'affichage, et c'est un piege mortel ici. Ecrit
naivement, ce fichier rechargerait BGE-M3 (2,2 Go) et le reranker (2,2 Go) a
CHAQUE clic, soit une quinzaine de secondes d'attente pour avoir deplace un
curseur d'un cran.

D'ou les trois @st.cache_resource ci-dessous. Ils sont la seule raison pour
laquelle cette interface est utilisable, pas une optimisation cosmetique.

@st.cache_resource garde l'objet VIVANT entre les reexecutions, contrairement a
@st.cache_data qui serialise une copie. C'est ce qu'il faut pour un modele ou
une connexion reseau : on veut le meme objet en memoire, pas un clone.

COROLLAIRE, ET C'EST LE BUG QU'ON NE VOIT PAS VENIR
--------------------------------------------------------------------------
Le client Weaviate est mis en cache, donc il ne faut JAMAIS l'appeler avec
close(). Partout ailleurs dans ce projet, connect_weaviate() est suivi d'un
try/finally qui ferme la connexion — c'est correct pour un script qui se
termine. Ici, fermer le client detruirait l'objet que le cache continue a
servir : la premiere requete marcherait, toutes les suivantes echoueraient sur
une connexion morte. Le bouton "reconnecter" de la barre laterale est la
maniere propre de repartir de zero.
"""

from __future__ import annotations

import os
import time

import streamlit as st
import weaviate

import rag_pipeline
import rag_rerank

# set_page_config doit etre le PREMIER appel Streamlit du script, sinon
# Streamlit leve une exception. Il n'est donc pas dans une fonction.
st.set_page_config(page_title="RAG Markdown", page_icon="🔎", layout="wide")

MODELES_RERANK = [
    "BAAI/bge-reranker-v2-m3",
    "BAAI/bge-reranker-base",
]


# =============================================================================
# RESSOURCES PARTAGEES — chargees une fois, reutilisees a chaque reexecution
# =============================================================================
@st.cache_resource(show_spinner="Connexion à Weaviate...")
def get_client() -> weaviate.WeaviateClient:
    """Connexion Weaviate persistante. Ne jamais fermer, cf. l'en-tete."""
    client = weaviate.connect_to_local()
    if not client.is_ready():
        client.close()
        raise RuntimeError("Weaviate répond mais n'est pas prêt.")
    return client


@st.cache_resource(show_spinner="Chargement de BGE-M3 (~2,2 Go)...")
def get_embedder():
    return rag_pipeline.build_embedder()


@st.cache_resource(show_spinner="Chargement du reranker...")
def get_reranker(model_name: str):
    """Un cache par nom de modele.

    Streamlit derive la cle du cache des ARGUMENTS : changer le modele dans la
    barre laterale charge le nouveau et garde l'ancien en memoire, donc revenir
    a l'autre est instantane. C'est aussi pourquoi le nom du modele est un
    parametre plutot qu'une lecture directe de rag_rerank.RERANK_MODEL.
    """
    return rag_rerank.build_reranker(model_name)


@st.cache_data(ttl=30, show_spinner=False)
def lister_collections(_client) -> dict[str, int]:
    """Nom -> nombre d'objets, pour chaque collection de l'instance.

    Le parametre s'appelle _client avec un underscore initial : c'est la
    convention Streamlit pour "n'essaie pas de hacher cet argument". Sans lui,
    @st.cache_data echouerait, le client Weaviate n'etant pas serialisable.

    ttl=30 parce qu'un `index` lance en parallele dans un terminal fait changer
    ces nombres, et qu'on veut les voir bouger sans redemarrer l'interface.
    """
    comptes = {}
    for nom in sorted(_client.collections.list_all().keys()):
        try:
            collection = _client.collections.get(nom)
            comptes[nom] = collection.aggregate.over_all(total_count=True).total_count
        except Exception:
            # Une collection illisible ne doit pas empecher d'afficher les autres.
            comptes[nom] = -1
    return comptes


# =============================================================================
# AFFICHAGE DES RESULTATS
# =============================================================================
def afficher_resultats(resultats: list[dict], rerank_actif: bool) -> None:
    """Un bloc depliable par chunk, avec ses scores et son deplacement."""
    for item in resultats:
        deplacement = ""
        if rerank_actif and "rank_retriever" in item:
            delta = item["rank_retriever"] - item["rank"]
            if delta > 0:
                deplacement = f" &nbsp; :green[▲ +{delta}]"
            elif delta < 0:
                deplacement = f" &nbsp; :red[▼ {delta}]"
            else:
                deplacement = " &nbsp; :gray[=]"

        titre = f"**#{item['rank']}** &nbsp; `{item['source']}`{deplacement}"
        # expanded sur le premier seulement : on veut voir la meilleure reponse
        # sans deplier, sans pour autant noyer la page.
        with st.expander(titre, expanded=item["rank"] == 1):
            colonnes = st.columns(3)
            colonnes[0].metric("cosinus BGE-M3", f"{item['score']:.4f}")
            if "score_rerank" in item:
                colonnes[1].metric("score reranker", f"{item['score_rerank']:.4f}")
            if "rank_retriever" in item:
                colonnes[2].metric(
                    "rang", item["rank"], delta=item["rank_retriever"] - item["rank"]
                )
            if item.get("headers"):
                st.caption(item["headers"])
            st.markdown(item["text"])


def afficher_citations(answer, resultats: list[dict]) -> None:
    """Les marqueurs [n] relus dans la reponse, et leur avertissement.

    parse_citations() produit une entree par couple (phrase, marqueur) : une
    source citee dans trois phrases revient trois fois. On deduplique donc par
    numero d'extrait, en gardant le compte, plutot que d'afficher trois lignes
    identiques.
    """
    if not answer.citations:
        st.info("Le modèle n'a écrit aucun marqueur `[n]` dans sa réponse.")
        return

    citees: dict[int, dict] = {}
    inventees: list[dict] = []
    for citation in answer.citations:
        index = citation["index"]
        # Un index hors bornes signifie que le modele a ecrit un numero qui ne
        # correspond a aucun extrait fourni. parse_citations le marque plutot
        # que de l'ignorer, et il faut que ca reste visible ici aussi.
        if not 0 <= index < len(resultats):
            inventees.append(citation)
            continue
        entree = citees.setdefault(
            index, {"source": citation["source"], "title": citation["title"], "n": 0}
        )
        entree["n"] += 1

    st.markdown("**Sources citées**")
    for index in sorted(citees):
        entree = citees[index]
        rappels = f" &nbsp;:gray[×{entree['n']}]" if entree["n"] > 1 else ""
        st.markdown(f"- `[{index + 1}]` &nbsp; `{entree['source']}`{rappels}")
        if entree["title"]:
            st.caption(f"&nbsp;&nbsp;&nbsp;&nbsp;{entree['title']}")

    if inventees:
        st.error(
            f"**{len(inventees)} marqueur(s) inventé(s).** Le modèle a cité un "
            "numéro qui ne correspond à aucun extrait fourni : "
            + ", ".join(f"`[{c['index'] + 1}]`" for c in inventees)
        )

    # Le meme avertissement que dans le README et l'en-tete de rag_generate :
    # il doit etre visible la ou les citations sont lues, pas seulement dans la
    # documentation que personne n'ouvre.
    st.caption(
        "⚠️ Les marqueurs sont écrits par le modèle. `parse_citations()` vérifie "
        "que le numéro existe, jamais qu'il est le bon."
    )


# =============================================================================
# BARRE LATERALE — tous les reglages du pipeline
# =============================================================================
st.sidebar.title("🔎 RAG Markdown")
st.sidebar.caption("BGE-M3 → Weaviate → Mistral")

try:
    client = get_client()
except Exception as exc:
    st.error(
        f"**Connexion à Weaviate impossible.**\n\n`{exc}`\n\n"
        "Le conteneur tourne-t-il ?  →  `docker compose up -d`"
    )
    st.stop()

collections = lister_collections(client)
if not collections:
    st.warning(
        "Aucune collection dans Weaviate. Indexe d'abord un corpus :\n\n"
        "`python rag_pipeline.py index --corpus DOSSIER --collection NOM`"
    )
    st.stop()

# Le nombre d'objets dans le libelle : ca evite d'interroger par erreur une
# collection vide et de conclure que le retrieval ne marche pas.
etiquettes = {
    f"{nom}  ({n} chunks)" if n >= 0 else f"{nom}  (illisible)": nom
    for nom, n in collections.items()
}
choix = st.sidebar.selectbox("Collection", list(etiquettes))
collection_name = etiquettes[choix]

top_k = st.sidebar.slider("Chunks retournés (k)", 1, 20, rag_pipeline.TOP_K)

st.sidebar.divider()
rerank_actif = st.sidebar.toggle(
    "Reranking (étage 6bis)",
    value=False,
    help="Élargit le vivier à 20 candidats puis les réordonne par cross-encodeur. "
         "+18,8 points au rang 1 sur le banc d'essai HTTP, mais ~34 s par question sur CPU.",
)
modele_rerank = st.sidebar.selectbox(
    "Modèle de reranking",
    MODELES_RERANK,
    disabled=not rerank_actif,
    help="v2-m3 est meilleur, base est 3,4× plus rapide.",
)

st.sidebar.divider()
cle_presente = bool(os.environ.get("MISTRAL_API_KEY"))
generer = st.sidebar.toggle(
    "Générer une réponse (étage 7)",
    value=cle_presente,
    disabled=not cle_presente,
    help="Envoie les chunks à Mistral. Sans clé, seul le retrieval est disponible.",
)
if not cle_presente:
    st.sidebar.warning(
        "`MISTRAL_API_KEY` absente de l'environnement — le retrieval reste "
        "utilisable. Pour l'ajouter :\n\n"
        "`setx MISTRAL_API_KEY \"...\"` puis relancer depuis un NOUVEAU terminal."
    )

st.sidebar.divider()
if st.sidebar.button("Reconnecter / vider le cache", use_container_width=True):
    # La seule facon propre de repartir de zero : le client Weaviate etant en
    # cache, un redemarrage du conteneur laisse une connexion morte derriere lui.
    st.cache_resource.clear()
    st.cache_data.clear()
    st.rerun()


# =============================================================================
# CORPS DE LA PAGE
# =============================================================================
st.title("Interroger le corpus")

with st.form("recherche"):
    question = st.text_area(
        "Question",
        placeholder="quel code indique qu'il manque des identifiants pour le proxy ?",
        height=80,
    )
    lancer = st.form_submit_button("Chercher", type="primary")

# st.form regroupe les saisies et ne declenche UNE reexecution qu'a la
# soumission. Sans lui, chaque lettre tapee relancerait le script.

if lancer and question.strip():
    embedder = get_embedder()
    collection = client.collections.get(collection_name)

    debut = time.perf_counter()
    if rerank_actif:
        reranker = get_reranker(modele_rerank)
        vivier = max(top_k, rag_rerank.RERANK_POOL)
        with st.spinner(f"Recherche puis reranking de {vivier} candidats..."):
            candidats = rag_pipeline.search(collection, embedder, question, k=vivier)
            # top_n=None garde le vivier entier reordonne : le haut alimente la
            # generation, le reste va dans le bloc "vivier complet" plus bas.
            classement = rag_rerank.rerank(reranker, question, candidats)
    else:
        with st.spinner("Recherche..."):
            classement = rag_pipeline.search(collection, embedder, question, k=top_k)
    duree = time.perf_counter() - debut

    resultats = classement[:top_k]

    # Tout passe par session_state : Streamlit reexecute le script a la moindre
    # interaction suivante, et des variables locales seraient perdues.
    st.session_state.update(
        question=question,
        resultats=resultats,
        classement=classement,
        rerank_actif=rerank_actif,
        duree=duree,
        collection_name=collection_name,
        reponse=None,
    )

    if generer:
        import rag_generate

        # Zone TEMPORAIRE, videe des que la generation aboutit. Elle n'existe
        # que pour l'affichage progressif pendant que Mistral repond ; le rendu
        # definitif est fait plus bas depuis session_state, seul capable de
        # survivre a la reexecution suivante.
        #
        # Le vidage n'est pas cosmetique : sans lui, les deux blocs s'executent
        # dans la MEME passe du script et le titre "Réponse" apparait deux fois,
        # suivi du meme texte. Un st.subheader ne pouvant pas etre retire une
        # fois ecrit, le titre est ici un simple markdown a l'interieur du
        # placeholder, ce qui le rend effacable avec le reste.
        flux = st.empty()
        morceaux: list[str] = []

        def afficher(fragment: str) -> None:
            """Appele par rag_generate a chaque morceau recu de Mistral."""
            morceaux.append(fragment)
            flux.markdown("### Réponse\n\n" + "".join(morceaux))

        try:
            with st.spinner(f"{rag_generate.MODEL}..."):
                st.session_state.reponse = rag_generate.generate(
                    question,
                    resultats,
                    # show_stream=False : sinon les fragments partent aussi dans
                    # le terminal qui a lance streamlit, ce qui n'aide personne.
                    show_stream=False,
                    on_fragment=afficher,
                )
            flux.empty()
        except Exception as exc:
            # On ne vide PAS la zone ici : session_state.reponse reste None,
            # donc le bloc de rendu n'affichera rien et le texte partiel deja
            # recu serait perdu. Le garder visible aide a diagnostiquer.
            st.error(f"**Échec de la génération.**\n\n`{type(exc).__name__}: {exc}`")

elif lancer:
    st.warning("Écris une question.")


# =============================================================================
# RENDU — depuis session_state, donc stable d'une reexecution a l'autre
# =============================================================================
if st.session_state.get("resultats"):
    resultats = st.session_state["resultats"]
    answer = st.session_state.get("reponse")

    if answer is not None:
        st.subheader("Réponse")
        st.markdown(answer.text)
        afficher_citations(answer, resultats)
        if answer.usage:
            # Les cles sont input/output/total : _usage() renomme deja les
            # champs Mistral (prompt_tokens, completion_tokens) au passage.
            st.caption(
                f"{answer.usage.get('input', '?')} tokens en entrée, "
                f"{answer.usage.get('output', '?')} en sortie, "
                f"{answer.usage.get('total', '?')} au total  ·  "
                f"arrêt : {answer.stop_reason or 'inconnu'}"
            )

    st.subheader(f"{len(resultats)} chunks retournés")
    st.caption(
        f"{st.session_state['collection_name']}  ·  "
        f"{st.session_state['duree']:.1f} s  ·  "
        + ("avec reranking" if st.session_state["rerank_actif"] else "dense seul")
    )
    afficher_resultats(resultats, st.session_state["rerank_actif"])

    # Le vivier complet n'a d'interet qu'avec le reranking : c'est la qu'on voit
    # ce que le cross-encodeur a ecarte, donc ce qu'on aurait eu sans lui.
    classement = st.session_state.get("classement", [])
    if st.session_state["rerank_actif"] and len(classement) > len(resultats):
        with st.expander(
            f"Vivier complet — les {len(classement)} candidats réordonnés"
        ):
            st.dataframe(
                [
                    {
                        "rang": item["rank"],
                        "était": item.get("rank_retriever", item["rank"]),
                        "delta": item.get("rank_retriever", item["rank"]) - item["rank"],
                        "reranker": round(item.get("score_rerank", float("nan")), 4),
                        "cosinus": round(item["score"], 4),
                        "source": item["source"],
                    }
                    for item in classement
                ],
                hide_index=True,
                use_container_width=True,
            )
else:
    st.info(
        "Pose une question pour interroger la collection. "
        "Le premier lancement charge BGE-M3, compter une dizaine de secondes."
    )
