"""
Lecture robuste de fichiers Markdown et faconnage de leurs metadonnees Weaviate.

read_markdown() / read_corpus() gerent les encodages heterogenes, le BOM, les
CRLF et le frontmatter YAML sans jamais perdre silencieusement du contenu.

to_weaviate_properties() / weaviate_properties() produisent le dict de
proprietes et le schema correspondant. Le schema Weaviate etant TYPE et FIGE a
la creation, chaque metadonnee est soit de premiere classe (propriete declaree,
donc filtrable, mais l'ajouter plus tard impose une reindexation), soit
transportee dans `extra_json` (preservee, non filtrable). Le choix fait ici met
en premiere classe ce sur quoi on filtre en pratique : source, titre, tags,
date, niveaux de titre.

Demo :  python md_metadata.py [dossier_ou_fichier]
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from weaviate.classes.config import DataType, Property, Tokenization

# =============================================================================
# 1. LECTURE ROBUSTE
# =============================================================================

# `latin-1` ne peut JAMAIS echouer (tout octet y est valide) : il doit donc
# rester en dernier, sinon il masquerait les encodages precedents.
_ENCODINGS = ("utf-8-sig", "cp1252", "latin-1")


def read_text_robust(path: Path) -> tuple[str, str]:
    """Lit un fichier texte sans presumer de son encodage.

    Retourne (texte, encodage_retenu). Deux normalisations :
      - le BOM UTF-8 est retire (utf-8-sig), sinon un `# Titre` en tete de
        fichier est precede d'un U+FEFF invisible et n'est plus reconnu ;
      - CRLF -> LF, car les text splitters decoupent sur "\\n\\n" et "\\n" et un
        "\\r" residuel se retrouve colle en fin de chaque metadonnee.
    """
    raw = path.read_bytes()
    for encoding in _ENCODINGS:
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        return text.replace("\r\n", "\n").replace("\r", "\n"), encoding
    raise RuntimeError(f"Aucun encodage n'a fonctionné pour {path}")  # inatteignable


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Separe un eventuel frontmatter YAML du corps du document.

    Retourne (frontmatter, corps) ; frontmatter vide si absent ou invalide.

    Trois cas ou l'on rend le texte INTACT plutot que d'avaler le debut du
    fichier (ce qui serait une perte de donnees silencieuse) : `---` en 1re ligne
    sans delimiteur fermant (c'est une ligne horizontale), bloc YAML invalide, ou
    bloc YAML valide qui ne donne pas un dictionnaire.
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, text

    for i in range(1, len(lines)):
        if lines[i].strip() in ("---", "..."):
            try:
                data = yaml.safe_load("\n".join(lines[1:i]))
            except yaml.YAMLError:
                return {}, text
            if not isinstance(data, dict):
                return {}, text
            return data, "\n".join(lines[i + 1 :]).lstrip("\n")

    return {}, text


_MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_MD_EMPHASIS_RE = re.compile(r"[*_`]")


def clean_header_text(text: str) -> str:
    """Reduit un titre Markdown a son texte lisible.

        "mon-projet [![Awesome](https://cdn.../badge.svg)](https://github.com/x)"
        -> "mon-projet"

    Ce texte sert de fil d'Ariane, que contextualize() prefixe a CHAQUE chunk du
    fichier avant vectorisation : une URL de badge s'y retrouverait dans tous les
    vecteurs du document, les tirant vers la meme region de l'espace.

    Les images sont retirees AVANT les liens : dans `[![alt](a)](b)` l'image est
    imbriquee dans le lien, et l'ordre inverse laisserait des debris.
    """
    cleaned = _MD_IMAGE_RE.sub("", str(text))
    cleaned = _MD_LINK_RE.sub(r"\1", cleaned)
    cleaned = _MD_EMPHASIS_RE.sub("", cleaned)
    return " ".join(cleaned.split())


_FENCE_RE = re.compile(r"^\s{0,3}(```|~~~)")
_H1_RE = re.compile(r"^\s{0,3}#\s+(.+?)\s*$")


def first_h1(body: str) -> str | None:
    """Retourne le premier titre de niveau 1, ou None. Titre de repli.

    Le suivi des blocs de code est necessaire : un README documentant des
    commandes shell contient souvent un `# installation` A L'INTERIEUR d'un bloc
    ```bash, qui deviendrait sinon le titre du document.
    """
    in_fence = False
    for line in body.split("\n"):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = _H1_RE.match(line)
        if match:
            # or None : un titre reduit a un badge devient vide apres nettoyage,
            # on laisse alors la cascade de repli continuer vers le nom de fichier.
            return clean_header_text(match.group(1)) or None
    return None


# =============================================================================
# 2. NORMALISATION VERS LES TYPES ACCEPTES PAR WEAVIATE
# =============================================================================

# `id` EST l'UUID de l'objet chez Weaviate et les horodatages sont geres par le
# serveur : une cle de frontmatter `id:` entrerait en collision avec l'identite.
_RESERVED_NAMES = {
    "id",
    "vector",
    "vectors",
    "_additional",
    "creationtimeunix",
    "lastupdatetimeunix",
}


def sanitize_property_name(name: str) -> str:
    """Transforme une cle quelconque en nom de propriete valide pour Weaviate.

    Contrainte : lettres, chiffres et underscore uniquement, pas de chiffre en
    premiere position.

        "Publication-Date" -> "publication_Date"
        "mon champ"        -> "mon_champ"
        "2024_review"      -> "f_2024_review"
        "id"               -> "fm_id"
    """
    cleaned = re.sub(r"[^0-9A-Za-z_]", "_", str(name).strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned:
        return "unnamed"
    if cleaned[0].isdigit():
        cleaned = "f_" + cleaned
    cleaned = cleaned[0].lower() + cleaned[1:]
    if cleaned.lower() in _RESERVED_NAMES:
        cleaned = "fm_" + cleaned
    return cleaned


def to_rfc3339(value: Any) -> str | None:
    """Convertit une date de frontmatter en RFC 3339, ou None si echec.

    DataType.DATE exige un decalage horaire explicite : `2026-08-11` seul est
    refuse. Et PyYAML rend un `date:` non quote comme un datetime.date, pas une
    chaine. Une date naive est supposee UTC — hypothese assumee, preferable a un
    rejet silencieux.
    """
    if isinstance(value, datetime):
        parsed = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    elif isinstance(value, date):
        parsed = datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
        if not parsed.tzinfo:
            parsed = parsed.replace(tzinfo=timezone.utc)
    else:
        return None
    return parsed.isoformat().replace("+00:00", "Z")


def normalize_tags(value: Any) -> list[str]:
    """Ramene des tags de forme libre a une list[str], pour DataType.TEXT_ARRAY.

    Les trois formes se rencontrent, parfois dans le meme corpus :
        tags: [rag, embeddings]     -> list
        tags: rag, embeddings       -> str a decouper
        tags: rag                   -> str seul
    """
    if value is None:
        return []
    if isinstance(value, str):
        parts = re.split(r"[,;]", value)
    elif isinstance(value, (list, tuple, set)):
        parts = [str(v) for v in value]
    else:
        parts = [str(value)]
    return [p.strip() for p in parts if str(p).strip()]


# =============================================================================
# 3. METADONNEES NIVEAU DOCUMENT
# =============================================================================

# Cles promues en proprietes de premiere classe. Les synonymes existent parce
# qu'un corpus agrege melange les conventions (Obsidian, Hugo, Jekyll...) et
# qu'on veut les faire converger vers un seul nom de propriete.
_FM_TITLE = ("title",)
_FM_TAGS = ("tags", "keywords")
_FM_DATE = ("date", "created", "published")
_FM_AUTHOR = ("author", "authors")

_CONSUMED_FM_KEYS = {k for group in (_FM_TITLE, _FM_TAGS, _FM_DATE, _FM_AUTHOR) for k in group}


def _first_present(frontmatter: dict[str, Any], keys: tuple[str, ...]) -> Any:
    lowered = {str(k).lower(): v for k, v in frontmatter.items()}
    for key in keys:
        if lowered.get(key) not in (None, ""):
            return lowered[key]
    return None


@dataclass
class MarkdownDoc:
    """Un fichier Markdown lu et decompose.

    body     : le corps sans le frontmatter, pret pour le chunking.
    doc_meta : metadonnees niveau document, deja aplaties et typees Weaviate.
    frontmatter / encoding : conserves bruts pour le debogage.
    """

    path: Path
    body: str
    frontmatter: dict[str, Any]
    encoding: str
    doc_meta: dict[str, Any]


def read_markdown(path: Path, corpus_root: Path | None = None) -> MarkdownDoc:
    """Lit un fichier Markdown et isole ses metadonnees niveau document."""
    text, encoding = read_text_robust(path)
    frontmatter, body = split_frontmatter(text)

    root = corpus_root or path.parent
    try:
        source = path.relative_to(root).as_posix()
    except ValueError:
        # Hors de corpus_root : nom seul plutot qu'un chemin absolu, qui rendrait
        # l'index non reproductible d'une machine a l'autre.
        source = path.name

    # Cascade de repli : frontmatter, puis premier H1, puis nom de fichier. Le
    # dernier niveau garantit que `title` n'est jamais vide.
    title = str(_first_present(frontmatter, _FM_TITLE) or "").strip()
    title = title or first_h1(body) or path.stem

    authors = normalize_tags(_first_present(frontmatter, _FM_AUTHOR))

    # Ce qui n'a pas ete promu part dans extra_json : rien n'est perdu, mais rien
    # de tout ca n'est filtrable cote Weaviate.
    extra = {
        sanitize_property_name(k): v
        for k, v in frontmatter.items()
        if str(k).lower() not in _CONSUMED_FM_KEYS
    }

    doc_meta = {
        "source": source,
        "filename": path.name,
        "title": title,
        "author": ", ".join(authors),
        "tags": normalize_tags(_first_present(frontmatter, _FM_TAGS)),
        "doc_date": to_rfc3339(_first_present(frontmatter, _FM_DATE)),
        # default=str absorbe les datetime.date de PyYAML que json.dumps
        # refuserait ; sort_keys rend la sortie deterministe donc comparable.
        "extra_json": (
            json.dumps(extra, ensure_ascii=False, default=str, sort_keys=True) if extra else ""
        ),
    }

    return MarkdownDoc(
        path=path,
        body=body,
        frontmatter=frontmatter,
        encoding=encoding,
        doc_meta=doc_meta,
    )


def read_corpus(corpus_dir: Path) -> list[MarkdownDoc]:
    """Lit recursivement les .md / .markdown d'un dossier, tries par chemin.

    Le tri rend l'ordre d'indexation reproductible, donc les `chunk_index`
    stables entre deux executions — ce dont depend l'idempotence de l'insertion.
    """
    paths = sorted(
        p
        for p in corpus_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in (".md", ".markdown")
    )
    return [read_markdown(p, corpus_root=corpus_dir) for p in paths]


# =============================================================================
# 4. METADONNEES NIVEAU CHUNK -> PROPRIETES WEAVIATE
# =============================================================================

# Doit correspondre aux noms choisis dans MARKDOWN_HEADERS (rag_pipeline.py).
HEADER_KEYS = ("h1", "h2", "h3")


def to_weaviate_properties(
    chunk_text: str,
    doc_meta: dict[str, Any],
    header_meta: dict[str, Any] | None = None,
    chunk_index: int = 0,
    n_chunks: int = 1,
) -> dict[str, Any]:
    """Construit le dict `properties` d'un objet Weaviate.

    `doc_meta` accepte soit MarkdownDoc.doc_meta, soit la `.metadata` d'un
    Document LangChain sorti des splitters : ne pas coupler cette fonction a
    MarkdownDoc la rend utilisable des deux cotes du chunking.

    `header_meta` est la metadata produite par MarkdownHeaderTextSplitter.
    """
    header_meta = header_meta or {}

    breadcrumb = " > ".join(
        str(header_meta[key]).strip() for key in HEADER_KEYS if header_meta.get(key)
    )

    # Les cles explicites sont posees APRES l'expansion de doc_meta : elles
    # gagnent donc si doc_meta les contient deja, ce qui permet de lui passer une
    # metadata de chunk complete sans la filtrer au prealable.
    properties: dict[str, Any] = {
        **doc_meta,
        "headers": breadcrumb,
        "chunk_index": int(chunk_index),
        "n_chunks": int(n_chunks),
        "char_count": len(chunk_text),
        # Empreinte du texte seul : repere les doublons reels (deux fichiers
        # partageant un paragraphe), qu'un UUID derive de la source ne voit pas.
        "content_sha1": hashlib.sha1(chunk_text.encode("utf-8")).hexdigest(),
    }
    for key in HEADER_KEYS:
        if header_meta.get(key):
            properties[key] = str(header_meta[key]).strip()

    # Weaviate accepte qu'un objet n'ait pas toutes les proprietes du schema
    # (elles valent null). Envoyer des chaines vides polluerait les filtres :
    # `author == ""` deviendrait un cas a gerer partout.
    properties = {k: v for k, v in properties.items() if v not in (None, "", [])}

    # Apres le filtrage : `text` est la seule propriete toujours presente.
    properties["text"] = chunk_text
    return properties


def weaviate_properties() -> list[Property]:
    """Le schema correspondant exactement a to_weaviate_properties().

    A passer au parametre `properties=` de client.collections.create(). La
    configuration du VECTEUR (self_provided, metrique de distance) est ailleurs,
    dans ensure_collection().

    index_searchable construit l'index inverse BM25, necessaire a la recherche
    hybride ; valable seulement sur TEXT et TEXT_ARRAY (le passer sur un INT fait
    echouer la creation). Son defaut etant True pour les types texte, il est
    passe explicitement partout ci-dessous, y compris quand la valeur coincide
    avec le defaut : "je n'y ai pas pense" ne doit pas etre indistinguable de
    "j'ai choisi True".

    Tokenization.FIELD fait compter la valeur entiere pour un seul token. C'est
    ce qu'il faut pour un chemin de fichier : avec la tokenisation WORD par
    defaut, "docs/rag/intro.md" serait decoupe en 4 tokens et un filtre par
    egalite exacte echouerait.
    """
    return [
        Property(
            name="text",
            data_type=DataType.TEXT,
            index_searchable=True,
            # Filtrer par egalite exacte sur un chunk entier n'a pas de sens.
            index_filterable=False,
            tokenization=Tokenization.WORD,
        ),
        Property(
            name="source",
            data_type=DataType.TEXT,
            index_searchable=False,
            index_filterable=True,
            tokenization=Tokenization.FIELD,
        ),
        Property(
            name="filename",
            data_type=DataType.TEXT,
            index_searchable=False,
            index_filterable=True,
            tokenization=Tokenization.FIELD,
        ),
        # searchable sur title/author : chercher un document par les mots de son
        # titre est un cas d'usage reel de la recherche hybride.
        Property(
            name="title",
            data_type=DataType.TEXT,
            index_searchable=True,
            index_filterable=True,
        ),
        Property(
            name="author",
            data_type=DataType.TEXT,
            index_searchable=True,
            index_filterable=True,
        ),
        Property(
            name="tags",
            data_type=DataType.TEXT_ARRAY,
            index_searchable=True,
            index_filterable=True,
        ),
        # DataType.DATE et DataType.INT n'acceptent pas index_searchable.
        Property(name="doc_date", data_type=DataType.DATE, index_filterable=True),
        Property(
            name="headers",
            data_type=DataType.TEXT,
            index_searchable=True,
            index_filterable=True,
        ),
        Property(
            name="h1",
            data_type=DataType.TEXT,
            index_searchable=True,
            index_filterable=True,
        ),
        Property(
            name="h2",
            data_type=DataType.TEXT,
            index_searchable=True,
            index_filterable=True,
        ),
        Property(
            name="h3",
            data_type=DataType.TEXT,
            index_searchable=True,
            index_filterable=True,
        ),
        Property(name="chunk_index", data_type=DataType.INT, index_filterable=True),
        Property(name="n_chunks", data_type=DataType.INT, index_filterable=True),
        Property(name="char_count", data_type=DataType.INT, index_filterable=True),
        Property(
            name="content_sha1",
            data_type=DataType.TEXT,
            index_searchable=False,
            index_filterable=True,
            tokenization=Tokenization.FIELD,
        ),
        Property(
            name="extra_json",
            data_type=DataType.TEXT,
            index_searchable=False,
            index_filterable=False,
        ),
    ]


def validate_properties(properties: dict[str, Any]) -> None:
    """Verifie qu'un dict de proprietes ne contient rien d'inconnu au schema.

    Par defaut Weaviate AJOUTE silencieusement au schema toute propriete
    inconnue : une faute de frappe ne leve rien, elle cree une propriete fantome
    et les filtres sur la bonne orthographe renvoient zero resultat sans
    expliquer pourquoi. Un appel sur le premier objet suffit a s'en proteger.
    """
    declared = {p.name for p in weaviate_properties()}
    unknown = set(properties) - declared
    if unknown:
        raise ValueError(
            f"Propriétés absentes du schéma : {sorted(unknown)}. "
            f"Ajoute-les dans weaviate_properties() ou corrige to_weaviate_properties()."
        )


# =============================================================================
# DEMO
# =============================================================================
def _demo(target: Path) -> None:
    docs = read_corpus(target) if target.is_dir() else [read_markdown(target)]
    if not docs:
        print(f"Aucun fichier Markdown trouvé dans {target}")
        return

    print(f"{len(docs)} document(s) lu(s) depuis {target}\n")
    for doc in docs:
        print("=" * 78)
        print(f"{doc.path.name}   [encodage retenu : {doc.encoding}]")
        print("=" * 78)
        print("  frontmatter brut :", doc.frontmatter or "(aucun)")
        print("  métadonnées document :")
        for key, value in doc.doc_meta.items():
            print(f"    {key:14} = {value!r}")

        properties = to_weaviate_properties(
            chunk_text=doc.body[:200],
            doc_meta=doc.doc_meta,
            header_meta={"h1": doc.doc_meta["title"], "h2": "Section d'exemple"},
            chunk_index=0,
            n_chunks=1,
        )
        validate_properties(properties)
        print("  -> properties Weaviate (chunk 0) :")
        for key, value in sorted(properties.items()):
            shown = repr(value)
            print(f"    {key:14} = {shown[:70]}{'...' if len(shown) > 70 else ''}")
        print()

    print(f"Schéma : {len(weaviate_properties())} propriétés déclarées.")
    print("validate_properties() : OK sur tous les documents.")


if __name__ == "__main__":
    default = Path(__file__).parent / "corpus"
    _demo(Path(sys.argv[1]) if len(sys.argv) > 1 else default)
