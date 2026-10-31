/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
export const localCopy = {
  en: { argv: "Executor launch command", title: "Local execution", backend: "Execution backend", account: "Current OS account", home: "Existing account home (optional)", path: "Installed tool PATH (optional)", cgroup: "Delegated Linux cgroup root", notice: "Execution runs on the ADORE server under its current OS account. You choose and independently install and prepare project tools, versions, SDKs and libraries on that machine. Installing them on your browser computer is insufficient. Existing executor sign-in is reused. A worktree is not a host sandbox; use a dedicated account without forge credentials.", existing: "Existing account sign-in", machine: "Execution machine" },
  fr: { argv: "Commande de lancement de l’exécuteur", title: "Exécution locale", backend: "Mode d’exécution", account: "Compte système actuel", home: "Dossier du compte existant (facultatif)", path: "PATH des outils installés (facultatif)", cgroup: "Racine cgroup Linux déléguée", notice: "L’exécution utilise le serveur ADORE et son compte système actuel. Vous choisissez et installez indépendamment les outils, versions, SDK et bibliothèques du projet sur cette machine. Les installer sur votre ordinateur de navigation ne suffit pas. La connexion existante de l’agent est réutilisée. Le dossier de travail n’isole pas l’hôte ; utilisez un compte dédié sans identifiants de forge.", existing: "Connexion existante du compte", machine: "Machine d’exécution" },
  de: { argv: "Executor-Startbefehl", title: "Lokale Ausführung", backend: "Ausführungsmodus", account: "Aktuelles Systemkonto", home: "Vorhandener Kontoordner (optional)", path: "PATH der installierten Werkzeuge (optional)", cgroup: "Delegierter Linux-cgroup-Pfad", notice: "Die Ausführung nutzt den ADORE-Server und dessen aktuelles Systemkonto. Sie wählen und installieren Projektwerkzeuge, Versionen, SDKs und Bibliotheken eigenständig auf diesem Rechner. Eine Installation auf dem Browserrechner reicht nicht aus. Die bestehende Agentenanmeldung wird verwendet. Ein Arbeitsverzeichnis isoliert den Rechner nicht; verwenden Sie ein eigenes Konto ohne Forge-Zugangsdaten.", existing: "Bestehende Kontoanmeldung", machine: "Ausführungsrechner" },
  ro: { argv: "Comanda de lansare a executorului", title: "Execuție locală", backend: "Mod de execuție", account: "Contul curent al sistemului", home: "Directorul contului existent (opțional)", path: "PATH pentru uneltele instalate (opțional)", cgroup: "Rădăcină cgroup Linux delegată", notice: "Execuția folosește serverul ADORE și contul său curent de sistem. Alegeți și instalați independent uneltele, versiunile, SDK-urile și bibliotecile proiectului pe acea mașină. Instalarea pe calculatorul cu browserul nu este suficientă. Autentificarea existentă a executorului este reutilizată. Arborele de lucru nu izolează gazda; folosiți un cont dedicat fără credențiale de forge.", existing: "Autentificarea existentă a contului", machine: "Mașina de execuție" },
};

export const localSettingHelp = Object.fromEntries(Object.entries(localCopy).map(([locale, copy]) => [locale, {
  "local.account": copy.account + ": current. " + copy.notice,
  "local.home": copy.home + ". " + copy.notice,
  "local.path": copy.path + ". " + copy.notice,
  "local.cgroup_root": copy.cgroup + ": cgroup v2 + cgroup.kill. " + copy.notice,
  "local.environment": copy.title + ": non-secret environment. " + copy.notice,
  "local.environment.*": copy.title + ": non-secret environment. " + copy.notice,
}])) as unknown as Record<keyof typeof localCopy, Record<string, string>>;
