/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { useEffect, useRef, useState, type FormEvent } from "react";
import { messages, type Locale } from "./i18n";
import { ApiError } from "./errors";

const copy = {
  en: { title: "Connect repository", server: "Repository server", token: "Access token", submit: "Verify and connect", cancel: "Cancel", busy: "Verifying…", account: "Connected account", help: "Create an access token on the selected repository server. Use an account allowed to read and update issues and create draft reviews. This verifies account sign-in and repository read access; Git clone/push credentials are separate. The token is saved privately on the ADORE server for this project, never in browser storage.", http: "Allow HTTP for this server (token is sent without encryption)", failed: "Connection failed. Check the server address, token and repository permissions. Existing credentials were retained.", invalid: "Use a server origin (no path or credentials) and a valid access token. HTTP requires explicit acknowledgement.", blocked: "The project must be idle, not archived, and have valid saved settings. Resolve pending work or settings first.", corrupt: "Credential storage is invalid or unavailable. Ask the server administrator to inspect it.", uncertain: "Connection could not be confirmed. Run Check host prerequisites before retrying or ask the server administrator.", success: "Connected. Run Check host prerequisites for fresh environment results." },
  ro: { title: "Conectează depozitul", server: "Serverul depozitului", token: "Token de acces", submit: "Verifică și conectează", cancel: "Anulează", busy: "Se verifică…", account: "Cont conectat", help: "Creează un token de acces pe serverul depozitului ales. Folosește un cont cu drepturi de citire și actualizare a tichetelor și creare a cererilor de revizuire în draft. Verificăm autentificarea și citirea depozitului; credențialele Git pentru clone/push sunt separate. Tokenul se salvează privat pe serverul ADORE pentru acest proiect, niciodată în stocarea browserului.", http: "Permite HTTP pentru acest server (tokenul se transmite fără criptare)", failed: "Conectarea a eșuat. Verifică adresa serverului, tokenul și accesul la depozit. Credențialele existente au fost păstrate.", invalid: "Introdu adresa serverului fără cale sau credențiale și un token valid. HTTP necesită confirmare explicită.", blocked: "Proiectul trebuie să fie inactiv, nearhivat și cu setări salvate valide. Rezolvă întâi lucrările sau setările în așteptare.", corrupt: "Stocarea credențialelor este invalidă sau indisponibilă. Administratorul serverului trebuie să o verifice.", uncertain: "Conectarea nu a putut fi confirmată. Rulează verificarea cerințelor gazdei înainte de reîncercare sau contactează administratorul serverului.", success: "Conectat. Rulează verificarea cerințelor gazdei pentru rezultate noi." },
  fr: { title: "Connecter le dépôt", server: "Serveur du dépôt", token: "Jeton d’accès", submit: "Vérifier et connecter", cancel: "Annuler", busy: "Vérification…", account: "Compte connecté", help: "Créez un jeton sur le serveur du dépôt choisi, avec un compte autorisé à lire et modifier les tickets et créer des demandes de revue en brouillon. Vérifie la connexion et la lecture du dépôt ; les identifiants Git clone/push sont séparés. Le jeton est conservé uniquement sur le serveur ADORE pour ce projet, jamais dans le stockage du navigateur.", http: "Autoriser HTTP (jeton transmis sans chiffrement)", failed: "Échec de connexion. Vérifiez le serveur, le jeton et les permissions. Les identifiants existants sont conservés.", invalid: "Indiquez une adresse serveur sans chemin ni identifiants et un jeton valide. HTTP exige une confirmation explicite.", blocked: "Le projet doit être inactif, non archivé et avoir des paramètres valides. Résolvez les opérations ou paramètres en attente.", corrupt: "Stockage des identifiants invalide ou indisponible. Contactez l’administrateur du serveur.", uncertain: "Connexion non confirmée. Vérifiez les prérequis avant de réessayer ou contactez l’administrateur.", success: "Connecté. Relancez le contrôle des prérequis pour des résultats à jour." },
  de: { title: "Repository verbinden", server: "Repository-Server", token: "Zugriffstoken", submit: "Prüfen und verbinden", cancel: "Abbrechen", busy: "Wird geprüft…", account: "Verbundenes Konto", help: "Erstellen Sie ein Token auf dem gewählten Repository-Server für ein Konto, das Tickets lesen und bearbeiten und Review-Entwürfe erstellen darf. Prüft Anmeldung und Repository-Lesezugriff; Git-Zugangsdaten für clone/push sind separat. Das Token wird nur auf dem ADORE-Server für dieses Projekt gespeichert, niemals im Browserspeicher.", http: "HTTP erlauben (Token wird unverschlüsselt übertragen)", failed: "Verbindung fehlgeschlagen. Prüfen Sie Server, Token und Rechte. Vorhandene Zugangsdaten bleiben erhalten.", invalid: "Geben Sie eine Serveradresse ohne Pfad oder Zugangsdaten und ein gültiges Token ein. HTTP benötigt ausdrückliche Zustimmung.", blocked: "Das Projekt muss inaktiv, nicht archiviert und gültig konfiguriert sein. Klären Sie ausstehende Arbeit oder Einstellungen.", corrupt: "Zugangsdaten-Speicher ungültig oder nicht verfügbar. Kontaktieren Sie den Serveradministrator.", uncertain: "Verbindung nicht bestätigt. Prüfen Sie die Host-Voraussetzungen vor einem neuen Versuch oder kontaktieren Sie den Administrator.", success: "Verbunden. Prüfen Sie die Host-Voraussetzungen erneut für aktuelle Ergebnisse." },
};
type Connection = { project_id: string; provider: string; server: string; repository: string; account: string };

/** Explicit administrator sign-in; credentials remain only in the current form/request. */
export function RepositoryConnection({ project, provider, repository, locale, connect, onConnected }: {
  project: string; provider: string; repository: string; locale: Locale;
  connect: (body: { server: string; token: string; allow_http: boolean }) => Promise<unknown>;
  onConnected: () => void;
}) {
  const text = copy[locale];
  const [open, setOpen] = useState(false);
  const [server, setServer] = useState(provider === "github" ? "https://github.com" : provider === "gitlab" ? "https://gitlab.com" : "");
  const [token, setToken] = useState("");
  const [allowHttp, setAllowHttp] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<Connection | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const close = () => { setOpen(false); setToken(""); setError(""); };
  useEffect(() => {
    if (open && !dialog.current?.open) dialog.current?.showModal();
    if (!open && dialog.current?.open) dialog.current.close();
  }, [open]);
  const mounted = useRef(true);
  const pending = useRef(false);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (pending.current) return;
    pending.current = true; setBusy(true); setError(""); setResult(null);
    const input = { server, token, allow_http: allowHttp };
    setToken("");
    try {
      const response = await connect(input);
      if (!mounted.current) return;
      const value = response as Connection;
      if (!value || Object.keys(value).sort().join() !== "account,project_id,provider,repository,server" ||
          value.project_id !== project || value.provider !== provider || value.repository !== repository ||
          typeof value.account !== "string" || !/^[A-Za-z0-9_.-]{1,128}$/.test(value.account) ||
          typeof value.server !== "string" || value.server !== server.replace(/\/$/, "").toLowerCase()) throw new ApiError("repository_credentials_corrupt");
      setResult(value); onConnected();
    } catch (cause) {
      if (!mounted.current) return;
      const code = cause instanceof ApiError ? cause.code : "request_failed";
      setError(code === "repository_connection_invalid" || code === "invalid_request" ? text.invalid :
        ["project_has_active_work", "project_archived", "invalid_config", "stale_config_revision"].includes(code) ? text.blocked :
        ["repository_credentials_corrupt", "repository_credentials_store_failed"].includes(code) ? text.corrupt : code === "repository_connection_failed" ? text.failed : text.uncertain);
    } finally {
      input.token = "";
      if (mounted.current) { pending.current = false; setBusy(false); }
    }
  };
  return <div className="repository-connection">
    <button type="button" className="ghost" aria-expanded={open} onClick={() => { setOpen(!open); setToken(""); setError(""); }}>{text.title}</button>
    <dialog ref={dialog} className="repository-connect-dialog" aria-label={text.title} onCancel={close} onClose={close}>
    {open && <form className="form-stack" onSubmit={submit}>
      <div className="card-heading"><h2>{text.title}</h2><button type="button" className="ghost" onClick={close}>{{en: "Close", ro: "Închide", fr: "Fermer", de: "Schließen"}[locale]}</button></div>
      <p><strong>{provider === "github" ? "GitHub" : provider === "gitlab" ? "GitLab" : "Gitea"}</strong> · {repository}</p>
      <p className="muted">{text.help}</p>
      <fieldset disabled={busy} className="form-stack">
        <label>{text.server}<input type="url" required maxLength={512} value={server} onChange={event => { setServer(event.target.value); setAllowHttp(false); }} autoComplete="off" placeholder={`${messages[locale].examplePrefix} https://git.example.com`} /></label>
        <label>{text.token}<input type="password" required maxLength={4096} value={token} onChange={event => setToken(event.target.value)} autoComplete="off" spellCheck={false} /></label>
        {server.startsWith("http:") && <label className="repository-http"><input type="checkbox" checked={allowHttp} onChange={event => setAllowHttp(event.target.checked)} /> {text.http}</label>}
        <div className="button-row"><button className="primary" type="submit" disabled={!token || server.startsWith("http:") && !allowHttp}>{text.submit}</button><button className="ghost" type="button" onClick={close}>{text.cancel}</button></div>
      </fieldset>
    </form>}
    {busy && <p role="status">{text.busy}</p>}
    {error && <p className="alert" role="alert">{error}</p>}
    {result && <p role="status"><strong>{text.account}: {result.account}</strong> · {result.server}<br />{text.success}</p>}
    </dialog>
  </div>;
}
