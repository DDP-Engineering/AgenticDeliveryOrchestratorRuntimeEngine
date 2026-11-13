# Ce que fait ADORE

L’approbation humaine avant publication est activée par défaut. Les administrateurs peuvent modifier **Exiger une approbation humaine avant PR/MR** dans Paramètres. Si elle est désactivée, ADORE contrôle l’actualité du candidat et de la cible avant publication ; les tests du dépôt restent à la charge de l’agent.

ADORE transforme un ticket préparé sur votre forge de code en une demande de fusion (MR) ou de tirage (PR) en brouillon que des personnes relisent. Cette page explique le flux et les deux rôles ; les autres sujets détaillent chaque écran.

## Ce que fait ADORE {#what-adore-does}

ADORE surveille les projets qu’un administrateur a inscrits. Lorsqu’un ticket de la forge (GitHub, GitLab ou Gitea) est préparé pour la prise en charge, ADORE démarre une **tâche** pour ce ticket :

- Il exécute un agent de programmation (l’exécuteur) dans un environnement isolé : une branche dédiée, un dossier de travail et un conteneur.
- L’agent suit le workflow AEGIS du dépôt, une étape à la fois : Cadrage, Spécification, Conception, Développement et Validation. Une petite modification peut suivre un chemin rapide sans Spécification ni Conception.
- ADORE observe le résultat rapporté par l’agent et demande à une personne d’approuver le candidat.
- Après l’approbation, ADORE publie une MR/PR en brouillon que des personnes relisent. Un projet peut être configuré pour publier à la place une MR/PR prête pour la revue.

> ADORE ne fusionne jamais. Il n’a aucune opération de fusion ; c’est une personne qui décide de fusionner ou non sur la forge.

L’interface web montre ce qui s’exécute et ce qui demande de l’attention. Elle permet aussi de démarrer des tickets, de relancer ou d’annuler des tâches et, pour un administrateur, de configurer les projets et les comptes.

Si l’état des tâches d’un projet est illisible, **À traiter** nomme le projet concerné. Les données des tâches des autres projets sélectionnés restent visibles.

## Du ticket à la fusion {#flow}

| Étape | État affiché | Qui agit | Ce qui se passe |
|---|---|---|---|
| 1. Préparer | Pas encore de tâche | Une personne | Le ticket reçoit l’étiquette de disponibilité et une étiquette de priorité, ou vous appuyez sur **Démarrer** dans Tâches → Tickets, ce qui ajoute les étiquettes manquantes après votre confirmation. |
| 2. Travailler | En cours | ADORE et l’agent de programmation | ADORE crée la tâche et l’agent parcourt les étapes AEGIS. |
| 3. Clarifier | En attente de clarification | Une personne | Seulement si l’agent a une question. Répondez dans le ticket du dépôt et ajoutez l’étiquette de réponse. |
| 4. Valider | En cours | Agent de programmation | L’agent rapporte les contrôles selon les instructions du dépôt, y compris ceux réservés à la CI et non exécutés localement, puis clôt la tâche AEGIS. ADORE observe la fin sans relancer les tests. |
| 5. Approuver | En attente d'approbation | Une personne | ADORE présente le candidat sur la forge. Une personne ajoute l’étiquette d’approbation. L’approbation est liée à ce candidat précis. |
| 6. Publier | Publication | ADORE | ADORE pousse la branche et ouvre la MR/PR en brouillon. |
| 7. Relire | Revue humaine | Une personne | Les personnes relisent. Une révision répète la validation et suit la politique d’approbation du projet. |
| 8. Fusionner | Terminé | Une personne | Une personne fusionne sur la forge. ADORE ne le fait pas. |

Si le candidat ou sa branche cible change après l’approbation, celle-ci ne s’applique plus et la tâche est de nouveau validée. Les termes sont expliqués dans le [glossaire](/help/glossary).

## Rôles {#roles}

| Rôle | Voit | Peut faire |
|---|---|---|
| Administrateur (Admin) | Tous les projets actuels et futurs, ainsi que l’Administration et les coûts | Tout ce qu’un Dev peut faire, et inscrire des projets, modifier les paramètres d’un projet par des changements vérifiés, suspendre ou reprendre la surveillance, archiver ou restaurer des projets, gérer les utilisateurs et l’accès aux projets, définir la conservation de l’audit, lire l’historique des changements, et voir et définir les coûts |
| Dev | Uniquement les projets attribués par un administrateur | Démarrer et arrêter des tickets, relancer ou annuler des tâches, lire les statistiques des projets attribués et lire les paramètres d’un projet (en lecture seule, sans secrets ni paramètres financiers) |

Un Dev ne voit jamais de valeurs monétaires et ne peut pas ouvrir les pages d’Administration. Sans projet attribué, la Vue d’ensemble invite le Dev à demander l’accès à un administrateur. S’il n’y a aucun projet, un Admin peut choisir **Inscrire un nouveau projet** dans la Vue d’ensemble.

## Premiers pas {#getting-started}

1. Les administrateurs inscrivent le dépôt : [Ajouter un dépôt](/help/projects).
2. Choisissez le modèle utilisé par l’agent de programmation Pi : [Exécuteurs et modèles](/help/executors).
3. Préparez les tickets pour qu’ADORE puisse les prendre en charge : [Tickets et prise en charge automatique](/help/tickets).
4. Suivez chaque tâche jusqu’à sa MR/PR en brouillon : [Cycle de vie d’une tâche](/help/jobs).

Les développeurs commencent à l’étape 3 dès qu’un administrateur leur a donné accès à un projet.

## Pour aller plus loin {#topics}

- [Ce que fait ADORE](/help/overview) : cette page.
- [Visite de l’interface](/help/interface) : barre latérale, en-tête, hub du projet et libellés d’état.
- [Ajouter un dépôt](/help/projects) : inscrire un projet.
- [Paramètres du projet](/help/settings) : ce que contrôle chaque groupe de paramètres.
- [Exécuteurs et modèles](/help/executors) : l’agent de programmation Pi, les modèles et l’authentification.
- [Tickets et prise en charge automatique](/help/tickets) : étiquettes et démarrage des tickets.
- [Cycle de vie d’une tâche](/help/jobs) : états, attentes, relance et annulation.
- [Statistiques et coûts](/help/statistics) : utilisation, qualité, tendances et coûts estimés.
- [Administration](/help/administration) : utilisateurs, accès, état du système et historique des changements.
- [Glossaire](/help/glossary) : les termes utilisés dans l’interface.
