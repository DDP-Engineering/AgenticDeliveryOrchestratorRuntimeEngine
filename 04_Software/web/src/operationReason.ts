/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import type { Locale } from "./i18n";

/** Stable codes the worker records when the engine refuses a queued Start. */
export const OPERATION_REASONS = ["pickup_paused", "at_capacity", "aegis_probe_failed", "not_eligible", "conductor_busy"] as const;
type Reason = typeof OPERATION_REASONS[number];

const sentences: Record<Locale, Record<Reason, string>> = {
  en: {
    pickup_paused: "Not started: monitoring is paused for this project. An administrator uses Activate monitoring in the project Summary.",
    at_capacity: "Not started: all execution slots are busy.",
    aegis_probe_failed: "Not started: the AEGIS check of the repository failed; see the lines below.",
    not_eligible: "Not started: the ticket no longer meets the pickup rules. Read the tickets again.",
    conductor_busy: "Not started: another ADORE process is working on this project. Try again when it finishes.",
  },
  fr: {
    pickup_paused: "Non démarré : la surveillance est en pause pour ce projet. Un administrateur utilise Activer la surveillance dans le Résumé du projet.",
    at_capacity: "Non démarré : tous les emplacements d’exécution sont occupés.",
    aegis_probe_failed: "Non démarré : la vérification AEGIS du dépôt a échoué ; voir les lignes ci-dessous.",
    not_eligible: "Non démarré : le ticket ne respecte plus les règles de sélection. Relisez les tickets.",
    conductor_busy: "Non démarré : un autre processus ADORE travaille sur ce projet. Réessayez quand il a terminé.",
  },
  de: {
    pickup_paused: "Nicht gestartet: Die Überwachung ist für dieses Projekt pausiert. Ein Administrator nutzt Überwachung aktivieren in der Projekt-Zusammenfassung.",
    at_capacity: "Nicht gestartet: Alle Ausführungsplätze sind belegt.",
    aegis_probe_failed: "Nicht gestartet: Die AEGIS-Prüfung des Repositorys ist fehlgeschlagen; siehe die Zeilen unten.",
    not_eligible: "Nicht gestartet: Das Ticket erfüllt die Auswahlregeln nicht mehr. Lesen Sie die Tickets erneut.",
    conductor_busy: "Nicht gestartet: Ein anderer ADORE-Prozess arbeitet an diesem Projekt. Versuchen Sie es erneut, wenn er fertig ist.",
  },
  ro: {
    pickup_paused: "Nepornit: monitorizarea este în pauză pentru acest proiect. Un administrator folosește Activează monitorizarea din Rezumatul proiectului.",
    at_capacity: "Nepornit: toate sloturile de execuție sunt ocupate.",
    aegis_probe_failed: "Nepornit: verificarea AEGIS a depozitului a eșuat; vedeți liniile de mai jos.",
    not_eligible: "Nepornit: tichetul nu mai respectă regulile de preluare. Citiți din nou tichetele.",
    conductor_busy: "Nepornit: alt proces ADORE lucrează la acest proiect. Încercați din nou după ce termină.",
  },
};

const ownershipSentences = {
  en: {
    permission_revoked: "Request refused: your access has changed.",
    project_identity_changed: "The requested project no longer exists. Refresh the project list.",
    project_archived: "The project is archived. Restore it before requesting this action.",
    project_corrupt: "Project information is unavailable. Ask the administrator to inspect it.",
    owner_dead: "The worker stopped before confirming the result. Inspect the job before retrying.",
    cancel_unconfirmed: "Stopping the job is not confirmed. Inspect its current state before retrying.",
  },
  fr: {
    permission_revoked: "Demande refusée : vos droits ont changé.",
    project_identity_changed: "Le projet demandé n’existe plus. Actualisez la liste des projets.",
    project_archived: "Le projet est archivé. Restaurez-le avant cette action.",
    project_corrupt: "Les informations du projet sont indisponibles. Contactez l’administrateur.",
    owner_dead: "Le service s’est arrêté sans confirmer le résultat. Vérifiez la tâche avant de réessayer.",
    cancel_unconfirmed: "L’arrêt de la tâche n’est pas confirmé. Vérifiez son état avant de réessayer.",
  },
  de: {
    permission_revoked: "Anfrage abgelehnt: Ihre Zugriffsrechte haben sich geändert.",
    project_identity_changed: "Das angeforderte Projekt existiert nicht mehr. Aktualisieren Sie die Projektliste.",
    project_archived: "Das Projekt ist archiviert. Stellen Sie es vor dieser Aktion wieder her.",
    project_corrupt: "Projektinformationen sind nicht verfügbar. Bitten Sie den Administrator um Prüfung.",
    owner_dead: "Der Dienst endete ohne bestätigtes Ergebnis. Prüfen Sie den Auftrag vor dem Wiederholen.",
    cancel_unconfirmed: "Der Auftragsstopp ist nicht bestätigt. Prüfen Sie vor dem Wiederholen den Status.",
  },
  ro: {
    permission_revoked: "Cerere refuzată: drepturile de acces s-au schimbat.",
    project_identity_changed: "Proiectul cerut nu mai există. Reîmprospătează lista proiectelor.",
    project_archived: "Proiectul este arhivat. Restaurează-l înainte de această acțiune.",
    project_corrupt: "Informațiile proiectului nu sunt disponibile. Cere verificarea administratorului.",
    owner_dead: "Serviciul s-a oprit fără să confirme rezultatul. Verifică lucrarea înainte de reluare.",
    cancel_unconfirmed: "Oprirea lucrării nu este confirmată. Verifică starea ei înainte de reluare.",
  },
} satisfies Record<Locale, Record<string, string>>;

/** The localized sentence for a refusal reason, or null for an empty or unknown code. */
export function reasonSentence(locale: Locale, reason: string | undefined): string | null {
  if (reason && Object.hasOwn(ownershipSentences[locale], reason)) {
    return ownershipSentences[locale][reason as keyof typeof ownershipSentences.en];
  }
  return reason && (OPERATION_REASONS as readonly string[]).includes(reason) ? sentences[locale][reason as Reason] : null;
}

/** Labels a Start added that stay on the ticket because the engine refused the start. */
export function keptLabels(operation: { status: string; reason?: string } | undefined, labels: string[] | undefined): string[] {
  // Only a named refusal proves no job started; an uncertain or unexplained failure may have run one.
  return operation?.status === "failed" && (OPERATION_REASONS as readonly string[]).includes(operation.reason ?? "") ? labels ?? [] : [];
}

/** The text that describes an operation's outcome: the reason sentence, else the stored result. */
export function outcomeText(locale: Locale, operation: { result?: string; reason?: string }): string {
  return reasonSentence(locale, operation.reason) ?? operation.result ?? "";
}
