# Repository hinzufügen

Fügen Sie ein Repository als Projekt hinzu, damit ADORE seine bereiten Tickets aufnehmen, einen Coding-Agenten darauf ansetzen und Entwürfe für Merge Requests oder Pull Requests zur menschlichen Prüfung veröffentlichen kann. Nur Administratoren fügen Projekte hinzu, und ADORE führt nie einen Merge aus.

## Bevor Sie beginnen {#before-you-start}

Halten Sie Folgendes bereit:

- Die Repository-Adresse (https oder ssh), die das Konto des ADORE-Servers lesen kann. ADORE klont das Repository beim Erstellen des Projekts in einen eigenen Ordner.
- AEGIS, installiert im Repository (`.agentic/aegis.py` und `.agentic/aegis.toml`). ADORE verwendet es so, wie es installiert ist, und ändert es nie. Seine Testbefehle laufen im Linux-Container, schreiben Sie sie also für den Container.
- Ein GitLab-, GitHub- oder Gitea-Konto, das Tickets lesen und aktualisieren und Review-Entwürfe erstellen darf.
- Die Namen des Bereitschafts- und des Freigabelabels. Ein Mensch setzt das Bereitschaftslabel, damit ein Ticket aufgenommen werden kann; siehe [Tickets für die automatische Aufnahme](/help/tickets#labels).
- Die Modell-ID für den Coding-Agenten Pi und, für ein Container-Projekt, ein Image auf dem Server auf Basis des ADORE-Basis-Images, das Pi enthält. Siehe [Executor und Modelle](/help/executors).

## Neues Projekt registrieren {#add-project}

Wählen Sie unter [Projekte](/projects) **Neues Projekt registrieren**. Der geführte Assistent beginnt mit Repository und Identität und besteht aus fünf Schritten; jede Änderung einer Angabe macht frühere Validierungen und Prüfungen ungültig.

| Schritt | Was abgefragt wird |
|---|---|
| Repository und Identität | **Repository-URL** und **Repository lesen**: ADORE füllt **Forge**, **Repository**, **Gitea tea login**, **Zielbranch** und die Projekt-ID zur Bestätigung aus und schlägt einen änderbaren **Lokaler Klonpfad** vor. **Weiter** bleibt deaktiviert, bis das Repository gelesen wurde. **Anzeigename** beginnt mit dem Repository-Namen; **Beschreibung** ist optional. |
| Agent und Modell | **Anbieter** und **Modell** (Pi-Liste des Anbieters oder eine eingegebene Modell-ID), dazu **Endpunkt-Basis-URL** (die Adresse aus Sicht des Containers) und **Endpunkt-API-Typ** für einen OpenAI-kompatiblen Endpunkt; die Hilfe nennt die API-Schlüsselvariable, die nach dem Anlegen in den Einstellungen gespeichert wird, **Ausführung** (**Container** oder **Auf dem Server installiert**), **Modell-Anmeldung** (api-key bei Container; api-key oder die bestehende Kontoanmeldung bei Auf dem Server installiert) und **Umgebungsreferenzen für Zugangsdaten**: Variablennamen wie LOCAL_API_KEY, nie Werte; bei der bestehenden Kontoanmeldung bleiben sie leer. Bei Container folgen **Container-Laufzeit** (docker oder podman) und **Executor-Image**: freier Text mit Vorschlägen aus den Images auf dem ADORE-Server und ein Hinweis, wenn das eingegebene Image dort fehlt. Bei Auf dem Server installiert erscheinen der native Executor-Befehl und die Felder des lokalen Kontos. |
| Eignung, Prüfer und Grenzen | **Bereitschaftslabel**, **Freigabelabel**, optional **Prüfende (kommagetrennt)** und vier Auftragslimits: Executor-Starts, aktive Sekunden, gemeldete Kosten in USD und geänderte Dateien. Ein Kostenlimit von 0 schaltet dieses Limit ab; es bedeutet nicht kostenlos. |
| Überprüfung | **Konfiguration validieren** prüft Struktur und Serverordner. **Umgebung prüfen** testet anschließend Git, das Forge-Werkzeug und die Anmeldung, die Container-Engine, Pi im Image und die AEGIS-Dateien. Es wird nichts veröffentlicht. Jedes Ergebnis erscheint neben seiner Schaltfläche; **Weiter** öffnet die Prüfung, sobald die Konfiguration gültig ist. |
| Prüfen und erstellen | Zeigt den exakten Kandidaten und die Serverorte sowie eine eingeklappte Liste **Auf Standard belassene Einstellungen** mit dem Standardwert jeder weiteren Einstellung (nur lesbar; nach dem Erstellen in den Einstellungen änderbar). **Ändern** führt zu einem Schritt zurück. **Mit gestoppter Aufnahme erstellen** klont zuerst das Repository (aus einer URL), prüft AEGIS und den Zielbranch und speichert dann das Projekt; sofern Sie **ADORE-Labels im Repository anlegen** nicht abwählen, legt es die fehlenden ADORE-Labels an und zeigt das Ergebnis; danach folgt **Projekt öffnen**. |

Für die native lokale Ausführung wählen Sie **Ausführung → Auf dem Server installiert**. Spezialisierte Container-Setups verwenden die erweiterte Server-TOML-Methode weiter unten.

## Projektkonfiguration importieren {#import-project}

Wählen Sie unter [Projekte](/projects) **Projektkonfiguration importieren**, um eine vorhandene ADORE-`config.toml` unverändert zu registrieren, etwa eine per Kommandozeile erstellte oder früher mit **Originalkonfiguration herunterladen** in den Einstellungen eines Projekts gespeicherte. Die Datei (UTF-8, bis 512 KiB) braucht absolute Serverpfade und keine eingebetteten Geheimnisse: Die Prüfung listet gefundene auf, ersetzen Sie sie zuerst durch Umgebungsreferenzen. Ihre Projekt-ID und ihr Statusordner dürfen keinem registrierten Projekt gehören. ADORE kopiert die Datei bytegenau und endet mit **Mit gestoppter Aufnahme registrieren**. Ein Verlauf erscheint nur, wenn seine Daten bereits im deklarierten Statusordner liegen.

## Projektkonfiguration klonen {#clone-project}

Wählen Sie unter [Projekte](/projects) **Projektkonfiguration klonen**, um ein neues Projekt mit den Arbeitsregeln eines anderen zu beginnen. **Aus einem Projekt auf diesem Server** liest ein Projekt, auf das Sie Zugriff haben; **Aus einer portablen Einstellungsdatei** liest eine portable JSON-Datei (bis 64 KiB) derselben ADORE-Version. Übernommen werden nur 15 Arbeitsregeln (Abfrage, Bereitschaft, Wiederherstellung, Auftragsbudgets); Identität, Repository, Labels, Zugangsdaten, Endpunkte, Images und Verlauf werden nie kopiert. Wählen Sie **Quellregeln prüfen**, dann **Neues Ziel einrichten** und beantworten Sie die Schritte der Anleitung. Prüfen Sie unbekannte Dateien: Die Prüfsumme erkennt Änderungen, belegt aber nicht die Urheberschaft.

## Nach der Erstellung {#after-creation}

Ein neues Projekt startet mit gestoppter Überwachung. Entwickler sehen es, sobald ein Administrator ihnen auf dem Reiter **Zugriff** Zugriff gewährt. Auf dem Reiter **Zusammenfassung**:

1. Wählen Sie **Repository verbinden**. Geben Sie die Adresse des Forge-Servers und ein in der Forge erstelltes Zugriffstoken ein, dann **Prüfen und verbinden**. Das bestätigt das Konto und den Lesezugriff auf das Repository. Das Token bleibt auf dem Server, nie im Browser. Alternativ melden Sie das Forge-Werkzeug unter dem ADORE-Dienstkonto an.
2. Wählen Sie **Host-Voraussetzungen prüfen**. Die Details betreffen Git, das Repository-Befehlswerkzeug, die Repository-Anmeldung, die Container-Engine, Pi im Image und die AEGIS-Dateien. Für ein Projekt, das direkt auf dem Server läuft, ersetzt **Lokale Ausführung** die Zeilen zu Container-Engine und Image: Sie prüft das installierte Pi für das Serverkonto und seine vorhandene Anmeldung oder einen Anbieter-API-Schlüssel. Das ist kein vollständiger Auftrag und belegt keine Push-Berechtigung.
3. Führen Sie **KI-Verbindung testen** in den Einstellungen aus, wie unter [Executor und Modelle](/help/executors#test-connection) beschrieben.
4. Wählen Sie **Überwachung aktivieren**. Die Kachel Überwachung wechselt von Pausiert auf Aktiv, und ADORE beginnt, Tickets mit dem Bereitschaftslabel aufzunehmen. **Überwachung pausieren** stoppt neue Aufnahmen, unterbricht aber keinen laufenden Auftrag.

## Archivieren, wiederherstellen und löschen {#lifecycle}

Administratoren finden diese Schaltflächen auf dem Reiter Zusammenfassung.

- **Projekt archivieren** funktioniert, nachdem Aufträge beendet und eingereihte Anfragen abgearbeitet sind. Es behält Einstellungen, Verlauf, Kennzahlen und Audit-Einträge und stoppt neue Arbeit. **Projekt wiederherstellen** bringt es zurück.
- **Projekt löschen** erscheint nur bei archivierten Projekten und verlangt die Eingabe des Projektnamens. Es entfernt die ADORE-Einstellungen, den Auftragsverlauf, die Kennzahlen, die Container und die Worktrees des Projekts. Erhalten bleiben das Repository und seine Branches, Worktrees von an eine Person übergebenen Aufträgen, ein Auftragsstatus-Ordner außerhalb des ADORE-Verzeichnisses und der Audit-Verlauf. Das Löschen wird abgelehnt, solange Arbeit eingereiht oder nicht abgeschlossen ist. **Auch den lokalen Klon entfernen** (nicht angehakt) löscht zusätzlich den Klon, den ADORE in seinem Ordner `repos` angelegt hat; die Option erscheint nur für einen sauberen Klon des Repositorys dieses Projekts, den kein anderes Projekt nutzt und kein beim Löschen behaltener Worktree mehr braucht, sonst nennt der Dialog den Grund, warum der Klon bleibt.

> Das Löschen kann nicht rückgängig gemacht werden. Um ein Projekt danach anzupassen, siehe [Projekteinstellungen](/help/settings).
