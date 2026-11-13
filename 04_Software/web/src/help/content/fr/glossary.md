# Glossaire

L’approbation humaine avant publication est activée par défaut. Les administrateurs peuvent modifier **Exiger une approbation humaine avant PR/MR** dans Paramètres. Si elle est désactivée, ADORE contrôle l’actualité du candidat et de la cible avant publication ; les tests du dépôt restent à la charge de l’agent.

Voici les termes utilisés dans l’interface web d’ADORE et dans ces rubriques d’aide.

## Termes {#terms}

| Terme | Signification |
|---|---|
| Tâche | Un ticket du dépôt traité et vérifié dans un environnement isolé. |
| Projet inscrit | Un dépôt existant configuré sur l’hôte ADORE, accessible à son équipe. |
| Surveillance | Le réglage d’un projet pour la prise en charge de nouveaux tickets, affiché comme **Active** ou **En pause**. Les administrateurs le modifient avec **Suspendre la surveillance** et **Activer la surveillance** dans l’onglet Résumé du projet. |
| Prise en charge arrêtée | ADORE ne prend plus de nouveaux tickets pour ce projet. Cela ne suspend pas une tâche active. C’est l’état que la Surveillance affiche comme **En pause**. |
| Ticket | Un ticket de la forge. ADORE le prend en charge lorsqu’il porte l’étiquette de disponibilité du projet et une étiquette de priorité, n’est ni bloqué ni exclu, et comporte des critères d’acceptation si le projet l’exige. |
| Agent de programmation / Exécuteur | L’outil d’IA en ligne de commande qui effectue le travail d’une tâche dans un environnement isolé : Pi, le seul agent de programmation lancé par ADORE. Il n’a aucun identifiant de forge et ne commit, ne pousse, n’ouvre ni ne fusionne jamais. |
| Modèle | L’ID du modèle chez le fournisseur choisi, par exemple gpt-5.4 pour OpenAI. Il se définit avec le fournisseur dans Paramètres → Agent et modèle, et les tarifs estimatifs appartiennent à un couple exécuteur et modèle. |
| AEGIS | Le workflow installé dans le dépôt qui cadre, spécifie, conçoit, développe et valide une modification. ADORE le conduit une étape à la fois (Cadrage, Spécification, Conception, Développement, Validation) et publie le résultat approuvé ; une petite modification peut omettre la Spécification et la Conception. |
| Workflow direct | Un dépôt sans AEGIS est traité directement par l’agent. L’agent mène ses contrôles ; ADORE observe le progrès et demande une approbation humaine. |
| Candidat | Le résultat validé d’une tâche qu’ADORE présente pour approbation, identifié par une empreinte et le commit cible. L’approbation s’applique à ce candidat exact et devient caduque si le candidat ou sa branche cible change. |
| En attente de clarification | L’agent attend une réponse pour continuer. Répondez à sa question dans le ticket du dépôt. |
| En attente d'approbation | Le résultat est validé et attend une autorisation humaine de publication. L’approbation est enregistrée sur la forge pour le candidat actuel. |
| MR/PR brouillon | La demande de fusion ou de tirage ouverte après validation et approbation si requise. Les personnes la relisent. |
| Revue humaine | Une MR/PR est disponible pour revue humaine. La fusion reste une décision humaine. |
| Tour de révision | Un nouveau passage de l’agent après une demande ou un échec CI. Chaque tour répète la validation et suit la politique d’approbation du projet. |
| Forge | La plateforme d’hébergement où se trouvent les tickets, étiquettes, approbations et MR/PR : GitHub, GitLab ou Gitea. |

> ADORE n’a aucune opération de fusion. La fusion est toujours une décision humaine sur la forge.
