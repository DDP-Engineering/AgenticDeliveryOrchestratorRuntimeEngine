/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import type { Locale } from "./i18n.ts";
import type { Lifecycle } from "./jobModel.ts";

const en = {
  stageFailures: "Failed attempts in this stage: {count}",
  executorOutput: "View latest executor output",
  outputHelp: "Host-captured operational stdout/stderr. Missing modules and test totals are kept; private content is withheld.",
  outputMissing: "No proven operational output is available for the latest recorded launch.",
  outputEmpty: "No operational records.",
  outputFailed: "Executor output could not be read. Reload to inspect current evidence.",
  refreshConsumption: "Refresh consumption",
  exitCode: "Exit code",
  timedOut: "Timed out",

  details: "Details", allProjects: "All projects", allJobs: "View all jobs", noActive: "No active jobs",
  completed: "Completed", afterClarification: "After a correlated answer is accepted, the executor can resume through the existing gates.", afterApproval: "After fresh approval of this exact candidate, ADORE can publish an MR/PR through the existing gates.", afterReview: "The MR/PR stays in human review; humans decide whether to merge.",
  waiting: "Waiting", terminal: "Finished jobs", staleJob: "Stale", attention: "Needs attention", noAttention: "No jobs need attention in this scope.", scope: "Job scope", all: "All authorized projects",
  search: "Search jobs", searchHelp: "Search saved ticket titles, numbers, project names, job IDs, lifecycle, stage or outcome (up to 80 characters).",
  now: "What is happening now", who: "Who acts", where: "Where", follows: "What follows",
  unknown: "Unknown — no recorded evidence", titleUnknown: "Ticket title not recorded", personUnknown: "Named person not recorded",
  evidenceMissing: "The saved evidence does not identify an action location. Inspect the ticket or ask the operator for context.",
  openQuestion: "Answer on the ticket", openApproval: "Review the candidate on the forge", openReview: "Review the MR/PR",
  responder: "Human responder", approver: "Human approver", reviewer: "Human reviewer", operator: "Operator", system: "ADORE / executor",
  oldActivity: "Last recorded activity is over 15 minutes old. This alone does not show whether work has stopped.", missingActivity: "No activity timestamp recorded.",
  workerUnavailable: "Worker unavailable or heartbeat stale", workerError: "Worker status could not be read", 
  incomplete: "Incomplete job response", incompleteHelp: "Totals and jobs are hidden because the server did not confirm complete evidence.",
  changed: "Job sources changed", changedHelp: "The source revision changed. Reload the first page to read the current authorized history.", reload: "Reload first page",
  consumption: "Consumption", duration: "Job duration", unknownTelemetry: "Not available in the job evidence contract.",
  technical: "Technical details", artifacts: "Evidence and artifacts", observedTimeline: "Only saved events are shown. Unobserved stages, including stages omitted on a quick path, are not marked complete.",
  reasonUnknown: "Reason not recorded", approvalReason: "Approval was requested for the saved candidate.", reviewReason: "A saved MR/PR is awaiting human review.",
  retryHelp: "Retry asks the worker to recover this failed job using the existing retry contract; it does not bypass validation or approval.",
  cancelHelp: "Cancel requests termination and resource cleanup. The worker rechecks the current job and grant before acting.",
  queued: "Command queued — waiting for the worker", running: "Command running", succeeded: "Command completed", failed: "Command failed", uncertain: "Command outcome uncertain — inspect before resubmitting",
  commandError: "Command status could not be read; completion is unknown.", pickup: "Monitoring", pickupActive: "Active", pickupStopped: "Paused", pickupHelp: "Active jobs continue when pickup is stopped.",
  stopPickup: "Pause monitoring", startPickup: "Activate monitoring", verification: "Environment verification", unverified: "Unverified", stale: "Stale verification", invalid: "Invalid configuration",
  passed: "Verified", partial: "Partially verified", checkFailed: "Verification failed", verificationHelp: "Verification is explicit and bound to the saved configuration revision and check time.",
  summary: "Summary", settings: "Settings", history: "History", historyHelp: "Completed, failed, cancelled, stale and human-handed-off jobs in this project.",
};
export type JobCopy = typeof en;
export const jobCopy: Record<Locale, JobCopy> = {
  en,
  fr: {
  stageFailures: "Tentatives échouées dans cette étape : {count}",
  executorOutput: "Voir la dernière sortie de l’exécuteur",
  outputHelp: "Sorties opérationnelles capturées sur l’hôte. Modules absents et totaux des tests conservés ; contenu privé masqué.",
  outputMissing: "Aucune sortie terminée disponible pour le dernier lancement enregistré.",
  outputEmpty: "Aucun événement opérationnel.",
  outputFailed: "Sortie de l’exécuteur illisible. Rechargez pour consulter les preuves actuelles.",
  refreshConsumption: "Actualiser la consommation",
  exitCode: "Code de sortie",
  timedOut: "Délai dépassé",

  details: "Détails", allProjects: "Tous les projets", allJobs: "Voir tous les travaux", noActive: "Aucun travail actif",
  completed: "Terminé", afterClarification: "Après acceptation d’une réponse corrélée, l’exécuteur peut reprendre en respectant les contrôles existants.", afterApproval: "Après approbation actuelle de ce candidat exact, ADORE peut publier une MR/PR avec les contrôles existants.", afterReview: "La MR/PR reste en revue humaine ; les humains décident de la fusion.",
    waiting: "En attente", terminal: "Travaux terminés", staleJob: "Périmé", attention: "À traiter", noAttention: "Aucun travail ne demande une intervention dans ce périmètre.", scope: "Périmètre des travaux", all: "Tous les projets autorisés",
    search: "Rechercher des travaux", searchHelp: "Rechercher titres et numéros de tickets, projets, identifiants, état, étape ou résultat enregistrés (80 caractères maximum).",
    now: "Que se passe-t-il maintenant", who: "Qui intervient", where: "Où", follows: "Ce qui suit",
    unknown: "Inconnu — aucune preuve enregistrée", titleUnknown: "Titre du ticket non enregistré", personUnknown: "Personne nommée non enregistrée",
    evidenceMissing: "Les preuves enregistrées ne précisent pas où intervenir. Consultez le ticket ou demandez le contexte à l’opérateur.",
    openQuestion: "Répondre sur le ticket", openApproval: "Examiner le candidat sur la forge", openReview: "Examiner la MR/PR",
    responder: "Répondant humain", approver: "Approbateur humain", reviewer: "Relecteur humain", operator: "Opérateur", system: "ADORE / exécuteur",
    oldActivity: "La dernière activité enregistrée date de plus de 15 minutes. Cela ne prouve pas que le travail est arrêté.", missingActivity: "Aucun horodatage d’activité enregistré.",
    workerUnavailable: "Worker indisponible ou signal ancien", workerError: "État du worker illisible", 
    incomplete: "Réponse des travaux incomplète", incompleteHelp: "Les totaux et travaux sont masqués car le serveur ne confirme pas des preuves complètes.",
    changed: "Les sources des travaux ont changé", changedHelp: "La révision source a changé. Rechargez la première page pour lire l’historique autorisé actuel.", reload: "Recharger la première page",
    consumption: "Consommation", duration: "Durée du travail", unknownTelemetry: "Indisponible dans le contrat de preuves des travaux.", technical: "Détails techniques", artifacts: "Preuves et artefacts",
    observedTimeline: "Seuls les événements sauvegardés sont affichés. Les étapes non observées, y compris celles omises sur un parcours rapide, ne sont pas marquées terminées.",
    reasonUnknown: "Motif non enregistré", approvalReason: "Une approbation a été demandée pour le candidat sauvegardé.", reviewReason: "Une MR/PR enregistrée attend une revue humaine.",
    retryHelp: "Réessayer demande au worker de récupérer ce travail échoué selon le contrat existant, avec validation et approbation.",
    cancelHelp: "Annuler demande l’arrêt et le nettoyage des ressources. Le worker revérifie le travail et les droits avant d’agir.",
    queued: "Commande en file — en attente du worker", running: "Commande en cours", succeeded: "Commande terminée", failed: "Commande échouée", uncertain: "Résultat incertain — inspecter avant de renvoyer", commandError: "État de commande illisible ; résultat inconnu.",
    pickup: "Surveillance", pickupActive: "Active", pickupStopped: "En pause", pickupHelp: "Les travaux actifs continuent lorsque la sélection est arrêtée.", stopPickup: "Suspendre la surveillance", startPickup: "Activer la surveillance",
    verification: "Vérification de l’environnement", unverified: "Non vérifié", stale: "Vérification périmée", invalid: "Configuration invalide", passed: "Vérifié", partial: "Partiellement vérifié", checkFailed: "Vérification échouée",
    verificationHelp: "La vérification est explicite et liée à la révision sauvegardée et à l’heure du contrôle.", summary: "Résumé", settings: "Paramètres", history: "Historique", historyHelp: "Travaux terminés, échoués, annulés, périmés et confiés à un humain dans ce projet.",
  },
  de: {
  stageFailures: "Fehlversuche in dieser Phase: {count}",
  executorOutput: "Letzte Executor-Ausgabe anzeigen",
  outputHelp: "Vom Host erfasste operative Ausgaben. Fehlende Module und Testsummen bleiben sichtbar; private Inhalte verborgen.",
  outputMissing: "Für den letzten gespeicherten Start liegt keine abgeschlossene Ausgabe vor.",
  outputEmpty: "Keine operativen Einträge.",
  outputFailed: "Executor-Ausgabe nicht lesbar. Für aktuelle Nachweise neu laden.",
  refreshConsumption: "Verbrauch aktualisieren",
  exitCode: "Exitcode",
  timedOut: "Zeitlimit überschritten",

  details: "Details", allProjects: "Alle Projekte", allJobs: "Alle Jobs anzeigen", noActive: "Keine aktiven Jobs",
  completed: "Abgeschlossen", afterClarification: "Nach Annahme einer zugeordneten Antwort kann der Executor unter den bestehenden Prüfungen fortfahren.", afterApproval: "Nach aktueller Freigabe genau dieses Kandidaten kann ADORE unter den bestehenden Prüfungen einen MR/PR veröffentlichen.", afterReview: "Der MR/PR bleibt in menschlicher Prüfung; Menschen entscheiden über das Zusammenführen.",
    waiting: "Wartend", terminal: "Beendete Jobs", staleJob: "Veraltet", attention: "Handlungsbedarf", noAttention: "Keine Jobs in diesem Bereich benötigen einen Eingriff.", scope: "Jobbereich", all: "Alle berechtigten Projekte",
    search: "Jobs suchen", searchHelp: "Gespeicherte Tickettitel, Nummern, Projekte, Job-IDs, Status, Phase oder Ergebnis suchen (maximal 80 Zeichen).",
    now: "Was gerade geschieht", who: "Wer handelt", where: "Wo", follows: "Was folgt",
    unknown: "Unbekannt — kein gespeicherter Nachweis", titleUnknown: "Tickettitel nicht gespeichert", personUnknown: "Keine Person namentlich gespeichert",
    evidenceMissing: "Die gespeicherten Nachweise nennen keinen Handlungsort. Ticket prüfen oder den Betreiber nach dem Kontext fragen.",
    openQuestion: "Im Ticket antworten", openApproval: "Kandidat auf der Forge prüfen", openReview: "MR/PR prüfen",
    responder: "Menschlicher Antwortgeber", approver: "Menschlicher Genehmiger", reviewer: "Menschlicher Prüfer", operator: "Betreiber", system: "ADORE / Executor",
    oldActivity: "Die letzte gespeicherte Aktivität ist über 15 Minuten alt. Das allein zeigt nicht, ob die Arbeit angehalten hat.", missingActivity: "Kein Aktivitätszeitpunkt gespeichert.",
    workerUnavailable: "Worker nicht verfügbar oder Lebenszeichen veraltet", workerError: "Workerstatus konnte nicht gelesen werden", 
    incomplete: "Unvollständige Jobantwort", incompleteHelp: "Summen und Jobs bleiben verborgen, weil der Server keine vollständigen Nachweise bestätigt.",
    changed: "Jobquellen wurden geändert", changedHelp: "Die Quellrevision wurde geändert. Erste Seite neu laden, um den aktuellen berechtigten Verlauf zu lesen.", reload: "Erste Seite neu laden",
    consumption: "Verbrauch", duration: "Jobdauer", unknownTelemetry: "Im Vertrag der Jobnachweise nicht verfügbar.", technical: "Technische Details", artifacts: "Nachweise und Artefakte",
    observedTimeline: "Nur gespeicherte Ereignisse werden angezeigt. Unbeobachtete Phasen, auch bei einem kurzen Ablauf ausgelassene, werden nicht als abgeschlossen markiert.",
    reasonUnknown: "Grund nicht gespeichert", approvalReason: "Genehmigung für den gespeicherten Kandidaten wurde angefordert.", reviewReason: "Eine gespeicherte MR/PR wartet auf menschliche Prüfung.",
    retryHelp: "Wiederholen fordert die Wiederherstellung des fehlgeschlagenen Jobs gemäß dem bestehenden Vertrag an; Validierung und Genehmigung bleiben erforderlich.",
    cancelHelp: "Abbrechen fordert Beendigung und Ressourcenbereinigung an. Der Worker prüft Job und Berechtigung vor der Ausführung erneut.",
    queued: "Befehl eingereiht — wartet auf Worker", running: "Befehl wird ausgeführt", succeeded: "Befehl abgeschlossen", failed: "Befehl fehlgeschlagen", uncertain: "Befehlsergebnis unsicher — vor erneutem Senden prüfen", commandError: "Befehlsstatus nicht lesbar; Abschluss unbekannt.",
    pickup: "Überwachung", pickupActive: "Aktiv", pickupStopped: "Pausiert", pickupHelp: "Aktive Jobs laufen weiter, wenn die Ticketauswahl gestoppt ist.", stopPickup: "Überwachung pausieren", startPickup: "Überwachung aktivieren",
    verification: "Umgebungsprüfung", unverified: "Ungeprüft", stale: "Prüfung veraltet", invalid: "Ungültige Konfiguration", passed: "Geprüft", partial: "Teilweise geprüft", checkFailed: "Prüfung fehlgeschlagen",
    verificationHelp: "Die ausdrückliche Prüfung ist an die gespeicherte Konfigurationsrevision und Prüfzeit gebunden.", summary: "Zusammenfassung", settings: "Einstellungen", history: "Verlauf", historyHelp: "Abgeschlossene, fehlgeschlagene, abgebrochene, veraltete und an Menschen übergebene Jobs dieses Projekts.",
  },
  ro: {
  stageFailures: "Încercări eșuate în această etapă: {count}",
  executorOutput: "Vezi ultima ieșire a executorului",
  outputHelp: "Ieșiri operaționale capturate de host. Modulele lipsă și totalurile testelor se păstrează; conținutul privat este ascuns.",
  outputMissing: "Nu există o ieșire încheiată pentru ultima lansare înregistrată.",
  outputEmpty: "Nicio înregistrare operațională.",
  outputFailed: "Ieșirea executorului nu poate fi citită. Reîncarcă pentru dovezile actuale.",
  refreshConsumption: "Actualizează consumul",
  exitCode: "Cod de ieșire",
  timedOut: "Timp expirat",

  details: "Detalii", allProjects: "Toate proiectele", allJobs: "Vezi toate lucrările", noActive: "Nicio lucrare activă",
  completed: "Finalizat", afterClarification: "După acceptarea unui răspuns corelat, executorul poate continua prin verificările existente.", afterApproval: "După aprobarea curentă a acestui candidat exact, ADORE poate publica un MR/PR prin verificările existente.", afterReview: "MR/PR-ul rămâne în revizuire umană; oamenii decid integrarea.",
    waiting: "În așteptare", terminal: "Joburi încheiate", staleJob: "Învechit", attention: "Necesită intervenție", noAttention: "Niciun job nu necesită intervenție în acest domeniu.", scope: "Domeniul joburilor", all: "Toate proiectele autorizate",
    search: "Caută joburi", searchHelp: "Caută titluri și numere de tichete, proiecte, ID-uri, stări, etape sau rezultate salvate (maximum 80 de caractere).",
    now: "Ce se întâmplă acum", who: "Cine intervine", where: "Unde", follows: "Ce urmează",
    unknown: "Necunoscut — fără dovezi înregistrate", titleUnknown: "Titlul tichetului nu este înregistrat", personUnknown: "Persoana nu este înregistrată",
    evidenceMissing: "Dovezile salvate nu identifică locul intervenției. Consultă tichetul sau cere context operatorului.",
    openQuestion: "Răspunde pe tichet", openApproval: "Verifică versiunea pe platforma Git", openReview: "Verifică MR/PR-ul",
    responder: "Persoana care răspunde", approver: "Persoana care aprobă", reviewer: "Persoana care verifică", operator: "Operator", system: "ADORE / executor",
    oldActivity: "Ultima activitate înregistrată are peste 15 minute. Acest lucru singur nu arată dacă lucrul s-a oprit.", missingActivity: "Momentul activității nu este înregistrat.",
    workerUnavailable: "Worker indisponibil sau semnal învechit", workerError: "Starea workerului nu a putut fi citită", 
    incomplete: "Răspuns incomplet pentru joburi", incompleteHelp: "Totalurile și joburile sunt ascunse deoarece serverul nu confirmă dovezi complete.",
    changed: "Sursele joburilor s-au schimbat", changedHelp: "Revizia surselor s-a schimbat. Reîncarcă prima pagină pentru istoricul autorizat curent.", reload: "Reîncarcă prima pagină",
    consumption: "Consum", duration: "Durata jobului", unknownTelemetry: "Indisponibil în contractul dovezilor jobului.", technical: "Detalii tehnice", artifacts: "Dovezi și artefacte",
    observedTimeline: "Sunt afișate doar evenimentele salvate. Etapele neobservate, inclusiv cele omise pe traseul rapid, nu sunt marcate ca terminate.",
    reasonUnknown: "Motivul nu este înregistrat", approvalReason: "S-a cerut aprobarea versiunii salvate.", reviewReason: "Un MR/PR salvat așteaptă verificarea umană.",
    retryHelp: "Reîncercarea cere workerului recuperarea jobului eșuat prin contractul existent; nu ocolește validarea sau aprobarea.",
    cancelHelp: "Anularea cere oprirea și eliberarea resurselor. Workerul verifică din nou jobul și accesul înainte să acționeze.",
    queued: "Comandă în coadă — așteaptă workerul", running: "Comandă în execuție", succeeded: "Comandă terminată", failed: "Comandă eșuată", uncertain: "Rezultat incert — verifică înainte de retrimitere", commandError: "Starea comenzii nu poate fi citită; rezultatul este necunoscut.",
    pickup: "Monitorizare", pickupActive: "Activă", pickupStopped: "În pauză", pickupHelp: "Joburile active continuă când preluarea este oprită.", stopPickup: "Pune monitorizarea în pauză", startPickup: "Activează monitorizarea",
    verification: "Verificarea mediului", unverified: "Neverificat", stale: "Verificare învechită", invalid: "Configurație invalidă", passed: "Verificat", partial: "Verificat parțial", checkFailed: "Verificare eșuată",
    verificationHelp: "Verificarea este explicită și legată de revizia configurației salvate și momentul verificării.", summary: "Rezumat", settings: "Setări", history: "Istoric", historyHelp: "Joburile terminate, eșuate, anulate, învechite și predate unui om din acest proiect.",
  },
};

// Lifecycle explanations describe the engine contract; next actions remain conditional on evidence.
const explanations: Record<Locale, Record<Lifecycle, string>> = {
  en: {
    working: "ADORE is conducting the saved AEGIS stage. The executor may work within that stage; the last record is not a live progress signal.",
    publishing: "ADORE is publishing the approved candidate. An MR/PR is opened only after the engine's approval checks.",
    "parked-clarification": "Work is waiting for clarification. Answer the recorded question on the ticket when its location is available.",
    "awaiting-approval": "Work is waiting for human approval of the candidate. Approval is recorded on the forge and bound to the saved candidate.",
    "in-review": "The saved MR/PR is in human review. ADORE follows review evidence; merge remains a human decision.",
    "handoff-pending": "Transfer to a human is pending at a safe boundary. Further autonomous work is waiting for the handoff to finish.",
    "handed-off": "The job has been handed to a human. Autonomous execution has ended and the retained worktree is protected for human work.",
    done: "The job is completed. This lifecycle alone does not establish a human merge.",
    failed: "The job failed and retains recovery evidence. An authorized operator can request the existing retry operation.",
    cancelled: "The job was cancelled. Inspect retained evidence for the final recorded outcome.",
    stale: "The job is marked stale. Inspect the saved outcome and ask the operator to reconcile its history.",
  },
  fr: {
    working: "ADORE conduit l’étape AEGIS enregistrée. L’exécuteur peut y travailler ; le dernier événement n’est pas un indicateur de progression en direct.",
    publishing: "ADORE publie le candidat approuvé. Une MR/PR est ouverte après les contrôles d’approbation du moteur.",
    "parked-clarification": "Le travail attend une clarification. Répondez à la question enregistrée sur le ticket lorsque son emplacement est disponible.",
    "awaiting-approval": "Le travail attend l’approbation humaine du candidat, enregistrée sur la forge et liée au candidat sauvegardé.",
    "in-review": "La MR/PR sauvegardée est en revue humaine. ADORE suit les preuves de revue ; la fusion reste une décision humaine.",
    "handoff-pending": "Le transfert à un humain attend une frontière sûre. La poursuite autonome attend la fin du transfert.",
    "handed-off": "Le travail a été confié à un humain. L’exécution autonome est terminée et le worktree conservé est protégé.",
    done: "Le travail est terminé. Cet état seul ne prouve pas une fusion humaine.", failed: "Le travail a échoué et conserve les preuves de récupération. Un opérateur autorisé peut demander une nouvelle tentative.",
    cancelled: "Le travail a été annulé. Consultez les preuves conservées pour le résultat final enregistré.", stale: "Le travail est marqué périmé. Consultez le résultat sauvegardé et demandez une réconciliation à l’opérateur.",
  },
  de: {
    working: "ADORE steuert die gespeicherte AEGIS-Phase. Der Executor kann darin arbeiten; der letzte Eintrag ist kein Live-Fortschrittsindikator.",
    publishing: "ADORE veröffentlicht den genehmigten Kandidaten. Eine MR/PR wird nach den Genehmigungsprüfungen geöffnet.",
    "parked-clarification": "Die Arbeit wartet auf Klärung. Die gespeicherte Frage im Ticket beantworten, sobald der Ort verfügbar ist.",
    "awaiting-approval": "Die Arbeit wartet auf menschliche Kandidatengenehmigung. Diese wird auf der Forge gespeichert und an den Kandidaten gebunden.",
    "in-review": "Die gespeicherte MR/PR wird menschlich geprüft. ADORE folgt den Nachweisen; Zusammenführen bleibt eine menschliche Entscheidung.",
    "handoff-pending": "Die Übergabe an einen Menschen steht an einer sicheren Grenze aus. Weitere autonome Arbeit wartet auf den Abschluss.",
    "handed-off": "Der Job wurde einem Menschen übergeben. Autonome Ausführung ist beendet; der gespeicherte Worktree bleibt für menschliche Arbeit geschützt.",
    done: "Der Job ist abgeschlossen. Dieser Status allein belegt keine menschliche Zusammenführung.", failed: "Der Job ist fehlgeschlagen; Wiederherstellungsnachweise bleiben erhalten. Ein berechtigter Betreiber kann Wiederholen anfordern.",
    cancelled: "Der Job wurde abgebrochen. Gespeicherte Nachweise zeigen das letzte aufgezeichnete Ergebnis.", stale: "Der Job ist als veraltet markiert. Gespeichertes Ergebnis prüfen und den Betreiber um Abgleich bitten.",
  },
  ro: {
    working: "ADORE conduce etapa AEGIS salvată. Executorul poate lucra în acea etapă; ultima înregistrare nu este un indicator de progres în timp real.",
    publishing: "ADORE publică versiunea aprobată. Un MR/PR se deschide numai după verificările aprobării din motor.",
    "parked-clarification": "Lucrul așteaptă o clarificare. Răspunde la întrebarea înregistrată pe tichet când locul ei este disponibil.",
    "awaiting-approval": "Lucrul așteaptă aprobarea umană a versiunii. Aprobarea se înregistrează pe platforma Git și este legată de versiunea salvată.",
    "in-review": "MR/PR-ul salvat este în verificare umană. ADORE urmărește dovezile verificării; integrarea rămâne o decizie umană.",
    "handoff-pending": "Predarea către un om așteaptă o limită sigură. Continuarea autonomă așteaptă finalizarea predării.",
    "handed-off": "Jobul a fost predat unui om. Execuția autonomă s-a încheiat, iar worktree-ul păstrat este protejat pentru lucrul uman.",
    done: "Jobul este terminat. Această stare singură nu confirmă o integrare umană.", failed: "Jobul a eșuat și păstrează dovezile recuperării. Un operator autorizat poate cere reîncercarea existentă.",
    cancelled: "Jobul a fost anulat. Consultă dovezile păstrate pentru ultimul rezultat înregistrat.", stale: "Jobul este marcat învechit. Consultă rezultatul salvat și cere operatorului reconcilierea istoricului.",
  },
};
export const lifecycleExplanation = (locale: Locale, lifecycle: Lifecycle) => explanations[locale][lifecycle];


/** Runtime budgets are independent of token and financial statistics. */
export const budgetCopy = {
  en: {unavailable:"Current limits are unavailable. Saved consumption and recovery remain available. Check project settings.",title:"Job budgets",launches:"Executor launches",active:"Active work (seconds)",
    timing:"Current project limits apply before the next attempt, including resume. Waiting time is excluded; consumed work is retained. A running attempt keeps its timeout.",
    near:"Approaching a budget limit (90% used).",reached:"A budget limit has been reached. Raise it before resuming.",settings:"Adjust budgets in project Settings"},
  fr: {unavailable:"Les limites actuelles sont indisponibles. Consommation et reprise restent accessibles. Vérifiez les paramètres du projet.",title:"Budgets du travail",launches:"Lancements de l’exécuteur",active:"Travail actif (secondes)",
    timing:"Les limites actuelles du projet s’appliquent avant la prochaine tentative, y compris la reprise. L’attente est exclue ; le travail consommé est conservé. Une tentative en cours garde son délai.",
    near:"Une limite de budget approche (90 % utilisés).",reached:"Une limite de budget est atteinte. Augmentez-la avant de reprendre.",settings:"Ajuster les budgets dans les paramètres du projet"},
  de: {unavailable:"Aktuelle Grenzen sind nicht verfügbar. Verbrauch und Wiederherstellung bleiben sichtbar. Projekteinstellungen prüfen.",title:"Jobbudgets",launches:"Executorstarts",active:"Aktive Arbeit (Sekunden)",
    timing:"Aktuelle Projektgrenzen gelten vor dem nächsten Versuch, auch beim Fortsetzen. Wartezeit zählt nicht; verbrauchte Arbeit bleibt erhalten. Ein laufender Versuch behält sein Zeitlimit.",
    near:"Eine Budgetgrenze nähert sich (90 % verbraucht).",reached:"Eine Budgetgrenze ist erreicht. Vor dem Fortsetzen erhöhen.",settings:"Budgets in den Projekteinstellungen anpassen"},
  ro: {unavailable:"Limitele actuale nu sunt disponibile. Consumul salvat și recuperarea rămân accesibile. Verifică setările proiectului.",title:"Bugetele jobului",launches:"Lansări executor",active:"Lucru activ (secunde)",
    timing:"Limitele actuale ale proiectului se aplică înaintea următoarei încercări, inclusiv la reluare. Așteptarea este exclusă; consumul acumulat se păstrează. Încercarea în curs își păstrează limita de timp.",
    near:"Se apropie o limită de buget (90% consumat).",reached:"O limită de buget a fost atinsă. Majoreaz-o înainte de reluare.",settings:"Ajustează bugetele în Setările proiectului"},
} satisfies Record<Locale, Record<string,string>>;

/** Normal lifecycle guidance is conditional, never inferred telemetry. */
const guidance: Record<Locale, Record<string, [string, string, string]>> = {
  "en": {
    "working": [
      "This stage is being conducted; no human intervention is currently requested.",
      "ADORE manages this job’s working environment.",
      "ADORE checks the recorded result before advancing or attempting recovery."
    ],
    "parked-clarification": [
      "Waiting for a human answer to the agent’s question.",
      "The question location is not recorded; inspect the ticket with the operator.",
      "After an accepted answer, ADORE rechecks the job before continuing."
    ],
    "failed": [
      "Autonomous work has stopped. Inspect the retained failure evidence.",
      "Inspect this job’s evidence and project settings with the operator.",
      "An authorized operator can remediate the cause and request recovery."
    ]
  },
  "fr": {
    "working": [
      "Cette étape est en cours ; aucune intervention humaine n’est actuellement demandée.",
      "ADORE gère l’environnement de ce travail.",
      "ADORE vérifie le résultat enregistré avant de poursuivre ou de tenter une récupération."
    ],
    "parked-clarification": [
      "En attente d’une réponse humaine à la question de l’agent.",
      "L’emplacement de la question est absent ; consultez le ticket avec l’opérateur.",
      "Après une réponse acceptée, ADORE revérifie le travail avant de poursuivre."
    ],
    "failed": [
      "Le travail autonome est arrêté. Consultez les preuves d’échec conservées.",
      "Consultez les preuves du travail et les paramètres du projet avec l’opérateur.",
      "Un opérateur autorisé peut corriger la cause et demander une récupération."
    ]
  },
  "de": {
    "working": [
      "Diese Phase wird bearbeitet; derzeit ist kein menschlicher Eingriff angefordert.",
      "ADORE verwaltet die Arbeitsumgebung dieses Jobs.",
      "ADORE prüft das gespeicherte Ergebnis vor dem Fortsetzen oder einem Wiederherstellungsversuch."
    ],
    "parked-clarification": [
      "Eine menschliche Antwort auf die Frage des Agenten steht aus.",
      "Der Frageort ist nicht gespeichert; das Ticket mit dem Betreiber prüfen.",
      "Nach einer angenommenen Antwort prüft ADORE den Job vor dem Fortsetzen erneut."
    ],
    "failed": [
      "Autonome Arbeit wurde angehalten. Gespeicherte Fehlernachweise prüfen.",
      "Jobnachweise und Projekteinstellungen mit dem Betreiber prüfen.",
      "Ein berechtigter Betreiber kann die Ursache beheben und Wiederherstellung anfordern."
    ]
  },
  "ro": {
    "working": [
      "Această etapă este în lucru; momentan nu se cere intervenția unui om.",
      "ADORE gestionează mediul de lucru al acestui job.",
      "ADORE verifică rezultatul salvat înainte de avansare sau de o încercare de recuperare."
    ],
    "parked-clarification": [
      "Se așteaptă răspunsul unui om la întrebarea agentului.",
      "Locul întrebării nu este înregistrat; consultă tichetul împreună cu operatorul.",
      "După un răspuns acceptat, ADORE verifică din nou jobul înainte de continuare."
    ],
    "failed": [
      "Lucrul autonom s-a oprit. Consultă dovezile păstrate ale eșecului.",
      "Consultă dovezile jobului și setările proiectului împreună cu operatorul.",
      "Un operator autorizat poate remedia cauza și cere recuperarea."
    ]
  }
};
export function jobGuidance(locale: Locale, lifecycle: Lifecycle) {
  const [reason, where, follows] = guidance[locale][lifecycle] ?? [jobCopy[locale].reasonUnknown, jobCopy[locale].evidenceMissing, jobCopy[locale].unknown];
  return { reason, where, follows };
}
