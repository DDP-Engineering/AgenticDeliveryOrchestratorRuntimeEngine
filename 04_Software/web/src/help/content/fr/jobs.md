# Cycle de vie d’une tâche

Une tâche est le travail qu’ADORE effectue pour un ticket, de la prise en charge à une modification fusionnée. Cet article présente ses étapes et les moments où vous intervenez. Les étiquettes et l’éligibilité sont décrites dans [Tickets et prise en charge automatique](/help/tickets).


Confirmez **Annuler**. Le nettoyage tente de supprimer l’environnement et le dossier de travail, y compris les changements non publiés ; des ressources peuvent rester. L’état et les preuves restent. Supprimer une tâche est distinct.

Ouvrez **Actions du travail**, près de l’étape actuelle, pour **Réessayer**, **Annuler** ou la reprise confirmée dans un nouveau travail si disponible. Seules les commandes autorisées pour ce travail sont affichées.

Le démarrage est confirmé après l’enregistrement durable et la prise en charge de la tâche. Celle-ci garde sa propre progression et son résultat. Une commande en attente ou en cours ne confirme pas son admission. L’annulation est confirmée uniquement après l’arrêt de la tâche avec un résultat enregistré. La mise en attente ou un signal d’arrêt ne confirme pas l’annulation. Si le résultat est incertain, vérifiez la tâche avant de réessayer.

Chaque projet a une limite de tâches simultanées, commune au démarrage, aux reprises, aux nouveaux départs et au travail repris. La pause arrête la prise en charge automatique et conserve le démarrage explicite. Réduire la limite laisse les tâches actives continuer. Les commandes en attente et les attentes stabilisées de réponse, approbation ou revue n’utilisent pas d’exécuteur ; l’initialisation et le nettoyage gardent leur place jusqu’à libération sûre. L’attente avant exécution ne consomme pas de travail actif.

Les tâches simultanées ont leurs propres dossiers de travail, ressources, identifiants et sorties. Annuler une tâche laisse les autres actives. Les mises à jour communes peuvent attendre ; les agents prêts continuent.

Les projets avancent indépendamment. Avec une limite de deux, deux tâches peuvent s’exécuter ensemble et le démarrage suivant attend une place. Arrêter l’application arrête ses workers et tâches ; un résultat interrompu incertain doit être vérifié avant de réessayer explicitement.

Après une baisse de la limite, les tâches admises mais non démarrées attendent une place selon la nouvelle limite. Les tâches déjà exécutées continuent, même au-delà de cette limite, et le nettoyage garde sa place jusqu’à libération sûre. Les paramètres des autres projets et l’administration du serveur restent accessibles.

## Étapes {#stages}

ADORE exécute les étapes AEGIS une à une, chaque tentative dans une session d’exécuteur neuve. Les exécuteurs ne poussent jamais, n’ouvrent jamais de MR/PR et ne fusionnent jamais.

| Étape | Ce qui se passe |
|---|---|
| Cadrage | Le périmètre est convenu et l’exécuteur consigne les exigences existantes qui couvrent le travail. |
| Spécification | L’exigence est rédigée. |
| Conception | Une courte note de conception est rédigée pour les travaux non triviaux. |
| Développement | L’agent implémente le ticket et choisit les contrôles adaptés selon les instructions du dépôt. |
| Validation | L’agent rapporte les contrôles selon les instructions du dépôt, y compris ceux réservés à la CI et non exécutés localement, puis clôt la tâche AEGIS. ADORE observe la fin sans relancer les tests. |

Spécification et Conception peuvent être consignées comme ignorées lorsque des exigences existantes couvrent déjà le travail. Après la Validation, la tâche affiche l’étape **Terminée** pendant l’attente d’approbation, la publication et la revue humaine. AEGIS peut revenir à toute étape précédente, dont Conception vers Spécification. ADORE enregistre l’étape et continue dans la même conversation du travail, dans les limites existantes. Une tâche terminée revient à Validation si une nouvelle vérification est nécessaire. Une étape dispose par défaut de trois tentatives échouées (**Tentatives échouées autorisées par étape**).

## Travaux directs {#direct-evidence}

La liste et le détail affichent **Workflow** : **AEGIS** ou **Direct**, selon le travail enregistré. Un travail direct utilise **Implémentation** (`build`), **Validation** (`validate`), puis **Terminée**. Il n’a ni Cadrage, Spécification, Conception, ni tâche AEGIS. La chronologie ne montre que les événements enregistrés, sans étapes terminées supposées.

**Dernière tentative enregistrée** indique le dernier lancement enregistré de l’agent. Sinon, **Tentative indisponible** apparaît. Les tests et contrôles sont rapportés par l’agent ; ADORE ne les exécute pas indépendamment.

**Implémentation** directe utilise la limite `build` dans `workflow.stage_timeout_overrides`, sinon `budgets.per_gate_timeout_seconds`. **Validation** (`validate`) enregistre le candidat pour approbation sans commande de test séparée.

## Clarification {#clarification}

Lorsque l’exécuteur demande des informations, ADORE publie un commentaire de clarification avec les questions et ajoute `agent-clarify`. Le travail indique l’attente de clarification. **Lire la question** ouvre la question dans **Détails du travail** ; **Répondre sur le ticket** utilise son emplacement enregistré.

Répondez par un commentaire normal sur le ticket, puis ajoutez `agent-answered`. Les deux sont nécessaires ; les commentaires d’ADORE lui-même ne comptent pas. ADORE retire les deux étiquettes et reprend. Les questions ne comptent pas comme des tentatives échouées. **Nombre maximal de tours de questions** (3 par défaut) limite le nombre de fois qu’une tâche peut poser des questions, et **Temps accordé à une réponse humaine** (72 heures par défaut) fait échouer la tâche à l’expiration.

## Approbation {#approval}

L’approbation humaine avant publication est activée par défaut. Les administrateurs peuvent modifier **Exiger une approbation humaine avant PR/MR** dans Paramètres. Si elle est désactivée, ADORE contrôle l’actualité du candidat et de la cible avant publication ; les tests du dépôt restent à la charge de l’agent.

Quand l’agent termine son workflow, ADORE enregistre le candidat, retire l’ancienne étiquette d’approbation et demande une nouvelle approbation humaine. Les contrôles du journal sont rapportés par l’agent.

Examinez-le, puis ajoutez de nouveau `agent-approved` ; seul un nouvel ajout compte. L’approbation est liée à ce candidat et au commit de la branche cible. Si l’un des deux change, l’approbation est caduque et ADORE intègre, valide et redemande. Cette attente n’a pas de minuterie. Le détail de la tâche propose **Examiner le candidat sur la forge**.

Si cette option est désactivée, ADORE vérifie le candidat validé et la cible puis publie sans attendre d’étiquette. ADORE ne fusionne jamais.

## Publication et revue {#review}

Après validation et approbation si requise, ADORE pousse la branche et ouvre la MR/PR vers la branche cible, demande une revue aux comptes indiqués dans **Demander une revue à**, et pose `agent-mr`. **État de la PR/MR à la publication** choisit Brouillon (par défaut) ou Prête pour revue. La tâche affiche **Publication** puis **Revue humaine**. ADORE ne fusionne jamais. Après la fusion par une personne, ADORE pose `agent-done`, la tâche affiche **Terminé**, et par défaut la branche distante est supprimée. Une MR/PR fermée sans fusion fait échouer la tâche.

Pour demander des modifications, un relecteur ajoute `agent-revise` sur la MR/PR. ADORE retire l’étiquette, démarre un nouveau travail sur la même branche (une nouvelle tâche pour AEGIS), puis répète la validation et une nouvelle approbation avant de pousser. **Nombre maximal de tours de révision** (5 par défaut) borne ce mécanisme. Une demande au-delà de la limite fait échouer la tâche.

Si les vérifications CI échouent sur la MR/PR, **Action en cas d’échec des vérifications CI de la PR/MR** décide : Réparation automatique (par défaut) démarre une révision, Notifier uniquement publie un commentaire, et Ignorer ignore l’état de la CI. Les réparations automatiques partagent le budget de révisions ; une fois celui-ci épuisé, ADORE publie un avis et la tâche reste en revue.

## Échec et reprise {#failures}

Lorsqu’une étape échoue, ADORE tient à jour un commentaire d’incident unique sur le ticket avec l’étape, la tentative, le code d’erreur, les preuves et la prochaine action ; si l’agent s’est arrêté sans faire avancer l’étape, les preuves montrent aussi ses dernières lignes de sortie d’erreur. Après la dernière tentative, il publie un commentaire final, pose `agent-failed`, arrête le conteneur, conserve le worktree et libère l’emplacement. Les autres causes sont un délai de réponse expiré, un ticket source supprimé et une limite dépassée comme le coût ou le nombre de fichiers modifiés. Fermer le ticket source pendant qu’une tâche attend l’annule.

Dans Tâches, une tâche échouée affiche **Échouées**, et son détail explique que les preuves de reprise sont conservées. **Réessayer** demande au worker de récupérer la tâche ; cela ne contourne ni la validation ni l’approbation requise. Dans la vue Tickets, Relancer remplace Démarrer. Retirer `agent-failed` ne relance rien. **Annuler** apparaît pour les tâches inachevées et demande au worker de s’arrêter et de nettoyer. Les tâches terminées ne peuvent pas être annulées. Les administrateurs et les développeurs attribués peuvent utiliser les deux. Une commande en file affiche sa progression, par exemple Commande en file ou Commande terminée. Une commande échouée ou incertaine indique aussi pourquoi, quand le moteur nomme une raison, et affiche les dernières lignes du moteur.

Pour les tâches locales, **Relancer** revérifie l’exécuteur installé et accepte un exécutable mis à jour ou un environnement hérité modifié sur le même ordinateur et compte. La tâche, le worktree, la branche, l’historique et les limites cumulées sont conservés. La surveillance automatique ne le fait pas. Les paramètres d’exécution modifiés ou les preuves de récupération corrompues doivent être corrigés. Si le redémarrage échoue, la commande indique l’échec et sa cause enregistrée : exécutable absent, version invalide, échec de commande ou délai dépassé. Ce contrôle de version n’envoie aucune requête au modèle ; utilisez **Tester la connexion IA** pour cela.

Lorsqu’une commande en conteneur dépasse sa limite, ADORE arrête ce conteneur avant toute autre commande. La prochaine tentative autorisée reprend le même conteneur avec ses dépendances et fichiers ; l’accès réseau reste inchangé. Si l’arrêt ou le redémarrage sûr ne peut être confirmé, la tâche échoue et conserve ses preuves à examiner avant de **Relancer**. Une préparation échouée conserve sa procédure de reprise explicite.

Les travaux en conteneur conservent l’image et la ressource choisies au démarrage, même sans préparation. Si cette ressource est remplacée, démarrez un nouveau travail. La préparation reste facultative.

## Abandonner et recommencer {#restart}

Pour une tâche échouée, **Abandonner et redémarrer avec AEGIS** ou **Abandonner et redémarrer sans AEGIS** supprime son état enregistré, sa copie de travail avec le travail non publié et sa branche distante propre inchangée. Lisez l’avertissement et confirmez. ADORE vérifie la propriété avant le nettoyage et démarre le même ticket ouvert avec les paramètres actuels seulement après un nettoyage réussi. La surveillance reste en pause si elle l’était. Les administrateurs et développeurs affectés peuvent utiliser cette action.

Réessayer ne corrige pas les changements de mode ou de paramètres stables ; les détails l’expliquent et proposent l’action confirmée. Restaurez les paramètres enregistrés pour conserver le travail. Réessayer peut toujours revalider les changements volatils de l’environnement natif, dont les variables processeur après redimensionnement d’une VM.

Les ressources étrangères, un autre ordinateur ou compte, les preuves corrompues ou une branche distante modifiée bloquent la récupération. Un nettoyage partiel conserve les preuves restantes sans nouvelle tâche. Si la tâche change après confirmation, actualisez ses détails et vérifiez à nouveau. Le verrou CLI peut appartenir au worker web : mettez la surveillance en pause dans le Résumé du projet et attendez la fin de la tâche bornée. Ne supprimez pas un verrou actif.

Si une ancienne tâche supprimée a laissé une branche sans checkpoint enregistré, ADORE la conserve et utilise une nouvelle génération. Un checkpoint connu modifié bloque toujours la récupération. Trois autres noms au maximum sont essayés et les règles du dépôt doivent autoriser un nom libre ; sinon la récupération s’arrête avant le nettoyage. Le résultat indique quand une ancienne branche est conservée.

## Suivre les tâches {#following-jobs}

Les lectures automatiques gardent les lignes, la consommation, les commandes du tableau et le détail ouvert visibles. **Actualiser** utilise la même lecture en arrière-plan ; **Dernière actualisation réussie** indique sa fin. Une panne de connexion temporaire de la liste ou de la consommation peut conserver l’instantané précédent avec un avertissement de péremption et **Réessayer**. Des preuves invalides ou un instantané de pagination expiré exigent toujours une reprise ou un retour à la première page ; des informations périmées n’autorisent pas les actions sur les tâches.

Utilisez **Travaux** dans la barre latérale ou l’onglet **Travaux** distinct du projet. Le tableau comporte les colonnes suivantes :

| Colonne | Contenu |
|---|---|
| Ticket | Numéro et titre ; ouvre le détail de la tâche. |
| Projet | Le projet propriétaire. |
| État | L’état, le Workflow enregistré, l’Étape courante, et un lien vers le ticket ou la MR/PR lorsqu’une personne doit agir. |
| Dernière activité | Heure du dernier événement enregistré. |
| Consommation | Jetons utilisés par la tâche. |

Cliquez sur un titre de colonne pour trier. **Rechercher des travaux** cherche dans les titres, numéros, projets, identifiants de tâche, état, étape ou résultat. Le filtre **État** propose Tâches actives, En attente, Revue humaine et Travaux terminés. La page s’actualise seule tant qu’elle est visible.

Le détail remplace sa liste d’origine. **Activité**, **Sessions de l’agent** et **Détails du travail** sont au-dessus du titre, avec **Afficher le ticket** et **Fermer** à droite. État, étape et workflow suivent le titre. Budgets et consommation occupent la colonne droite. Les actions de question, approbation et revue restent visibles si nécessaires. **Fermer** restaure la vue, le périmètre, la recherche, les filtres et la pagination.

**Activité** est un tableau paginé avec heure, activité, étape et session. Choisissez 10, 25, 50 ou Tout et utilisez Précédent/Suivant. **Ouvrir la conversation** ouvre la session exacte quand l’étape et la tentative identifient un seul lancement enregistré ; les événements sans lien certain n’ont pas de lien. Le retour conserve la page. Budgets et consommation occupent la colonne droite, sous le contenu sur petit écran.

## Historique des sessions de l’agent {#agent-sessions}

**Sessions de l’agent** ouvre la session actuelle ou la dernière session terminée. La conversation montre la consigne initiale, les réponses de l’agent, les messages utilisateur et les appels/résultats d’outils dépliables. Les réponses utilisent Markdown. Les messages apparaissent directement avec un seul auteur ; le raisonnement et les outils peuvent être dépliés. La consommation reste dans le panneau droit.

Pi conserve une conversation d’implémentation pour le travail entre étapes, reprises et corrections. Les processus peuvent redémarrer aux points de contrôle ; la conversation reprend avec son contexte et la compaction automatique de Pi. Le sélecteur montre toujours les tentatives enregistrées, avec leur nouvelle activité et consommation uniquement. Les revues indépendantes utilisent des contextes séparés si la politique du dépôt l’exige.

Session, son sélecteur et l’activité en direct partagent une ligne juste au-dessus de la conversation, sur sa largeur. La conversation tient dans la hauteur disponible et défile à l’intérieur à l’arrivée des messages. Les boutons d’envoi sont à droite du champ sur grand écran et dessous sur petit écran.

L’historique se charge progressivement sans raccourcir le texte conservé. Les nouveaux messages défilent automatiquement uniquement en bas ; **Nouveaux messages** permet d’y revenir. Le sélecteur conserve les autres tentatives et **Session actuelle** revient au travail en direct.

Les nouveaux lancements conservent explicitement les consignes envoyées et l’heure des messages. Les anciennes sessions montrent uniquement ce qui a été enregistré. Les droits des administrateurs et développeurs affectés restent identiques ; les coûts structurés restent réservés aux administrateurs.

**Agrandir** utilise toute la page pour les sessions. **Rétablir** ou Échap revient à la vue normale. La session choisie, les messages et le brouillon sont conservés.

### Envoyer des instructions {#instructions}

Saisissez un **Message à l’agent** au bas de la conversation actuelle. **Envoyer maintenant** soumet le message à la prochaine limite sûre ; **Mettre en attente** attend la fin du travail actuel. Entre les sessions, la mise en attente reste disponible pendant le travail. Les conversations historiques sont en lecture seule.

Le message apparaît dans la conversation avec **En attente**, **Reçu par l’agent** ou un échec. Reçu confirme la réception, pas la fin du travail. Les erreurs de saisie sont expliquées à l’envoi : 1 à 4000 caractères sans NUL et au plus 256 instructions conservées par travail.

Les instructions non confirmées restent en attente pour une session ultérieure. La réception confirmée est conservée dans le travail et publiée sur le ticket ; les échecs temporaires du commentaire sont réessayés séparément.

## Budgets du travail {#budgets}

Le détail affiche **Lancements de l’exécuteur** (par exemple 9 / 20) et **Travail actif (secondes)** avec les limites actuelles du projet, indépendamment des statistiques de jetons. À 90 %, il signale une limite proche ; à la limite, il demande de l’augmenter avant la reprise. La limite initiale est 20 dans l’inscription et `adore init`.

Les administrateurs peuvent suivre **Ajuster les budgets dans les paramètres du projet**, ouvrir **Implémentation**, modifier uniquement les budgets, choisir **Enregistrer** et confirmer les valeurs exactes. Cet enregistrement révisé est permis pendant une attente de clarification, sans conducteur actif ni opération inachevée. Les autres paramètres gardent leurs contrôles habituels ; les développeurs restent en lecture seule.

Les budgets sont relus avant chaque tentative, reprise ou relance. Une tentative en cours garde son délai. Le travail actif est cumulé entre relances, réponses et révisions ; l’attente est exclue. Augmenter une limite conserve le travail consommé, la tâche et la progression. Une tâche échouée par épuisement exige toujours **Relancer** après ajustement. Une configuration invalide ou absente bloque les tentatives suivantes jusqu’à correction.

Si les limites actuelles sont illisibles, le détail conserve la consommation, les preuves et les actions de reprise. Les limites affichent — avec un avis d’indisponibilité ; aucune valeur par défaut n’est supposée. Corrigez la configuration avant de relancer.

## Détails du travail et diagnostic {#operational-evidence}

**Détails du travail** affiche une seule fois le résultat enregistré, la **Branche**, le **Dernier commit publié** si disponible, le lien MR/PR et les tours de revue séparément. Une branche absente indique **Non enregistré**. Le commit publié correspond au dernier point de contrôle poussé et vérifié, pas à une empreinte de candidat.

Lorsqu’une clarification est requise, **Lire la question** ouvre cet onglet. La question utilise Markdown lisible, les liens dangereux sont inactifs et les images ne se chargent pas automatiquement. Les actions de réponse, approbation et revue restent visibles près de l’état si nécessaires. La question originale est dans **Diagnostic**.

**Diagnostic** est replié au départ. Ouvrez-le pour les identifiants internes du projet et du travail, les **Tentatives échouées à l’étape actuelle**, les preuves de tentative directe ou de préparation et la dernière sortie de l’exécuteur. Les tours de revue sont distincts des échecs de l’étape actuelle.

**Données indisponibles** nomme le ticket, l’historique, le titre ou l’heure d’activité seulement lorsque ces sources manquent. Il s’agit des preuves disponibles, pas des jetons consommés. La consommation reste à droite.

La dernière sortie de l’exécuteur présente stdout/stderr opérationnels normalisés, avec heure, tentative, étape et code de sortie. Le contenu privé est masqué ; au plus 500 enregistrements dans 64 Kio par flux sont conservés. Les preuves absentes ou corrompues sont signalées et une lecture modifiée propose Réessayer.

**Activité** est l’unique tableau d’événements. Le code publié est accessible par le lien MR/PR. Les détails utilisent les preuves sauvegardées sans créer de fichiers ni démarrer d’exécuteur.

## Capacité du projet {#project-capacity}

**Résumé** affiche la limite de travaux parallèles, les places libres et les travaux en attente avec les faits opérationnels du projet. Travaux et Tickets sont des onglets distincts sans sous-onglet Capacité. La page globale Travaux conserve son tableau Capacité avec limites, places libres, file et surveillance, ainsi que sa pagination.

La file compte les demandes soumises et les tâches admises attendant leur lancement, pas les tickets non demandés. Un projet plein ne bloque pas les autres. Les paramètres conservent **Vos dernières opérations** et leurs résultats ; En file et En cours ne signifient pas Confirmé.

Une limite réduite préparée retient déjà les nouveaux démarrages et reprises jusqu’à ce que l’occupation passe sous la limite ; les tâches déjà en cours continuent ; les réservations en file attendent une place d’exécution. Elle n’augmente jamais la limite active. L’application sûre attend les travaux inachevés ; la valeur enregistrée et le candidat restent visibles jusqu’à Enregistrer ou Abandonner les modifications.

## Choisir le workflow {#workflow-choice}

Dans **Actions du travail**, choisissez **Abandonner et redémarrer avec AEGIS** ou **Abandonner et redémarrer sans AEGIS** pour un nouveau travail, puis acceptez la courte confirmation du navigateur qui supprime le travail existant. AEGIS absent désactive son action. Tickets conserve le sélecteur **Workflow** avant **Démarrer**. Réessayer, la continuation et les corrections de revue conservent le workflow enregistré et la même conversation Pi.

## Redémarrer les travaux annulés {#restart-cancelled}

Pour le dernier travail annulé, choisissez **Redémarrer le travail** dans Tickets, sélectionnez **Workflow** et confirmez, ou choisissez **Redémarrer avec AEGIS** / **Redémarrer sans AEGIS** dans les actions du travail. ADORE applique les paramètres actuels et les contrôles habituels ; la surveillance suspendue reste suspendue.

La nouvelle exécution possède une identité, des ressources, une conversation et des budgets distincts. Le travail annulé, son activité, ses sessions enregistrées et son résultat restent lisibles. **Travail précédent** et **Nouveau travail** relient les exécutions ; un ancien travail déjà redémarré ne crée pas de doublon. La confirmation ouvre le nouveau travail après son admission durable.

Si le redémarrage n’est pas confirmé, actualisez Travaux ou Tickets et cherchez le nouveau travail avant de réessayer. L’absence de confirmation ne signifie pas que le nettoyage a échoué ou qu’aucun travail n’a été créé. Un redémarrage refusé est signalé séparément.

L’historique n’expire pas automatiquement. Un opérateur peut supprimer une ancienne exécution avec `adore delete RUN_ID --force`. La rétention d’audit ne supprime pas cet historique.
