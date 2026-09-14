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

## Reste à faire

**Le découpage.** Docling embarque ses propres découpeurs conscients du
tokenizer (`HierarchicalChunker`, `HybridChunker`), concurrents directs de la
passe en deux temps de `rag_pipeline.chunk_documents()`. Le banc d'essai
(96 questions graduées) permet de les départager pour de vrai.

Attention au piège vu à l'inventaire : un élément `text` n'est **pas** un
paragraphe. Sur le cobaye, une phrase était coupée en 4 éléments (un par ligne
à l'écran), et des cellules de tableau s'étaient échappées en éléments isolés
(`'92'`, `'virtuel'`). Un chunk par élément produirait des chunks
inexploitables — c'est précisément le travail des découpeurs.

Ensuite : étendre `rag_ingest.EXTENSIONS` à `.pdf` et brancher la conversion
dans `pages/2_Ingestion.py`, dans un sous-processus.
