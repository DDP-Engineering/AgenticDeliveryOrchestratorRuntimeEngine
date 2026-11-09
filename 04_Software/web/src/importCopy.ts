/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import type { Locale } from "./i18n";

const en = {
  title: "Import raw configuration",
  file: "TOML file",
  validating: "Validating file…",
  importing: "Importing…",
  ready: "Ready to import",
  confirm: "Import",
  cancel: "Cancel",
  imported: "Project imported with monitoring paused.",
  invalidFile: "Choose a readable UTF-8 TOML file up to 512 KiB.",
  changed: "The file changed or could not be read. Select it again.",
  stale: "Select the file again to validate it.",
  correctFile: "Correct this setting in the TOML file and select it again.",
  issues: {
    state_root_already_owned: "Choose a state folder that is free on the server.",
    absolute_path_required: "Use an absolute path on the ADORE server.",
    path_must_not_be_volume_root: "Choose a project folder below the volume root.",
    secret_value: "Replace the secret with an environment reference.",
  },
};

export const importCopy: Record<Locale, typeof en> = {
  en,
  fr: {
    title: "Importer la configuration brute",
    file: "Fichier TOML",
    validating: "Validation du fichier…",
    importing: "Importation…",
    ready: "Prêt à importer",
    confirm: "Importer",
    cancel: "Annuler",
    imported: "Projet importé avec la surveillance en pause.",
    invalidFile: "Choisissez un fichier TOML UTF-8 lisible de 512 Kio maximum.",
    changed: "Le fichier a changé ou est illisible. Sélectionnez-le à nouveau.",
    stale: "Sélectionnez à nouveau le fichier pour le valider.",
    correctFile: "Corrigez ce paramètre dans le fichier TOML et sélectionnez-le à nouveau.",
    issues: {
      state_root_already_owned: "Choisissez un dossier d’état disponible sur le serveur.",
      absolute_path_required: "Utilisez un chemin absolu sur le serveur ADORE.",
      path_must_not_be_volume_root: "Choisissez un dossier de projet sous la racine du volume.",
      secret_value: "Remplacez le secret par une référence d’environnement.",
    },
  },
  de: {
    title: "Originalkonfiguration importieren",
    file: "TOML-Datei",
    validating: "Datei wird geprüft…",
    importing: "Import läuft…",
    ready: "Bereit zum Import",
    confirm: "Importieren",
    cancel: "Abbrechen",
    imported: "Projekt mit pausierter Überwachung importiert.",
    invalidFile: "Wählen Sie eine lesbare UTF-8-TOML-Datei bis 512 KiB.",
    changed: "Die Datei wurde geändert oder ist unlesbar. Wählen Sie sie erneut.",
    stale: "Wählen Sie die Datei erneut aus, um sie zu prüfen.",
    correctFile: "Korrigieren Sie diese Einstellung in der TOML-Datei und wählen Sie sie erneut aus.",
    issues: {
      state_root_already_owned: "Wählen Sie einen freien Statusordner auf dem Server.",
      absolute_path_required: "Verwenden Sie einen absoluten Pfad auf dem ADORE-Server.",
      path_must_not_be_volume_root: "Wählen Sie einen Projektordner unterhalb des Laufwerksstammverzeichnisses.",
      secret_value: "Ersetzen Sie das Geheimnis durch eine Umgebungsreferenz.",
    },
  },
  ro: {
    title: "Importă configurația brută",
    file: "Fișier TOML",
    validating: "Se validează fișierul…",
    importing: "Se importă…",
    ready: "Pregătit pentru import",
    confirm: "Importă",
    cancel: "Anulează",
    imported: "Proiect importat cu monitorizarea în pauză.",
    invalidFile: "Alege un fișier TOML UTF-8 lizibil de cel mult 512 KiB.",
    changed: "Fișierul s-a schimbat sau nu poate fi citit. Selectează-l din nou.",
    stale: "Selectează fișierul din nou pentru a-l valida.",
    correctFile: "Corectează setarea în fișierul TOML și selectează-l din nou.",
    issues: {
      state_root_already_owned: "Alege un dosar de stare disponibil pe server.",
      absolute_path_required: "Folosește o cale absolută pe serverul ADORE.",
      path_must_not_be_volume_root: "Alege un dosar de proiect în interiorul volumului.",
      secret_value: "Înlocuiește secretul cu o referință la o variabilă de mediu.",
    },
  },
};
