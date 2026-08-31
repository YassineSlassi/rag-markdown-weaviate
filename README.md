# RAG Markdown → Weaviate → Mistral

Pipeline RAG complet sur un corpus de fichiers Markdown : chunking conscient de
la structure, embeddings BGE-M3, index vectoriel Weaviate, et génération de
réponses citées avec Mistral.

```
corpus/*.md ─▶ [1 LOAD] ─▶ [2 CHUNK] ─▶ [3 EMBED] ─▶ [4 INDEX] ─▶ Weaviate
question ────▶ [5 EMBED QUERY] ─────▶ [6 SEARCH] ─▶ Top-K ─▶ [7 GENERATION]
```

## Prérequis

- Python 3.11
- Docker (pour Weaviate)
- Une clé API Mistral (**uniquement** pour la commande `ask`)

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate.bat          # cmd.exe  (PowerShell : .\.venv\Scripts\Activate.ps1)
pip install -r requirements.txt
docker compose up -d
```

Le premier lancement télécharge BGE-M3 (~2,2 Go) dans `~/.cache/huggingface`.

Pour la génération, définir la clé dans l'environnement (jamais dans le code) :

```bash
setx MISTRAL_API_KEY "..."
```

## Utilisation

```bash
python rag_pipeline.py index --dry-run              # lit et chunke, sans rien écrire
python rag_pipeline.py index                        # indexe le corpus
python rag_pipeline.py query "ma question" -k 5     # retrieval seul, sans clé API
python rag_pipeline.py ask   "ma question"          # réponse citée par Mistral
```

`--corpus DIR` et `--collection NAME` permettent d'indexer plusieurs corpus
côte à côte sans mélanger leurs vecteurs.

## Fichiers

| Fichier | Rôle |
|---|---|
| `rag_pipeline.py` | les 6 premiers étages + la CLI |
| `md_metadata.py` | lecture robuste du Markdown, schéma des 16 propriétés Weaviate |
| `rag_generate.py` | étage de génération et relecture des citations |
| `docker-compose.yml` | Weaviate (REST 8080 + gRPC 50051) |
| `eval/` | banc d'essai : recall@k, MRR, revue des échecs |

## Choix de conception

- **Chunking en deux passes** : structurelle (titres Markdown) puis par taille.
  La première donne des chunks portant une seule idée et remplit `h1/h2/h3` ;
  la seconde borne les sections trop longues.
- **Contextualisation** : le texte vectorisé est le chunk préfixé de son fil
  d'Ariane, ce qui lui rend le contexte que le découpage lui a retiré. Le texte
  *stocké* reste le chunk brut, et la requête n'est jamais contextualisée.
- **Citations par marqueurs** : les extraits sont numérotés dans le prompt, le
  modèle écrit `[1]`, `[2]`, et `parse_citations()` les relie aux sources.
- **Idempotence** : l'identité d'un chunk est `(source, chunk_index)`, jamais son
  contenu, réindexer écrase au lieu de dupliquer.

## Évaluation

Le dossier `eval/` mesure la qualité du retrieval sur des jeux de questions
annotées, pour savoir si un changement de configuration améliore ou dégrade
réellement les résultats.

```bash
python eval/recall_at_k.py --questions eval/questions_http_v2.json --collection HttpStress
python eval/revue_echecs.py --questions eval/questions_http_v2.json --collection HttpStress
```

Les annotations désignent des **fichiers sources**, jamais des `chunk_id` : un
`chunk_id` change dès qu'on touche à `CHUNK_SIZE`, ce qui invaliderait le jeu de
test sans le moindre message d'erreur.

## Limites connues

- L'embedding tourne sur CPU (~3 chunks/s). Compter ~1 h pour 10 000 chunks.
- Recherche dense uniquement. `text` est déjà indexé pour BM25, donc le passage
  en recherche hybride ne demande pas de réindexation.
- Les fichiers `.mdx` sont ignorés (seuls `.md` et `.markdown` sont lus).
- **Les citations peuvent être mal attribuées.** Le modèle écrit lui-même les
  marqueurs `[n]` ; `parse_citations()` vérifie que le numéro existe, jamais
  qu'il est le bon. `cited_text` contient l'extrait entier, pas le passage exact.
  L'API Anthropic offrait des citations attachées côté serveur, donc
  vérifiables ; l'API Mistral n'a pas d'équivalent.
- Les jeux de questions de `eval/` sont annotés par un modèle, pas par un
  humain. Ils servent à **comparer** deux configurations, pas à publier un
  chiffre absolu.

## Licences et attribution

Le code de ce dépôt est publié sous la licence indiquée dans `LICENSE.md`.

Le dossier `eval/corpus150/` contient 150 fiches du glossaire de
[MDN Web Docs](https://developer.mozilla.org/fr/docs/Glossary), extraites du
dépôt [`mdn/translated-content`](https://github.com/mdn/translated-content).
Ce contenu appartient à Mozilla et aux contributeurs de MDN, et est réutilisé
ici sous licence **CC-BY-SA 2.5** à des seules fins d'évaluation technique.
Il est régénérable avec `python eval/build_sample.py`.

Le corpus HTTP utilisé par `eval/questions_http_v2.json` n'est pas versionné :
il provient du même dépôt MDN, sous-arbres
`files/fr/web/http/reference/{headers,status}`.
