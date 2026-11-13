# Statistiques et coûts

Statistiques montre le travail effectué par ADORE, ce qu’il a consommé et la solidité des résultats. Les coûts ne sont montrés qu’aux administrateurs, et les coûts estimés ne sont pas des factures.

## Période de rapport et export {#period}

Ouvrez **Statistiques** dans la barre latérale pour voir tous les projets auxquels vous avez accès, ou ouvrez l’onglet **Statistiques** d’un projet pour voir ce projet seul. Les deux utilisent la même disposition : une ligne **Période de rapport** au-dessus de quatre onglets.

| Commande | Ce qu’elle fait |
|---|---|
| Projet | Page Statistiques uniquement. Les administrateurs commencent avec **Tous les projets** ; un Dev choisit parmi les projets attribués. L’onglet du projet n’a pas de sélecteur. |
| Depuis et Jusqu’au | Le premier et le dernier jour à inclure. **Jusqu’au** inclut ce jour entier. |
| Regrouper par | Des tranches par **Jour**, **Semaine** ou **Mois**, utilisées par l’onglet Tendances et par les exports. |
| Toute la période | Efface les deux dates. Laisser les deux dates vides signifie aussi toute la période. |
| Exporter CSV | Ouvre un menu de téléchargements pour le projet, les dates et le regroupement en cours. |

Les dates et les tranches utilisent UTC, sauf si l’adresse de la page porte un autre fuseau horaire. Les dates s’appliquent à tous les onglets et à tous les exports. Changer de projet conserve la période et l’onglet affiché.

Le menu **Exporter CSV** propose **Indicateurs du projet**, **Utilisation du projet** et **Consommation du job** pour un projet, ou **Indicateurs de tous les projets**, **Utilisation de tous les projets** et **Consommation du job** pour **Tous les projets**. Il apparaît une fois les données chargées. Les lectures en arrière-plan conservent le rapport, le menu ouvert et les commandes du tableau jusqu’à la validation d’un remplacement complet.

**Actualiser** relit les mesures et l’utilisation sans réinitialiser la vue. **Actualisé le** indique leur dernière lecture complète réussie ; **Mesures actualisées** et **Utilisation actualisée** indiquent l’heure de chaque source. Les mesures du projet choisi s’actualisent toutes les 15 secondes ; l’utilisation et les mesures globales toutes les 30 secondes lorsque l’onglet est visible.

Après une panne de connexion ou un délai de lecture dépassé, le dernier rapport validé peut rester avec un avis d’échec, ses heures d’origine et **Réessayer**. Ce ne sont pas des données actuelles. Une lecture manuelle ou automatique réussie efface l’avis. Les CSV lisent les données actuelles du serveur, pas nécessairement ce rapport conservé. Les lectures initiales, invalides, non autorisées ou les autres échecs affichent **Chargement des données impossible** et masquent totaux et exports.

Un tiret signifie que la valeur est inconnue. Sous une valeur, **Zéro mesuré** signifie qu’ADORE a observé zéro, **Non disponible** signifie que rien n’a été enregistré, et **Partiel · sous-total connu** signifie que le chiffre ne couvre que l’utilisation qui a déclaré des jetons.

## Les quatre onglets {#tabs}

### Résumé {#tab-summary}

Des cartes pour **Jobs démarrés**, **Jobs terminés**, **Jobs échoués**, **Jetons en entrée**, **Jetons en sortie** et **Total connu des jetons**. Terminés compte toutes les tâches finies, quel que soit leur résultat. Le total exige que les deux sens de jetons soient connus. Les administrateurs voient aussi les cartes **Coût déclaré** et **Coût estimé**. Avec **Tous les projets**, un tableau **Comparaison des projets** liste, par projet, les tâches démarrées, terminées et échouées et la durée moyenne écoulée, avec le dépôt sous le nom de chaque projet.

### Utilisation {#tab-usage}

**Utilisation par exécuteur et modèle** commence par des totaux compacts : événements d’utilisation, jetons en entrée et en sortie, cache lu et cache écrit, et durée écoulée des tâches (**Tâches mesurées**, **Durée moyenne**, **Durée médiane**). Le tableau en dessous liste l’utilisation par date, exécuteur et modèle ; cliquez sur un titre de colonne pour trier. Avec **Tous les projets**, un tableau par projet suit. Les administrateurs voient aussi des colonnes de coût.

### Qualité {#tab-quality}

**Qualité de livraison** montre **Reprises demandées en revue**, **Validation réussie au premier essai**, **Fusion sans reprise en revue**, **Revues encore ouvertes**, **Échecs d'étape** et **Nouvelles tentatives opérateur**. Chaque taux affiche son numérateur et son dénominateur. **Revues encore ouvertes** est l’état actuel et ignore la période. Viennent ensuite **Révisions demandées sur MR/PR** et **Réparations du pipeline**, avec un tableau quotidien des jours actifs. Avec **Tous les projets**, un tableau par projet ajoute les cycles de revue.

### Tendances {#tab-trends}

La couverture de l’utilisation apparaît sous forme de valeur compacte. Un tableau comporte une ligne par tranche (jour, semaine ou mois) avec les tâches démarrées, terminées et échouées sous forme de barres proportionnelles, ainsi que les jetons en entrée et en sortie et, pour les administrateurs, le coût déclaré et estimé.

Si le périmètre n’a encore aucune tâche, Qualité et Tendances l’indiquent et vous orientent vers Tâches → Tickets pour en démarrer une.

## Coûts déclarés et estimés {#costs}

Deux chiffres de coût sont tenus séparés, et aucun n’est une facture.

- Le **Coût déclaré** est ce que l’exécuteur a déclaré, retenu comme preuve observée. S’il n’en a déclaré aucun, la valeur indique **Non disponible**.
- Le **Coût estimé** est le nombre de jetons enregistré multiplié par des tarifs que les administrateurs définissent. C’est une estimation, pas une facture ni un plafond de dépense.

Les administrateurs enregistrent les tarifs dans **Paramètres → Agent et modèle** d’un projet, sous **Tarifs estimatifs** : choisissez **Valable à partir du**, puis saisissez **USD entrée / 1 M jetons** et **USD sortie / 1 M jetons** et **Enregistrer**. Un tarif s’applique à Pi et à son modèle configuré ; définissez donc d’abord le modèle. Chaque événement d’utilisation est tarifé selon l’exécuteur, le modèle et le jour de consommation. Les événements sans tarif correspondant sont comptés comme **Utilisations sans tarif** dans les totaux d’Utilisation.

> Un tarif saisi avec une date d’effet antérieure peut modifier les estimations passées. Exportez un CSV si vous avez besoin d’un chiffre à un instant donné.

Dans l’onglet Qualité, les administrateurs voient aussi **Coût par tâche documentée**, par tâche terminée et par tâche fusionnée par un humain, chacun avec le nombre de tâches concernées.

## Qui voit les valeurs monétaires {#visibility}

| Rôle | Projets | Argent |
|---|---|---|
| Administrateur | **Tous les projets** ou n’importe quel projet | Coût déclaré, Coût estimé, Utilisations sans tarif, coût par tâche, coût par révision, colonnes de coût et champs financiers des exports CSV |
| Dev | Projets attribués uniquement ; pas de **Tous les projets** | Aucune. Les Dev voient le nombre de tâches, les jetons, la durée écoulée et les indicateurs de qualité, jamais un champ financier. |

Les tarifs ne sont définis et visibles que par les administrateurs ; les Paramètres en lecture seule d’un Dev omettent les paramètres financiers.
