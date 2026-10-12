# Paramètres du projet

L’onglet Paramètres d’un projet liste les règles de fonctionnement qu’ADORE lui applique : quels tickets il prend en charge, ses limites, la façon dont il publie et l’agent qu’il utilise. Les administrateurs les modifient par un flux vérifié, un paramètre à la fois ; les développeurs les lisent.

## Où trouver les Paramètres {#where}

Ouvrez [Projets](/projects), choisissez un projet et sélectionnez l’onglet **Paramètres**. Les onglets sont Résumé, Paramètres, Tâches, Statistiques, Historique et, pour les administrateurs, Accès.

Les administrateurs peuvent modifier. Les développeurs qui ont accès au projet voient **Paramètres en lecture seule**, sans boutons Modifier et sans secrets ni paramètres financiers. Chaque projet a ses propres paramètres ; la capacité globale et la conservation de l’audit relèvent de l’Administration. Les Paramètres ne s’actualisent pas seuls : utilisez Actualiser dans l’en-tête pour les relire.

## Groupes de paramètres {#groups}

Chaque groupe est fermé à l’ouverture des Paramètres, et le nombre à côté de son nom compte ses lignes.

| Groupe | Ce qu’il contrôle |
|---|---|
| Dépôt | Forge et dépôt, connexion Gitea, **Branche cible** (base des nouvelles tâches et destination des PR/MR), le modèle de nom de branche des tâches avec une règle de nommage facultative et un exemple en direct, ainsi que le nom affiché de l’agent, son nom de ressource et l’adresse e-mail de l’auteur des commits. |
| Tickets | **Étiquette de disponibilité pour la prise en charge**, **Étiquette d’exclusion de la prise en charge**, les **Étiquettes de statut** repliées, la fréquence à laquelle ADORE interroge la forge, la nécessité ou non de critères d’acceptation ou d’une étiquette de priorité, et le type de tâche par défaut. Voir [Tickets et prise en charge automatique](/help/tickets#labels). |
| Implémentation | Limites par tâche : **Limite de tâches actives**, **Nombre maximal de lancements de l’exécuteur par tâche**, **Limite de temps de travail actif (secondes)**, **Plafond de coût de la tâche (USD)**, **Nombre maximal de fichiers modifiés par tâche** et **Limite de temps par tentative d’étape (secondes)**. Il contient aussi **Clarifications**, **Reprise après erreur**, **Limites de temps avancées par étape**, **Publier les commits de progression** et l’étiquette du chemin rapide. |
| PR/MR et revue | **Demander une revue à**, **État de la PR/MR à la publication** (Brouillon ou Prête pour revue), l’étiquette d’approbation, **Supprimer la branche après la fusion humaine**, les tours de révision et **Action en cas d’échec des vérifications CI de la PR/MR** (Réparation automatique, Notifier uniquement ou Ignorer). |
| Statistiques | **Enregistrer les mesures des tâches terminées** et **Enregistrer les jetons déclarés par l’agent**. **Fichier de la base de statistiques** est affiché à titre d’information seulement. |
| Agent et modèle | L’agent de programmation, la commande de lancement, le modèle, l’authentification et **Tester la connexion IA**. Voir [Exécuteurs et modèles](/help/executors). |
| Détails techniques | Valeurs d’installation en lecture seule, comme le dossier d’état des tâches, le chemin du dépôt local et les dossiers de travail des tâches. Elles se modifient dans le `config.toml` du projet sur le serveur, et changer un chemin ne déplace pas les données existantes. |

## Valeurs et aide {#values}

Chaque ligne a un libellé, une description toujours visible, une **Valeur active** et une **Valeur par défaut d'ADORE**. La description indique ce que contrôle le paramètre, son unité ou ses valeurs admises, et l’effet d’une modification, ou précise qu’il est réservé et inutilisé. Il n’y a pas de bouton d’aide séparé.

Un badge **Par défaut** signifie que le `config.toml` du projet ne définit pas la valeur : le défaut d’ADORE s’applique. La modifier écrit une valeur pour ce projet seulement. Une ligne marquée **Non modifiable ici** se change dans le `config.toml` sur le serveur. Une ligne marquée **À appliquer seulement avec la sélection suspendue et sans tâche active** exige la condition supplémentaire décrite ci-dessous.

## Modification {#editing}

1. Choisissez **Modifier** à côté de la valeur active, saisissez la nouvelle valeur et choisissez **Préparer le candidat**. Cela n’écrit qu’un candidat en attente ; la configuration en service reste inchangée.
2. Le panneau **Configuration en attente** apparaît au-dessus des groupes et ne liste que les valeurs modifiées. Un candidat qui ne change rien ne peut pas être appliqué. Ouvrez **Détails techniques** pour la comparaison complète, l’effet, l’heure de préparation, les deux révisions et **Copier la revue expurgée**. Les valeurs d’identifiants sont masquées.
3. Choisissez **Appliquer** pour le soumettre, ou **Abandonner** pour supprimer uniquement le candidat.

Règles applicables :

- Un paramètre à la fois : les autres boutons Modifier restent désactivés jusqu’à ce que le candidat soit appliqué ou abandonné.
- La revue est liée aux révisions. Appliquer envoie les révisions de base et du candidat vérifiées ; si le fichier actif a changé entre-temps, vous devez abandonner, actualiser et préparer de nouveau. Deux administrateurs qui modifient en même temps obtiennent un conflit au lieu de s’écraser mutuellement. Les modifications faites directement dans le fichier sur le serveur contournent cette protection.
- Au moment d’Appliquer, le serveur revérifie qu’aucune tâche n’est active et qu’aucune opération n’est inachevée. Un Appliquer bloqué conserve le candidat et explique comment rétablir la situation.
- Les paramètres qui changent l’identité ou l’environnement d’exécution exigent aussi que la surveillance soit en pause. Choisissez **Suspendre la surveillance** dans Résumé et laissez le travail actif se terminer ; la suspension n’interrompt pas une tâche en cours.
- Les nouvelles valeurs s’appliquent aux tâches suivantes. Les tâches existantes conservent leur configuration.

## TOML d’origine {#toml}

À côté du titre Paramètres du projet, les administrateurs disposent de **Voir la configuration brute** et **Télécharger la configuration brute**. L’aperçu ouvre une boîte de dialogue fermable et ne garde le texte qu’en mémoire. Le téléchargement fournit le `config.toml` enregistré exactement tel que stocké, avec ses commentaires, sa mise en forme et d’éventuels secrets en clair : traitez-le comme un secret. Ni l’un ni l’autre n’inclut un candidat en attente, les valeurs par défaut résolues, les fichiers `.env` séparés ou les identifiants externes. Les développeurs ne peuvent pas les utiliser.
