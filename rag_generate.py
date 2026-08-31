"""
Etage de generation du RAG : Top-K chunks -> reponse citee par Mistral.

MIGRATION DEPUIS ANTHROPIC — CE QUI CHANGE POUR LES CITATIONS
--------------------------------------------------------------------------
La version Anthropic passait chaque chunk comme un bloc `search_result` et le
SERVEUR attachait lui-meme les citations a la reponse : `cited_text` contenait
le passage exact qui appuyait chaque affirmation. C'etait verifiable — le modele
n'ecrivait aucun marqueur, il ne pouvait donc pas se tromper d'attribution.

L'API Mistral n'a pas d'equivalent. Il faut donc revenir a la methode que la
version precedente interdisait explicitement : numeroter les extraits dans le
prompt et demander au modele d'ecrire "[1]", "[2]" lui-meme.

Consequence a assumer : une citation peut desormais etre MAL ATTRIBUEE sans que
rien ne le detecte. Le modele peut ecrire [2] en s'appuyant en realite sur
l'extrait 3. On ne verifie plus que le numero existe, pas qu'il est le bon.
`cited_text` ne contient plus le passage exact mais l'extrait entier.

Si la tracabilite exacte compte pour ton usage, c'est un argument reel pour
rester sur Anthropic — la fonctionnalite n'est pas remplacable cote client.

Auth : MISTRAL_API_KEY dans l'environnement, jamais en dur ici.
    cmd.exe :  setx MISTRAL_API_KEY "..."   puis NOUVEAU terminal
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any

from mistralai.client import Mistral

# =============================================================================
# CONFIGURATION
# =============================================================================
# En mistralai 2.x, la classe s'importe depuis `mistralai.client` et non plus
# depuis `mistralai` : le paquet racine est devenu un namespace sans __init__.
MODEL = "mistral-large-latest"

# Chez Mistral, max_tokens plafonne la SORTIE seule. C'est different d'Anthropic
# ou reflexion et texte partageaient ce budget. 16000 reste large ici.
MAX_TOKENS = 16000

# `reasoning_effort` n'existe que sur les modeles de raisonnement (Magistral).
# L'envoyer a mistral-large-latest serait au mieux ignore, au pire une erreur.
DEFAULT_EFFORT = "low"

SYSTEM_PROMPT = """\
Tu réponds à des questions en t'appuyant uniquement sur les extraits de \
documents fournis.

- Si les extraits ne permettent pas de répondre, dis-le franchement au lieu de \
compléter avec tes connaissances générales. C'est le comportement attendu, pas \
un échec : une réponse inventée coûte plus cher à l'utilisateur qu'un « ce \
corpus ne le dit pas ».
- Si deux extraits se contredisent, signale la contradiction plutôt que d'en \
choisir un silencieusement.
- Distingue ce que les extraits affirment de ce que tu en déduis.

Réponds directement, sans préambule. Quelques phrases suffisent pour une \
question simple ; développe seulement si la question le demande.

CITATIONS — obligatoire :
Chaque extrait porte un numéro entre crochets. Termine par ce numéro toute \
phrase qui s'appuie sur un extrait, par exemple : « BGE-M3 accepte 8192 \
tokens [3]. » N'invente jamais un numéro qui n'existe pas dans la liste, et \
n'en mets aucun sur une phrase qui ne s'appuie sur aucun extrait.
"""


@dataclass
class Answer:
    """Resultat de l'etage de generation."""

    text: str
    citations: list[dict[str, Any]] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)
    stop_reason: str = ""
    refusal: str | None = None


# =============================================================================
# CONSTRUCTION DE LA REQUETE
# =============================================================================
def build_extracts(results: list[dict]) -> str:
    """Formate les chunks en un bloc de texte numerote.

    L'API Mistral n'accepte que du texte : pas de blocs typés comme les
    `search_result` d'Anthropic. La numerotation visible dans le prompt est le
    SEUL lien entre la reponse du modele et les extraits — d'ou son importance.
    """
    morceaux = []
    for n, item in enumerate(results, start=1):
        source = item.get("source", "?")
        headers = item.get("headers") or source
        morceaux.append(
            f"[{n}] source : {source}\n"
            f"    section : {headers}\n"
            f"    {item.get('text', '')}"
        )
    return "\n\n".join(morceaux)


def build_messages(question: str, results: list[dict]) -> list[dict[str, Any]]:
    """Assemble les messages au format Mistral.

    Deux differences avec Anthropic :
      - le systeme prompt est un MESSAGE de role "system", pas un parametre ;
      - le contenu est une chaine, pas une liste de blocs typés.

    L'ordre extraits -> question est conserve : contenu de reference d'abord.
    """
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Extraits du corpus :\n\n{build_extracts(results)}\n\n"
                f"Question : {question}"
            ),
        },
    ]


# =============================================================================
# APPEL DU MODELE
# =============================================================================
def make_client() -> Mistral:
    """Instancie le client, avec un message utile s'il manque la cle."""
    cle = os.environ.get("MISTRAL_API_KEY")
    if not cle:
        raise SystemExit(
            "MISTRAL_API_KEY n'est pas définie.\n"
            "  1. Récupère une clé sur https://console.mistral.ai\n"
            '  2. cmd.exe :  setx MISTRAL_API_KEY "..."\n'
            "  3. Ouvre un NOUVEAU terminal (setx n'affecte pas la session courante)"
        )
    return Mistral(api_key=cle)


def supports_effort(model: str) -> bool:
    """Seuls les modeles de raisonnement acceptent reasoning_effort.

    Publique : rag_pipeline s'en sert pour n'annoncer l'effort que s'il part
    reellement dans la requete.
    """
    return "magistral" in model.lower()


def generate(
    question: str,
    results: list[dict],
    effort: str = DEFAULT_EFFORT,
    model: str = MODEL,
    show_stream: bool = True,
) -> Answer:
    """Appelle Mistral avec les chunks recuperes et retourne la reponse citee.

    On streame pour l'affichage progressif et pour eviter les timeouts HTTP avec
    un max_tokens large. Les citations, elles, sont relues APRES coup dans le
    texte complet : contrairement a Anthropic, elles ne viennent pas du serveur.
    """
    client = make_client()

    parametres: dict[str, Any] = {
        "model": model,
        "messages": build_messages(question, results),
        "max_tokens": MAX_TOKENS,
    }
    if effort and supports_effort(model):
        parametres["reasoning_effort"] = effort

    text_parts: list[str] = []
    finish_reason = ""
    usage_final: Any = None

    with client.chat.stream(**parametres) as flux:
        for event in flux:
            chunk = event.data
            if chunk.usage is not None:
                # L'usage n'arrive que sur le dernier evenement du flux.
                usage_final = chunk.usage
            for choix in chunk.choices or []:
                fragment = getattr(choix.delta, "content", None)
                if isinstance(fragment, str) and fragment:
                    text_parts.append(fragment)
                    if show_stream:
                        print(fragment, end="", flush=True)
                if choix.finish_reason:
                    finish_reason = str(choix.finish_reason)

    if show_stream:
        print()

    texte = "".join(text_parts)
    return Answer(
        text=texte,
        citations=parse_citations(texte, results),
        usage=_usage(usage_final),
        stop_reason=finish_reason,
    )


def parse_citations(texte: str, results: list[dict]) -> list[dict[str, Any]]:
    """Relit les marqueurs [n] ecrits par le modele et les relie aux extraits.

    ATTENTION a ce que cette fonction ne fait PAS : elle verifie que le numero
    existe, jamais qu'il est le bon. Un [2] pose sur une affirmation tiree de
    l'extrait 3 passera sans bruit. C'est la limite structurelle des citations
    ecrites par le modele, et la raison pour laquelle Anthropic les fait
    attacher par le serveur.
    """
    citations: list[dict[str, Any]] = []
    # On decoupe en phrases pour rattacher chaque marqueur a son affirmation.
    phrases = re.split(r"(?<=[.!?])\s+", texte)

    for phrase in phrases:
        for numero in re.findall(r"\[(\d+)\]", phrase):
            index = int(numero) - 1
            if not (0 <= index < len(results)):
                # Le modele a invente un numero : on le signale plutot que de
                # l'ignorer, sinon la reponse parait mieux sourcee qu'elle ne l'est.
                citations.append(
                    {
                        "cited_text": "",
                        "source": f"[{numero}] INEXISTANT",
                        "title": "numéro inventé par le modèle",
                        "index": index,
                        "claim": phrase.strip(),
                    }
                )
                continue

            item = results[index]
            citations.append(
                {
                    # Avec Anthropic, ce champ contenait le passage EXACT.
                    # Ici on ne peut donner que l'extrait entier.
                    "cited_text": item.get("text", ""),
                    "source": item.get("source", "?"),
                    "title": item.get("headers", "") or "",
                    "index": index,
                    "claim": phrase.strip(),
                }
            )
    return citations


def _usage(usage: Any) -> dict[str, int]:
    """Normalise l'usage Mistral vers les cles attendues par print_answer.

    Correspondance :  prompt_tokens -> input,  completion_tokens -> output.
    Il n'y a pas d'equivalent aux compteurs de cache d'Anthropic.
    """
    if usage is None:
        return {}
    return {
        "input": getattr(usage, "prompt_tokens", 0) or 0,
        "output": getattr(usage, "completion_tokens", 0) or 0,
        "total": getattr(usage, "total_tokens", 0) or 0,
    }


# =============================================================================
# AFFICHAGE
# =============================================================================
def print_answer(answer: Answer, show_text: bool = False) -> None:
    """Affiche les sources citees et le compte de tokens sous la reponse."""
    if show_text:
        print(answer.text)

    if answer.stop_reason in ("length", "model_length"):
        print(
            f"\n[!] Réponse tronquée (finish_reason={answer.stop_reason}) : "
            f"max_tokens={MAX_TOKENS} a été atteint."
        )

    if answer.citations:
        # Plusieurs phrases de la reponse peuvent s'appuyer sur le meme extrait.
        seen: set[tuple[str, int]] = set()
        print("\nSources citées :")
        for citation in answer.citations:
            key = (citation["source"], citation["index"])
            if key in seen:
                continue
            seen.add(key)
            excerpt = " ".join(citation["cited_text"].split())
            if len(excerpt) > 220:
                excerpt = excerpt[:220] + "..."
            print(f"\n  [{citation['index'] + 1}] {citation['source']}")
            if citation["title"]:
                print(f"      {citation['title']}")
            if excerpt:
                print(f"      « {excerpt} »")
    else:
        # Signal, pas un detail : soit le modele a repondu sans s'appuyer sur les
        # extraits, soit il a dit ne pas savoir — ce qui est le comportement voulu.
        print("\nAucune citation : le modèle ne s'est appuyé sur aucun extrait.")

    if answer.usage:
        u = answer.usage
        print(
            f"\ntokens — entrée {u.get('input', 0)} / sortie {u.get('output', 0)}"
            f" / total {u.get('total', 0)}"
        )


# =============================================================================
# INSPECTION SANS APPEL RESEAU
# =============================================================================
def describe_request(question: str, results: list[dict], effort: str = DEFAULT_EFFORT) -> str:
    """Decrit la requete qui SERAIT envoyee, sans rien envoyer."""
    messages = build_messages(question, results)
    envoie_effort = bool(effort) and supports_effort(MODEL)
    lines = [
        f"model          : {MODEL}",
        f"max_tokens     : {MAX_TOKENS}   (sortie seule chez Mistral)",
        f"reasoning_effort : {effort if envoie_effort else 'non envoyé'}"
        f"{'' if envoie_effort else f'  (le modèle {MODEL} ne le supporte pas)'}",
        f"messages       : {len(messages)}  (1 system + 1 user)",
        f"system         : {len(SYSTEM_PROMPT)} caractères",
        f"user           : {len(messages[1]['content'])} caractères",
        f"extraits       : {len(results)}, numérotés [1] à [{len(results)}]",
        "",
        "--- contenu du message user ---",
        messages[1]["content"],
    ]
    return "\n".join(lines)
