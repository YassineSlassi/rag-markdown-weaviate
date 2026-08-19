"""
Etage de generation du RAG : Top-K chunks -> reponse citee par Claude.

Les citations ne sont PAS ecrites par le modele. Chaque chunk est passe comme un
bloc de contenu `search_result` (type prevu pour le RAG, pas d'en-tete beta), et
le serveur attache lui-meme les citations a la reponse : `cited_text` (le passage
exact qui appuie l'affirmation), `source`, `title`, `search_result_index`.

C'est verifiable, contrairement a des marqueurs "[1]" que le modele ecrirait
lui-meme et pourrait mal attribuer sans que rien ne le detecte. Le systeme prompt
lui interdit donc explicitement d'en ecrire, sous peine de doublon contradictoire.

Auth : ANTHROPIC_API_KEY dans l'environnement, jamais en dur ici.
    cmd.exe :  setx ANTHROPIC_API_KEY "sk-ant-..."   puis NOUVEAU terminal
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import anthropic

# =============================================================================
# CONFIGURATION
# =============================================================================
MODEL = "claude-opus-5"

# Sur Claude Opus 5 la reflexion est active par defaut, et max_tokens plafonne
# reflexion + texte ENSEMBLE : un budget calibre sur la seule longueur de reponse
# la tronque en plein milieu. On streame, donc la marge ne coute rien.
MAX_TOKENS = 16000

# Synthese extractive sur quelques courts extraits : `low` suffit et reste bien
# moins cher et plus rapide. A balayer (--effort) sur ses propres questions, le
# bon reglage depend du corpus.
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

N'écris pas de marqueurs de source toi-même — ni [1], ni (source: X), ni notes \
de bas de page. Les citations sont attachées automatiquement à ta réponse par \
l'API, à partir des extraits ; en ajouter à la main ferait doublon et pourrait \
contredire les vraies.
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
def build_search_results(results: list[dict]) -> list[dict[str, Any]]:
    """Convertit les chunks du retrieval en blocs `search_result`.

    Champs obligatoires : `source` (chaine stable identifiant la provenance),
    `title`, et `content` qui doit etre un TABLEAU de blocs texte.
    `citations: {"enabled": True}` est ce qui declenche l'attachement des
    citations ; sans lui le modele repond mais rien n'est attribue.
    """
    blocks: list[dict[str, Any]] = []
    for item in results:
        source = item.get("source", "?")
        headers = item.get("headers") or source
        blocks.append(
            {
                "type": "search_result",
                # URI plutot que le nom de fichier seul : un meme fichier fournit
                # plusieurs chunks et on veut savoir lequel a ete cite.
                "source": f"corpus://{source}#chunk-{item.get('rank', 0)}",
                "title": headers,
                "content": [{"type": "text", "text": item.get("text", "")}],
                "citations": {"enabled": True},
            }
        )
    return blocks


def build_messages(question: str, results: list[dict]) -> list[dict[str, Any]]:
    """Assemble le message utilisateur : les extraits PUIS la question.

    L'ordre compte : contenu de reference avant la question, comme pour les
    documents et les PDF. C'est aussi le bon ordre pour le cache de prompt.
    """
    return [
        {
            "role": "user",
            "content": [
                *build_search_results(results),
                {"type": "text", "text": f"Question : {question}"},
            ],
        }
    ]


# =============================================================================
# APPEL DU MODELE
# =============================================================================
def make_client() -> anthropic.Anthropic:
    """Instancie le client, avec un message utile s'il manque la cle."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit(
            "ANTHROPIC_API_KEY n'est pas définie.\n"
            "  1. Récupère une clé sur https://console.anthropic.com\n"
            '  2. cmd.exe :  setx ANTHROPIC_API_KEY "sk-ant-..."\n'
            "  3. Ouvre un NOUVEAU terminal (setx n'affecte pas la session courante)"
        )
    # Le SDK lit aussi ANTHROPIC_BASE_URL s'il est defini : verifier qu'il ne
    # traine pas dans l'environnement, il redirigerait les appels ailleurs.
    return anthropic.Anthropic()


def generate(
    question: str,
    results: list[dict],
    effort: str = DEFAULT_EFFORT,
    model: str = MODEL,
    show_stream: bool = True,
) -> Answer:
    """Appelle Claude avec les chunks recuperes et retourne la reponse citee.

    On streame pour l'affichage progressif et pour eviter les timeouts HTTP avec
    un max_tokens large. Les citations arrivent aussi en streaming (deltas
    `citations_delta`) mais sont relues ici sur le message final : resultat
    identique, et les deltas ne servent qu'a surligner en direct dans une UI.
    """
    client = make_client()

    text_parts: list[str] = []
    with client.messages.stream(
        model=model,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=build_messages(question, results),
        output_config={"effort": effort},
        # Explicite bien que ce soit le defaut sur Opus 5.
        thinking={"type": "adaptive"},
    ) as stream:
        for delta in stream.text_stream:
            text_parts.append(delta)
            if show_stream:
                print(delta, end="", flush=True)
        message = stream.get_final_message()

    if show_stream:
        print()

    # Verifier stop_reason AVANT de lire le contenu : les classificateurs de
    # surete peuvent decliner une requete, ce qui renvoie un HTTP 200 avec un
    # contenu vide ou partiel. Lire message.content[0] casserait sur ce cas.
    if message.stop_reason == "refusal":
        details = getattr(message, "stop_details", None)
        return Answer(
            text="".join(text_parts),
            usage=_usage(message),
            stop_reason="refusal",
            refusal=getattr(details, "category", None) or "non précisée",
        )

    citations: list[dict[str, Any]] = []
    for block in message.content:
        # Une reponse citee est decoupee en PLUSIEURS blocs texte : seuls ceux
        # qui s'appuient sur un extrait portent une liste `citations`.
        if block.type != "text":
            continue
        for citation in getattr(block, "citations", None) or []:
            citations.append(
                {
                    "cited_text": getattr(citation, "cited_text", ""),
                    "source": getattr(citation, "source", ""),
                    "title": getattr(citation, "title", "") or "",
                    "index": getattr(citation, "search_result_index", -1),
                    "claim": block.text,
                }
            )

    return Answer(
        text="".join(text_parts),
        citations=citations,
        usage=_usage(message),
        stop_reason=message.stop_reason or "",
    )


def _usage(message: Any) -> dict[str, int]:
    usage = getattr(message, "usage", None)
    if usage is None:
        return {}
    return {
        "input": getattr(usage, "input_tokens", 0) or 0,
        "output": getattr(usage, "output_tokens", 0) or 0,
        "cache_read": getattr(usage, "cache_read_input_tokens", 0) or 0,
        "cache_write": getattr(usage, "cache_creation_input_tokens", 0) or 0,
    }


# =============================================================================
# AFFICHAGE
# =============================================================================
def print_answer(answer: Answer, show_text: bool = False) -> None:
    """Affiche les sources citees et le compte de tokens sous la reponse."""
    if answer.stop_reason == "refusal":
        print(
            f"\n[!] Requête déclinée par les garde-fous du modèle "
            f"(catégorie : {answer.refusal}). Ce n'est pas une erreur HTTP."
        )
        return

    if show_text:
        print(answer.text)

    if answer.citations:
        # Plusieurs phrases de la reponse peuvent s'appuyer sur le meme passage.
        seen: set[tuple[str, str]] = set()
        print("\nSources citées :")
        for citation in answer.citations:
            key = (citation["source"], citation["cited_text"][:120])
            if key in seen:
                continue
            seen.add(key)
            excerpt = " ".join(citation["cited_text"].split())
            if len(excerpt) > 220:
                excerpt = excerpt[:220] + "..."
            print(f"\n  [{citation['source']}]")
            if citation["title"]:
                print(f"    {citation['title']}")
            print(f"    « {excerpt} »")
    else:
        # Signal, pas un detail : soit le modele a repondu sans s'appuyer sur les
        # extraits, soit il a dit ne pas savoir — ce qui est le comportement voulu.
        print("\nAucune citation : le modèle ne s'est appuyé sur aucun extrait.")

    if answer.usage:
        u = answer.usage
        print(
            f"\ntokens — entrée {u.get('input', 0)} / sortie {u.get('output', 0)}"
            f" / cache lu {u.get('cache_read', 0)}"
        )


# =============================================================================
# INSPECTION SANS APPEL RESEAU
# =============================================================================
def describe_request(question: str, results: list[dict], effort: str = DEFAULT_EFFORT) -> str:
    """Decrit la requete qui SERAIT envoyee, sans rien envoyer.

    Permet de relire la charge utile sans cle API ni depense de tokens.
    """
    messages = build_messages(question, results)
    blocks = messages[0]["content"]
    lines = [
        f"model        : {MODEL}",
        f"max_tokens   : {MAX_TOKENS}   (réflexion + texte partagent ce plafond)",
        f"effort       : {effort}",
        "thinking     : adaptive",
        f"system       : {len(SYSTEM_PROMPT)} caractères",
        f"blocs        : {len(blocks)}  ({len(blocks) - 1} search_result + 1 text)",
        "",
    ]
    for block in blocks:
        if block["type"] == "search_result":
            body = " ".join(block["content"][0]["text"].split())
            lines.append(f"  search_result  source={block['source']}")
            lines.append(f"                 title={block['title']}")
            lines.append(f"                 citations={block['citations']}")
            lines.append(f"                 content={body[:90]}...")
        else:
            lines.append(f"  text           {block['text']}")
    return "\n".join(lines)
