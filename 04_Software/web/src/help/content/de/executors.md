# Executor und Modelle

Ein Executor ist das Paar, das ADORE für jeden Auftrag startet: ein Coding-Agent und das KI-Modell, das er verwendet. Administratoren wählen beides in den Einstellungen eines Projekts.

## Was ein Executor ist {#what}

Für jeden Auftrag startet ADORE den Coding-Agenten des Projekts in einer isolierten Arbeitskopie, und der Agent arbeitet mit dem konfigurierten Modell die AEGIS-Phasen des Repositorys ab. Die Agenten sind OpenCode, Pi, Codex und Qwen Code. Der Agent committet und überträgt nie und sieht keine Forge-Zugangsdaten; das übernimmt ADORE. ADORE installiert keine Agenten und lädt keine Modelllisten, der Agent muss also bereits im Projekt-Image oder auf dem Server vorhanden sein. Änderungen gelten nur für neue Aufträge.

## Agent und Modell wählen {#agent-and-model}

Öffnen Sie **Einstellungen → Agent und Modell**. Die Zeilen sind **Standard-Coding-Agent**, **Executor-Startbefehl** und **Executor-Modellkennung**.

Administratoren wählen **Bearbeiten** in der Zeile Standard-Coding-Agent und wählen OpenCode, Pi, Codex oder Qwen Code. Die Auswahl eines Agenten lädt seinen gespeicherten Befehl und sein Modell oder die dokumentierte Befehlsvorlage. Geben Sie die Modell-ID für einen neuen Agenten selbst ein: die ID, die Ihr Agent und Ihr Anbieter akzeptieren, meist `provider/model`. Es gibt keinen universellen Standard. Der Startbefehl muss `{prompt}` enthalten. **Kandidat vorbereiten** prüft Agent, Befehl und Modell gemeinsam, und **Anwenden** schreibt sie als eine Änderung. Rechnen Sie damit, die Überwachung zuvor zu pausieren; siehe [Projekteinstellungen](/help/settings#editing).

## Authentifizierung {#credentials}

Öffnen Sie **Authentifizierung** in derselben Gruppe. Ein Projekt kann sich auf drei Arten authentifizieren.

- **Anbieter-API-Schlüssel.** Wählen Sie eine **Zugangsdaten-Variable** (zum Beispiel OPENAI_API_KEY oder ANTHROPIC_API_KEY), geben Sie den **API-Schlüssel** ein und wählen Sie **API-Schlüssel speichern**. ADORE speichert ihn privat auf dem Server und zeigt ihn nie wieder an; **Projekt-API-Schlüssel entfernen** löscht ihn. Die Variable muss zuvor unter **Erlaubte Zugangsdaten-Variablen** aufgeführt sein, die nur Namen enthält (**Zugangsdaten-Variable hinzufügen**). Das Ändern eines Schlüssels erfordert pausierte Überwachung, ein inaktives Projekt und keine ausstehende Änderung und testet den Schlüssel nicht.
- **Abo- oder Host-Anmeldung.** Der Agent verwendet seine eigene Anmeldung auf dem ADORE-Server unter dem Dienstkonto, die außerhalb der Weboberfläche eingerichtet wird (der Aufklapper **Abo- oder Browser-Anmeldung** nennt den Befehl). **Host-Anmeldung des Agenten verwenden** ist eine Pilotbrücke, die diese Anmeldung in den Container kopiert, nur für OpenCode und Codex. Ein ChatGPT-Abonnement ist kein OpenAI-API-Schlüssel.
- **Von der Umgebung verwaltete Werte.** Eine Variable, die bereits in der Umgebung des ADORE-Servers gesetzt ist, trägt den Hinweis **Auf dem ADORE-Server gesetzt; extern verwalten**. Die Weboberfläche kann sie nicht überschreiben.

Werte von Zugangsdaten erscheinen nie in Prüfungen, Audit-Einträgen oder Exporten. Eine leere Variablenliste ist bei vorhandener Server-Anmeldung gültig, ebenso im api-key-Modus, wenn sich das Image oder der installierte Executor selbst anmeldet.

## KI-Verbindung testen {#test-connection}

Administratoren wählen **KI-Verbindung testen** unter **KI-Verbindung**. Das sendet eine kurze Anfrage über den konfigurierten Agenten in einem temporären Container oder, bei einem auf dem Server installierten Agenten, in einem temporären Ordner, wodurch Anbietergebühren entstehen können. Das Projekt muss inaktiv sein, gültige gespeicherte Einstellungen und keine ausstehende Änderung haben; bei einem Container-Projekt braucht das Image Python und den Agenten.

Das Ergebnis lautet **KI-Modell verbunden** oder **KI-Verbindung nicht bestätigt**, mit Hinweisen bei Zeitüberschreitung, fehlendem Image oder Agenten, falschen Zugangsdaten, nicht verfügbarem Modell oder einem Shell-Befehl, den der Agent nicht ausführen konnte. Bei auf dem Server installiertem OpenCode, Pi oder Codex bittet die Anfrage den Agenten zusätzlich, einen Shell-Befehl auszuführen, und das Ergebnis lautet nur dann verbunden, wenn dieser Befehl lief; sonst belegt der Test nur den Modellzugriff. Er startet keinen Auftrag. Das gespeicherte Ergebnis ist an das aktuelle Modell, die Einstellungen und die Zugangsdaten gebunden und erscheint in den Host-Prüfungen der Zusammenfassung. Entwickler sehen es, können den Test aber nicht ausführen.

## Wo Aufträge laufen {#where-jobs-run}

| | Container | Native lokale Ausführung |
|---|---|---|
| Läuft in | Einem temporären Docker- oder Podman-Container auf dem ADORE-Server | Dem ADORE-Server selbst, unter dem Betriebssystemkonto des Dienstes, in einem eigenen Worktree |
| Umgebung | Einem vom Administrator vorbereiteten Projekt-Image | Werkzeugen, Versionen und Bibliotheken, die Sie selbst auf diesem Server installieren |
| Anmeldung | Aufgeführte API-Schlüssel oder Host-Anmeldung | Die vorhandene Anmeldung des Agenten auf diesem Konto, an Ort und Stelle weiterverwendet |
| Agent-Einstellungen | Die Einstellungen des Images, dazu der [lokale Endpunkt für OpenCode](#local-endpoint), falls gesetzt | Für OpenCode ein von ADORE verwalteter Einstellungsordner: Agenten, Anbieter, Plugins und Berechtigungen aus Ihrem persönlichen OpenCode-Einstellungsordner werden nicht verwendet, `git push` und die Forge-Werkzeuge sind gesperrt, und die Ordner `.opencode` und `.agents/skills` im Home-Verzeichnis des Kontos gelten weiterhin |
| Isolation | Container mit Netzwerkrichtlinie | Nur der Worktree; Befehle erreichen alles, was das Konto erreicht, verwenden Sie daher ein eigenes Konto mit minimalen Rechten |
| Gewählt | **Ausführung** → **Container**, Standard, in Schritt 2 der Registrierung oder unter Einstellungen → Agent und Modell | **Ausführung** → **Auf dem Server installiert**, oder im Serverprofil oder per TOML-Registrierung |

Änderungen in den Einstellungen laufen über **Kandidat vorbereiten**, Prüfung und **Anwenden**. **Auf dem Server installiert** zeigt den nativen Executor-Befehl und die Felder des lokalen Kontos (Konto `current`, Home-Verzeichnis, PATH und unter Linux die cgroup-Wurzel) zusammen mit dem Hinweis zur lokalen Ausführung.

Host-Prüfungen für ein lokales Projekt überspringen die Container-Engine und prüfen den nativen Agenten und seine Anmeldung.

## Projekt-Image {#project-image}

Für ein Container-Projekt zeigt Einstellungen → Agent und Modell **Executor läuft in einem Container**, die Angabe **Verwendetes Image** und einen Aufklapper **Anleitung zur Vorbereitung der Umgebung**. Die Weboberfläche definiert oder baut das Image nicht, und eine Dockerfile im Repository startet keinen Build. Der Administrator bereitet es auf dem Server vor:

1. Erstellen Sie `executor/Dockerfile` im Repository, ausgehend vom ADORE-Basis-Image und ohne Zugangsdaten. Das Image braucht Python, sh und den gewählten Agenten.
2. Bauen Sie es mit Docker oder Podman des Servers und prüfen Sie die Versionen von Agent und Werkzeugen.
3. Wählen Sie das Image in der Weboberfläche wie unten beschrieben oder setzen Sie bei pausierter Überwachung und ohne aktive Aufträge `execution.backend`, `container.image` und `container.required_tool_checks` in der `config.toml` des Projekts (Administratoren sehen ihren Pfad im Aufklapper) und validieren Sie dann das Profil.

```
FROM adore-executor-base:1.0.0
USER root
# RUN ... install the project's system tools
USER adore
```

Um das Image zu verwenden, wählen Sie in Schritt 2 der Registrierung die **Container-Laufzeit** (Docker oder Podman) und das **Executor-Image**, oder bearbeiten Sie dieselben Zeilen in den Einstellungen. Das Image ist ein freies Textfeld mit Vorschlägen aus den Images auf dem ADORE-Server für diese Laufzeit (nur für Administratoren); ein Hinweis erscheint, wenn das eingegebene Image nicht auf dem Server ist, ein weiterer, wenn die Liste nicht gelesen werden kann. Die Wahl eines Executors schlägt ein Image vor, dessen Tag mit dem Executor-Namen und einem Bindestrich beginnt (zum Beispiel `pi-`), bevorzugt `adore-executor-base:`; es ersetzt nur den alten Standard oder einen früheren Vorschlag, nie einen eingegebenen Wert.

Bestätigen Sie anschließend mit **Host-Voraussetzungen prüfen** und **KI-Verbindung testen**.

## Lokaler Endpunkt für OpenCode {#local-endpoint}

Für ein Container-Projekt mit OpenCode sehen Administratoren unter Agent und Modell zusätzlich **URL des OpenAI-kompatiblen Endpunkts**, für ein Modell in Ihrem eigenen Netzwerk. Geben Sie die URL, optional eine **Umgebungsreferenz für Zugangsdaten**, das **Anfragezeitlimit (Sekunden)** und, für HTTPS mit privater CA, die **CA-Datei im Executor-Image** ein. Das Protokoll ist fest auf OpenAI Chat Completions eingestellt. **Kandidat vorbereiten** prüft URL und Modell gemeinsam.

Die URL muss aus dem Executor-Container erreichbar sein, in dem localhost der Container selbst ist, und das Image muss das Anbieterpaket bereits enthalten. Das Speichern testet die Erreichbarkeit nicht und fügt keinen Cloud-Fallback hinzu; **Host-Voraussetzungen prüfen** testet einen gestreamten Werkzeugaufruf aus einem temporären Container.
