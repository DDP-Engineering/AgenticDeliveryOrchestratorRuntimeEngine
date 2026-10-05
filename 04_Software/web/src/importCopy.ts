/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import type { Locale } from "./i18n";

const en = {
  title: "Enroll an existing configuration for this ADORE server",
  steps: ["Choose a file", "Declared identity and paths", "Structural validation", "Environment verification", "Review and enroll", "Enrollment complete"],
  source: "Choose config.toml from an existing ADORE profile, or a file prepared by an operator from config.example.toml. This advanced mode requires a configuration already prepared for this ADORE server.",
  exact: "The UTF-8 file is copied as exact unchanged bytes, including comments and unknown keys. Correct settings in the source file and select it again; enrollment never rewrites paths.",
  history: "The file alone does not transfer historical jobs. History appears only where the underlying completed job data already exists at the declared state location on this server.",
  paths: "Every repository, worktree, state and metrics location belongs to the ADORE server, not your browser computer. Use absolute project-specific paths. The repository clone must already exist; enrollment does not clone it.",
  file: "Existing UTF-8 TOML file", read: "Read declared locations", validate: "Validate file",
  structural: "Validation checks configuration structure, server paths, existing state and ownership locally. It does not run Git, forge, container or model commands.",
  valid: "Structural configuration valid", invalidFile: "Select a readable UTF-8 file of at most 512 KiB; no configuration has been enrolled.",
  changed: "The source file changed or became unreadable. Select the corrected file again, validate and review it before enrollment.",
  effect: "Enrollment saves the exact reviewed file with pickup stopped. Activation is a separate administrator action; it does not promise that any particular issue starts.",
  stopped: "Configuration enrolled with pickup stopped. Activation is a separate administrator action on the project. Existing completed history is shown only from the server's declared state location.",
  change: "Change identity or source", enroll: "Enroll with pickup stopped", destination: "Configuration destination",
  settings: "Recognized agent and runtime settings", correction: "Correct this field or source location",
  correctionHelp: "Correct the indicated configuration key in the source file, then select it again. For ID/display fields, correct this form. For state or lock findings, resolve the server condition before revalidation.",
  selected: "Selected file", loss: "Discard this exact enrollment draft? The selected file and identity exist only in memory and will be lost.",
};
type Copy = { [K in keyof typeof en]: typeof en[K] };
export const importCopy: Record<Locale, Copy> = {
  en,
  fr: {
    title: "Inscrire une configuration existante pour ce serveur ADORE",
    steps: ["Choisir un fichier", "Identité et chemins déclarés", "Validation structurelle", "Vérification de l’environnement", "Vérifier et inscrire", "Inscription terminée"],
    source: "Choisissez config.toml d’un profil ADORE existant ou un fichier préparé par un opérateur à partir de config.example.toml. Ce mode avancé exige une configuration préparée pour ce serveur ADORE.",
    exact: "Le fichier UTF-8 est copié octet par octet, sans modification des commentaires ni des clés inconnues. Corrigez le fichier source et sélectionnez-le à nouveau ; les chemins ne sont jamais réécrits.",
    history: "Le fichier seul ne transfère pas les tâches historiques. L’historique apparaît uniquement si les données des tâches terminées existent déjà à l’emplacement d’état déclaré sur ce serveur.",
    paths: "Tous les emplacements du dépôt, des worktrees, de l’état et des métriques appartiennent au serveur ADORE, pas à votre navigateur. Utilisez des chemins absolus propres au projet. Le clone doit déjà exister ; l’inscription ne clone pas le dépôt.",
    file: "Fichier TOML UTF-8 existant", read: "Lire les emplacements déclarés", validate: "Valider le fichier",
    structural: "La validation vérifie localement la structure, les chemins, l’état et leur propriété. Elle n’exécute aucune commande Git, forge, conteneur ou modèle.",
    valid: "Structure de configuration valide", invalidFile: "Sélectionnez un fichier UTF-8 lisible de 512 Kio maximum ; aucune configuration n’a été inscrite.",
    changed: "Le fichier source a changé ou est illisible. Sélectionnez-le à nouveau, validez-le et vérifiez-le avant l’inscription.",
    effect: "L’inscription enregistre le fichier exact vérifié avec la sélection arrêtée. L’activation est une action administrative séparée et ne garantit le démarrage d’aucune tâche.",
    stopped: "Configuration inscrite avec la sélection arrêtée. L’activation est une action administrative séparée. L’historique terminé provient uniquement de l’emplacement d’état déclaré sur le serveur.",
    change: "Modifier l’identité ou la source", enroll: "Inscrire avec la sélection arrêtée", destination: "Destination de la configuration",
    settings: "Paramètres reconnus de l’agent et de l’environnement", correction: "Corriger ce champ ou cet emplacement source",
    correctionHelp: "Corrigez la clé indiquée dans le fichier source et sélectionnez-le à nouveau. Corrigez l’ID et le nom dans ce formulaire. Résolvez l’état ou le verrou sur le serveur avant de revalider.",
    selected: "Fichier sélectionné", loss: "Abandonner cette inscription exacte ? Le fichier et l’identité sont conservés uniquement en mémoire et seront perdus.",
  },
  de: {
    title: "Eine vorhandene Konfiguration für diesen ADORE-Server registrieren",
    steps: ["Datei auswählen", "Deklarierte Identität und Pfade", "Strukturprüfung", "Umgebungsprüfung", "Prüfen und registrieren", "Registrierung abgeschlossen"],
    source: "Wählen Sie config.toml aus einem vorhandenen ADORE-Profil oder eine vom Betreiber aus config.example.toml erstellte Datei. Dieser erweiterte Modus erfordert eine für diesen ADORE-Server vorbereitete Konfiguration.",
    exact: "Die UTF-8-Datei wird bytegenau unverändert kopiert, einschließlich Kommentaren und unbekannten Schlüsseln. Korrigieren Sie die Quelldatei und wählen Sie sie erneut; Pfade werden niemals umgeschrieben.",
    history: "Die Datei allein überträgt keine früheren Jobs. Der Verlauf erscheint nur, wenn die Daten abgeschlossener Jobs bereits am deklarierten Statusort auf diesem Server liegen.",
    paths: "Repository-, Worktree-, Status- und Metrikpfade gehören zum ADORE-Server, nicht zum Browsercomputer. Verwenden Sie absolute projektspezifische Pfade. Der Klon muss bereits vorhanden sein; die Registrierung klont kein Repository.",
    file: "Vorhandene UTF-8-TOML-Datei", read: "Deklarierte Speicherorte lesen", validate: "Datei validieren",
    structural: "Die Validierung prüft Struktur, Serverpfade, Status und Eigentümerschaft lokal. Sie führt keine Git-, Forge-, Container- oder Modellbefehle aus.",
    valid: "Konfigurationsstruktur gültig", invalidFile: "Wählen Sie eine lesbare UTF-8-Datei bis 512 KiB; es wurde keine Konfiguration registriert.",
    changed: "Die Quelldatei wurde geändert oder ist unlesbar. Wählen Sie sie erneut, validieren und prüfen Sie sie vor der Registrierung.",
    effect: "Die Registrierung speichert die exakt geprüfte Datei mit gestoppter Aufnahme. Die Aktivierung ist eine separate Administratoraktion und garantiert keinen Jobstart.",
    stopped: "Konfiguration mit gestoppter Aufnahme registriert. Die Aktivierung ist eine separate Administratoraktion. Abgeschlossener Verlauf stammt nur vom deklarierten Statusort auf dem Server.",
    change: "Identität oder Quelle ändern", enroll: "Mit gestoppter Aufnahme registrieren", destination: "Konfigurationsziel",
    settings: "Erkannte Agent- und Laufzeiteinstellungen", correction: "Dieses Feld oder den Quellort korrigieren",
    correctionHelp: "Korrigieren Sie den angegebenen Schlüssel in der Quelldatei und wählen Sie sie erneut. ID und Anzeigename werden im Formular korrigiert. Beheben Sie Status- oder Sperrprobleme auf dem Server vor erneuter Validierung.",
    selected: "Ausgewählte Datei", loss: "Diesen Registrierungsentwurf verwerfen? Datei und Identität bleiben nur im Speicher und gehen verloren.",
  },
  ro: {
    title: "Înrolează o configurație existentă pentru acest server ADORE",
    steps: ["Alege fișierul", "Identitate și căi declarate", "Validare structurală", "Verificarea mediului", "Revizuiește și înrolează", "Înrolare finalizată"],
    source: "Alege config.toml dintr-un profil ADORE existent sau un fișier pregătit de operator din config.example.toml. Acest mod avansat necesită o configurație pregătită pentru acest server ADORE.",
    exact: "Fișierul UTF-8 este copiat exact, octet cu octet, inclusiv comentariile și cheile necunoscute. Corectează fișierul sursă și selectează-l din nou; căile nu sunt rescrise.",
    history: "Fișierul singur nu transferă istoricul sarcinilor. Istoricul apare numai dacă datele sarcinilor finalizate există deja la locația stării declarată pe acest server.",
    paths: "Locațiile depozitului, worktree-urilor, stării și metricilor aparțin serverului ADORE, nu calculatorului browserului. Folosește căi absolute specifice proiectului. Clona trebuie să existe deja; înrolarea nu clonează depozitul.",
    file: "Fișier TOML UTF-8 existent", read: "Citește locațiile declarate", validate: "Validează fișierul",
    structural: "Validarea verifică local structura, căile, starea și proprietarii. Nu execută comenzi Git, forge, container sau model.",
    valid: "Structura configurației este validă", invalidFile: "Selectează un fișier UTF-8 lizibil de maximum 512 KiB; nicio configurație nu a fost înrolată.",
    changed: "Fișierul sursă s-a schimbat sau nu poate fi citit. Selectează-l din nou, validează și revizuiește înainte de înrolare.",
    effect: "Înrolarea salvează fișierul exact revizuit cu preluarea oprită. Activarea este o acțiune separată a administratorului și nu garantează pornirea unei sarcini.",
    stopped: "Configurație înrolată cu preluarea oprită. Activarea este o acțiune separată a administratorului. Istoricul finalizat provine numai din locația stării declarată pe server.",
    change: "Schimbă identitatea sau sursa", enroll: "Înrolează cu preluarea oprită", destination: "Destinația configurației",
    settings: "Setări recunoscute ale agentului și mediului", correction: "Corectează câmpul sau locația sursă",
    correctionHelp: "Corectează cheia indicată în fișier și selectează-l din nou. ID-ul și numele se corectează în formular. Pentru stare sau blocare, rezolvă condiția pe server înainte de revalidare.",
    selected: "Fișier selectat", loss: "Renunți la această înrolare exactă? Fișierul și identitatea sunt păstrate numai în memorie și se vor pierde.",
  },
};
