# Repository hinzufügen

Die menschliche Freigabe vor Veröffentlichung ist standardmäßig aktiv. Administratoren können **Menschliche Freigabe vor PR/MR verlangen** in Einstellungen ändern. Ohne diese Freigabe prüft ADORE vor Veröffentlichung Kandidat und Ziel auf Aktualität; Repository-Tests bleiben Aufgabe des Agenten.

Fügen Sie ein Repository als Projekt hinzu, damit ADORE seine bereiten Tickets aufnehmen, einen Coding-Agenten darauf ansetzen und Entwürfe für Merge Requests oder Pull Requests zur menschlichen Prüfung veröffentlichen kann. Nur Administratoren fügen Projekte hinzu, und ADORE führt nie einen Merge aus.


Eine aktuelle Umgebungsprüfung wird an das erstellte Projekt übertragen. Ungeprüfte Voraussetzungen bleiben teilweise geprüft; Konfigurationsänderungen machen das Ergebnis veraltet. Wiederholen Sie eine abgelaufene Prüfung.


Eine erfolgreiche externe CLI-Anmeldung bleibt teilweise geprüft, da sie sich außerhalb von ADORE unbemerkt ändern kann. Verbinden Sie den Repository-Zugang und prüfen Sie erneut, um die Projekt-Zugangsdaten zu binden.

## Bevor Sie beginnen {#before-you-start}

Halten Sie Folgendes bereit:

- Die Repository-Adresse (https oder ssh), die das Konto des ADORE-Servers lesen kann. ADORE klont das Repository beim Erstellen des Projekts in einen eigenen Ordner.
- Ein GitLab-, GitHub- oder Gitea-Konto, das Tickets lesen und aktualisieren und Review-Entwürfe erstellen darf.
- Die Namen des Bereitschafts- und des Freigabelabels. Ein Mensch setzt das Bereitschaftslabel, damit ein Ticket aufgenommen werden kann; siehe [Tickets für die automatische Aufnahme](/help/tickets#labels).
- Die Modell-ID für Pi und bei Containern einen laufenden Docker- oder Podman-Dienst. Das gemeinsame Standardimage wird beim Import automatisch vorbereitet; eigene Images müssen bereits in diesem Dienst vorhanden sein. Siehe [Executor und Modelle](/help/executors).

## Neues Projekt registrieren {#add-project}

Wählen Sie unter [Projekte](/projects) **Neues Projekt registrieren**. Der geführte Assistent beginnt mit Repository und Identität und besteht aus fünf Schritten; jede Änderung einer Angabe macht frühere Validierungen und Prüfungen ungültig.

Wenn keine Projekte mehr vorhanden sind, bieten Übersicht und Projekte Administratoren **Neues Projekt registrieren** und **Rohkonfiguration importieren** an. Nach dem Löschen des letzten Projekts kehren Sie zu Projekte zurück, wo beide Aktionen verfügbar bleiben.

| Schritt | Was abgefragt wird |
|---|---|
| Repository und Identität | **Repository-URL** und **Repository lesen**: ADORE füllt **Forge**, **Repository**, **Gitea tea login**, **Zielbranch** und die Projekt-ID zur Bestätigung aus und schlägt einen änderbaren **Lokaler Klonpfad** vor. **Weiter** bleibt deaktiviert, bis das Repository gelesen wurde. **Anzeigename** beginnt mit dem Repository-Namen; **Beschreibung** ist optional. |
| Agent und Modell | Wählen Sie **Anbieter**, **Modell** und bei Bedarf den Endpunkt. Wählen Sie für einen Container Laufzeit und Image. Speichern Sie den Anbieterschlüssel nach der Erstellung unter Einstellungen. Unter **Auf dem Server installiert** erscheinen das aktuelle Systemkonto und der optionale **PATH für Projektwerkzeuge**. |
| Eignung, Prüfer und Grenzen | **Bereitschaftslabel**, **Freigabelabel**, optional **Prüfende (kommagetrennt)** und vier Auftragslimits: Executor-Starts, aktive Sekunden, gemeldete Kosten in USD und geänderte Dateien. Ein Kostenlimit von 0 schaltet dieses Limit ab; es bedeutet nicht kostenlos. |
| Überprüfung | Beim Öffnen dieses Schritts werden Konfiguration, Serverordner, Git und Forge-Zugriff automatisch geprüft. **Umgebung erneut prüfen** wiederholt diese Prüfungen. **Workflow** zeigt separat den beobachteten Repository-Workflow, ohne die Registrierung zu sperren. Bei Ausführung auf dem Server zeigt **Pi auf dem Server** lokale Fehler wie inkompatible Node-Versionen. Bei Containerausführung werden die Engine und Pi im lokalen Image geprüft. Es wird nichts veröffentlicht. **Weiter** öffnet die Prüfung, sobald die Konfiguration gültig ist. |
| Prüfen und erstellen | Zeigt den exakten Kandidaten und die Serverorte sowie eine eingeklappte Liste **Auf Standard belassene Einstellungen** mit dem Standardwert jeder weiteren Einstellung (nur lesbar; nach dem Erstellen in den Einstellungen änderbar). **Ändern** führt zu einem Schritt zurück. **Mit gestoppter Aufnahme erstellen** klont zuerst das Repository (aus einer URL), prüft den Zielbranch und speichert dann das Projekt; sofern Sie **ADORE-Labels im Repository anlegen** nicht abwählen, legt es die fehlenden ADORE-Labels an und zeigt das Ergebnis; danach folgt **Projekt öffnen**. |

Für die native lokale Ausführung wählen Sie **Ausführung → Auf dem Server installiert**. Spezialisierte Container-Setups verwenden die erweiterte Server-TOML-Methode weiter unten.

Wählen Sie **Auf dem Server installiert** für das von ADORE verwaltete Pi unter dem aktuellen Systemkonto. Der optionale **PATH für Projektwerkzeuge** bestimmt die Werkzeugordner. Siehe [Pi auf dem Server installieren](/help/executors#installed-executors).

**Automatischer Speicherort** behält den vorgeschlagenen Klonpfad bei. Wählen Sie **Eigener Speicherort** und **Ordner wählen…**, um Ordner auf dem ADORE-Rechner zu durchsuchen. Ein Klick wählt eine Zeile; Doppelklick oder Eingabe öffnet den Ordner. Nutzen Sie Zurück oder Übergeordneter Ordner und dann **Ordner auswählen**, um genau den bestehenden Ordner zu bestätigen. Ein neues Ziel geben Sie direkt im Klonpfad des Hauptformulars ein. Die Auswahl erstellt nichts; Links und Netzwerkpfade werden abgewiesen. **Abbrechen** erhält den Entwurf. Ein beim Laden eingegebener Ordnerpfad bleibt in der Adressleiste stehen.

**Zielbranch** listet die Remote-Branches von GitHub, GitLab und Gitea auf, auch bei eigenen Instanzen. Der Standardbranch des Repositorys ist ausgewählt und mit **Standard** markiert. Wählen Sie bei Bedarf einen anderen Branch. **Repository lesen** aktualisiert die Liste und behält eine ausdrückliche Auswahl bei, solange der Branch existiert. Eine andere URL löscht die bisherigen Optionen. Ohne gemeldeten Standardbranch wählen Sie selbst; ohne Branches legen Sie zuerst einen im Repository an und lesen es erneut. Der Git-Zugriff des ADORE-Kontos wird verwendet; unbekannte Forge-Typen werden weiterhin manuell gewählt.

## Repository-Workflows {#workflows}

Bei Bestätigung der geführten Registrierung oder eines Konfigurationsimports bereitet ADORE fehlende gemeinsame Ausführungs- und Proxy-Images vor dem Speichern des Projekts vor. Die aktuelle Phase wird angezeigt; die erste Vorbereitung kann mehrere Minuten dauern und benötigt Internet auf dem Server. Weitere Importe verwenden die Images erneut. Nach einem Vorbereitungsfehler können Sie den Import ohne erneute Eingabe derselben Antworten wiederholen. Native Importe überspringen die Container-Vorbereitung. Eigene Images bleiben Aufgabe des Administrators.

**AEGIS / Direkt**. Der Agent wählt und führt Prüfungen gemäß den Repository-Anweisungen aus. Mit AEGIS folgt er den gespeicherten Phasen, sonst implementiert er das Ticket direkt. ADORE beobachtet Fortschritt und Journal, speichert den Kandidaten und fordert menschliche Freigabe an. Es startet keine zusätzlichen Repository-Tests oder strikten AEGIS-Prüfungen.

## Originalkonfiguration importieren {#import-project}

Wählen Sie unter [Projekte](/projects) **Originalkonfiguration importieren** und im Dialog eine exportierte ZIP oder UTF-8-Datei `config.toml`. ADORE prüft automatisch die Datei, Serverpfade, die Zuordnung des Statusordners und eingebettete Geheimnisse. Korrigieren Sie gemeldete Probleme in der Datei und wählen Sie sie erneut. Wählen Sie nach der Prüfung **Importieren**. Das neue Projekt startet mit pausierter Überwachung und übernimmt die Konfiguration bytegenau.

Wählen Sie die vollständige exportierte ZIP direkt: Konfiguration und Image-Definitionen werden zusammen importiert. ADORE prüft auch den Quellgraphen, die Image-Zuordnung und vorhandene Definitionen. Eine andere Definition mit demselben Root-Image-Namen wird abgelehnt. TOML-Dateien dürfen bis zu 512 KiB, ZIPs bis zu 18 MiB groß sein. Bauen Sie die Images separat auf dem Zielserver mit der enthaltenen Compose-Datei. Siehe [Einstellungen → Originalkonfiguration exportieren](/help/settings#toml).


Ein neues Projekt startet mit gestoppter Überwachung. Entwickler sehen es, sobald ein Administrator ihnen auf dem Reiter **Zugriff** Zugriff gewährt. Auf dem Reiter **Zusammenfassung**:

Die Zusammenfassung zeigt zusätzlich die Parallelgrenze, freie Plätze und wartende Aufträge als kompakte Rechtecke neben den Betriebsangaben.

1. Wählen Sie **Repository-Zugang**. Geben Sie die Adresse des Forge-Servers und ein in der Forge erstelltes Zugriffstoken ein, dann **Prüfen und verbinden**. Das bestätigt das Konto und den Lesezugriff auf das Repository. Das Token bleibt auf dem Server, nie im Browser. Alternativ melden Sie das Forge-Werkzeug unter dem ADORE-Dienstkonto an.
2. Wählen Sie **Host-Voraussetzungen prüfen**. Die Details betreffen Git, das Repository-Befehlswerkzeug, die Repository-Anmeldung, die Container-Engine, Pi im Image, bei einem ChatGPT-Abonnement außerdem die ChatGPT-Anmeldung des Servers, bei ausgeschaltetem [Internetzugang](/help/executors#internet) das Netzwerk-Proxy-Image und den Websuche-Schlüssel, wenn Brave oder Tavily einen braucht. Für ein Projekt, das direkt auf dem Server läuft, ersetzt **Lokale Ausführung** die Zeilen zu Container-Engine und Image: Sie prüft kompatibles Node, das von ADORE verwaltete Pi und die Zugangsdaten des Anbieters. Die separate Zeile **Workflow** bestimmt den Workflow, ohne AEGIS auszuführen. Das ist kein vollständiger Auftrag und belegt keine Push-Berechtigung.
3. Führen Sie **KI-Verbindung testen** in den Einstellungen aus, wie unter [Executor und Modelle](/help/executors#test-connection) beschrieben.
4. Wählen Sie **Überwachung aktivieren**. Die Kachel Überwachung wechselt von Pausiert auf Aktiv, und ADORE beginnt, Tickets mit dem Bereitschaftslabel aufzunehmen. **Überwachung pausieren** stoppt neue Aufnahmen, unterbricht aber keinen laufenden Auftrag.

## Archivieren, wiederherstellen und löschen {#lifecycle}

Archivierung und Löschung erfordern, dass alle Aufträge ihre Ausführung und Bereinigung beendet haben, auch bei bereits abgeschlossenem Status. Ressourcen ohne Eigentumsnachweis bleiben zur Prüfung erhalten.

Administratoren finden diese Schaltflächen auf dem Reiter Zusammenfassung.

- **Projekt archivieren** funktioniert, nachdem Aufträge beendet und eingereihte Anfragen abgearbeitet sind. Es behält Einstellungen, Verlauf, Kennzahlen und Audit-Einträge und stoppt neue Arbeit. **Projekt wiederherstellen** bringt es zurück.
- **Projekt löschen** erscheint nur bei archivierten Projekten und verlangt die Eingabe des Projektnamens. Es entfernt die ADORE-Einstellungen, den Auftragsverlauf, die Kennzahlen, die Container und die Worktrees des Projekts. Erhalten bleiben das Repository und seine Branches, Worktrees von an eine Person übergebenen Aufträgen, ein Auftragsstatus-Ordner außerhalb des ADORE-Verzeichnisses und der Audit-Verlauf. Das Löschen wird abgelehnt, solange Arbeit eingereiht oder nicht abgeschlossen ist. **Auch den lokalen Klon entfernen** (nicht angehakt) löscht zusätzlich den Klon, den ADORE in seinem Ordner `repos` angelegt hat; die Option erscheint nur für einen sauberen Klon des Repositorys dieses Projekts, den kein anderes Projekt nutzt und kein beim Löschen behaltener Worktree mehr braucht, sonst nennt der Dialog den Grund, warum der Klon bleibt.

> Das Löschen kann nicht rückgängig gemacht werden. Um ein Projekt danach anzupassen, siehe [Projekteinstellungen](/help/settings).

## Gitea-Anmeldung auf diesem Rechner {#gitea-sign-in}

ADORE nutzt zuerst die gespeicherte Projektverbindung. Andernfalls verwendet es die tea-Konfiguration des aktuellen Kontos. Meldet tea eine fehlende Anmeldung, prüft ADORE die Windows- oder Linux-Standardpfade und wählt die konfigurierte Anmeldung, genau eine Standardanmeldung oder die einzige vorhandene Anmeldung. Mehrere Konten ohne eindeutige Auswahl erfordern eine ausdrückliche Verbindung.

Die Erkennung beachtet `XDG_CONFIG_HOME`. Unter Windows prüft sie außerdem Local AppData, Roaming AppData und `.config` im Benutzerverzeichnis; unter Linux `.config` im Benutzerverzeichnis. Private Anwendungscaches werden nicht durchsucht und Zugangsdaten nicht zwischen Rechnern kopiert.

1. Öffnen Sie die **Übersicht** des Projekts und wählen Sie **Repository-Zugang**.
2. Geben Sie den Gitea-Ursprung bei Bedarf mit Port unter **Repository-Server** ein.
3. Erstellen Sie dort ein Token für das Konto mit Lese-/Änderungsrechten für Tickets und Entwurfsreviews und tragen Sie es unter **Zugriffstoken** ein.
4. Wählen Sie **Prüfen und verbinden**. Ein HTTP-Server erfordert die angezeigte Bestätigung. Ein Fehler erhält die gespeicherte Verbindung.
5. Prüfen Sie die Host-Voraussetzungen erneut. Git-Zugangsdaten für clone/push werden getrennt eingerichtet.

Richten Sie auf einem anderen Rechner dessen eigene CLI-Anmeldung ein oder nutzen Sie dieses Formular. Das Lieferarchiv enthält keine Benutzertokens.
