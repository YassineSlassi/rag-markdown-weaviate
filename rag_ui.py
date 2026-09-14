"""Ressources partagees par les pages Streamlit.

Ce module n'affiche rien. Il ne contient que les objets couteux — connexion
Weaviate, modeles — et les caches qui evitent de les reconstruire.

POURQUOI UN MODULE SEPARE
--------------------------------------------------------------------------
Streamlit derive la cle d'un @st.cache_resource de l'IDENTITE de la fonction
decoree. Deux pages qui definiraient chacune leur `get_embedder()` auraient
donc deux caches distincts, et BGE-M3 serait charge deux fois : 4,4 Go pour le
meme modele. Les pages doivent appeler la MEME fonction, d'ou ce module.

CE QU'IL FAUT COMPRENDRE DE STREAMLIT AVANT DE LIRE LA SUITE
--------------------------------------------------------------------------
Streamlit REEXECUTE le script de la page de haut en bas a chaque interaction.
Bouger un curseur, cocher une case, taper une lettre : le script repart de la
ligne 1.

C'est confortable pour ecrire l'affichage, et c'est un piege mortel ici. Ecrit
naivement, chaque clic rechargerait BGE-M3 (2,2 Go) et le reranker (2,2 Go),
soit une quinzaine de secondes d'attente pour avoir deplace un curseur d'un
cran.

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

from pathlib import Path

import streamlit as st
import weaviate

import rag_pipeline
import rag_rerank

RACINE = Path(__file__).resolve().parent

# Dossier ou sont deposes les fichiers televerses, un sous-dossier par
# collection. Exclu du depot par .gitignore : ce sont les donnees de
# l'utilisateur, pas du code.
DOSSIER_UPLOADS = RACINE / "uploads"

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
        # Ici le close() est CORRECT, et c'est la seule exception a la regle :
        # on leve juste apres, donc cet objet ne sera jamais mis en cache
        # (st.cache_resource ne memorise pas les echecs). Sans lui, la connexion
        # gRPC resterait ouverte sans que personne puisse plus la fermer.
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
# COMMUN AUX PAGES
# =============================================================================
def connecter_ou_stopper():
    """Retourne le client, ou affiche l'erreur et interrompt la page.

    Factorise ici parce que les deux pages en ont besoin a l'identique, et que
    le message doit rester le meme : c'est la premiere chose que voit quelqu'un
    dont le conteneur n'est pas demarre.
    """
    try:
        return get_client()
    except Exception as exc:
        st.error(
            f"**Connexion à Weaviate impossible.**\n\n`{exc}`\n\n"
            "Le conteneur tourne-t-il ?  →  `docker compose up -d`"
        )
        st.stop()


def bouton_reconnexion() -> None:
    """Bouton de purge des caches, identique sur toutes les pages."""
    if st.sidebar.button("Reconnecter / vider le cache", use_container_width=True):
        # La seule facon propre de repartir de zero : le client Weaviate etant
        # en cache, un redemarrage du conteneur laisse une connexion morte
        # derriere lui. Vide aussi les modeles, donc libere leurs ~4,4 Go.
        st.cache_resource.clear()
        st.cache_data.clear()
        st.rerun()
