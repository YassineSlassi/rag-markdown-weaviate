# Revue des echecs — HttpStress

14 question(s) sur 31 dont le fichier
annote n'arrive pas en 1re position.

Pour chaque document remonte, demande-toi : **repond-il aussi a la
question ?** Si oui, ajoute sa source dans le tableau `pertinents` de
cette question dans `eval/questions_http.json`.

Si AUCUN document remonte n'est acceptable et que le fichier annote
reste le seul bon, c'est un vrai echec du retriever : laisse tel quel.

---

## [s02] Quel code indique que le serveur a bien compris la requete mais refuse de l'autoriser ?

- **annote** : `status/403/index.md`
- **rang obtenu** : 3

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.671 | `status/index.md` | Les codes de statut de réponse HTTP indiquent si une requête HTTP a été exécutée avec succès ou non. Les réponses sont regroupées en cinq classes&nbsp |
| 3 | 0.652 | `status/403/index.md` **(annote)** | Le code de statut de réponse d'erreur client HTTP 403 Forbidden indique que le serveur a compris la requête mais a refusé de la traiter. |
| 5 | 0.642 | `status/406/index.md` | Le code de statut de réponse d'erreur client HTTP 406 Not Acceptable indique que le serveur n'a pas pu produire une réponse correspondant à la liste d |

## [s03] Quel code indique que le serveur ne trouve pas la ressource demandee ?

- **annote** : `status/404/index.md`
- **rang obtenu** : 2

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.714 | `status/index.md` | Les codes de statut de réponse HTTP indiquent si une requête HTTP a été exécutée avec succès ou non. Les réponses sont regroupées en cinq classes&nbsp |
| 2 | 0.682 | `status/404/index.md` **(annote)** | Le code de statut de réponse d'erreur client HTTP 404 Not Found indique que le serveur ne trouve pas la ressource demandée. |
| 3 | 0.654 | `status/507/index.md` | Le code de statut de réponse d'erreur serveur HTTP 507 Insufficient Storage indique qu'une action n'a pas pu être effectuée, car le serveur ne dispose |
| 5 | 0.648 | `status/302/index.md` | Le code de statut de réponse de redirection HTTP 302 Found indique que la ressource demandée a été temporairement déplacée vers l'URL indiquée dans l' |

## [s06] Apres quel code de redirection temporaire l'agent utilisateur est-il autorise a changer la methode de la requete ?

- **annote** : `status/302/index.md`
- **rang obtenu** : 5
- note : Distinction avec 307 : apres un 302 l'agent utilisateur PEUT changer la methode, apres un 307 c'est interdit.

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.658 | `status/index.md` | Les codes de statut de réponse HTTP indiquent si une requête HTTP a été exécutée avec succès ou non. Les réponses sont regroupées en cinq classes&nbsp |
| 2 | 0.657 | `status/301/index.md` | Le code de statut de réponse de redirection 301 Moved Permanently indique que la ressource a définitivement été déplacée à l'URL contenue dans l'en-tê |
| 3 | 0.636 | `status/307/index.md` | Le code de statut de réponse de redirection HTTP 307 Temporary Redirect indique que la ressource demandée a été déplacée temporairement vers l'URL fig |
| 5 | 0.626 | `status/302/index.md` **(annote)** | Le code de statut de réponse de redirection HTTP 302 Found indique que la ressource demandée a été temporairement déplacée vers l'URL indiquée dans l' |

## [s07] Quel code de redirection temporaire interdit de modifier la methode de la requete redirigee ?

- **annote** : `status/307/index.md`
- **rang obtenu** : 2

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.642 | `status/index.md` | Les codes de statut de réponse HTTP indiquent si une requête HTTP a été exécutée avec succès ou non. Les réponses sont regroupées en cinq classes&nbsp |
| 2 | 0.639 | `status/307/index.md` **(annote)** | Le code de statut de réponse de redirection HTTP 307 Temporary Redirect indique que la ressource demandée a été déplacée temporairement vers l'URL fig |
| 3 | 0.625 | `status/301/index.md` | Le code de statut de réponse de redirection 301 Moved Permanently indique que la ressource a définitivement été déplacée à l'URL contenue dans l'en-tê |
| 5 | 0.615 | `status/304/index.md` | Le code de statut de réponse de redirection HTTP 304 Not Modified indique qu'il n'est pas nécessaire de retransmettre les ressources demandées. |

## [h05] Quel en-tete ne declenche la reponse que si l'identifiant de version de la ressource CORRESPOND a celui fourni ?

- **annote** : `headers/if-match/index.md`
- **rang obtenu** : absent du top-5

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.600 | `headers/etag/index.md` | L' HTTP ETag (balise d'entité) est un identifiant pour une version spécifique d'une ressource. |
| 2 | 0.593 | `headers/allow/index.md` | L' HTTP Allow liste l'ensemble des méthodes de requête prises en charge par une ressource. |
| 3 | 0.592 | `headers/rtt/index.md` | L' HTTP RTT est un indicateur du client sur le réseau qui fournit le temps de trajet aller-retour approximatif au niveau de l'application, en millisec |
| 4 | 0.587 | `headers/attribution-reporting-eligible/index.md` | HTTP Attribution-Reporting-Eligible indique que la réponse correspondante est éligible à l'enregistrement d'une source ou d'un déclencheur d'attributi |
| 5 | 0.582 | `headers/cross-origin-embedder-policy-report-only/index.md` | HTTP Cross-Origin-Embedder-Policy-Report-Only (COEP) définit la politique rapport seulement du document actuel pour le chargement et l'intégration de  |

## [h06] Quel en-tete ne declenche la reponse que si AUCUN des identifiants de version fournis ne correspond a celui de la ressource ?

- **annote** : `headers/if-none-match/index.md`
- **rang obtenu** : absent du top-5

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.588 | `headers/cross-origin-embedder-policy/index.md` | HTTP Cross-Origin-Embedder-Policy (COEP) configure la politique du document courant pour le chargement et l'intégration de ressources d'origine croisé |
| 2 | 0.581 | `headers/index.md` | Les en-têtes HTTP permettent au client et au serveur de transmettre des informations supplémentaires avec un message dans une requête ou une réponse. |
| 3 | 0.580 | `headers/rtt/index.md` | L' HTTP RTT est un indicateur du client sur le réseau qui fournit le temps de trajet aller-retour approximatif au niveau de l'application, en millisec |
| 4 | 0.571 | `headers/cross-origin-embedder-policy-report-only/index.md` | HTTP Cross-Origin-Embedder-Policy-Report-Only (COEP) définit la politique rapport seulement du document actuel pour le chargement et l'intégration de  |
| 5 | 0.565 | `headers/cross-origin-resource-policy/index.md` | L' HTTP Cross-Origin-Resource-Policy (CORP) indique que le navigateur doit bloquer les requêtes inter-origines ou inter-sites `no-cors` vers la ressou |

## [h07] Quel en-tete ne renvoie la ressource que si elle a ete modifiee apres une date donnee ?

- **annote** : `headers/if-modified-since/index.md`
- **rang obtenu** : 2

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.674 | `headers/if-unmodified-since/index.md` | L' HTTP If-Unmodified-Since rend la requête pour la ressource conditionnelle. |
| 2 | 0.664 | `headers/if-modified-since/index.md` **(annote)** | L' HTTP If-Modified-Since rend la requête conditionnelle. |
| 3 | 0.627 | `headers/index.md` | Les en-têtes HTTP permettent au client et au serveur de transmettre des informations supplémentaires avec un message dans une requête ou une réponse. |
| 4 | 0.623 | `headers/last-modified/index.md` | L' HTTP Last-Modified contient la date et l'heure auxquelles le serveur d'origine estime que la ressource a été modifiée pour la dernière fois. |

## [h12] Quel en-tete de reponse indique quelle methode d'authentification employer pour acceder a une ressource ?

- **annote** : `headers/www-authenticate/index.md`
- **rang obtenu** : 2

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.665 | `headers/authorization/index.md` | L' HTTP Authorization permet de fournir des informations d'identification afin d'authentifier un agent utilisateur auprès d'un serveur, donnant ainsi  |
| 2 | 0.658 | `headers/www-authenticate/index.md` **(annote)** | L'entête HTTP de réponse WWW-Authenticate définit la méthode d'authentification qui doit être utilisé pour obtenir l'accès à une ressource. |
| 3 | 0.652 | `headers/access-control-allow-methods/index.md` | L' HTTP Access-Control-Allow-Methods indique une ou plusieurs méthodes de requête HTTP autorisées lors de l'accès à une ressource en réponse à une . |
| 4 | 0.636 | `headers/proxy-authenticate/index.md` | HTTP Proxy-Authenticate définit la méthode d'authentification (ou ) à utiliser pour accéder à une ressource derrière un . |
| 5 | 0.631 | `headers/allow/index.md` | L' HTTP Allow liste l'ensemble des méthodes de requête prises en charge par une ressource. |

## [h13] Quel en-tete decide si le contenu s'affiche dans le navigateur ou declenche un telechargement ?

- **annote** : `headers/content-disposition/index.md`
- **rang obtenu** : 2

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.711 | `headers/index.md` | Les en-têtes HTTP permettent au client et au serveur de transmettre des informations supplémentaires avec un message dans une requête ou une réponse. |
| 2 | 0.677 | `headers/content-disposition/index.md` **(annote)** | L'en-tête HTTP Content-Disposition indique si le contenu doit être affiché en ligne (inline en anglais) dans le navigateur en tant que page Web ou par |
| 3 | 0.630 | `headers/accept/index.md` | L' et HTTP Accept indique quels types de contenu, exprimés sous forme de types MIME, l'émetteur·rice est capable de comprendre. |
| 4 | 0.630 | `headers/range/index.md` | L' HTTP Range indique la partie d'une ressource que le serveur doit retourner. |
| 5 | 0.627 | `headers/x-frame-options/index.md` | L'en-tête de réponse HTTP X-Frame-Options peut être utilisé afin d'indiquer si un navigateur devrait être autorisé à afficher une page au sein d'un él |

## [x02] Quel en-tete CORS enumere les methodes HTTP autorisees pour acceder a une ressource ?

- **annote** : `headers/access-control-allow-methods/index.md`
- **rang obtenu** : 2

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.691 | `headers/access-control-allow-origin/index.md` | L' HTTP Access-Control-Allow-Origin indique si la réponse peut être partagée avec le code demandeur provenant de l' donnée. |
| 2 | 0.678 | `headers/access-control-allow-methods/index.md` **(annote)** | L' HTTP Access-Control-Allow-Methods indique une ou plusieurs méthodes de requête HTTP autorisées lors de l'accès à une ressource en réponse à une . |
| 4 | 0.662 | `headers/cross-origin-resource-policy/index.md` | L' HTTP Cross-Origin-Resource-Policy (CORP) indique que le navigateur doit bloquer les requêtes inter-origines ou inter-sites `no-cors` vers la ressou |
| 5 | 0.661 | `headers/index.md` | Les en-têtes HTTP permettent au client et au serveur de transmettre des informations supplémentaires avec un message dans une requête ou une réponse. |

## [x03] Quel en-tete CORS enumere les en-tetes que la requete reelle sera autorisee a utiliser ?

- **annote** : `headers/access-control-allow-headers/index.md`
- **rang obtenu** : 3

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.571 | `headers/range/index.md` | L' HTTP Range indique la partie d'une ressource que le serveur doit retourner. |
| 2 | 0.568 | `headers/activate-storage-access/index.md` | HTTP Activate-Storage-Access permet à un serveur d'activer une autorisation accordée pour accéder à ses cookies non partitionnés lors d'une requête in |
| 3 | 0.563 | `headers/access-control-allow-headers/index.md` **(annote)** | L' HTTP Access-Control-Allow-Headers est utilisé en réponse à une pour indiquer les en-têtes HTTP qui peuvent être utilisés lors de la requête réelle. |
| 5 | 0.558 | `headers/accept-language/index.md` | L' HTTP Accept-Language indique quelles sont les langues que le client est capable de comprendre, et quelle variante locale est préférée. |

## [x05] Quel en-tete CORS fixe la duree de validite du resultat d'une requete preliminaire ?

- **annote** : `headers/access-control-max-age/index.md`
- **rang obtenu** : absent du top-5

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.576 | `headers/index.md` | Les en-têtes HTTP permettent au client et au serveur de transmettre des informations supplémentaires avec un message dans une requête ou une réponse. |
| 2 | 0.575 | `headers/access-control-allow-headers/index.md` | L' HTTP Access-Control-Allow-Headers est utilisé en réponse à une pour indiquer les en-têtes HTTP qui peuvent être utilisés lors de la requête réelle. |
| 5 | 0.537 | `headers/access-control-request-method/index.md` | L' HTTP Access-Control-Request-Method est utilisé par les navigateurs lors de l'émission d'une pour indiquer au serveur quelle méthode HTTP sera utili |

## [p02] Quelle directive CSP definit les sources valides pour le code JavaScript ?

- **annote** : `headers/content-security-policy/script-src/index.md`
- **rang obtenu** : 3

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.775 | `headers/content-security-policy/script-src-attr/index.md` | La directive HTTP (CSP) script-src-attr définit les sources valides pour les gestionnaires d'évènements JavaScript embarqués. |
| 2 | 0.770 | `headers/content-security-policy/script-src-elem/index.md` | La directive HTTP (CSP) script-src-elem indique les sources valides pour des éléments HTML . |
| 3 | 0.748 | `headers/content-security-policy/script-src/index.md` **(annote)** | La directive HTTP (CSP) script-src définit les sources valides pour du code JavaScript. Cela inclut les URL chargées directement par les éléments HTML |
| 4 | 0.745 | `headers/content-security-policy/style-src-attr/index.md` | La directive HTTP (CSP) style-src-attr définit les sources valides pour des feuilles de styles appliquées à des éléments individuels du DOM par l'attr |
| 5 | 0.712 | `headers/content-security-policy/style-src-elem/index.md` | La directive HTTP (CSP) style-src-elem définit les sources valides pour les feuilles de styles embarquées avec les éléments HTML et avec les éléments  |

## [p04] Quelle directive CSP definit qui a le droit d'integrer la page dans un cadre ?

- **annote** : `headers/content-security-policy/frame-ancestors/index.md`
- **rang obtenu** : 2

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.636 | `headers/content-security-policy/frame-src/index.md` | La directive HTTP (CSP) frame-src définit les sources valides pour les contextes de navigation imbriqués chargés avec des éléments HTML tels que et . |
| 2 | 0.633 | `headers/content-security-policy/frame-ancestors/index.md` **(annote)** | La directive HTTP (CSP) frame-ancestors définit les parents valides pouvant intégrer une page en utilisant , , ou . |
| 3 | 0.632 | `headers/content-security-policy/index.md` | HTTP Content-Security-Policy permet aux administrateur·ice·s d'un site web de contrôler les ressources que l'agent utilisateur est autorisé à charger  |
| 4 | 0.631 | `headers/content-security-policy/fenced-frame-src/index.md` | La directive HTTP (CSP) fenced-frame-src définit les sources valides pour les contextes de navigation imbriqués chargés dans les éléments . |
| 5 | 0.617 | `headers/content-security-policy/sandbox/index.md` | La directive HTTP (CSP) sandbox active un bac à sable (sandbox en anglais) pour les ressources demandées, similaire à l'attribut `sandbox` des élément |

