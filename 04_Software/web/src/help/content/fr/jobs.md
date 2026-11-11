# Cycle de vie d’une tâche

Une tâche est le travail qu’ADORE effectue pour un ticket, de la prise en charge à une modification fusionnée. Cet article présente ses étapes et les moments où vous intervenez. Les étiquettes et l’éligibilité sont décrites dans [Tickets et prise en charge automatique](/help/tickets).


Confirmez **Annuler**. Le nettoyage tente de supprimer l’environnement et le dossier de travail, y compris les changements non publiés ; des ressources peuvent rester. L’état et les preuves restent. Supprimer une tâche est distinct.

## Étapes {#stages}

ADORE exécute les étapes AEGIS une à une, chaque tentative dans une session d’exécuteur neuve. Les exécuteurs ne poussent jamais, n’ouvrent jamais de MR/PR et ne fusionnent jamais.

| Étape | Ce qui se passe |
|---|---|
| Cadrage | Le périmètre est convenu et l’exécuteur consigne si la tâche suit le chemin complet ou le chemin rapide. |
| Spécification | L’exigence est rédigée. |
| Conception | Une courte note de conception est rédigée pour les travaux non triviaux. |
| Développement | Un test en échec vient d’abord, puis l’implémentation, jusqu’à ce que les tests passent. |
| Validation | Revue, suite de tests complète, contrôle strict et rapport AEGIS ; la tâche AEGIS se clôt. ADORE enregistre la validation terminée et demande l’approbation du candidat précis. |

Le chemin rapide exécute Cadrage, Développement et Validation. Après la Validation, la tâche affiche l’étape **Terminée** pendant l’attente d’approbation, la publication et la revue humaine. AEGIS peut revenir à toute étape précédente du chemin choisi, dont Conception vers Spécification. ADORE enregistre l’étape et continue dans une nouvelle session, dans les limites existantes. Une tâche terminée revient à Validation si une nouvelle vérification est nécessaire. Une étape dispose par défaut de trois tentatives échouées (**Tentatives échouées autorisées par étape**).

## Clarification {#clarification}

Lorsque l’exécuteur a besoin d’informations, ADORE publie un commentaire de ticket, « Clarification required for stage » (en anglais, tel que publié par ADORE), qui liste les questions, et pose `agent-clarify`. La tâche affiche **En attente de clarification**, et son détail propose **Répondre sur le ticket**.

Répondez par un commentaire normal sur le ticket, puis ajoutez `agent-answered`. Les deux sont nécessaires ; les commentaires d’ADORE lui-même ne comptent pas. ADORE retire les deux étiquettes et reprend. Les questions ne comptent pas comme des tentatives échouées. **Nombre maximal de tours de questions** (3 par défaut) limite le nombre de fois qu’une tâche peut poser des questions, et **Temps accordé à une réponse humaine** (72 heures par défaut) fait échouer la tâche à l’expiration.

## Approbation {#approval}

Lorsque la validation stricte réussit, ADORE retire `agent-approved`, publie les preuves sur le ticket et attend. La tâche affiche **En attente d'approbation** et le ticket conserve `agent-working`. Les preuves nomment le candidat exact et les écarts éventuellement consignés par l’exécuteur.

Examinez-le, puis ajoutez de nouveau `agent-approved` ; seul un nouvel ajout compte. L’approbation est liée à ce candidat et au commit de la branche cible. Si l’un des deux change, l’approbation est caduque et ADORE intègre, valide et redemande. Cette attente n’a pas de minuterie. Le détail de la tâche propose **Examiner le candidat sur la forge**.

## Publication et revue {#review}

Après l’approbation, ADORE pousse la branche et ouvre la MR/PR vers la branche cible, demande une revue aux comptes indiqués dans **Demander une revue à**, et pose `agent-mr`. **État de la PR/MR à la publication** choisit Brouillon (par défaut) ou Prête pour revue. La tâche affiche **Publication** puis **Revue humaine**. ADORE ne fusionne jamais. Après la fusion par une personne, ADORE pose `agent-done`, la tâche affiche **Terminé**, et par défaut la branche distante est supprimée. Une MR/PR fermée sans fusion fait échouer la tâche.

Pour demander des modifications, un relecteur ajoute `agent-revise` sur la MR/PR. ADORE retire l’étiquette, démarre une nouvelle tâche sur la même branche, puis répète la validation et une nouvelle approbation avant de pousser. **Nombre maximal de tours de révision** (5 par défaut) borne ce mécanisme. Une demande au-delà de la limite fait échouer la tâche.

Si les vérifications CI échouent sur la MR/PR, **Action en cas d’échec des vérifications CI de la PR/MR** décide : Réparation automatique (par défaut) démarre une révision, Notifier uniquement publie un commentaire, et Ignorer ignore l’état de la CI. Les réparations automatiques partagent le budget de révisions ; une fois celui-ci épuisé, ADORE publie un avis et la tâche reste en revue.

## Échec et reprise {#failures}

Lorsqu’une étape échoue, ADORE tient à jour un commentaire d’incident unique sur le ticket avec l’étape, la tentative, le code d’erreur, les preuves et la prochaine action ; si l’agent s’est arrêté sans faire avancer l’étape, les preuves montrent aussi ses dernières lignes de sortie d’erreur. Après la dernière tentative, il publie un commentaire final, pose `agent-failed`, arrête le conteneur, conserve le worktree et libère l’emplacement. Les autres causes sont un délai de réponse expiré, un ticket source supprimé et une limite dépassée comme le coût ou le nombre de fichiers modifiés. Fermer le ticket source pendant qu’une tâche attend l’annule.

Dans Tâches, une tâche échouée affiche **Échouées**, et son détail explique que les preuves de reprise sont conservées. **Réessayer** demande au worker de récupérer la tâche ; cela ne contourne ni la validation ni l’approbation. Dans la vue Tickets, Relancer remplace Démarrer. Retirer `agent-failed` ne relance rien. **Annuler** apparaît pour les tâches inachevées et demande au worker de s’arrêter et de nettoyer. Les tâches terminées ne peuvent pas être annulées. Les administrateurs et les développeurs attribués peuvent utiliser les deux. Une commande en file affiche sa progression, par exemple Commande en file ou Commande terminée. Une commande échouée ou incertaine indique aussi pourquoi, quand le moteur nomme une raison, et affiche les dernières lignes du moteur.

Pour les tâches locales, **Relancer** revérifie l’exécuteur installé et accepte un exécutable mis à jour ou un environnement hérité modifié sur le même ordinateur et compte. La tâche, le worktree, la branche, l’historique et les limites cumulées sont conservés. La surveillance automatique ne le fait pas. Les paramètres d’exécution modifiés ou les preuves de récupération corrompues doivent être corrigés. Si le redémarrage échoue, la commande indique l’échec et sa cause enregistrée : exécutable absent, version invalide, échec de commande ou délai dépassé. Ce contrôle de version n’envoie aucune requête au modèle ; utilisez **Tester la connexion IA** pour cela.

Lorsqu’une commande en conteneur dépasse sa limite, ADORE arrête ce conteneur avant toute autre commande. La prochaine tentative autorisée reprend le même conteneur avec ses dépendances et fichiers ; l’accès réseau reste inchangé. Si l’arrêt ou le redémarrage sûr ne peut être confirmé, la tâche échoue et conserve ses preuves à examiner avant de **Relancer**. Une préparation échouée conserve sa procédure de reprise explicite.

## Abandonner et recommencer {#restart}

Pour une tâche échouée, **Abandonner et recommencer** supprime son état enregistré, sa copie de travail avec le travail non publié et sa branche distante propre inchangée. Lisez l’avertissement et confirmez. ADORE vérifie la propriété avant le nettoyage et démarre le même ticket ouvert avec les paramètres actuels seulement après un nettoyage réussi. La surveillance reste en pause si elle l’était. Les administrateurs et développeurs affectés peuvent utiliser cette action.

Réessayer ne corrige pas les changements de mode ou de paramètres stables ; les détails l’expliquent et proposent l’action confirmée. Restaurez les paramètres enregistrés pour conserver le travail. Réessayer peut toujours revalider les changements volatils de l’environnement natif, dont les variables processeur après redimensionnement d’une VM.

Les ressources étrangères, un autre ordinateur ou compte, les preuves corrompues ou une branche distante modifiée bloquent la récupération. Un nettoyage partiel conserve les preuves restantes sans nouvelle tâche. Si la tâche change après confirmation, actualisez ses détails et vérifiez à nouveau. Le verrou CLI peut appartenir au worker web : mettez la surveillance en pause dans le Résumé du projet et attendez la fin de la tâche bornée. Ne supprimez pas un verrou actif.

Si une ancienne tâche supprimée a laissé une branche sans checkpoint enregistré, ADORE la conserve et utilise une nouvelle génération. Un checkpoint connu modifié bloque toujours la récupération. Trois autres noms au maximum sont essayés et les règles du dépôt doivent autoriser un nom libre ; sinon la récupération s’arrête avant le nettoyage. Le résultat indique quand une ancienne branche est conservée.

## Suivre les tâches {#following-jobs}

Utilisez **Tâches** dans la barre latérale ou l’onglet **Tâches** d’un projet, puis le sous-onglet **Tâches**. Le tableau a ces colonnes :

| Colonne | Contenu |
|---|---|
| Ticket | Numéro et titre ; ouvre le détail de la tâche. |
| Projet | Le projet propriétaire. |
| État | L’état, l’Étape courante, et un lien vers le ticket ou la MR/PR lorsqu’une personne doit agir. |
| Dernière activité | Heure du dernier événement enregistré. |
| Consommation | Jetons utilisés par la tâche. |

Cliquez sur un titre de colonne pour trier. **Rechercher des travaux** cherche dans les titres, numéros, projets, identifiants de tâche, état, étape ou résultat. Le filtre **État** propose Tâches actives, En attente, Revue humaine et Travaux terminés. La page s’actualise seule tant qu’elle est visible.

Le détail affiche **Que se passe-t-il maintenant**, **Qui intervient**, **Où** et **Ce qui suit**, puis la Consommation, une Chronologie (Date, Événement, Étape), des liens **Preuves et artefacts** et les **Détails techniques**. La chronologie ne liste que les événements enregistrés. Une ancienne activité ne prouve pas à elle seule que le travail s’est arrêté.

## Budgets du travail {#budgets}

Le détail affiche **Lancements de l’exécuteur** (par exemple 9 / 20) et **Travail actif (secondes)** avec les limites actuelles du projet, indépendamment des statistiques de jetons. À 90 %, il signale une limite proche ; à la limite, il demande de l’augmenter avant la reprise. La limite initiale est 20 dans l’inscription et `adore init`.

Les administrateurs peuvent suivre **Ajuster les budgets dans les paramètres du projet**, ouvrir **Implémentation**, modifier uniquement les budgets, choisir **Enregistrer** et confirmer les valeurs exactes. Cet enregistrement révisé est permis pendant une attente de clarification, sans conducteur actif ni opération inachevée. Les autres paramètres gardent leurs contrôles habituels ; les développeurs restent en lecture seule.

Les budgets sont relus avant chaque tentative, reprise ou relance. Une tentative en cours garde son délai. Le travail actif est cumulé entre relances, réponses et révisions ; l’attente est exclue. Augmenter une limite conserve le travail consommé, la tâche et la progression. Une tâche échouée par épuisement exige toujours **Relancer** après ajustement. Une configuration invalide ou absente bloque les tentatives suivantes jusqu’à correction.

Si les limites actuelles sont illisibles, le détail conserve la consommation, les preuves et les actions de reprise. Les limites affichent — avec un avis d’indisponibilité ; aucune valeur par défaut n’est supposée. Corrigez la configuration avant de relancer.

## État et preuves de l’exécuteur {#operational-evidence}

**En cours** signifie qu’ADORE conduit l’étape enregistrée ; aucune action humaine n’est demandée. **En attente de clarification** nécessite une réponse sur le ticket. **Échoué** arrête le travail autonome et conserve les preuves de récupération. La carte affiche les tentatives échouées de l’étape courante même si le travail reste En cours.

Les questions affichent listes, tableaux et code en Markdown. Le HTML reste littéral, les liens dangereux sont inactifs et les images ne se chargent pas automatiquement. Tableaux et code larges défilent dans la question.

Les étapes de la chronologie viennent de l’étape, du contexte d’étape ou de la destination de transition enregistrés dans chaque événement ; les événements sans rapport restent inconnus. Les heures incluent les secondes. Un événement est une preuve enregistrée, pas une progression en direct.

Dans **Preuves et artefacts**, choisissez **Voir la dernière sortie de l’exécuteur**. Les sorties opérationnelles capturées par l’hôte du dernier lancement terminé sont affichées, avec modules absents et totaux des tests. Prompts, raisonnement, scripts, configuration, chemins, identifiants et données financières sont masqués. Les sorties inconnues deviennent un avis ou une catégorie de diagnostic. Seuls les 500 derniers diagnostics par flux, dans 64 Kio, sont conservés.

Le résumé affiche la tentative, son heure, le résultat et le code de sortie. Dépliez **stdout** ou **stderr** si des données sont présentes. Si un lancement est en cours, le panneau le signale et conserve la dernière sortie terminée. Si le journal change pendant la lecture, choisissez **Réessayer**. La dernière sortie vérifiée est signalée comme potentiellement périmée.

Un lancement sans capture prouvée ou un instantané supprimé est explicitement indisponible ; aucune archive brute ne sert de repli. Les preuves corrompues sont refusées. Un travail existant peut rester sans sortie jusqu’à un lancement ultérieur ; cette vue n’en démarre aucun.

Si **Consommation** ne se charge pas, utilisez **Actualiser la consommation** près de l’erreur. Preuves et récupération restent séparées. Une source corrompue nécessite toujours l’intervention de l’opérateur.
