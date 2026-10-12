/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import type { Locale } from "./i18n";
import { portableFields } from "./portable";

const en = {
  sources: "Clone from", file: "From a portable settings file", project: "From a project on this server",
  source: "Source project", choose: "Choose a source project",
  upload: "Portable JSON file", review: "Review source rules", target: "Set up new target", back: "Review source again",
  title: "Portable rules for a new project", recognized: "Recognized working rules",
  help: "Transfer rules only. Supply a new identity, repository clone and target environment. The server allocates independent state, worktree and metrics locations; no repository is cloned.",
  exclusions: "No jobs, history, users, grants, audit, pending changes, secrets or source resource ownership are copied. Identity, host paths, labels, credentials and endpoint references are excluded.",
  integrity: "The checksum detects changes; it does not authenticate a file. Review an untrusted package before using its rules.",
  sourceValue: "Source value", serverValue: "This server value", effect: "Effect", copied: "Copy as working rule",
  defaults: "This server value means the installed rule default. Creation uses the source rules shown here.",
  revision: "Source revision", confirm: "I reconfirm this target environment, credential references and endpoint setup.",
  references: "Enter target credential environment names or select supported host authentication. No source credentials or endpoints transfer. Standard provider connections use the selected model; custom endpoint setup is a separate target Settings action while pickup remains stopped.",
  blocked: "Select and review a supported source before continuing.", changed: "Source or candidate changed. Review the source again, then validate a new target review.",
  paths: "Independent target locations", cancel: "Cancel", loading: "Reading source…",
};

export const transferCopy: Record<Locale, typeof en> = {
  en,
  fr: {
    sources: "Cloner depuis", file: "Depuis un fichier de paramètres portables", project: "Depuis un projet de ce serveur",
    source: "Projet source", choose: "Choisir un projet source",
    upload: "Fichier JSON portable", review: "Examiner les règles source", target: "Configurer la nouvelle cible", back: "Revoir la source",
    title: "Règles portables pour un nouveau projet", recognized: "Règles reconnues",
    help: "Seules les règles sont transférées. Saisissez une nouvelle identité, un clone existant et un environnement cible. Le serveur attribue des emplacements indépendants pour les données, worktrees et métriques ; aucun dépôt n’est cloné.",
    exclusions: "Aucun job, historique, utilisateur, droit, audit, changement en attente, secret ou propriété des ressources source n’est copié. Identité, chemins, labels et références de connexion sont exclus.",
    integrity: "La somme détecte les modifications sans authentifier le fichier. Examinez les règles d’un fichier non fiable.",
    sourceValue: "Valeur source", serverValue: "Valeur de ce serveur", effect: "Effet", copied: "Copier comme règle",
    defaults: "La valeur serveur est le défaut installé. La création utilise les règles source affichées.",
    revision: "Révision source", confirm: "Je reconfirme l’environnement cible, les références d’identifiants et les connexions.",
    references: "Saisissez les noms de variables cible ou l’authentification hôte prise en charge. Aucun identifiant ni endpoint source n’est transféré. Les connexions standard utilisent le modèle sélectionné ; les endpoints personnalisés se configurent ensuite dans Paramètres, collecte arrêtée.",
    blocked: "Sélectionnez et examinez une source compatible.", changed: "Source ou candidat modifié. Revoyez la source puis validez la cible.",
    paths: "Emplacements cible indépendants", cancel: "Annuler", loading: "Lecture de la source…",
  },
  de: {
    sources: "Klonen aus", file: "Aus einer portablen Einstellungsdatei", project: "Aus einem Projekt auf diesem Server",
    source: "Quellprojekt", choose: "Quellprojekt wählen",
    upload: "Portable JSON-Datei", review: "Quellregeln prüfen", target: "Neues Ziel einrichten", back: "Quelle erneut prüfen",
    title: "Portable Regeln für ein neues Projekt", recognized: "Erkannte Arbeitsregeln",
    help: "Nur Regeln werden übertragen. Neue Identität, vorhandenen Repository-Klon und Zielumgebung angeben. Der Server vergibt unabhängige Zustands-, Worktree- und Metrikpfade; kein Repository wird geklont.",
    exclusions: "Jobs, Verlauf, Benutzer, Rechte, Audit, ausstehende Änderungen, Geheimnisse und Quellressourcen werden nicht kopiert. Identität, Hostpfade, Labels und Verbindungsreferenzen sind ausgeschlossen.",
    integrity: "Die Prüfsumme erkennt Änderungen, authentifiziert aber keine Datei. Regeln aus nicht vertrauenswürdigen Dateien prüfen.",
    sourceValue: "Quellwert", serverValue: "Wert dieses Servers", effect: "Wirkung", copied: "Als Arbeitsregel kopieren",
    defaults: "Der Serverwert ist der installierte Standard. Die Erstellung verwendet die angezeigten Quellregeln.",
    revision: "Quellrevision", confirm: "Ich bestätige Zielumgebung, Zugangsdatenreferenzen und Endpunkte erneut.",
    references: "Zielvariablen oder unterstützte Hostanmeldung angeben. Quellzugangsdaten und Endpunkte werden nicht übertragen. Standardverbindungen verwenden das gewählte Modell; eigene Endpunkte später unter Einstellungen bei gestopptem Abruf einrichten.",
    blocked: "Eine unterstützte Quelle wählen und prüfen.", changed: "Quelle oder Kandidat geändert. Quelle erneut prüfen, dann das Ziel validieren.",
    paths: "Unabhängige Zielpfade", cancel: "Abbrechen", loading: "Quelle wird gelesen…",
  },
  ro: {
    sources: "Clonează din", file: "Dintr-un fișier de setări portabile", project: "Dintr-un proiect de pe acest server",
    source: "Proiect sursă", choose: "Alege proiectul sursă",
    upload: "Fișier JSON portabil", review: "Revizuiește regulile sursei", target: "Configurează ținta nouă", back: "Revizuiește sursa din nou",
    title: "Reguli portabile pentru un proiect nou", recognized: "Reguli recunoscute",
    help: "Se transferă doar reguli. Introdu o identitate nouă, o clonă existentă și mediul țintă. Serverul alocă locații independente pentru stare, worktree și metrici; nu clonează depozitul.",
    exclusions: "Nu se copiază joburi, istoric, utilizatori, drepturi, audit, modificări în așteptare, secrete sau proprietatea resurselor sursei. Identitatea, căile, etichetele și referințele de conectare sunt excluse.",
    integrity: "Checksumul detectează modificări, dar nu autentifică fișierul. Revizuiește regulile unui fișier neverificat.",
    sourceValue: "Valoare sursă", serverValue: "Valoare pe acest server", effect: "Efect", copied: "Copiază ca regulă de lucru",
    defaults: "Valoarea serverului este implicitul instalat. Crearea folosește regulile sursei afișate.",
    revision: "Revizia sursei", confirm: "Reconfirm mediul țintă, referințele de credențiale și configurarea endpointurilor.",
    references: "Introdu numele variabilelor țintă sau autentificarea pe gazdă acceptată. Nu se transferă credențiale sau endpointuri sursă. Conexiunile standard folosesc modelul ales; endpointurile personalizate se configurează separat în Setări, cu preluarea oprită.",
    blocked: "Selectează și revizuiește o sursă compatibilă.", changed: "Sursa sau candidatul s-a schimbat. Revizuiește sursa, apoi validează ținta din nou.",
    paths: "Locații țintă independente", cancel: "Anulează", loading: "Se citește sursa…",
  },
};

export type TransferSelection = { method: "file" | "project"; file_text?: string; source_id?: string };
export type TransferSource = { selection: TransferSelection; source_revision: string; settings: Record<string, Record<string, unknown>> };

/** Closed portable value domains for source and installed-default API mapping. */
export function validTransferSettings(value: unknown): value is TransferSource["settings"] {
  const object = (item: unknown): item is Record<string, unknown> => !!item && typeof item === "object" && !Array.isArray(item);
  const number = (item: unknown, min: number, integer = true) => typeof item === "number" && Number.isFinite(item) &&
    item >= min && item <= 1_000_000_000 && (!integer || Number.isInteger(item));
  if (!object(value) || Object.keys(value).length !== 4) return false;
  for (const [section, fields] of Object.entries(portableFields)) {
    const settings = value[section];
    if (!object(settings) || Object.keys(settings).length !== fields.length) return false;
    for (const key of fields) {
      const item = settings[key];
      if (key === "mode" ? item !== "loop" && item !== "once" :
        key === "poll_backoff" || section === "readiness" ? typeof item !== "boolean" :
          key === "retry_backoff_seconds" ? !Array.isArray(item) || !item.length || item.length > 100 || !item.every(n => number(n, 0)) :
            !number(item, ["max_cost_usd", "poll_jitter_seconds"].includes(key) ? 0 : 1, key !== "max_cost_usd")) return false;
    }
  }
  return true;
}
