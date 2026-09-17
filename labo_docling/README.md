# Labo Docling — lire des PDF pour le pipeline RAG

Bac d'essai pour comprendre [Docling](https://github.com/docling-project/docling)
avant de brancher les PDF sur l'étage 1 du pipeline. Chaque script est
autonome, commenté, et se lance seul.

**En une phrase : Docling ne lit pas un PDF, il en reconstruit la structure.**
Là où `pypdf` rend des caractères avec leurs coordonnées, Docling fait passer
des modèles de vision sur les images de pages et répond *ceci est un titre de
niveau 2, ceci un tableau à 3 colonnes, et voici l'ordre de lecture*.

C'est exactement ce dont le pipeline a besoin : le chunking s'appuie sur les
titres (`MarkdownHeaderTextSplitter` puis `contextualize()`), et un PDF n'a pas
de `#`.

## Mise en route

```bash
pip install docling
```

Puis dépose un PDF dans `documents/` (ce dossier n'est pas versionné) :

```bash
python labo_docling/bloc1_conversion.py labo_docling/documents/ton_fichier.pdf
```

Au tout premier lancement, Docling télécharge ~500 Mo de modèles de vision.

## La chaîne, et où sont les paramètres

Convertir n'est pas une opération mais sept. **Tout `PdfPipelineOptions`
s'explique par cette table** : chaque champ règle un étage.

| # | Étage | Ce qu'il fait | Ses paramètres |
|---|---|---|---|
| 1 | Parse | lit le PDF : caractères, positions, image de page | — |
| 2 | Layout | étiquette les zones : titre ? paragraphe ? tableau ? | `layout_options` |
| 3 | OCR | lit le texte présent seulement en image | `do_ocr`, `ocr_options` |
| 4 | Tables | TableFormer reconstruit lignes et colonnes | `do_table_structure`, `table_structure_options` |
| 5 | Enrichissements | code, formules, description d'images | `do_code_enrichment`, `do_formula_enrichment`, `do_picture_description` |
| 6 | Assemblage | construit l'arbre `DoclingDocument` | — |
| 7 | Export | Markdown, HTML, JSON | `images_scale`, `generate_page_images` |

Transversal : `accelerator_options` (threads, device).

Devant un paramètre inconnu, la seule question utile est : **il agit sur quel
étage ?** La réponse est presque toujours dans son nom.

## Ce qui a été mesuré

Cobaye : un cours de 4 pages avec 5 tableaux, sur un Intel i5-1035G1
(4 cœurs physiques, 8 logiques, 15 W).

### Où part le temps (réglages par défaut)

```
     84.2s  100.0%  pipeline_total
     68.1s   81.0%  ocr
     20.2s   24.0%  table_structure
     15.1s   17.9%  layout
      0.2s    0.2%  page_parse
```

Les étages se recouvrent, d'où une somme supérieure à 100 %.

**`page_parse` = 0,2 s.** Lire le PDF est gratuit ; les 99 % restants sont des
modèles de vision. C'est toute la thèse de Docling en une ligne.

`resultat.timings` est **vide par défaut**. Il faut l'activer avant la
conversion, et c'est le seul réglage qui ne passe pas par `PdfPipelineOptions` :

```python
from docling.datamodel.settings import settings
settings.debug.profile_pipeline_timings = True
```

### L'OCR coûte 3x et ne sert à rien sur un PDF non scanné

```
                     médiane   empreinte SHA du Markdown produit
OCR actif (défaut)     90,0s   49714b543b49e7f3
OCR désactivé          30,2s   49714b543b49e7f3
```

Même empreinte : **document identique au caractère près.** `do_ocr=True` sert
uniquement à lire du texte qui n'existe qu'en image (document scanné, photo).
Sur un PDF produit par un traitement de texte, c'est deux tiers du temps pour
rien.

```python
options = PdfPipelineOptions()
options.do_ocr = False
```

### L'étage 4 en deux temps

```
                                temps   orphelines   grilles obtenues
ACCURATE + matching (défaut)    28,8s       47       8x3  5x3  5x3  12x3  8x3
ACCURATE sans matching          22,2s        0       8x3  5x3  5x3  12x3  8x3
FAST + matching                 16,2s       29       8x3 (6x3) 5x3 (13x3) 8x3
```

- **temps 1** — TableFormer regarde l'*image* et prédit une grille. Réglage
  `mode` : `ACCURATE` (défaut) ou `FAST`.
- **temps 2** — on range le *vrai* texte du PDF dans cette grille. Réglage
  `do_cell_matching`.

`FAST` a **inventé une ligne** sur 2 tableaux sur 5. Le gain de 44 % ne vaut
pas une ligne fantôme dans les données : **garder `ACCURATE`**.

Les avertissements `Orphan pdf_cell ... recovered by nearest-row fallback` ne
sont **pas** un bug : c'est le journal du temps 2, qui signale un morceau de
texte sans case et le range dans la ligne la plus proche. Ici le rattrapage
était bon. À surveiller, pas à craindre.

### `do_table_structure=False` n'est jamais bon pour un RAG

Le désactiver ne supprime pas le tableau, il le **disperse** : 243 éléments de
texte au lieu de 33, et 5 cellules au lieu de 107. `SAISCAR | 5 | Lit un
caractère au clavier` devient trois fragments sans lien, et la question
« quelle routine lit un caractère ? » ne retrouve plus `SAISCAR`.

### 4 threads suffisent

`num_threads=4` par défaut colle déjà aux 4 cœurs *physiques*. Passer à 8
n'ajoute que des threads hyperthreadés qui partagent les mêmes unités
vectorielles : mesuré à 1,06x, c'est-à-dire rien.

Corollaire méthodologique : sur une puce 15 W qui throttle, **les écarts
inférieurs à ~20 % ne sont pas interprétables**. Répéter et prendre la médiane.

## `DoclingDocument` contre Markdown

Le Markdown est ce qui *reste* après export. Trois choses qu'il ne peut pas
porter :

1. **L'étiquette.** `page_header`, `caption`, `footnote`, `formula` n'ont
   aucune traduction Markdown. Impossible de filtrer un en-tête courant avant
   de découper.
2. **Les coordonnées.** `page_no` et `bbox` — ce qui permettrait de citer
   « page 2 » au lieu d'un nom de fichier.
3. **Les fusions de tableau.** Un tableau Markdown n'a droit qu'à une ligne
   d'en-tête sans fusion ; l'export aplatit une cellule `col_span=3` en collant
   les lignes avec ` - `.

Et l'aller-retour, qui a une conséquence pratique immédiate :

```python
dictionnaire = doc.export_to_dict()                   # JSON, 7x plus gros
doc = DoclingDocument.model_validate(dictionnaire)    # rechargement exact
```

Le JSON se recharge à l'identique, le Markdown jamais. **Convertir une fois,
stocker le JSON, re-découper autant qu'on veut** — pour faire varier
`CHUNK_SIZE`, c'est la différence entre 10 secondes et 30 minutes.
`bloc3b_inventaire.py` met ce cache en pratique.

## Un piège qui touche l'interface

Une conversion Docling peut mourir en **segmentation fault** — code natif
(torch, OpenCV, `docling-parse`), donc processus tué par l'OS. Aucun
`try/except` ne l'attrape : il n'y a pas d'exception à lever.

Ça s'est produit une fois pendant ces essais. Conséquence pour
`pages/2_Ingestion.py` : un PDF pathologique ne donnerait pas un `st.error`,
**Streamlit tomberait**, sans trace du fichier en cause.

La parade est architecturale : la conversion tourne dans un sous-processus dont
on lit le code de sortie. C'est ce que font `ouvrier.py` et
`bloc2b_verif_ocr.py`.

## Les étages qu'on n'a pas encore réglés

Tout ce qui suit a été vérifié par introspection sur docling 2.127.0.

### Étage 3 — l'OCR en détail

Par défaut `ocr_options` vaut `OcrAutoOptions` (`kind="auto"`) : Docling choisit
le moteur. Sur cette machine il retient **RapidOCR** (modèles PP-OCRv6,
téléchargés au premier usage).

Les moteurs disponibles, tous interchangeables :

| Classe | Remarque |
|---|---|
| `EasyOcrOptions` | historique, lourd |
| `RapidOcrOptions` | retenu par `auto` ici |
| `TesseractOcrOptions` | via la bibliothèque |
| `TesseractCliOcrOptions` | via le binaire `tesseract` |
| `OcrMacOptions` | macOS seulement |
| `NemotronOcrOptions`, `KserveV2OcrOptions` | **distants** — voir `enable_remote_services` |

`OcrMode` a quatre valeurs, et c'est le réglage qui change le coût :

| Mode | Ce qu'il fait |
|---|---|
| `default` | le défaut |
| `layout_regions` | OCR seulement sur les zones repérées par le layout |
| `pdf_aware_layout_regions` | idem, en tenant compte de la couche texte existante |
| `full_page` | OCR sur la page entière, sans exception |

`full_page` est le seul à utiliser sur un **scan**, et le plus cher. C'est
l'ancien `force_full_page_ocr=True`, désormais déprécié.

`ocr_options.lang` vaut `[]` par défaut, c'est-à-dire détection automatique.

### Étage 5 — les enrichissements (tous désactivés par défaut)

| Champ | Ce qu'il ajoute |
|---|---|
| `do_code_enrichment` | reconnaît les blocs de code et leur langage |
| `do_formula_enrichment` | transcrit les formules en LaTeX |
| `do_picture_classification` | classe les images (graphique, photo, schéma…) |
| `do_picture_description` | fait **décrire** les images par un VLM |
| `do_chart_extraction` | extrait les données d'un graphique |

Chacun ajoute un modèle à la chaîne, donc du temps. Sur un corpus technique,
`do_code_enrichment` et `do_formula_enrichment` sont les deux qui changent
vraiment la qualité du texte indexé.

**`enable_remote_services = False` par défaut.** C'est le garde-fou de vie
privée : tant qu'il est à `False`, aucun contenu de document ne sort de la
machine. Les moteurs OCR distants et certains VLM ne s'activent qu'en le
passant à `True` — un choix conscient, jamais un défaut.

### Étage 7 — les images

| Champ | Défaut |
|---|---|
| `generate_page_images` | `False` |
| `generate_picture_images` | `False` |
| `generate_table_images` | `False` |
| `images_scale` | `1.0` |

`images_scale` est un multiplicateur de la résolution de base (72 ppp) : `2.0`
donne 144 ppp. Utile seulement si on veut réafficher les images ; pour un RAG
textuel, tout laisser à `False` évite de gonfler le JSON.

### Ce qu'une vraie ingestion doit régler

C'est la partie que la documentation d'exemple passe sous silence, et c'est
celle qui compte pour `pages/2_Ingestion.py`.

```python
resultats = converter.convert_all(
    chemins,
    raises_on_error=False,   # <- LE reglage a ne pas oublier
    max_num_pages=500,
    max_file_size=50 * 1024 * 1024,
    page_range=(1, 50),
)
```

- **`raises_on_error=True` est le défaut.** Dans un lot, un seul fichier illisible
  fait donc tout échouer. À `False`, le document fautif revient avec
  `status=FAILURE` et ses erreurs, et le lot continue.
- **`convert_all()`** rend un *itérateur* : les résultats arrivent au fil de l'eau,
  ce qui permet d'avancer une barre de progression sans tout garder en mémoire.
- **`max_num_pages`, `max_file_size`, `page_range`** : les garde-fous. Leurs
  défauts sont « illimité » (2^63), donc un PDF de 3000 pages part en conversion
  sans rien demander.
- **`document_timeout`** (dans `PdfPipelineOptions`) : `None` par défaut, donc
  aucune limite de durée par document.

`ConversionStatus` a six valeurs : `pending`, `started`, `failure`, `success`,
`partial_success`, `skipped`. **`partial_success` est la vicieuse** : le
document existe et s'indexe sans broncher, mais une page a échoué. Il faut la
tester explicitement, sinon on indexe un document amputé sans le savoir.

Rappel du piège déjà rencontré : rien de tout cela ne protège d'une
**segmentation fault**. `raises_on_error=False` attrape les exceptions Python,
pas un processus tué par l'OS. D'où le sous-processus.

### Les autres formats

Docling n'est pas un outil à PDF. Il accepte 33 formats en entrée :

```
docx doc rtf pptx ppt html mhtml image pdf asciidoc md csv xlsx xls
odt ods odp xml_uspto xml_jats xml_xbrl xml_doclang dclx mets_gbs
json_docling audio video vtt latex email epub boxnote iwork_pages ebcdic
```

**Tous produisent le même `DoclingDocument`.** C'est le point d'architecture à
retenir : un arbre, beaucoup de lecteurs. Le découpage, l'enrichissement et
l'export écrits une fois valent pour les 33.

Conséquence directe pour le projet : `rag_ingest.EXTENSIONS` pourrait accepter
`.docx` et `.pptx` au même prix que `.pdf`.

Et `md` est dans la liste — donc le corpus HTTP actuel peut passer par Docling,
ce qui rend possible un duel de découpages sur le banc d'essai existant.

## Les scripts

| Script | Ce qu'il montre |
|---|---|
| `bloc1_conversion.py` | la conversion minimale, le `ConversionResult`, l'arbre, l'export |
| `bloc2_parametres.py` | le profilage, et 5 configurations comparées |
| `bloc2b_verif_ocr.py` | l'OCR confirmé sur plusieurs essais, conversions isolées |
| `ouvrier.py` | convertit un PDF dans un processus jetable (appelé par le précédent) |
| `bloc3_document.py` | `DoclingDocument` contre Markdown, élément par élément |
| `bloc3b_inventaire.py` | les 33 éléments un par un, avec cache JSON |
| `bloc4_tableaux.py` | `TableFormerMode` et `do_cell_matching`, mesurés |
| `bloc5_decoupage.py` | les découpeurs de Docling contre un découpage naïf |

## Le découpage (`bloc5_decoupage.py`)

Un élément `text` n'est **pas** un paragraphe. Sur le cobaye, une phrase était
coupée en 4 éléments (un par ligne à l'écran), et des cellules de tableau
s'étaient échappées en éléments isolés (`'92'`, `'virtuel'`). Un chunk par
élément serait donc inexploitable — c'est ce que les découpeurs réparent.

```
                              chunks  médiane   mini   maxi  jetons max  < 80 car.
naïf (1 élément = 1 chunk)        33       41      2    276          74         22
HierarchicalChunker               24      107     29   2244         904         10
HybridChunker (340 jetons)        14      666     78   1176         353          1
HybridChunker (512 jetons)         9     1277     78   1666         525          1
```

La dernière colonne est la mesure qui compte : le nombre de chunks trop petits
pour être retrouvables. **22 → 10 → 1.**

- `HierarchicalChunker` suit l'arbre et recolle les voisins d'une même section,
  mais n'a **aucune limite de taille** (2244 caractères ici) et laisse les
  éléments isolés isolés.
- `HybridChunker` ajoute deux passes : il **découpe** ce qui dépasse le budget
  de jetons, et **fusionne** les voisins trop petits (`merge_peers=True`).
  C'est cette seconde passe qui fait tomber les miettes.

Trois détails qui comptent pour le projet :

**`chunker.contextualize(chunk)`** recolle le fil d'Ariane devant le texte
avant vectorisation — le même mécanisme que `rag_pipeline.contextualize()`. Et
`chunk.meta.doc_items[*].prov[*].page_no` survit au découpage : chaque chunk
sait de quelles **pages** il vient.

**Les tableaux sont sérialisés ligne par ligne**, chaque ligne portant les noms
de ses colonnes :

```
SAISCAR, Les Appels de BIBLIO.X68.N° de la routine valeur pour D0 = 5.
SAISCAR, Action réalisée = Lit un caractère au clavier...
```

Le lien `SAISCAR` ↔ `5` ↔ `lit un caractère` survit donc jusque dans le
vecteur. C'est la réponse directe à ce que le banc d'essai avait établi — *les
embeddings capturent le sujet, pas les relations*.

**Le budget se compte en jetons, pas en caractères.** C'est la différence avec
`CHUNK_SIZE`. Mesure sur ce corpus : **2,93 caractères par jeton en français**,
donc `CHUNK_SIZE = 1000` vaut ~340 jetons. Attention à ne pas se tromper de
raison : BGE-M3 accepte 8192 jetons (`max_seq_length` vérifié), la troncature
n'est donc pas la contrainte — c'est la **dilution sémantique**, comme
`rag_pipeline.py` le documente déjà.

Petite réserve : le maximum observé dépasse un peu le budget (353 pour 340,
525 pour 512), le fil d'Ariane étant ajouté après le contrôle de taille.

## Reste à faire

**Le duel, arbitré par le banc d'essai.** `md` est dans les formats acceptés,
donc le corpus HTTP peut passer par Docling. Même corpus, même embedder, même
reranker, mêmes 96 questions — seul le découpage change. Références à battre :
`@1 = 0,79`, `MRR = 0,868`.

Ensuite : étendre `rag_ingest.EXTENSIONS` à `.pdf` (voire `.docx`, `.pptx`, au
même prix) et brancher la conversion dans `pages/2_Ingestion.py`, dans un
sous-processus, avec `raises_on_error=False` et des garde-fous de taille.
