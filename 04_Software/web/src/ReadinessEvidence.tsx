/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import type { ModelEvidence } from "./ModelConnection";
import { type Locale } from "./i18n";
import { readinessKeys, type ProjectReadiness } from "./readiness";
import { localCopy } from "./localExecution";

const copy = {
  en: {
    details: "Check details", externalSignIn: "Use Connect repository in Summary to configure this project’s account, or sign in on the ADORE server under its service account. Browser sign-in is separate.",
    passed: "Performed checks passed", failed: "Attention required", partial: "Verification incomplete",
    coverage: "This checks prerequisites on the ADORE server and in the configured image. It does not test a complete job or confirm Git push permission.",
    ok: "✓ Passed", error: "! Action needed", unknown: "? Could not verify", skipped: "○ Not checked",
    unsupported: "Use Test AI connection in Executor configuration to explicitly check the configured model through this executor.",
    unconfigured: "No compatible model endpoint is configured for this check. Model access remains unverified.",
    rows: [
      ["Git", "Creates isolated working copies and records code changes.", "Install Git on the ADORE server and check that the service can run it."],
      ["Repository command tool", "Lets ADORE read issues and publish draft reviews on Gitea, GitHub or GitLab.", "Install the command tool for the configured repository service on the ADORE server."],
      ["Repository sign-in", "Confirms that the configured repository account can authenticate through its command tool.", "Sign in on the ADORE server using the configured account and verify its repository access."],
      ["Container engine", "Starts the isolated environment where the coding agent works.", "Check the configured container engine and the ADORE service account's permissions."],
      ["Coding agent in image", "Checks that the selected coding agent's executable exists in the local container image.", "Check that the configured image is installed locally and contains the selected agent."],
      ["Repository workflow files", "Checks that the repository contains the AEGIS files used to guide and validate implementation.", "Check the configured repository path and its .agentic/aegis.py and .agentic/aegis.toml files."],
      ["AI model connection", "For a configured compatible OpenCode endpoint, sends a test request from a temporary container and checks a streamed tool call.", "Review the model endpoint, credentials and container connectivity in Executor configuration."],
    ],
  },
  ro: {
    details: "Detaliile verificării", externalSignIn: "Folosește Conectează depozitul din Summary pentru contul acestui proiect, sau configurează contul serviciului pe serverul ADORE. Autentificarea în browser este separată.",
    passed: "Verificările efectuate au reușit", failed: "Necesită intervenție", partial: "Verificare incompletă",
    coverage: "Verifică cerințele pe serverul ADORE și în imaginea configurată. Nu testează un job complet și nu confirmă permisiunea Git de publicare.",
    ok: "✓ Reușit", error: "! Necesită intervenție", unknown: "? Nu s-a putut verifica", skipped: "○ Neverificat",
    unsupported: "Folosește Testează conexiunea AI din Configurare executor pentru a verifica explicit modelul configurat.",
    unconfigured: "Nu este configurat un endpoint de model compatibil pentru această verificare. Accesul la model rămâne neverificat.",
    rows: [
      ["Git", "Creează copii de lucru izolate și înregistrează modificările de cod.", "Instalează Git pe serverul ADORE și verifică dacă serviciul îl poate executa."],
      ["Instrumentul pentru repository", "Permite ADORE să citească tichete și să publice propuneri de review pe Gitea, GitHub sau GitLab.", "Instalează pe serverul ADORE instrumentul pentru serviciul repository configurat."],
      ["Autentificare la repository", "Confirmă că acel cont configurat se poate autentifica prin instrumentul serviciului repository.", "Autentifică-te pe serverul ADORE cu acel cont configurat și verifică accesul la repository."],
      ["Motorul de containere", "Pornește mediul izolat în care lucrează agentul de programare.", "Verifică motorul de containere configurat și permisiunile contului serviciului ADORE."],
      ["Agentul din imagine", "Verifică dacă executabilul agentului selectat există în imaginea locală de container.", "Verifică dacă imaginea configurată este instalată local și conține agentul selectat."],
      ["Fișierele workflow-ului", "Verifică dacă repository-ul conține fișierele AEGIS care ghidează și validează implementarea.", "Verifică locația repository-ului și fișierele .agentic/aegis.py și .agentic/aegis.toml."],
      ["Conexiunea la modelul AI", "Pentru un endpoint OpenCode compatibil configurat, trimite o cerere de test dintr-un container temporar și verifică un apel de instrument transmis în flux.", "Verifică endpoint-ul modelului, credențialele și conectivitatea containerului în Configurare executor."],
    ],
  },
  fr: {
    details: "Détails du contrôle", externalSignIn: "Utilisez Connecter le dépôt dans Summary pour ce projet, ou configurez le compte du service sur le serveur ADORE. La connexion au navigateur est séparée.",
    passed: "Les contrôles effectués ont réussi", failed: "Intervention nécessaire", partial: "Vérification incomplète",
    coverage: "Vérifie les prérequis sur le serveur ADORE et dans l’image configurée. Ne teste pas une tâche complète ni l’autorisation de publication Git.",
    ok: "✓ Réussi", error: "! Intervention nécessaire", unknown: "? Impossible à vérifier", skipped: "○ Non vérifié",
    unsupported: "Utilisez Tester la connexion IA dans Configuration de l’exécuteur pour vérifier explicitement le modèle configuré.",
    unconfigured: "Aucun endpoint de modèle compatible n’est configuré pour ce contrôle. L’accès au modèle reste non vérifié.",
    rows: [
      ["Git", "Crée des copies de travail isolées et enregistre les modifications du code.", "Installez Git sur le serveur ADORE et vérifiez son accès par le service."],
      ["Outil du dépôt", "Permet de lire les tickets et de publier des demandes de revue en brouillon sur Gitea, GitHub ou GitLab.", "Installez l’outil du service de dépôt configuré sur le serveur ADORE."],
      ["Connexion au dépôt", "Confirme l’authentification du compte configuré via l’outil du dépôt.", "Connectez-vous sur le serveur ADORE avec le compte configuré et vérifiez son accès au dépôt."],
      ["Moteur de conteneurs", "Démarre l’environnement isolé de l’agent de programmation.", "Vérifiez le moteur configuré et les permissions du compte du service ADORE."],
      ["Agent dans l’image", "Vérifie la présence de l’exécutable de l’agent dans l’image locale du conteneur.", "Vérifiez que l’image configurée est installée localement et contient l’agent choisi."],
      ["Fichiers du workflow", "Vérifie les fichiers AEGIS du dépôt qui guident et valident l’implémentation.", "Vérifiez le chemin du dépôt et ses fichiers .agentic/aegis.py et .agentic/aegis.toml."],
      ["Connexion au modèle IA", "Pour un endpoint OpenCode compatible configuré, envoie une requête depuis un conteneur temporaire et vérifie un appel d’outil en streaming.", "Vérifiez l’endpoint, les identifiants et la connexion du conteneur dans Configuration de l’exécuteur."],
    ],
  },
  de: {
    details: "Prüfungsdetails", externalSignIn: "Nutzen Sie Repository verbinden in Summary für dieses Projekt, oder richten Sie das Dienstkonto auf dem ADORE-Server ein. Die Browser-Anmeldung ist separat.",
    passed: "Durchgeführte Prüfungen bestanden", failed: "Handlung erforderlich", partial: "Prüfung unvollständig",
    coverage: "Prüft Voraussetzungen auf dem ADORE-Server und im konfigurierten Image. Testet keinen vollständigen Job und bestätigt keine Git-Push-Berechtigung.",
    ok: "✓ Bestanden", error: "! Handlung erforderlich", unknown: "? Nicht feststellbar", skipped: "○ Nicht geprüft",
    unsupported: "Nutzen Sie KI-Verbindung testen in Executor-Konfiguration, um das konfigurierte Modell explizit zu prüfen.",
    unconfigured: "Für diese Prüfung ist kein kompatibler Modell-Endpunkt konfiguriert. Der Modellzugriff bleibt ungeprüft.",
    rows: [
      ["Git", "Erstellt isolierte Arbeitskopien und speichert Codeänderungen.", "Installieren Sie Git auf dem ADORE-Server und prüfen Sie den Zugriff des Dienstes."],
      ["Repository-Werkzeug", "Liest Tickets und veröffentlicht Review-Entwürfe auf Gitea, GitHub oder GitLab.", "Installieren Sie das Werkzeug des konfigurierten Repository-Dienstes auf dem ADORE-Server."],
      ["Repository-Anmeldung", "Bestätigt die Anmeldung des konfigurierten Kontos über das Repository-Werkzeug.", "Melden Sie sich auf dem ADORE-Server mit dem konfigurierten Konto an und prüfen Sie den Repository-Zugriff."],
      ["Container-Engine", "Startet die isolierte Arbeitsumgebung des Programmieragenten.", "Prüfen Sie die konfigurierte Engine und die Rechte des ADORE-Dienstkontos."],
      ["Agent im Image", "Prüft, ob die ausführbare Datei des ausgewählten Agenten im lokalen Container-Image vorhanden ist.", "Prüfen Sie, ob das konfigurierte Image lokal installiert ist und den Agenten enthält."],
      ["Workflow-Dateien", "Prüft die AEGIS-Dateien im Repository zur Steuerung und Validierung der Implementierung.", "Prüfen Sie den Repository-Pfad sowie .agentic/aegis.py und .agentic/aegis.toml."],
      ["KI-Modellverbindung", "Sendet für einen konfigurierten kompatiblen OpenCode-Endpunkt eine Testanfrage aus einem temporären Container und prüft einen gestreamten Werkzeugaufruf.", "Prüfen Sie Modell-Endpunkt, Zugangsdaten und Container-Verbindung in Executor-Konfiguration."],
    ],
  },
};

/** Localized accessible name for the Summary disclosure control. */
export function readinessDetailsLabel(locale: Locale): string { return copy[locale].details; }

/** Localized action hides only the details panel, without cancelling the check. */
export function readinessCloseLabel(locale: Locale): string { return { en: "Close details", ro: "Închide detaliile", fr: "Fermer les détails", de: "Details schließen" }[locale]; }

/** Present only validated results inside the view-owned disclosure. */
export function ReadinessEvidence({ evidence, locale, modelReason, modelEvidence }: { modelEvidence?: ModelEvidence | null; evidence: ProjectReadiness; locale: Locale; modelReason: string }) {
  const c = copy[locale];
  const local = evidence.model_probe.context === "executor-local";
  return <div className="readiness-evidence">
    <p className="muted">{local ? localCopy[locale].notice : c.coverage}</p>
    <div className="readiness-details">
    <div className="readiness-checks">{readinessKeys.map((key, index) => {
      if (local && key === "container_runtime") return null;
      const explicit = key === "model_endpoint" ? modelEvidence : null;
      const value = explicit ? explicit.ready : evidence.checks[key];
      const status = value === true ? "passed" : value === false ? "failed" : value === null ? "unknown" : "skipped";
      const [label, purpose, fix] = local && key === "executor_cli"
        ? [localCopy[locale].title, localCopy[locale].notice, localCopy[locale].notice]
        : c.rows[index];
      const accessPurpose = {en:"Explicit model access test through the selected executor. Full job and tool support require separate acceptance.",ro:"Test explicit de acces la model prin executorul selectat. Joburile complete și instrumentele necesită acceptare separată.",fr:"Test explicite d’accès au modèle via l’exécuteur. Les tâches complètes et outils nécessitent une validation distincte.",de:"Expliziter Modellzugriffstest über den Executor. Vollständige Aufträge und Werkzeuge benötigen separate Abnahme."}[locale];
      const reason = evidence.model_probe.reason;
      return <div className={`readiness-check ${status}`} key={key}>
        <div><strong>{label}</strong><p>{explicit ? accessPurpose : purpose}</p>
          {value === false && <p className="readiness-remediation">{fix}</p>}
          {key === "forge_auth" && value === false && <p>{c.externalSignIn}</p>}
          {value === null && <p className="readiness-remediation">{fix}</p>}
          {explicit && <p>{explicit.executor} · {explicit.model}</p>}
          {key === "model_endpoint" && !explicit && <p>{reason === "unsupported-executor" ? c.unsupported : reason === "not-configured" ? c.unconfigured : modelReason}{evidence.model_probe.model ? ` (${evidence.model_probe.model})` : ""}</p>}
        </div>
        <strong className="readiness-result">{c[status === "passed" ? "ok" : status === "failed" ? "error" : status === "unknown" ? "unknown" : "skipped"]}</strong>
      </div>;
    })}{modelEvidence && evidence.checks.model_endpoint !== "not-checked" && <div className={`readiness-check ${evidence.checks.model_endpoint ? "passed" : "failed"}`}><div><strong>{{en:"OpenCode endpoint and tool compatibility",ro:"Compatibilitatea endpoint-ului și instrumentelor OpenCode",fr:"Compatibilité endpoint et outils OpenCode",de:"OpenCode-Endpunkt- und Werkzeugkompatibilität"}[locale]}</strong><p>{modelReason}</p></div><strong className="readiness-result">{evidence.checks.model_endpoint ? c.ok : c.error}</strong></div>}</div></div>
  </div>;
}
