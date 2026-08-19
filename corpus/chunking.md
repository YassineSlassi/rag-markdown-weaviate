# Le chunking dans un pipeline RAG

Le chunking est l'opération qui consiste à découper un document long en fragments
plus courts, appelés chunks, avant de les vectoriser. C'est l'étape la plus
sous-estimée d'un pipeline RAG : un mauvais découpage ne se rattrape ni par un
meilleur modèle d'embedding, ni par un meilleur LLM en aval.

## Pourquoi découper

### La contrainte du modèle d'embedding

Tout modèle d'embedding a une fenêtre de contexte maximale. Au-delà, le texte est
tronqué silencieusement. La plupart des modèles de la famille BERT s'arrêtent à
512 tokens. BGE-M3 est une exception notable puisqu'il accepte jusqu'à 8192
tokens, ce qui autorise des chunks nettement plus longs que la moyenne.

### La dilution sémantique

Un vecteur unique représente la moyenne sémantique de tout ce qu'on lui donne.
Si un chunk aborde cinq sujets différents, son vecteur se retrouve au barycentre
de ces cinq sujets, donc proche d'aucun d'entre eux. La recherche devient floue.
C'est pour cette raison qu'un chunk devrait idéalement traiter d'une seule idée.

### Le coût du contexte en aval

Les chunks retournés sont injectés dans le prompt du LLM. Des chunks trop gros
saturent la fenêtre de contexte, coûtent cher en tokens, et noient l'information
utile au milieu de remplissage. Le phénomène du « lost in the middle » montre
qu'un LLM exploite mal ce qui se trouve au centre d'un long contexte.

## Les stratégies de découpage

### Découpage à taille fixe

On coupe tous les N caractères ou tous les N tokens. Simple, rapide, prévisible,
mais aveugle : la coupure tombe volontiers au milieu d'une phrase, voire au
milieu d'un mot. À réserver aux corpus sans aucune structure.

### Découpage récursif

On fournit une liste de séparateurs par ordre de préférence, typiquement le
double saut de ligne, puis le simple saut de ligne, puis l'espace, puis le
caractère. L'algorithme tente le premier séparateur ; si le fragment obtenu reste
trop grand, il descend au séparateur suivant. C'est le compromis par défaut
raisonnable pour du texte libre.

### Découpage structurel

Quand le document possède une structure explicite, on s'en sert. Pour du
Markdown, les titres de niveau un, deux et trois délimitent naturellement des
unités sémantiques. L'avantage décisif est qu'on peut conserver le chemin des
titres dans les métadonnées du chunk, ce qui donne au fragment un contexte
d'appartenance qu'il aurait perdu sinon.

L'approche la plus robuste combine les deux : d'abord un découpage structurel par
titres, puis un découpage récursif appliqué aux sections encore trop volumineuses.

## Le paramètre de recouvrement

Le recouvrement, ou overlap, duplique les derniers caractères d'un chunk au début
du suivant. Il sert d'assurance contre une coupure malheureuse au milieu d'une
idée. Un ordre de grandeur courant se situe entre dix et vingt pour cent de la
taille du chunk.

Le recouvrement a un coût : il augmente le nombre de chunks, donc le volume
d'embeddings à calculer, l'espace de stockage, et il introduit une redondance qui
peut faire remonter deux fois presque le même passage dans le Top-K.

## Comment évaluer un découpage

La question n'est pas esthétique mais mesurable. On construit un petit jeu de
questions dont on connaît la réponse et le passage source, puis on mesure si le
chunk contenant la réponse remonte effectivement dans le Top-K. Les métriques
usuelles sont le recall@k et le MRR. Sans ce garde-fou, régler la taille des
chunks revient à deviner.
