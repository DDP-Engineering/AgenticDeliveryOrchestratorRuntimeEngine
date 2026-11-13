# Administration

L’Administration couvre les comptes utilisateurs, l’accès aux projets, la santé du système et l’historique des changements. Elle est réservée aux administrateurs : un Dev ne voit pas le menu Administration, et un Dev qui ouvre l’une de ses adresses est redirigé vers la Vue d’ensemble.

> Tout ce qui figure sur cette page exige le rôle Administrateur.


Un battement récent indique que le worker est disponible. **Occupé** indique une commande ou vérification en cours ; **Activité inconnue** indique une preuve indisponible. Un seul worker traite projets et commandes à tour de rôle. Un signal d’annulation autorisé peut atteindre une tâche active avant la fin de la commande en file.

## Utilisateurs {#users}

Sous **Administration**, ouvrez [Utilisateurs](/admin/users). La page comporte un panneau **Ajouter un utilisateur** et une liste **Utilisateurs**.

Pour créer un compte :

1. Choisissez **Ajouter un utilisateur** au-dessus de la liste pour ouvrir la fenêtre de création. Saisissez l’**Identifiant** et le **Mot de passe** (au moins 8 caractères), puis répétez-le dans **Confirmer le nouveau mot de passe**. Les boutons en forme d’œil affichent ou masquent chaque champ. Choisissez **Continuer vers les accès**. Après **Corriger l’identité**, saisissez de nouveau la confirmation. La vérification omet le mot de passe.
2. Choisissez le **Rôle** et, pour un Dev, les projets. **Admin** donne accès à tous les projets actuels et futurs, à l’administration du système et aux coûts. **Dev** donne accès uniquement aux projets que vous cochez, chacun listé avec son nom, sa forge et le chemin de son dépôt. Pour créer un Dev sans projet, cochez volontairement **Créer Dev sans accès aux projets**.
3. Choisissez **Vérifier le compte**, contrôlez l’identité et les accès exacts, puis choisissez **Créer le compte vérifié**. **Corriger l’identité** et **Corriger les accès** vous ramènent en arrière sans rien créer.

Le compte et ses accès sont créés ensemble, ou pas du tout. Un identifiant en double ou un projet modifié entre-temps fait rejeter la demande ; corrigez et recommencez la vérification.

Dans la liste **Utilisateurs**, chaque compte propose ces actions.

- **Projets attribués** (comptes Dev) : cochez ou décochez des projets, choisissez **Enregistrer**, comparez **Avant** et **Après**, puis choisissez **Appliquer les accès vérifiés**. **Corriger les accès** annule la vérification.
- **Désactiver** ou **Activer** : un compte désactivé ne peut plus se connecter et ses sessions prennent fin. Vous ne pouvez pas désactiver votre propre compte, et le dernier administrateur actif ne peut pas être désactivé.
- **Réinitialiser le mot de passe** : choisissez cette action sur la ligne du compte. Vérifiez le nom du compte, saisissez un **Nouveau mot de passe** d’au moins 8 caractères puis remplissez **Confirmer le nouveau mot de passe**. Les boutons en forme d’œil affichent ou masquent les saisies. Choisissez **Enregistrer** si elles correspondent ou **Fermer** pour abandonner la saisie. L’enregistrement ferme les sessions du compte et impose un nouveau mot de passe à sa prochaine connexion. Il n’existe pas de récupération par e-mail.

## Accès aux projets {#project-access}

L’onglet **Accès** d’un projet liste chaque compte développeur avec **A accès** ou **Pas d’accès**. Choisissez **Donner l’accès** ou **Retirer l’accès** à côté d’un développeur, comparez **Avant** et **Après**, puis choisissez **Appliquer les accès vérifiés**. Le changement laisse intacts les autres projets du développeur et est consigné dans l’Historique des changements. La liste des accès s’actualise toutes les 15 secondes quand l’onglet du navigateur est visible.

Un développeur qui a accès voit le projet et peut démarrer, relancer ou annuler ses tâches. Les administrateurs ont toujours accès.

## État du système {#system-status}

Sous **Administration**, ouvrez [État du système](/admin/status). Il s’actualise seul.

- **Agent de contrôle** affiche **Prêt** au repos, **Occupé** en traitement, **Activité inconnue** si la preuve manque, **Indisponible**, **Échec de la vérification** ou **Vérification…**. Un battement récent ne confirme pas l’accès à la forge, aux exécuteurs ou aux modèles.
- **Stockage** indique **Espace disponible**, **Espace disque faible** ou **Échec de la vérification du stockage**. Il mesure l’espace disque libre pour la base de comptes d’ADORE et le dossier d’état des tâches de chaque projet, regroupés par volume physique. Un disque partagé donne une seule ligne ; plusieurs disques donnent un tableau **Volume**, **Libre** et **État**. Moins de 1 Gio libre est considéré comme faible, et une mesure en échec n’est jamais présentée comme de l’espace libre.
- **Conservation de l'audit** définit la durée de conservation de l’historique des changements. Les limites actuelles (ou **Illimité**) apparaissent au-dessus du formulaire. Définissez **Conserver pendant (jours)** (jours entiers, de 0 à 36500) et **Limite des données d'audit (Mio)** (de 0 à 1024, fractions admises) puis choisissez **Enregistrer**. Zéro ou vide signifie illimité. Les deux limites s’appliquent indépendamment et les plus anciens événements sont supprimés en premier. Le message après l’enregistrement indique combien d’événements ont été supprimés. La limite de taille compte le texte d’audit stocké, pas le fichier de base de données sur le disque. Les tâches, les journaux d’exécution et les comptes sont conservés.

## Historique des changements {#change-history}

Sous **Administration**, ouvrez [Historique des changements](/admin/audit) pour voir qui a changé quoi, quand, et avec quel résultat. L’onglet **Historique** d’un projet montre les mêmes preuves pour ce projet seul, avec ses tâches terminées. Les deux vues s’actualisent toutes les 15 secondes quand elles sont visibles et conservent vos filtres, la page et les preuves ouvertes. Dans les deux vues, **Actualiser** relit la même page sans effacer le tableau, les filtres en cours de saisie, les preuves ouvertes ni le focus clavier. **Actualisé le** indique une lecture validée réussie, pas son début. Une panne de connexion ou le délai de lecture de 10 secondes peut laisser les preuves précédentes clairement signalées comme non actuelles, avec **Réessayer**. Les preuves invalides, non autorisées ou ayant échoué autrement restent masquées jusqu’à une lecture réussie.

L’historique distingue les tickets et les tâches des numéros d’opération. Une opération échouée affiche **Échec**, une opération refusée **Refusé**. Les suppressions par CLI indiquent CLI comme auteur et restent visibles après suppression de la tâche. Une suppression interrompue reste **Incertain** jusqu’à confirmation.

Filtres :

- **ID de l’auteur** : le numéro affiché à côté du nom d’un compte.
- **Projet** : n’importe quel projet, ou **Tous les projets**.
- **Type de modification** : le code d’action exact.
- **Depuis (UTC)** inclut son instant ; **Jusqu’à (UTC, exclusif)** ne l’inclut pas.

Choisissez **Appliquer les filtres** ; cela revient à la première page. La page indique combien d’événements correspondent, et **Lignes par page** propose 10, 25, 50 ou Tout avec **Précédent** et **Suivant**.

Chaque ligne affiche **Qui**, **Quoi**, **Quand** et **Résultat** : **Préparé**, **Appliqué**, **Abandonné**, **Refusé** ou **Incertain**. Préparé signifie qu’un candidat a été préparé, pas appliqué. **Incertain** signifie que l’hôte n’a pas pu confirmer l’achèvement ; examinez la ressource réelle avant de rétablir la situation. **Preuve** ouvre une ligne sous l’événement avec **Avant**, **Après / candidat**, l’**Opération**, ainsi que la **Révision de base** et la **Révision candidate** lorsqu’elles sont enregistrées. **Valeur précédente non enregistrée** signifie inconnue, pas vide. Les mots de passe et les valeurs d’environnement ne sont jamais affichés.

L’historique des changements est conservé indéfiniment, sauf si vous définissez des limites sous [État du système](#system-status). L’historique des changements ne peut être ni téléchargé ni exporté. Un Dev ne voit les changements opérationnels que pour les projets attribués ; les événements de compte, d’accès, de tarif et de politique restent réservés aux administrateurs.
