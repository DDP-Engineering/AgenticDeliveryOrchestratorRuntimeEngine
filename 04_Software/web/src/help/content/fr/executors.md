# Exécuteurs et modèles

Un exécuteur est ce qu’ADORE lance pour chaque tâche : l’agent de programmation Pi et le modèle d’IA qu’il utilise. Les administrateurs choisissent le modèle dans les Paramètres d’un projet.

## Ce qu’est un exécuteur {#what}

Pour chaque tâche, ADORE démarre Pi, son unique agent de programmation, dans une copie de travail isolée, et Pi parcourt les étapes AEGIS du dépôt avec le modèle configuré. Pi ne commit jamais, ne pousse jamais et ne voit jamais les identifiants de la forge ; c’est ADORE qui s’en charge. ADORE ne récupère aucune liste de modèles. Dans un conteneur, ADORE utilise le Pi intégré à l’image de l’exécuteur ; pour un projet installé sur le serveur, Pi doit déjà être installé pour le compte du serveur. Les changements ne s’appliquent qu’aux nouvelles tâches.

## Choisir le modèle {#agent-and-model}

Ouvrez **Paramètres → Agent et modèle**. Les lignes sont **Identifiant du modèle de l’exécuteur** et **Commande de lancement de l’exécuteur**.

Saisissez vous-même l’ID du modèle : le modèle Pi sous la forme `provider/model`, par exemple `openai/gpt-5.4`. Il n’existe aucun défaut universel. Dans un conteneur, ADORE lance lui-même le Pi intégré à l’image, via son mode RPC avec des réglages fixes, et l’arrête à la limite de durée de l’étape ou à l’annulation ; la commande de lancement n’y est pas utilisée, seul le préréglage Pi est donc proposé. Pour un projet installé sur le serveur, la commande de lancement démarre le Pi installé, vaut par défaut `pi -p --mode json --model {model} {prompt}`, doit contenir `{prompt}` et ne doit pas utiliser `--auto`. Chaque ligne est un paramètre ordinaire : **Préparer le candidat** l’examine et **Appliquer** l’écrit. Prévoyez de suspendre d’abord la surveillance ; voir [Paramètres du projet](/help/settings#editing).

Un modèle servi sur votre propre réseau par un point d’accès compatible OpenAI, comme LM Studio, ne peut pas être configuré dans cette version.

## Authentification {#credentials}

Ouvrez **Authentification** dans le même groupe. Un projet peut s’authentifier de trois façons.

- **Clés API du fournisseur.** Choisissez une **Variable d’identification** (par exemple OPENAI_API_KEY ou ANTHROPIC_API_KEY), saisissez la **Clé API** et choisissez **Enregistrer la clé API**. ADORE la conserve de façon privée sur le serveur et ne l’affiche plus jamais ; **Déconnecter la clé API du projet** la supprime. La variable doit d’abord figurer sous **Variables d’identification autorisées**, qui ne contient que des noms (**Ajouter une variable d’identification**). Changer une clé exige une surveillance en pause, un projet inactif et aucun changement en attente, et ne teste pas la clé.
- **Connexion existante du compte.** Uniquement pour un projet installé sur le serveur : Pi utilise sa propre connexion pour le compte du serveur, configurée en dehors de l’interface web. Un projet en conteneur utilise toujours des clés API du fournisseur ; aucune connexion n’est copiée dans le conteneur.
- **Valeurs gérées par l’environnement.** Une variable déjà définie dans l’environnement du serveur ADORE porte la mention **Définie sur le serveur ADORE ; gestion externe**. L’interface web ne peut pas l’écraser.

Les valeurs d’identifiants n’apparaissent jamais dans les revues, les enregistrements d’audit ou les exports. Une liste de variables vide est valide pour un projet installé sur le serveur qui utilise la connexion existante du compte.

## Tester la connexion IA {#test-connection}

Les administrateurs choisissent **Tester la connexion IA** sous **Connexion IA**. Cela envoie une courte requête via Pi dans un conteneur temporaire, ou dans un dossier temporaire pour Pi installé sur le serveur, ce qui peut entraîner des frais du fournisseur. Le projet doit être inactif, avec des paramètres enregistrés valides et aucun changement en attente ; pour un projet en conteneur, l’image configurée doit exister sur le serveur.

Le résultat est **Modèle IA connecté** ou **Connexion IA non vérifiée**, avec des indications en cas de délai dépassé, d’image ou de Pi absent, d’identifiants incorrects, de modèle indisponible ou d’une commande shell que Pi n’a pas pu exécuter. Dans un conteneur, Pi répond sans utiliser d’outils : le test prouve donc uniquement l’accès au modèle. Pour Pi installé sur le serveur, la requête demande aussi à Pi d’exécuter une commande shell, et le résultat n’est connecté que si cette commande s’est exécutée. Il ne démarre aucune tâche. Le résultat enregistré est lié au modèle, aux paramètres et aux identifiants actuels et apparaît dans les contrôles de l’hôte du Résumé. Les développeurs le voient mais ne peuvent pas lancer le test.

## Où s’exécutent les tâches {#where-jobs-run}

| | Conteneur | Exécution locale native |
|---|---|---|
| S’exécute dans | Un conteneur Docker ou Podman temporaire sur le serveur ADORE | Le serveur ADORE lui-même, sous le compte du système d’exploitation du service, dans un worktree dédié |
| Environnement | Une image de projet préparée par l’administrateur | Les outils, versions et bibliothèques que vous installez vous-même sur ce serveur |
| Connexion | Clés API du fournisseur listées | Clés API du fournisseur listées ou connexion existante de Pi sur ce compte, réutilisée telle quelle |
| Réglages de l’agent | Le Pi intégré à l’image, avec des réglages fixés par ADORE ; les réglages et compétences Pi personnels ne sont pas lus | Le Pi installé pour ce compte, lancé avec la commande de lancement et les réglages Pi de ce compte |
| Isolation | Conteneur avec une politique réseau | Uniquement le worktree ; les commandes peuvent atteindre tout ce que le compte peut atteindre, utilisez donc un compte dédié aux privilèges minimaux |
| Choisi | **Exécution** → **Conteneur**, par défaut, à l’étape 2 de l’inscription ou dans Paramètres → Agent et modèle | **Exécution** → **Installé sur le serveur**, ou le profil du serveur ou l’inscription TOML |

Les modifications dans Paramètres passent par **Préparer le candidat**, la revue et **Appliquer**. **Installé sur le serveur** affiche la commande native de l’exécuteur et les champs du compte local (compte `current`, dossier personnel, PATH et, sous Linux, la racine cgroup) avec l’avis d’exécution locale.

Les contrôles de l’hôte pour un projet local ignorent le moteur de conteneur et vérifient le Pi installé et sa connexion ou sa clé API.

## Image du projet {#project-image}

Pour un projet en conteneur, Paramètres → Agent et modèle affiche **L’exécuteur fonctionne dans un conteneur**, l’**Image utilisée** et un volet **Instructions de préparation de l’environnement**. L’interface web ne définit ni ne construit l’image, et l’ajout d’un Dockerfile au dépôt ne lance aucune construction. L’administrateur la prépare sur le serveur :

1. Créer `executor/Dockerfile` dans le dépôt, à partir de l’image de base d’ADORE, sans identifiants. L’image de base contient déjà Python, sh et le Pi épinglé.
2. La construire avec Docker ou Podman du serveur et vérifier les versions des outils.
3. Sélectionner l’image dans l’interface web comme décrit ci-dessous ou, avec la surveillance en pause et aucune tâche active, définir `execution.backend`, `container.image` et `container.required_tool_checks` dans le `config.toml` du projet (les administrateurs en voient le chemin dans le volet), puis valider le profil.

```
FROM adore-executor-base:1.0.0
USER root
# RUN ... install the project's system tools
USER adore
```

Pour utiliser l’image, choisissez le **Moteur de conteneur** (Docker ou Podman) et l’**Image de l'exécuteur** à l’étape 2 de l’inscription, ou modifiez ces mêmes lignes dans Paramètres. L’image est un champ libre avec des suggestions tirées des images du serveur ADORE pour ce moteur (administrateurs uniquement) ; un avis s’affiche quand l’image saisie n’est pas sur le serveur, un autre quand la liste ne peut pas être lue.

Confirmez ensuite avec **Vérifier les prérequis de l’hôte** et **Tester la connexion IA**.
