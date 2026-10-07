/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import type { Locale } from "./i18n";
export type ImageDraft = {schema: 1; project_id: string; dockerfile: string; checks: string[]; network: "none" | "default"; timeout_seconds: number; memory_mib: number; revision: string};
export type ImageBinding = {id: string; project_id: string; config_revision: string; runtime: string; runtime_identity: string; base_id: string; image_id: string; context_sha256: string; draft_revision: string; verified_checks: string[]};
export type ImageOperation = ImageBinding & {phase: string; tag: string; error: string; host: {system: string; account: string; machine: string}};
export type ImageView = {project_id: string; backend: "container" | "local"; draft: ImageDraft | null; template: string; template_checks: string[]; operations: ImageOperation[]};
const mapping = (value: unknown): value is Record<string, unknown> => !!value && typeof value === "object" && !Array.isArray(value);
const closed = (value: Record<string, unknown>, fields: string[]) => Object.keys(value).sort().join() === fields.sort().join();
const digest = (value: unknown, length=64) => typeof value === "string" && new RegExp("^[0-9a-f]{" + length + "}$").test(value);
const text = (value: unknown, bytes: number): value is string => typeof value === "string" && new TextEncoder().encode(value).length <= bytes && !Array.from(value).some(c=>c.charCodeAt(0)<32 && !"\n\r\t".includes(c));
const checks = (value: unknown, min=0): value is string[] => Array.isArray(value) && value.length >= min && value.length <= 33 && value.every(v=>text(v,512) && v.trim().length > 0);
const image = (value: unknown) => typeof value === "string" && /^sha256:[0-9a-f]{64}$/.test(value);

/** Closed bounded drafts are scoped again by the consuming project component. */
export function validImageDraft(value: unknown): value is ImageDraft {
  return mapping(value) && closed(value, ["schema","project_id","dockerfile","checks","network","timeout_seconds","memory_mib","revision"])
    && value.schema === 1 && digest(value.project_id,32) && digest(value.revision)
    && text(value.dockerfile,65536) && checks(value.checks) && value.checks.length <= 32
    && (value.network === "none" || value.network === "default")
    && typeof value.timeout_seconds === "number" && Number.isInteger(value.timeout_seconds) && value.timeout_seconds >= 30 && value.timeout_seconds <= 1800
    && typeof value.memory_mib === "number" && Number.isInteger(value.memory_mib) && value.memory_mib >= 512 && value.memory_mib <= 4096;
}

/** Only complete verified bindings can enable a reviewed image selection. */
export function validImageBinding(value: unknown): value is ImageBinding {
  return mapping(value) && closed(value,["id","project_id","config_revision","runtime","runtime_identity","base_id","image_id","context_sha256","draft_revision","verified_checks"])
    && digest(value.id,32) && digest(value.project_id,32) && digest(value.config_revision) && digest(value.context_sha256) && digest(value.draft_revision)
    && image(value.image_id) && image(value.base_id) && text(value.runtime,512) && !!value.runtime && text(value.runtime_identity,256) && !!value.runtime_identity && checks(value.verified_checks,1);
}

/** Unknown phases, identities or extra fields cannot become actionable evidence. */
export function validImageOperation(value: unknown): value is ImageOperation {
  if (!mapping(value) || !closed(value,["id","project_id","config_revision","runtime","runtime_identity","base_id","image_id","context_sha256","draft_revision","verified_checks","phase","tag","error","host"])) return false;
  if (!digest(value.id,32) || !digest(value.project_id,32) || !digest(value.config_revision) || !digest(value.draft_revision)
      || !text(value.runtime,512) || !text(value.runtime_identity,256) || !checks(value.verified_checks)
      || typeof value.phase !== "string" || !["queued","inspecting","building","verifying","verified","failed","cancelled","uncertain","interrupted"].includes(value.phase)
      || value.tag !== "adore-built-" + value.project_id + ":" + value.id || !text(value.error,128)
      || !mapping(value.host) || !closed(value.host,["system","account","machine"]) || !Object.values(value.host).every(v=>text(v,256))) return false;
  for (const field of ["image_id","base_id"]) if (value[field] !== "" && !image(value[field])) return false;
  if (value.context_sha256 !== "" && !digest(value.context_sha256)) return false;
  if (value.phase === "verified") {
    const {phase: _phase, tag: _tag, error, host: _host, ...binding} = value;
    return error === "" && validImageBinding(binding);
  }
  return true;
}

export function validImageView(value: unknown, project: string): value is ImageView {
  return mapping(value) && closed(value,["project_id","backend","draft","template","template_checks","operations"]) && value.project_id === project
    && (value.backend === "container" || value.backend === "local") && text(value.template,65536) && checks(value.template_checks) && value.template_checks.length <= 32
    && (value.draft === null || validImageDraft(value.draft) && value.draft.project_id === project)
    && Array.isArray(value.operations) && value.operations.length <= 10 && value.operations.every(v=>validImageOperation(v) && v.project_id === project)
    && new Set(value.operations.map(v=>v.id)).size === value.operations.length;
}

/** Instructions are examples only; displaying them never changes a saved definition. */
export const IMAGE_COMPILER_EXAMPLE = "RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*";
export const IMAGE_COMPILER_CHECKS = "gcc --version\nmake --version";

/** Operator-facing steps and diagnosis; unknown codes retain the generic failure. */
export const imageWorkflowCopy = {
  en: {advanced:"Advanced environment settings", downloadHelp:"Allow downloads when RUN installs packages. Keep Offline for a definition that needs no network.", definition:"1. Define system tools", validation:"2. Set tool checks and downloads", execution:"3. Save, build and review", unsaved:"Save the definition to enable Build and verify.", ready:"Definition saved. Build and verify is ready; the active project image stays selected until you review and apply a verified result.", evidence:"Build result", details:"Technical evidence", limits:"Time and memory limits", unavailable:"The container runtime executable is unavailable to the ADORE server account. Check its installation and PATH on the server, then retry.", capabilities:"The runtime did not confirm the required Linux CPU and memory limits. Check the server runtime and diagnostic output before retrying.", tools:"A required tool or the selected executor is missing or failed its check. Add its installation to Dockerfile, save, then build again. The output below identifies the command.", buildFailed:"The image build failed. Check the output below, correct Dockerfile or allow downloads if packages are required, then save and build again."},
  ro: {advanced:"Setări avansate ale mediului", downloadHelp:"Permite descărcările când RUN instalează pachete. Păstrează Offline dacă definiția nu are nevoie de rețea.", definition:"1. Definește uneltele de sistem", validation:"2. Alege verificările și descărcările", execution:"3. Salvează, construiește și revizuiește", unsaved:"Salvează definiția pentru a activa Construiește și verifică.", ready:"Definiție salvată. Poți construi și verifica; imaginea activă rămâne selectată până revizuiești și aplici rezultatul verificat.", evidence:"Rezultatul construirii", details:"Dovezi tehnice", limits:"Limite de timp și memorie", unavailable:"Comanda runtime nu este disponibilă contului serverului ADORE. Verifică instalarea și PATH pe server, apoi reîncearcă.", capabilities:"Runtime-ul nu a confirmat limitele Linux de CPU și memorie. Verifică runtime-ul serverului și ieșirea diagnostică înainte de reîncercare.", tools:"O unealtă necesară sau executorul lipsește ori nu trece verificarea. Adaugă instalarea în Dockerfile, salvează și reconstruiește. Ieșirea de mai jos identifică comanda.", buildFailed:"Construirea imaginii a eșuat. Verifică ieșirea de mai jos, corectează Dockerfile sau permite descărcările necesare, apoi salvează și reconstruiește."},
  fr: {advanced:"Paramètres avancés de l’environnement", downloadHelp:"Autorisez les téléchargements si RUN installe des paquets. Gardez Hors ligne si la définition ne nécessite aucun réseau.", definition:"1. Définir les outils système", validation:"2. Choisir contrôles et téléchargements", execution:"3. Enregistrer, construire et examiner", unsaved:"Enregistrez la définition pour activer Construire et vérifier.", ready:"Définition enregistrée. La construction est prête ; l’image active reste sélectionnée jusqu’à l’examen et l’application du résultat vérifié.", evidence:"Résultat de construction", details:"Preuves techniques", limits:"Limites de temps et mémoire", unavailable:"L’exécutable du runtime est indisponible pour le compte du serveur ADORE. Vérifiez son installation et PATH sur le serveur, puis réessayez.", capabilities:"Le runtime n’a pas confirmé les limites Linux de CPU et mémoire. Vérifiez le runtime du serveur et la sortie diagnostique avant de réessayer.", tools:"Un outil requis ou l’exécuteur manque ou échoue au contrôle. Ajoutez son installation au Dockerfile, enregistrez et reconstruisez. La sortie ci-dessous identifie la commande.", buildFailed:"La construction a échoué. Consultez la sortie, corrigez le Dockerfile ou autorisez les téléchargements nécessaires, puis enregistrez et reconstruisez."},
  de: {advanced:"Erweiterte Umgebungseinstellungen", downloadHelp:"Erlauben Sie Downloads, wenn RUN Pakete installiert. Behalten Sie Offline, wenn die Definition kein Netzwerk braucht.", definition:"1. Systemwerkzeuge definieren", validation:"2. Prüfungen und Downloads wählen", execution:"3. Speichern, bauen und prüfen", unsaved:"Speichern Sie die Definition, um Bauen und prüfen zu aktivieren.", ready:"Definition gespeichert. Der Build ist bereit; das aktive Image bleibt gewählt, bis Sie das geprüfte Ergebnis prüfen und übernehmen.", evidence:"Build-Ergebnis", details:"Technische Nachweise", limits:"Zeit- und Speichergrenzen", unavailable:"Die Runtime-Datei ist für das ADORE-Serverkonto nicht verfügbar. Prüfen Sie Installation und PATH auf dem Server und versuchen Sie es erneut.", capabilities:"Die Runtime hat die Linux-Grenzen für CPU und Speicher nicht bestätigt. Prüfen Sie die Server-Runtime und Diagnoseausgabe vor dem nächsten Versuch.", tools:"Ein benötigtes Werkzeug oder der Executor fehlt oder besteht seine Prüfung nicht. Ergänzen Sie die Installation in Dockerfile, speichern und bauen Sie erneut. Die Ausgabe unten nennt den Befehl.", buildFailed:"Der Image-Build ist fehlgeschlagen. Prüfen Sie die Ausgabe, korrigieren Sie Dockerfile oder erlauben Sie nötige Downloads, speichern und bauen Sie erneut."},
};

export function imageFailure(locale: Locale, code: string): string {
  const copy=imageWorkflowCopy[locale];
  if(code==="image_runtime_unavailable") return copy.unavailable;
  if(code==="image_runtime_capabilities_unsupported") return copy.capabilities;
  if(code==="image_tool_check_failed") return copy.tools;
  if(code==="image_build_failed") return copy.buildFailed;
  return imageCopy[locale].failed;
}
export const imageGuidance = {
  en: {
    current: "Image currently used", change: "Change existing image", noImage: "No image selected",
    existing: "Use an image already installed on the ADORE server. Change existing image opens the image name or ID here; prepare, review and apply the candidate to select it.",
    source: "Add RUN commands between USER root and USER adore to install the system tools your project needs. Keep the FROM base and final USER adore lines. You can also load an existing Dockerfile.",
    checks: "List a version or help command for each tool you add. Every command must exit successfully. The selected executor is checked automatically; installation commands belong in Dockerfile.",
    finish: "Save the definition, then Build and verify. When verification succeeds, Use image prepares a change for review; apply it to select the new image.",
    example: "Example: C/C++ compiler and Make", exampleSource: "Add this RUN line before USER adore:", exampleChecks: "Add these tool checks:",
    downloads: "This example downloads packages. Set Build downloads to Allow default build network before saving and building.",
    blocked: "Editing, saving and building require paused project pickup with no active work or pending settings. Pause pickup in the project controls, then return here.",
  },
  ro: {
    current: "Imaginea folosită acum", change: "Schimbă imaginea existentă", noImage: "Nicio imagine selectată",
    existing: "Folosește o imagine deja instalată pe serverul ADORE. Schimbă imaginea existentă deschide aici numele sau ID-ul imaginii; pregătește, revizuiește și aplică propunerea.",
    source: "Adaugă comenzi RUN între USER root și USER adore pentru a instala uneltele de sistem necesare proiectului. Păstrează baza FROM și linia finală USER adore. Poți încărca și un Dockerfile existent.",
    checks: "Scrie câte o comandă de versiune sau ajutor pentru fiecare unealtă adăugată. Fiecare comandă trebuie să se încheie cu succes. Executorul ales este verificat automat; comenzile de instalare aparțin Dockerfile-ului.",
    finish: "Salvează definiția, apoi Construiește și verifică. După verificare, Folosește imaginea pregătește o propunere; aplic-o pentru a selecta noua imagine.",
    example: "Exemplu: compilator C/C++ și Make", exampleSource: "Adaugă această linie RUN înainte de USER adore:", exampleChecks: "Adaugă aceste verificări de unelte:",
    downloads: "Exemplul descarcă pachete. Setează Descărcări la construire pe Permite rețeaua implicită înainte de salvare și construire.",
    blocked: "Editarea, salvarea și construirea cer preluarea proiectului pe pauză, fără lucrări active sau setări în așteptare. Pune preluarea pe pauză din comenzile proiectului, apoi revino aici.",
  },
  fr: {
    current: "Image utilisée actuellement", change: "Changer l’image existante", noImage: "Aucune image sélectionnée",
    existing: "Utilisez une image déjà installée sur le serveur ADORE. Changer l’image existante ouvre ici son nom ou ID ; préparez, examinez et appliquez le candidat.",
    source: "Ajoutez des commandes RUN entre USER root et USER adore pour installer les outils système du projet. Conservez la base FROM et la dernière ligne USER adore. Vous pouvez aussi charger un Dockerfile existant.",
    checks: "Indiquez une commande de version ou d’aide pour chaque outil ajouté. Chaque commande doit réussir. L’exécuteur choisi est vérifié automatiquement ; les commandes d’installation appartiennent au Dockerfile.",
    finish: "Enregistrez la définition, puis Construire et vérifier. Après vérification, Utiliser l’image prépare un candidat à examiner ; appliquez-le pour sélectionner la nouvelle image.",
    example: "Exemple : compilateur C/C++ et Make", exampleSource: "Ajoutez cette ligne RUN avant USER adore :", exampleChecks: "Ajoutez ces contrôles des outils :",
    downloads: "Cet exemple télécharge des paquets. Choisissez Autoriser le réseau par défaut pour Téléchargements de construction avant d’enregistrer et construire.",
    blocked: "L’édition, l’enregistrement et la construction exigent une collecte en pause, sans travail actif ni paramètres en attente. Mettez la collecte en pause dans les commandes du projet, puis revenez ici.",
  },
  de: {
    current: "Aktuell verwendetes Image", change: "Vorhandenes Image ändern", noImage: "Kein Image ausgewählt",
    existing: "Verwenden Sie ein bereits auf dem ADORE-Server installiertes Image. Vorhandenes Image ändern öffnet hier Namen oder ID; bereiten Sie den Kandidaten vor, prüfen und übernehmen Sie ihn.",
    source: "Fügen Sie RUN-Befehle zwischen USER root und USER adore ein, um benötigte Systemwerkzeuge zu installieren. Behalten Sie die FROM-Basis und die letzte Zeile USER adore. Sie können auch eine vorhandene Dockerfile laden.",
    checks: "Geben Sie je hinzugefügtem Werkzeug einen Versions- oder Hilfebefehl an. Jeder Befehl muss erfolgreich enden. Der gewählte Executor wird automatisch geprüft; Installationsbefehle gehören in die Dockerfile.",
    finish: "Speichern Sie die Definition, dann Bauen und prüfen. Nach erfolgreicher Prüfung bereitet Image verwenden einen Kandidaten vor; prüfen und übernehmen Sie ihn zur Auswahl des neuen Images.",
    example: "Beispiel: C/C++-Compiler und Make", exampleSource: "Fügen Sie diese RUN-Zeile vor USER adore ein:", exampleChecks: "Fügen Sie diese Werkzeugprüfungen ein:",
    downloads: "Dieses Beispiel lädt Pakete herunter. Wählen Sie für Build-Downloads Standardnetzwerk erlauben, bevor Sie speichern und bauen.",
    blocked: "Bearbeiten, Speichern und Bauen erfordern pausierte Projektauswahl ohne aktive Arbeit oder ausstehende Einstellungen. Pausieren Sie die Auswahl in den Projektaktionen und kehren Sie hierher zurück.",
  },
};

export const imageCopy = {
  en: {title:"Project executor image", existing:"Existing image", define:"Define image", help:"Install system tools in this image. Per-worktree library preparation uses the project recipe; model access and full run readiness are checked separately.", local:"Local execution uses this server account's installed tools and dependencies. Image builds and automatic host preparation are unavailable.", source:"Dockerfile", checks:"Tool checks (one command per line)", upload:"Load Dockerfile text", save:"Save definition", export:"Export Dockerfile", evidence:"Export build evidence", build:"Build and verify", use:"Use image", advanced:"Advanced build details", context:"Only Dockerfile enters the context. COPY/ADD and checkout snapshots are deferred. Administrator commands are executable input; syntax checks are not a sandbox.", network:"Build downloads", none:"Offline (no network)", downloads:"Allow default build network", timeout:"Maximum seconds", memory:"Memory per build step (MiB)", cancel:"Cancel build", refresh:"Refresh evidence", logs:"Bounded build output", blocked:"Stop project pickup and finish active work or pending settings before saving or building.", failed:"Image request failed. Check the saved definition, installed base, runtime support and server evidence.", uncertain:"Build outcome or daemon cleanup is unconfirmed. Ask the server operator to reconcile preserved evidence; this image cannot be selected.", saved:"Definition saved. Build explicitly when ready.", stale:"This result belongs to an older definition or configuration. Save and build a current definition.", reviewed:"Verified tool checks", phases:{queued:"Queued",inspecting:"Checking runtime and base",building:"Building image",verifying:"Verifying image and tools",verified:"Verified",failed:"Failed",cancelled:"Cancelled before start",uncertain:"Uncertain",interrupted:"Interrupted by restart"}},
  ro: {title:"Imaginea executorului proiectului", existing:"Imagine existentă", define:"Definește imaginea", help:"Instalează uneltele de sistem în imagine. Bibliotecile per worktree folosesc rețeta proiectului; accesul la model și pregătirea completă se verifică separat.", local:"Execuția locală folosește uneltele și dependențele contului acestui server. Construirea imaginilor și pregătirea automată a gazdei nu sunt disponibile.", source:"Dockerfile", checks:"Verificări de unelte (o comandă pe linie)", upload:"Încarcă text Dockerfile", save:"Salvează definiția", export:"Exportă Dockerfile", evidence:"Exportă dovezile construirii", build:"Construiește și verifică", use:"Folosește imaginea", advanced:"Detalii avansate de construire", context:"Doar Dockerfile intră în context. COPY/ADD și copiile depozitului sunt amânate. Comenzile administratorului sunt executabile; verificarea sintaxei nu este un sandbox.", network:"Descărcări la construire", none:"Offline (fără rețea)", downloads:"Permite rețeaua implicită", timeout:"Secunde maxime", memory:"Memorie pe pas (MiB)", cancel:"Anulează construirea", refresh:"Actualizează dovezile", logs:"Ieșire limitată a construirii", blocked:"Oprește preluarea proiectului și încheie lucrările sau setările în așteptare înainte de salvare sau construire.", failed:"Cererea a eșuat. Verifică definiția, baza instalată, suportul runtime și dovezile serverului.", uncertain:"Rezultatul sau curățarea runtime nu sunt confirmate. Operatorul trebuie să reconcilieze dovezile păstrate; imaginea nu poate fi selectată.", saved:"Definiție salvată. Construiește explicit când este gata.", stale:"Rezultatul aparține unei definiții sau configurații vechi. Salvează și construiește o definiție curentă.", reviewed:"Verificări confirmate", phases:{queued:"În așteptare",inspecting:"Verificare runtime și bază",building:"Construire imagine",verifying:"Verificare imagine și unelte",verified:"Verificat",failed:"Eșuat",cancelled:"Anulat înainte de pornire",uncertain:"Incert",interrupted:"Întrerupt la repornire"}},
  fr: {title:"Image de l’exécuteur du projet", existing:"Image existante", define:"Définir l’image", help:"Installez les outils système dans cette image. Les bibliothèques par worktree utilisent la recette du projet ; l’accès au modèle et la disponibilité complète sont vérifiés séparément.", local:"L’exécution locale utilise les outils et dépendances du compte serveur. La construction d’images et la préparation automatique de l’hôte sont indisponibles.", source:"Dockerfile", checks:"Contrôles des outils (une commande par ligne)", upload:"Charger le texte Dockerfile", save:"Enregistrer la définition", export:"Exporter Dockerfile", evidence:"Exporter les preuves", build:"Construire et vérifier", use:"Utiliser l’image", advanced:"Détails avancés", context:"Seul Dockerfile entre dans le contexte. COPY/ADD et les copies du dépôt sont différés. Les commandes administrateur sont exécutables ; les contrôles de syntaxe ne sont pas un sandbox.", network:"Téléchargements de construction", none:"Hors ligne (sans réseau)", downloads:"Autoriser le réseau par défaut", timeout:"Secondes maximales", memory:"Mémoire par étape (MiB)", cancel:"Annuler la construction", refresh:"Actualiser les preuves", logs:"Sortie de construction limitée", blocked:"Arrêtez la collecte et terminez les travaux ou paramètres en attente avant d’enregistrer ou construire.", failed:"Échec. Vérifiez la définition, la base installée, le runtime et les preuves serveur.", uncertain:"Résultat ou nettoyage non confirmé. L’opérateur doit rapprocher les preuves conservées ; cette image ne peut pas être sélectionnée.", saved:"Définition enregistrée. Lancez explicitement la construction.", stale:"Ce résultat utilise une ancienne définition ou configuration. Enregistrez et construisez une définition actuelle.", reviewed:"Contrôles vérifiés", phases:{queued:"En attente",inspecting:"Contrôle du runtime et de la base",building:"Construction de l’image",verifying:"Vérification de l’image et des outils",verified:"Vérifié",failed:"Échec",cancelled:"Annulé avant lancement",uncertain:"Incertain",interrupted:"Interrompu au redémarrage"}},
  de: {title:"Executor-Image des Projekts", existing:"Vorhandenes Image", define:"Image definieren", help:"Installieren Sie Systemwerkzeuge im Image. Bibliotheken je Worktree verwenden das Projektrezept; Modellzugriff und vollständige Startbereitschaft werden separat geprüft.", local:"Lokale Ausführung nutzt installierte Werkzeuge und Abhängigkeiten dieses Serverkontos. Image-Builds und automatische Host-Vorbereitung sind nicht verfügbar.", source:"Dockerfile", checks:"Werkzeugprüfungen (ein Befehl je Zeile)", upload:"Dockerfile-Text laden", save:"Definition speichern", export:"Dockerfile exportieren", evidence:"Build-Nachweise exportieren", build:"Bauen und prüfen", use:"Image verwenden", advanced:"Erweiterte Build-Details", context:"Nur Dockerfile gelangt in den Kontext. COPY/ADD und Repository-Kopien sind aufgeschoben. Administratorbefehle sind ausführbar; Syntaxprüfungen sind keine Sandbox.", network:"Build-Downloads", none:"Offline (kein Netzwerk)", downloads:"Standardnetzwerk erlauben", timeout:"Maximale Sekunden", memory:"Speicher je Schritt (MiB)", cancel:"Build abbrechen", refresh:"Nachweise aktualisieren", logs:"Begrenzte Build-Ausgabe", blocked:"Stoppen Sie die Projektauswahl und beenden Sie aktive Arbeit oder ausstehende Einstellungen vor dem Speichern oder Bauen.", failed:"Anfrage fehlgeschlagen. Prüfen Sie Definition, installierte Basis, Runtime und Servernachweise.", uncertain:"Ergebnis oder Bereinigung nicht bestätigt. Der Betreiber muss die gespeicherten Nachweise abgleichen; dieses Image kann nicht ausgewählt werden.", saved:"Definition gespeichert. Starten Sie den Build ausdrücklich.", stale:"Ergebnis gehört zu einer alten Definition oder Konfiguration. Speichern und bauen Sie eine aktuelle Definition.", reviewed:"Geprüfte Werkzeuge", phases:{queued:"Wartend",inspecting:"Runtime und Basis prüfen",building:"Image bauen",verifying:"Image und Werkzeuge prüfen",verified:"Geprüft",failed:"Fehlgeschlagen",cancelled:"Vor Start abgebrochen",uncertain:"Ungewiss",interrupted:"Beim Neustart unterbrochen"}},
};
