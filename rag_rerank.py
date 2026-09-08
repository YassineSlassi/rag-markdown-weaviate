"""ETAGE 6bis — reordonnancement des candidats par cross-encodeur.

    from rag_rerank import build_reranker, rerank
    reranker = build_reranker()
    resultats = rerank(reranker, question, search(collection, embedder, q, k=20))

BI-ENCODEUR CONTRE CROSS-ENCODEUR
--------------------------------------------------------------------------
BGE-M3 est un BI-encodeur : il encode la question d'un cote, chaque chunk de
l'autre, separement. Le chunk ne voit jamais la question. C'est ce qui permet
de pre-calculer les vecteurs une fois pour toutes a l'indexation, et c'est
pourquoi une recherche coute 200 ms sur 2244 chunks.

Un reranker est un CROSS-encodeur : il recoit la PAIRE (question, chunk) comme
une seule entree et les fait passer ensemble dans le transformeur. Chaque mot
de la question peut donc porter attention a chaque mot du chunk. La sortie
n'est pas un vecteur mais un score de pertinence unique.

Consequence : rien n'est pre-calculable. Un passage avant par candidat, au
moment de la requete. Sur 2244 chunks c'est hors de question ; sur les 20 que
le retriever a deja selectionnes, c'est l'affaire de quelques secondes.

CE QUE CET ETAGE PEUT ET NE PEUT PAS AMELIORER
--------------------------------------------------------------------------
Le reranker ne cherche RIEN de nouveau : il recoit les candidats du retriever
et se contente de les reordonner. Il ne peut donc pas ameliorer le recall a la
profondeur du vivier — recall@20 sur un vivier de 20 est mathematiquement
invariant. Il ne peut bouger que le rang 1, le MRR et le nDCG.

C'est une prediction falsifiable, et elle sert de temoin de controle :
si `recall@20` change entre un run avec et un run sans --rerank, c'est un bug,
pas un gain.
"""

from __future__ import annotations

import time

# Constante partagee avec rag_pipeline : nombre de candidats a demander au
# retriever AVANT reranking. Plus large que le TOP_K final, sinon le reranker
# n'a rien a reordonner ; trop large et on paie un passage avant pour rien.
RERANK_POOL = 20

# Defaut sur v2-m3 : il DOMINE base sur la mesure, sans contrepartie de
# qualite. Sur les 96 questions HTTP, @1 0,79 contre 0,73, MRR 0,868 contre
# 0,816, et surtout aucune des dix familles de questions degradee la ou base en
# regressait trois. Sa superiorite vient de son entrainement multilingue, pas de
# sa taille : sur une question francaise dont le vocabulaire s'ecarte du corpus
# ("duree de conservation d'une verification prealable" pour
# Access-Control-Max-Age), base renvoie le bon fichier au rang 14, v2-m3 au
# rang 1.
#
# Fait notable, les DEUX modeles y ont une confiance basse — 0,003 pour base,
# 0,031 pour v2-m3. Ce n'est donc pas le score absolu qui les separe, mais la
# qualite du classement a confiance egale : quand base ne comprend pas, son
# ordre devient du bruit, alors que v2-m3 ordonne encore correctement. Raison
# de plus de ne jamais seuiller sur ce score (cf. plus bas).
#
#   BAAI/bge-reranker-base    278 M parametres, ~1,1 Go,  501 ms / candidat
#   BAAI/bge-reranker-v2-m3   568 M parametres, ~2,2 Go, 1702 ms / candidat
#
# base reste utile quand la latence compte : 10 s par question contre 34 s, et
# il apporte deja +12,5 points au rang 1. Le passer en --rerank-modele.
RERANK_MODEL = "BAAI/bge-reranker-v2-m3"

# 512 tokens, soit la longueur de contexte de XLM-RoBERTa, dont bge-reranker
# derive. v2-m3 accepterait bien plus (il partage l'architecture de BGE-M3 et
# ses 8192 tokens), mais un chunk de 1000 caracteres fait ~300 tokens fil
# d'Ariane compris : rien n'est tronque, et un plafond plus haut ne couterait
# que du temps de calcul. La valeur est laissee identique pour les deux modeles,
# pour qu'une comparaison ne fasse varier que le modele.
#
# Si CHUNK_SIZE augmente un jour, c'est cette constante qu'il faut revoir — et
# c'est aussi pourquoi pair_text() met le fil d'Ariane en TETE : ce qui deborde
# est coupe a la fin.
RERANK_MAX_LENGTH = 512

# Meme raisonnement que EMBED_BATCH_SIZE : 7,7 Go de RAM, pas de GPU.
RERANK_BATCH_SIZE = 8

# CE QUE VAUT UN SCORE DE RERANKING
# ---------------------------------------------------------------------------
# predict() applique une sigmoide : les scores tombent dans [0, 1], et ils sont
# beaucoup plus CONTRASTES qu'un cosinus. Sur la question du proxy, les cinq
# premiers vont de 0,974 a 0,908 la ou les cosinus BGE-M3 se serrent entre
# 0,735 et 0,634 : c'est exactement cette dynamique retrouvee qui permet de
# discriminer des documents proches.
#
# Un vrai hors-sujet s'ecrase en revanche vers 0 (mesure : 3,7e-05 pour une
# phrase sur le fromage face a une question sur le code 407).
#
# Ce n'est pas pour autant une probabilite calibree : le seuil separant
# "pertinent" de "hors-sujet" depend du corpus. Ne pas s'en servir pour decider
# "aucun document ne repond" sans l'avoir mesure sur SON corpus.


def build_reranker(model_name: str = RERANK_MODEL):
    """Charge le cross-encodeur (~2,2 Go pour bge-reranker-v2-m3).

    Import local et non en tete de module : rag_pipeline importe rag_rerank
    seulement quand --rerank est demande, et `index` ne doit pas payer le
    chargement de sentence_transformers.CrossEncoder pour rien.
    """
    from sentence_transformers import CrossEncoder

    print(f"[6bis] chargement du reranker {model_name} sur CPU...")
    started = time.perf_counter()
    reranker = CrossEncoder(model_name, device="cpu", max_length=RERANK_MAX_LENGTH)
    print(f"       reranker prêt en {time.perf_counter() - started:.1f}s")
    return reranker


def pair_text(result: dict, avec_fil: bool = True) -> str:
    """Texte du chunk tel qu'il est soumis au cross-encodeur.

    Reproduit volontairement contextualize() : le fil d'Ariane est souvent LA
    donnee qui tranche. Sur le carre de l'authentification, les corps de
    `www-authenticate` et `proxy-authenticate` se ressemblent enormement, mais
    leurs titres, eux, sont sans ambiguite.

    Le fil est reconstruit depuis `headers` (h1 > h2 > ...) et `title`, que
    search() renvoie separement. dict.fromkeys() deduplique en gardant l'ordre :
    title et h1 sont souvent identiques.
    """
    if not avec_fil:
        return result["text"]

    trail = [result.get("title", "")]
    trail += str(result.get("headers", "")).split(" > ")
    parts = dict.fromkeys(str(t).strip() for t in trail if t and str(t).strip())
    breadcrumb = " > ".join(parts)
    return f"{breadcrumb}\n\n{result['text']}" if breadcrumb else result["text"]


def rerank(
    reranker,
    question: str,
    results: list[dict],
    top_n: int | None = None,
    avec_fil: bool = True,
) -> list[dict]:
    """Reordonne `results` par score du cross-encodeur, du meilleur au pire.

    Les dictionnaires sont copies, jamais modifies en place : l'appelant garde
    le classement du retriever intact et peut comparer les deux.

    Trois cles sont posees ou reecrites :
      score_rerank   score du cross-encodeur (nouveau)
      rank_retriever rang d'origine, pour mesurer le deplacement (nouveau)
      rank           renumerote 1..n dans le NOUVEL ordre (reecrit)

    `score` est laisse tel quel : c'est la similarite cosinus de BGE-M3, et la
    renommer en score de reranking ferait mentir tout ce qui l'affiche.

    top_n=None retourne TOUS les candidats reordonnes. C'est le mode a utiliser
    en evaluation : l'ensemble est inchange, seul l'ordre bouge, donc le recall
    a la profondeur du vivier reste un temoin de controle. top_n=5 est le mode
    production : on ne garde que ce qu'on envoie au modele de generation.
    """
    if not results:
        return []

    paires = [(question, pair_text(r, avec_fil=avec_fil)) for r in results]
    scores = reranker.predict(paires, batch_size=RERANK_BATCH_SIZE)

    enrichis = []
    for result, score in zip(results, scores):
        copie = dict(result)
        copie["score_rerank"] = float(score)
        copie["rank_retriever"] = result["rank"]
        enrichis.append(copie)

    # sorted() est stable : a scores egaux, l'ordre du retriever est conserve.
    # Une egalite parfaite est improbable sur des flottants, mais la garantie
    # rend le classement reproductible plutot que dependant de l'implementation.
    enrichis.sort(key=lambda r: r["score_rerank"], reverse=True)

    if top_n is not None:
        enrichis = enrichis[:top_n]

    for rank, result in enumerate(enrichis, start=1):
        result["rank"] = rank

    return enrichis


def print_mouvement(results: list[dict], limite: int = 10) -> None:
    """Affiche le deplacement de chaque candidat, pour voir le reranker agir.

    Un chiffre global dit qu'il y a un gain, jamais lequel. Cette vue montre
    QUEL document est remonte et de combien de places.
    """
    print(f"\n{'rang':>5}  {'etait':>6}  {'delta':>6}  {'rerank':>8}  {'cosinus':>8}  source")
    print("-" * 78)
    for item in results[:limite]:
        avant = item.get("rank_retriever", item["rank"])
        delta = avant - item["rank"]
        fleche = f"+{delta}" if delta > 0 else (str(delta) if delta < 0 else "=")
        print(
            f"{item['rank']:>5}  {avant:>6}  {fleche:>6}  "
            f"{item.get('score_rerank', float('nan')):>8.4f}  {item['score']:>8.4f}  "
            f"{item['source']}"
        )
