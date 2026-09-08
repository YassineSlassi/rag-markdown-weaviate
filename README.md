# RAG Markdown → Weaviate → Mistral

Pipeline RAG complet sur un corpus de fichiers Markdown : chunking conscient de
la structure, embeddings BGE-M3, index vectoriel Weaviate, et génération de
réponses citées avec Mistral.

```
corpus/*.md ─▶ [1 LOAD] ─▶ [2 CHUNK] ─▶ [3 EMBED] ─▶ [4 INDEX] ─▶ Weaviate
question ────▶ [5 EMBED QUERY] ─▶ [6 SEARCH] ─▶ [6bis RERANK] ─▶ [7 GENERATION]
                                                  (optionnel)

CLI : rag_pipeline.py          Interface graphique : app.py (Streamlit)
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
python rag_pipeline.py query "ma question" --rerank # + reranking par cross-encodeur
streamlit run app.py                                # interface graphique
```

Ces commandes supposent le **venv activé** (cf. Installation). Sans activation,
`python` et `streamlit` désignent ceux du système — ou n'existent pas — et tu
obtiens `'streamlit' n'est pas reconnu`. Préfixer par l'interpréteur du venv
fonctionne dans tous les cas, activé ou non :

```bash
.venv\Scripts\python.exe rag_pipeline.py query "ma question"
```

```bash
.venv\Scripts\python.exe -m streamlit run app.py
```

Le `-m` n'est nécessaire que pour Streamlit : `rag_pipeline.py` est un script
qu'on passe directement à l'interpréteur, alors que `streamlit` est un paquet
dont on invoque le point d'entrée. Sous PowerShell, le préfixe `.\` est
obligatoire : `.\.venv\Scripts\python.exe`.

`--corpus DIR` et `--collection NAME` permettent d'indexer plusieurs corpus
côte à côte sans mélanger leurs vecteurs.

## Fichiers

| Fichier | Rôle |
|---|---|
| `app.py` | interface Streamlit : retrieval, reranking, réponse citée |
| `rag_pipeline.py` | les 6 premiers étages + la CLI |
| `md_metadata.py` | lecture robuste du Markdown, schéma des 16 propriétés Weaviate |
| `rag_rerank.py` | étage 6bis : reranking des candidats par cross-encodeur |
| `rag_generate.py` | étage de génération et relecture des citations |
| `docker-compose.yml` | Weaviate (REST 8080 + gRPC 50051) |
| `eval/` | banc d'essai : recall@k, MRR, nDCG, revue des échecs |
| `eval/test_mesures.py` | vérifie les propriétés des métriques, sans Weaviate ni modèle |

## Interface graphique

```bash
.venv\Scripts\python.exe -m streamlit run app.py
```

Puis `http://localhost:8501`. La barre latérale expose la collection (avec son
nombre de chunks), `k`, le reranking et son modèle, et la génération. Chaque
chunk retourné est dépliable, avec son cosinus, son score de reranking et son
déplacement dans le classement ; avec le reranking, un bloc montre le vivier
complet des 20 candidats réordonnés, donc ce que le cross-encodeur a écarté.

Sans `MISTRAL_API_KEY` dans l'environnement, la génération est désactivée et le
retrieval reste pleinement utilisable.

**Le point à comprendre avant de lire `app.py`** : Streamlit réexécute le script
de haut en bas à chaque interaction. Les trois `@st.cache_resource` ne sont donc
pas une optimisation mais la condition pour que l'interface soit utilisable —
sans eux, bouger un curseur rechargerait 4,4 Go de modèles. Corollaire : le
client Weaviate étant mis en cache, il ne faut jamais l'y fermer, contrairement
au `try/finally` correct partout ailleurs dans ce projet.

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
- **Reranking en deux étages** (`--rerank`) : BGE-M3 est un *bi-encodeur*, il
  encode question et document séparément — d'où des vecteurs pré-calculables,
  et une recherche en 200 ms sur des milliers de chunks. Le reranker est un
  *cross-encodeur* : il lit la paire `(question, chunk)` d'un seul tenant, donc
  chaque mot de la question porte attention au document. Plus fin, mais rien
  n'est pré-calculable. D'où la division du travail : le retriever ratisse large
  sur tout l'index, le reranker ordonne finement les 20 candidats retenus.

## Évaluation

Le dossier `eval/` mesure la qualité du retrieval sur des jeux de questions
annotées, pour savoir si un changement de configuration améliore ou dégrade
réellement les résultats.

```bash
python eval/recall_at_k.py --questions eval/questions_http_v3.json --collection HttpStress
python eval/recall_at_k.py --questions eval/questions_http_v3.json --collection HttpStress --rerank
python eval/revue_echecs.py --questions eval/questions_http_v2.json --collection HttpStress
```

Trois mesures, et elles ne disent pas la même chose. **recall@k** répond « le bon
document remonte-t-il ? » et ignore le rang. **MRR** ne regarde que le rang du
*premier* succès. **nDCG@k** lit tout le classement, pondère chaque position et
exploite les niveaux de pertinence — c'est la seule des trois à voir au-delà du
premier succès, et donc la seule utile quand une question a plusieurs bonnes
réponses de qualité inégale.

Les annotations désignent des **fichiers sources**, jamais des `chunk_id` : un
`chunk_id` change dès qu'on touche à `CHUNK_SIZE`, ce qui invaliderait le jeu de
test sans le moindre message d'erreur.

`questions_http_v3.json` gradue la pertinence : `2` répond exactement, `1` est un
voisin utile de la même famille. `recall@k` et le MRR seuillent à `2` — ajouter
des voisins ne doit pas gonfler des mesures binaires — et seul le nDCG exploite
les niveaux.

`--rerank` mesure les deux classements **dans le même run**, sur les mêmes
candidats. C'est ce qui rend la comparaison exacte, et ça fournit un témoin de
contrôle : le reranker réordonne sans rien chercher, donc `recall@20` sur un
vivier de 20 est mathématiquement invariant. Le script le vérifie et signale
l'écart comme un bug s'il en trouve un.

### Résultats mesurés

96 questions graduées, corpus HTTP (259 fiches, 2244 chunks), vivier de 20.

| | @1 | @3 | @5 | @10 | @20 | MRR | nDCG@10 | ms/candidat |
|---|---|---|---|---|---|---|---|---|
| BGE-M3 seul | 0,60 | 0,79 | 0,86 | 0,93 | 0,99 | 0,725 | 0,720 | — |
| `+ bge-reranker-base` | 0,73 | 0,90 | 0,93 | 0,94 | 0,99 | 0,816 | 0,770 | 501 |
| `+ bge-reranker-v2-m3` *(défaut)* | **0,79** | **0,94** | **0,97** | **0,99** | 0,99 | **0,868** | **0,819** | 1702 |

`@20` est identique sur les trois lignes : c'est le témoin de contrôle, pas une
coïncidence. Le gain se concentre en tête, ce qu'un reranker est censé faire.

`v2-m3` est bâti sur BGE-M3 lui-même et **ne dégrade aucune famille de
questions**, là où `base` en régressait trois. La différence est nette sur les
questions dont la formulation française s'éloigne du vocabulaire du corpus
(« durée de conservation d'une vérification préalable » pour
`Access-Control-Max-Age`) : `base` y renvoie le bon fichier au rang 14, `v2-m3`
au rang 1. Les deux ont pourtant une confiance basse sur cette question (0,003
et 0,031) — ce qui les sépare n'est pas le score absolu mais la qualité du
classement à confiance égale.

Les 20 échecs restants sont presque tous des quasi-succès au rang 2 ou 3, sur
des paires confusables (`if-modified-since` / `if-unmodified-since`,
`www-authenticate` / `proxy-authenticate`). Un seul échec est hors de portée du
reranking : `if-match` n'est pas dans le vivier de 20, donc c'est le retriever
qu'il faudrait corriger, pas l'ordre.

## Limites connues

- L'embedding tourne sur CPU (~3 chunks/s). Compter ~1 h pour 10 000 chunks.
- Le reranking coûte un passage avant par candidat, sans rien de pré-calculable :
  **~34 s par question** sur CPU avec `v2-m3` et 20 candidats. Acceptable pour
  un run d'évaluation ou une question posée à la main, exclu pour du trafic.
  Trois leviers, dans cet ordre : un GPU, `--rerank-modele BAAI/bge-reranker-base`
  (3,4× plus rapide, ~6 points de `@1` en moins), ou réduire `RERANK_POOL`.
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
