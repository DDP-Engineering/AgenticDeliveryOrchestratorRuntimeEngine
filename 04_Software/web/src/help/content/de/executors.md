# Executor und Modelle

Ein Executor ist das, was ADORE für jeden Auftrag startet: der Coding-Agent Pi und das KI-Modell, das er verwendet. Administratoren wählen das Modell in den Einstellungen eines Projekts.

## Was ein Executor ist {#what}

Für jeden Auftrag startet ADORE Pi, seinen einzigen Coding-Agenten, in einer isolierten Arbeitskopie, und Pi arbeitet die AEGIS-Phasen des Repositorys mit dem konfigurierten Anbieter und Modell ab. Pi committet nicht, pusht nicht und sieht keine Forge-Zugangsdaten; das übernimmt ADORE. Im Container nutzt ADORE das im Executor-Image enthaltene Pi; für ein auf dem Server installiertes Projekt muss Pi bereits für das Serverkonto installiert sein. Änderungen gelten nur für neue Aufträge.

## Anbieter und Modell wählen {#agent-and-model}

Öffnen Sie **Einstellungen → Agent und Modell**. Die Zeilen sind **Anbieter**, **Modell**, **Executor-Startbefehl** und, für einen Endpunkt, **Endpunkt-Basis-URL** und **Endpunkt-API-Typ**. **Bearbeiten** an einer der Zeilen für Anbieter, Modell oder Endpunkt öffnet einen gemeinsamen Editor; sie werden als eine Änderung geprüft und angewendet.

- **Anbieter**: ein Pi-Anbieter mit API-Schlüssel (OpenAI, Anthropic, Google Gemini, OpenRouter, Mistral und weitere), **ChatGPT-Abonnement** oder **OpenAI-kompatibler Endpunkt**.
- **Modell**: aus der Pi-Liste für diesen Anbieter wählen oder eine vom Anbieter akzeptierte Modell-ID eingeben, z. B. `gpt-5.4`. Die Liste gehört zur von ADORE ausgelieferten Pi-Version und wird ohne Internetzugang gelesen. Es gibt kein universelles Standardmodell.
- **ChatGPT-Abonnement**: Pi nutzt das ChatGPT-Plus- oder -Pro-Konto, bei dem dieser ADORE-Server angemeldet ist, siehe [Mit ChatGPT anmelden](#chatgpt). Die Liste enthält die Modelle, die ein ChatGPT-Abonnement bedient, zum Beispiel `gpt-5.6-luna`.

**Kandidat vorbereiten** zeigt den aktiven und vorgeschlagenen Wert jedes Felds, **Anwenden** schreibt sie; rechnen Sie damit, die Überwachung vorher zu pausieren, siehe [Projekteinstellungen](/help/settings#editing). Im Container startet ADORE das im Image enthaltene Pi selbst, über seinen RPC-Modus mit festen Einstellungen, und stoppt es am Zeitlimit der Phase oder beim Abbrechen; der Startbefehl wird dort nicht verwendet, daher wird nur die Pi-Vorgabe angeboten. Für ein auf dem Server installiertes Projekt startet der Startbefehl das installierte Pi, ist standardmäßig `pi -p --mode json --model {model} {prompt}` (`{model}` wird zu Anbieter/Modell), muss `{prompt}` enthalten und darf `--auto` nicht verwenden.

## OpenAI-kompatibler Endpunkt {#endpoint}

Für ein Modell aus dem eigenen Netzwerk, etwa LM Studio, Ollama oder vLLM, wählen Sie **OpenAI-kompatibler Endpunkt** und füllen aus:

- **Endpunkt-Basis-URL**: die Adresse aus Sicht des Containers, z. B. `http://192.168.1.20:1234/v1`. `localhost` ist der Container selbst. `host.docker.internal` erreicht den Host nur mit Docker Desktop; mit Docker Engine unter Linux oder in WSL nutzen Sie die Netzwerkadresse des Hosts, und für einen Server unter Windows, der von Docker in WSL aus erreicht wird, das Standard-Gateway von WSL.
- **Endpunkt-API-Typ**: `openai-completions` für LM Studio, Ollama und vLLM; `openai-responses`, `anthropic-messages` und `google-generative-ai` werden ebenfalls akzeptiert.
- **Modell**: die Modell-ID, die der Endpunkt bereitstellt.

Ein Endpunkt-Schlüssel ist optional: Speichern Sie ihn unter Authentifizierung als ADORE_ENDPOINT_API_KEY. ADORE beschreibt Pi den Endpunkt für jeden Auftrag; die Adresse enthält nie Benutzername, Passwort oder Abfrage. Bei einer eingeschränkten Netzwerkrichtlinie muss die Adresse des Endpunkts erlaubt sein. Ein Endpunkt ist nur für Container-Projekte verfügbar.

## Authentifizierung {#credentials}

Öffnen Sie **Authentifizierung** in derselben Gruppe.

- **API-Schlüssel des Anbieters.** Das Feld nennt die Variable, die der konfigurierte Anbieter braucht, z. B. OPENAI_API_KEY für OpenAI oder ANTHROPIC_API_KEY für Anthropic. Geben Sie den **API-Schlüssel** ein und wählen Sie **API-Schlüssel speichern**. ADORE speichert ihn privat im Zugangsdatenspeicher des Projekts auf dem Server, nie in der Konfigurationsdatei, gibt ihn Pi nur als diese Variable weiter und zeigt ihn nie wieder an; **Projekt-API-Schlüssel entfernen** löscht ihn. Eine Schlüsseländerung erfordert pausierte Überwachung, ein inaktives Projekt und keinen offenen Vorschlag und prüft den Schlüssel nicht.
- **Vorhandene Kontoanmeldung.** Nur für ein auf dem Server installiertes Projekt: Pi nutzt seine eigene Anmeldung für das Serverkonto, außerhalb der Weboberfläche eingerichtet. Ein Container-Projekt nutzt den API-Schlüssel des Anbieters oder, bei einem ChatGPT-Abonnement, ein kurzlebiges Zugriffstoken aus der [ChatGPT-Anmeldung](#chatgpt) des Servers; keine Anmeldung wird in den Container kopiert.
- **Von der Umgebung verwaltete Werte.** Eine bereits in der Umgebung des ADORE-Servers gesetzte Variable trägt den Hinweis **Auf dem ADORE-Server gesetzt; extern verwalten**. Die Weboberfläche kann sie nicht überschreiben.
- **Zusätzliche Zugangsdaten-Variablen.** Nur Namen (**Zugangsdaten-Variable hinzufügen**) weiterer Geheimnisse, die Pi neben dem Schlüssel des Anbieters erhält; die meisten Projekte brauchen keine.

Zugangsdatenwerte erscheinen nie in der Konfigurationsdatei, in Prüfungen, Audit-Einträgen, Protokollen oder Exporten.

## Mit ChatGPT anmelden {#chatgpt}

Ein ChatGPT-Plus- oder -Pro-Konto dient allen Projekten dieses ADORE-Servers, deren Anbieter **ChatGPT-Abonnement** ist. Administratoren melden sich unter **Authentifizierung** eines solchen Projekts an; ADORE führt die OpenAI-Anmeldung von Pi aus, daher braucht der Server keinen Browser.

1. Wählen Sie **Mit ChatGPT anmelden**.
2. Öffnen Sie **ChatGPT-Anmeldeseite öffnen** auf Ihrem eigenen Computer und melden Sie sich mit dem ChatGPT-Konto an. Der Link ist 15 Minuten gültig.
3. Der Browser zeigt danach eine Fehlerseite unter `127.0.0.1:1455`. Das ist erwartet: Kopieren Sie die vollständige Adresse aus seiner Adressleiste.
4. Fügen Sie sie unter **Weiterleitungsadresse** ein und wählen Sie **Anmeldung abschließen**.

Der Status ist **Angemeldet**, **Nicht angemeldet** oder **Erneut anmelden**. **Erneut anmelden** bedeutet, dass OpenAI die gespeicherte Anmeldung nicht mehr annimmt; Aufträge schlagen fehl, bis sich ein Administrator erneut anmeldet. Eine Adresse von einem älteren Link wird abgelehnt und die Anmeldung wartet weiter; **Abbrechen** beendet sie. Lehnt OpenAI das Konto ab, etwa weil sein Abo nicht geteilt werden kann, endet die Anmeldung mit diesem Grund. **ChatGPT trennen** löscht die gespeicherte Anmeldung.

Die Anmeldung bleibt in einem privaten Ordner auf dem ADORE-Server. Vor jeder Phase holt ADORE daraus ein frisches Zugriffstoken, etwa eine Stunde gültig, und gibt nur dieses Token an Pi weiter; die Anmeldung selbst gelangt nie in den Container des Auftrags. Ein ChatGPT-Projekt läuft deshalb im Container, seine Phasenzeitlimits betragen höchstens 3000 Sekunden, und sein Image muss auf dem aktuellen ADORE-Executor-Image aufbauen. Nur Administratoren sehen oder ändern die Anmeldung; Audit-Einträge nennen die Aktion, nie ein Token oder eine Adresse.

> ADORE ist heute kostenlos. Es mit ChatGPT-Anmeldung als gehosteten oder kostenpflichtigen Dienst anzubieten, erfordert zuerst das Interessenformular von OpenAI.

## KI-Verbindung testen {#test-connection}

Administratoren wählen **KI-Verbindung testen** unter **KI-Verbindung**. Der Test startet Pi einmal in einem temporären Container, bzw. in einem temporären Ordner für auf dem Server installiertes Pi, lässt es einen Shell-Befehl ausführen und dann mit einem festen Text antworten und kann Anbietergebühren verursachen. Das Projekt muss inaktiv sein, gültige gespeicherte Einstellungen und keinen offenen Vorschlag haben; für ein Container-Projekt muss das konfigurierte Image auf dem Server vorhanden sein.

Das Ergebnis ist **KI-Modell verbunden** nur, wenn der Shell-Befehl lief und die Antwort ankam. Sonst kommt **KI-Verbindung nicht bestätigt** mit eigenem Hinweis für: keine gespeicherten Zugangsdaten, keine ChatGPT-Anmeldung, ein ChatGPT-Abo, das nicht geteilt werden kann, ein erreichtes ChatGPT-Nutzungslimit, einen vom Anbieter abgelehnten Schlüssel, einen Anbieter oder Endpunkt, den Pi nicht erreichen konnte, ein Modell, das Anbieter oder Endpunkt nicht kennen, ein Ratenlimit, einen anderen Anbieterfehler, eine Zeitüberschreitung, ein fehlendes Image oder Pi, oder einen Shell-Befehl, den Pi nicht ausführen konnte. Es wird kein Auftrag gestartet. Das gespeicherte Ergebnis ist an aktuellen Anbieter, Modell, Einstellungen und Zugangsdaten gebunden und erscheint in den Host-Prüfungen der Übersicht. Entwickler sehen es, können den Test aber nicht ausführen.

## Wo Aufträge laufen {#where-jobs-run}

| | Container | Native lokale Ausführung |
|---|---|---|
| Läuft in | Einem temporären Docker- oder Podman-Container auf dem ADORE-Server | Dem ADORE-Server selbst, unter dem Betriebssystemkonto des Dienstes, in einem eigenen Worktree |
| Umgebung | Einem vom Administrator vorbereiteten Projekt-Image | Werkzeugen, Versionen und Bibliotheken, die Sie selbst auf diesem Server installieren |
| Anmeldung | Der API-Schlüssel des Anbieters oder, bei einem ChatGPT-Abonnement, ein kurzlebiges Zugriffstoken aus der ChatGPT-Anmeldung des Servers | Der API-Schlüssel des Anbieters oder die vorhandene Pi-Anmeldung auf diesem Konto, an Ort und Stelle weiterverwendet |
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
