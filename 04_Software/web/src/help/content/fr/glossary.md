# Glossaire

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
| Workflow direct | Le workflow d’un dépôt sans `.agentic/aegis.py` : une session d’implémentation Pi limitée, suivie de la vérification indépendante facultative d’ADORE, avec les mêmes limites d’approbation et de revue humaines. |
| Commande de vérification | Commande shell facultative sur une seule ligne, définie à l’inscription ou dans Paramètres → Implémentation et enregistrée comme `[workflow] verify_command`. Les exécutions directes la lancent depuis la racine de l’arbre de travail sous la limite de validation ; vide signifie non vérifié, et AEGIS utilise ses propres tests à la place. |
| Candidat | Le résultat validé d’une tâche qu’ADORE présente pour approbation, identifié par une empreinte et le commit cible. L’approbation s’applique à ce candidat exact et devient caduque si le candidat ou sa branche cible change. |
| En attente de clarification | L’agent attend une réponse pour continuer. Répondez à sa question dans le ticket du dépôt. |
| En attente d'approbation | Le résultat est validé et attend une autorisation humaine de publication. L’approbation est enregistrée sur la forge pour le candidat actuel. |
| MR/PR brouillon | La demande de fusion (GitLab) ou de tirage (GitHub, Gitea) qu’ADORE ouvre après l’approbation, en brouillon sauf si le projet est configuré pour en publier une prête. Des personnes la relisent. |
| Revue humaine | Une MR/PR est disponible pour revue humaine. La fusion reste une décision humaine. |
| Tour de révision | Un passage supplémentaire de l’agent de programmation sur la même branche après qu’un relecteur a demandé des modifications, ou après l’échec de vérifications CI lorsque la réparation automatique est activée. Les tours sont limités par **Nombre maximal de tours de révision**, et chacun exige une nouvelle approbation avant toute publication. |
| Forge | La plateforme d’hébergement où se trouvent les tickets, étiquettes, approbations et MR/PR : GitHub, GitLab ou Gitea. |

> ADORE n’a aucune opération de fusion. La fusion est toujours une décision humaine sur la forge.
