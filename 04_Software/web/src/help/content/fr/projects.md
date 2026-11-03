# Ajouter un dépôt

Ajoutez un dépôt comme projet pour qu’ADORE puisse prendre en charge ses tickets prêts, lancer un agent de programmation dessus et publier des demandes de fusion ou de tirage en brouillon que des personnes relisent. Seuls les administrateurs ajoutent des projets, et ADORE ne fusionne jamais.

## Avant de commencer {#before-you-start}

Préparez ces éléments :

- L’adresse du dépôt (https ou ssh) que le compte du serveur ADORE peut lire. ADORE le clone dans son propre dossier à la création du projet.
- AEGIS installé dans le dépôt (`.agentic/aegis.py` et `.agentic/aegis.toml`). ADORE l’utilise tel quel et ne le modifie jamais. Ses commandes de test s’exécutent dans le conteneur Linux ; écrivez-les donc pour le conteneur.
- Un compte GitLab, GitHub ou Gitea qui peut lire et mettre à jour les tickets et créer des revues en brouillon.
- Les noms des étiquettes de disponibilité et d’approbation. Une personne ajoute l’étiquette de disponibilité pour rendre un ticket éligible ; voir [Tickets et prise en charge automatique](/help/tickets#labels).
- L’identifiant du modèle de l’agent de programmation Pi et, pour un projet en conteneur, une image sur le serveur construite à partir de l’image de base d’ADORE, qui contient Pi. Voir [Exécuteurs et modèles](/help/executors).

## Inscrire un nouveau projet {#add-project}

Choisissez **Inscrire un nouveau projet** dans [Projets](/projects). L’assistant guidé commence par Dépôt et identité et comporte cinq étapes, et la modification d’une réponse rend périmées les validations et vérifications précédentes.

| Étape | Ce qui est demandé |
|---|---|
| Dépôt et identité | **URL du dépôt** et **Lire le dépôt** : ADORE remplit **Forge**, **Dépôt**, **Gitea tea login**, **Branche cible** et l’identifiant du projet, à confirmer, et propose un **Chemin du clone local** modifiable. **Continuer** reste désactivé tant que le dépôt n’a pas été lu. **Nom affiché** reprend le nom du dépôt ; **Description** est facultative. |
| Agent et modèle | Choisissez le **Fournisseur**, le **Modèle** et, si nécessaire, le point de terminaison. Pour un conteneur, choisissez le moteur et l’image. Enregistrez la clé du fournisseur dans Paramètres après la création. Pour **Installé sur le serveur**, seuls le compte système actuel et le **PATH des outils du projet** facultatif s’affichent. |
| Éligibilité, relecteurs et limites | **Label prêt**, **Label d'approbation**, **Réviseurs (séparés par des virgules)** facultatifs et quatre limites par tâche : lancements de l’exécuteur, secondes actives, coût déclaré en USD et fichiers modifiés. Un plafond de coût à 0 désactive ce plafond ; cela ne signifie pas gratuit. |
| Vérification | **Valider la configuration** contrôle la structure et les dossiers du serveur. **Vérifier l'environnement** teste ensuite Git, l’outil de la forge et la connexion, le moteur de conteneur, Pi dans l’image et les fichiers AEGIS. Rien n’est publié. Chaque résultat s’affiche à côté de son bouton ; **Continuer** ouvre la révision une fois la configuration valide. |
| Révision et création | Affiche le candidat exact et les emplacements sur le serveur, ainsi qu’une liste repliée **Paramètres laissés par défaut** avec la valeur par défaut de chaque autre paramètre (en lecture seule ; modifiez-les dans Paramètres après la création). **Modifier** revient à une étape. **Créer avec prise de tickets arrêtée** clone d’abord le dépôt (depuis une URL), vérifie AEGIS et la branche cible, puis enregistre le projet et, sauf si vous décochez **Créer les étiquettes ADORE dans le dépôt**, crée les étiquettes ADORE manquantes et en affiche le résultat ; **Ouvrir le projet** suit. |

Pour l’exécution locale native, choisissez **Exécution → Installé sur le serveur**. Les configurations de conteneur spécialisées passent par la méthode TOML serveur avancée ci-dessous.

Choisissez **Installé sur le serveur** pour utiliser le Pi géré par ADORE sous le compte système actuel. Le **PATH des outils du projet** facultatif sélectionne leurs dossiers. Voir [Installer Pi sur le serveur](/help/executors#installed-executors).

**Emplacement automatique** conserve le chemin proposé pour le clone. Choisissez **Emplacement personnalisé** puis **Choisir un dossier…** pour parcourir les dossiers de l’hôte ADORE. Un clic sélectionne une ligne ; un double-clic ou Entrée ouvre le dossier. Utilisez Retour ou Dossier parent, puis **Sélectionner le dossier** pour confirmer exactement le dossier existant. Saisissez une nouvelle destination dans le champ du clone du formulaire principal. Le sélecteur ne crée rien ; liens et chemins réseau sont refusés. **Annuler** conserve le brouillon.

**Branche cible** liste les branches distantes de GitHub, GitLab et Gitea, y compris les instances privées. La branche par défaut du dépôt est sélectionnée et marquée **par défaut**. Choisissez une autre branche si nécessaire. **Lire le dépôt** actualise la liste et conserve un choix explicite tant que la branche existe. Changer l’URL efface les anciens choix. Sans branche par défaut, choisissez-en une ; sans branches, ajoutez-en une au dépôt et relisez-le. L’accès Git du compte ADORE est utilisé ; un type de forge inconnu reste à sélectionner manuellement.

## Importer une configuration de projet {#import-project}

Choisissez **Importer une configuration de projet** dans [Projets](/projects) pour inscrire un `config.toml` ADORE existant tel quel, par exemple créé en ligne de commande ou enregistré auparavant avec **Télécharger la configuration brute** dans les Paramètres d’un projet. Le fichier (UTF-8, jusqu’à 512 Kio) doit contenir des chemins serveur absolus et aucun secret en clair : la revue liste ceux qu’elle trouve, remplacez-les d’abord par des références d’environnement. Son identifiant de projet et son dossier d’état ne doivent appartenir à aucun projet inscrit. ADORE copie le fichier octet par octet et termine par **Inscrire avec la sélection arrêtée**. L’historique n’apparaît que si ses données existent déjà dans le dossier d’état déclaré.

## Cloner une configuration de projet {#clone-project}

Choisissez **Cloner une configuration de projet** dans [Projets](/projects) pour démarrer un nouveau projet avec les règles de fonctionnement d’un autre. **Depuis un projet de ce serveur** lit un projet auquel vous avez accès ; **Depuis un fichier de paramètres portables** lit un fichier JSON portable (jusqu’à 64 Kio) de la même version d’ADORE. Seules 15 règles de fonctionnement (scrutation, préparation, reprise, budgets des tâches) sont reprises ; l’identité, le dépôt, les étiquettes, les identifiants, les points d’accès, les images et l’historique ne sont jamais copiés. Choisissez **Examiner les règles source**, puis **Configurer la nouvelle cible** et répondez aux étapes guidées. Examinez les fichiers inconnus : la somme de contrôle détecte les modifications mais ne prouve pas l’auteur.

## Après la création {#after-creation}

Un nouveau projet démarre avec la surveillance arrêtée. Les développeurs le voient une fois qu’un administrateur leur donne accès dans son onglet **Accès**. Dans l’onglet **Résumé** :

1. Choisissez **Connecter le dépôt**. Saisissez l’adresse du serveur de la forge et un jeton d’accès créé sur la forge, puis **Vérifier et connecter**. Cela confirme le compte et l’accès en lecture au dépôt. Le jeton reste sur le serveur, jamais dans le navigateur. Vous pouvez aussi connecter l’outil de la forge sous le compte de service d’ADORE.
2. Choisissez **Vérifier les prérequis de l’hôte**. Le détail couvre Git, l’outil de commande du dépôt, la connexion au dépôt, le moteur de conteneur, Pi dans l’image et les fichiers AEGIS, ainsi que la connexion ChatGPT du serveur pour un abonnement ChatGPT, l’image du proxy réseau quand l’[accès Internet](/help/executors#internet) est désactivé et la clé de recherche web quand Brave ou Tavily en demande une. Pour un projet exécuté directement sur le serveur, **Exécution locale** remplace les lignes du moteur de conteneur et de l’image : elle vérifie la version compatible de Node, Pi géré par ADORE et les identifiants du fournisseur. Ce n’est pas une tâche complète et cela ne prouve pas l’autorisation de poussée.
3. Lancez **Tester la connexion IA** dans Paramètres, comme décrit dans [Exécuteurs et modèles](/help/executors#test-connection).
4. Choisissez **Activer la surveillance**. La tuile Surveillance passe de En pause à Active et ADORE commence à prendre en charge les tickets qui portent l’étiquette de disponibilité. **Suspendre la surveillance** arrête les nouvelles prises en charge mais n’interrompt pas une tâche en cours.

## Archiver, restaurer et supprimer {#lifecycle}

Les administrateurs trouvent ces boutons dans l’onglet Résumé.

- **Archiver le projet** fonctionne une fois les tâches terminées et les demandes en file traitées. Il conserve les paramètres, l’historique, les statistiques et les enregistrements d’audit, et arrête tout nouveau travail. **Restaurer le projet** le ramène.
- **Supprimer le projet** n’apparaît que pour les projets archivés et demande de saisir le nom du projet. Il supprime les paramètres ADORE du projet, l’historique des tâches, les statistiques, les conteneurs et les worktrees. Il conserve le dépôt et ses branches, les worktrees des tâches confiées à une personne, un dossier d’état de tâche situé hors du répertoire ADORE et la piste d’audit. La suppression est refusée tant que du travail est en file ou inachevé. **Supprimer aussi le clone local** (décoché) supprime aussi le clone créé par ADORE dans son dossier `repos` ; l’option n’apparaît que pour un clone propre du dépôt de ce projet qu’aucun autre projet n’utilise et dont aucun worktree conservé par la suppression n’a encore besoin, sinon la fenêtre indique pourquoi le clone est conservé.

> La suppression est irréversible. Pour ajuster un projet ensuite, voir [Paramètres du projet](/help/settings).

## Connexion Gitea sur cet ordinateur {#gitea-sign-in}

ADORE utilise d’abord la connexion enregistrée du projet. Sinon, il réutilise la configuration tea du compte courant. Si tea signale un compte absent, ADORE vérifie les emplacements standard Windows ou Linux et choisit le compte configuré, un unique compte par défaut ou le seul compte disponible. Plusieurs comptes sans sélection claire exigent une connexion explicite.

La détection respecte `XDG_CONFIG_HOME`. Sous Windows, elle vérifie aussi Local AppData, Roaming AppData et le répertoire personnel `.config` ; sous Linux, le répertoire personnel `.config`. Elle ne parcourt pas les caches privés des applications et ne copie pas les identifiants entre ordinateurs.

1. Ouvrez l’onglet **Résumé** du projet et choisissez **Connecter le dépôt**.
2. Indiquez l’origine Gitea, avec son port si nécessaire, dans **Serveur du dépôt**.
3. Créez sur ce serveur un jeton pour le compte autorisé à lire/modifier les tickets et créer des demandes de revue en brouillon, puis saisissez-le dans **Jeton d’accès**.
4. Choisissez **Vérifier et connecter**. Un serveur HTTP exige la confirmation affichée. Un échec préserve la connexion enregistrée.
5. Contrôlez à nouveau les prérequis de l’hôte. Les identifiants Git clone/push sont configurés séparément.

Sur un autre ordinateur, préparez sa propre connexion CLI ou utilisez ce formulaire. L’archive de livraison ne contient aucun jeton utilisateur.
