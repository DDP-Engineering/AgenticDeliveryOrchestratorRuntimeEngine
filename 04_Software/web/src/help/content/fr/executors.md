# Exécuteurs et modèles

Un exécuteur est ce qu’ADORE lance pour chaque tâche : l’agent de programmation Pi et le modèle d’IA qu’il utilise. Les administrateurs choisissent le modèle dans les Paramètres d’un projet.


**Effort de raisonnement** propose les niveaux pris en charge par le modèle dans le catalogue Pi fourni. La valeur par défaut laisse Pi choisir. Les modèles absents et les points personnalisés ne peuvent pas déclarer de niveaux non pris en charge. Le choix vaut pour les tâches et le test de connexion IA.

## Ce qu’est un exécuteur {#what}

Pour chaque tâche, ADORE démarre Pi, son unique agent de codage, dans une copie de travail isolée, et Pi suit les étapes AEGIS du dépôt avec le fournisseur et le modèle configurés. ADORE utilise le Pi intégré à l’image dans un conteneur et son installation gérée de Pi pour les tâches sur le serveur.

## Choisir le fournisseur et le modèle {#agent-and-model}

Ouvrez **Paramètres → Agent et modèle**. Modifiez ensemble **Fournisseur**, **Modèle** et, pour un point de terminaison, **URL de base du point de terminaison** et **Type d’API du point de terminaison** en une seule modification à relire.

- **Fournisseur** : un fournisseur Pi à clé API (OpenAI, Anthropic, Google Gemini, OpenRouter, Mistral et d’autres), **Abonnement ChatGPT** ou **Point de terminaison compatible OpenAI**.
- **Modèle** : choisissez dans la liste de Pi pour ce fournisseur ou saisissez tout ID de modèle accepté par le fournisseur, par exemple `gpt-5.4`. La liste accompagne la version de Pi fournie par ADORE et se lit sans accès à internet. Il n’y a pas de modèle universel par défaut.
- **Abonnement ChatGPT** : Pi utilise le compte ChatGPT Plus ou Pro auquel ce serveur ADORE est connecté, voir [Se connecter avec ChatGPT](#chatgpt). La liste propose les modèles servis par un abonnement ChatGPT, par exemple `gpt-5.6-luna`.

**Enregistrer** sauvegarde les paramètres ensemble après confirmation des effets importants ; voir [Paramètres du projet](/help/settings#editing) pour suspendre la surveillance. ADORE lance un nouveau processus Pi par étape et l’arrête en cas de délai dépassé ou d’annulation.

## Point de terminaison compatible OpenAI {#endpoint}

Pour un modèle servi sur votre propre réseau, comme LM Studio, Ollama ou vLLM, choisissez **Point de terminaison compatible OpenAI** et renseignez :

- **URL de base du point de terminaison** : l’adresse telle que Pi la voit. Pour **Conteneur**, l’adresse est vue depuis le conteneur ; pour une tâche locale, depuis le serveur.
- **Type d’API du point de terminaison** : `openai-completions` pour LM Studio, Ollama et vLLM ; `openai-responses`, `anthropic-messages` et `google-generative-ai` sont aussi acceptés.
- **Modèle** : l’ID du modèle servi par le point de terminaison.

Une clé de point de terminaison est facultative : enregistrez-la sous Authentification sous ADORE_ENDPOINT_API_KEY. ADORE décrit le point de terminaison à Pi pour chaque tâche ; l’adresse ne contient jamais de nom d’utilisateur, de mot de passe ni de requête. Avec l’[accès Internet](#internet) désactivé, ADORE autorise lui-même l’adresse du point de terminaison. Le point de terminaison est disponible en conteneur et sur le serveur.

## Authentification {#credentials}

Ouvrez **Authentification** dans le même groupe.

- **Clé API du fournisseur.** Le panneau indique la variable requise par le fournisseur configuré, par exemple OPENAI_API_KEY pour OpenAI ou ANTHROPIC_API_KEY pour Anthropic. Saisissez la **Clé API** et choisissez **Enregistrer la clé API**. ADORE la conserve en privé dans le magasin d’identifiants du projet sur le serveur, jamais dans le fichier de configuration, ne la transmet à Pi que par cette variable et ne l’affiche plus jamais ; **Déconnecter la clé API du projet** la supprime. Changer une clé exige la surveillance suspendue, un projet inactif et aucune proposition en attente, et ne teste pas la clé.
- **Projets sur le serveur.** Enregistrez la clé du fournisseur sous **Clé API du fournisseur** si nécessaire. ADORE ignore la connexion personnelle à Pi. Utilisez la [connexion ChatGPT](#chatgpt) partagée pour un abonnement sous Windows ou Linux, y compris WSL2.
- **Valeurs gérées par l’environnement.** Une variable déjà définie dans l’environnement du serveur ADORE porte la mention **Définie sur le serveur ADORE ; gestion externe**. L’interface web ne peut pas l’écraser.
- **Clé de recherche web.** Avec l’accès Internet activé et la recherche web Brave ou Tavily, le panneau liste aussi BRAVE_API_KEY ou TAVILY_API_KEY, enregistrée de la même manière, aussi pour un abonnement ChatGPT.
- **Variables d’identification supplémentaires.** Noms uniquement (**Ajouter une variable d’identification**) de secrets supplémentaires reçus par Pi en plus de la clé du fournisseur ; la plupart des projets n’en ont pas besoin.

Les valeurs d’identifiants n’apparaissent jamais dans le fichier de configuration, les revues, les journaux d’audit, les journaux ou les exports.

## Se connecter avec ChatGPT {#chatgpt}

Un seul compte ChatGPT Plus ou Pro sert tous les projets de ce serveur ADORE dont le fournisseur est **Abonnement ChatGPT**. Les administrateurs se connectent dans **Authentification** d’un tel projet ; ADORE exécute la connexion OpenAI de Pi, le serveur n’a donc besoin d’aucun navigateur.

Sur le serveur natif, Pi peut recevoir directement le retour du navigateur et ADORE affiche automatiquement la connexion. Sinon, suivez les étapes manuelles ci-dessous.

1. Choisissez **Se connecter avec ChatGPT**.
2. Ouvrez **Ouvrir la page de connexion ChatGPT** sur votre ordinateur et connectez-vous avec le compte ChatGPT. Le lien est valable 15 minutes.
3. Le navigateur affiche ensuite une page d’erreur sur `127.0.0.1:1455`. C’est normal : copiez l’adresse complète de sa barre d’adresse.
4. Collez-la dans **Adresse de redirection** et choisissez **Terminer la connexion**.

L’état est **Connecté**, **Non connecté** ou **Reconnectez-vous**. **Reconnectez-vous** signifie qu’OpenAI n’accepte plus la connexion enregistrée ; les tâches échouent jusqu’à ce qu’un administrateur se reconnecte. Une adresse issue d’un lien plus ancien est refusée et la connexion reste en attente ; **Annuler** y met fin. Quand OpenAI refuse le compte, par exemple parce que son abonnement ne peut pas être partagé, la connexion se termine avec ce motif. **Déconnecter ChatGPT** supprime la connexion enregistrée.

La connexion reste dans un dossier privé du serveur ADORE. Avant chaque étape, ADORE en tire un jeton d’accès récent, valable environ une heure, et ne transmet que ce jeton à Pi ; la connexion elle-même n’entre jamais dans le conteneur de la tâche. Les projets ChatGPT s’exécutent en conteneur ou nativement sous Windows/Linux, y compris WSL2. La connexion native utilise Pi géré par ADORE sans Docker ; les conteneurs utilisent l’image actuelle d’ADORE. La durée par étape est limitée à 3000 secondes dans les deux modes. Seuls les administrateurs voient ou modifient la connexion ; le journal d’audit nomme l’action, jamais un jeton ni une adresse.

> ADORE est gratuit aujourd’hui. Le proposer comme service hébergé ou payant avec la connexion ChatGPT exigerait d’abord le formulaire d’intérêt d’OpenAI.

## Tester la connexion IA {#test-connection}

Les administrateurs choisissent **Tester la connexion IA** sous **Connexion IA**. Le test démarre Pi une fois dans un conteneur temporaire, ou dans un dossier temporaire pour Pi installé sur le serveur, lui demande d’exécuter une commande shell puis de répondre par un texte fixe, et peut entraîner des frais du fournisseur. Le projet doit être inactif, avec des paramètres enregistrés valides et aucune proposition en attente ; pour un projet en conteneur, l’image configurée doit exister sur le serveur.

Le résultat est **Modèle IA connecté** seulement si la commande shell a été exécutée et que la réponse est arrivée. Sinon **Connexion IA non vérifiée** s’accompagne de conseils propres pour : aucun identifiant enregistré, aucune connexion ChatGPT, un abonnement ChatGPT qui ne peut pas être partagé, une limite d’utilisation ChatGPT atteinte, une clé refusée par le fournisseur, un fournisseur ou point de terminaison que Pi n’a pas pu joindre, un modèle inconnu du fournisseur ou du point de terminaison, une limite de débit, une autre erreur du fournisseur, un délai dépassé, une image ou un Pi manquant, ou une commande shell que Pi n’a pas pu exécuter. Aucune tâche n’est lancée. Le résultat enregistré est lié au fournisseur, au modèle, aux paramètres et aux identifiants actuels et apparaît dans les vérifications de l’hôte du Résumé. Les développeurs le voient mais ne peuvent pas lancer le test.

## Accès Internet de l’agent {#internet}

**Accès Internet de l’agent** dans Paramètres → Agent et modèle décide de ce que le conteneur d’une tâche peut atteindre. Il est **Désactivé** par défaut.

- **Désactivé** : le conteneur n’atteint que le fournisseur du modèle. ADORE autorise lui-même les adresses du fournisseur, pour un point de terminaison compatible OpenAI son adresse, par un proxy réseau propre à chaque tâche. La recherche web, la lecture de pages et les téléchargements comme `curl`, `npm install` ou `pip install` échouent, et Pi en est informé.
- **Activé** : le conteneur dispose d’un réseau ouvert. Pi peut chercher sur le web, lire des pages et télécharger des bibliothèques avec `curl`, `npm` ou `pip`.

**Recherche web** choisit le service de recherche quand l’accès est activé : **Exa (sans clé)**, par défaut, **Brave (clé requise)**, **Tavily (clé requise)** ou **Aucune** (ni recherche web ni lecture de pages). Pour Brave ou Tavily, enregistrez BRAVE_API_KEY ou TAVILY_API_KEY sous **Authentification**.

> Avec l’accès Internet activé, une page web malveillante pourrait tenter de faire envoyer par l’agent sa clé API ou son jeton ChatGPT. Préférez des clés limitées et de courte durée.

Utilisez **Enregistrer** pour les deux paramètres et confirmez les effets importants. Avec l’accès Internet désactivé, l’image du proxy doit exister sur le serveur ADORE ; **Vérifier les prérequis de l’hôte** la signale, ainsi que la clé de recherche si elle est nécessaire. Pour un projet installé sur le serveur, le commutateur est affiché **Non appliqué** : Pi atteint tout ce que le serveur atteint.

## Où s’exécutent les tâches {#where-jobs-run}

| | Conteneur | Exécution locale native |
|---|---|---|
| S’exécute dans | Un conteneur Docker ou Podman temporaire sur le serveur ADORE | Le serveur ADORE lui-même, sous le compte du système d’exploitation du service, dans un worktree dédié |
| Environnement | Une image de projet préparée par l’administrateur | Les outils, versions et bibliothèques que vous installez vous-même sur ce serveur |
| Connexion | La clé API du fournisseur ou, pour un abonnement ChatGPT, un jeton d’accès de courte durée issu de la connexion ChatGPT du serveur | La clé du fournisseur ou un jeton temporaire de la connexion ChatGPT du serveur |
| Réglages de l’agent | Le Pi intégré à l’image, avec des réglages fixés par ADORE ; les réglages et compétences Pi personnels ne sont pas lus | Pi géré par ADORE, avec ses propres réglages et extensions |
| Isolation | Conteneur ; avec l’accès Internet désactivé, il n’atteint que le fournisseur du modèle | Uniquement le worktree ; les commandes peuvent atteindre tout ce que le compte peut atteindre, utilisez donc un compte dédié aux privilèges minimaux |
| Choisi | **Exécution** → **Conteneur**, par défaut, à l’étape 2 de l’inscription ou dans Paramètres → Agent et modèle | **Exécution** → **Installé sur le serveur**, ou le profil du serveur ou l’inscription TOML |

**Installé sur le serveur** utilise le compte système actuel et propose un **PATH des outils du projet** facultatif. La commande de lancement est fixe.

**Vérifier les prérequis de l’hôte** ignore le moteur de conteneur et vérifie Node, l’installation gérée de Pi et les identifiants du fournisseur choisi.

## Installer Pi sur le serveur {#installed-executors}

Exécutez `adore pi install` et `adore pi verify` sur le serveur ADORE sous son compte de service. Utilisez Node 22.23.4 ou une version ultérieure de la série 22.x avec npm. Si Node est hors du PATH du service, indiquez son chemin absolu dans `ADORE_NODE` sur le serveur.

Relancez `adore pi install` lorsqu’une nouvelle version d’ADORE fixe une autre version de Pi. Aucun Pi global n’est nécessaire ; les réglages et extensions personnels sont ignorés.

Windows utilise l’outil PowerShell ; sous Linux, l’administrateur du serveur configure une racine cgroup v2 déléguée. Pi ne demande pas d’autorisation. Utilisez un compte système dédié.

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

Dans Paramètres, modifiez **Moteur de conteneur** pour choisir Docker ou Podman détecté sur le serveur, y compris dans WSL sous Windows. Choisissez **Commande de conteneur manuelle** pour saisir la vôtre, puis utilisez **Enregistrer**. La vérification des prérequis recherche Pi dans l’image choisie.

Pour une commande WSL personnalisée, placez `--` ou `--exec` avant la commande du conteneur. Les entrées Docker et Podman standard sont traitées automatiquement.

Confirmez ensuite avec **Vérifier les prérequis de l’hôte** et **Tester la connexion IA**.

## Paquets système {#system-packages}

Un administrateur peut préparer **Autoriser l’installation de paquets système par l’agent** dans **Paramètres → Agent et modèle**. Désactivé par défaut, ce droit concerne seulement les conteneurs. Pi peut installer directement avec `sudo -n`, lire les résultats et s’adapter dans les limites de la tâche. **Accès Internet de l’agent** reste distinct ; désactivé, les sources externes exigent un hôte autorisé. Utilisez une image avec sudo, suspendez la surveillance et attendez la fin du travail actif avant d’appliquer, puis lancez une nouvelle tâche. Les paquets restent dans ce conteneur et ne modifient pas l’image.
