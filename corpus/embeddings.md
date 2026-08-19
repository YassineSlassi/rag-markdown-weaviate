# Les embeddings et le modèle BGE-M3

Un embedding est la projection d'un texte dans un espace vectoriel de dimension
fixe, construite de telle sorte que la proximité géométrique traduise une
proximité de sens. C'est ce qui permet de chercher par intention plutôt que par
mot-clé exact.

## Propriétés d'un espace d'embedding

### Dimension

La dimension est fixée par l'architecture du modèle et ne se choisit pas. Elle
conditionne l'empreinte mémoire de l'index : mille chunks en dimension 1024
stockés en flottants 32 bits occupent environ quatre mégaoctets pour les seuls
vecteurs. Certaines familles récentes acceptent une troncature dite Matryoshka,
qui permet de réduire la dimension au prix d'un peu de précision.

### Normalisation

Normaliser un vecteur, c'est le ramener à une longueur de un. L'intérêt est que
le produit scalaire entre deux vecteurs normalisés est exactement leur similarité
cosinus. Le classement obtenu par produit scalaire et par cosinus devient alors
identique, ce qui simplifie le choix de la métrique de distance côté base
vectorielle.

### Métriques de distance

La similarité cosinus mesure l'angle et ignore la norme. La distance euclidienne
tient compte de la norme. Le produit scalaire favorise les vecteurs de grande
norme. Pour de la recherche sémantique sur des vecteurs normalisés, le cosinus
est le choix par défaut.

Une distance cosinus vaut zéro pour deux textes identiques, un pour deux textes
orthogonaux, et deux pour deux textes diamétralement opposés. On la convertit en
similarité lisible en calculant un moins la distance.

## Le modèle BGE-M3

BGE-M3 est développé par la Beijing Academy of Artificial Intelligence. Son nom
tient aux trois dimensions de sa polyvalence : multilingue, multi-granularité,
multi-fonctionnalité.

### Caractéristiques principales

Il est construit sur une base XLM-RoBERTa, produit des vecteurs denses de
dimension 1024, accepte des séquences jusqu'à 8192 tokens et couvre plus de cent
langues. Son poids sur disque atteint environ deux gigaoctets et deux cents
mégaoctets, ce qui en fait un modèle lourd pour du CPU seul.

### Les trois modes de représentation

Le mode dense produit un vecteur unique par texte, celui qu'on utilise pour la
recherche sémantique classique. Le mode sparse, ou lexical, produit un vecteur
creux de poids par token, comparable à un BM25 appris, efficace sur les termes
rares et les noms propres. Le mode multi-vecteur, de style ColBERT, conserve un
vecteur par token et permet un réordonnancement fin.

Combiner le dense et le sparse donne une recherche hybride souvent nettement
supérieure au dense seul, en particulier sur les acronymes, les références et le
vocabulaire technique.

### Le cas des préfixes d'instruction

Plusieurs modèles de la famille BGE en anglais exigent qu'on préfixe la requête
par une instruction du type « Represent this sentence for searching relevant
passages ». Cette asymétrie entre requête et document est un piège classique :
l'oublier dégrade silencieusement la pertinence.

BGE-M3 se distingue sur ce point : il n'attend aucun préfixe d'instruction, ni
côté requête ni côté document. Le même appel d'encodage convient aux deux.
Ce qui reste vrai en revanche, c'est qu'il faut absolument utiliser le même
modèle et le même prétraitement à l'indexation et à l'interrogation.

## Encoder efficacement

### Le rôle du batch

Un modèle transformeur traite un lot de textes en parallèle bien plus vite qu'un
par un, car l'opération est dominée par des multiplications matricielles. Passer
d'un batch de un à un batch de trente-deux change l'ordre de grandeur du débit.

La taille de batch se règle par la mémoire disponible. Un batch trop grand
provoque un dépassement de mémoire, d'autant plus vite que les textes sont longs,
puisque le coût du padding est dicté par le texte le plus long du lot.

### Ordre et intégrité

L'appel d'encodage doit garantir que le vecteur en position i correspond bien au
texte en position i. C'est une invariance triviale à énoncer et facile à casser
dès qu'on introduit du parallélisme ou du filtrage entre les deux. Une assertion
sur la longueur des listes et sur la dimension des vecteurs coûte une ligne et
évite des heures de diagnostic.
