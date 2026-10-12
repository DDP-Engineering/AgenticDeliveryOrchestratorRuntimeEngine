# Repository hinzufügen

Fügen Sie ein Repository als Projekt hinzu, damit ADORE seine bereiten Tickets aufnehmen, einen Coding-Agenten darauf ansetzen und Entwürfe für Merge Requests oder Pull Requests zur menschlichen Prüfung veröffentlichen kann. Nur Administratoren fügen Projekte hinzu, und ADORE führt nie einen Merge aus.

## Bevor Sie beginnen {#before-you-start}

Halten Sie Folgendes bereit:

- Einen Git-Klon des Repositorys auf dem ADORE-Server mit einem `origin` und einem vorhandenen Zielbranch. Das Hinzufügen eines Projekts klont nie; der Pfad liegt auf dem Server, nicht auf Ihrem Computer.
- AEGIS, installiert in diesem Klon (`.agentic/aegis.py` und `.agentic/aegis.toml`). ADORE verwendet es so, wie es installiert ist, und ändert es nie. Seine Testbefehle laufen im Linux-Container, schreiben Sie sie also für den Container.
- Ein GitLab-, GitHub- oder Gitea-Konto, das Tickets lesen und aktualisieren und Review-Entwürfe erstellen darf.
- Die Namen des Bereitschafts- und des Freigabelabels. Ein Mensch setzt das Bereitschaftslabel, damit ein Ticket aufgenommen werden kann; siehe [Tickets für die automatische Aufnahme](/help/tickets#labels).
- Den Coding-Agenten, seine Modell-ID und ein Container-Image auf dem Server, das den Agenten enthält. Siehe [Executor und Modelle](/help/executors).

## Projekt hinzufügen {#add-project}

Wählen Sie unter [Projekte](/projects) **Projekt hinzufügen**. **Neues Projekt mit Anleitung** besteht aus sechs Schritten; jede Änderung einer Angabe macht frühere Validierungen und Prüfungen ungültig.

| Schritt | Was abgefragt wird |
|---|---|
| Registrierungsmethode | Nichts einzugeben. Der Schritt bestätigt, dass der Klon bereits auf dem Server liegt. |
| Repository und Identität | **Anzeigename**, **Stabile Projekt-ID** (Kleinbuchstaben, Ziffern, Punkt, Unterstrich oder Bindestrich, bis zu 64 Zeichen), optional **Beschreibung**, **Forge**, **Repository** als Eigentümer/Repository (keine URL), **Gitea tea login** (nur Gitea), **Lokaler Klonpfad** und **Zielbranch**. |
| Agent und Modell | **Executor** (opencode, codex, pi oder qwen), **Modell**, **Modell-Anmeldung** (api-key oder host-auth, Letzteres nur für OpenCode und Codex) und **Umgebungsreferenzen für Zugangsdaten**: Variablennamen wie LOCAL_API_KEY, nie Werte. |
| Eignung, Prüfer und Grenzen | **Bereitschaftslabel**, **Freigabelabel**, **Prüfende (kommagetrennt)** (mindestens eine Person) und vier Auftragslimits: Executor-Starts, aktive Sekunden, gemeldete Kosten in USD und geänderte Dateien. Ein Kostenlimit von 0 schaltet dieses Limit ab; es bedeutet nicht kostenlos. |
| Überprüfung | **Konfiguration validieren** prüft Struktur und Serverordner. **Umgebung prüfen** testet anschließend Git, das Forge-Werkzeug und die Anmeldung, die Container-Engine, den Agenten im Image, die AEGIS-Dateien und, wo möglich, den Modell-Endpunkt. Es wird nichts veröffentlicht. |
| Prüfen und erstellen | Zeigt den exakten Kandidaten und die Serverorte. **Ändern** führt zu einem Schritt zurück. **Mit gestoppter Aufnahme erstellen** speichert das Projekt; danach folgt **Projekt öffnen**. |

Der Assistent verwendet das Standard-Containerprofil. Native lokale Ausführung und spezialisierte Container-Setups verwenden die erweiterte Server-TOML-Methode weiter unten.

## Projekt importieren {#import-project}

Dieselbe Seite bietet drei weitere Methoden.

- **Portable Einstellungen importieren** liest eine portable JSON-Datei (bis 64 KiB) derselben ADORE-Version. **Projekteinstellungen kopieren** liest ein anderes Projekt, auf das Sie Zugriff haben. Beide übertragen nur 15 Arbeitsregeln (Abfrage, Bereitschaft, Wiederherstellung, Auftragsbudgets); Identität, Repository, Labels, Zugangsdaten, Endpunkte, Images und Verlauf werden nie kopiert. Wählen Sie **Quellregeln prüfen**, dann **Neues Ziel einrichten** und beantworten Sie die Schritte der Anleitung. Prüfen Sie unbekannte Dateien: Die Prüfsumme erkennt Änderungen, belegt aber nicht die Urheberschaft.
- **Erweitert: unveränderte Server-TOML-Kopie** öffnet [Eine vorhandene Konfiguration für diesen ADORE-Server registrieren](/projects/import). Sie nimmt eine vorhandene ADORE-`config.toml` (UTF-8, bis 512 KiB) mit absoluten Serverpfaden und ohne Geheimnisse, kopiert sie bytegenau und endet mit **Mit gestoppter Aufnahme registrieren**. Ein Verlauf erscheint nur, wenn seine Daten bereits im deklarierten Statusordner liegen.

## Nach der Erstellung {#after-creation}

Ein neues Projekt startet mit gestoppter Überwachung. Entwickler sehen es, sobald ein Administrator ihnen auf dem Reiter **Zugriff** Zugriff gewährt. Auf dem Reiter **Zusammenfassung**:

1. Wählen Sie **Repository verbinden**. Geben Sie die Adresse des Forge-Servers und ein in der Forge erstelltes Zugriffstoken ein, dann **Prüfen und verbinden**. Das bestätigt das Konto und den Lesezugriff auf das Repository. Das Token bleibt auf dem Server, nie im Browser. Alternativ melden Sie das Forge-Werkzeug unter dem ADORE-Dienstkonto an.
2. Wählen Sie **Host-Voraussetzungen prüfen**. Die Details betreffen Git, das Repository-Befehlswerkzeug, die Repository-Anmeldung, die Container-Engine, den Agenten im Image, die AEGIS-Dateien und die Verbindung zum KI-Modell. Das ist kein vollständiger Auftrag und belegt keine Push-Berechtigung.
3. Führen Sie **KI-Verbindung testen** in den Einstellungen aus, wie unter [Executor und Modelle](/help/executors#test-connection) beschrieben.
4. Wählen Sie **Überwachung aktivieren**. Die Kachel Überwachung wechselt von Pausiert auf Aktiv, und ADORE beginnt, Tickets mit dem Bereitschaftslabel aufzunehmen. **Überwachung pausieren** stoppt neue Aufnahmen, unterbricht aber keinen laufenden Auftrag.

## Archivieren, wiederherstellen und löschen {#lifecycle}

Administratoren finden diese Schaltflächen auf dem Reiter Zusammenfassung.

- **Projekt archivieren** funktioniert, nachdem Aufträge beendet und eingereihte Anfragen abgearbeitet sind. Es behält Einstellungen, Verlauf, Kennzahlen und Audit-Einträge und stoppt neue Arbeit. **Projekt wiederherstellen** bringt es zurück.
- **Projekt löschen** erscheint nur bei archivierten Projekten und verlangt die Eingabe des Projektnamens. Es entfernt die ADORE-Einstellungen, den Auftragsverlauf, die Kennzahlen, die Container und die Worktrees des Projekts. Erhalten bleiben das Repository und seine Branches, Worktrees von an eine Person übergebenen Aufträgen, ein Auftragsstatus-Ordner außerhalb des ADORE-Verzeichnisses und der Audit-Verlauf. Das Löschen wird abgelehnt, solange Arbeit eingereiht oder nicht abgeschlossen ist.

> Das Löschen kann nicht rückgängig gemacht werden. Um ein Projekt danach anzupassen, siehe [Projekteinstellungen](/help/settings).
