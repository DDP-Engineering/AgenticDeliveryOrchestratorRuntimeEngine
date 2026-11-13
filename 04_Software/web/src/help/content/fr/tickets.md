# Tickets et prise en charge automatique

ADORE prend en charge les tickets de votre dépôt sur la forge (GitHub, GitLab ou Gitea) lorsqu’ils portent les bonnes étiquettes, et vous pouvez aussi en démarrer un à la main. Cet article couvre les étiquettes, l’éligibilité et la vue Tickets.


Les tickets portant le label de type épopée configuré ne sont ni sélectionnés ni démarrés. Démarrer reste disponible pour les tickets éligibles quand la surveillance est en pause.

## Comment fonctionne la prise en charge {#how-pickup-works}

Chaque projet a un état de **Surveillance**, affiché comme **Active** ou **En pause** dans le tableau Projets et dans l’onglet Résumé du projet. Tant que la surveillance est Active, ADORE interroge le dépôt à intervalle régulier pour trouver des tickets prêts (60 secondes par défaut ; voir **Intervalle de scrutation (secondes)** dans [Paramètres du projet](/help/settings)). Il prend en premier le ticket éligible de plus haute priorité (P1, puis P2, puis P3), puis le plus petit numéro, et fait avancer une tâche à la fois.

Un administrateur peut utiliser **Suspendre la surveillance** et **Activer la surveillance** dans l’onglet Résumé du projet. Une surveillance en pause arrête les prises en charge automatiques ; les tâches en cours continuent.

Avant la prise en charge, ADORE ne vérifie AEGIS que si `.agentic/aegis.py` est présent. Un AEGIS présent mais défectueux ou non pris en charge est refusé, jamais remplacé silencieusement par le workflow direct. Sans ce fichier, le workflow direct utilise la **Commande de vérification** facultative ; vide signifie non vérifié. Les deux workflows gardent les mêmes étiquettes, limites et approbation humaine. Voir [Workflows du dépôt](/help/projects#workflows).

## Créer d’abord les étiquettes {#labels}

GitHub et Gitea rejettent un nom d’étiquette inconnu : une étiquette manquante fait donc échouer les mises à jour d’état. Toutes les étiquettes ci-dessous doivent exister dans le dépôt de la forge avant la première exécution. ADORE crée celles qui manquent à l’ajout d’un projet (**Créer les étiquettes ADORE dans le dépôt**, cochée par défaut dans Révision et création) ou quand vous appuyez sur **Créer les étiquettes manquantes** dans Paramètres → Dépôt ; il ne modifie ni ne supprime jamais les étiquettes existantes et indique ce qu’il a créé, ce qui existait déjà et ce qui a échoué (par exemple si le compte forge du serveur ne peut pas créer d’étiquettes). Les noms sont des valeurs par défaut ; ne renommez une étiquette qu’avec son paramètre de projet.

| Étiquette | Rôle |
|---|---|
| `agent-ready` | Vous l’ajoutez pour proposer un ticket à la prise en charge. ADORE la remplace par l’étiquette de travail au démarrage de la tâche. |
| `agent-working` | ADORE la pose pendant qu’il travaille, publie et attend votre approbation. |
| `agent-clarify` | ADORE la pose lorsqu’il a posé une question et attend une réponse. |
| `agent-answered` | Vous l’ajoutez après avoir répondu à une question. |
| `agent-mr` | ADORE la pose après avoir publié la MR/PR, pendant qu’il attend la revue humaine. |
| `agent-failed` | ADORE la pose lorsqu’une tâche échoue. |
| `agent-done` | ADORE la pose après qu’une personne a fusionné la MR/PR. |
| `agent-approved` | Vous l’ajoutez sur le ticket pour approuver la publication du candidat présenté. |
| `agent-revise` | Un relecteur l’ajoute sur la MR/PR pour demander un tour de révision. |

À chaque mise à jour d’état, ADORE retire les étiquettes de cycle de vie qu’il n’applique pas ; toutes doivent donc exister. Ajouter à la main une étiquette d’état ne modifie pas la tâche.

## Ce qui rend un ticket éligible {#eligible-tickets}

Un ticket n’est pris en charge que si toutes les règles sont satisfaites. Elles sont vérifiées dans cet ordre :

1. Le ticket est ouvert.
2. Il porte l’étiquette de disponibilité (`agent-ready`).
3. Il ne porte pas l’étiquette de blocage (`agent-hold`). Retirer l’étiquette de blocage rend de nouveau le ticket éligible.
4. Il ne porte pas l’étiquette d’exclusion (`no-agent`, paramètre **Étiquette d’exclusion de la prise en charge**). Elle l’emporte sur l’étiquette de disponibilité. La retirer rétablit l’éligibilité ; l’ajouter n’arrête pas une tâche déjà démarrée.
5. ADORE n’a pas encore de tâche pour ce ticket.
6. Il porte une étiquette de priorité : `P1`, `P2` ou `P3`. **Exiger une étiquette de priorité sur le ticket** est activé par défaut.
7. Si **Exiger des critères d’acceptation sur le ticket** est activé, la description contient les mots acceptance criteria (sans distinction de casse) ou un élément de tâche non coché, `- [ ]`. Cette vérification est désactivée par défaut.

Des étiquettes facultatives orientent la tâche : `bug` ou `fix` donne une tâche de correction, `change` une tâche de modification, et tout autre ticket une tâche de fonctionnalité. `agent-quick` n’est qu’une indication ; l’exécuteur choisit entre le chemin complet et le chemin rapide et en consigne la raison.

## Examiner et démarrer les tickets {#tickets-view}

Ouvrez un projet depuis Projets, choisissez son onglet **Tâches** et restez dans le sous-onglet **Tickets**. La page globale **Tâches** de la barre latérale a les mêmes deux sous-onglets et un sélecteur **Périmètre des travaux**. Avec **Tous les projets**, le tableau gagne une colonne Projet et chaque ligne agit sur son propre projet.

Rien n’est lu tant que vous n’appuyez pas sur **Lire les tickets**. Cela charge jusqu’à 500 tickets ouverts. Au-delà de 10 tickets, ils s’affichent page par page : choisissez 10, 25, 50 ou Tout dans **Lignes par page** et naviguez avec **Précédent** et **Suivant** ; le numéro de page et le nombre de pages sont indiqués. Chaque ligne affiche le numéro dans une colonne étroite, à côté du titre, des étiquettes, de l’état et des actions. L’état nomme ce qui bloque un ticket :

| État | Signification |
|---|---|
| Prêt à démarrer | Toutes les règles sont satisfaites. |
| Étiquette ... manquante | L’étiquette de disponibilité est absente. |
| En attente ou Exclu d’ADORE | L’étiquette de blocage ou d’exclusion est présente. |
| Étiquette de priorité manquante | Aucune étiquette de priorité. |
| Critères d’acceptation manquants | Le texte requis est introuvable. |
| A une tâche ou Tâche : ... | ADORE a déjà une tâche ; son état est affiché. |
| Non ouvert | Le ticket est fermé. |

**Démarrer** met une tâche en file ; le worker applique toujours les contrôles habituels. Si le ticket n’a pas l’étiquette de disponibilité ou de priorité, ADORE vous demande de confirmer, vous laisse choisir une priorité, et **Ajouter les étiquettes et démarrer** les ajoute d’abord dans le dépôt. Démarrer n’est pas disponible pour les tickets fermés, bloqués ou exclus, les tickets sans les critères d’acceptation requis et les tickets qui ont une tâche. **Relancer** remplace Démarrer lorsque la tâche a échoué. **Arrêter** demande une confirmation, annule une tâche inachevée et retire l’étiquette de disponibilité pour que la surveillance ne reprenne pas le ticket. **Détails** affiche la description et les commentaires.

**Démarrer** lance manuellement le seul ticket sélectionné, même avec la **Surveillance** **En pause**, et laisse la surveillance en pause. Capacité, workflow du dépôt, éligibilité, verrou du conducteur et approbations restent vérifiés. Une opération échouée affiche sa raison précise ; si le résultat est invalide ou incertain, consultez les journaux de l’hôte avant de réessayer.

Les opérations en file sont vérifiées toutes les 2 secondes lorsque cet onglet est visible, avec une seule lecture d’état à la fois et une limite de 30 secondes. Les onglets masqués suspendent ces contrôles ; le retour en effectue un. Si un contrôle échoue ou renvoie un résultat invalide, la fin reste inconnue. Un résultat observé actualise les informations partagées du projet sans relire les tickets ou commentaires de la forge ni fermer les contenus ouverts. Appuyez sur **Lire les tickets** pour une nouvelle lecture du dépôt.

Les mises à jour inchangées du projet conservent les contenus ouverts et les confirmations Démarrer/Arrêter valides. Si l’identité, l’accès ou l’archivage change, l’ancienne confirmation ne peut plus être envoyée, même après restauration. Appuyez sur **Lire les tickets** et vérifiez à nouveau. Les contenus des projets retirés restent masqués jusqu’à une nouvelle lecture explicite. Quitter le contexte annule les requêtes du navigateur et ignore les résultats obsolètes ; cela n’annule pas une commande déjà acceptée par le serveur.

Les lectures de tickets et commentaires sont limitées à 30 secondes et ne réessaient jamais automatiquement la forge. Après une erreur, utilisez **Lire les tickets** pour la liste, ou fermez puis rouvrez **Détails** pour les commentaires. Rouvrir des commentaires en cours de lecture partage cette lecture.

## Lire descriptions et commentaires {#reading-bodies}

**Détails** ouvre par défaut descriptions et commentaires en Markdown **Rendu**. Titres, emphase, code, listes imbriquées, tâches en lecture seule, citations, tableaux et liens sont mis en forme ; une description vide conserve **Aucune description.**

Utilisez **Affichage du contenu** à droite du titre **Description**, avec le libellé et le sélecteur sur une ligne pour choisir **Rendu** ou **Source Markdown** pour toutes les descriptions et tous les commentaires ouverts. La source montre le texte exact reçu du dépôt, espaces et sauts de ligne compris. Votre compte conserve un choix enregistré entre projets, rechargements et navigateurs ; un autre navigateur connecté le lit à sa prochaine connexion ou au rechargement. Si l’enregistrement échoue, une erreur apparaît et le dernier mode enregistré revient ; choisissez à nouveau pour réessayer.

Le HTML reste du texte visible, jamais du contenu exécutable. Seuls les liens absolus http, https et mailto sont cliquables et s’ouvrent séparément. Les images ne se chargent jamais automatiquement : **Image non chargée** et le texte alternatif éventuel les remplacent. Code, source et tableaux larges défilent dans leurs propres zones, accessibles au clavier. Les cases de tâches ne modifient pas le ticket.

## Liste de contrôle pour un premier ticket {#checklist}

1. Créez les neuf étiquettes dans le dépôt de la forge.
2. Pour la prise en charge automatique, vérifiez la surveillance Active ; pour Démarrer manuellement, elle peut rester En pause.
3. Rédigez un titre clair et une description avec des critères d’acceptation.
4. Ajoutez une étiquette de priorité et, si vous le souhaitez, `bug`, `fix`, `change` ou `agent-quick`.
5. Ajoutez `agent-ready` en dernier.
6. Attendez la prochaine vérification, ou appuyez sur **Lire les tickets** puis **Démarrer**.
7. Suivez la tâche dans [Cycle de vie d’une tâche](/help/jobs). Les termes sont dans le [Glossaire](/help/glossary).
