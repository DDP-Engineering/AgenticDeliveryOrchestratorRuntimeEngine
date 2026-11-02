# Executor und Modelle

Ein Executor ist das, was ADORE für jeden Auftrag startet: der Coding-Agent Pi und das KI-Modell, das er verwendet. Administratoren wählen das Modell in den Einstellungen eines Projekts.

## Was ein Executor ist {#what}

Für jeden Auftrag startet ADORE Pi, seinen einzigen Coding-Agenten, in einer isolierten Arbeitskopie, und Pi arbeitet mit dem konfigurierten Modell die AEGIS-Phasen des Repositorys ab. Pi committet und überträgt nie und sieht keine Forge-Zugangsdaten; das übernimmt ADORE. ADORE lädt keine Modelllisten. In einem Container verwendet ADORE das im Executor-Image enthaltene Pi; für ein auf dem Server installiertes Projekt muss Pi bereits für das Serverkonto installiert sein. Änderungen gelten nur für neue Aufträge.

## Modell wählen {#agent-and-model}

Öffnen Sie **Einstellungen → Agent und Modell**. Die Zeilen sind **Executor-Modellkennung** und **Executor-Startbefehl**.

Geben Sie die Modell-ID selbst ein: das Pi-Modell in der Form `provider/model`, zum Beispiel `openai/gpt-5.4`. Es gibt keinen universellen Standard. In einem Container startet ADORE das im Image enthaltene Pi selbst, über seinen RPC-Modus mit festen Einstellungen, und stoppt es beim Zeitlimit der Stufe oder beim Abbrechen; der Startbefehl wird dort nicht verwendet, daher wird nur die Pi-Vorlage angeboten. Für ein auf dem Server installiertes Projekt startet der Startbefehl das installierte Pi, lautet standardmäßig `pi -p --mode json --model {model} {prompt}`, muss `{prompt}` enthalten und darf `--auto` nicht verwenden. Jede Zeile ist eine gewöhnliche Einstellung: **Kandidat vorbereiten** prüft sie und **Anwenden** schreibt sie. Rechnen Sie damit, die Überwachung zuvor zu pausieren; siehe [Projekteinstellungen](/help/settings#editing).

Ein Modell, das in Ihrem eigenen Netzwerk über einen OpenAI-kompatiblen Endpunkt bereitgestellt wird, etwa LM Studio, kann in dieser Version nicht konfiguriert werden.

## Authentifizierung {#credentials}

Öffnen Sie **Authentifizierung** in derselben Gruppe. Ein Projekt kann sich auf drei Arten authentifizieren.

- **Anbieter-API-Schlüssel.** Wählen Sie eine **Zugangsdaten-Variable** (zum Beispiel OPENAI_API_KEY oder ANTHROPIC_API_KEY), geben Sie den **API-Schlüssel** ein und wählen Sie **API-Schlüssel speichern**. ADORE speichert ihn privat auf dem Server und zeigt ihn nie wieder an; **Projekt-API-Schlüssel entfernen** löscht ihn. Die Variable muss zuvor unter **Erlaubte Zugangsdaten-Variablen** aufgeführt sein, die nur Namen enthält (**Zugangsdaten-Variable hinzufügen**). Das Ändern eines Schlüssels erfordert pausierte Überwachung, ein inaktives Projekt und keine ausstehende Änderung und testet den Schlüssel nicht.
- **Bestehende Kontoanmeldung.** Nur für ein auf dem Server installiertes Projekt: Pi verwendet seine eigene Anmeldung für das Serverkonto, die außerhalb der Weboberfläche eingerichtet wird. Ein Container-Projekt verwendet immer Anbieter-API-Schlüssel; keine Anmeldung wird in den Container kopiert.
- **Von der Umgebung verwaltete Werte.** Eine Variable, die bereits in der Umgebung des ADORE-Servers gesetzt ist, trägt den Hinweis **Auf dem ADORE-Server gesetzt; extern verwalten**. Die Weboberfläche kann sie nicht überschreiben.

Werte von Zugangsdaten erscheinen nie in Prüfungen, Audit-Einträgen oder Exporten. Eine leere Variablenliste ist für ein auf dem Server installiertes Projekt gültig, das die bestehende Kontoanmeldung verwendet.

## KI-Verbindung testen {#test-connection}

Administratoren wählen **KI-Verbindung testen** unter **KI-Verbindung**. Das sendet eine kurze Anfrage über Pi in einem temporären Container oder, bei auf dem Server installiertem Pi, in einem temporären Ordner, wodurch Anbietergebühren entstehen können. Das Projekt muss inaktiv sein, gültige gespeicherte Einstellungen und keine ausstehende Änderung haben; bei einem Container-Projekt muss das konfigurierte Image auf dem Server vorhanden sein.

Das Ergebnis lautet **KI-Modell verbunden** oder **KI-Verbindung nicht bestätigt**, mit Hinweisen bei Zeitüberschreitung, fehlendem Image oder Pi, falschen Zugangsdaten, nicht verfügbarem Modell oder einem Shell-Befehl, den Pi nicht ausführen konnte. In einem Container antwortet Pi ohne Werkzeuge, der Test belegt also nur den Modellzugriff. Bei auf dem Server installiertem Pi bittet die Anfrage Pi zusätzlich, einen Shell-Befehl auszuführen, und das Ergebnis lautet nur dann verbunden, wenn dieser Befehl lief. Er startet keinen Auftrag. Das gespeicherte Ergebnis ist an das aktuelle Modell, die Einstellungen und die Zugangsdaten gebunden und erscheint in den Host-Prüfungen der Zusammenfassung. Entwickler sehen es, können den Test aber nicht ausführen.

## Wo Aufträge laufen {#where-jobs-run}

| | Container | Native lokale Ausführung |
|---|---|---|
| Läuft in | Einem temporären Docker- oder Podman-Container auf dem ADORE-Server | Dem ADORE-Server selbst, unter dem Betriebssystemkonto des Dienstes, in einem eigenen Worktree |
| Umgebung | Einem vom Administrator vorbereiteten Projekt-Image | Werkzeugen, Versionen und Bibliotheken, die Sie selbst auf diesem Server installieren |
| Anmeldung | Aufgeführte Anbieter-API-Schlüssel | Aufgeführte Anbieter-API-Schlüssel oder die vorhandene Pi-Anmeldung auf diesem Konto, an Ort und Stelle weiterverwendet |
| Agent-Einstellungen | Das im Image enthaltene Pi mit von ADORE festgelegten Einstellungen; persönliche Pi-Einstellungen und Skills werden nicht gelesen | Das für dieses Konto installierte Pi, gestartet mit dem Startbefehl und den Pi-Einstellungen dieses Kontos |
| Isolation | Container mit Netzwerkrichtlinie | Nur der Worktree; Befehle erreichen alles, was das Konto erreicht, verwenden Sie daher ein eigenes Konto mit minimalen Rechten |
| Gewählt | **Ausführung** → **Container**, Standard, in Schritt 2 der Registrierung oder unter Einstellungen → Agent und Modell | **Ausführung** → **Auf dem Server installiert**, oder im Serverprofil oder per TOML-Registrierung |

Änderungen in den Einstellungen laufen über **Kandidat vorbereiten**, Prüfung und **Anwenden**. **Auf dem Server installiert** zeigt den nativen Executor-Befehl und die Felder des lokalen Kontos (Konto `current`, Home-Verzeichnis, PATH und unter Linux die cgroup-Wurzel) zusammen mit dem Hinweis zur lokalen Ausführung.

Host-Prüfungen für ein lokales Projekt überspringen die Container-Engine und prüfen das installierte Pi und seine Anmeldung oder seinen API-Schlüssel.

## Projekt-Image {#project-image}

Für ein Container-Projekt zeigt Einstellungen → Agent und Modell **Executor läuft in einem Container**, die Angabe **Verwendetes Image** und einen Aufklapper **Anleitung zur Vorbereitung der Umgebung**. Die Weboberfläche definiert oder baut das Image nicht, und eine Dockerfile im Repository startet keinen Build. Der Administrator bereitet es auf dem Server vor:

1. Erstellen Sie `executor/Dockerfile` im Repository, ausgehend vom ADORE-Basis-Image und ohne Zugangsdaten. Das Basis-Image enthält bereits Python, sh und das fest eingestellte Pi.
2. Bauen Sie es mit Docker oder Podman des Servers und prüfen Sie die Versionen der Werkzeuge.
3. Wählen Sie das Image in der Weboberfläche wie unten beschrieben oder setzen Sie bei pausierter Überwachung und ohne aktive Aufträge `execution.backend`, `container.image` und `container.required_tool_checks` in der `config.toml` des Projekts (Administratoren sehen ihren Pfad im Aufklapper) und validieren Sie dann das Profil.

```
FROM adore-executor-base:1.0.0
USER root
# RUN ... install the project's system tools
USER adore
```

Um das Image zu verwenden, wählen Sie in Schritt 2 der Registrierung die **Container-Laufzeit** (Docker oder Podman) und das **Executor-Image**, oder bearbeiten Sie dieselben Zeilen in den Einstellungen. Das Image ist ein freies Textfeld mit Vorschlägen aus den Images auf dem ADORE-Server für diese Laufzeit (nur für Administratoren); ein Hinweis erscheint, wenn das eingegebene Image nicht auf dem Server ist, ein weiterer, wenn die Liste nicht gelesen werden kann.

Bestätigen Sie anschließend mit **Host-Voraussetzungen prüfen** und **KI-Verbindung testen**.
