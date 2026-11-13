/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import type { Locale } from "./i18n";
import { recoveryCopy } from "./recoveryCopy.ts";

const en = {
  sections: "Jobs sections", tickets: "Tickets", jobs: "Jobs",
  read: "Read tickets", reading: "Reading tickets…", lastRead: "Read at {time}",
  notRead: "Press Read tickets to load this project's open tickets from its repository. Nothing is read until you ask.",
  none: "This repository has no open tickets.", truncated: "Showing the first 500 open tickets.", page: "Page {page} of {pages}",
  number: "#", project: "Project", title: "Title", labels: "Labels", status: "Status", actions: "Actions",
  startable: "Ready to start", epic: "Epic cannot be started", not_open: "Not open", missing_ready_label: "Missing label {label}", held: "On hold",
  excluded: "Excluded from ADORE", has_job: "Has a job", missing_priority_label: "Missing priority label",
  missing_acceptance_criteria: "Missing acceptance criteria", job: "Job: {lifecycle}",
  start: "Start", stop: "Stop", details: "Details", hide: "Hide details",
  description: "Description", noDescription: "No description.", comments: "Comments",
  bodyDisplay: "Body display", rendered: "Rendered", markdownSource: "Markdown source", savingMode: "Saving display preference…",
  imageNotLoaded: "Image not loaded", code: "Code", table: "Table",
  loadingComments: "Loading comments…", noComments: "No comments.", by: "{author} · {time}",
  startQueued: "Start for #{iid} queued as operation #{id}.", startEffect: "Starts only this ticket, even with monitoring paused. All other checks still apply.",
  stopConfirm: "Stop #{iid}? This cancels its unfinished job, if any, and removes the {label} label so monitoring does not pick it up again. Cleanup may remove the worktree and unpublished work; job evidence remains.",
  stopTicket: "Stop ticket", keepRunning: "Keep running", keep: "Cancel",
  startConfirm: "Start #{iid}? ADORE adds {labels} to the ticket in the repository, then queues the job.", startTicket: "Add labels and start", priority: "Priority", labelsAdded: "Labels added: {labels}.", retry: "Retry", retryQueued: "Retry for #{iid} queued as operation #{id}.",
  cancelQueued: "Cancellation for #{iid} queued as operation #{id}.", noCancel: "#{iid} had no unfinished job to cancel.",
  labelRemoved: "Ready label removed.", labelAbsent: "The ticket had no ready label.",
  labelFailed: "The ready label could not be removed: {reason}",
  pickup_paused: "Monitoring paused",
  pickupStopped: "Monitoring is paused for this project, so Start is unavailable. An administrator activates monitoring in the project Summary.",
  labelsKept: "The ticket keeps the labels {labels}: ADORE picks it up when its pickup rules allow, and Stop removes them.",
  reviewChanged: "Project authority changed. Read tickets again and review the action.",
  operation: { pending: "queued", running: "running", succeeded: "finished", failed: "failed", uncertain: "outcome uncertain" },
};

type TicketCopy = typeof en;

const ro: TicketCopy = {
  sections: "Secțiuni lucrări", tickets: "Tichete", jobs: "Lucrări",
  read: "Citește tichetele", reading: "Se citesc tichetele…", lastRead: "Citite la {time}",
  notRead: "Apăsați Citește tichetele pentru a încărca tichetele deschise ale proiectului din depozit. Nimic nu se citește până nu cereți.",
  none: "Depozitul nu are tichete deschise.", truncated: "Se afișează primele 500 de tichete deschise.", page: "Pagina {page} din {pages}",
  number: "#", project: "Proiect", title: "Titlu", labels: "Etichete", status: "Stare", actions: "Acțiuni",
  startable: "Gata de pornire", epic: "Epicurile nu pot fi pornite", not_open: "Nu este deschis", missing_ready_label: "Lipsește eticheta {label}", held: "În așteptare",
  excluded: "Exclus din ADORE", has_job: "Are o lucrare", missing_priority_label: "Lipsește eticheta de prioritate",
  missing_acceptance_criteria: "Lipsesc criteriile de acceptare", job: "Lucrare: {lifecycle}",
  start: "Pornește", stop: "Oprește", details: "Detalii", hide: "Ascunde detaliile",
  description: "Descriere", noDescription: "Fără descriere.", comments: "Comentarii",
  bodyDisplay: "Afișarea conținutului", rendered: "Randat", markdownSource: "Sursă Markdown", savingMode: "Se salvează preferința de afișare…",
  imageNotLoaded: "Imagine neîncărcată", code: "Cod", table: "Tabel",
  loadingComments: "Se încarcă comentariile…", noComments: "Fără comentarii.", by: "{author} · {time}",
  startQueued: "Pornirea pentru #{iid} a fost pusă în coadă ca operația #{id}.", startEffect: "Pornește doar acest tichet, inclusiv cu monitorizarea în pauză. Celelalte verificări rămân active.",
  stopConfirm: "Opriți #{iid}? Se anulează lucrarea neterminată, dacă există, și se elimină eticheta {label}, ca monitorizarea să nu o mai preia. Curățarea poate șterge directorul de lucru și modificările nepublicate; dovezile rămân.",
  stopTicket: "Oprește tichetul", keepRunning: "Lasă să ruleze", keep: "Renunță",
  startConfirm: "Porniți #{iid}? ADORE adaugă {labels} la tichet în depozit, apoi pune lucrarea în coadă.", startTicket: "Adaugă etichetele și pornește", priority: "Prioritate", labelsAdded: "Etichete adăugate: {labels}.", retry: "Reia", retryQueued: "Reluarea pentru #{iid} a fost pusă în coadă ca operația #{id}.",
  cancelQueued: "Anularea pentru #{iid} a fost pusă în coadă ca operația #{id}.", noCancel: "#{iid} nu avea nicio lucrare neterminată de anulat.",
  labelRemoved: "Eticheta ready a fost eliminată.", labelAbsent: "Tichetul nu avea eticheta ready.",
  labelFailed: "Eticheta ready nu a putut fi eliminată: {reason}",
  pickup_paused: "Monitorizare în pauză",
  pickupStopped: "Monitorizarea este în pauză pentru acest proiect, deci Pornește nu este disponibil. Un administrator activează monitorizarea din Rezumatul proiectului.",
  labelsKept: "Tichetul păstrează etichetele {labels}: ADORE îl preia când regulile de preluare o permit, iar Oprește le elimină.",
  reviewChanged: "Drepturile proiectului s-au schimbat. Recitiți tichetele și revizuiți acțiunea.",
  operation: { pending: "în coadă", running: "în curs", succeeded: "finalizată", failed: "eșuată", uncertain: "rezultat incert" },
};

const fr: TicketCopy = {
  sections: "Sections des tâches", tickets: "Tickets", jobs: "Tâches",
  read: "Lire les tickets", reading: "Lecture des tickets…", lastRead: "Lus à {time}",
  notRead: "Appuyez sur Lire les tickets pour charger les tickets ouverts du projet depuis son dépôt. Rien n’est lu sans votre demande.",
  none: "Ce dépôt n’a aucun ticket ouvert.", truncated: "Affichage des 500 premiers tickets ouverts.", page: "Page {page} sur {pages}",
  number: "#", project: "Projet", title: "Titre", labels: "Étiquettes", status: "État", actions: "Actions",
  startable: "Prêt à démarrer", epic: "Une épopée ne peut pas démarrer", not_open: "Non ouvert", missing_ready_label: "Étiquette {label} manquante", held: "En attente",
  excluded: "Exclu d’ADORE", has_job: "A une tâche", missing_priority_label: "Étiquette de priorité manquante",
  missing_acceptance_criteria: "Critères d’acceptation manquants", job: "Tâche : {lifecycle}",
  start: "Démarrer", stop: "Arrêter", details: "Détails", hide: "Masquer les détails",
  description: "Description", noDescription: "Aucune description.", comments: "Commentaires",
  bodyDisplay: "Affichage du contenu", rendered: "Rendu", markdownSource: "Source Markdown", savingMode: "Enregistrement de la préférence d’affichage…",
  imageNotLoaded: "Image non chargée", code: "Code", table: "Tableau",
  loadingComments: "Chargement des commentaires…", noComments: "Aucun commentaire.", by: "{author} · {time}",
  startQueued: "Démarrage de #{iid} mis en file comme opération #{id}.", startEffect: "Démarre ce seul ticket, même en surveillance suspendue. Les autres contrôles restent actifs.",
  stopConfirm: "Arrêter #{iid} ? Sa tâche inachevée éventuelle est annulée et l’étiquette {label} est retirée pour que la surveillance ne la reprenne pas. Le nettoyage peut supprimer le dossier de travail et les changements non publiés ; les preuves restent.",
  stopTicket: "Arrêter le ticket", keepRunning: "Laisser tourner", keep: "Annuler",
  startConfirm: "Démarrer #{iid} ? ADORE ajoute {labels} au ticket dans le dépôt, puis met la tâche en file.", startTicket: "Ajouter les étiquettes et démarrer", priority: "Priorité", labelsAdded: "Étiquettes ajoutées : {labels}.", retry: "Relancer", retryQueued: "Relance de #{iid} mise en file comme opération #{id}.",
  cancelQueued: "Annulation de #{iid} mise en file comme opération #{id}.", noCancel: "#{iid} n’avait aucune tâche inachevée à annuler.",
  labelRemoved: "Étiquette ready retirée.", labelAbsent: "Le ticket n’avait pas l’étiquette ready.",
  labelFailed: "L’étiquette ready n’a pas pu être retirée : {reason}",
  pickup_paused: "Surveillance en pause",
  pickupStopped: "La surveillance est en pause pour ce projet : Démarrer est indisponible. Un administrateur active la surveillance dans le Résumé du projet.",
  labelsKept: "Le ticket garde les étiquettes {labels} : ADORE le prend en charge quand ses règles de sélection le permettent, et Arrêter les retire.",
  reviewChanged: "Les droits du projet ont changé. Relisez les tickets et vérifiez l’action.",
  operation: { pending: "en file", running: "en cours", succeeded: "terminée", failed: "échouée", uncertain: "résultat incertain" },
};

const de: TicketCopy = {
  sections: "Auftragsbereiche", tickets: "Tickets", jobs: "Aufträge",
  read: "Tickets lesen", reading: "Tickets werden gelesen …", lastRead: "Gelesen um {time}",
  notRead: "Drücken Sie Tickets lesen, um die offenen Tickets des Projekts aus seinem Repository zu laden. Ohne Ihre Anfrage wird nichts gelesen.",
  none: "Dieses Repository hat keine offenen Tickets.", truncated: "Die ersten 500 offenen Tickets werden angezeigt.", page: "Seite {page} von {pages}",
  number: "#", project: "Projekt", title: "Titel", labels: "Labels", status: "Status", actions: "Aktionen",
  startable: "Startbereit", epic: "Epic kann nicht gestartet werden", not_open: "Nicht offen", missing_ready_label: "Label {label} fehlt", held: "Angehalten",
  excluded: "Von ADORE ausgeschlossen", has_job: "Hat einen Auftrag", missing_priority_label: "Prioritätslabel fehlt",
  missing_acceptance_criteria: "Akzeptanzkriterien fehlen", job: "Auftrag: {lifecycle}",
  start: "Starten", stop: "Stoppen", details: "Details", hide: "Details ausblenden",
  description: "Beschreibung", noDescription: "Keine Beschreibung.", comments: "Kommentare",
  bodyDisplay: "Inhaltsanzeige", rendered: "Gerendert", markdownSource: "Markdown-Quelltext", savingMode: "Anzeigeeinstellung wird gespeichert …",
  imageNotLoaded: "Bild nicht geladen", code: "Code", table: "Tabelle",
  loadingComments: "Kommentare werden geladen …", noComments: "Keine Kommentare.", by: "{author} · {time}",
  startQueued: "Start für #{iid} als Vorgang #{id} eingereiht.", startEffect: "Startet nur dieses Ticket, auch bei pausierter Überwachung. Alle anderen Prüfungen gelten weiter.",
  stopConfirm: "#{iid} stoppen? Ein unvollständiger Auftrag wird abgebrochen und das Label {label} entfernt, damit die Überwachung das Ticket nicht erneut aufnimmt. Die Bereinigung kann Arbeitsverzeichnis und unveröffentlichte Arbeit löschen; Nachweise bleiben.",
  stopTicket: "Ticket stoppen", keepRunning: "Weiterlaufen lassen", keep: "Abbrechen",
  startConfirm: "#{iid} starten? ADORE fügt dem Ticket im Repository {labels} hinzu und reiht den Auftrag ein.", startTicket: "Labels hinzufügen und starten", priority: "Priorität", labelsAdded: "Labels hinzugefügt: {labels}.", retry: "Wiederholen", retryQueued: "Wiederholung für #{iid} als Vorgang #{id} eingereiht.",
  cancelQueued: "Abbruch für #{iid} als Vorgang #{id} eingereiht.", noCancel: "#{iid} hatte keinen unvollständigen Auftrag.",
  labelRemoved: "Ready-Label entfernt.", labelAbsent: "Das Ticket hatte kein Ready-Label.",
  labelFailed: "Das Ready-Label konnte nicht entfernt werden: {reason}",
  pickup_paused: "Überwachung pausiert",
  pickupStopped: "Die Überwachung ist für dieses Projekt pausiert, daher ist Starten nicht verfügbar. Ein Administrator aktiviert die Überwachung in der Projekt-Zusammenfassung.",
  labelsKept: "Das Ticket behält die Labels {labels}: ADORE übernimmt es, sobald seine Auswahlregeln es erlauben, und Stoppen entfernt sie.",
  reviewChanged: "Die Projektberechtigung hat sich geändert. Tickets erneut lesen und Aktion prüfen.",
  operation: { pending: "eingereiht", running: "läuft", succeeded: "abgeschlossen", failed: "fehlgeschlagen", uncertain: "Ergebnis unsicher" },
};

/** Localized Tickets sub-tab copy; forge ticket text itself is never translated. */
export const ticketCopy: Record<Locale, TicketCopy> = { en, ro, fr, de };

/** Replace `{name}` placeholders with plain-text values. */
export function fill(template: string, values: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (match, key: string) => key in values ? String(values[key]) : match);
}


const startReasonCopy: Record<Locale, Record<string, string>> = {
  en: {
    at_capacity: "The project's concurrent job limit has been reached.",
    workflow_unavailable: "Repository workflow files are missing, incompatible or unavailable.",
    ticket_unavailable: "The selected ticket could not be found or read.",
    project_archived: "The project is archived. Restore it before starting work.",
    configuration_invalid: "The project configuration is missing or invalid.",
    engine_setup_failed: "The execution environment could not be initialized. Check the host configuration.",
    lock_held: "Another conductor or operation holds the project lock. Wait for it to finish.",
    repository_unavailable: "The repository could not be read. Check repository sign-in and connectivity.",
    state_unavailable: "Project run state is unavailable or corrupt. Inspect the host logs.",
    engine_fault: "The engine encountered an error while starting the ticket. Inspect the host logs.",
    invalid_request: "Manual Start requires a positive ticket number and a single run.",
    not_eligible: "The ticket no longer meets the project's start rules. Read tickets again.",
    epic: "This ticket is an epic and cannot be started.",
    not_open: "The ticket is no longer open.", missing_ready_label: "The ticket's ready label is missing.",
    held: "The ticket is on hold.", excluded: "The ticket is excluded from ADORE.",
    has_job: "The ticket already has a job.", missing_priority_label: "The ticket's priority label is missing.",
    missing_acceptance_criteria: "The required acceptance criteria are missing.",
    invalid_result: "The engine returned no valid start result. Inspect the host logs before retrying.",
  },
  ro: {
    at_capacity: "S-a atins limita de lucrări simultane a proiectului.",
    workflow_unavailable: "Fișierele fluxului din repository lipsesc, sunt incompatibile sau inaccesibile.",
    ticket_unavailable: "Tichetul selectat nu a putut fi găsit sau citit.",
    project_archived: "Proiectul este arhivat. Restaurează-l înainte de pornire.",
    configuration_invalid: "Configurația proiectului lipsește sau nu este validă.",
    engine_setup_failed: "Mediul de execuție nu a putut fi inițializat. Verifică setările gazdei.",
    lock_held: "Alt conductor sau altă operație deține blocarea proiectului. Așteaptă finalizarea.",
    repository_unavailable: "Repository-ul nu a putut fi citit. Verifică autentificarea și conexiunea.",
    state_unavailable: "Starea lucrărilor este inaccesibilă sau coruptă. Consultă logurile gazdei.",
    engine_fault: "Motorul a întâmpinat o eroare la pornirea tichetului. Consultă logurile gazdei.",
    invalid_request: "Pornirea manuală cere un număr pozitiv de tichet și o singură rulare.",
    not_eligible: "Tichetul nu mai respectă regulile de pornire. Citește din nou tichetele.",
    epic: "Tichetul este un epic și nu poate fi pornit.",
    not_open: "Tichetul nu mai este deschis.", missing_ready_label: "Lipsește eticheta ready a tichetului.",
    held: "Tichetul este blocat.", excluded: "Tichetul este exclus din ADORE.",
    has_job: "Tichetul are deja o lucrare.", missing_priority_label: "Lipsește eticheta de prioritate.",
    missing_acceptance_criteria: "Lipsesc criteriile de acceptare cerute.",
    invalid_result: "Motorul nu a returnat un rezultat valid. Consultă logurile gazdei înainte de reluare.",
  },
  fr: {
    at_capacity: "La limite des tâches simultanées du projet est atteinte.",
    workflow_unavailable: "Les fichiers du workflow sont absents, incompatibles ou inaccessibles.",
    ticket_unavailable: "Le ticket sélectionné est introuvable ou illisible.",
    project_archived: "Le projet est archivé. Restaurez-le avant de démarrer.",
    configuration_invalid: "La configuration du projet est absente ou invalide.",
    engine_setup_failed: "L'environnement d'exécution ne peut pas être initialisé. Vérifiez l'hôte.",
    lock_held: "Un autre conducteur ou une opération verrouille le projet. Attendez sa fin.",
    repository_unavailable: "Le dépôt est illisible. Vérifiez la connexion au dépôt et au réseau.",
    state_unavailable: "L'état des tâches est inaccessible ou corrompu. Consultez les journaux de l'hôte.",
    engine_fault: "Le moteur a échoué au démarrage du ticket. Consultez les journaux de l'hôte.",
    invalid_request: "Le démarrage manuel exige un numéro de ticket positif et une seule exécution.",
    not_eligible: "Le ticket ne respecte plus les règles de démarrage. Relisez les tickets.",
    epic: "Ce ticket est une épopée et ne peut pas démarrer.",
    not_open: "Le ticket n'est plus ouvert.", missing_ready_label: "L'étiquette ready du ticket manque.",
    held: "Le ticket est en attente.", excluded: "Le ticket est exclu d'ADORE.",
    has_job: "Le ticket a déjà une tâche.", missing_priority_label: "L'étiquette de priorité manque.",
    missing_acceptance_criteria: "Les critères d'acceptation requis manquent.",
    invalid_result: "Aucun résultat de démarrage valide. Consultez les journaux avant de réessayer.",
  },
  de: {
    at_capacity: "Die Grenze gleichzeitiger Aufträge des Projekts ist erreicht.",
    workflow_unavailable: "Workflow-Dateien fehlen, sind inkompatibel oder nicht erreichbar.",
    ticket_unavailable: "Das ausgewählte Ticket wurde nicht gefunden oder konnte nicht gelesen werden.",
    project_archived: "Das Projekt ist archiviert. Stellen Sie es vor dem Start wieder her.",
    configuration_invalid: "Die Projektkonfiguration fehlt oder ist ungültig.",
    engine_setup_failed: "Die Ausführungsumgebung konnte nicht initialisiert werden. Prüfen Sie den Host.",
    lock_held: "Ein anderer Conductor oder Vorgang sperrt das Projekt. Warten Sie auf dessen Abschluss.",
    repository_unavailable: "Das Repository ist nicht lesbar. Prüfen Sie Anmeldung und Verbindung.",
    state_unavailable: "Der Auftragszustand ist unzugänglich oder beschädigt. Prüfen Sie die Host-Protokolle.",
    engine_fault: "Der Ticketstart ist im Engine fehlgeschlagen. Prüfen Sie die Host-Protokolle.",
    invalid_request: "Ein manueller Start erfordert eine positive Ticketnummer und einen einzelnen Lauf.",
    not_eligible: "Das Ticket erfüllt die Startregeln nicht mehr. Lesen Sie die Tickets erneut.",
    epic: "Dieses Ticket ist ein Epic und kann nicht gestartet werden.",
    not_open: "Das Ticket ist nicht mehr offen.", missing_ready_label: "Das Ready-Label des Tickets fehlt.",
    held: "Das Ticket ist angehalten.", excluded: "Das Ticket ist von ADORE ausgeschlossen.",
    has_job: "Das Ticket hat bereits einen Auftrag.", missing_priority_label: "Das Prioritätslabel fehlt.",
    missing_acceptance_criteria: "Die erforderlichen Akzeptanzkriterien fehlen.",
    invalid_result: "Kein gültiges Startergebnis. Prüfen Sie vor einem erneuten Versuch die Host-Protokolle.",
  },
};

const retryReasonCopy: Record<Locale, Record<string, string>> = {
  en: {
    executable_missing: "The installed executor is unavailable. Check its executable in Agent and model.",
    account_mismatch: "The local account or its home folder is unavailable. Check Agent and model.",
    permission_denied: "The ADORE account lacks permission to access the local executor or runtime.",
    run_unavailable: "The job or its repository ticket is unavailable.",
    not_failed: "Only failed jobs can be retried.",
    notification_pending: "A required repository notification is still pending. Deliver it before retrying.",
    reprepare_unavailable: "Preparation cannot be replayed for this job or its retry limit was reached.",
    invalid_result: "No valid Retry result. Inspect the job details before retrying again.",
    engine_fault: "Retry encountered an engine error. Inspect the host logs.",
    failed: "Retry failed: ",
  },
  ro: {
    executable_missing: "Executorul instalat este inaccesibil. Verifică executabilul în Agent și model.",
    account_mismatch: "Contul local sau directorul său personal este inaccesibil. Verifică Agent și model.",
    permission_denied: "Contul ADORE nu are permisiuni pentru executorul local sau mediul de execuție.",
    run_unavailable: "Lucrarea sau tichetul său din repository este inaccesibil.",
    not_failed: "Se pot relua doar lucrările eșuate.",
    notification_pending: "O notificare obligatorie către repository este în așteptare. Trimite-o înainte de reluare.",
    reprepare_unavailable: "Pregătirea nu poate fi repetată sau s-a atins limita de încercări.",
    invalid_result: "Rezultatul reluării nu este valid. Consultă detaliile lucrării înainte de o nouă încercare.",
    engine_fault: "Reluarea a întâmpinat o eroare a motorului. Consultă logurile gazdei.",
    failed: "Reluarea a eșuat: ",
  },
  fr: {
    executable_missing: "L’exécuteur installé est inaccessible. Vérifiez son programme dans Agent et modèle.",
    account_mismatch: "Le compte local ou son dossier personnel est inaccessible. Vérifiez Agent et modèle.",
    permission_denied: "Le compte ADORE n’a pas accès à l’exécuteur local ou à son environnement.",
    run_unavailable: "La tâche ou son ticket dans le dépôt est inaccessible.",
    not_failed: "Seules les tâches échouées peuvent être relancées.",
    notification_pending: "Une notification obligatoire au dépôt est en attente. Envoyez-la avant de relancer.",
    reprepare_unavailable: "La préparation ne peut pas être rejouée ou sa limite est atteinte.",
    invalid_result: "Résultat de relance invalide. Consultez la tâche avant de réessayer.",
    engine_fault: "La relance a rencontré une erreur du moteur. Consultez les journaux de l'hôte.",
    failed: "Échec de la relance : ",
  },
  de: {
    executable_missing: "Der installierte Executor ist nicht erreichbar. Prüfen Sie Agent und Modell.",
    account_mismatch: "Das lokale Konto oder sein Benutzerordner ist nicht verfügbar. Prüfen Sie Agent und Modell.",
    permission_denied: "Dem ADORE-Konto fehlen Zugriffsrechte auf den lokalen Executor oder die Laufzeit.",
    run_unavailable: "Der Auftrag oder sein Repository-Ticket ist nicht erreichbar.",
    not_failed: "Nur fehlgeschlagene Aufträge können wiederholt werden.",
    notification_pending: "Eine erforderliche Repository-Nachricht steht aus. Senden Sie diese vor der Wiederholung.",
    reprepare_unavailable: "Die Vorbereitung kann nicht wiederholt werden oder ihr Versuchslimit ist erreicht.",
    invalid_result: "Ungültiges Wiederholungsergebnis. Prüfen Sie vor einem neuen Versuch die Auftragsdetails.",
    engine_fault: "Bei der Wiederholung trat ein Engine-Fehler auf. Prüfen Sie die Host-Protokolle.",
    failed: "Wiederholung fehlgeschlagen: ",
  },
};

/** Render bound Start/Retry results and the job's persisted terminal cause. */
export function operationResultText(result: string, locale: Locale): string {
  if (result.startsWith("restart:")) return result === "restart:job_changed" ? recoveryCopy[locale].changed : result === "restart:retained" ? recoveryCopy[locale].retained : recoveryCopy[locale].failed;
  if (result.startsWith("retry:")) {
    const copy = { ...startReasonCopy[locale], ...retryReasonCopy[locale] };
    if (result.startsWith("retry:failed:")) return copy.failed + result.slice(13);
    const reason = result.slice(6);
    return Object.hasOwn(copy, reason) ? copy[reason] : copy.invalid_result;
  }
  if (!result.startsWith("start:")) return result;
  const copy = startReasonCopy[locale];
  const reason = result.slice(6);
  return Object.hasOwn(copy, reason) ? copy[reason] : copy.invalid_result;
}
