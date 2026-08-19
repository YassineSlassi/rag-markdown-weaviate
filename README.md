# RAG Markdown → Weaviate → Claude

Pipeline RAG complet sur un corpus de fichiers Markdown : chunking conscient de
la structure, embeddings BGE-M3, index vectoriel Weaviate, et génération de
réponses citées avec Claude.

```
corpus/*.md ─▶ [1 LOAD] ─▶ [2 CHUNK] ─▶ [3 EMBED] ─▶ [4 INDEX] ─▶ Weaviate
question ────▶ [5 EMBED QUERY] ─────▶ [6 SEARCH] ─▶ Top-K ─▶ [7 GENERATION]
```

## Prérequis

- Python 3.11
- Docker (pour Weaviate)
- Une clé API Anthropic — **uniquement** pour la commande `ask`

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
setx ANTHROPIC_API_KEY "sk-ant-..."
```

## Utilisation

```bash
python rag_pipeline.py index --dry-run              # lit et chunke, sans rien écrire
python rag_pipeline.py index                        # indexe le corpus
python rag_pipeline.py query "ma question" -k 5     # retrieval seul, sans clé API
python rag_pipeline.py ask   "ma question"          # réponse citée par Claude
```

`--corpus DIR` et `--collection NAME` permettent d'indexer plusieurs corpus
côte à côte sans mélanger leurs vecteurs.

## Fichiers

| Fichier | Rôle |
|---|---|
| `rag_pipeline.py` | les 6 premiers étages + la CLI |
| `md_metadata.py` | lecture robuste du Markdown, schéma des 16 propriétés Weaviate |
| `rag_generate.py` | étage de génération, citations natives de l'API |
| `docker-compose.yml` | Weaviate (REST 8080 + gRPC 50051) |

## Choix de conception

- **Chunking en deux passes** : structurelle (titres Markdown) puis par taille.
  La première donne des chunks portant une seule idée et remplit `h1/h2/h3` ;
  la seconde borne les sections trop longues.
- **Contextualisation** : le texte vectorisé est le chunk préfixé de son fil
  d'Ariane, ce qui lui rend le contexte que le découpage lui a retiré. Le texte
  *stocké* reste le chunk brut, et la requête n'est jamais contextualisée.
- **Citations natives** : chaque chunk est passé à Claude comme bloc
  `search_result`, et l'API attache elle-même les citations avec le passage
  exact qui appuie chaque affirmation. Le modèle n'écrit aucun marqueur.
- **Idempotence** : l'identité d'un chunk est `(source, chunk_index)`, jamais son
  contenu, réindexer écrase au lieu de dupliquer.

## Limites connues

- L'embedding tourne sur CPU (~3 chunks/s). Compter ~1 h pour 10 000 chunks.
- Recherche dense uniquement. `text` est déjà indexé pour BM25, donc le passage
  en recherche hybride ne demande pas de réindexation.
- Les fichiers `.mdx` sont ignorés (seuls `.md` et `.markdown` sont lus).
