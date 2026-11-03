/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
export const localCopy = {
  "en": {
    "title": "Local execution",
    "account": "Current OS account",
    "path": "Project tools PATH (optional)",
    "machine": "Execution machine",
    "notice": "Pi uses the ADORE service account on the server. It has no permission prompts. Use a dedicated OS account and install project tools there. ADORE does not enforce internet restrictions on the server.",
    "agentPurpose": "Checks managed Pi and Node, the native process scope and the selected provider credential.",
    "agentFix": "Run adore pi install and adore pi verify as the ADORE service account.",
    "nodeMissing": "Node is missing. Add Node to the ADORE service PATH or set ADORE_NODE.",
    "nodeIncompatible": "Managed Pi requires Node 22.23.4 or later in the 22.x line.",
    "nodeInvalid": "ADORE could not run the Node version check.",
    "credentials": "Save the provider API key in Settings → Agent and model."
  },
  "fr": {
    "title": "Exécution locale",
    "account": "Compte système actuel",
    "path": "PATH des outils du projet (facultatif)",
    "machine": "Machine d’exécution",
    "notice": "Pi utilise le compte du service ADORE sur le serveur. Il ne demande pas d’autorisation. Utilisez un compte système dédié et installez-y les outils du projet. ADORE ne limite pas l’accès Internet sur le serveur.",
    "agentPurpose": "Vérifie Pi et Node, le contrôle des processus locaux et les identifiants du fournisseur choisi.",
    "agentFix": "Exécutez adore pi install et adore pi verify sous le compte du service ADORE.",
    "nodeMissing": "Node est absent. Ajoutez-le au PATH du service ADORE ou renseignez ADORE_NODE.",
    "nodeIncompatible": "Pi géré par ADORE exige Node 22.23.4 ou une version ultérieure de la série 22.x.",
    "nodeInvalid": "ADORE n’a pas pu vérifier la version de Node.",
    "credentials": "Enregistrez la clé API du fournisseur dans Paramètres → Agent et modèle."
  },
  "de": {
    "title": "Lokale Ausführung",
    "account": "Aktuelles Systemkonto",
    "path": "PATH für Projektwerkzeuge (optional)",
    "machine": "Ausführungsrechner",
    "notice": "Pi läuft auf dem Server unter dem ADORE-Dienstkonto. Pi fragt nicht nach Berechtigungen. Verwenden Sie ein eigenes Systemkonto und installieren Sie dort die Projektwerkzeuge. ADORE beschränkt den Internetzugang auf dem Server nicht.",
    "agentPurpose": "Prüft Pi und Node, die lokale Prozesskontrolle und die Zugangsdaten des gewählten Anbieters.",
    "agentFix": "Führen Sie adore pi install und adore pi verify als ADORE-Dienstkonto aus.",
    "nodeMissing": "Node fehlt. Ergänzen Sie den PATH des ADORE-Dienstes oder setzen Sie ADORE_NODE.",
    "nodeIncompatible": "Das verwaltete Pi benötigt Node ab Version 22.23.4 aus der Reihe 22.x.",
    "nodeInvalid": "ADORE konnte die Node-Version nicht prüfen.",
    "credentials": "Speichern Sie den API-Schlüssel unter Einstellungen → Agent und Modell."
  },
  "ro": {
    "title": "Execuție locală",
    "account": "Contul curent al sistemului",
    "path": "PATH pentru uneltele proiectului (opțional)",
    "machine": "Mașina de execuție",
    "notice": "Pi rulează pe server sub contul serviciului ADORE. Pi nu cere permisiuni. Folosiți un cont dedicat și instalați acolo uneltele proiectului. ADORE nu impune restricții de internet pe server.",
    "agentPurpose": "Verifică Pi și Node, controlul proceselor locale și credențialele furnizorului ales.",
    "agentFix": "Rulați adore pi install și adore pi verify sub contul serviciului ADORE.",
    "nodeMissing": "Node lipsește. Adăugați-l în PATH-ul serviciului ADORE sau setați ADORE_NODE.",
    "nodeIncompatible": "Pi administrat necesită Node 22.23.4 sau o versiune ulterioară din seria 22.x.",
    "nodeInvalid": "ADORE nu a putut verifica versiunea Node.",
    "credentials": "Salvați cheia API a furnizorului în Setări → Agent și model."
  }
};

export const localSettingHelp = Object.fromEntries(Object.entries(localCopy).map(([locale, copy]) => [locale, {
  "local.account": copy.account + ". " + copy.notice,
  "local.path": copy.path + ". " + copy.notice,
}])) as unknown as Record<keyof typeof localCopy, Record<string, string>>;
