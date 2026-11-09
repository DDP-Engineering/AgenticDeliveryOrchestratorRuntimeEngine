/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
/** Shared four-locale labels for automatic setup and host folder selection. */
export const setupCopy = {
 en: {
  chooseBranch:"Choose a branch",defaultBranch:"default",
  branchHelp:"Remote branches; the repository's default branch is selected initially. Read the repository again to refresh.",
  noDefaultBranch:"No default branch was reported. Choose a remote branch from the list.",
  noBranches:"No remote branches found. Add a branch to the repository, then read it again.",
  advanced:"Advanced",runsAs:"Runs as",processAccount:"the account running ADORE",
  automaticEnvironment:"By default, uses the ADORE account’s home folder, tool PATH and existing executor sign-in.",
  overrideHelp:"Leave home and PATH empty to use automatic values. PATH is a list of tool folders, not an executable file. Account names only verify the current account; they do not switch user. Linux requires a delegated cgroup root.",
  automatic:"Automatic location",custom:"Custom location",choose:"Choose folder…",dialog:"Select folder",
  hostHelp:"Folders on the computer running ADORE",
  location:"Folder on the ADORE host",go:"Open folder",up:"Parent folder",roots:"Locations",back:"Back",folders:"Folders",loading:"Reading folders…",
  unavailable:"The folder could not be read. Check its path and permissions, or enter the clone path manually.",
  empty:"No subfolders here.",truncated:"The list is limited. Enter a more specific path to find another folder.",
  use:"Select folder",cancel:"Cancel",cloneHelp:"ADORE clones here when you create the project, or reuses an existing clone of the same repository.",
 },
 ro: {
  chooseBranch:"Alege o ramură",defaultBranch:"implicită",
  branchHelp:"Ramuri remote; inițial este selectată ramura implicită a repository-ului. Recitește repository-ul pentru actualizare.",
  noDefaultBranch:"Nu a fost raportată o ramură implicită. Alege o ramură remote din listă.",
  noBranches:"Nu există ramuri remote. Adaugă o ramură în repository, apoi recitește-l.",
  advanced:"Avansate",runsAs:"Rulează ca",processAccount:"contul care rulează ADORE",
  automaticEnvironment:"Implicit, folosește directorul contului ADORE, PATH-ul uneltelor și autentificarea existentă a executorului.",
  overrideHelp:"Lasă directorul și PATH goale pentru valorile automate. PATH este o listă de directoare cu unelte, nu un executabil. Numele contului doar verifică identitatea curentă; nu schimbă utilizatorul. Linux necesită o rădăcină cgroup delegată.",
  automatic:"Locație automată",custom:"Locație personalizată",choose:"Alege folderul…",dialog:"Selectează folderul",
  hostHelp:"Foldere de pe calculatorul care rulează ADORE",
  location:"Folder de pe gazda ADORE",go:"Deschide folderul",up:"Folderul părinte",roots:"Locații",back:"Înapoi",folders:"Foldere",loading:"Se citesc folderele…",
  unavailable:"Folderul nu a putut fi citit. Verifică calea și permisiunile sau introdu manual calea clonei.",
  empty:"Nu există subfoldere aici.",truncated:"Lista este limitată. Introdu o cale mai precisă pentru a găsi alt folder.",
  use:"Selectează folderul",cancel:"Anulează",cloneHelp:"ADORE clonează aici la crearea proiectului sau reutilizează o clonă existentă a aceluiași repository.",
 },
 fr: {
  chooseBranch:"Choisir une branche",defaultBranch:"par défaut",
  branchHelp:"Branches distantes ; la branche par défaut du dépôt est sélectionnée au départ. Relisez le dépôt pour actualiser.",
  noDefaultBranch:"Aucune branche par défaut signalée. Choisissez une branche distante dans la liste.",
  noBranches:"Aucune branche distante. Ajoutez une branche au dépôt, puis relisez-le.",
  advanced:"Avancé",runsAs:"Exécution sous",processAccount:"le compte qui exécute ADORE",
  automaticEnvironment:"Utilise par défaut le dossier du compte ADORE, le PATH des outils et la connexion existante de l’exécuteur.",
  overrideHelp:"Laissez le dossier et le PATH vides pour les valeurs automatiques. Le PATH est une liste de dossiers d’outils, pas un exécutable. Le nom du compte vérifie uniquement l’identité actuelle, sans changer d’utilisateur. Linux exige une racine cgroup déléguée.",
  automatic:"Emplacement automatique",custom:"Emplacement personnalisé",choose:"Choisir un dossier…",dialog:"Sélectionner un dossier",
  hostHelp:"Dossiers de l’ordinateur qui exécute ADORE",
  location:"Dossier sur l’hôte ADORE",go:"Ouvrir le dossier",up:"Dossier parent",roots:"Emplacements",back:"Retour",folders:"Dossiers",loading:"Lecture des dossiers…",
  unavailable:"Impossible de lire le dossier. Vérifiez le chemin et les autorisations ou saisissez le chemin du clone manuellement.",
  empty:"Aucun sous-dossier ici.",truncated:"La liste est limitée. Saisissez un chemin plus précis pour trouver un autre dossier.",
  use:"Sélectionner le dossier",cancel:"Annuler",cloneHelp:"ADORE clone ici à la création du projet ou réutilise un clone existant du même dépôt.",
 },
 de: {
  chooseBranch:"Branch auswählen",defaultBranch:"Standard",
  branchHelp:"Remote-Branches; anfangs ist der Standardbranch des Repositorys ausgewählt. Zum Aktualisieren Repository erneut lesen.",
  noDefaultBranch:"Kein Standardbranch gemeldet. Wählen Sie einen Remote-Branch aus der Liste.",
  noBranches:"Keine Remote-Branches gefunden. Legen Sie einen Branch im Repository an und lesen Sie es erneut.",
  advanced:"Erweitert",runsAs:"Ausführung als",processAccount:"das Konto, unter dem ADORE läuft",
  automaticEnvironment:"Verwendet standardmäßig Kontoordner, Werkzeug-PATH und vorhandene Executor-Anmeldung des ADORE-Kontos.",
  overrideHelp:"Ordner und PATH für automatische Werte leer lassen. PATH ist eine Liste von Werkzeugordnern, keine Programmdatei. Der Kontoname prüft nur die aktuelle Identität und wechselt keinen Benutzer. Linux benötigt einen delegierten cgroup-Pfad.",
  automatic:"Automatischer Speicherort",custom:"Eigener Speicherort",choose:"Ordner wählen…",dialog:"Ordner auswählen",
  hostHelp:"Ordner auf dem Rechner, auf dem ADORE läuft",
  location:"Ordner auf dem ADORE-Rechner",go:"Ordner öffnen",up:"Übergeordneter Ordner",roots:"Orte",back:"Zurück",folders:"Ordner",loading:"Ordner werden gelesen…",
  unavailable:"Der Ordner konnte nicht gelesen werden. Pfad und Rechte prüfen oder den Klonpfad manuell eingeben.",
  empty:"Hier gibt es keine Unterordner.",truncated:"Die Liste ist begrenzt. Für weitere Ordner einen genaueren Pfad eingeben.",
  use:"Ordner auswählen",cancel:"Abbrechen",cloneHelp:"ADORE klont beim Erstellen des Projekts hierher oder verwendet einen vorhandenen Klon desselben Repositorys.",
 },
};
