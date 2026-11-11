# Projekteinstellungen

Der Reiter Einstellungen eines Projekts listet die Arbeitsregeln auf, die ADORE dafür anwendet: welche Tickets aufgenommen werden, welche Limits gelten, wie veröffentlicht wird und welcher Agent verwendet wird. Administratoren bearbeiten mehrere Einstellungen und speichern sie gemeinsam; Entwickler lesen sie.

## Wo Sie die Einstellungen finden {#where}

Öffnen Sie [Projekte](/projects), wählen Sie ein Projekt und dann den Reiter **Einstellungen**. Die Reiter sind Zusammenfassung, Einstellungen, Aufträge, Statistiken, Verlauf und, für Administratoren, Zugriff.

Die gespeicherten Einstellungen werden alle 15 Sekunden aktualisiert, solange der Browser-Tab sichtbar ist. Bei ungespeicherten Änderungen sowie beim Speichern oder Verwerfen pausiert die Aktualisierung. Auch bei der Eingabe eines Preises oder API-Schlüssels und bei der ChatGPT-Anmeldung pausiert die Aktualisierung.

Administratoren können bearbeiten. Entwickler mit Zugriff auf das Projekt sehen **Schreibgeschützte Einstellungen**, ohne Schaltflächen zum Bearbeiten und ohne Geheimnisse oder Finanzeinstellungen. Jedes Projekt hat eigene Einstellungen; die globale Kapazität und die Audit-Aufbewahrung gehören zur Verwaltung.

## Einstellungsgruppen {#groups}

Jede Gruppe ist beim Öffnen der Einstellungen eingeklappt, und die Zahl neben ihrem Namen gibt die Anzahl ihrer Zeilen an.

| Gruppe | Was sie steuert |
|---|---|
| Repository | Forge und Repository, Gitea-Login, **Zielbranch** (Basis neuer Aufträge und Ziel der PR/MRs), die Vorlage für den Namen des Auftrags-Branches mit optionaler Namensregel und einem Live-Beispiel sowie Anzeigename, Ressourcenname und Commit-Autor-E-Mail des Agenten. |
| Tickets | **Label für aufnahmebereite Tickets**, **Label zum Ausschluss von der Aufnahme**, die eingeklappten **Statuslabels**, wie oft ADORE die Forge prüft, ob Tickets Akzeptanzkriterien oder ein Prioritätslabel brauchen, und den Standard-Aufgabentyp. Siehe [Tickets für die automatische Aufnahme](/help/tickets#labels). |
| Implementierung | Limits je Auftrag: **Limit aktiver Aufträge**, **Maximale Executor-Starts je Auftrag**, **Zeitlimit für aktive Arbeit (Sekunden)**, **Kostenlimit je Auftrag (USD)**, **Maximale geänderte Dateien je Auftrag** und **Zeitlimit je Phasenversuch (Sekunden)**. Außerdem **Rückfragen**, **Wiederherstellung nach Fehlern**, **Erweiterte Zeitlimits pro Phase**, **Fortschrittscommits veröffentlichen** und das Label für den Schnellpfad. |
| PR/MR und Review | **Review anfordern von**, **PR/MR-Status bei Veröffentlichung** (Entwurf oder Bereit zur Prüfung), das Freigabelabel, **Branch nach menschlichem Merge entfernen**, Überarbeitungsrunden und **Aktion bei fehlgeschlagenen PR/MR-CI-Prüfungen** (Automatisch reparieren, Nur benachrichtigen oder Ignorieren). |
| Statistik | **Messwerte abgeschlossener Aufträge erfassen** und **Vom Agenten gemeldete Token erfassen**. **Statistik-Datenbankdatei** wird nur zur Information angezeigt. |
| Agent und Modell | Anbieter, Modell, Authentifizierung und **KI-Verbindung testen** [Executor und Modelle](/help/executors). |
| Technische Details | Schreibgeschützte Installationswerte wie der Auftragsstatus-Ordner, der lokale Repository-Pfad und die Arbeitsordner der Aufträge. Sie werden in der `config.toml` des Projekts auf dem Server geändert, und das Ändern eines Pfads verschiebt keine vorhandenen Daten. |

## Werte und Hilfe {#values}

Jede Zeile hat ein Label, eine stets sichtbare Beschreibung sowie die Angaben **Aktiver Wert** und **ADORE-Standard**. Die Beschreibung sagt, was die Einstellung steuert, welche Einheit oder welche Werte erlaubt sind und was eine Änderung bewirkt, oder dass sie reserviert und unbenutzt ist. Es gibt keine separate Hilfeschaltfläche.

Ein Badge **Standard** bedeutet, dass die `config.toml` des Projekts den Wert nicht setzt, sodass der ADORE-Standard gilt. Beim Bearbeiten wird ein Wert nur für dieses Projekt geschrieben. Eine Zeile mit **Hier nicht änderbar** wird in der `config.toml` auf dem Server geändert. Eine Zeile mit **Nur bei pausierter Aufnahme ohne aktive Aufträge anwendbar** braucht die unten beschriebene zusätzliche Bedingung.

Wählen Sie **Auf dem Server installiert** für das von ADORE verwaltete Pi unter dem aktuellen Systemkonto. Der optionale **PATH für Projektwerkzeuge** bestimmt die Werkzeugordner. Siehe [Pi auf dem Server installieren](/help/executors#installed-executors).

## Bearbeiten {#editing}

1. Wählen Sie **Bearbeiten** neben jedem zu ändernden Wert. Sie können mehrere Einstellungen in verschiedenen Gruppen bearbeiten.
2. Verwenden Sie die einzige Schaltfläche **Speichern** oberhalb der Gruppen. Sie ist nur bei geänderten Werten und gültigen Eingaben aktiv.
3. Bei wichtigen Änderungen zeigt **Wichtige Änderungen bestätigen** das Projekt, die geänderten Werte und Auswirkungen. Wählen Sie **Änderungen speichern** oder **Weiter bearbeiten**, um ohne Speichern zurückzukehren.

Es gelten folgende Regeln:

- **Änderungen verwerfen** entfernt alle ungespeicherten Eingaben. Das Abbrechen der Bestätigung behält sie ohne einen gespeicherten Kandidaten.
- Speichern ist an die bearbeitete Konfiguration gebunden. Eine veraltete Revision sperrt das Speichern und behält die Eingaben. Verwerfen Sie Ihre Änderungen, um die gespeicherten Einstellungen vor dem Bearbeiten neu zu laden. Gleichzeitige Änderungen führen zu einem Konflikt.
- Der Server prüft die gesamte Konfiguration und speichert alles gemeinsam. Geprüfte reine Budgetänderungen erlauben auch wartende Rückfragen, ohne aktiven Conductor oder unfertigen Vorgang. Andere Einstellungen erfordern beendete Jobs. Ein Fehler behält Eingaben und vorbereitete Kandidaten.
- Identitäts- und Laufzeitänderungen erfordern zusätzlich pausierte Überwachung. Wählen Sie **Überwachung pausieren** in Übersicht und lassen Sie aktive Arbeit enden; die Pause unterbricht keinen Auftrag.
- Budgets gelten vor dem nächsten Versuch oder Fortsetzen bei erhaltenem Verbrauch und Fortschritt. Siehe [Jobbudgets](#budgets).

Beim Navigieren oder Neuladen der Seite erscheint eine Rückfrage, bevor ungespeicherte Einstellungen verworfen werden. Kurze Windows-Dateisperren werden automatisch erneut versucht; bei weiterem Fehler prüfen Sie den Dateizugriff und versuchen erneut **Speichern**.

## Original-TOML {#toml}

Neben Projekteinstellungen stehen Administratoren **Originalkonfiguration anzeigen** und **Originalkonfiguration exportieren** zur Verfügung. Die Vorschau zeigt die exakt gespeicherte TOML in einem schließbaren Dialog. Ausstehende Änderungen, separate Umgebungsdateien, externe Zugangsdaten und laufende Auftragsdaten sind ausgeschlossen. Eine einzelne TOML kann Klartextwerte enthalten und muss vertraulich behandelt werden; der vollständige Build-Export verweigert eingebettete Zugangsdaten.

Wählen Sie **Originalkonfiguration exportieren**, wählen Sie das Ziel und speichern Sie. Container-Projekte exportieren ein ZIP mit gespeicherter Konfiguration und vollständiger Image-Definition. Native Projekte speichern `config.toml`. Es gibt keinen Export-Einstellungsdialog. Ohne Zielauswahl gelten die normalen Download-Einstellungen des Browsers.

Administratoren verwalten Quellen separat unter **Technische Details → Image-Definition**. Wählen Sie eine Dockerfile oder ZIP unter **Definitionsdatei**; sie wird automatisch geprüft. **Rezept speichern** speichert sie, **Definition ändern** ersetzt sie. Fehlende lokale Basisdefinitionen werden ebenfalls hier ergänzt. Die Standard-Executor-Basis von ADORE ist automatisch enthalten.

Definitionen werden je Image gespeichert und von Projekten mit diesem Image geteilt. Das Speichern baut kein Image, ändert keine Einstellungen und startet keine Aufträge neu. Das ZIP enthält alle deklarierten lokalen Basisquellen und eine Compose-Datei zum Bauen auf einem anderen Server. Image-Binärdateien und später vom Agenten installierte Pakete sind ausgeschlossen. Registries und Paketquellen müssen dort erreichbar sein.

Bei beschädigten Rezeptdaten nennt der Dialog, was auf dem Server für einen Neuanfang zu löschen ist. Ein Zurücksetzen des Rezeptkatalogs entfernt gespeicherte Image-Definitionen aller Projekte; Konfigurationen, Zugangsdaten und Aufträge bleiben unverändert. ADORE löscht diese Daten niemals automatisch.

## Systempakete des Agenten {#system-packages}

**Systempaketinstallation durch den Agenten erlauben**

Unter Einstellungen → Agent und Modell aktivieren Administratoren diese Berechtigung mit **Speichern** und bestätigen die Auswirkung. Sie ist standardmäßig aus und für Container-Projekte verfügbar. Zuerst ein kompatibles Image mit sudo erstellen oder wählen, danach einen neuen Auftrag starten. Der Agent führt Paketbefehle direkt aus, prüft Fehler und passt seine Schritte innerhalb der Auftragsgrenzen an.

Netzwerkzugriff bleibt separat: open erlaubt erreichbare Quellen, allowlist-proxy erlaubte HTTP/HTTPS-Domains und none nur verfügbare lokale Quellen. Paketskripte haben administrative Rechte im Container; eingebundene Projektordner bleiben mit dem Server geteilt. Systempakete bleiben beim Fortsetzen desselben Containers erhalten; ein neuer Container erfordert erneute Prüfung und Installation.

## Jobbudgets {#budgets}

Jobdetails zeigen **Executorstarts** (zum Beispiel 9 / 20) und **Aktive Arbeit (Sekunden)** neben den aktuellen Projektgrenzen, unabhängig von Tokenstatistiken. Ab 90 % erscheint ein Hinweis; bei Erreichen soll die Grenze vor dem Fortsetzen erhöht werden. Die Startvorgabe ist 20 bei Registrierung und `adore init`.

Administratoren können **Budgets in den Projekteinstellungen anpassen** wählen, **Implementierung** öffnen, nur Budgets ändern, **Speichern** wählen und die genauen Werte bestätigen. Solche geprüften Budgetänderungen sind bei wartenden Rückfragen erlaubt, ohne aktiven Conductor oder unfertigen Vorgang. Andere Einstellungen behalten die üblichen Ruhe- und Pausenprüfungen; Entwickler haben Lesezugriff.

Budgets werden vor jedem Versuch, Fortsetzen und Wiederholen neu gelesen. Ein laufender Versuch behält sein Zeitlimit. Aktive Arbeit wird über Wiederholungen, Rückfrageantworten und Überarbeitungen summiert; Wartezeit zählt nicht. Eine Erhöhung erhält Verbrauch, Aufgabe und Fortschritt. Ein wegen Budgetüberschreitung fehlgeschlagener Job braucht danach weiterhin **Wiederholen**. Ungültige oder fehlende Konfiguration sperrt weitere Versuche bis zur Korrektur.

Sind aktuelle Grenzen nicht lesbar, bleiben Verbrauch, Nachweise und Wiederherstellung sichtbar. Grenzen zeigen — mit einem ausdrücklichen Hinweis; Standardwerte werden nicht angenommen. Vor erneutem Ausführen die Projektkonfiguration korrigieren.
