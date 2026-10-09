/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import type { Locale } from "./i18n";

/** Human ticket actions and the status names managed by the conductor. */
export const lifecycleCopy: Record<Locale, { title: string; help: string; labels: Record<string, string> }> = {
 en: { title: "Status labels", help: "ADORE applies these labels to tickets as jobs change state. Customize their names to match your repository conventions; adding or removing them manually does not change the saved job state.", labels: {
  "labels.lifecycle.ready": "Ready for pickup label", "labels.lifecycle.answered": "Clarification answered label",
  "labels.lifecycle.clarify": "Job status: clarify label", "labels.lifecycle.done": "Job status: done label", "labels.lifecycle.failed": "Job status: failed label", "labels.lifecycle.review": "Job status: review label", "labels.lifecycle.working": "Job status: working label",
 } },
 fr: { title: "Étiquettes de statut", help: "ADORE applique ces étiquettes aux tickets selon l’état des tâches. Adaptez leurs noms aux conventions du dépôt ; les ajouter ou les retirer manuellement ne modifie pas l’état enregistré de la tâche.", labels: {
  "labels.lifecycle.ready": "Étiquette de disponibilité pour la prise en charge", "labels.lifecycle.answered": "Étiquette de réponse à une clarification",
  "labels.lifecycle.clarify": "Étiquette de clarification en attente", "labels.lifecycle.done": "Étiquette de tâche terminée", "labels.lifecycle.failed": "Étiquette de tâche échouée", "labels.lifecycle.review": "Étiquette de revue en attente", "labels.lifecycle.working": "Étiquette de travail en cours",
 } },
 de: { title: "Statuslabels", help: "ADORE setzt diese Labels entsprechend dem Aufgabenstatus auf Tickets. Passen Sie die Namen an die Repository-Konventionen an; manuelles Setzen oder Entfernen ändert den gespeicherten Aufgabenstatus nicht.", labels: {
  "labels.lifecycle.ready": "Label für aufnahmebereite Tickets", "labels.lifecycle.answered": "Label für beantwortete Rückfragen",
  "labels.lifecycle.clarify": "Label für offene Rückfragen", "labels.lifecycle.done": "Label für abgeschlossene Aufgaben", "labels.lifecycle.failed": "Label für fehlgeschlagene Aufgaben", "labels.lifecycle.review": "Label für ausstehendes Review", "labels.lifecycle.working": "Label für laufende Arbeit",
 } },
 ro: { title: "Etichete de stare", help: "ADORE aplică aceste etichete pe tichete în funcție de starea lucrării. Adaptează numele la convențiile depozitului; adăugarea sau eliminarea lor manuală nu schimbă starea salvată a lucrării.", labels: {
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

const en = {
  repository: "Repository and tickets", agent: "Agent and model", isolation: "Isolated environment", rules: "Rules and approvals", limits: "Limits and recovery", measurement: "Measurement and notifications", advanced: "Advanced",
  readFailed: "The saved candidate could not be verified. Refresh to read it again, or explicitly discard it.", single: "Prepare one setting at a time. Review and apply or discard its candidate before editing another setting.", active: "Active value", proposed: "Proposed value", effect: "Effect after applying", project: "Affected project", prepared: "Prepared at", actor: "Prepared by: not recorded", stale: "The active configuration changed. Discard this candidate, refresh and prepare the change again.", idle: "Apply requires no active job, conductor lock or unfinished operation. The server checks these conditions again when you apply.", pause: "Stop project pickup and wait for active work to finish before applying this identity or runtime change.", discard: "Discard removes only this candidate. The active configuration stays unchanged.", copy: "Copy safe review", copied: "Review copied", details: "Technical details", base: "Reviewed base revision", candidate: "Candidate revision", unknown: "Not recorded", minimum: "Minimum", maximum: "Maximum", prepare: "Prepare candidate", readOnly: "Read-only settings", future: "Applies to subsequent execution; existing jobs retain their configuration.", endpoint: "This endpoint change also updates the displayed model and connection options together.",
};
export const settingsCopy: Record<Locale, typeof en> = {
 en,
 fr: { readFailed: "Le candidat enregistré est invérifiable. Actualisez ou abandonnez-le explicitement.", repository: "Dépôt et tickets", agent: "Agent et modèle", isolation: "Environnement isolé", rules: "Règles et approbations", limits: "Limites et reprise", measurement: "Mesure et notifications", advanced: "Avancé", single: "Préparez un paramètre à la fois. Appliquez ou abandonnez son candidat avant une autre modification.", active: "Valeur active", proposed: "Valeur proposée", effect: "Effet après application", project: "Projet concerné", prepared: "Préparé le", actor: "Préparé par : non enregistré", stale: "La configuration active a changé. Abandonnez ce candidat, actualisez et préparez de nouveau.", idle: "L’application exige aucune tâche active, aucun verrou du conducteur et aucune opération inachevée. Le serveur revérifie ces conditions.", pause: "Arrêtez la prise en charge et attendez la fin du travail actif avant ce changement d’identité ou d’environnement.", discard: "Abandonner supprime seulement ce candidat. La configuration active reste inchangée.", copy: "Copier la revue expurgée", copied: "Revue copiée", details: "Détails techniques", base: "Révision de base revue", candidate: "Révision du candidat", unknown: "Non enregistré", minimum: "Minimum", maximum: "Maximum", prepare: "Préparer le candidat", readOnly: "Paramètres en lecture seule", future: "S’applique aux exécutions suivantes ; les tâches existantes conservent leur configuration.", endpoint: "Cette modification met à jour ensemble le modèle affiché et les options de connexion." },
 de: { readFailed: "Der gespeicherte Kandidat konnte nicht geprüft werden. Aktualisieren oder ausdrücklich verwerfen.", repository: "Repository und Tickets", agent: "Agent und Modell", isolation: "Isolierte Umgebung", rules: "Regeln und Freigaben", limits: "Grenzen und Wiederherstellung", measurement: "Messung und Benachrichtigungen", advanced: "Erweitert", single: "Bereiten Sie jeweils eine Einstellung vor. Wenden Sie den Kandidaten an oder verwerfen Sie ihn vor der nächsten Änderung.", active: "Aktiver Wert", proposed: "Vorgeschlagener Wert", effect: "Wirkung nach Anwendung", project: "Betroffenes Projekt", prepared: "Vorbereitet am", actor: "Vorbereitet von: nicht erfasst", stale: "Die aktive Konfiguration hat sich geändert. Verwerfen, aktualisieren und erneut vorbereiten.", idle: "Anwenden erfordert keine aktive Aufgabe, Leitprozess-Sperre oder offene Operation. Der Server prüft erneut.", pause: "Stoppen Sie die Übernahme und warten Sie auf laufende Arbeit vor dieser Identitäts- oder Laufzeitänderung.", discard: "Verwerfen entfernt nur diesen Kandidaten. Die aktive Konfiguration bleibt unverändert.", copy: "Bereinigte Prüfung kopieren", copied: "Prüfung kopiert", details: "Technische Details", base: "Geprüfte Basisrevision", candidate: "Kandidatenrevision", unknown: "Nicht erfasst", minimum: "Minimum", maximum: "Maximum", prepare: "Kandidat vorbereiten", readOnly: "Schreibgeschützte Einstellungen", future: "Gilt für folgende Ausführungen; vorhandene Aufgaben behalten ihre Konfiguration.", endpoint: "Diese Änderung aktualisiert Modell und Verbindungsoptionen gemeinsam." },
 ro: { readFailed: "Candidatul salvat nu a putut fi verificat. Reîncărcați sau eliminați-l explicit.", repository: "Depozit și tichete", agent: "Agent și model", isolation: "Mediu izolat", rules: "Reguli și aprobări", limits: "Limite și recuperare", measurement: "Măsurare și notificări", advanced: "Avansat", single: "Pregătiți o singură setare odată. Aplicați sau eliminați candidatul înainte de altă modificare.", active: "Valoare activă", proposed: "Valoare propusă", effect: "Efect după aplicare", project: "Proiect afectat", prepared: "Pregătit la", actor: "Pregătit de: neînregistrat", stale: "Configurația activă s-a schimbat. Eliminați candidatul, reîncărcați și pregătiți schimbarea din nou.", idle: "Aplicarea cere lipsa unei lucrări active, a blocării conductorului și a operațiilor neterminate. Serverul reverifică aceste condiții.", pause: "Opriți preluarea și așteptați terminarea lucrărilor înainte de această schimbare de identitate sau mediu.", discard: "Eliminarea șterge doar candidatul. Configurația activă rămâne neschimbată.", copy: "Copiază recenzia fără secrete", copied: "Recenzie copiată", details: "Detalii tehnice", base: "Revizie de bază revizuită", candidate: "Revizia candidatului", unknown: "Neînregistrat", minimum: "Minim", maximum: "Maxim", prepare: "Pregătește candidatul", readOnly: "Setări doar pentru citire", future: "Se aplică execuțiilor următoare; lucrările existente își păstrează configurația.", endpoint: "Schimbarea actualizează împreună modelul afișat și opțiunile conexiunii." },
};

/** Understandable English catalog labels, including named entries. */
export function settingLabel(key: string): string {
 const labels: Record<string, string> = {
 "labels.lifecycle.ready": "Ready for pickup label", "labels.lifecycle.answered": "Clarification answered label",
 "labels.control.exclude": "Exclude from pickup label",
 "execution.backend": "Execution backend",
 "execution.preparation": "Reviewed preparation recipe",
 "execution.preparation_step_timeout_seconds": "Preparation step limit (seconds)",
 "execution.preparation_total_timeout_seconds": "Preparation total limit (seconds)",
 "execution.preparation_max_attempts": "Maximum preparation attempts",

 "container.runtime_env.OPENAI_BASE_URL": "Model endpoint URL", "agent.name": "Agent display name", "agent.slug": "Agent resource name", "agent.email": "Commit author email", "platform.kind": "Repository service", "platform.repo": "Repository owner and name", "platform.login": "Gitea login name",
 "executor.default": "Default coding agent", "executor.mode": "Agent execution mode", "executor.stage_host_auth": "Use host agent sign-in", "executor.questions_file": "Agent question file", "executor.env_keys": "Credential variable names",
 "polling.mode": "Ticket checking mode", "polling.poll_interval_seconds": "Ticket check interval (seconds)", "polling.poll_jitter_seconds": "Random check delay (seconds)", "polling.poll_backoff": "Wait longer after ticket service errors", "polling.max_concurrent_runs": "Active job limit", "polling.quiet_hours": "Hours with no pickup or advancement",
 "budgets.max_iterations": "Maximum iterations per job", "budgets.max_files_touched": "Maximum changed files per job", "budgets.max_cost_usd": "Job cost cap (USD)", "budgets.max_wall_clock_seconds": "Job time limit (seconds)", "budgets.per_gate_timeout_seconds": "Stage attempt time limit (seconds)",
 "container.runtime": "Container runtime command", "container.image": "Agent container image", "container.selinux_relabel": "Shared mount access on SELinux", "container.egress.mode": "Outbound network policy", "container.egress.proxy_port": "Network proxy port", "container.egress.proxy_image": "Network proxy image", "container.egress.network_prefix": "Isolated network name prefix", "container.keep_parked": "Keep containers while waiting", "container.parked_ttl_mode": "Waiting-container retention unit", "container.parked_ttl_seconds": "Waiting-container retention (seconds)", "container.parked_ttl_polls": "Waiting-container retention (checks)",
 "worktree.repo_path": "Existing local repository path", "worktree.root": "Job working folders", "worktree.branch_template": "Job branch naming template", "worktree.branch_rule": "Required branch name pattern",
 "delivery.draft": "PR/MR state at publication", "delivery.approval_label": "Human publication approval label", "delivery.publish_checkpoints": "Publish progress commits", "delivery.target_branch": "Target branch", "delivery.remove_source_branch": "Remove branch after human merge", "delivery.reviewers": "Request review from",
 "workflow.default_kind": "Default task type", "workflow.aegis_python": "Workflow Python command", "workflow.quick_label": "Quick-path suggestion label", "state.channel": "State reporting channel", "state.store_root": "Durable job state folder", "review.trigger": "Review request method", "review.revise_label": "Revision request label", "review.max_review_rounds": "Maximum revision rounds", "review.on_pipeline_failure": "Response to failed review pipeline", "review.review_reminder_after": "Review reminder interval (reserved)",
 "recovery.max_stage_failures": "Failed attempts allowed per stage", "recovery.max_transient_retries": "Attempts allowed for temporary errors", "recovery.retry_backoff_seconds": "Retry delays (seconds)", "metrics.enabled": "Record completed job measurements", "metrics.capture_tokens": "Record agent-reported tokens", "metrics.capture_resource": "Resource measurement (reserved)", "metrics.db_path": "Measurement database path", "metrics.export_jsonl": "Measurement export path", "metrics.html_out": "Statistics HTML output path",
 "readiness.max_scope_hint": "Ticket scope hint (reserved)", "readiness.require_acceptance_criteria": "Require ticket acceptance criteria", "readiness.require_priority_label": "Require ticket priority label",
 "reconcile.on_ticket_closed": "Response when a ticket closes (reserved)", "reconcile.on_ticket_deleted": "Response when a ticket is deleted (reserved)", "reconcile.on_trigger_removed": "Response when pickup label is removed (reserved)",
 "clarification.answer_timeout": "Time allowed for a human answer", "clarification.reminder_after": "Human answer reminder interval", "clarification.max_rounds": "Maximum question rounds", "clarification.timeout_state": "Outcome when an answer expires",
 };
 if (labels[key]) return labels[key];
 const parts = key.split(".");
 if (key.startsWith("executor.commands.")) return `${parts[2]} ${parts[3] === "model" ? "model identifier" : "launch command"}`;
 if (key.startsWith("container.runtime_env.")) return `Container environment: ${parts.slice(2).join(".")}`;
 if (key.startsWith("workflow.stage_timeout_overrides.")) return `${parts[2]} attempt time limit (seconds)`;
 if (key.startsWith("workflow.kind_labels.")) return `Task type for ticket label ${parts[2]}`;
 if (key.startsWith("labels.")) return `${parts[1] === "lifecycle" ? "Job status" : parts[1] === "control" ? "Pickup control" : parts[1] === "selection" ? "Ticket selection" : "Agent selection"}: ${parts[2].replaceAll("_", " ")} label`;
 return parts.slice(1).join(" ").replaceAll("_", " ").replace(/^./, letter => letter.toUpperCase());
}
