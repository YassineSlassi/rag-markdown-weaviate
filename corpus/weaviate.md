# Bases vectorielles et Weaviate

Une base vectorielle stocke des vecteurs accompagnés de leurs métadonnées et sait
répondre efficacement à la question : quels sont les k vecteurs stockés les plus
proches de ce vecteur de requête.

## La recherche de voisins approchée

### Pourquoi renoncer à l'exactitude

Comparer une requête à tous les vecteurs de la base donne le résultat exact mais
coûte un temps linéaire en la taille du corpus. À l'échelle du million de
vecteurs, cela devient inacceptable en interactif. Les index ANN, pour
approximate nearest neighbour, échangent une petite perte de rappel contre un
gain de plusieurs ordres de grandeur en latence.

### L'index HNSW

HNSW construit un graphe de navigation hiérarchique. Les couches supérieures sont
clairsemées et servent à se déplacer grossièrement vers la bonne région de
l'espace, les couches inférieures affinent. La recherche descend de couche en
couche en suivant les voisins les plus prometteurs.

Deux paramètres gouvernent le compromis. Le paramètre de construction contrôle la
qualité du graphe et donc le temps d'indexation. Le paramètre de recherche
contrôle la largeur de l'exploration et donc le compromis entre rappel et
latence au moment de la requête.

## Concepts Weaviate

### Collections et propriétés

Une collection est l'équivalent d'une table : elle regroupe des objets de même
forme. Chaque objet possède des propriétés typées, du texte, des nombres, des
dates, et un ou plusieurs vecteurs. Le nom d'une collection commence par une
majuscule par convention.

### Vectorisation intégrée ou vecteurs fournis

Weaviate peut vectoriser lui-même le contenu à l'insertion, en déléguant à un
module de vectorisation. C'est pratique mais cela impose que le modèle soit
accessible depuis le serveur.

L'alternative consiste à apporter ses propres vecteurs. On déclare alors la
collection sans vectorizer, et chaque objet est inséré accompagné explicitement
de son vecteur. C'est le mode à retenir quand on calcule ses embeddings dans son
propre code, par exemple avec un modèle local. Le piège classique est d'oublier
cette déclaration : la collection tente alors de vectoriser toute seule et
échoue, ou pire, produit des vecteurs incohérents avec ceux de la requête.

### Identifiants et idempotence

Chaque objet possède un identifiant universel unique. Si on le laisse générer
aléatoirement, relancer un script d'indexation crée des doublons. En dérivant
l'identifiant de manière déterministe à partir du contenu du chunk et de sa
source, on obtient une insertion idempotente : rejouer l'indexation écrase les
objets existants au lieu de les dupliquer.

### Insertion par lots

L'insertion objet par objet paie un aller-retour réseau à chaque fois. L'insertion
par lots regroupe les objets et traite les erreurs individuellement, si bien
qu'un objet mal formé ne fait pas échouer le lot entier. Il faut penser à
inspecter le rapport d'erreurs après coup, faute de quoi des objets manquants
passent inaperçus.

## Interroger l'index

### Recherche vectorielle

On fournit le vecteur de la requête et un nombre de résultats souhaité. La
réponse contient les propriétés demandées, et, si on la réclame explicitement,
des métadonnées de résultat comme la distance ou le score. Oublier de demander
ces métadonnées est une source fréquente de confusion : on croit alors que le
score est absent alors qu'on ne l'a simplement pas demandé.

### Filtrage par métadonnées

On peut restreindre la recherche à un sous-ensemble d'objets, par exemple une
langue ou un fichier source. Le filtre s'applique conjointement à la recherche
vectorielle, ce qui permet de combiner pertinence sémantique et contraintes
métier.

### Recherche hybride

La recherche hybride fusionne un classement vectoriel et un classement lexical de
type BM25, généralement par fusion de rangs réciproques. Un coefficient règle le
poids relatif des deux. Cela suppose que la propriété textuelle ait été indexée
pour la recherche plein-texte au moment de la création de la collection, décision
qu'on ne peut pas prendre après coup sans réindexer.
