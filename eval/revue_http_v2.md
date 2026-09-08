# Revue des echecs — HttpStress

38 question(s) sur 96 dont le fichier
annote n'arrive pas en 1re position.

Pour chaque document remonte, demande-toi : **repond-il aussi a la
question ?** Si oui, ajoute sa source dans le tableau `pertinents` de
cette question dans `eval\questions_http_v2.json`.

Si AUCUN document remonte n'est acceptable et que le fichier annote
reste le seul bon, c'est un vrai echec du retriever : laisse tel quel.

---

## [st05] Quel code indique que la ressource est absente, sans preciser si c'est temporaire ou definitif ?

- **annote** : `status/404/index.md`
- **rang obtenu** : 2

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.603 | `status/410/index.md` | Le code de statut de réponse d'erreur client HTTP 410 Gone indique que la ressource cible n'est plus disponible sur le serveur d'origine et que cette  |
| 2 | 0.557 | `status/404/index.md` **(annote)** | Le code de statut de réponse d'erreur client HTTP 404 Not Found indique que le serveur ne trouve pas la ressource demandée. |
| 3 | 0.557 | `headers/attribution-reporting-register-source/index.md` | HTTP Attribution-Reporting-Register-Source enregistre une fonctionnalité de page comme source d'attribution. |
| 4 | 0.544 | `status/index.md` | Les codes de statut de réponse HTTP indiquent si une requête HTTP a été exécutée avec succès ou non. Les réponses sont regroupées en cinq classes&nbsp |

## [st09] Quelle redirection temporaire interdit a l'agent utilisateur de changer la methode de la requete ?

- **annote** : `status/307/index.md`
- **rang obtenu** : 4

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.617 | `status/301/index.md` | Le code de statut de réponse de redirection 301 Moved Permanently indique que la ressource a définitivement été déplacée à l'URL contenue dans l'en-tê |
| 2 | 0.592 | `status/302/index.md` | Le code de statut de réponse de redirection HTTP 302 Found indique que la ressource demandée a été temporairement déplacée vers l'URL indiquée dans l' |
| 3 | 0.588 | `status/index.md` | Les codes de statut de réponse HTTP indiquent si une requête HTTP a été exécutée avec succès ou non. Les réponses sont regroupées en cinq classes&nbsp |
| 4 | 0.574 | `status/307/index.md` **(annote)** | Le code de statut de réponse de redirection HTTP 307 Temporary Redirect indique que la ressource demandée a été déplacée temporairement vers l'URL fig |

## [st10] Quel code demande au navigateur d'aller chercher une confirmation ailleurs, souvent apres l'envoi d'un formulaire ?

- **annote** : `status/303/index.md`
- **rang obtenu** : 4

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.626 | `status/index.md` | Les codes de statut de réponse HTTP indiquent si une requête HTTP a été exécutée avec succès ou non. Les réponses sont regroupées en cinq classes&nbsp |
| 3 | 0.607 | `status/302/index.md` | Le code de statut de réponse de redirection HTTP 302 Found indique que la ressource demandée a été temporairement déplacée vers l'URL indiquée dans l' |
| 4 | 0.604 | `status/303/index.md` **(annote)** | Le code de statut de réponse de redirection HTTP 303 See Other indique que le navigateur doit se rediriger vers l'URL indiquée dans l'en-tête au lieu  |
| 5 | 0.596 | `status/301/index.md` | Le code de statut de réponse de redirection 301 Moved Permanently indique que la ressource a définitivement été déplacée à l'URL contenue dans l'en-tê |

## [st12] Quel code repond a une requete conditionnelle en confirmant que la copie en cache est toujours valable ?

- **annote** : `status/304/index.md`
- **rang obtenu** : 4

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.696 | `headers/cache-control/index.md` | et HTTP Cache-Control contient des directives (c'est-à-dire des instructions), dans les requêtes et dans les réponses, pour contrôler la mise en cache |
| 2 | 0.635 | `headers/index.md` | Les en-têtes HTTP permettent au client et au serveur de transmettre des informations supplémentaires avec un message dans une requête ou une réponse. |
| 4 | 0.613 | `status/304/index.md` **(annote)** | Le code de statut de réponse de redirection HTTP 304 Not Modified indique qu'il n'est pas nécessaire de retransmettre les ressources demandées. |

## [st14] Quel code indique qu'une passerelle n'a recu aucune reponse a temps du serveur en amont ?

- **annote** : `status/504/index.md`
- **rang obtenu** : 2

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.677 | `status/502/index.md` | Le code de statut de réponse d'erreur serveur HTTP 502 Bad Gateway indique qu'un serveur agissait en tant que passerelle ou et qu'il a reçu une répons |
| 2 | 0.671 | `status/504/index.md` **(annote)** | Le code de statut de réponse d'erreur serveur HTTP 504 Gateway Timeout indique que le serveur, agissant en tant que passerelle ou , n'a pas reçu de ré |
| 3 | 0.656 | `status/index.md` | Les codes de statut de réponse HTTP indiquent si une requête HTTP a été exécutée avec succès ou non. Les réponses sont regroupées en cinq classes&nbsp |

## [st16] Quel code indique que la condition posee par la requete n'est pas remplie, pour une methode autre que la lecture ?

- **annote** : `status/412/index.md`
- **rang obtenu** : 2

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.588 | `status/304/index.md` | Le code de statut de réponse de redirection HTTP 304 Not Modified indique qu'il n'est pas nécessaire de retransmettre les ressources demandées. |
| 2 | 0.572 | `status/412/index.md` **(annote)** | Le code de statut de réponse d'erreur client HTTP 412 Precondition Failed indique que l'accès à la ressource cible a été refusé. |
| 3 | 0.570 | `headers/if-none-match/index.md` | L' HTTP If-None-Match rend la requête conditionnelle. |
| 4 | 0.565 | `status/index.md` | Les codes de statut de réponse HTTP indiquent si une requête HTTP a été exécutée avec succès ou non. Les réponses sont regroupées en cinq classes&nbsp |
| 5 | 0.560 | `status/401/index.md` | Le code de statut de réponse d'erreur client HTTP 401 Unauthorized indique qu'une requête n'a pas abouti, car elle ne comporte pas d'identifiants d'au |

## [st17] Quel code exige que le client rende sa requete conditionnelle avant de la rejouer ?

- **annote** : `status/428/index.md`
- **rang obtenu** : absent du top-5

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.597 | `status/index.md` | Les codes de statut de réponse HTTP indiquent si une requête HTTP a été exécutée avec succès ou non. Les réponses sont regroupées en cinq classes&nbsp |
| 2 | 0.560 | `status/304/index.md` | Le code de statut de réponse de redirection HTTP 304 Not Modified indique qu'il n'est pas nécessaire de retransmettre les ressources demandées. |
| 3 | 0.556 | `headers/index.md` | Les en-têtes HTTP permettent au client et au serveur de transmettre des informations supplémentaires avec un message dans une requête ou une réponse. |
| 4 | 0.551 | `headers/cache-control/index.md` | et HTTP Cache-Control contient des directives (c'est-à-dire des instructions), dans les requêtes et dans les réponses, pour contrôler la mise en cache |
| 5 | 0.547 | `status/205/index.md` | Le code de statut de réponse de succès HTTP 205 Reset Content indique que la requête a été traitée avec succès et que le client doit réinitialiser l'a |

## [st23] Quel code indique que le serveur ne prend pas du tout en charge la fonctionnalite necessaire a la requete ?

- **annote** : `status/501/index.md`
- **rang obtenu** : 4

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.670 | `status/503/index.md` | Le code de statut de réponse d'erreur serveur HTTP 503 Service Unavailable indique que le serveur n'est pas prêt à traiter la requête. |
| 2 | 0.661 | `status/408/index.md` | Le code de statut de réponse d'erreur client HTTP 408 Request Timeout indique que le serveur souhaite fermer cette connexion inutilisée. |
| 3 | 0.659 | `status/507/index.md` | Le code de statut de réponse d'erreur serveur HTTP 507 Insufficient Storage indique qu'une action n'a pas pu être effectuée, car le serveur ne dispose |
| 4 | 0.652 | `status/501/index.md` **(annote)** | Le code de statut de réponse d'erreur serveur HTTP 501 Not Implemented signifie que le serveur ne prend pas en charge la fonctionnalité requise pour s |
| 5 | 0.651 | `status/index.md` | Les codes de statut de réponse HTTP indiquent si une requête HTTP a été exécutée avec succès ou non. Les réponses sont regroupées en cinq classes&nbsp |

## [st27] Quel code repond a une demande portant sur une partie seulement de la ressource ?

- **annote** : `status/206/index.md`
- **rang obtenu** : 2

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.599 | `headers/access-control-allow-origin/index.md` | L' HTTP Access-Control-Allow-Origin indique si la réponse peut être partagée avec le code demandeur provenant de l' donnée. |
| 2 | 0.593 | `status/206/index.md` **(annote)** | Le code de statut de réponse de succès HTTP 206 Partial Content est envoyé en réponse à une requête de plage. |
| 3 | 0.578 | `headers/range/index.md` | L' HTTP Range indique la partie d'une ressource que le serveur doit retourner. |
| 5 | 0.571 | `headers/prefer/index.md` | L'en-tête HTTP Prefer permet aux clients d'indiquer des préférences pour des comportements spécifiques du serveur lors du traitement d'une requête. |

## [st28] Quel code refuse la requete parce que le serveur ne veut pas risquer de traiter des donnees rejouables ?

- **annote** : `status/425/index.md`
- **rang obtenu** : absent du top-5

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.542 | `status/406/index.md` | Le code de statut de réponse d'erreur client HTTP 406 Not Acceptable indique que le serveur n'a pas pu produire une réponse correspondant à la liste d |
| 2 | 0.539 | `status/index.md` | Les codes de statut de réponse HTTP indiquent si une requête HTTP a été exécutée avec succès ou non. Les réponses sont regroupées en cinq classes&nbsp |
| 4 | 0.528 | `status/503/index.md` | Le code de statut de réponse d'erreur serveur HTTP 503 Service Unavailable indique que le serveur n'est pas prêt à traiter la requête. |
| 5 | 0.524 | `status/431/index.md` | Le code de statut de réponse d'erreur client HTTP 431 Request Header Fields Too Large indique que le serveur refuse de traiter la requête, car les en- |

## [au01] Quel en-tete de requete transporte les identifiants du client vers le serveur d'origine ?

- **annote** : `headers/authorization/index.md`
- **rang obtenu** : absent du top-5

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.652 | `headers/rtt/index.md` | L' HTTP RTT est un indicateur du client sur le réseau qui fournit le temps de trajet aller-retour approximatif au niveau de l'application, en millisec |
| 2 | 0.622 | `headers/device-memory/index.md` | L'en-tête Device-Memory a été standardisé sous le nom et ce nouveau nom est désormais privilégié. |
| 3 | 0.618 | `headers/index.md` | Les en-têtes HTTP permettent au client et au serveur de transmettre des informations supplémentaires avec un message dans une requête ou une réponse. |
| 5 | 0.616 | `headers/sec-ch-device-memory/index.md` | HTTP Sec-CH-Device-Memory est utilisé dans les indices client pour les appareils pour indiquer la quantité approximative de RAM disponible sur l'appar |

## [au02] Quel en-tete de requete transporte les identifiants destines a l'intermediaire, et non au serveur final ?

- **annote** : `headers/proxy-authorization/index.md`
- **rang obtenu** : absent du top-5

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.626 | `headers/index.md` | Les en-têtes HTTP permettent au client et au serveur de transmettre des informations supplémentaires avec un message dans une requête ou une réponse. |
| 3 | 0.621 | `headers/rtt/index.md` | L' HTTP RTT est un indicateur du client sur le réseau qui fournit le temps de trajet aller-retour approximatif au niveau de l'application, en millisec |
| 4 | 0.613 | `headers/prefer/index.md` | L'en-tête HTTP Prefer permet aux clients d'indiquer des préférences pour des comportements spécifiques du serveur lors du traitement d'une requête. |
| 5 | 0.603 | `headers/device-memory/index.md` | L'en-tête Device-Memory a été standardisé sous le nom et ce nouveau nom est désormais privilégié. |

## [au03] Quel en-tete de reponse annonce la methode d'authentification a employer pour acceder a une ressource protegee ?

- **annote** : `headers/www-authenticate/index.md`
- **rang obtenu** : 2

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.647 | `headers/authorization/index.md` | L' HTTP Authorization permet de fournir des informations d'identification afin d'authentifier un agent utilisateur auprès d'un serveur, donnant ainsi  |
| 2 | 0.625 | `headers/www-authenticate/index.md` **(annote)** | L'entête HTTP de réponse WWW-Authenticate définit la méthode d'authentification qui doit être utilisé pour obtenir l'accès à une ressource. |
| 3 | 0.615 | `headers/proxy-authenticate/index.md` | HTTP Proxy-Authenticate définit la méthode d'authentification (ou ) à utiliser pour accéder à une ressource derrière un . |
| 4 | 0.599 | `headers/index.md` | Les en-têtes HTTP permettent au client et au serveur de transmettre des informations supplémentaires avec un message dans une requête ou une réponse. |
| 5 | 0.591 | `headers/access-control-allow-methods/index.md` | L' HTTP Access-Control-Allow-Methods indique une ou plusieurs méthodes de requête HTTP autorisées lors de l'accès à une ressource en réponse à une . |

## [au04] Quel en-tete de reponse annonce la methode d'authentification exigee par l'intermediaire place devant la ressource ?

- **annote** : `headers/proxy-authenticate/index.md`
- **rang obtenu** : 4

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.625 | `headers/authorization/index.md` | L' HTTP Authorization permet de fournir des informations d'identification afin d'authentifier un agent utilisateur auprès d'un serveur, donnant ainsi  |
| 2 | 0.597 | `headers/index.md` | Les en-têtes HTTP permettent au client et au serveur de transmettre des informations supplémentaires avec un message dans une requête ou une réponse. |
| 3 | 0.596 | `headers/www-authenticate/index.md` | L'entête HTTP de réponse WWW-Authenticate définit la méthode d'authentification qui doit être utilisé pour obtenir l'accès à une ressource. |
| 4 | 0.587 | `headers/proxy-authenticate/index.md` **(annote)** | HTTP Proxy-Authenticate définit la méthode d'authentification (ou ) à utiliser pour accéder à une ressource derrière un . |
| 5 | 0.585 | `headers/access-control-allow-credentials/index.md` | L' HTTP Access-Control-Allow-Credentials indique aux navigateurs si le serveur autorise l'inclusion de justificatifs dans les requêtes HTTP inter-orig |

## [co01] Quel en-tete n'autorise le traitement que si la ressource correspond a l'une des versions listees par le client ?

- **annote** : `headers/if-match/index.md`
- **rang obtenu** : absent du top-5

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.615 | `headers/allow/index.md` | L' HTTP Allow liste l'ensemble des méthodes de requête prises en charge par une ressource. |
| 2 | 0.593 | `headers/permissions-policy-report-only/index.md` | HTTP Permissions-Policy-Report-Only fournit un mécanisme permettant aux administrateur·ice·s de sites Web de signaler les violations d'une sans les ap |
| 4 | 0.589 | `headers/cross-origin-embedder-policy-report-only/index.md` | HTTP Cross-Origin-Embedder-Policy-Report-Only (COEP) définit la politique rapport seulement du document actuel pour le chargement et l'intégration de  |
| 5 | 0.586 | `headers/accept-language/index.md` | L' HTTP Accept-Language indique quelles sont les langues que le client est capable de comprendre, et quelle variante locale est préférée. |

## [co02] Quel en-tete n'autorise l'envoi de la ressource que si le serveur ne possede aucune des versions listees par le client ?

- **annote** : `headers/if-none-match/index.md`
- **rang obtenu** : absent du top-5

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.600 | `headers/allow/index.md` | L' HTTP Allow liste l'ensemble des méthodes de requête prises en charge par une ressource. |
| 2 | 0.588 | `status/index.md` | Les codes de statut de réponse HTTP indiquent si une requête HTTP a été exécutée avec succès ou non. Les réponses sont regroupées en cinq classes&nbsp |
| 4 | 0.579 | `headers/accept-language/index.md` | L' HTTP Accept-Language indique quelles sont les langues que le client est capable de comprendre, et quelle variante locale est préférée. |
| 5 | 0.573 | `headers/index.md` | Les en-têtes HTTP permettent au client et au serveur de transmettre des informations supplémentaires avec un message dans une requête ou une réponse. |

## [co03] Quel en-tete ne renvoie la ressource que si elle a change depuis la date indiquee ?

- **annote** : `headers/if-modified-since/index.md`
- **rang obtenu** : 2

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.691 | `headers/if-unmodified-since/index.md` | L' HTTP If-Unmodified-Since rend la requête pour la ressource conditionnelle. |
| 2 | 0.677 | `headers/if-modified-since/index.md` **(annote)** | L' HTTP If-Modified-Since rend la requête conditionnelle. |
| 3 | 0.631 | `headers/index.md` | Les en-têtes HTTP permettent au client et au serveur de transmettre des informations supplémentaires avec un message dans une requête ou une réponse. |
| 5 | 0.615 | `headers/last-modified/index.md` | L' HTTP Last-Modified contient la date et l'heure auxquelles le serveur d'origine estime que la ressource a été modifiée pour la dernière fois. |

## [co05] Quel en-tete conditionne une demande portant sur une portion de ressource, et renvoie sinon la ressource entiere ?

- **annote** : `headers/if-range/index.md`
- **rang obtenu** : 4

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.642 | `headers/if-unmodified-since/index.md` | L' HTTP If-Unmodified-Since rend la requête pour la ressource conditionnelle. |
| 2 | 0.639 | `headers/index.md` | Les en-têtes HTTP permettent au client et au serveur de transmettre des informations supplémentaires avec un message dans une requête ou une réponse. |
| 3 | 0.625 | `headers/if-none-match/index.md` | L' HTTP If-None-Match rend la requête conditionnelle. |
| 4 | 0.620 | `headers/if-range/index.md` **(annote)** | HTTP If-Range rend une requête de plage conditionnelle. |
| 5 | 0.615 | `headers/if-modified-since/index.md` | L' HTTP If-Modified-Since rend la requête conditionnelle. |

## [co09] Quel en-tete de reponse situe la portion renvoyee par rapport a la ressource complete ?

- **annote** : `headers/content-range/index.md`
- **rang obtenu** : absent du top-5

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.610 | `headers/referer/index.md` | L' HTTP Referer contient l'adresse absolue ou partielle à partir de laquelle une ressource a été demandée. |
| 2 | 0.574 | `headers/range/index.md` | L' HTTP Range indique la partie d'une ressource que le serveur doit retourner. |
| 3 | 0.557 | `headers/cross-origin-resource-policy/index.md` | L' HTTP Cross-Origin-Resource-Policy (CORP) indique que le navigateur doit bloquer les requêtes inter-origines ou inter-sites `no-cors` vers la ressou |
| 4 | 0.551 | `headers/index.md` | Les en-têtes HTTP permettent au client et au serveur de transmettre des informations supplémentaires avec un message dans une requête ou une réponse. |
| 5 | 0.548 | `headers/rtt/index.md` | L' HTTP RTT est un indicateur du client sur le réseau qui fournit le temps de trajet aller-retour approximatif au niveau de l'application, en millisec |

## [co10] Quel en-tete permet au serveur d'annoncer qu'il accepte les demandes portant sur une partie seulement d'une ressource ?

- **annote** : `headers/accept-ranges/index.md`
- **rang obtenu** : 3

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.665 | `headers/allow/index.md` | L' HTTP Allow liste l'ensemble des méthodes de requête prises en charge par une ressource. |
| 2 | 0.663 | `headers/accept/index.md` | L' et HTTP Accept indique quels types de contenu, exprimés sous forme de types MIME, l'émetteur·rice est capable de comprendre. |
| 3 | 0.641 | `headers/accept-ranges/index.md` **(annote)** | L' HTTP Accept-Ranges est utilisé par le serveur pour indiquer sa prise en charge des requêtes de plage, permettant aux clients de demander une partie |
| 4 | 0.640 | `headers/accept-language/index.md` | L' HTTP Accept-Language indique quelles sont les langues que le client est capable de comprendre, et quelle variante locale est préférée. |
| 5 | 0.637 | `headers/range/index.md` | L' HTTP Range indique la partie d'une ressource que le serveur doit retourner. |

## [ca04] Quel en-tete indique quels champs de la requete determinent si une reponse en cache peut etre reutilisee ?

- **annote** : `headers/vary/index.md`
- **rang obtenu** : 2

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.680 | `headers/rtt/index.md` | L' HTTP RTT est un indicateur du client sur le réseau qui fournit le temps de trajet aller-retour approximatif au niveau de l'application, en millisec |
| 2 | 0.678 | `headers/vary/index.md` **(annote)** | L'en-tête HTTP Vary détermine comment les en-têtes de requêtes futures sont associés pour décider si une réponse en cache peut être réutilisée plutôt  |
| 3 | 0.662 | `headers/no-vary-search/index.md` | L' HTTP No-Vary-Search définit un ensemble de règles qui déterminent comment les paramètres de requête d'une URL affectent la correspondance du cache. |
| 4 | 0.650 | `headers/index.md` | Les en-têtes HTTP permettent au client et au serveur de transmettre des informations supplémentaires avec un message dans une requête ou une réponse. |
| 5 | 0.647 | `headers/sec-ch-device-memory/index.md` | HTTP Sec-CH-Device-Memory est utilisé dans les indices client pour les appareils pour indiquer la quantité approximative de RAM disponible sur l'appar |

## [cr03] Quel en-tete de reponse enumere les champs que la requete reelle sera autorisee a employer ?

- **annote** : `headers/access-control-allow-headers/index.md`
- **rang obtenu** : absent du top-5

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.600 | `headers/allow/index.md` | L' HTTP Allow liste l'ensemble des méthodes de requête prises en charge par une ressource. |
| 2 | 0.584 | `headers/accept-language/index.md` | L' HTTP Accept-Language indique quelles sont les langues que le client est capable de comprendre, et quelle variante locale est préférée. |
| 3 | 0.582 | `headers/content-length/index.md` | L'en-tête HTTP Content-Length indique la taille, en octets, du corps du message envoyé au destinataire. |
| 4 | 0.582 | `headers/content-language/index.md` | L' HTTP Content-Language est utilisé pour décrire la ou les langues destinées au public, afin que les utilisateur·ice·s puissent la différencier selon |
| 5 | 0.574 | `headers/accept-ranges/index.md` | L' HTTP Accept-Ranges est utilisé par le serveur pour indiquer sa prise en charge des requêtes de plage, permettant aux clients de demander une partie |

## [cr05] Quel en-tete envoye par le navigateur annonce les champs qu'il pourrait joindre a la requete reelle ?

- **annote** : `headers/access-control-request-headers/index.md`
- **rang obtenu** : absent du top-5

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.649 | `headers/trailer/index.md` | L'en-tête Trailer permet à l'expéditeur d'inclure des champs supplémentaires à la fin des blocs de messages pour fournir des métadonnées supplémentair |
| 2 | 0.635 | `headers/referer/index.md` | L' HTTP Referer contient l'adresse absolue ou partielle à partir de laquelle une ressource a été demandée. |
| 3 | 0.630 | `headers/available-dictionary/index.md` | L'en-tête de requête HTTP Available-Dictionary permet au navigateur de définir le dictionnaire le plus adapté qu'il possède afin d'autoriser le serveu |
| 4 | 0.630 | `headers/index.md` | Les en-têtes HTTP permettent au client et au serveur de transmettre des informations supplémentaires avec un message dans une requête ou une réponse. |
| 5 | 0.630 | `headers/accept/index.md` | L' et HTTP Accept indique quels types de contenu, exprimés sous forme de types MIME, l'émetteur·rice est capable de comprendre. |

## [cr07] Quel en-tete rend certains champs de la reponse lisibles par le code JavaScript de la page ?

- **annote** : `headers/access-control-expose-headers/index.md`
- **rang obtenu** : absent du top-5

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.644 | `headers/accept-ranges/index.md` | L' HTTP Accept-Ranges est utilisé par le serveur pour indiquer sa prise en charge des requêtes de plage, permettant aux clients de demander une partie |
| 2 | 0.641 | `headers/allow/index.md` | L' HTTP Allow liste l'ensemble des méthodes de requête prises en charge par une ressource. |
| 3 | 0.637 | `headers/x-frame-options/index.md` | L'en-tête de réponse HTTP X-Frame-Options peut être utilisé afin d'indiquer si un navigateur devrait être autorisé à afficher une page au sein d'un él |
| 4 | 0.634 | `headers/accept-encoding/index.md` | L' et HTTP Accept-Encoding indique le codage du contenu (généralement un algorithme de compression) que l'émetteur peut comprendre. |
| 5 | 0.632 | `headers/access-control-allow-origin/index.md` | L' HTTP Access-Control-Allow-Origin indique si la réponse peut être partagée avec le code demandeur provenant de l' donnée. |

## [cn06] Quel en-tete fournit une empreinte calculee sur le contenu du message, pour en verifier l'integrite ?

- **annote** : `headers/content-digest/index.md`
- **rang obtenu** : absent du top-5

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.593 | `headers/index.md` | Les en-têtes HTTP permettent au client et au serveur de transmettre des informations supplémentaires avec un message dans une requête ou une réponse. |
| 5 | 0.563 | `headers/content-length/index.md` | L'en-tête HTTP Content-Length indique la taille, en octets, du corps du message envoyé au destinataire. |

## [cs01] Quelle directive sert de valeur de repli lorsqu'une autre directive de la politique est absente ?

- **annote** : `headers/content-security-policy/default-src/index.md`
- **rang obtenu** : absent du top-5

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.607 | `headers/content-security-policy/index.md` | HTTP Content-Security-Policy permet aux administrateur·ice·s d'un site web de contrôler les ressources que l'agent utilisateur est autorisé à charger  |
| 2 | 0.605 | `headers/content-security-policy/style-src-attr/index.md` | La directive HTTP (CSP) style-src-attr définit les sources valides pour des feuilles de styles appliquées à des éléments individuels du DOM par l'attr |
| 3 | 0.604 | `headers/content-security-policy/object-src/index.md` | La directive HTTP (CSP) object-src définit les sources valides pour les éléments HTML et . |
| 4 | 0.600 | `headers/content-security-policy/style-src-elem/index.md` | La directive HTTP (CSP) style-src-elem définit les sources valides pour les feuilles de styles embarquées avec les éléments HTML et avec les éléments  |
| 5 | 0.591 | `headers/content-security-policy/connect-src/index.md` | La directive HTTP (CSP) connect-src restreint les URL qui peuvent être chargées en utilisant des interfaces de programmation. Les API suivantes sont c |

## [cs02] Quelle directive couvre a la fois les scripts charges par balise, les scripts embarques et les attributs de gestion d'evenements ?

- **annote** : `headers/content-security-policy/script-src/index.md`
- **rang obtenu** : 2

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.603 | `headers/content-security-policy/script-src-attr/index.md` | La directive HTTP (CSP) script-src-attr définit les sources valides pour les gestionnaires d'évènements JavaScript embarqués. |
| 2 | 0.589 | `headers/content-security-policy/script-src/index.md` **(annote)** | La directive HTTP (CSP) script-src définit les sources valides pour du code JavaScript. Cela inclut les URL chargées directement par les éléments HTML |
| 3 | 0.582 | `headers/content-security-policy/index.md` | HTTP Content-Security-Policy permet aux administrateur·ice·s d'un site web de contrôler les ressources que l'agent utilisateur est autorisé à charger  |

## [cs04] Quelle directive ne concerne QUE les balises de script, requetes et blocs, sans toucher aux attributs ?

- **annote** : `headers/content-security-policy/script-src-elem/index.md`
- **rang obtenu** : 2

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.592 | `headers/content-security-policy/script-src-attr/index.md` | La directive HTTP (CSP) script-src-attr définit les sources valides pour les gestionnaires d'évènements JavaScript embarqués. |
| 2 | 0.589 | `headers/content-security-policy/script-src-elem/index.md` **(annote)** | La directive HTTP (CSP) script-src-elem indique les sources valides pour des éléments HTML . |
| 3 | 0.585 | `headers/content-security-policy/base-uri/index.md` | La directive HTTP (CSP) base-uri restreint les URL qui peuvent être utilisées comme valeur d'un élément HTML . Si cette valeur est absente, alors tout |
| 4 | 0.571 | `headers/content-security-policy/object-src/index.md` | La directive HTTP (CSP) object-src définit les sources valides pour les éléments HTML et . |
| 5 | 0.570 | `headers/content-security-policy/script-src/index.md` | La directive HTTP (CSP) script-src définit les sources valides pour du code JavaScript. Cela inclut les URL chargées directement par les éléments HTML |

## [cs05] Quelle directive ne s'applique qu'aux styles poses directement sur un element par son attribut de style ?

- **annote** : `headers/content-security-policy/style-src-attr/index.md`
- **rang obtenu** : 2

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.597 | `headers/content-security-policy/style-src/index.md` | La directive HTTP (CSP) style-src définit les sources valides pour les feuilles de style. |
| 2 | 0.596 | `headers/content-security-policy/style-src-attr/index.md` **(annote)** | La directive HTTP (CSP) style-src-attr définit les sources valides pour des feuilles de styles appliquées à des éléments individuels du DOM par l'attr |
| 3 | 0.592 | `headers/content-security-policy/style-src-elem/index.md` | La directive HTTP (CSP) style-src-elem définit les sources valides pour les feuilles de styles embarquées avec les éléments HTML et avec les éléments  |

## [cs09] Quelle directive limite les adresses utilisables comme base de resolution des liens relatifs ?

- **annote** : `headers/content-security-policy/base-uri/index.md`
- **rang obtenu** : 2

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.595 | `headers/content-security-policy/connect-src/index.md` | La directive HTTP (CSP) connect-src restreint les URL qui peuvent être chargées en utilisant des interfaces de programmation. Les API suivantes sont c |
| 2 | 0.582 | `headers/content-security-policy/base-uri/index.md` **(annote)** | La directive HTTP (CSP) base-uri restreint les URL qui peuvent être utilisées comme valeur d'un élément HTML . Si cette valeur est absente, alors tout |
| 3 | 0.544 | `headers/content-security-policy/form-action/index.md` | La directive HTTP (CSP) form-action restreint les URL pouvant être utilisées comme cibles d'envoi de formulaire depuis un contexte donné. |
| 4 | 0.543 | `headers/content-security-policy/index.md` | HTTP Content-Security-Policy permet aux administrateur·ice·s d'un site web de contrôler les ressources que l'agent utilisateur est autorisé à charger  |

## [ob02] Quel en-tete signale les violations d'une politique d'autorisations sans bloquer les fonctionnalites concernees ?

- **annote** : `headers/permissions-policy-report-only/index.md`
- **rang obtenu** : 2

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.681 | `headers/permissions-policy/index.md` | HTTP Permissions-Policy fournit un mécanisme pour autoriser ou refuser l'utilisation de fonctionnalités du navigateur dans un document ou dans tout él |
| 2 | 0.670 | `headers/permissions-policy-report-only/index.md` **(annote)** | HTTP Permissions-Policy-Report-Only fournit un mécanisme permettant aux administrateur·ice·s de sites Web de signaler les violations d'une sans les ap |

## [ob03] Quel en-tete signale ce qui violerait les garanties d'integrite des sous-ressources, sans encore les imposer ?

- **annote** : `headers/integrity-policy-report-only/index.md`
- **rang obtenu** : 2

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.599 | `headers/integrity-policy/index.md` | HTTP Integrity-Policy permet aux administrateur·ice·s de site web de s'assurer que toutes les ressources chargées par l'agent utilisateur (d'un certai |
| 2 | 0.594 | `headers/integrity-policy-report-only/index.md` **(annote)** | HTTP Integrity-Policy-Report-Only permet aux administrateur·ice·s de site web de signaler les ressources chargées par l'agent utilisateur qui violerai |
| 3 | 0.588 | `headers/cross-origin-embedder-policy/index.md` | HTTP Cross-Origin-Embedder-Policy (COEP) configure la politique du document courant pour le chargement et l'intégration de ressources d'origine croisé |
| 4 | 0.586 | `headers/cross-origin-embedder-policy-report-only/index.md` | HTTP Cross-Origin-Embedder-Policy-Report-Only (COEP) définit la politique rapport seulement du document actuel pour le chargement et l'intégration de  |
| 5 | 0.571 | `headers/index.md` | Les en-têtes HTTP permettent au client et au serveur de transmettre des informations supplémentaires avec un message dans une requête ou une réponse. |

## [ob04] Quel en-tete definit les points de collecte des rapports et remplace un mecanisme anterieur devenu obsolete ?

- **annote** : `headers/reporting-endpoints/index.md`
- **rang obtenu** : 2

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.556 | `headers/report-to/index.md` | Cet en-tête a été remplacé par l'en-tête HTTP . |
| 2 | 0.521 | `headers/reporting-endpoints/index.md` **(annote)** | HTTP Reporting-Endpoints permet aux administrateur·ice·s de sites de définir un ou plusieurs points de terminaison vers lesquels peuvent être envoyés  |
| 4 | 0.491 | `headers/index.md` | Les en-têtes HTTP permettent au client et au serveur de transmettre des informations supplémentaires avec un message dans une requête ou une réponse. |
| 5 | 0.490 | `headers/integrity-policy/index.md` | HTTP Integrity-Policy permet aux administrateur·ice·s de site web de s'assurer que toutes les ressources chargées par l'agent utilisateur (d'un certai |

## [ob05] Quel en-tete fournit la quantite approximative de memoire vive de l'appareil, sous son nom normalise actuel ?

- **annote** : `headers/sec-ch-device-memory/index.md`
- **rang obtenu** : 3

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.616 | `headers/device-memory/index.md` | L'en-tête Device-Memory a été standardisé sous le nom et ce nouveau nom est désormais privilégié. |
| 3 | 0.598 | `headers/sec-ch-device-memory/index.md` **(annote)** | HTTP Sec-CH-Device-Memory est utilisé dans les indices client pour les appareils pour indiquer la quantité approximative de RAM disponible sur l'appar |
| 5 | 0.545 | `headers/index.md` | Les en-têtes HTTP permettent au client et au serveur de transmettre des informations supplémentaires avec un message dans une requête ou une réponse. |

## [ob06] Quel en-tete transmet le rapport de pixels de l'appareil client, sous son nom normalise actuel ?

- **annote** : `headers/sec-ch-dpr/index.md`
- **rang obtenu** : 4

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.628 | `headers/dpr/index.md` | L'en-tête DPR a été standardisé sous le nom et ce nouveau nom est désormais privilégié. |
| 2 | 0.604 | `headers/device-memory/index.md` | L'en-tête Device-Memory a été standardisé sous le nom et ce nouveau nom est désormais privilégié. |
| 3 | 0.589 | `headers/index.md` | Les en-têtes HTTP permettent au client et au serveur de transmettre des informations supplémentaires avec un message dans une requête ou une réponse. |
| 4 | 0.587 | `headers/sec-ch-dpr/index.md` **(annote)** | HTTP Sec-CH-DPR fournit des indications du client pour les appareils concernant le ratio de pixels de l'appareil client (DPR). |

## [di04] Quel en-tete empeche le navigateur de deviner le type d'un fichier autrement qu'en lisant sa declaration ?

- **annote** : `headers/x-content-type-options/index.md`
- **rang obtenu** : 2

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.632 | `headers/content-type/index.md` | HTTP Content-Type est utilisé pour indiquer le original d'une ressource avant qu'un encodage de contenu ne soit appliqué. |
| 2 | 0.630 | `headers/x-content-type-options/index.md` **(annote)** | L'entête X-Content-Type-Options est un marqueur utilisé par le serveur pour indiquer que les types MIME annoncés dans les en-têtes ne doivent pas être |
| 3 | 0.594 | `headers/content-disposition/index.md` | L'en-tête HTTP Content-Disposition indique si le contenu doit être affiché en ligne (inline en anglais) dans le navigateur en tant que page Web ou par |
| 4 | 0.588 | `headers/content-digest/index.md` | L'en-tête HTTP Content-Digest et fournit un calculé à l'aide d'un algorithme de hachage appliqué au contenu du message. |

## [di06] Quel en-tete permet de basculer une connexion deja etablie vers un autre protocole ?

- **annote** : `headers/upgrade/index.md`
- **rang obtenu** : 2

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.685 | `headers/index.md` | Les en-têtes HTTP permettent au client et au serveur de transmettre des informations supplémentaires avec un message dans une requête ou une réponse. |
| 2 | 0.648 | `headers/upgrade/index.md` **(annote)** | et HTTP Upgrade peuvent être utilisés pour basculer une connexion client/serveur déjà établie sur un autre protocole (en conservant le même protocole  |
| 5 | 0.618 | `status/101/index.md` | Le code de statut HTTP de réponse informative 101 Switching Protocols indique le protocole sur lequel un serveur a basculé. |

## [di11] Quel en-tete rend une requete rejouable sans risque qu'elle soit traitee deux fois ?

- **annote** : `headers/idempotency-key/index.md`
- **rang obtenu** : absent du top-5

| # | score | document | definition |
|---|---|---|---|
| 1 | 0.497 | `headers/if-unmodified-since/index.md` | L' HTTP If-Unmodified-Since rend la requête pour la ressource conditionnelle. |
| 2 | 0.494 | `headers/cross-origin-embedder-policy/index.md` | HTTP Cross-Origin-Embedder-Policy (COEP) configure la politique du document courant pour le chargement et l'intégration de ressources d'origine croisé |
| 3 | 0.489 | `headers/cross-origin-embedder-policy-report-only/index.md` | HTTP Cross-Origin-Embedder-Policy-Report-Only (COEP) définit la politique rapport seulement du document actuel pour le chargement et l'intégration de  |
| 4 | 0.480 | `headers/rtt/index.md` | L' HTTP RTT est un indicateur du client sur le réseau qui fournit le temps de trajet aller-retour approximatif au niveau de l'application, en millisec |
| 5 | 0.478 | `headers/retry-after/index.md` | L' HTTP Retry-After indique pendant combien de temps l'agent utilisateur doit attendre avant d'effectuer une requête de suivi. |

