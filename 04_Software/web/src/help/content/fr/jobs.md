# Cycle de vie d’une tâche

Une tâche est le travail qu’ADORE effectue pour un ticket, de la prise en charge à une modification fusionnée. Cet article présente ses étapes et les moments où vous intervenez. Les étiquettes et l’éligibilité sont décrites dans [Tickets et prise en charge automatique](/help/tickets).

## Étapes {#stages}

ADORE exécute les étapes AEGIS une à une, chaque tentative dans une session d’exécuteur neuve. Les exécuteurs ne poussent jamais, n’ouvrent jamais de MR/PR et ne fusionnent jamais.

| Étape | Ce qui se passe |
|---|---|
| Cadrage | Le périmètre est convenu et l’exécuteur consigne si la tâche suit le chemin complet ou le chemin rapide. |
| Spécification | L’exigence est rédigée. |
| Conception | Une courte note de conception est rédigée pour les travaux non triviaux. |
| Développement | Un test en échec vient d’abord, puis l’implémentation, jusqu’à ce que les tests passent. |
| Validation | Revue, suite de tests complète, contrôle strict et rapport AEGIS ; la tâche AEGIS se clôt. ADORE répète ensuite lui-même le contrôle strict avant de demander l’approbation. |

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

Lorsqu’une étape échoue, ADORE tient à jour un commentaire d’incident unique sur le ticket avec l’étape, la tentative, le code d’erreur, les preuves et la prochaine action. Après la dernière tentative, il publie un commentaire final, pose `agent-failed`, arrête le conteneur, conserve le worktree et libère l’emplacement. Les autres causes sont un délai de réponse expiré, un ticket source supprimé et une limite dépassée comme le coût ou le nombre de fichiers modifiés. Fermer le ticket source pendant qu’une tâche attend l’annule.

Dans Tâches, une tâche échouée affiche **Échouées**, et son détail explique que les preuves de reprise sont conservées. **Réessayer** demande au worker de récupérer la tâche ; cela ne contourne ni la validation ni l’approbation. Dans la vue Tickets, Relancer remplace Démarrer. Retirer `agent-failed` ne relance rien. **Annuler** apparaît pour les tâches inachevées et demande au worker de s’arrêter et de nettoyer. Les tâches terminées ne peuvent pas être annulées. Les administrateurs et les développeurs attribués peuvent utiliser les deux. Une commande en file affiche sa progression, par exemple Commande en file ou Commande terminée.

Pour les tâches locales, **Relancer** revérifie l’exécuteur installé et accepte un exécutable mis à jour ou un environnement hérité modifié sur le même ordinateur et compte. La tâche, le worktree, la branche, l’historique et les limites cumulées sont conservés. La surveillance automatique ne le fait pas. Les paramètres d’exécution modifiés ou les preuves de récupération corrompues doivent être corrigés. Si le redémarrage échoue, la commande indique l’échec et sa cause enregistrée : exécutable absent, version invalide, échec de commande ou délai dépassé. Ce contrôle de version n’envoie aucune requête au modèle ; utilisez **Tester la connexion IA** pour cela.

Lorsqu’une commande en conteneur dépasse sa limite, ADORE arrête ce conteneur avant toute autre commande. La prochaine tentative autorisée reprend le même conteneur avec ses dépendances et fichiers ; l’accès réseau reste inchangé. Si l’arrêt ou le redémarrage sûr ne peut être confirmé, la tâche échoue et conserve ses preuves à examiner avant de **Relancer**. Une préparation échouée conserve sa procédure de reprise explicite.

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
