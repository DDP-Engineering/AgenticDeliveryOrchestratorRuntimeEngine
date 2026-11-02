# Exécuteurs et modèles

Un exécuteur est ce qu’ADORE lance pour chaque tâche : l’agent de programmation Pi et le modèle d’IA qu’il utilise. Les administrateurs choisissent le modèle dans les Paramètres d’un projet.

## Ce qu’est un exécuteur {#what}

Pour chaque tâche, ADORE démarre Pi, son unique agent de codage, dans une copie de travail isolée, et Pi suit les étapes AEGIS du dépôt avec le fournisseur et le modèle configurés. Pi ne commite pas, ne pousse pas et ne voit aucun identifiant de forge ; ADORE s’en charge. En conteneur, ADORE utilise le Pi intégré à l’image de l’exécuteur ; pour un projet installé sur le serveur, Pi doit déjà être installé pour le compte du serveur. Les changements s’appliquent aux nouvelles tâches uniquement.

## Choisir le fournisseur et le modèle {#agent-and-model}

Ouvrez **Paramètres → Agent et modèle**. Les lignes sont **Fournisseur**, **Modèle**, **Commande de lancement de l’exécuteur** et, pour un point de terminaison, **URL de base du point de terminaison** et **Type d’API du point de terminaison**. **Modifier** sur l’une des lignes fournisseur, modèle ou point de terminaison ouvre un seul éditeur pour toutes, revues et appliquées en une seule modification.

- **Fournisseur** : un fournisseur Pi à clé API (OpenAI, Anthropic, Google Gemini, OpenRouter, Mistral et d’autres), **Abonnement ChatGPT** ou **Point de terminaison compatible OpenAI**.
- **Modèle** : choisissez dans la liste de Pi pour ce fournisseur ou saisissez tout ID de modèle accepté par le fournisseur, par exemple `gpt-5.4`. La liste accompagne la version de Pi fournie par ADORE et se lit sans accès à internet. Il n’y a pas de modèle universel par défaut.
- **Abonnement ChatGPT** : la connexion avec ChatGPT n’est pas disponible dans cette version ; choisissez un fournisseur à clé API ou un point de terminaison pour exécuter des tâches.

**Préparer le candidat** montre la valeur active et proposée de chaque champ et **Appliquer** les écrit ; prévoyez de suspendre la surveillance, voir [Paramètres du projet](/help/settings#editing). En conteneur, ADORE démarre lui-même le Pi intégré à l’image, via son mode RPC avec des réglages fixes, et l’arrête à la limite de temps de l’étape ou à l’annulation ; la commande de lancement n’y sert pas, seul le préréglage Pi est proposé. Pour un projet installé sur le serveur, la commande de lancement démarre le Pi installé, vaut par défaut `pi -p --mode json --model {model} {prompt}` (`{model}` devient fournisseur/modèle), doit contenir `{prompt}` et ne doit pas utiliser `--auto`.

## Point de terminaison compatible OpenAI {#endpoint}

Pour un modèle servi sur votre propre réseau, comme LM Studio, Ollama ou vLLM, choisissez **Point de terminaison compatible OpenAI** et renseignez :

- **URL de base du point de terminaison** : l’adresse vue depuis le conteneur, par exemple `http://192.168.1.20:1234/v1`. `localhost` est le conteneur lui-même. `host.docker.internal` n’atteint l’hôte qu’avec Docker Desktop ; avec Docker Engine sous Linux ou dans WSL, utilisez l’adresse réseau de l’hôte, et pour un serveur sous Windows atteint depuis Docker dans WSL, la passerelle par défaut de WSL.
- **Type d’API du point de terminaison** : `openai-completions` pour LM Studio, Ollama et vLLM ; `openai-responses`, `anthropic-messages` et `google-generative-ai` sont aussi acceptés.
- **Modèle** : l’ID du modèle servi par le point de terminaison.

Une clé de point de terminaison est facultative : enregistrez-la sous Authentification sous ADORE_ENDPOINT_API_KEY. ADORE décrit le point de terminaison à Pi pour chaque tâche ; l’adresse ne contient jamais de nom d’utilisateur, de mot de passe ni de requête. Avec une politique réseau restreinte, l’adresse du point de terminaison doit être autorisée. Un point de terminaison n’est disponible que pour les projets en conteneur.

## Authentification {#credentials}

Ouvrez **Authentification** dans le même groupe.

- **Clé API du fournisseur.** Le panneau indique la variable requise par le fournisseur configuré, par exemple OPENAI_API_KEY pour OpenAI ou ANTHROPIC_API_KEY pour Anthropic. Saisissez la **Clé API** et choisissez **Enregistrer la clé API**. ADORE la conserve en privé dans le magasin d’identifiants du projet sur le serveur, jamais dans le fichier de configuration, ne la transmet à Pi que par cette variable et ne l’affiche plus jamais ; **Déconnecter la clé API du projet** la supprime. Changer une clé exige la surveillance suspendue, un projet inactif et aucune proposition en attente, et ne teste pas la clé.
- **Connexion existante du compte.** Uniquement pour un projet installé sur le serveur : Pi utilise sa propre connexion pour le compte du serveur, configurée hors de l’interface web. Un projet en conteneur utilise toujours la clé API du fournisseur ; aucune connexion n’est copiée dans le conteneur.
- **Valeurs gérées par l’environnement.** Une variable déjà définie dans l’environnement du serveur ADORE porte la mention **Définie sur le serveur ADORE ; gestion externe**. L’interface web ne peut pas l’écraser.
- **Variables d’identification supplémentaires.** Noms uniquement (**Ajouter une variable d’identification**) de secrets supplémentaires reçus par Pi en plus de la clé du fournisseur ; la plupart des projets n’en ont pas besoin.

Les valeurs d’identifiants n’apparaissent jamais dans le fichier de configuration, les revues, les journaux d’audit, les journaux ou les exports.

## Tester la connexion IA {#test-connection}

Les administrateurs choisissent **Tester la connexion IA** sous **Connexion IA**. Le test démarre Pi une fois dans un conteneur temporaire, ou dans un dossier temporaire pour Pi installé sur le serveur, lui demande d’exécuter une commande shell puis de répondre par un texte fixe, et peut entraîner des frais du fournisseur. Le projet doit être inactif, avec des paramètres enregistrés valides et aucune proposition en attente ; pour un projet en conteneur, l’image configurée doit exister sur le serveur.

Le résultat est **Modèle IA connecté** seulement si la commande shell a été exécutée et que la réponse est arrivée. Sinon **Connexion IA non vérifiée** s’accompagne de conseils propres pour : aucun identifiant enregistré, une clé refusée par le fournisseur, un fournisseur ou point de terminaison que Pi n’a pas pu joindre, un modèle inconnu du fournisseur ou du point de terminaison, une limite de débit, une autre erreur du fournisseur, un délai dépassé, une image ou un Pi manquant, ou une commande shell que Pi n’a pas pu exécuter. Aucune tâche n’est lancée. Le résultat enregistré est lié au fournisseur, au modèle, aux paramètres et aux identifiants actuels et apparaît dans les vérifications de l’hôte du Résumé. Les développeurs le voient mais ne peuvent pas lancer le test.

## Où s’exécutent les tâches {#where-jobs-run}

| | Conteneur | Exécution locale native |
|---|---|---|
| S’exécute dans | Un conteneur Docker ou Podman temporaire sur le serveur ADORE | Le serveur ADORE lui-même, sous le compte du système d’exploitation du service, dans un worktree dédié |
| Environnement | Une image de projet préparée par l’administrateur | Les outils, versions et bibliothèques que vous installez vous-même sur ce serveur |
| Connexion | La clé API du fournisseur | La clé API du fournisseur ou la connexion existante de Pi sur ce compte, réutilisée telle quelle |
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
