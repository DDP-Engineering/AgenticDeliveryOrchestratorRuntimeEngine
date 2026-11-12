/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import type { ModelEvidence } from "./ModelConnection";
import { type Locale } from "./i18n";
import { readinessKeys, workflowCopy, type RepositoryWorkflow, type ProjectReadiness } from "./readiness";
import { localCopy } from "./localExecution";
import { localFailureText, modelFailureText } from "./localDiagnostics";
import { repositoryConnectionHelp } from "./errors";

const copy = {
  en: {
    details: "Check details", externalSignIn: repositoryConnectionHelp.en,
    passed: "Performed checks passed", failed: "Attention required", partial: "Verification incomplete",
    coverage: "This checks prerequisites on the ADORE server and in the configured image. It does not test a complete job or confirm Git push permission.",
    ok: "✓ Passed", error: "! Action needed", unknown: "? Could not verify", skipped: "○ Not checked",
    testHint: "Use Test AI connection in Settings → Agent and model to explicitly check the configured model through Pi.",
    signIn: ["ChatGPT sign-in", "The ADORE server is signed in with ChatGPT, so each stage can get a short-lived access token.", "Use Sign in with ChatGPT in Settings → Agent and model."],
    egressProxy: ["Network proxy image", "Internet access for the agent is off: each run reaches the model provider through a per-run proxy built from this image.", "Build the proxy image on the ADORE server (docker/Dockerfile.egress-proxy), then check again."],
    webSearchKey: ["Web search key", "Internet access for the agent is on and web search uses Brave or Tavily, which needs its key.", "Save the search key in Settings → Agent and model."],
    rows: [
      ["Git", "Creates isolated working copies and records code changes.", "Install Git on the ADORE server and check that the service can run it."],
      ["Repository command tool", "Lets ADORE read issues and publish draft reviews on Gitea, GitHub or GitLab.", "Install the command tool for the configured repository service on the ADORE server."],
      ["Repository sign-in", "Confirms that the configured repository account can authenticate through its command tool.", "Sign in on the ADORE server using the configured account and verify its repository access."],
      ["Container engine", "Starts the isolated environment where the coding agent works.", "Check the configured container engine and the ADORE service account's permissions."],
      ["Coding agent in image", "Checks that Pi exists in the local container image.", "Check that the configured image is installed locally and contains Pi."],
      ["AI model connection", "Latest explicit model access test through Pi; Pi installed on the server must also run a shell command. A complete job requires separate acceptance.", "Review the model, credentials and container connectivity in Settings → Agent and model."],
    ],
  },
  ro: {
    details: "Detaliile verificării", externalSignIn: repositoryConnectionHelp.ro,
    passed: "Verificările efectuate au reușit", failed: "Necesită intervenție", partial: "Verificare incompletă",
    coverage: "Verifică cerințele pe serverul ADORE și în imaginea configurată. Nu testează un job complet și nu confirmă permisiunea Git de publicare.",
    ok: "✓ Reușit", error: "! Necesită intervenție", unknown: "? Nu s-a putut verifica", skipped: "○ Neverificat",
    testHint: "Folosește Testează conexiunea AI din Setări → Agent și model pentru a verifica explicit modelul configurat.",
    signIn: ["Autentificare ChatGPT", "Serverul ADORE este autentificat cu ChatGPT, deci fiecare etapă poate primi un token de acces de scurtă durată.", "Folosește Autentificare cu ChatGPT din Setări → Agent și model."],
    egressProxy: ["Imaginea proxyului de rețea", "Accesul la internet al agentului este dezactivat: fiecare rulare ajunge la furnizorul modelului printr-un proxy per rulare construit din această imagine.", "Construiește imaginea proxyului pe serverul ADORE (docker/Dockerfile.egress-proxy), apoi verifică din nou."],
    webSearchKey: ["Cheia de căutare web", "Accesul la internet al agentului este activat, iar căutarea web folosește Brave sau Tavily, care are nevoie de cheia sa.", "Salvează cheia de căutare în Setări → Agent și model."],
    rows: [
      ["Git", "Creează copii de lucru izolate și înregistrează modificările de cod.", "Instalează Git pe serverul ADORE și verifică dacă serviciul îl poate executa."],
      ["Instrumentul pentru repository", "Permite ADORE să citească tichete și să publice propuneri de review pe Gitea, GitHub sau GitLab.", "Instalează pe serverul ADORE instrumentul pentru serviciul repository configurat."],
      ["Autentificare la repository", "Confirmă că acel cont configurat se poate autentifica prin instrumentul serviciului repository.", "Autentifică-te pe serverul ADORE cu acel cont configurat și verifică accesul la repository."],
      ["Motorul de containere", "Pornește mediul izolat în care lucrează agentul de programare.", "Verifică motorul de containere configurat și permisiunile contului serviciului ADORE."],
      ["Agentul din imagine", "Verifică dacă Pi există în imaginea locală de container.", "Verifică dacă imaginea configurată este instalată local și conține Pi."],
      ["Conexiunea la modelul AI", "Ultimul test explicit de acces la model prin Pi; Pi instalat pe server trebuie să ruleze și o comandă shell. Un job complet necesită acceptare separată.", "Verifică modelul, credențialele și conectivitatea containerului în Setări → Agent și model."],
    ],
  },
  fr: {
    details: "Détails du contrôle", externalSignIn: repositoryConnectionHelp.fr,
    passed: "Les contrôles effectués ont réussi", failed: "Intervention nécessaire", partial: "Vérification incomplète",
    coverage: "Vérifie les prérequis sur le serveur ADORE et dans l’image configurée. Ne teste pas une tâche complète ni l’autorisation de publication Git.",
    ok: "✓ Réussi", error: "! Intervention nécessaire", unknown: "? Impossible à vérifier", skipped: "○ Non vérifié",
    testHint: "Utilisez Tester la connexion IA dans Paramètres → Agent et modèle pour vérifier explicitement le modèle configuré.",
    signIn: ["Connexion ChatGPT", "Le serveur ADORE est connecté à ChatGPT : chaque étape peut recevoir un jeton d’accès de courte durée.", "Utilisez Se connecter avec ChatGPT dans Paramètres → Agent et modèle."],
    egressProxy: ["Image du proxy réseau", "L’accès Internet de l’agent est désactivé : chaque exécution atteint le fournisseur du modèle par un proxy propre construit à partir de cette image.", "Construisez l’image du proxy sur le serveur ADORE (docker/Dockerfile.egress-proxy), puis vérifiez à nouveau."],
    webSearchKey: ["Clé de recherche web", "L’accès Internet de l’agent est activé et la recherche web utilise Brave ou Tavily, qui demande sa clé.", "Enregistrez la clé de recherche dans Paramètres → Agent et modèle."],
    rows: [
      ["Git", "Crée des copies de travail isolées et enregistre les modifications du code.", "Installez Git sur le serveur ADORE et vérifiez son accès par le service."],
      ["Outil du dépôt", "Permet de lire les tickets et de publier des demandes de revue en brouillon sur Gitea, GitHub ou GitLab.", "Installez l’outil du service de dépôt configuré sur le serveur ADORE."],
      ["Connexion au dépôt", "Confirme l’authentification du compte configuré via l’outil du dépôt.", "Connectez-vous sur le serveur ADORE avec le compte configuré et vérifiez son accès au dépôt."],
      ["Moteur de conteneurs", "Démarre l’environnement isolé de l’agent de programmation.", "Vérifiez le moteur configuré et les permissions du compte du service ADORE."],
      ["Agent dans l’image", "Vérifie la présence de Pi dans l’image locale du conteneur.", "Vérifiez que l’image configurée est installée localement et contient Pi."],
      ["Connexion au modèle IA", "Dernier test explicite d’accès au modèle via Pi ; un Pi installé sur le serveur doit aussi exécuter une commande shell. Une tâche complète nécessite une validation distincte.", "Vérifiez le modèle, les identifiants et la connexion du conteneur dans Paramètres → Agent et modèle."],
    ],
  },
  de: {
    details: "Prüfungsdetails", externalSignIn: repositoryConnectionHelp.de,
    passed: "Durchgeführte Prüfungen bestanden", failed: "Handlung erforderlich", partial: "Prüfung unvollständig",
    coverage: "Prüft Voraussetzungen auf dem ADORE-Server und im konfigurierten Image. Testet keinen vollständigen Job und bestätigt keine Git-Push-Berechtigung.",
    ok: "✓ Bestanden", error: "! Handlung erforderlich", unknown: "? Nicht feststellbar", skipped: "○ Nicht geprüft",
    testHint: "Nutzen Sie KI-Verbindung testen in Einstellungen → Agent und Modell, um das konfigurierte Modell explizit zu prüfen.",
    signIn: ["ChatGPT-Anmeldung", "Der ADORE-Server ist mit ChatGPT angemeldet, sodass jede Phase ein kurzlebiges Zugriffstoken erhält.", "Nutzen Sie Mit ChatGPT anmelden unter Einstellungen → Agent und Modell."],
    egressProxy: ["Netzwerk-Proxy-Image", "Der Internetzugang des Agenten ist aus: Jeder Lauf erreicht den Modellanbieter über einen eigenen Proxy aus diesem Image.", "Bauen Sie das Proxy-Image auf dem ADORE-Server (docker/Dockerfile.egress-proxy) und prüfen Sie erneut."],
    webSearchKey: ["Websuche-Schlüssel", "Der Internetzugang des Agenten ist an und die Websuche nutzt Brave oder Tavily, das seinen Schlüssel braucht.", "Speichern Sie den Suchschlüssel unter Einstellungen → Agent und Modell."],
    rows: [
      ["Git", "Erstellt isolierte Arbeitskopien und speichert Codeänderungen.", "Installieren Sie Git auf dem ADORE-Server und prüfen Sie den Zugriff des Dienstes."],
      ["Repository-Werkzeug", "Liest Tickets und veröffentlicht Review-Entwürfe auf Gitea, GitHub oder GitLab.", "Installieren Sie das Werkzeug des konfigurierten Repository-Dienstes auf dem ADORE-Server."],
      ["Repository-Anmeldung", "Bestätigt die Anmeldung des konfigurierten Kontos über das Repository-Werkzeug.", "Melden Sie sich auf dem ADORE-Server mit dem konfigurierten Konto an und prüfen Sie den Repository-Zugriff."],
      ["Container-Engine", "Startet die isolierte Arbeitsumgebung des Programmieragenten.", "Prüfen Sie die konfigurierte Engine und die Rechte des ADORE-Dienstkontos."],
      ["Agent im Image", "Prüft, ob Pi im lokalen Container-Image vorhanden ist.", "Prüfen Sie, ob das konfigurierte Image lokal installiert ist und Pi enthält."],
      ["KI-Modellverbindung", "Letzter expliziter Modellzugriffstest über Pi; ein auf dem Server installiertes Pi muss auch einen Shell-Befehl ausführen. Ein vollständiger Auftrag benötigt separate Abnahme.", "Prüfen Sie Modell, Zugangsdaten und Container-Verbindung in Einstellungen → Agent und Modell."],
    ],
  },
};

/** Localized check names shared with enrollment. */
export function readinessCheckLabel(locale: Locale, key: string): string {
  const index = readinessKeys.findIndex(item => item === key);
  if (index >= 0) return copy[locale].rows[index][0];
  if (key === "executor_sign_in") return copy[locale].signIn[0];
  if (key === "egress_proxy") return copy[locale].egressProxy[0];
  if (key === "web_search_key") return copy[locale].webSearchKey[0];
  return key;
}

/** Localized accessible name for the Summary disclosure control. */
export function readinessDetailsLabel(locale: Locale): string { return copy[locale].details; }

/** Localized action hides only the details panel, without cancelling the check. */
export function readinessCloseLabel(locale: Locale): string { return { en: "Close details", ro: "Închide detaliile", fr: "Fermer les détails", de: "Details schließen" }[locale]; }

/** Descriptive file observation, outside prerequisite pass/fail rows. */
export function WorkflowInformation({ workflow, locale }: { workflow: RepositoryWorkflow; locale: Locale }) {
  const c = workflowCopy[locale];
  return <p className="workflow-information"><strong>{c.label}</strong>: {c[workflow]}</p>;
}

/** Present only validated results inside the view-owned disclosure. */
export function ReadinessEvidence({ evidence, locale, local, modelEvidence }: { modelEvidence?: ModelEvidence | null; evidence: ProjectReadiness; locale: Locale; local: boolean }) {
  const c = copy[locale];
  const result = (status: string) => c[status === "passed" ? "ok" : status === "failed" ? "error" : status === "unknown" ? "unknown" : "skipped"];
  const [modelLabel, modelPurpose, modelFix] = c.rows[readinessKeys.length];
  const modelStatus = !modelEvidence ? "skipped" : modelEvidence.ready ? "passed" : "failed";
  return <div className="readiness-evidence">
    <p className="muted">{local ? localCopy[locale].notice : c.coverage}</p>
    {!evidence.auth_bound && <p>{({ en: "External CLI sign-in can change outside ADORE; connect repository access and check again to bind it.", fr: "La connexion CLI externe peut changer hors d’ADORE ; connectez l’accès au dépôt puis vérifiez à nouveau.", de: "Die externe CLI-Anmeldung kann sich außerhalb von ADORE ändern; verbinden Sie den Repository-Zugang und prüfen Sie erneut.", ro: "Autentificarea CLI externă se poate schimba în afara ADORE; conectați accesul la repository și verificați din nou." })[locale]}</p>}
    <WorkflowInformation workflow={evidence.workflow} locale={locale} />
    <div className="readiness-details">
    <div className="readiness-checks">{readinessKeys.map((key, index) => {
      if (local && key === "container_runtime") return null;
      const value = evidence.checks[key];
      const status = value === true ? "passed" : value === false ? "failed" : "unknown";
      const [label, purpose, fix] = local && key === "executor_cli"
        ? [localCopy[locale].title, localCopy[locale].agentPurpose, localCopy[locale].agentFix]
        : c.rows[index];
      return <div className={`readiness-check ${status}`} key={key}>
        <div><strong>{label}</strong><p>{purpose}</p>
          {value === false && <p className="readiness-remediation">{local && key === "executor_cli"
            ? localFailureText(locale, evidence.local_probe) : fix}</p>}
          {key === "forge_auth" && value === false && <p>{c.externalSignIn}</p>}
          {value === null && <p className="readiness-remediation">{fix}</p>}
        </div>
        <strong className="readiness-result">{result(status)}</strong>
      </div>;
    })}{([["executor_sign_in", c.signIn], ["egress_proxy", c.egressProxy], ["web_search_key", c.webSearchKey]] as const).map(([key, [label, purpose, fix]]) => {
      if (typeof evidence.checks[key] !== "boolean") return null;
      const status = evidence.checks[key] ? "passed" : "failed";
      return <div className={`readiness-check ${status}`} key={key}>
        <div><strong>{label}</strong><p>{purpose}</p>
          {status === "failed" && <p className="readiness-remediation">{fix}</p>}
        </div>
        <strong className="readiness-result">{result(status)}</strong>
      </div>;
    })}<div className={`readiness-check ${modelStatus}`} key="model">
        <div><strong>{modelLabel}</strong><p>{modelPurpose}</p>
          {modelStatus === "failed" && <p className="readiness-remediation">{modelEvidence ? modelFailureText(locale, modelEvidence.reason) : modelFix}</p>}
          <p>{modelEvidence ? `${modelEvidence.executor} · ${modelEvidence.model}` : c.testHint}</p>
        </div>
        <strong className="readiness-result">{result(modelStatus)}</strong>
      </div></div></div>
  </div>;
}
