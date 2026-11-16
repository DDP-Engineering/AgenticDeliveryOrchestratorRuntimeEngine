/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import type { Locale } from "./i18n";

/** Explain destructive recovery consistently in every supported locale. */
export const recoveryCopy: Record<Locale, { restart: string; restartAegis: string; restartDirect: string; confirm: string; drift: string; changed: string; failed: string; retained: string }> = {
  en: {
    retained: "A fresh job started. An older branch without ownership evidence was kept; a new branch is used.",
    restart: "Abandon and start again",
    restartAegis: "Abandon and restart with AEGIS",
    restartDirect: "Abandon and restart without AEGIS",
    confirm: "Discard existing work for ticket #{ticket} and restart?",
    drift: "Execution settings changed. Retry cannot replace the saved backend or stable settings. Restore those settings or abandon and start again. Retry can revalidate volatile environment changes, including processor variables after resizing a VM.",
    changed: "The confirmed job changed. Refresh Job details and review it before starting again.",
    failed: "Recovery was refused or incomplete. Inspect Job details and operation evidence. A new job requires successful owned cleanup.",
  },
  ro: {
    retained: "Jobul nou a pornit pe un branch nou. Branchul vechi fără dovezi de proprietate a fost păstrat.",
    restart: "Renunță și pornește din nou",
    restartAegis: "Renunță și repornește cu AEGIS",
    restartDirect: "Renunță și repornește fără AEGIS",
    confirm: "Ștergi lucrul existent pentru tichetul #{ticket} și repornești?",
    drift: "Setările de execuție s-au schimbat. Reîncercarea nu poate înlocui mediul sau setările stabile salvate. Restabilește setările sau renunță și pornește din nou. Reîncercarea poate revalida schimbările volatile ale mediului, inclusiv variabilele procesorului după redimensionarea unui VM.",
    changed: "Jobul confirmat s-a schimbat. Reîncarcă detaliile jobului și verifică-l înainte să pornești din nou.",
    failed: "Recuperarea a fost refuzată sau este incompletă. Consultă detaliile jobului și dovezile operației. Jobul nou necesită curățarea verificată a resurselor proprii.",
  },
  fr: {
    retained: "Une nouvelle tâche a démarré sur une nouvelle branche ; l’ancienne sans preuve a été conservée.",
    restart: "Abandonner et recommencer",
    restartAegis: "Abandonner et redémarrer avec AEGIS",
    restartDirect: "Abandonner et redémarrer sans AEGIS",
    confirm: "Supprimer le travail existant du ticket #{ticket} et redémarrer ?",
    drift: "Les paramètres d’exécution ont changé. Réessayer ne remplace pas le mode ou les paramètres stables enregistrés. Restaurez-les ou abandonnez et recommencez. Réessayer peut revalider les changements volatils de l’environnement, dont les variables processeur après redimensionnement d’une VM.",
    changed: "Le travail confirmé a changé. Actualisez ses détails et vérifiez-le avant de recommencer.",
    failed: "La récupération a été refusée ou reste incomplète. Consultez les détails et les preuves de l’opération. Un nouveau travail exige un nettoyage vérifié des ressources propres.",
  },
  de: {
    retained: "Ein neuer Auftrag nutzt einen neuen Branch. Der alte Branch ohne Eigentumsnachweis bleibt erhalten.",
    restart: "Verwerfen und neu starten",
    restartAegis: "Verwerfen und mit AEGIS neu starten",
    restartDirect: "Verwerfen und ohne AEGIS neu starten",
    confirm: "Bestehende Arbeit für Ticket #{ticket} verwerfen und neu starten?",
    drift: "Ausführungseinstellungen haben sich geändert. Wiederholen ersetzt weder die gespeicherte Ausführungsart noch feste Einstellungen. Stellen Sie diese wieder her oder verwerfen und starten Sie neu. Wiederholen kann veränderliche Umgebungswerte neu prüfen, auch Prozessorvariablen nach einer VM-Größenänderung.",
    changed: "Der bestätigte Job hat sich geändert. Aktualisieren und prüfen Sie die Jobdetails vor dem Neustart.",
    failed: "Wiederherstellung abgelehnt oder unvollständig. Prüfen Sie Jobdetails und Operationsnachweise. Ein neuer Job erfordert eine geprüfte Bereinigung eigener Ressourcen.",
  },
};
