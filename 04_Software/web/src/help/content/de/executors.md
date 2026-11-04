# Executor und Modelle

Ein Executor ist das, was ADORE für jeden Auftrag startet: der Coding-Agent Pi und das KI-Modell, das er verwendet. Administratoren wählen das Modell in den Einstellungen eines Projekts.

## Was ein Executor ist {#what}

Für jeden Auftrag startet ADORE Pi, seinen einzigen Coding-Agenten, in einer isolierten Arbeitskopie, und Pi arbeitet die AEGIS-Phasen des Repositorys mit dem konfigurierten Anbieter und Modell ab. ADORE verwendet das Pi im Image für Containeraufträge und seine verwaltete Pi-Installation für Serveraufträge.

## Anbieter und Modell wählen {#agent-and-model}

Öffnen Sie **Einstellungen → Agent und Modell**. Bearbeiten Sie **Anbieter**, **Modell** und bei einem Endpunkt **Endpunkt-Basis-URL** und **Endpunkt-API-Typ** gemeinsam in einer geprüften Änderung.

- **Anbieter**: ein Pi-Anbieter mit API-Schlüssel (OpenAI, Anthropic, Google Gemini, OpenRouter, Mistral und weitere), **ChatGPT-Abonnement** oder **OpenAI-kompatibler Endpunkt**.
- **Modell**: aus der Pi-Liste für diesen Anbieter wählen oder eine vom Anbieter akzeptierte Modell-ID eingeben, z. B. `gpt-5.4`. Die Liste gehört zur von ADORE ausgelieferten Pi-Version und wird ohne Internetzugang gelesen. Es gibt kein universelles Standardmodell.
- **ChatGPT-Abonnement**: Pi nutzt das ChatGPT-Plus- oder -Pro-Konto, bei dem dieser ADORE-Server angemeldet ist, siehe [Mit ChatGPT anmelden](#chatgpt). Die Liste enthält die Modelle, die ein ChatGPT-Abonnement bedient, zum Beispiel `gpt-5.6-luna`.

**Kandidaten vorbereiten** zeigt aktive und vorgeschlagene Werte. **Änderung anwenden** speichert sie; siehe [Projekteinstellungen](/help/settings#editing) zum Pausieren der Überwachung. ADORE startet je Phase einen neuen Pi-Prozess und beendet ihn bei Zeitüberschreitung oder Abbruch.

## OpenAI-kompatibler Endpunkt {#endpoint}

Für ein Modell aus dem eigenen Netzwerk, etwa LM Studio, Ollama oder vLLM, wählen Sie **OpenAI-kompatibler Endpunkt** und füllen aus:

- **Endpunkt-Basis-URL**: die Adresse aus Sicht von Pi. Bei **Container** gilt die Adresse aus Sicht des Containers; bei Serveraufträgen aus Sicht des Servers.
- **Endpunkt-API-Typ**: `openai-completions` für LM Studio, Ollama und vLLM; `openai-responses`, `anthropic-messages` und `google-generative-ai` werden ebenfalls akzeptiert.
- **Modell**: die Modell-ID, die der Endpunkt bereitstellt.

Ein Endpunkt-Schlüssel ist optional: Speichern Sie ihn unter Authentifizierung als ADORE_ENDPOINT_API_KEY. ADORE beschreibt Pi den Endpunkt für jeden Auftrag; die Adresse enthält nie Benutzername, Passwort oder Abfrage. Bei ausgeschaltetem [Internetzugang](#internet) erlaubt ADORE die Adresse des Endpunkts selbst. Ein Endpunkt ist für Container- und Serverprojekte verfügbar.

## Authentifizierung {#credentials}

Öffnen Sie **Authentifizierung** in derselben Gruppe.

- **API-Schlüssel des Anbieters.** Das Feld nennt die Variable, die der konfigurierte Anbieter braucht, z. B. OPENAI_API_KEY für OpenAI oder ANTHROPIC_API_KEY für Anthropic. Geben Sie den **API-Schlüssel** ein und wählen Sie **API-Schlüssel speichern**. ADORE speichert ihn privat im Zugangsdatenspeicher des Projekts auf dem Server, nie in der Konfigurationsdatei, gibt ihn Pi nur als diese Variable weiter und zeigt ihn nie wieder an; **Projekt-API-Schlüssel entfernen** löscht ihn. Eine Schlüsseländerung erfordert pausierte Überwachung, ein inaktives Projekt und keinen offenen Vorschlag und prüft den Schlüssel nicht.
- **Serverprojekte.** Speichern Sie bei Bedarf den **Anbieter-API-Schlüssel**. ADORE ignoriert die persönliche Pi-Anmeldung. Nutzen Sie die gemeinsame [ChatGPT-Anmeldung](#chatgpt) für ein Abo unter Windows oder Linux einschließlich WSL2.
- **Von der Umgebung verwaltete Werte.** Eine bereits in der Umgebung des ADORE-Servers gesetzte Variable trägt den Hinweis **Auf dem ADORE-Server gesetzt; extern verwalten**. Die Weboberfläche kann sie nicht überschreiben.
- **Websuche-Schlüssel.** Bei eingeschaltetem Internetzugang und Websuche Brave oder Tavily listet das Feld auch BRAVE_API_KEY oder TAVILY_API_KEY, gespeichert auf dieselbe Weise, auch für ein ChatGPT-Abonnement.
- **Zusätzliche Zugangsdaten-Variablen.** Nur Namen (**Zugangsdaten-Variable hinzufügen**) weiterer Geheimnisse, die Pi neben dem Schlüssel des Anbieters erhält; die meisten Projekte brauchen keine.

Zugangsdatenwerte erscheinen nie in der Konfigurationsdatei, in Prüfungen, Audit-Einträgen, Protokollen oder Exporten.

## Mit ChatGPT anmelden {#chatgpt}

Ein ChatGPT-Plus- oder -Pro-Konto dient allen Projekten dieses ADORE-Servers, deren Anbieter **ChatGPT-Abonnement** ist. Administratoren melden sich unter **Authentifizierung** eines solchen Projekts an; ADORE führt die OpenAI-Anmeldung von Pi aus, daher braucht der Server keinen Browser.

Auf dem nativen Server kann Pi den Browser-Rückruf direkt empfangen und ADORE zeigt den Abschluss automatisch an. Andernfalls folgen Sie den manuellen Schritten unten.

1. Wählen Sie **Mit ChatGPT anmelden**.
2. Öffnen Sie **ChatGPT-Anmeldeseite öffnen** auf Ihrem eigenen Computer und melden Sie sich mit dem ChatGPT-Konto an. Der Link ist 15 Minuten gültig.
3. Der Browser zeigt danach eine Fehlerseite unter `127.0.0.1:1455`. Das ist erwartet: Kopieren Sie die vollständige Adresse aus seiner Adressleiste.
4. Fügen Sie sie unter **Weiterleitungsadresse** ein und wählen Sie **Anmeldung abschließen**.

Der Status ist **Angemeldet**, **Nicht angemeldet** oder **Erneut anmelden**. **Erneut anmelden** bedeutet, dass OpenAI die gespeicherte Anmeldung nicht mehr annimmt; Aufträge schlagen fehl, bis sich ein Administrator erneut anmeldet. Eine Adresse von einem älteren Link wird abgelehnt und die Anmeldung wartet weiter; **Abbrechen** beendet sie. Lehnt OpenAI das Konto ab, etwa weil sein Abo nicht geteilt werden kann, endet die Anmeldung mit diesem Grund. **ChatGPT trennen** löscht die gespeicherte Anmeldung.

Die Anmeldung bleibt in einem privaten Ordner auf dem ADORE-Server. Vor jeder Phase holt ADORE daraus ein frisches Zugriffstoken, etwa eine Stunde gültig, und gibt nur dieses Token an Pi weiter; die Anmeldung selbst gelangt nie in den Container des Auftrags. ChatGPT-Projekte laufen im Container oder nativ unter Windows/Linux einschließlich WSL2. Die native Anmeldung nutzt von ADORE verwaltetes Pi ohne Docker; Container nutzen das aktuelle ADORE-Image. Phasen sind in beiden Modi auf 3000 Sekunden begrenzt. Nur Administratoren sehen oder ändern die Anmeldung; Audit-Einträge nennen die Aktion, nie ein Token oder eine Adresse.

> ADORE ist heute kostenlos. Es mit ChatGPT-Anmeldung als gehosteten oder kostenpflichtigen Dienst anzubieten, erfordert zuerst das Interessenformular von OpenAI.

## KI-Verbindung testen {#test-connection}

Administratoren wählen **KI-Verbindung testen** unter **KI-Verbindung**. Der Test startet Pi einmal in einem temporären Container, bzw. in einem temporären Ordner für auf dem Server installiertes Pi, lässt es einen Shell-Befehl ausführen und dann mit einem festen Text antworten und kann Anbietergebühren verursachen. Das Projekt muss inaktiv sein, gültige gespeicherte Einstellungen und keinen offenen Vorschlag haben; für ein Container-Projekt muss das konfigurierte Image auf dem Server vorhanden sein.

Das Ergebnis ist **KI-Modell verbunden** nur, wenn der Shell-Befehl lief und die Antwort ankam. Sonst kommt **KI-Verbindung nicht bestätigt** mit eigenem Hinweis für: keine gespeicherten Zugangsdaten, keine ChatGPT-Anmeldung, ein ChatGPT-Abo, das nicht geteilt werden kann, ein erreichtes ChatGPT-Nutzungslimit, einen vom Anbieter abgelehnten Schlüssel, einen Anbieter oder Endpunkt, den Pi nicht erreichen konnte, ein Modell, das Anbieter oder Endpunkt nicht kennen, ein Ratenlimit, einen anderen Anbieterfehler, eine Zeitüberschreitung, ein fehlendes Image oder Pi, oder einen Shell-Befehl, den Pi nicht ausführen konnte. Es wird kein Auftrag gestartet. Das gespeicherte Ergebnis ist an aktuellen Anbieter, Modell, Einstellungen und Zugangsdaten gebunden und erscheint in den Host-Prüfungen der Übersicht. Entwickler sehen es, können den Test aber nicht ausführen.

## Internetzugang für den Agenten {#internet}

**Internetzugang für den Agenten** unter Einstellungen → Agent und Modell bestimmt, was der Container eines Auftrags erreichen kann. Standardmäßig ist er **Aus**.

- **Aus**: Der Container erreicht nur den Modellanbieter. ADORE erlaubt die Adressen des Anbieters selbst, bei einem OpenAI-kompatiblen Endpunkt dessen Adresse, über einen eigenen Netzwerk-Proxy je Auftrag. Websuche, Seitenlesen und Downloads wie `curl`, `npm install` oder `pip install` schlagen fehl, und Pi wird darauf hingewiesen.
- **An**: Der Container hat ein offenes Netzwerk. Pi kann im Web suchen, Seiten lesen und Bibliotheken mit `curl`, `npm` oder `pip` herunterladen.

**Websuche** wählt den Suchdienst, solange der Zugang an ist: **Exa (ohne Schlüssel)**, der Standard, **Brave (Schlüssel nötig)**, **Tavily (Schlüssel nötig)** oder **Keine** (keine Websuche und kein Seitenlesen). Für Brave oder Tavily speichern Sie BRAVE_API_KEY oder TAVILY_API_KEY unter **Authentifizierung**.

> Bei eingeschaltetem Internetzugang könnte eine bösartige Webseite versuchen, den Agenten seinen API-Schlüssel oder sein ChatGPT-Token versenden zu lassen. Verwenden Sie möglichst eingeschränkte, kurzlebige Schlüssel.

Beide Einstellungen ändern sich wie andere über **Kandidat vorbereiten** und **Anwenden**. Bei ausgeschaltetem Internetzugang muss das Proxy-Image auf dem ADORE-Server vorhanden sein; **Host-Voraussetzungen prüfen** meldet es, ebenso den Suchschlüssel, wenn er nötig ist. Für ein auf dem Server installiertes Projekt wird der Schalter als **Nicht durchgesetzt** angezeigt: Pi erreicht alles, was der Server erreicht.

## Wo Aufträge laufen {#where-jobs-run}

| | Container | Native lokale Ausführung |
|---|---|---|
| Läuft in | Einem temporären Docker- oder Podman-Container auf dem ADORE-Server | Dem ADORE-Server selbst, unter dem Betriebssystemkonto des Dienstes, in einem eigenen Worktree |
| Umgebung | Einem vom Administrator vorbereiteten Projekt-Image | Werkzeugen, Versionen und Bibliotheken, die Sie selbst auf diesem Server installieren |
| Anmeldung | Der API-Schlüssel des Anbieters oder, bei einem ChatGPT-Abonnement, ein kurzlebiges Zugriffstoken aus der ChatGPT-Anmeldung des Servers | Der Anbieterschlüssel oder ein temporäres Token der ChatGPT-Anmeldung des Servers |
| Agent-Einstellungen | Das im Image enthaltene Pi mit von ADORE festgelegten Einstellungen; persönliche Pi-Einstellungen und Skills werden nicht gelesen | Von ADORE verwaltetes Pi mit eigenen Einstellungen und Erweiterungen |
| Isolation | Container; bei ausgeschaltetem Internetzugang erreicht er nur den Modellanbieter | Nur der Worktree; Befehle erreichen alles, was das Konto erreicht, verwenden Sie daher ein eigenes Konto mit minimalen Rechten |
| Gewählt | **Ausführung** → **Container**, Standard, in Schritt 2 der Registrierung oder unter Einstellungen → Agent und Modell | **Ausführung** → **Auf dem Server installiert**, oder im Serverprofil oder per TOML-Registrierung |

**Auf dem Server installiert** nutzt das aktuelle Systemkonto und bietet einen optionalen **PATH für Projektwerkzeuge**. Der Startbefehl ist fest.

**Host-Voraussetzungen prüfen** überspringt die Container-Engine und prüft Node, das verwaltete Pi und die Zugangsdaten des gewählten Anbieters.

## Pi auf dem Server installieren {#installed-executors}

Führen Sie `adore pi install` und `adore pi verify` als ADORE-Dienstkonto auf dem Server aus. Verwenden Sie Node ab 22.23.4 aus der Reihe 22.x mit npm. Liegt Node außerhalb des Dienst-PATH, setzen Sie `ADORE_NODE` auf den absoluten Pfad.

Führen Sie `adore pi install` erneut aus, sobald eine neue ADORE-Version eine andere Pi-Version festlegt. Globales Pi wird nicht benötigt; persönliche Einstellungen und Erweiterungen werden ignoriert.

Windows nutzt das PowerShell-Werkzeug; unter Linux richtet die Serveradministration einen delegierten cgroup-v2-Pfad ein. Pi fragt nicht nach Berechtigungen. Verwenden Sie ein eigenes Systemkonto.

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

Setzen Sie bei einem eigenen WSL-Laufzeitbefehl `--` oder `--exec` vor den Containerbefehl. Die Standardeinträge für Docker und Podman werden automatisch behandelt.

Bestätigen Sie anschließend mit **Host-Voraussetzungen prüfen** und **KI-Verbindung testen**.

## Systempakete {#system-packages}

Administratoren können **Systempaketinstallation durch den Agenten erlauben** unter **Einstellungen → Agent und Modell** prüfen. Die Berechtigung ist standardmäßig aus und nur für Container verfügbar. Pi installiert dann direkt mit `sudo -n`, liest die Ergebnisse und reagiert innerhalb der Auftragslimits. **Internetzugang für den Agenten** bleibt eine eigene Wahl; bei Aus benötigen externe Paketquellen einen erlaubten Host. Nutzen Sie ein Image mit sudo, pausieren Sie die Überwachung und warten Sie auf das Ende aktiver Arbeit, bevor Sie anwenden und einen neuen Auftrag starten. Pakete bleiben im Container und ändern das Image nicht.
