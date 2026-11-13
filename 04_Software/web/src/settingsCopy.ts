/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import type { Locale } from "./i18n.ts";

/** Branch row/editor/review names and server preview findings share four locales. */
export const branchNamingCopy = {
 en: {
  template: "Job branch name template", rule: "Optional branch name rule", preview: "Example job branch", checking: "Checking this example…", unavailable: "Preview unavailable. Check the connection or refresh the settings.", matched: "This example matches the rule.", noRule: "No naming rule configured.", example: "Example only: no branch is created. The rule must also allow future ticket and run identifiers.", variables: "Template variables: {slug} = agent resource name, {iid} = ticket number, {run_id} = unique run identifier.",
  issues: { missing_identity: "Include {iid} or {run_id} in the template.", invalid_template: "Use only {slug}, {iid} and {run_id}, without formatting modifiers.", invalid_branch: "The example is not a valid Git branch name.", invalid_rule: "The rule is not a valid Python regular expression.", rule_mismatch: "This example does not match the rule.", rule_timeout: "Rule checking took too long. Simplify the expression.", rule_check_failed: "The server could not check this rule.", too_long: "The template and rule must each contain at most 512 characters." },
 },
 ro: {
  template: "Șablonul numelui branch-ului de job", rule: "Regulă opțională pentru numele branch-ului", preview: "Exemplu de branch pentru job", checking: "Se verifică acest exemplu…", unavailable: "Previzualizarea nu este disponibilă. Verifică conexiunea sau reîncarcă setările.", matched: "Acest exemplu respectă regula.", noRule: "Nu este configurată o regulă de denumire.", example: "Este doar un exemplu: nu se creează niciun branch. Regula trebuie să permită și identificatorii viitoarelor tichete și rulări.", variables: "Variabile în șablon: {slug} = numele tehnic al agentului, {iid} = numărul tichetului, {run_id} = identificatorul unic al rulării.",
  issues: { missing_identity: "Include {iid} sau {run_id} în șablon.", invalid_template: "Folosește doar {slug}, {iid} și {run_id}, fără modificatori de formatare.", invalid_branch: "Exemplul nu este un nume valid de branch Git.", invalid_rule: "Regula nu este o expresie regulată Python validă.", rule_mismatch: "Acest exemplu nu respectă regula.", rule_timeout: "Verificarea regulii a durat prea mult. Simplifică expresia.", rule_check_failed: "Serverul nu a putut verifica această regulă.", too_long: "Șablonul și regula pot avea fiecare cel mult 512 caractere." },
 },
 fr: {
  template: "Modèle du nom de branche du travail", rule: "Règle facultative du nom de branche", preview: "Exemple de branche du travail", checking: "Vérification de cet exemple…", unavailable: "Aperçu indisponible. Vérifiez la connexion ou rechargez les paramètres.", matched: "Cet exemple respecte la règle.", noRule: "Aucune règle de nommage configurée.", example: "Exemple uniquement : aucune branche n’est créée. La règle doit aussi autoriser les futurs identifiants de tickets et d’exécutions.", variables: "Variables du modèle : {slug} = nom technique de l’agent, {iid} = numéro du ticket, {run_id} = identifiant unique de l’exécution.",
  issues: { missing_identity: "Incluez {iid} ou {run_id} dans le modèle.", invalid_template: "Utilisez uniquement {slug}, {iid} et {run_id}, sans modificateurs de format.", invalid_branch: "L’exemple n’est pas un nom de branche Git valide.", invalid_rule: "La règle n’est pas une expression régulière Python valide.", rule_mismatch: "Cet exemple ne respecte pas la règle.", rule_timeout: "La vérification a pris trop de temps. Simplifiez l’expression.", rule_check_failed: "Le serveur n’a pas pu vérifier cette règle.", too_long: "Le modèle et la règle sont limités à 512 caractères chacun." },
 },
 de: {
  template: "Vorlage für den Job-Branch-Namen", rule: "Optionale Regel für Branch-Namen", preview: "Beispiel eines Job-Branches", checking: "Dieses Beispiel wird geprüft…", unavailable: "Vorschau nicht verfügbar. Verbindung prüfen oder Einstellungen neu laden.", matched: "Dieses Beispiel erfüllt die Regel.", noRule: "Keine Namensregel konfiguriert.", example: "Nur ein Beispiel: Es wird kein Branch erstellt. Die Regel muss auch künftige Ticket- und Laufkennungen zulassen.", variables: "Vorlagenvariablen: {slug} = technischer Agentenname, {iid} = Ticketnummer, {run_id} = eindeutige Laufkennung.",
  issues: { missing_identity: "{iid} oder {run_id} in die Vorlage aufnehmen.", invalid_template: "Nur {slug}, {iid} und {run_id} ohne Formatmodifikatoren verwenden.", invalid_branch: "Das Beispiel ist kein gültiger Git-Branch-Name.", invalid_rule: "Die Regel ist kein gültiger regulärer Python-Ausdruck.", rule_mismatch: "Dieses Beispiel erfüllt die Regel nicht.", rule_timeout: "Die Prüfung dauerte zu lange. Ausdruck vereinfachen.", rule_check_failed: "Der Server konnte diese Regel nicht prüfen.", too_long: "Vorlage und Regel dürfen jeweils höchstens 512 Zeichen enthalten." },
 },
};

export function branchSettingLabel(key: string, locale: Locale): string | null {
 return key === "worktree.branch_template" ? branchNamingCopy[locale].template
  : key === "worktree.branch_rule" ? branchNamingCopy[locale].rule : null;
}

/** Implementation setting names shared by rows, editors and review. */
export const implementationLabels: Record<Locale, Record<string, string>> = {
 en: { "clarification.answer_timeout": "Time allowed for a human answer", "clarification.max_rounds": "Maximum question rounds", "recovery.max_stage_failures": "Failed attempts allowed per stage", "recovery.max_transient_retries": "Attempts allowed for temporary errors", "recovery.retry_backoff_seconds": "Retry delays (seconds)", "workflow.stage_timeout_overrides": "Stage timeout overrides", "polling.max_concurrent_runs": "Active job limit", "budgets.max_iterations": "Maximum executor launches per job", "budgets.max_wall_clock_seconds": "Active work time limit (seconds)", "budgets.max_files_touched": "Maximum changed files per job", "budgets.max_cost_usd": "Job cost cap (USD)", "budgets.per_gate_timeout_seconds": "Stage attempt time limit (seconds)", "delivery.publish_checkpoints": "Publish progress commits", "workflow.quick_label": "Quick-path suggestion label" },
 fr: { "clarification.answer_timeout": "Temps accordé à une réponse humaine", "clarification.max_rounds": "Nombre maximal de tours de questions", "recovery.max_stage_failures": "Tentatives échouées autorisées par étape", "recovery.max_transient_retries": "Tentatives autorisées pour les erreurs temporaires", "recovery.retry_backoff_seconds": "Délais de relance (secondes)", "workflow.stage_timeout_overrides": "Limites de temps individuelles par étape", "polling.max_concurrent_runs": "Limite de tâches actives", "budgets.max_iterations": "Nombre maximal de lancements de l’exécuteur par tâche", "budgets.max_wall_clock_seconds": "Limite de temps de travail actif (secondes)", "budgets.max_files_touched": "Nombre maximal de fichiers modifiés par tâche", "budgets.max_cost_usd": "Plafond de coût de la tâche (USD)", "budgets.per_gate_timeout_seconds": "Limite de temps par tentative d’étape (secondes)", "delivery.publish_checkpoints": "Publier les commits de progression", "workflow.quick_label": "Étiquette de suggestion du chemin rapide" },
 de: { "clarification.answer_timeout": "Wartezeit auf eine menschliche Antwort", "clarification.max_rounds": "Maximale Rückfragerunden", "recovery.max_stage_failures": "Erlaubte Fehlversuche je Phase", "recovery.max_transient_retries": "Versuche bei vorübergehenden Fehlern", "recovery.retry_backoff_seconds": "Wiederholungspausen (Sekunden)", "workflow.stage_timeout_overrides": "Individuelle Zeitlimits je Phase", "polling.max_concurrent_runs": "Limit aktiver Aufträge", "budgets.max_iterations": "Maximale Executor-Starts je Auftrag", "budgets.max_wall_clock_seconds": "Zeitlimit für aktive Arbeit (Sekunden)", "budgets.max_files_touched": "Maximale geänderte Dateien je Auftrag", "budgets.max_cost_usd": "Kostenlimit je Auftrag (USD)", "budgets.per_gate_timeout_seconds": "Zeitlimit je Phasenversuch (Sekunden)", "delivery.publish_checkpoints": "Fortschrittscommits veröffentlichen", "workflow.quick_label": "Label als Schnellpfad-Vorschlag" },
 ro: { "clarification.answer_timeout": "Timpul acordat unui răspuns uman", "clarification.max_rounds": "Numărul maxim de runde de întrebări", "recovery.max_stage_failures": "Încercări eșuate permise per etapă", "recovery.max_transient_retries": "Încercări permise pentru erori temporare", "recovery.retry_backoff_seconds": "Pauze între reîncercări (secunde)", "workflow.stage_timeout_overrides": "Limite de timp individuale pe etape", "polling.max_concurrent_runs": "Limita lucrărilor active", "budgets.max_iterations": "Numărul maxim de lansări ale executorului per job", "budgets.max_wall_clock_seconds": "Limita timpului de lucru activ (secunde)", "budgets.max_files_touched": "Numărul maxim de fișiere modificate per job", "budgets.max_cost_usd": "Plafonul costului jobului (USD)", "budgets.per_gate_timeout_seconds": "Limita timpului pentru o încercare de etapă (secunde)", "delivery.publish_checkpoints": "Publică commituri de progres", "workflow.quick_label": "Eticheta de sugestie pentru traseul rapid" },
};

export function implementationSettingLabel(key: string, locale: Locale): string | null {
 const labels = implementationLabels[locale];
 return Object.hasOwn(labels, key) ? labels[key] : null;
}

/** Human ticket actions and the status names managed by the conductor. */
export const lifecycleCopy: Record<Locale, { title: string; help: string; labels: Record<string, string> }> = {
 en: { title: "Status labels", help: "Names used for ticket states and clarification replies. ADORE manages the state labels; a person adds the answered label after posting a new reply. Labels alone do not replace a required comment or recovery action.", labels: {
  "labels.lifecycle.ready": "Ready for pickup label", "labels.lifecycle.answered": "Clarification answered label",
  "labels.lifecycle.clarify": "Job status: clarify label", "labels.lifecycle.done": "Job status: done label", "labels.lifecycle.failed": "Job status: failed label", "labels.lifecycle.review": "Job status: review label", "labels.lifecycle.working": "Job status: working label",
 } },
 fr: { title: "Étiquettes de statut", help: "Noms des états des tickets et des réponses aux clarifications. ADORE gère les étiquettes d’état ; une personne ajoute celle de réponse après un nouveau commentaire. Une étiquette seule ne remplace pas le commentaire ou l’action de reprise requis.", labels: {
  "labels.lifecycle.ready": "Étiquette de disponibilité pour la prise en charge", "labels.lifecycle.answered": "Étiquette de réponse à une clarification",
  "labels.lifecycle.clarify": "Étiquette de clarification en attente", "labels.lifecycle.done": "Étiquette de tâche terminée", "labels.lifecycle.failed": "Étiquette de tâche échouée", "labels.lifecycle.review": "Étiquette de revue en attente", "labels.lifecycle.working": "Étiquette de travail en cours",
 } },
 de: { title: "Statuslabels", help: "Namen für Ticketstatus und Rückfrageantworten. ADORE verwaltet Statuslabels; eine Person setzt das Antwortlabel nach einem neuen Kommentar. Labels allein ersetzen keinen erforderlichen Kommentar oder Wiederherstellungsschritt.", labels: {
  "labels.lifecycle.ready": "Label für aufnahmebereite Tickets", "labels.lifecycle.answered": "Label für beantwortete Rückfragen",
  "labels.lifecycle.clarify": "Label für offene Rückfragen", "labels.lifecycle.done": "Label für abgeschlossene Aufgaben", "labels.lifecycle.failed": "Label für fehlgeschlagene Aufgaben", "labels.lifecycle.review": "Label für ausstehendes Review", "labels.lifecycle.working": "Label für laufende Arbeit",
 } },
 ro: { title: "Etichete de stare", help: "Nume folosite pentru stările tichetelor și răspunsurile la clarificări. ADORE gestionează etichetele de stare; o persoană adaugă eticheta de răspuns după un comentariu nou. Etichetele singure nu înlocuiesc comentariul sau acțiunea necesară de recuperare.", labels: {
  "labels.lifecycle.ready": "Eticheta pentru preluare", "labels.lifecycle.answered": "Eticheta de răspuns la clarificări",
  "labels.lifecycle.clarify": "Eticheta de așteptare a clarificărilor", "labels.lifecycle.done": "Eticheta lucrării finalizate", "labels.lifecycle.failed": "Eticheta lucrării eșuate", "labels.lifecycle.review": "Eticheta de așteptare a review-ului", "labels.lifecycle.working": "Eticheta lucrului în curs",
 } },
};

/** Exclusion controls ticket pickup while its configured label is present. */
export const excludeLabelCopy: Record<Locale, { label: string }> = {
 en: { label: "Exclude from pickup label" },
 fr: { label: "Étiquette d’exclusion de la prise en charge" },
 de: { label: "Label zum Ausschluss von der Aufnahme" },
 ro: { label: "Eticheta de excludere de la preluare" },
};

/** Statistics storage is configured externally and shown informationally. */
export const statisticsDatabaseCopy: Record<Locale, { label: string }> = {
 en: { label: "Statistics database file" },
 fr: { label: "Fichier de la base de statistiques" },
 de: { label: "Statistik-Datenbankdatei" },
 ro: { label: "Fișierul bazei de date pentru statistici" },
};

/** The integration branch supplies both the worktree base and the PR/MR target. */
export const targetBranchCopy: Record<Locale, { label: string }> = {
 en: { label: "Target branch" },
 fr: { label: "Branche cible" },
 de: { label: "Zielbranch" },
 ro: { label: "Ramura de integrare" },
};

/** Reviewer requests are distinct from publication approval and merge authorization. */
export const reviewerCopy: Record<Locale, { label: string }> = {
 en: { label: "Request review from" },
 fr: { label: "Demander une revue à" },
 de: { label: "Review anfordern von" },
 ro: { label: "Solicită review de la" },
};

/** Localized presentation of the boolean wire contract for newly created reviews. */
export const publicationCopy: Record<Locale, { label: string; draft: string; ready: string }> = {
 en: { label: "PR/MR state at publication", draft: "Draft", ready: "Ready for review" },
 fr: { label: "État de la PR/MR à la publication", draft: "Brouillon", ready: "Prête pour revue" },
 de: { label: "PR/MR-Status bei Veröffentlichung", draft: "Entwurf", ready: "Bereit zur Prüfung" },
 ro: { label: "Starea PR/MR la publicare", draft: "Draft", ready: "Pregătit pentru review" },
};

/** Name an exact review-state value without coercing malformed values. */
export function publicationValue(value: unknown, locale: Locale): string | null {
 return value === true || value === "true" ? publicationCopy[locale].draft
  : value === false || value === "false" ? publicationCopy[locale].ready : null;
}

/** Human CI actions share names across active/default values, editors and review. */
export const pipelineFailureCopy: Record<Locale, { label: string; revise: string; notify: string; ignore: string }> = {
 en: { label: "Action when PR/MR CI checks fail", revise: "Automatic repair", notify: "Notify only", ignore: "Ignore" },
 fr: { label: "Action en cas d’échec des vérifications CI de la PR/MR", revise: "Réparation automatique", notify: "Notifier uniquement", ignore: "Ignorer" },
 de: { label: "Aktion bei fehlgeschlagenen PR/MR-CI-Prüfungen", revise: "Automatisch reparieren", notify: "Nur benachrichtigen", ignore: "Ignorieren" },
 ro: { label: "Acțiune când verificările CI ale PR/MR eșuează", revise: "Reparare automată", notify: "Doar notificare", ignore: "Ignoră" },
};

/** Accept only the three exact configured CI responses. */
export function pipelineFailureValue(value: unknown, locale: Locale): string | null {
 return value === "revise" || value === "notify" || value === "ignore" ? pipelineFailureCopy[locale][value] : null;
}

const en = {
  repository: "Repository", tickets: "Tickets", implementation: "Implementation", reviews: "PR/MR and review", statistics: "Statistics", authentication: "Authentication", technical: "Technical details", executor: "Agent and model", environment: "Execution environment",
  clarification: "Clarifications", recovery: "Recovery after errors", stageLimits: "Advanced stage time limits", statisticsFiles: "Advanced statistics paths", integrationBranch: "Integration branch", integrationBranchLink: "View in Repository", integrationBranchHelp: "PR/MRs target this branch. Configure it in Repository.",
  readFailed: "The saved candidate could not be verified. Refresh to read it again, or explicitly discard it.", single: "Prepare one setting at a time. Review and apply or discard its candidate before editing another setting.", active: "Active value", proposed: "Proposed value", effect: "Effect after applying", project: "Affected project", prepared: "Prepared at", actor: "Prepared by: not recorded", stale: "The active configuration changed. Discard this candidate, refresh and prepare the change again.", idle: "Apply requires no active job, conductor lock or unfinished operation. The server checks these conditions again when you apply.", pause: "Stop project pickup and wait for active work to finish before applying this identity or runtime change.", discard: "Discard removes only this candidate. The active configuration stays unchanged.", copy: "Copy safe review", copied: "Review copied", details: "Technical details", base: "Reviewed base revision", candidate: "Candidate revision", unknown: "Not recorded", minimum: "Minimum", maximum: "Maximum", prepare: "Prepare candidate", readOnly: "Read-only settings", future: "Applies to subsequent execution; existing jobs retain their configuration.", endpoint: "This endpoint change also updates the displayed model and connection options together.",
};
/** Installation values are informative; external path edits do not relocate data. */
export const technicalSettingsHelp = {
 en: "Configured externally in the project's TOML file on the ADORE server. Changing a path does not move existing job state, repositories or job working folders.",
 ro: "Se configurează extern, în fișierul TOML al proiectului de pe serverul ADORE. Schimbarea unei căi nu mută starea existentă a joburilor, repository-urile sau dosarele de lucru ale joburilor.",
 fr: "Configuration externe dans le fichier TOML du projet sur le serveur ADORE. Modifier un chemin ne déplace pas les états des tâches, les dépôts ou les dossiers de travail existants.",
 de: "Extern in der TOML-Datei des Projekts auf dem ADORE-Server konfiguriert. Eine Pfadänderung verschiebt keine vorhandenen Auftragszustände, Repositorys oder Arbeitsordner.",
};

export const settingsCopy: Record<Locale, typeof en> = {
 en,
 fr: { readFailed: "Le candidat enregistré est invérifiable. Actualisez ou abandonnez-le explicitement.", repository: "Dépôt", tickets: "Tickets", implementation: "Implémentation", reviews: "PR/MR et revue", statistics: "Statistiques", authentication: "Authentification", technical: "Détails techniques", executor: "Agent et modèle", environment: "Environnement d’exécution", clarification: "Clarifications", recovery: "Reprise après erreur", stageLimits: "Limites de temps avancées par étape", statisticsFiles: "Chemins avancés des statistiques", integrationBranch: "Branche d’intégration", integrationBranchLink: "Voir dans Dépôt", integrationBranchHelp: "Les PR/MR ciblent cette branche. Configurez-la dans Dépôt.", single: "Préparez un paramètre à la fois. Appliquez ou abandonnez son candidat avant une autre modification.", active: "Valeur active", proposed: "Valeur proposée", effect: "Effet après application", project: "Projet concerné", prepared: "Préparé le", actor: "Préparé par : non enregistré", stale: "La configuration active a changé. Abandonnez ce candidat, actualisez et préparez de nouveau.", idle: "L’application exige aucune tâche active, aucun verrou du conducteur et aucune opération inachevée. Le serveur revérifie ces conditions.", pause: "Arrêtez la prise en charge et attendez la fin du travail actif avant ce changement d’identité ou d’environnement.", discard: "Abandonner supprime seulement ce candidat. La configuration active reste inchangée.", copy: "Copier la revue expurgée", copied: "Revue copiée", details: "Détails techniques", base: "Révision de base revue", candidate: "Révision du candidat", unknown: "Non enregistré", minimum: "Minimum", maximum: "Maximum", prepare: "Préparer le candidat", readOnly: "Paramètres en lecture seule", future: "S’applique aux exécutions suivantes ; les tâches existantes conservent leur configuration.", endpoint: "Cette modification met à jour ensemble le modèle affiché et les options de connexion." },
 de: { readFailed: "Der gespeicherte Kandidat konnte nicht geprüft werden. Aktualisieren oder ausdrücklich verwerfen.", repository: "Repository", tickets: "Tickets", implementation: "Implementierung", reviews: "PR/MR und Review", statistics: "Statistik", authentication: "Authentifizierung", technical: "Technische Details", executor: "Agent und Modell", environment: "Ausführungsumgebung", clarification: "Rückfragen", recovery: "Wiederherstellung nach Fehlern", stageLimits: "Erweiterte Zeitlimits pro Phase", statisticsFiles: "Erweiterte Statistikpfade", integrationBranch: "Integrationsbranch", integrationBranchLink: "Im Repository anzeigen", integrationBranchHelp: "PR/MRs haben diesen Zielbranch. Konfigurieren Sie ihn im Repository.", single: "Bereiten Sie jeweils eine Einstellung vor. Wenden Sie den Kandidaten an oder verwerfen Sie ihn vor der nächsten Änderung.", active: "Aktiver Wert", proposed: "Vorgeschlagener Wert", effect: "Wirkung nach Anwendung", project: "Betroffenes Projekt", prepared: "Vorbereitet am", actor: "Vorbereitet von: nicht erfasst", stale: "Die aktive Konfiguration hat sich geändert. Verwerfen, aktualisieren und erneut vorbereiten.", idle: "Anwenden erfordert keine aktive Aufgabe, Leitprozess-Sperre oder offene Operation. Der Server prüft erneut.", pause: "Stoppen Sie die Übernahme und warten Sie auf laufende Arbeit vor dieser Identitäts- oder Laufzeitänderung.", discard: "Verwerfen entfernt nur diesen Kandidaten. Die aktive Konfiguration bleibt unverändert.", copy: "Bereinigte Prüfung kopieren", copied: "Prüfung kopiert", details: "Technische Details", base: "Geprüfte Basisrevision", candidate: "Kandidatenrevision", unknown: "Nicht erfasst", minimum: "Minimum", maximum: "Maximum", prepare: "Kandidat vorbereiten", readOnly: "Schreibgeschützte Einstellungen", future: "Gilt für folgende Ausführungen; vorhandene Aufgaben behalten ihre Konfiguration.", endpoint: "Diese Änderung aktualisiert Modell und Verbindungsoptionen gemeinsam." },
 ro: { readFailed: "Candidatul salvat nu a putut fi verificat. Reîncărcați sau eliminați-l explicit.", repository: "Repository", tickets: "Tichete", implementation: "Implementare", reviews: "PR/MR și review", statistics: "Statistici", authentication: "Autentificare", technical: "Detalii tehnice", executor: "Agent și model", environment: "Mediu de execuție", clarification: "Clarificări", recovery: "Recuperare după erori", stageLimits: "Limite avansate de timp pe etapă", statisticsFiles: "Căi avansate pentru statistici", integrationBranch: "Ramura de integrare", integrationBranchLink: "Vezi în Repository", integrationBranchHelp: "PR/MR-urile au această ramură ca destinație. Configureaz-o în Repository.", single: "Pregătiți o singură setare odată. Aplicați sau eliminați candidatul înainte de altă modificare.", active: "Valoare activă", proposed: "Valoare propusă", effect: "Efect după aplicare", project: "Proiect afectat", prepared: "Pregătit la", actor: "Pregătit de: neînregistrat", stale: "Configurația activă s-a schimbat. Eliminați candidatul, reîncărcați și pregătiți schimbarea din nou.", idle: "Aplicarea cere lipsa unei lucrări active, a blocării conductorului și a operațiilor neterminate. Serverul reverifică aceste condiții.", pause: "Opriți preluarea și așteptați terminarea lucrărilor înainte de această schimbare de identitate sau mediu.", discard: "Eliminarea șterge doar candidatul. Configurația activă rămâne neschimbată.", copy: "Copiază recenzia fără secrete", copied: "Recenzie copiată", details: "Detalii tehnice", base: "Revizie de bază revizuită", candidate: "Revizia candidatului", unknown: "Neînregistrat", minimum: "Minim", maximum: "Maxim", prepare: "Pregătește candidatul", readOnly: "Setări doar pentru citire", future: "Se aplică execuțiilor următoare; lucrările existente își păstrează configurația.", endpoint: "Schimbarea actualizează împreună modelul afișat și opțiunile conexiunii." },
};

/** French, German and Romanian names for settings that had only an English label; the help uses the same names. */
const localizedSettingLabels: Partial<Record<Locale, Record<string, string>>> = {
  fr: {
    "readiness.require_priority_label": "Exiger une étiquette de priorité sur le ticket",
    "readiness.require_acceptance_criteria": "Exiger des critères d’acceptation sur le ticket",
    "delivery.remove_source_branch": "Supprimer la branche après la fusion humaine",
    "metrics.enabled": "Enregistrer les mesures des tâches terminées",
    "metrics.capture_tokens": "Enregistrer les jetons déclarés par l’agent",
    "review.max_review_rounds": "Nombre maximal de tours de révision",
  },
  de: {
    "readiness.require_priority_label": "Prioritätslabel am Ticket verlangen",
    "readiness.require_acceptance_criteria": "Akzeptanzkriterien im Ticket verlangen",
    "delivery.remove_source_branch": "Branch nach menschlichem Merge entfernen",
    "metrics.enabled": "Messwerte abgeschlossener Aufträge erfassen",
    "metrics.capture_tokens": "Vom Agenten gemeldete Token erfassen",
    "review.max_review_rounds": "Maximale Überarbeitungsrunden",
  },
  ro: {
    "readiness.require_priority_label": "Cere etichetă de prioritate pentru tichet",
    "readiness.require_acceptance_criteria": "Cere criterii de acceptare pentru tichet",
    "delivery.remove_source_branch": "Șterge ramura după integrarea făcută de o persoană",
    "metrics.enabled": "Înregistrează măsurătorile lucrărilor finalizate",
    "metrics.capture_tokens": "Înregistrează tokenurile raportate de agent",
    "review.max_review_rounds": "Numărul maxim de runde de revizie",
  },
};

/** A setting's name in a non-English locale, when the catalog has one. */
export const localizedSettingLabel = (key: string, locale: Locale): string | undefined => localizedSettingLabels[locale]?.[key];

/** Understandable English catalog labels, including named entries. */
export function settingLabel(key: string): string {
 if (key === "metrics.db_path") return statisticsDatabaseCopy.en.label;
 if (key === "review.on_pipeline_failure") return pipelineFailureCopy.en.label;
 const branch = implementationSettingLabel(key, "en") || branchSettingLabel(key, "en");
 if (branch) return branch;
 const labels: Record<string, string> = {
 "labels.lifecycle.ready": "Ready for pickup label", "labels.lifecycle.answered": "Clarification answered label",
 "labels.control.exclude": "Exclude from pickup label",
 "labels.selection.type_epic": "Epic label",
 "execution.backend": "Runs in",
 "execution.preparation": "Reviewed preparation recipe",
 "execution.preparation_step_timeout_seconds": "Preparation step limit (seconds)",
 "execution.preparation_total_timeout_seconds": "Preparation total limit (seconds)",
 "execution.preparation_max_attempts": "Maximum preparation attempts",

 "agent.name": "Agent display name", "agent.slug": "Agent resource name", "agent.email": "Commit author email", "platform.kind": "Repository service", "platform.repo": "Repository owner and name", "platform.login": "Gitea login name",
 "executor.mode": "Agent execution mode", "executor.internet": "Internet access for the agent", "executor.web.search": "Web search", "executor.questions_file": "Agent question file", "executor.env_keys": "Credential variable names",
 "polling.mode": "Ticket checking mode", "polling.poll_interval_seconds": "Ticket check interval (seconds)", "polling.poll_jitter_seconds": "Random check delay (seconds)", "polling.poll_backoff": "Wait longer after ticket service errors", "polling.max_concurrent_runs": "Active job limit", "polling.quiet_hours": "Hours with no pickup or advancement",
 "budgets.max_iterations": "Maximum executor launches per job", "budgets.max_files_touched": "Maximum changed files per job", "budgets.max_cost_usd": "Job cost cap (USD)", "budgets.max_wall_clock_seconds": "Active work time limit (seconds)", "budgets.per_gate_timeout_seconds": "Stage attempt time limit (seconds)",
 "container.runtime": "Container runtime command", "container.image": "Agent container image", "container.selinux_relabel": "Shared mount access on SELinux", "container.egress.proxy_port": "Network proxy port", "container.egress.proxy_image": "Network proxy image", "container.egress.network_prefix": "Isolated network name prefix", "container.keep_parked": "Keep containers while waiting", "container.parked_ttl_mode": "Waiting-container retention unit", "container.parked_ttl_seconds": "Waiting-container retention (seconds)", "container.parked_ttl_polls": "Waiting-container retention (checks)",
 "worktree.repo_path": "Existing local repository path", "worktree.root": "Job working folders", "worktree.branch_template": "Job branch name template", "worktree.branch_rule": "Optional branch name rule",
 "delivery.draft": "PR/MR state at publication", "delivery.approval_label": "Human publication approval label", "delivery.publish_checkpoints": "Publish progress commits", "delivery.target_branch": "Target branch", "delivery.remove_source_branch": "Remove branch after human merge", "delivery.reviewers": "Request review from",
 "workflow.default_kind": "Default task type", "workflow.aegis_python": "Workflow Python command", "workflow.quick_label": "Quick-path suggestion label", "state.store_root": "Durable job state folder", "review.trigger": "Review request method", "review.revise_label": "Revision request label", "review.max_review_rounds": "Maximum revision rounds", "review.on_pipeline_failure": "Action when PR/MR CI checks fail", "review.review_reminder_after": "Review reminder interval (reserved)",
 "recovery.max_stage_failures": "Failed attempts allowed per stage", "recovery.max_transient_retries": "Attempts allowed for temporary errors", "recovery.retry_backoff_seconds": "Retry delays (seconds)", "metrics.enabled": "Record completed job measurements", "metrics.capture_tokens": "Record agent-reported tokens", "metrics.capture_resource": "Resource measurement (reserved)", "metrics.db_path": "Statistics database file", "metrics.export_jsonl": "Measurement export path", "metrics.html_out": "Statistics HTML output path",
 "readiness.max_scope_hint": "Ticket scope hint (reserved)", "readiness.require_acceptance_criteria": "Require ticket acceptance criteria", "readiness.require_priority_label": "Require ticket priority label",
 "reconcile.on_ticket_closed": "Response when a ticket closes (reserved)", "reconcile.on_ticket_deleted": "Response when a ticket is deleted (reserved)", "reconcile.on_trigger_removed": "Response when pickup label is removed (reserved)",
 "clarification.answer_timeout": "Time allowed for a human answer", "clarification.reminder_after": "Human answer reminder interval", "clarification.max_rounds": "Maximum question rounds", "clarification.timeout_state": "Outcome when an answer expires",
 };
 if (labels[key]) return labels[key];
 const parts = key.split(".");
 if (key.startsWith("container.runtime_env.")) return `Container environment: ${parts.slice(2).join(".")}`;
 if (key.startsWith("workflow.stage_timeout_overrides.")) return `${parts[2]} attempt time limit (seconds)`;
 if (key.startsWith("workflow.kind_labels.")) return `Task type for ticket label ${parts[2]}`;
 if (key.startsWith("labels.")) return `${parts[1] === "lifecycle" ? "Job status" : parts[1] === "control" ? "Pickup control" : parts[1] === "selection" ? "Ticket selection" : "Labels"}: ${parts[2].replaceAll("_", " ")} label`;
 return parts.slice(1).join(" ").replaceAll("_", " ").replace(/^./, letter => letter.toUpperCase());
}

/** Compact comparison headings and explicit unchanged-candidate feedback. */
export const compactReviewCopy: Record<Locale, { setting: string; complete: string; unchanged: string }> = {
 en: { setting: "Setting", complete: "Complete comparison", unchanged: "No values have changed." },
 ro: { setting: "Setare", complete: "Comparație completă", unchanged: "Nu există valori modificate." },
 fr: { setting: "Paramètre", complete: "Comparaison complète", unchanged: "Aucune valeur n’a changé." },
 de: { setting: "Einstellung", complete: "Vollständiger Vergleich", unchanged: "Keine Werte wurden geändert." },
};
