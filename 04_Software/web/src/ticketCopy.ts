/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import type { Locale } from "./i18n";

const en = {
  sections: "Jobs sections", tickets: "Tickets", jobs: "Jobs",
  read: "Read tickets", reading: "Reading tickets…", lastRead: "Read at {time}",
  notRead: "Press Read tickets to load this project's open tickets from its repository. Nothing is read until you ask.",
  none: "This repository has no open tickets.", truncated: "Showing the first 500 open tickets.",
  number: "#", project: "Project", title: "Title", labels: "Labels", status: "Status", actions: "Actions",
  startable: "Ready to start", not_open: "Not open", missing_ready_label: "Missing label {label}", held: "On hold",
  excluded: "Excluded from ADORE", has_job: "Has a job", missing_priority_label: "Missing priority label",
  missing_acceptance_criteria: "Missing acceptance criteria", job: "Job: {lifecycle}",
  start: "Start", stop: "Stop", details: "Details", hide: "Hide details",
  description: "Description", noDescription: "No description.", comments: "Comments",
  loadingComments: "Loading comments…", noComments: "No comments.", by: "{author} · {time}",
  startQueued: "Start for #{iid} queued as operation #{id}.", startEffect: "The worker will attempt this existing ticket through the configured selection, readiness and approval gates.",
  stopConfirm: "Stop #{iid}? This cancels its unfinished job, if any, and removes the {label} label so monitoring does not pick it up again.",
  stopTicket: "Stop ticket", keepRunning: "Keep running", keep: "Cancel",
  startConfirm: "Start #{iid}? ADORE adds {labels} to the ticket in the repository, then queues the job.", startTicket: "Add labels and start", priority: "Priority", labelsAdded: "Labels added: {labels}.", retry: "Retry", retryQueued: "Retry for #{iid} queued as operation #{id}.",
  cancelQueued: "Cancellation for #{iid} queued as operation #{id}.", noCancel: "#{iid} had no unfinished job to cancel.",
  labelRemoved: "Ready label removed.", labelAbsent: "The ticket had no ready label.",
  labelFailed: "The ready label could not be removed: {reason}",
  operation: { pending: "queued", running: "running", succeeded: "finished", failed: "failed", uncertain: "outcome uncertain" },
};

type TicketCopy = typeof en;

const ro: TicketCopy = {
  sections: "Secțiuni lucrări", tickets: "Tichete", jobs: "Lucrări",
  read: "Citește tichetele", reading: "Se citesc tichetele…", lastRead: "Citite la {time}",
  notRead: "Apăsați Citește tichetele pentru a încărca tichetele deschise ale proiectului din depozit. Nimic nu se citește până nu cereți.",
  none: "Depozitul nu are tichete deschise.", truncated: "Se afișează primele 500 de tichete deschise.",
  number: "#", project: "Proiect", title: "Titlu", labels: "Etichete", status: "Stare", actions: "Acțiuni",
  startable: "Gata de pornire", not_open: "Nu este deschis", missing_ready_label: "Lipsește eticheta {label}", held: "În așteptare",
  excluded: "Exclus din ADORE", has_job: "Are o lucrare", missing_priority_label: "Lipsește eticheta de prioritate",
  missing_acceptance_criteria: "Lipsesc criteriile de acceptare", job: "Lucrare: {lifecycle}",
  start: "Pornește", stop: "Oprește", details: "Detalii", hide: "Ascunde detaliile",
  description: "Descriere", noDescription: "Fără descriere.", comments: "Comentarii",
  loadingComments: "Se încarcă comentariile…", noComments: "Fără comentarii.", by: "{author} · {time}",
  startQueued: "Pornirea pentru #{iid} a fost pusă în coadă ca operația #{id}.", startEffect: "Workerul va încerca acest tichet existent prin regulile configurate de selecție, pregătire și aprobare.",
  stopConfirm: "Opriți #{iid}? Se anulează lucrarea neterminată, dacă există, și se elimină eticheta {label}, ca monitorizarea să nu o mai preia.",
  stopTicket: "Oprește tichetul", keepRunning: "Lasă să ruleze", keep: "Renunță",
  startConfirm: "Porniți #{iid}? ADORE adaugă {labels} la tichet în depozit, apoi pune lucrarea în coadă.", startTicket: "Adaugă etichetele și pornește", priority: "Prioritate", labelsAdded: "Etichete adăugate: {labels}.", retry: "Reia", retryQueued: "Reluarea pentru #{iid} a fost pusă în coadă ca operația #{id}.",
  cancelQueued: "Anularea pentru #{iid} a fost pusă în coadă ca operația #{id}.", noCancel: "#{iid} nu avea nicio lucrare neterminată de anulat.",
  labelRemoved: "Eticheta ready a fost eliminată.", labelAbsent: "Tichetul nu avea eticheta ready.",
  labelFailed: "Eticheta ready nu a putut fi eliminată: {reason}",
  operation: { pending: "în coadă", running: "în curs", succeeded: "finalizată", failed: "eșuată", uncertain: "rezultat incert" },
};

const fr: TicketCopy = {
  sections: "Sections des tâches", tickets: "Tickets", jobs: "Tâches",
  read: "Lire les tickets", reading: "Lecture des tickets…", lastRead: "Lus à {time}",
  notRead: "Appuyez sur Lire les tickets pour charger les tickets ouverts du projet depuis son dépôt. Rien n’est lu sans votre demande.",
  none: "Ce dépôt n’a aucun ticket ouvert.", truncated: "Affichage des 500 premiers tickets ouverts.",
  number: "#", project: "Projet", title: "Titre", labels: "Étiquettes", status: "État", actions: "Actions",
  startable: "Prêt à démarrer", not_open: "Non ouvert", missing_ready_label: "Étiquette {label} manquante", held: "En attente",
  excluded: "Exclu d’ADORE", has_job: "A une tâche", missing_priority_label: "Étiquette de priorité manquante",
  missing_acceptance_criteria: "Critères d’acceptation manquants", job: "Tâche : {lifecycle}",
  start: "Démarrer", stop: "Arrêter", details: "Détails", hide: "Masquer les détails",
  description: "Description", noDescription: "Aucune description.", comments: "Commentaires",
  loadingComments: "Chargement des commentaires…", noComments: "Aucun commentaire.", by: "{author} · {time}",
  startQueued: "Démarrage de #{iid} mis en file comme opération #{id}.", startEffect: "Le worker tentera ce ticket existant selon les règles configurées de sélection, préparation et approbation.",
  stopConfirm: "Arrêter #{iid} ? Sa tâche inachevée éventuelle est annulée et l’étiquette {label} est retirée pour que la surveillance ne la reprenne pas.",
  stopTicket: "Arrêter le ticket", keepRunning: "Laisser tourner", keep: "Annuler",
  startConfirm: "Démarrer #{iid} ? ADORE ajoute {labels} au ticket dans le dépôt, puis met la tâche en file.", startTicket: "Ajouter les étiquettes et démarrer", priority: "Priorité", labelsAdded: "Étiquettes ajoutées : {labels}.", retry: "Relancer", retryQueued: "Relance de #{iid} mise en file comme opération #{id}.",
  cancelQueued: "Annulation de #{iid} mise en file comme opération #{id}.", noCancel: "#{iid} n’avait aucune tâche inachevée à annuler.",
  labelRemoved: "Étiquette ready retirée.", labelAbsent: "Le ticket n’avait pas l’étiquette ready.",
  labelFailed: "L’étiquette ready n’a pas pu être retirée : {reason}",
  operation: { pending: "en file", running: "en cours", succeeded: "terminée", failed: "échouée", uncertain: "résultat incertain" },
};

const de: TicketCopy = {
  sections: "Auftragsbereiche", tickets: "Tickets", jobs: "Aufträge",
  read: "Tickets lesen", reading: "Tickets werden gelesen …", lastRead: "Gelesen um {time}",
  notRead: "Drücken Sie Tickets lesen, um die offenen Tickets des Projekts aus seinem Repository zu laden. Ohne Ihre Anfrage wird nichts gelesen.",
  none: "Dieses Repository hat keine offenen Tickets.", truncated: "Die ersten 500 offenen Tickets werden angezeigt.",
  number: "#", project: "Projekt", title: "Titel", labels: "Labels", status: "Status", actions: "Aktionen",
  startable: "Startbereit", not_open: "Nicht offen", missing_ready_label: "Label {label} fehlt", held: "Angehalten",
  excluded: "Von ADORE ausgeschlossen", has_job: "Hat einen Auftrag", missing_priority_label: "Prioritätslabel fehlt",
  missing_acceptance_criteria: "Akzeptanzkriterien fehlen", job: "Auftrag: {lifecycle}",
  start: "Starten", stop: "Stoppen", details: "Details", hide: "Details ausblenden",
  description: "Beschreibung", noDescription: "Keine Beschreibung.", comments: "Kommentare",
  loadingComments: "Kommentare werden geladen …", noComments: "Keine Kommentare.", by: "{author} · {time}",
  startQueued: "Start für #{iid} als Vorgang #{id} eingereiht.", startEffect: "Der Worker versucht dieses vorhandene Ticket über die konfigurierten Auswahl-, Bereitschafts- und Genehmigungsschritte.",
  stopConfirm: "#{iid} stoppen? Ein unvollständiger Auftrag wird abgebrochen und das Label {label} entfernt, damit die Überwachung das Ticket nicht erneut aufnimmt.",
  stopTicket: "Ticket stoppen", keepRunning: "Weiterlaufen lassen", keep: "Abbrechen",
  startConfirm: "#{iid} starten? ADORE fügt dem Ticket im Repository {labels} hinzu und reiht den Auftrag ein.", startTicket: "Labels hinzufügen und starten", priority: "Priorität", labelsAdded: "Labels hinzugefügt: {labels}.", retry: "Wiederholen", retryQueued: "Wiederholung für #{iid} als Vorgang #{id} eingereiht.",
  cancelQueued: "Abbruch für #{iid} als Vorgang #{id} eingereiht.", noCancel: "#{iid} hatte keinen unvollständigen Auftrag.",
  labelRemoved: "Ready-Label entfernt.", labelAbsent: "Das Ticket hatte kein Ready-Label.",
  labelFailed: "Das Ready-Label konnte nicht entfernt werden: {reason}",
  operation: { pending: "eingereiht", running: "läuft", succeeded: "abgeschlossen", failed: "fehlgeschlagen", uncertain: "Ergebnis unsicher" },
};

/** Localized Tickets sub-tab copy; forge ticket text itself is never translated. */
export const ticketCopy: Record<Locale, TicketCopy> = { en, ro, fr, de };

/** Replace `{name}` placeholders with plain-text values. */
export function fill(template: string, values: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (match, key: string) => key in values ? String(values[key]) : match);
}
