# Exécuteurs et modèles

Un exécuteur est le couple qu’ADORE lance pour chaque tâche : un agent de programmation et le modèle d’IA qu’il utilise. Les administrateurs choisissent les deux dans les Paramètres d’un projet.

## Ce qu’est un exécuteur {#what}

Pour chaque tâche, ADORE démarre l’agent de programmation du projet dans une copie de travail isolée, et l’agent parcourt les étapes AEGIS du dépôt avec le modèle configuré. Les agents sont OpenCode, Pi, Codex et Qwen Code. L’agent ne commit jamais, ne pousse jamais et ne voit jamais les identifiants de la forge ; c’est ADORE qui s’en charge. ADORE n’installe aucun agent et ne récupère aucune liste de modèles : l’agent doit donc déjà exister dans l’image du projet ou sur le serveur. Les changements ne s’appliquent qu’aux nouvelles tâches.

## Choisir l’agent et le modèle {#agent-and-model}

Ouvrez **Paramètres → Agent et modèle**. Les lignes sont **Agent de programmation par défaut**, **Commande de lancement de l’exécuteur** et **Identifiant du modèle de l’exécuteur**.

Les administrateurs choisissent **Modifier** sur la ligne de l’agent de programmation par défaut et sélectionnent OpenCode, Pi, Codex ou Qwen Code. La sélection d’un agent charge sa commande et son modèle enregistrés, ou le préréglage de commande documenté. Saisissez vous-même l’ID du modèle pour un nouvel agent : l’ID que votre agent et votre fournisseur acceptent, généralement `provider/model`. Il n’existe aucun défaut universel. La commande de lancement doit contenir `{prompt}`. **Préparer le candidat** examine ensemble l’agent, la commande et le modèle, et **Appliquer** les écrit en un seul changement. Prévoyez de suspendre d’abord la surveillance ; voir [Paramètres du projet](/help/settings#editing).

## Authentification {#credentials}

Ouvrez **Authentification** dans le même groupe. Un projet peut s’authentifier de trois façons.

- **Clés API du fournisseur.** Choisissez une **Variable d’identification** (par exemple OPENAI_API_KEY ou ANTHROPIC_API_KEY), saisissez la **Clé API** et choisissez **Enregistrer la clé API**. ADORE la conserve de façon privée sur le serveur et ne l’affiche plus jamais ; **Déconnecter la clé API du projet** la supprime. La variable doit d’abord figurer sous **Variables d’identification autorisées**, qui ne contient que des noms (**Ajouter une variable d’identification**). Changer une clé exige une surveillance en pause, un projet inactif et aucun changement en attente, et ne teste pas la clé.
- **Abonnement ou connexion de l’hôte.** L’agent utilise sa propre connexion sur le serveur ADORE sous le compte de service, configurée en dehors de l’interface web (le volet **Connexion par abonnement ou navigateur** indique la commande). **Utiliser la connexion de l’agent de l’hôte** est une passerelle pilote qui copie cette connexion dans le conteneur, pour OpenCode et Codex uniquement. Un abonnement ChatGPT n’est pas une clé API OpenAI.
- **Valeurs gérées par l’environnement.** Une variable déjà définie dans l’environnement du serveur ADORE porte la mention **Définie sur le serveur ADORE ; gestion externe**. L’interface web ne peut pas l’écraser.

Les valeurs d’identifiants n’apparaissent jamais dans les revues, les enregistrements d’audit ou les exports. Une liste de variables vide est valide avec une connexion existante sur le serveur, et aussi en mode api-key quand l’image ou l’exécuteur installé se connecte seul.

## Tester la connexion IA {#test-connection}

Les administrateurs choisissent **Tester la connexion IA** sous **Connexion IA**. Cela envoie une courte requête via l’agent configuré dans un conteneur temporaire, ou dans un dossier temporaire pour un agent installé sur le serveur, ce qui peut entraîner des frais du fournisseur. Le projet doit être inactif, avec des paramètres enregistrés valides et aucun changement en attente ; pour un projet en conteneur, l’image doit contenir Python et l’agent.

Le résultat est **Modèle IA connecté** ou **Connexion IA non vérifiée**, avec des indications en cas de délai dépassé, d’image ou d’agent absent, d’identifiants incorrects, de modèle indisponible ou d’une commande shell que l’agent n’a pas pu exécuter. Pour OpenCode, Pi ou Codex installés sur le serveur, la requête demande aussi à l’agent d’exécuter une commande shell, et le résultat n’est connecté que si cette commande s’est exécutée ; sinon le test prouve uniquement l’accès au modèle. Il ne démarre aucune tâche. Le résultat enregistré est lié au modèle, aux paramètres et aux identifiants actuels et apparaît dans les contrôles de l’hôte du Résumé. Les développeurs le voient mais ne peuvent pas lancer le test.

## Où s’exécutent les tâches {#where-jobs-run}

| | Conteneur | Exécution locale native |
|---|---|---|
| S’exécute dans | Un conteneur Docker ou Podman temporaire sur le serveur ADORE | Le serveur ADORE lui-même, sous le compte du système d’exploitation du service, dans un worktree dédié |
| Environnement | Une image de projet préparée par l’administrateur | Les outils, versions et bibliothèques que vous installez vous-même sur ce serveur |
| Connexion | Clés API listées ou connexion de l’hôte | La connexion existante de l’agent sur ce compte, réutilisée telle quelle |
| Réglages de l’agent | Les réglages de l’image, plus le [point d’accès local pour OpenCode](#local-endpoint) s’il est défini | Pour OpenCode, un dossier de réglages géré par ADORE : agents, fournisseurs, extensions et autorisations de votre dossier de réglages OpenCode personnel ne sont pas utilisés, `git push` et les outils de la forge sont bloqués, et les dossiers `.opencode` et `.agents/skills` du dossier personnel du compte s’appliquent toujours |
| Isolation | Conteneur avec une politique réseau | Uniquement le worktree ; les commandes peuvent atteindre tout ce que le compte peut atteindre, utilisez donc un compte dédié aux privilèges minimaux |
| Choisi | **Exécution** → **Conteneur**, par défaut, à l’étape 2 de l’inscription ou dans Paramètres → Agent et modèle | **Exécution** → **Installé sur le serveur**, ou le profil du serveur ou l’inscription TOML |

Les modifications dans Paramètres passent par **Préparer le candidat**, la revue et **Appliquer**. **Installé sur le serveur** affiche la commande native de l’exécuteur et les champs du compte local (compte `current`, dossier personnel, PATH et, sous Linux, la racine cgroup) avec l’avis d’exécution locale.

Les contrôles de l’hôte pour un projet local ignorent le moteur de conteneur et vérifient l’agent natif et sa connexion.

## Détecter les exécuteurs installés {#installed-executors}

Quand vous choisissez **Installé sur le serveur**, ADORE détecte OpenCode, Pi, Codex et Qwen Code sur l’hôte d’exécution. **Exécution sous** identifie la machine et le compte ; pour une installation portable sur ordinateur, il s’agit de l’ordinateur exécutant ADORE. La première installation détectée complète une commande vide ou standard pendant l’inscription. **Installations détectées** permet de choisir une autre installation. Les commandes enregistrées et les modifications manuelles sont conservées.

ADORE utilise automatiquement le compte de son processus, son dossier personnel, le PATH des outils et la connexion enregistrée de l’exécuteur. Il lance un nouveau processus, sans se connecter à un terminal ouvert. Un service utilise son compte de service.

La détection démarre automatiquement lorsque l’exécution locale est choisie ; changer d’agent utilise la liste détectée. Ouvrez **Avancé** puis **Détecter les exécuteurs installés** pour l’actualiser. Ouvrez **Avancé**, saisissez **Chemin de l’exécutable sur l’hôte ADORE** puis **Utiliser l’exécutable**, ou modifiez **Commande de lancement de l’exécuteur**. Windows utilise un vrai `.exe` ; les agents Node nécessitent la commande Node/JavaScript installée. La détection lit les emplacements, sans installation, connexion ni test du modèle.

Ouvrez **Avancé** pour la commande complète, un chemin d’exécutable manuel, les valeurs de dossier/PATH et la délégation cgroup Linux. Laissez dossier et PATH vides pour les valeurs automatiques. PATH désigne les dossiers des outils, pas un exécutable. Les noms de compte dans Paramètres vérifient l’identité actuelle sans changer d’utilisateur.

## Image du projet {#project-image}

Pour un projet en conteneur, Paramètres → Agent et modèle affiche **L’exécuteur fonctionne dans un conteneur**, l’**Image utilisée** et un volet **Instructions de préparation de l’environnement**. L’interface web ne définit ni ne construit l’image, et l’ajout d’un Dockerfile au dépôt ne lance aucune construction. L’administrateur la prépare sur le serveur :

1. Créer `executor/Dockerfile` dans le dépôt, à partir de l’image de base d’ADORE, sans identifiants. L’image a besoin de Python, de sh et de l’agent choisi.
2. La construire avec Docker ou Podman du serveur et vérifier les versions de l’agent et des outils.
3. Sélectionner l’image dans l’interface web comme décrit ci-dessous ou, avec la surveillance en pause et aucune tâche active, définir `execution.backend`, `container.image` et `container.required_tool_checks` dans le `config.toml` du projet (les administrateurs en voient le chemin dans le volet), puis valider le profil.

```
FROM adore-executor-base:1.0.0
USER root
# RUN ... install the project's system tools
USER adore
```

Pour utiliser l’image, choisissez le **Moteur de conteneur** (Docker ou Podman) et l’**Image de l'exécuteur** à l’étape 2 de l’inscription, ou modifiez ces mêmes lignes dans Paramètres. L’image est un champ libre avec des suggestions tirées des images du serveur ADORE pour ce moteur (administrateurs uniquement) ; un avis s’affiche quand l’image saisie n’est pas sur le serveur, un autre quand la liste ne peut pas être lue. Le choix d’un exécuteur propose une image dont l’étiquette commence par le nom de l’exécuteur suivi d’un tiret (par exemple `pi-`), de préférence `adore-executor-base:` ; elle ne remplace que l’ancienne valeur par défaut ou une proposition précédente, jamais une valeur saisie.

Pour une commande WSL personnalisée, placez `--` ou `--exec` avant la commande du conteneur. Les entrées Docker et Podman standard sont traitées automatiquement.

Confirmez ensuite avec **Vérifier les prérequis de l’hôte** et **Tester la connexion IA**.

## Point d’accès local pour OpenCode {#local-endpoint}

Pour un projet en conteneur qui utilise OpenCode, les administrateurs voient aussi **URL du serveur compatible OpenAI** dans Agent et modèle, pour un modèle servi sur votre propre réseau. Saisissez l’URL, une **Référence de variable d'identification** facultative, le **Délai maximal de la requête (secondes)** et, pour HTTPS avec une autorité de certification privée, le **Fichier CA dans l'image d'exécution**. Le protocole est fixé à OpenAI chat completions. **Préparer le candidat** examine ensemble l’URL et le modèle.

L’URL doit être joignable depuis l’intérieur du conteneur de l’exécuteur, où localhost désigne le conteneur lui-même, et l’image doit déjà contenir le paquet du fournisseur. L’enregistrement ne teste pas la joignabilité et n’ajoute aucun repli vers le cloud ; **Vérifier les prérequis de l’hôte** teste un appel d’outil en flux depuis un conteneur temporaire.

## Résultats des contrôles locaux {#local-check-results}

Dans Résumé, **Vérifier les prérequis de l’hôte** vérifie la version de l’exécuteur installé et sa connexion existante. L’exécution locale affiche un objectif concis et la cause mesurée : exécutable, version/code de sortie, délai, compte, identifiants, droits, préparation ou arrêt des processus. Les anciens résultats sans cause enregistrée demandent un nouveau contrôle.

Utilisez séparément **Tester la connexion IA** dans Paramètres → Agent et modèle. En local, il utilise la commande native enregistrée et la connexion du compte ADORE dans un dossier temporaire vide. Des frais peuvent s’appliquer. Le résultat distingue identifiants refusés, modèle indisponible, connexion/délai et sortie invalide ou incomplète. Corrigez cette cause avant de répéter le contrôle concerné ; une connexion réussie ne prouve pas une tâche complète ni ses outils.

## Paquets système de l’agent {#system-packages}

**Autoriser l’installation de paquets système par l’agent**

Dans Paramètres → Agent et modèle, les administrateurs activent cette permission distincte avec Préparer le candidat et Appliquer le changement. Désactivée par défaut, elle concerne les projets en conteneur. Reconstruisez ou choisissez une image compatible avec sudo, puis lancez une nouvelle tâche. L’agent exécute directement les commandes, analyse les échecs et s’adapte dans les limites de la tâche.

L’accès réseau reste distinct : open autorise les sources accessibles, allowlist-proxy les domaines HTTP/HTTPS permis, et none uniquement les sources locales disponibles. Les scripts de paquets ont des droits administratifs dans le conteneur ; les dossiers montés restent partagés avec le serveur. Les paquets système restent dans le même conteneur à la reprise ; un nouveau conteneur exige une nouvelle évaluation et installation.
