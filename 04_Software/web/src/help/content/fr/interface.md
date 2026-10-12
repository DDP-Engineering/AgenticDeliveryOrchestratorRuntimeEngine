# Visite de l’interface

L’interface comprend une barre latérale sombre pour passer d’une page à l’autre et une barre supérieure qui nomme la page courante et propose les actions courantes. Cette page décrit les pages, les boutons de l’en-tête, le hub du projet et les libellés d’état.

## Navigation {#navigation}

| Page | Ce que vous y faites |
|---|---|
| Vue d'ensemble | Consulter **À traiter** et **Tâches actives** pour les projets auxquels vous avez accès. **Détails** ouvre une tâche dans Tâches. |
| [Projets](/projects) | Parcourir les projets inscrits avec leur dépôt, leur forge, l’état de la surveillance, le nombre de tâches et la dernière activité. Ouvrez un projet pour accéder à son hub. Les administrateurs voient aussi **Inscrire un nouveau projet**, **Importer une configuration de projet** et **Cloner une configuration de projet**. |
| [Tâches](/jobs) | Choisir un **Périmètre des travaux**, puis utiliser le sous-onglet **Tickets** pour lire les tickets de la forge et les démarrer, ou le sous-onglet **Tâches** pour rechercher des tâches et ouvrir leurs détails. |
| [Statistiques](/metrics) | Consulter l’utilisation, la qualité et les tendances sur une période de rapport. Voir [Statistiques et coûts](/help/statistics). |
| Administration | Réservée aux administrateurs. Elle ouvre trois pages : [État du système](/admin/status), [Utilisateurs](/admin/users) et [Historique des changements](/admin/audit). Voir [Administration](/help/administration). |
| [Mon compte](/account) | Choisir votre langue et votre thème, et changer votre mot de passe. |

La barre latérale affiche aussi votre nom et votre rôle, ainsi que **Se déconnecter**. Sur un écran étroit, **Menu** ouvre la navigation et le choix d’une page la referme.

Un Dev ne voit que les projets attribués par un administrateur et n’a pas d’entrée Administration. Chaque page a sa propre adresse : les favoris, Précédent, Suivant et le rechargement conservent donc votre position.

## En-tête {#header}

La barre supérieure affiche le titre de la page et ces commandes.

- **Projet** : un sélecteur, uniquement sur la Vue d’ensemble. Il limite **À traiter** et **Tâches actives** à un projet ; par défaut, ce sont tous les projets accessibles. Tâches a son propre sélecteur **Périmètre des travaux** et Statistiques a un sélecteur **Projet** dans sa ligne de période de rapport.
- **Actualiser** : affiché, avec l’heure **Actualisé le**, uniquement sur les pages qui ne se mettent pas à jour seules : Utilisateurs, Historique des changements, et les onglets Paramètres, Accès et Historique d’un projet.
- **À propos** : la version d’ADORE, avec **Nouveautés** (notes de version par version, de la plus récente à la plus ancienne, regroupées en Nouveau, Amélioré et Corrigé), **Licence** et **Mentions des composants tiers**.
- **Comment fonctionne ADORE** : ouvre ce centre d’aide.

## Hub du projet {#project-hub}

L’ouverture d’un projet depuis Projets affiche son nom et le chemin de son dépôt au-dessus de ces onglets.

| Onglet | Ce qu’il contient |
|---|---|
| Résumé | Type de conteneur, exécuteur, surveillance, vérification de l’environnement, nombre de tâches, et tableaux compacts À traiter et Tâches actives. Les administrateurs disposent aussi de **Suspendre la surveillance** ou **Activer la surveillance**, **Archiver le projet** ou **Restaurer le projet**, **Vérifier les prérequis de l’hôte** et **Connecter le dépôt**. |
| Paramètres | Les paramètres effectifs du projet, par groupes. Les administrateurs modifient un paramètre à la fois par un changement vérifié ; les Dev les lisent sans les secrets. Voir [Paramètres du projet](/help/settings). |
| Tâches | Les sous-onglets Tickets et Tâches de ce projet, sans sélecteur de projet. |
| Statistiques | La même période de rapport, les mêmes onglets et les mêmes exports que la page Statistiques, pour ce projet seulement. |
| Historique | Les changements enregistrés du projet et ses tâches terminées. |
| Accès | Réservé aux administrateurs : donner ou retirer l’accès d’un développeur. |

Une surveillance en pause empêche la prise en charge de nouveaux tickets ; les tâches déjà démarrées continuent.

## Libellés d’état et badges {#statuses}

Les badges portent un symbole en plus de la couleur, et les listes de tâches affichent l’étape courante à côté de l’état.

| État de la tâche | Signification |
|---|---|
| En cours | ADORE conduit une étape. |
| Publication | ADORE publie un candidat approuvé. |
| En attente de clarification | L’agent attend une réponse dans le ticket du dépôt. |
| En attente d'approbation | Une personne doit approuver le candidat sur la forge. |
| Revue humaine | Une MR/PR en brouillon est ouverte ; des personnes décident de fusionner ou non. |
| Transfert en cours | Un transfert à une personne attend un point sûr. |
| Transféré | Une personne a pris le relais ; le travail automatique est terminé. |
| Terminé | La tâche est finie. Cela ne prouve pas à lui seul que quelqu’un a fusionné. Les listes compactes l’appellent Terminée. |
| Échouées | La tâche s’est arrêtée en conservant les preuves ; un utilisateur autorisé peut la **Réessayer**. |
| Annulée | La tâche a été annulée. |
| Périmé | La tâche est marquée comme périmée ; consultez son résultat enregistré. |

Dans Tâches, **État** limite la liste à **Tâches actives**, **En attente**, **Revue humaine** ou **Travaux terminés**. Le badge de surveillance d’un projet indique **Active** ou **En pause**, et un projet archivé indique **Archivé**. La vérification de l’environnement indique **Vérifié**, **Partiellement vérifié**, **Vérification échouée**, **Vérification périmée** ou **Non vérifié** ; Non vérifié signifie qu’il n’y a aucune preuve à jour, pas qu’un contrôle a échoué.

Après **Démarrer**, **Réessayer** ou **Annuler**, un message indique si la commande est en file, en cours, terminée, échouée ou incertaine. Examinez une commande incertaine avant de la soumettre de nouveau.

## Mises à jour automatiques, langue et thème {#preferences}

La Vue d’ensemble, Projets et Tâches rechargent leurs données toutes les 15 secondes tant que l’onglet du navigateur est visible ; Statistiques et État du système s’actualisent aussi seuls. Un onglet masqué cesse de se mettre à jour et s’actualise dès votre retour. Si une mise à jour échoue, les chiffres concernés restent masqués jusqu’à la prochaine mise à jour réussie.

Dans [Mon compte](/account), **Apparence** contient **Langue** (English, Français, Deutsch, Română) et **Thème** (**Système**, **Clair**, **Sombre**). Chaque choix est enregistré dans votre compte et vous suit d’un navigateur à l’autre ; avant la connexion, la page de connexion mémorise le choix dans le navigateur. **Changer le mot de passe** demande votre mot de passe actuel et un nouveau mot de passe d’au moins 8 caractères.
