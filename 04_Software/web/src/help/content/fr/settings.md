# Paramètres du projet

L’onglet Paramètres d’un projet liste les règles de fonctionnement qu’ADORE lui applique : quels tickets il prend en charge, ses limites, la façon dont il publie et l’agent qu’il utilise. Les administrateurs modifient plusieurs paramètres et les enregistrent ensemble ; les développeurs les lisent.

## Où trouver les Paramètres {#where}

Ouvrez [Projets](/projects), choisissez un projet et sélectionnez l’onglet **Paramètres**. Les onglets sont Résumé, Paramètres, Tâches, Statistiques, Historique et, pour les administrateurs, Accès.

Les paramètres enregistrés s’actualisent toutes les 15 secondes quand l’onglet du navigateur est visible. L’actualisation se met en pause en cas de modification non enregistrée, d’enregistrement ou d’abandon en cours. L’actualisation se met aussi en pause pendant la saisie d’un tarif ou d’une clé API et pendant la connexion ChatGPT.

Les administrateurs peuvent modifier. Les développeurs qui ont accès au projet voient **Paramètres en lecture seule**, sans boutons Modifier et sans secrets ni paramètres financiers. Chaque projet a ses propres paramètres ; la capacité globale et la conservation de l’audit relèvent de l’Administration.

## Groupes de paramètres {#groups}

Chaque groupe est fermé à l’ouverture des Paramètres, et le nombre à côté de son nom compte ses lignes.

| Groupe | Ce qu’il contrôle |
|---|---|
| Dépôt | Forge et dépôt, connexion Gitea, **Branche cible** (base des nouvelles tâches et destination des PR/MR), le modèle de nom de branche des tâches avec une règle de nommage facultative et un exemple en direct, ainsi que le nom affiché de l’agent, son nom de ressource et l’adresse e-mail de l’auteur des commits. |
| Tickets | **Étiquette de disponibilité pour la prise en charge**, **Étiquette d’exclusion de la prise en charge**, les **Étiquettes de statut** repliées, la fréquence à laquelle ADORE interroge la forge, la nécessité ou non de critères d’acceptation ou d’une étiquette de priorité, et le type de tâche par défaut. Voir [Tickets et prise en charge automatique](/help/tickets#labels). |
| Implémentation | Limites par tâche : **Limite de tâches actives**, **Nombre maximal de lancements de l’exécuteur par tâche**, **Limite de temps de travail actif (secondes)**, **Plafond de coût de la tâche (USD)**, **Nombre maximal de fichiers modifiés par tâche** et **Limite de temps par tentative d’étape (secondes)**. Il contient aussi **Clarifications**, **Reprise après erreur**, **Limites de temps avancées par étape**, **Publier les commits de progression** et l’étiquette du chemin rapide. |
| PR/MR et revue | **Demander une revue à**, **État de la PR/MR à la publication** (Brouillon ou Prête pour revue), l’étiquette d’approbation, **Supprimer la branche après la fusion humaine**, les tours de révision et **Action en cas d’échec des vérifications CI de la PR/MR** (Réparation automatique, Notifier uniquement ou Ignorer). |
| Statistiques | **Enregistrer les mesures des tâches terminées** et **Enregistrer les jetons déclarés par l’agent**. **Fichier de la base de statistiques** est affiché à titre d’information seulement. |
| Agent et modèle | Fournisseur, modèle, authentification et **Tester la connexion IA** [Exécuteurs et modèles](/help/executors). |
| Détails techniques | Valeurs d’installation en lecture seule, comme le dossier d’état des tâches, le chemin du dépôt local et les dossiers de travail des tâches. Elles se modifient dans le `config.toml` du projet sur le serveur, et changer un chemin ne déplace pas les données existantes. |

## Valeurs et aide {#values}

Chaque ligne a un libellé, une description toujours visible, une **Valeur active** et une **Valeur par défaut d'ADORE**. La description indique ce que contrôle le paramètre, son unité ou ses valeurs admises, et l’effet d’une modification, ou précise qu’il est réservé et inutilisé. Il n’y a pas de bouton d’aide séparé.

Un badge **Par défaut** signifie que le `config.toml` du projet ne définit pas la valeur : le défaut d’ADORE s’applique. La modifier écrit une valeur pour ce projet seulement. Une ligne marquée **Non modifiable ici** se change dans le `config.toml` sur le serveur. Une ligne marquée **À appliquer seulement avec la sélection suspendue et sans tâche active** exige la condition supplémentaire décrite ci-dessous.

Choisissez **Installé sur le serveur** pour utiliser le Pi géré par ADORE sous le compte système actuel. Le **PATH des outils du projet** facultatif sélectionne leurs dossiers. Voir [Installer Pi sur le serveur](/help/executors#installed-executors).

## Modification {#editing}

1. Choisissez **Modifier** à côté de chaque valeur à changer. Vous pouvez modifier plusieurs paramètres dans différents groupes.
2. Utilisez le bouton unique **Enregistrer** au-dessus des groupes. Il est actif seulement si des valeurs changent et si toutes les modifications sont valides.
3. Pour les changements importants, **Confirmer les modifications importantes** affiche le projet, les valeurs modifiées et les effets. Choisissez **Enregistrer les modifications**, ou **Continuer la modification** pour revenir sans enregistrer.

Règles applicables :

- **Annuler les modifications** efface toutes les modifications non enregistrées. Annuler la confirmation les conserve sans créer de candidat enregistré.
- L’enregistrement est lié à la configuration modifiée. Une révision périmée bloque l’enregistrement et conserve vos saisies . Abandonnez vos modifications pour recharger les paramètres enregistrés avant de recommencer. Les modifications concurrentes provoquent un conflit.
- Le serveur vérifie toute la configuration et enregistre les changements ensemble. Un enregistrement révisé des seuls budgets permet aussi les tâches en attente de clarification, sans conducteur actif ni opération inachevée. Les autres paramètres exigent des tâches terminées. Un échec conserve vos saisies et le candidat préparé.
- Les changements d’identité ou d’environnement exigent aussi la surveillance en pause. Choisissez **Suspendre la surveillance** dans Résumé et laissez le travail actif se terminer ; la pause n’interrompt pas une tâche.
- Les budgets s’appliquent avant la prochaine tentative ou reprise, en conservant consommation et progression. Voir [Budgets du travail](#budgets).

La navigation et le rechargement de la page demandent confirmation avant d’abandonner les modifications. Les brefs blocages de fichier Windows sont réessayés automatiquement ; si l’enregistrement échoue, vérifiez l’accès au fichier et réessayez **Enregistrer**.

## TOML d’origine {#toml}

À côté du titre Paramètres du projet, les administrateurs disposent de **Voir la configuration brute** et **Exporter la configuration brute**. L’aperçu ouvre une boîte de dialogue fermable et ne garde le texte qu’en mémoire. Le téléchargement fournit le `config.toml` enregistré exactement tel que stocké, avec ses commentaires, sa mise en forme et d’éventuels secrets en clair : traitez-le comme un secret. Ni l’un ni l’autre n’inclut un candidat en attente, les valeurs par défaut résolues, les fichiers `.env` séparés ou les identifiants externes. Les développeurs ne peuvent pas les utiliser. Sélectionnez le fichier exporté dans [Importer la configuration brute](/help/projects#import-project) et ADORE vérifie automatiquement les chemins du serveur, le dossier d’état et les secrets en clair avant l’inscription.

Choisissez **Exporter la configuration brute** pour ouvrir le dialogue d’export. Pour Docker, il propose **Inclure les fichiers de build Docker**. Cette option devient disponible après l’enregistrement d’une **Définition de build Docker** vérifiée dans **Agent et modèle**. Le ZIP contient le même TOML, un fichier Compose et les sources déclarées du commit choisi. Si les fichiers de build manquent, le dialogue l’explique et permet toujours l’export du TOML. Choisissez **Exporter** pour télécharger ou **Annuler** pour fermer.

## Paquets système de l’agent {#system-packages}

**Autoriser l’installation de paquets système par l’agent**

Dans Paramètres → Agent et modèle, les administrateurs activent cette permission avec **Enregistrer** et confirment son effet. Désactivée par défaut, elle concerne les projets en conteneur. Reconstruisez ou choisissez une image compatible avec sudo, puis lancez une nouvelle tâche. L’agent exécute directement les commandes, analyse les échecs et s’adapte dans les limites de la tâche.

L’accès réseau reste distinct : open autorise les sources accessibles, allowlist-proxy les domaines HTTP/HTTPS permis, et none uniquement les sources locales disponibles. Les scripts de paquets ont des droits administratifs dans le conteneur ; les dossiers montés restent partagés avec le serveur. Les paquets système restent dans le même conteneur à la reprise ; un nouveau conteneur exige une nouvelle évaluation et installation.

## Budgets du travail {#budgets}

Le détail affiche **Lancements de l’exécuteur** (par exemple 9 / 20) et **Travail actif (secondes)** avec les limites actuelles du projet, indépendamment des statistiques de jetons. À 90 %, il signale une limite proche ; à la limite, il demande de l’augmenter avant la reprise. La limite initiale est 20 dans l’inscription et `adore init`.

Les administrateurs peuvent suivre **Ajuster les budgets dans les paramètres du projet**, ouvrir **Implémentation**, modifier uniquement les budgets, choisir **Enregistrer** et confirmer les valeurs exactes. Cet enregistrement révisé est permis pendant une attente de clarification, sans conducteur actif ni opération inachevée. Les autres paramètres gardent leurs contrôles habituels ; les développeurs restent en lecture seule.

Les budgets sont relus avant chaque tentative, reprise ou relance. Une tentative en cours garde son délai. Le travail actif est cumulé entre relances, réponses et révisions ; l’attente est exclue. Augmenter une limite conserve le travail consommé, la tâche et la progression. Une tâche échouée par épuisement exige toujours **Relancer** après ajustement. Une configuration invalide ou absente bloque les tentatives suivantes jusqu’à correction.

Si les limites actuelles sont illisibles, le détail conserve la consommation, les preuves et les actions de reprise. Les limites affichent — avec un avis d’indisponibilité ; aucune valeur par défaut n’est supposée. Corrigez la configuration avant de relancer.
