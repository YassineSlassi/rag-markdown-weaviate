"""
Pipeline RAG : Markdown -> chunks -> BGE-M3 -> Weaviate -> Top-K -> reponse.

    corpus/*.md --> [1 LOAD] --> [2 CHUNK] --> [3 EMBED] --> [4 INDEX] --> Weaviate
    question ------> [5 EMBED QUERY] -------> [6 SEARCH] -------> Top-K
                                                 |
                                                 +--> [7 GENERATION] (rag_generate)

Usage :
    python rag_pipeline.py index [--corpus DIR] [--collection NAME] [--recreate] [--dry-run]
    python rag_pipeline.py query "question" [-k 5] [--collection NAME]
    python rag_pipeline.py ask   "question" [-k 5] [--effort low] [--dry-run]

`query` s'arrete au retrieval et ne demande aucune cle API. `ask` ajoute l'etage
de generation (voir rag_generate.py). Une collection par corpus permet de les
comparer sans melanger leurs vecteurs.

Lecture des fichiers et faconnage des metadonnees : md_metadata.py.

Trois invariants a ne pas casser :
  - normalize_embeddings=True (etage 3) va avec VectorDistances.COSINE (etage 4).
    Changer l'un sans l'autre degrade la pertinence sans lever d'erreur.
  - Le texte vectorise n'est pas le texte stocke : contextualize() prefixe le fil
    d'Ariane avant l'embedding. La requete, elle, n'est jamais contextualisee.
  - L'identite d'un chunk est (source, chunk_index), jamais son contenu.
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

import weaviate
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)
from tqdm import tqdm
from weaviate.classes.config import Configure, VectorDistances
from weaviate.classes.query import MetadataQuery
from weaviate.util import generate_uuid5

from md_metadata import (
    HEADER_KEYS,
    clean_header_text,
    read_corpus,
    to_weaviate_properties,
    validate_properties,
    weaviate_properties,
)

# =============================================================================
# CONFIGURATION
# =============================================================================
CORPUS_DIR = Path(__file__).parent / "corpus"

EMBED_MODEL_NAME = "BAAI/bge-m3"
EMBED_DIM = 1024

# Sur CPU, un batch plus large n'accelere presque pas et augmente le padding
# (le cout d'un lot suit son texte le plus long). Sur GPU CUDA : 32 ou 64.
EMBED_BATCH_SIZE = 8

COLLECTION_NAME = "MarkdownChunk"

# ~1000 caracteres = 250-300 tokens en francais. Tres en dessous des 8192 tokens
# que BGE-M3 accepte, volontairement : un chunk large dilue son vecteur sur
# plusieurs idees. Recouvrement de 15 % contre les coupures en pleine idee.
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

# Jusqu'a H3 seulement : plus profond donne des chunks d'une ou deux phrases,
# trop specifiques pour matcher une question formulee largement.
MARKDOWN_HEADERS = [
    ("#", "h1"),
    ("##", "h2"),
    ("###", "h3"),
]

TOP_K = 5

# Debit mesure sur CPU (Ryzen 5 5600X) : sert a estimer un temps en --dry-run.
CHUNKS_PER_SECOND = 2.9


# =============================================================================
# ETAGE 1 — Lecture du corpus
# =============================================================================
def load_markdown(corpus_dir: Path) -> list[Document]:
    """Lit recursivement les .md et retourne un Document par fichier.

    page_content garde la syntaxe Markdown intacte : l'etage 2 decoupe dessus.
    """
    docs: list[Document] = []
    for md in read_corpus(corpus_dir):
        if not md.body.strip():
            print(f"    ignoré (vide) : {md.doc_meta['source']}")
            continue
        docs.append(Document(page_content=md.body, metadata=dict(md.doc_meta)))
    return docs


# =============================================================================
# ETAGE 2 — Chunking
# =============================================================================
def chunk_documents(docs: list[Document]) -> list[Document]:
    """Decoupe en deux passes : structurelle (titres) puis par taille.

    La passe structurelle remplit h1/h2/h3 mais ne borne pas la taille ; la passe
    par taille sert de garde-fou sur les sections trop longues.
    strip_headers=False : le titre reste dans le texte, car c'est le texte qui
    est vectorise, pas la metadata.
    """
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=MARKDOWN_HEADERS,
        strip_headers=False,
    )
    size_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        # ". " ajoute aux separateurs par defaut pour preferer une frontiere de
        # phrase a une espace quelconque dans un long paragraphe.
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: list[Document] = []
    for doc in docs:
        sections = header_splitter.split_text(doc.page_content)
        for section in sections:
            # split_text() rend des Documents portant SA propre metadata : sans
            # cette refusion, source/title/tags sont perdus des la 1re passe.
            cleaned = {
                key: clean_header_text(section.metadata[key])
                for key in HEADER_KEYS
                if section.metadata.get(key)
            }
            section.metadata = {**doc.metadata, **section.metadata, **cleaned}

        sized = [
            c for c in size_splitter.split_documents(sections) if c.page_content.strip()
        ]
        # Numeroter APRES le filtrage : sinon chunk_index a des trous et
        # l'idempotence de l'indexation, qui en depend, devient instable.
        for i, chunk in enumerate(sized):
            chunk.metadata["chunk_index"] = i
            chunk.metadata["n_chunks"] = len(sized)
        chunks.extend(sized)

    return chunks


def contextualize(chunk: Document) -> str:
    """Retourne le texte envoye au modele d'embedding : fil d'Ariane + chunk.

    Rend au chunk le contexte que le decoupage lui a retire. dict.fromkeys()
    deduplique en gardant l'ordre : title et h1 sont souvent identiques.
    """
    trail = [chunk.metadata.get("title", "")]
    trail += [chunk.metadata.get(key, "") for key in HEADER_KEYS]
    parts = dict.fromkeys(str(t).strip() for t in trail if t and str(t).strip())
    breadcrumb = " > ".join(parts)
    return f"{breadcrumb}\n\n{chunk.page_content}" if breadcrumb else chunk.page_content


# =============================================================================
# ETAGE 3 — Embeddings BGE-M3
# =============================================================================
def build_embedder() -> HuggingFaceEmbeddings:
    """Charge BGE-M3 (~2,2 Go). A n'appeler qu'une fois par processus."""
    print(f"[3] chargement de {EMBED_MODEL_NAME} sur CPU...")
    print("    (au tout premier lancement : ~2,2 Go à télécharger)")
    started = time.perf_counter()
    embedder = HuggingFaceEmbeddings(
        model_name=EMBED_MODEL_NAME,
        # model_kwargs configure le chargement du modele, encode_kwargs l'appel
        # d'encodage. device="cpu" : le GPU AMD n'est pas exploitable par
        # PyTorch sous Windows et torch est en build CPU — "cuda" leverait.
        model_kwargs={"device": "cpu"},
        encode_kwargs={
            "normalize_embeddings": True,
            "batch_size": EMBED_BATCH_SIZE,
        },
    )
    print(f"    modèle prêt en {time.perf_counter() - started:.1f}s")
    return embedder


def embed_texts(embedder: HuggingFaceEmbeddings, texts: list[str]) -> list[list[float]]:
    """Encode une liste de textes en vecteurs, dans le meme ordre.

    Deux niveaux de batch : sentence-transformers regroupe deja en interne via
    encode_kwargs ; la boucle ci-dessous existe pour la progression et pour ne
    pas garder toute la matrice intermediaire en memoire.
    """
    if not texts:
        return []

    vectors: list[list[float]] = []
    for start in tqdm(
        range(0, len(texts), EMBED_BATCH_SIZE),
        desc="[3] embeddings",
        unit="batch",
    ):
        vectors.extend(embedder.embed_documents(texts[start : start + EMBED_BATCH_SIZE]))

    # Un decalage d'ordre ou une dimension inattendue produit une recherche qui
    # renvoie des resultats absurdes sans jamais lever d'erreur.
    assert len(vectors) == len(texts), f"{len(vectors)} vecteurs pour {len(texts)} textes"
    assert len(vectors[0]) == EMBED_DIM, f"dimension {len(vectors[0])} != {EMBED_DIM}"
    return vectors


# =============================================================================
# ETAGE 4 — Weaviate : connexion, schema, indexation
# =============================================================================
def connect_weaviate() -> weaviate.WeaviateClient:
    """Connexion au Weaviate local (REST 8080 + gRPC 50051)."""
    try:
        client = weaviate.connect_to_local()
    except Exception as exc:
        raise SystemExit(
            f"Connexion à Weaviate impossible : {exc}\n"
            "Le conteneur tourne-t-il ?  ->  docker compose up -d"
        ) from exc

    if not client.is_ready():
        client.close()
        raise SystemExit("Weaviate répond mais n'est pas prêt.")
    return client


def ensure_collection(client, name: str = COLLECTION_NAME, recreate: bool = False):
    """Cree la collection si absente, la retourne."""
    if recreate and client.collections.exists(name):
        print(f"[4] suppression de la collection {name}")
        client.collections.delete(name)

    if not client.collections.exists(name):
        client.collections.create(
            name,
            properties=weaviate_properties(),
            # Sans self_provided(), Weaviate vectorise lui-meme a l'insertion :
            # nos vecteurs BGE-M3 sont ignores et les requetes comparent des
            # vecteurs de deux modeles differents. Ca ne plante pas, ca renvoie
            # n'importe quoi.
            vector_config=Configure.Vectors.self_provided(
                # COSINE parce que les embeddings sont normalises (etage 3).
                vector_index_config=Configure.VectorIndex.hnsw(
                    distance_metric=VectorDistances.COSINE,
                ),
            ),
        )
        print(f"[4] collection {name} créée ({len(weaviate_properties())} propriétés)")
    else:
        print(f"[4] collection {name} existante, réutilisée")

    return client.collections.get(name)


def index_chunks(collection, chunks: list[Document], vectors: list[list[float]]) -> None:
    """Insere les chunks et leurs vecteurs, de facon idempotente."""
    assert len(chunks) == len(vectors), "chunks et vecteurs désalignés"

    checked = False
    with collection.batch.dynamic() as batch:
        for chunk, vector in zip(chunks, vectors):
            meta = chunk.metadata
            properties = to_weaviate_properties(
                chunk_text=chunk.page_content,
                doc_meta=meta,
                header_meta={key: meta.get(key) for key in HEADER_KEYS},
                chunk_index=meta.get("chunk_index", 0),
                n_chunks=meta.get("n_chunks", 1),
            )
            if not checked:
                # Weaviate ajoute silencieusement au schema toute propriete
                # inconnue : une faute de frappe cree une propriete fantome au
                # lieu de lever. Un controle sur le premier objet suffit.
                validate_properties(properties)
                checked = True

            batch.add_object(
                properties=properties,
                vector=vector,
                # Identite = (source, chunk_index), pas le contenu : un
                # paragraphe corrige doit ECRASER l'objet existant. Inclure le
                # contenu produirait un nouvel UUID et laisserait l'ancien en
                # base. Contrepartie : si un document passe de 12 a 8 chunks,
                # les chunks 8-11 survivent — d'ou --recreate.
                uuid=generate_uuid5(
                    {
                        "source": properties["source"],
                        "chunk_index": properties["chunk_index"],
                    }
                ),
            )

    failed = collection.batch.failed_objects
    if failed:
        print(f"    [!] {len(failed)} objet(s) en échec :")
        for failure in failed[:5]:
            print(f"       - {failure.message}")
    else:
        print(f"    {len(chunks)} objets envoyés sans erreur")


# =============================================================================
# ETAGES 5 & 6 — Requete et recherche Top-K
# =============================================================================
def search(collection, embedder, question: str, k: int = TOP_K) -> list[dict]:
    """Encode la question et retourne les k chunks les plus proches."""
    # embed_query() et non embed_documents() : certains modeles encodent requete
    # et document differemment (pas BGE-M3, mais la distinction reste correcte).
    # Pas de contextualize() ici : la requete n'a pas de fil d'Ariane.
    query_vector = embedder.embed_query(question)
    assert len(query_vector) == EMBED_DIM

    response = collection.query.near_vector(
        near_vector=query_vector,
        limit=k,
        # Sans return_metadata, aucun score n'est renvoye : il vit dans
        # metadata, pas dans properties.
        return_metadata=MetadataQuery(distance=True),
    )

    results = []
    for rank, obj in enumerate(response.objects, start=1):
        properties = obj.properties
        distance = obj.metadata.distance
        results.append(
            {
                "rank": rank,
                # Distance cosinus : 0 = identique, 1 = orthogonal, 2 = oppose.
                "score": 1.0 - distance if distance is not None else float("nan"),
                "source": properties.get("source", "?"),
                "headers": properties.get("headers") or properties.get("title", ""),
                "text": properties.get("text", ""),
            }
        )
    return results


def print_results(results: list[dict]) -> None:
    """Affiche les resultats du retrieval."""
    if not results:
        print("Aucun résultat. La collection est-elle indexée ?  -> python rag_pipeline.py index")
        return

    for item in results:
        extract = " ".join(item["text"].split())
        if len(extract) > 300:
            extract = extract[:300] + "..."
        print(f"\n#{item['rank']}  score {item['score']:.4f}  —  {item['source']}")
        if item["headers"]:
            print(f"    {item['headers']}")
        print(f"    {extract}")


# =============================================================================
# ORCHESTRATION
# =============================================================================
def normalize_collection_name(name: str) -> str:
    """Met la 1re lettre en majuscule, comme Weaviate le fait cote serveur.

    Sans ca, indexer avec `--collection mdn` cree "Mdn" et un exists("mdn")
    ulterieur peut viser a cote.
    """
    name = name.strip()
    return name[:1].upper() + name[1:] if name else name


def cmd_index(
    corpus_dir: Path = CORPUS_DIR,
    collection_name: str = COLLECTION_NAME,
    recreate: bool = False,
    dry_run: bool = False,
) -> None:
    """Indexation complete : etages 1 -> 4."""
    if not corpus_dir.is_dir():
        raise SystemExit(f"Dossier introuvable : {corpus_dir}")

    print(f"[1] lecture de {corpus_dir}")
    docs = load_markdown(corpus_dir)
    if not docs:
        raise SystemExit(f"Aucun fichier Markdown exploitable dans {corpus_dir}")
    print(f"    {len(docs)} document(s)")

    print("[2] chunking")
    chunks = chunk_documents(docs)
    if not chunks:
        raise SystemExit("Le chunking n'a produit aucun chunk.")
    lengths = [len(c.page_content) for c in chunks]
    print(
        f"    {len(chunks)} chunks — "
        f"min {min(lengths)} / médiane {int(statistics.median(lengths))} / max {max(lengths)} car."
    )

    if dry_run:
        # L'embedding CPU coute des dizaines de minutes sur un gros corpus :
        # inspecter le chunking avant de le payer.
        minutes = len(chunks) / CHUNKS_PER_SECOND / 60
        median = int(statistics.median(lengths))
        print("\n--dry-run : arrêt avant l'embedding.")
        print(f"    {len(chunks)} chunks -> environ {minutes:.1f} min d'embedding sur CPU")
        print(f"    médiane {median} caractères.")
        print("    Trop petit (<150) = découpage trop fin. Trop gros (proche de")
        print(f"    {CHUNK_SIZE}) = la passe structurelle n'a pas mordu : pas de titres ?")
        print("\n    3 chunks échantillonnés, tels qu'ils seront vectorisés :")
        step = max(1, len(chunks) // 3)
        for chunk in chunks[::step][:3]:
            preview = " ".join(contextualize(chunk).split())[:180]
            print(f"      - [{chunk.metadata['source']}] {preview}...")
        return

    texts = [contextualize(chunk) for chunk in chunks]

    embedder = build_embedder()
    vectors = embed_texts(embedder, texts)
    print(f"    {len(vectors)} vecteurs de dimension {len(vectors[0])}")

    client = connect_weaviate()
    try:
        collection = ensure_collection(client, collection_name, recreate=recreate)
        index_chunks(collection, chunks, vectors)
        total = collection.aggregate.over_all(total_count=True).total_count
        print(f"\n{len(docs)} fichiers -> {len(chunks)} chunks -> {len(vectors)} vecteurs "
              f"-> {total} objets dans {collection_name}")
    finally:
        # Le client v4 garde des connexions gRPC ouvertes sans close().
        client.close()


def cmd_query(
    question: str,
    k: int = TOP_K,
    collection_name: str = COLLECTION_NAME,
) -> None:
    """Retrieval seul : etages 5 -> 6."""
    client = connect_weaviate()
    try:
        if not client.collections.exists(collection_name):
            existing = sorted(client.collections.list_all().keys())
            raise SystemExit(
                f"La collection {collection_name} n'existe pas.\n"
                f"Collections présentes : {existing or '(aucune)'}\n"
                "Indexe d'abord :  python rag_pipeline.py index"
            )
        collection = client.collections.get(collection_name)

        embedder = build_embedder()
        print(f"\n[5-6] question : {question!r}  (collection {collection_name})")
        results = search(collection, embedder, question, k=k)
        print_results(results)
    finally:
        client.close()


def cmd_ask(
    question: str,
    k: int = TOP_K,
    collection_name: str = COLLECTION_NAME,
    effort: str | None = None,
    dry_run: bool = False,
) -> None:
    """RAG complet : retrieval (5-6) puis generation (7).

    rag_generate est importe ici et non en tete de module : le SDK mistralai
    n'est requis que pour cette commande, `index` et `query` s'en passent.
    """
    import rag_generate

    effort = effort or rag_generate.DEFAULT_EFFORT

    client = connect_weaviate()
    try:
        if not client.collections.exists(collection_name):
            raise SystemExit(
                f"La collection {collection_name} n'existe pas.\n"
                "Indexe d'abord :  python rag_pipeline.py index"
            )
        collection = client.collections.get(collection_name)

        embedder = build_embedder()
        print(f"\n[5-6] retrieval : {question!r}")
        results = search(collection, embedder, question, k=k)
        if not results:
            raise SystemExit("Le retrieval n'a rien renvoyé — la collection est-elle vide ?")
        for item in results:
            print(f"      #{item['rank']} {item['score']:.4f}  {item['source']}  |  {item['headers']}")
    finally:
        client.close()

    if dry_run:
        print("\n[7] --dry-run : requête qui SERAIT envoyée, sans appel réseau\n")
        print(rag_generate.describe_request(question, results, effort=effort))
        return

    effort_affiche = (
        effort if rag_generate.supports_effort(rag_generate.MODEL) else "non envoye"
    )
    print(f"\n[7] génération — {rag_generate.MODEL}, effort={effort_affiche}\n")
    answer = rag_generate.generate(question, results, effort=effort)
    rag_generate.print_answer(answer)


def main() -> None:
    # La console Windows tourne en cp1252, ou certains caracteres n'existent pas.
    # Sans ce garde-fou, un print les contenant leve UnicodeEncodeError et fait
    # planter le script — typiquement sur un chemin d'erreur.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    parser = argparse.ArgumentParser(description="Pipeline RAG Markdown -> Weaviate")
    sub = parser.add_subparsers(dest="command", required=True)

    p_index = sub.add_parser("index", help="Indexe un corpus dans Weaviate")
    p_index.add_argument(
        "--corpus",
        type=Path,
        default=CORPUS_DIR,
        help="dossier de fichiers .md a indexer (parcouru recursivement)",
    )
    p_index.add_argument(
        "--collection",
        type=str,
        default=COLLECTION_NAME,
        help="nom de la collection Weaviate. Un nom par corpus permet de les "
             "comparer sans les melanger.",
    )
    p_index.add_argument(
        "--dry-run",
        action="store_true",
        help="Lit et chunke seulement : aucune vectorisation, aucune ecriture. "
             "A lancer sur tout nouveau corpus avant de payer l'embedding.",
    )
    p_index.add_argument(
        "--recreate",
        action="store_true",
        help="Supprime et recree la collection avant d'indexer",
    )

    p_query = sub.add_parser("query", help="Interroge l'index")
    p_query.add_argument("question", type=str)
    p_query.add_argument("-k", type=int, default=TOP_K, help="nombre de chunks")
    p_query.add_argument(
        "--collection",
        type=str,
        default=COLLECTION_NAME,
        help="collection a interroger",
    )

    p_ask = sub.add_parser(
        "ask", help="RAG complet : retrieval puis reponse citee par Mistral"
    )
    p_ask.add_argument("question", type=str)
    p_ask.add_argument("-k", type=int, default=TOP_K, help="nombre de chunks a fournir")
    p_ask.add_argument(
        "--collection", type=str, default=COLLECTION_NAME, help="collection a interroger"
    )
    p_ask.add_argument(
        "--effort",
        type=str,
        default=None,
        choices=["low", "medium", "high", "xhigh", "max"],
        help="profondeur de reflexion du modele (defaut: low)",
    )
    p_ask.add_argument(
        "--dry-run",
        action="store_true",
        help="fait le retrieval et affiche la requete, sans appeler le modele "
             "(ne necessite pas de cle API)",
    )

    args = parser.parse_args()

    if args.command == "index":
        cmd_index(
            corpus_dir=args.corpus,
            collection_name=normalize_collection_name(args.collection),
            recreate=args.recreate,
            dry_run=args.dry_run,
        )
    elif args.command == "query":
        cmd_query(
            args.question,
            k=args.k,
            collection_name=normalize_collection_name(args.collection),
        )
    elif args.command == "ask":
        cmd_ask(
            args.question,
            k=args.k,
            collection_name=normalize_collection_name(args.collection),
            effort=args.effort,
            dry_run=args.dry_run,
        )


if __name__ == "__main__":
    main()
