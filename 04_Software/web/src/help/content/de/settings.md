# Projekteinstellungen

Der Reiter Einstellungen eines Projekts listet die Arbeitsregeln auf, die ADORE dafür anwendet: welche Tickets aufgenommen werden, welche Limits gelten, wie veröffentlicht wird und welcher Agent verwendet wird. Administratoren ändern sie in einem geprüften Ablauf, eine Einstellung nach der anderen; Entwickler lesen sie.

## Wo Sie die Einstellungen finden {#where}

Öffnen Sie [Projekte](/projects), wählen Sie ein Projekt und dann den Reiter **Einstellungen**. Die Reiter sind Zusammenfassung, Einstellungen, Aufträge, Statistiken, Verlauf und, für Administratoren, Zugriff.

Administratoren können bearbeiten. Entwickler mit Zugriff auf das Projekt sehen **Schreibgeschützte Einstellungen**, ohne Schaltflächen zum Bearbeiten und ohne Geheimnisse oder Finanzeinstellungen. Jedes Projekt hat eigene Einstellungen; die globale Kapazität und die Audit-Aufbewahrung gehören zur Verwaltung. Die Einstellungen aktualisieren sich nicht selbst, lesen Sie sie daher mit Aktualisieren in der Kopfzeile neu.

## Einstellungsgruppen {#groups}

Jede Gruppe ist beim Öffnen der Einstellungen eingeklappt, und die Zahl neben ihrem Namen gibt die Anzahl ihrer Zeilen an.

| Gruppe | Was sie steuert |
|---|---|
| Repository | Forge und Repository, Gitea-Login, **Zielbranch** (Basis neuer Aufträge und Ziel der PR/MRs), die Vorlage für den Namen des Auftrags-Branches mit optionaler Namensregel und einem Live-Beispiel sowie Anzeigename, Ressourcenname und Commit-Autor-E-Mail des Agenten. |
| Tickets | **Label für aufnahmebereite Tickets**, **Label zum Ausschluss von der Aufnahme**, die eingeklappten **Statuslabels**, wie oft ADORE die Forge prüft, ob Tickets Akzeptanzkriterien oder ein Prioritätslabel brauchen, und den Standard-Aufgabentyp. Siehe [Tickets für die automatische Aufnahme](/help/tickets#labels). |
| Implementierung | Limits je Auftrag: **Limit aktiver Aufträge**, **Maximale Executor-Starts je Auftrag**, **Zeitlimit für aktive Arbeit (Sekunden)**, **Kostenlimit je Auftrag (USD)**, **Maximale geänderte Dateien je Auftrag** und **Zeitlimit je Phasenversuch (Sekunden)**. Außerdem **Rückfragen**, **Wiederherstellung nach Fehlern**, **Erweiterte Zeitlimits pro Phase**, **Fortschrittscommits veröffentlichen** und das Label für den Schnellpfad. |
| PR/MR und Review | **Review anfordern von**, **PR/MR-Status bei Veröffentlichung** (Entwurf oder Bereit zur Prüfung), das Freigabelabel, **Branch nach menschlichem Merge entfernen**, Überarbeitungsrunden und **Aktion bei fehlgeschlagenen PR/MR-CI-Prüfungen** (Automatisch reparieren, Nur benachrichtigen oder Ignorieren). |
| Statistik | **Messwerte abgeschlossener Aufträge erfassen** und **Vom Agenten gemeldete Token erfassen**. **Statistik-Datenbankdatei** wird nur zur Information angezeigt. |
| Agent und Modell | Der Coding-Agent, der Startbefehl, das Modell, die Authentifizierung und **KI-Verbindung testen**. Siehe [Executor und Modelle](/help/executors). |
| Technische Details | Schreibgeschützte Installationswerte wie der Auftragsstatus-Ordner, der lokale Repository-Pfad und die Arbeitsordner der Aufträge. Sie werden in der `config.toml` des Projekts auf dem Server geändert, und das Ändern eines Pfads verschiebt keine vorhandenen Daten. |

## Werte und Hilfe {#values}

Jede Zeile hat ein Label, eine stets sichtbare Beschreibung sowie die Angaben **Aktiver Wert** und **ADORE-Standard**. Die Beschreibung sagt, was die Einstellung steuert, welche Einheit oder welche Werte erlaubt sind und was eine Änderung bewirkt, oder dass sie reserviert und unbenutzt ist. Es gibt keine separate Hilfeschaltfläche.

Ein Badge **Standard** bedeutet, dass die `config.toml` des Projekts den Wert nicht setzt, sodass der ADORE-Standard gilt. Beim Bearbeiten wird ein Wert nur für dieses Projekt geschrieben. Eine Zeile mit **Hier nicht änderbar** wird in der `config.toml` auf dem Server geändert. Eine Zeile mit **Nur bei pausierter Aufnahme ohne aktive Aufträge anwendbar** braucht die unten beschriebene zusätzliche Bedingung.

## Bearbeiten {#editing}

1. Wählen Sie **Bearbeiten** neben dem Aktiven Wert, geben Sie den neuen Wert ein und wählen Sie **Kandidat vorbereiten**. Das schreibt nur einen ausstehenden Kandidaten; die aktive Konfiguration bleibt unverändert.
2. Das Feld **Ausstehende Konfiguration** erscheint über den Gruppen und listet nur die geänderten Werte. Ein Kandidat, der nichts ändert, kann nicht angewendet werden. Öffnen Sie **Technische Details** für den vollständigen Vergleich, die Wirkung, den Zeitpunkt der Vorbereitung, beide Revisionen und **Bereinigte Prüfung kopieren**. Werte von Zugangsdaten sind geschwärzt.
3. Wählen Sie **Anwenden**, um die Änderung zu senden, oder **Änderung verwerfen**, um nur den Kandidaten zu entfernen.

Es gelten diese Regeln:

- Eine Einstellung nach der anderen: Die anderen Schaltflächen Bearbeiten bleiben deaktiviert, bis der Kandidat angewendet oder verworfen wurde.
- Die Prüfung ist an Revisionen gebunden. Anwenden sendet die geprüfte Basis- und Kandidatenrevision; hat sich die aktive Datei inzwischen geändert, müssen Sie verwerfen, aktualisieren und erneut vorbereiten. Zwei Administratoren, die gleichzeitig bearbeiten, erhalten einen Konflikt, statt sich gegenseitig zu überschreiben. Änderungen direkt an der Datei auf dem Server umgehen diesen Schutz.
- Der Server prüft beim Anwenden erneut, dass kein Auftrag aktiv und kein Vorgang unvollständig ist. Ein blockiertes Anwenden behält den Kandidaten und erklärt, wie Sie fortfahren können.
- Einstellungen, die Identität oder Laufzeit ändern, brauchen zusätzlich eine pausierte Überwachung. Wählen Sie auf der Zusammenfassung **Überwachung pausieren** und lassen Sie aktive Arbeit abschließen; das Pausieren unterbricht keinen laufenden Auftrag.
- Neue Werte gelten für spätere Aufträge. Bestehende Aufträge behalten ihre Konfiguration.

## Original-TOML {#toml}

Neben der Überschrift Projekteinstellungen haben Administratoren **Originalkonfiguration anzeigen** und **Originalkonfiguration herunterladen**. Die Anzeige öffnet einen schließbaren Dialog und hält den Text nur im Speicher. Der Download liefert die gespeicherte `config.toml` genau wie abgelegt, mit Kommentaren, Formatierung und eventuell eingebetteten Geheimnissen, behandeln Sie sie also als Geheimnis. Keine der beiden Funktionen enthält einen ausstehenden Kandidaten, aufgelöste Standardwerte, separate `.env`-Dateien oder externe Zugangsdaten. Entwickler können sie nicht nutzen. Eine heruntergeladene Datei lässt sich mit [Projektkonfiguration importieren](/help/projects#import-project) erneut registrieren, sobald ihre Geheimnisse durch Umgebungsreferenzen ersetzt sind.
