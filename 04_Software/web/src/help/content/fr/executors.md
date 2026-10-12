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

Les valeurs d’identifiants n’apparaissent jamais dans les revues, les enregistrements d’audit ou les exports. Une liste de variables vide est valide avec une connexion existante sur le serveur.

## Tester la connexion IA {#test-connection}

Les administrateurs choisissent **Tester la connexion IA** sous **Connexion IA**. Cela envoie une courte requête via l’agent configuré dans un conteneur temporaire, ce qui peut entraîner des frais du fournisseur. Le projet doit être inactif, avec des paramètres enregistrés valides et aucun changement en attente ; l’image doit contenir Python et l’agent.

Le résultat est **Modèle IA connecté** ou **Connexion IA non vérifiée**, avec des indications en cas de délai dépassé, d’image ou d’agent absent, d’identifiants incorrects ou de modèle indisponible. Il prouve uniquement l’accès au modèle, pas la prise en charge des outils, et ne démarre aucune tâche. Le résultat enregistré est lié au modèle, aux paramètres et aux identifiants actuels et apparaît dans les contrôles de l’hôte du Résumé. Les développeurs le voient mais ne peuvent pas lancer le test.

## Où s’exécutent les tâches {#where-jobs-run}

| | Conteneur | Exécution locale native |
|---|---|---|
| S’exécute dans | Un conteneur Docker ou Podman temporaire sur le serveur ADORE | Le serveur ADORE lui-même, sous le compte du système d’exploitation du service, dans un worktree dédié |
| Environnement | Une image de projet préparée par l’administrateur | Les outils, versions et bibliothèques que vous installez vous-même sur ce serveur |
| Connexion | Clés API listées ou connexion de l’hôte | La connexion existante de l’agent sur ce compte, réutilisée telle quelle |
| Isolation | Conteneur avec une politique réseau | Uniquement le worktree ; les commandes peuvent atteindre tout ce que le compte peut atteindre, utilisez donc un compte dédié aux privilèges minimaux |
| Choisi | Par défaut pour les projets ajoutés ici | En dehors de l’interface web, dans le profil du serveur ou par inscription TOML |

Les contrôles de l’hôte pour un projet local ignorent le moteur de conteneur et vérifient l’agent natif et sa connexion.

## Image du projet {#project-image}

Pour un projet en conteneur, Paramètres → Agent et modèle affiche **L’exécuteur fonctionne dans un conteneur**, l’**Image utilisée** et un volet **Instructions de préparation de l’environnement**. L’interface web ne définit, ne construit ni ne sélectionne l’image, et l’ajout d’un Dockerfile au dépôt ne lance aucune construction. L’administrateur procède ainsi sur le serveur :

1. Créer `executor/Dockerfile` dans le dépôt, à partir de l’image de base d’ADORE, sans identifiants. L’image a besoin de Python, de sh et de l’agent choisi.
2. La construire avec Docker ou Podman du serveur et vérifier les versions de l’agent et des outils.
3. Avec la surveillance en pause et aucune tâche active, définir `execution.backend`, `container.image` et `container.required_tool_checks` dans le `config.toml` du projet (les administrateurs en voient le chemin dans le volet), puis valider le profil.

```
FROM adore-executor-base:1.0.0
USER root
# RUN ... install the project's system tools
USER adore
```

Confirmez ensuite avec **Vérifier les prérequis de l’hôte** et **Tester la connexion IA**.

## Point d’accès local pour OpenCode {#local-endpoint}

Pour un projet en conteneur qui utilise OpenCode, les administrateurs voient aussi **URL du serveur compatible OpenAI** dans Agent et modèle, pour un modèle servi sur votre propre réseau. Saisissez l’URL, une **Référence de variable d'identification** facultative, le **Délai maximal de la requête (secondes)** et, pour HTTPS avec une autorité de certification privée, le **Fichier CA dans l'image d'exécution**. Le protocole est fixé à OpenAI chat completions. **Préparer le candidat** examine ensemble l’URL et le modèle.

L’URL doit être joignable depuis l’intérieur du conteneur de l’exécuteur, où localhost désigne le conteneur lui-même, et l’image doit déjà contenir le paquet du fournisseur. L’enregistrement ne teste pas la joignabilité et n’ajoute aucun repli vers le cloud ; **Vérifier les prérequis de l’hôte** teste un appel d’outil en flux depuis un conteneur temporaire.
