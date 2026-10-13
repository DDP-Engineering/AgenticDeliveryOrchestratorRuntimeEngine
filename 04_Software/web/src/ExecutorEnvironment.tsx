/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import type { Locale } from "./i18n";

/** Current server configuration; the host path is available only to administrators. */
export type ExecutorEnvironmentInfo = {
  backend: "container" | "local";
  image: string | null;
  config_path: string | null;
};

export const externalEnvironmentCopy = {
  en: {
    title: "Executor runs in a container", image: "Image used", unknown: "Image selection needs operator attention",
    notice: "The image itself is prepared on the ADORE server; choose which one this project uses under Agent container image. It must contain the selected executor and the tools your project needs.", external: "This environment setting is managed on the ADORE server and cannot be applied from the web.",
    instructions: "Environment preparation instructions", source: "1. Create the image definition", sourceHelp: "Create a Dockerfile in the project repository. Recommended location: executor/Dockerfile. Keep building and verification instructions in executor/README.md.",
    tools: "Start from an installed compatible ADORE base, add RUN commands between USER root and USER adore to install system tools, and finish as USER adore. Include Python, sh and the selected executor. Keep credentials outside the Dockerfile.",
    build: "2. Build and verify on the server", buildHelp: "Build the image externally with the server's Docker or Podman runtime, then verify the executor and tool versions. Docker example, run from the repository root on that server:",
    configure: "3. Select the image in the server profile", configHelp: "With pickup paused and no active jobs, the administrator updates the existing profile's config.toml: execution.backend selects container, container.image selects the built image, and container.required_tool_checks lists the commands to verify. Validate the profile before resuming pickup.",
    path: "Server configuration file", admin: "Ask the ADORE administrator for the server configuration file and environment preparation.",
    explicit: "Adding a Dockerfile to the repository does not start a build. ADORE uses the installed image selected in the profile, or in its reviewed preparation recipe. Keep both image selections consistent when a recipe is configured.",
    executor: "Selected executor", example: "Example Dockerfile structure",
  },
  ro: {
    title: "Executorul rulează într-un container", image: "Imagine utilizată", unknown: "Selectarea imaginii necesită intervenția administratorului",
    notice: "Imaginea se pregătește pe serverul ADORE; alegeți ce imagine folosește proiectul la Imagine executor. Trebuie să conțină executorul selectat și instrumentele necesare proiectului.", external: "Această setare de mediu se gestionează pe serverul ADORE și nu poate fi aplicată din web.",
    instructions: "Instrucțiuni pentru pregătirea mediului", source: "1. Creează definiția imaginii", sourceHelp: "Creează un Dockerfile în repository-ul proiectului. Locație recomandată: executor/Dockerfile. Păstrează pașii de construire și verificare în executor/README.md.",
    tools: "Pornește de la o bază ADORE compatibilă, deja instalată, adaugă comenzi RUN între USER root și USER adore pentru instrumentele de sistem și termină cu USER adore. Include Python, sh și executorul selectat. Păstrează credențialele în afara Dockerfile.",
    build: "2. Construiește și verifică pe server", buildHelp: "Construiește imaginea extern, cu Docker sau Podman de pe server, apoi verifică versiunile executorului și instrumentelor. Exemplu Docker, executat din rădăcina repository-ului de pe acel server:",
    configure: "3. Selectează imaginea în profilul de pe server", configHelp: "Cu preluarea tichetelor oprită și fără joburi active, administratorul actualizează config.toml al profilului existent: execution.backend selectează container, container.image selectează imaginea construită, iar container.required_tool_checks listează comenzile de verificare. Validează profilul înainte de reluarea preluării tichetelor.",
    path: "Fișierul de configurare de pe server", admin: "Solicită administratorului ADORE fișierul de configurare și pregătirea mediului pe server.",
    explicit: "Adăugarea unui Dockerfile în repository nu pornește o construire. ADORE folosește imaginea instalată selectată în profil sau în rețeta de pregătire verificată. Dacă există o rețetă, păstrează selecțiile imaginii consecvente.",
    executor: "Executor selectat", example: "Exemplu de structură Dockerfile",
  },
  fr: {
    title: "L’exécuteur fonctionne dans un conteneur", image: "Image utilisée", unknown: "La sélection de l’image nécessite l’intervention de l’administrateur",
    notice: "L’image est préparée sur le serveur ADORE ; choisissez celle du projet dans Image de l'exécuteur. Elle doit contenir l’exécuteur sélectionné et les outils nécessaires au projet.", external: "Ce paramètre d’environnement est géré sur le serveur ADORE et ne peut pas être appliqué depuis le web.",
    instructions: "Instructions de préparation de l’environnement", source: "1. Créer la définition de l’image", sourceHelp: "Créer un Dockerfile dans le dépôt du projet. Emplacement conseillé : executor/Dockerfile. Conserver les instructions de construction et de vérification dans executor/README.md.",
    tools: "Partir d’une base ADORE compatible déjà installée, ajouter les commandes RUN entre USER root et USER adore et terminer par USER adore. Inclure Python, sh et l’exécuteur sélectionné. Conserver les identifiants hors du Dockerfile.",
    build: "2. Construire et vérifier sur le serveur", buildHelp: "Construire l’image séparément avec Docker ou Podman sur le serveur, puis vérifier les versions de l’exécuteur et des outils. Exemple Docker, depuis la racine du dépôt sur ce serveur :",
    configure: "3. Sélectionner l’image dans le profil du serveur", configHelp: "Avec la collecte suspendue et sans tâche active, l’administrateur actualise le config.toml du profil existant : execution.backend sélectionne container, container.image sélectionne l’image construite et container.required_tool_checks définit les commandes de vérification. Valider le profil avant de reprendre la collecte.",
    path: "Fichier de configuration du serveur", admin: "Demander à l’administrateur ADORE le fichier de configuration et la préparation de l’environnement.",
    explicit: "Ajouter un Dockerfile au dépôt ne lance aucune construction. ADORE utilise l’image installée sélectionnée dans le profil ou sa recette de préparation vérifiée. Maintenir les deux sélections cohérentes lorsqu’une recette est configurée.",
    executor: "Exécuteur sélectionné", example: "Exemple de structure Dockerfile",
  },
  de: {
    title: "Executor läuft in einem Container", image: "Verwendetes Image", unknown: "Die Image-Auswahl muss vom Administrator geprüft werden",
    notice: "Das Image selbst wird auf dem ADORE-Server vorbereitet; welches das Projekt nutzt, wählen Sie unter Executor-Image. Es muss den ausgewählten Executor und die benötigten Projektwerkzeuge enthalten.", external: "Diese Umgebungseinstellung wird auf dem ADORE-Server verwaltet und kann nicht im Web angewendet werden.",
    instructions: "Anleitung zur Vorbereitung der Umgebung", source: "1. Image-Definition erstellen", sourceHelp: "Eine Dockerfile im Projekt-Repository erstellen. Empfohlener Pfad: executor/Dockerfile. Build- und Prüfschritte in executor/README.md dokumentieren.",
    tools: "Ein installiertes kompatibles ADORE-Basisimage verwenden, RUN-Befehle zwischen USER root und USER adore ergänzen und mit USER adore abschließen. Python, sh und den ausgewählten Executor bereitstellen. Zugangsdaten außerhalb der Dockerfile halten.",
    build: "2. Auf dem Server bauen und prüfen", buildHelp: "Das Image extern mit Docker oder Podman auf dem Server bauen und danach Executor- und Werkzeugversionen prüfen. Docker-Beispiel im Repository-Stammverzeichnis auf diesem Server:",
    configure: "3. Image im Serverprofil auswählen", configHelp: "Bei pausierter Ticket-Abholung und ohne aktive Jobs aktualisiert der Administrator die bestehende config.toml: execution.backend wählt container, container.image das gebaute Image und container.required_tool_checks die Prüfbefehle. Vor Wiederaufnahme das Profil validieren.",
    path: "Konfigurationsdatei auf dem Server", admin: "Den ADORE-Administrator nach der Konfigurationsdatei und der Vorbereitung der Serverumgebung fragen.",
    explicit: "Eine Dockerfile im Repository startet keinen Build. ADORE nutzt das installierte Image aus dem Profil oder dessen geprüftem Vorbereitungsschritt. Bei einer Rezeptkonfiguration beide Image-Auswahlen konsistent halten.",
    executor: "Ausgewählter Executor", example: "Beispiel einer Dockerfile-Struktur",
  },
};

const template = `# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0

FROM adore-executor-base:1.0.0
USER root
# RUN ... install the project's system tools
USER adore`;

/** A disclosure explains external preparation without editing or launching operations. */
export function ExecutorEnvironment({ environment, executor, locale }: {
  environment?: ExecutorEnvironmentInfo; executor: string; locale: Locale;
}) {
  if (!environment || environment.backend !== "container") return null;
  const c = externalEnvironmentCopy[locale];
  return <section className="executor-environment" role="note" aria-labelledby="executor-environment-title">
    <h3 id="executor-environment-title">{c.title}</h3>
    <p>{c.image}: <strong>{typeof environment.image === "string" && environment.image ? environment.image : c.unknown}</strong></p>
    <p>{c.notice}</p>
    <details>
      <summary>{c.instructions}</summary>
      <h4>{c.source}</h4><p>{c.sourceHelp}</p><p>{c.tools}</p>
      <p>{c.executor}: <strong>{executor}</strong></p>
      <pre aria-label={c.example}><code>{template}</code></pre>
      <h4>{c.build}</h4><p>{c.buildHelp}</p>
      <pre><code>docker build --file executor/Dockerfile --tag adore-executor-project:1.0 .</code></pre>
      <h4>{c.configure}</h4><p>{c.configHelp}</p>
      {typeof environment.config_path === "string" && environment.config_path ?
        <p>{c.path}: <code>{environment.config_path}</code></p> : <p>{c.admin}</p>}
      <p>{c.explicit}</p>
    </details>
  </section>;
}
