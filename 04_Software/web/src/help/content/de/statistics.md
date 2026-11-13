# Statistiken und Kosten

Statistiken zeigt, wie viel Arbeit ADORE geleistet hat, was dabei verbraucht wurde und wie gut die Ergebnisse Bestand hatten. Kosten sehen nur Administratoren, und geschätzte Kosten sind keine Rechnungen.

## Berichtszeitraum und Export {#period}

Öffnen Sie **Statistiken** in der Seitenleiste, um alle Projekte zu sehen, auf die Sie Zugriff haben, oder den Reiter **Statistiken** eines Projekts, um nur dieses Projekt zu sehen. Beide verwenden dasselbe Layout: eine Zeile **Berichtszeitraum** über vier Reitern.

| Bedienelement | Funktion |
|---|---|
| Projekt | Nur auf der Seite Statistiken. Administratoren beginnen mit **Alle Projekte**; ein Dev wählt unter den zugewiesenen Projekten. Der Projektreiter hat keine Auswahl. |
| Ab und Bis | Der erste und der letzte einzubeziehende Tag. **Bis** schließt diesen ganzen Tag ein. |
| Gruppieren nach | Gruppen nach **Tag**, **Woche** oder **Monat**, verwendet vom Reiter Trends und von den Exporten. |
| Gesamter Zeitraum | Leert beide Daten. Zwei leere Datumsfelder bedeuten ebenfalls den gesamten Zeitraum. |
| CSV exportieren | Öffnet ein Menü mit Downloads für das aktuelle Projekt, die Daten und die Gruppierung. |

Daten und Gruppen verwenden UTC, sofern die Seitenadresse keine andere Zeitzone enthält. Die Daten gelten für jeden Reiter und jeden Export. Ein Bericht für andere Tage wird abgelehnt, selbst wenn beide Quellen übereinstimmen; Zeitumstellungen und ein leeres Datumsfeld bleiben unterstützt. Fehlende erforderliche Jobsummen zeigen einen Fehler und **Wiederholen**, nicht null oder einen leeren Bericht. Ein Wechsel des Projekts behält den Zeitraum und den aktuellen Reiter bei.

Das Menü **CSV exportieren** bietet **Projektkennzahlen**, **Projektnutzung** und **Jobverbrauch** für ein Projekt oder **Kennzahlen aller Projekte**, **Nutzung aller Projekte** und **Jobverbrauch** für **Alle Projekte**. Es erscheint, sobald die Daten geladen sind. Hintergrundabfragen lassen Bericht, offenes Menü und Tabellensteuerung sichtbar, bis ein vollständig geprüfter Ersatz bereitsteht.

**Aktualisieren** liest Kennzahlen und Nutzung, ohne die Ansicht zurückzusetzen. **Zuletzt aktualisiert** zeigt die letzte vollständige erfolgreiche Abfrage; **Kennzahlen aktualisiert** und **Nutzung aktualisiert** zeigen die Zeit jeder Quelle. Kennzahlen des gewählten Projekts werden alle 15 Sekunden gelesen, Nutzung und globale Kennzahlen alle 30 Sekunden bei sichtbarem Tab.

Nach einem Verbindungsfehler oder einer abgelaufenen Lesefrist kann der letzte geprüfte Bericht mit Fehlerhinweis, ursprünglichen Zeiten und **Wiederholen** sichtbar bleiben. Er ist kein aktueller Nachweis. Eine erfolgreiche manuelle oder automatische Abfrage entfernt den Hinweis. CSV-Downloads lesen aktuelle Serverdaten, nicht unbedingt diesen behaltenen Bericht. Erstabfragen, ungültige, nicht autorisierte oder andere fehlgeschlagene Abfragen zeigen **Daten konnten nicht geladen werden** ohne Summen und Exporte.

Ein Strich bedeutet, dass der Wert unbekannt ist. Unter einem Wert bedeutet **Gemessene Null**, dass ADORE null beobachtet hat, **Nicht verfügbar**, dass nichts aufgezeichnet wurde, und **Teilweise · bekannte Teilsumme**, dass die Zahl nur die Nutzung umfasst, die Token gemeldet hat.

Projektübergreifende Anzahlen und Zeitsummen müssen exakt sein; eine zu große Summe zeigt einen Fehler und **Wiederholen**, keine gerundete aktuelle Zahl. Fehlt bei einem Projekt die erfasste Anzahl für **Nutzung ohne Preis**, bleibt die Gesamtanzahl unbekannt, auch wenn ein anderes Projekt null oder eine positive Zahl meldet. Bekannte Anzahlen je Projekt bleiben sichtbar.

## Die vier Reiter {#tabs}

### Übersicht {#tab-summary}

Karten für **Gestartete Jobs**, **Abgeschlossene Jobs**, **Fehlgeschlagene Jobs**, **Eingabe-Token**, **Ausgabe-Token** und **Bekannte Token insgesamt**. Abgeschlossen zählt jeden beendeten Auftrag unabhängig vom Ergebnis. Die Summe setzt voraus, dass beide Token-Richtungen bekannt sind. Administratoren sehen außerdem die Karten **Gemeldete Kosten** und **Geschätzte Kosten**. Bei **Alle Projekte** listet eine Tabelle **Projektvergleich** gestartete, abgeschlossene und fehlgeschlagene Aufträge sowie die durchschnittliche Dauer je Projekt, mit dem Repository unter dem Projektnamen.

### Nutzung {#tab-usage}

**Nutzung nach Executor und Modell** beginnt mit kompakten Summen: Nutzungsereignisse, Eingabe- und Ausgabe-Token, Cache gelesen und Cache geschrieben sowie die Auftragsdauer (**Gemessene Aufträge**, **Durchschnittliche Dauer**, **Median der Dauer**). Die Tabelle darunter listet die Nutzung nach Datum, Executor und Modell; klicken Sie auf eine Spaltenüberschrift, um zu sortieren. Bei **Alle Projekte** folgt eine Tabelle je Projekt. Administratoren sehen außerdem Kostenspalten.

### Qualität {#tab-quality}

**Lieferqualität** zeigt **Überarbeitungen nach Review**, **Validierung im ersten Versuch**, **Merge ohne Review-Überarbeitung**, **Reviews noch offen**, **Phasenfehler** und **Manuelle Wiederholungen**. Jede Rate zeigt Zähler und Nenner. **Reviews noch offen** ist der aktuelle Stand und ignoriert den Zeitraum. Darunter stehen **MR/PR-Revisionen nach Prüfung** und **Pipeline-Reparaturen** mit einer Tagestabelle der aktiven Tage. Bei **Alle Projekte** ergänzt eine Tabelle je Projekt die Prüfrunden.

### Trends {#tab-trends}

Die Messabdeckung erscheint als kompakter Wert. Eine Tabelle hat eine Zeile je Gruppe (Tag, Woche oder Monat) mit gestarteten, abgeschlossenen und fehlgeschlagenen Aufträgen als proportionale Balken, dazu Eingabe- und Ausgabe-Token und, für Administratoren, gemeldete und geschätzte Kosten.

Hat der Bereich noch keine Aufträge, sagen Qualität und Trends das und weisen Sie auf Aufträge → Tickets hin, wo Sie einen starten können.

## Gemeldete und geschätzte Kosten {#costs}

Zwei Kostenzahlen werden getrennt geführt, und keine ist eine Rechnung.

- **Gemeldete Kosten** sind das, was der Executor gemeldet hat, übernommen als beobachteter Nachweis. Hat er keine gemeldet, lautet der Wert **Nicht verfügbar**.
- **Geschätzte Kosten** sind die aufgezeichneten Token-Mengen multipliziert mit Preisen, die Administratoren festlegen. Es ist eine Schätzung, keine Rechnung und keine Ausgabengrenze.

Administratoren erfassen Preise im Projekt unter **Einstellungen → Agent und Modell** bei **Schätzpreise**: Wählen Sie **Gültig ab**, geben Sie dann **Eingabe USD / 1 Mio. Token** und **Ausgabe USD / 1 Mio. Token** ein und wählen Sie **Speichern**. Ein Preis gilt für Pi und sein konfiguriertes Modell, legen Sie also zuerst das Modell fest. Jedes Nutzungsereignis wird nach Executor, Modell und dem Tag seines Verbrauchs bepreist. Ereignisse ohne passenden Preis werden in den Nutzungssummen als **Nutzung ohne Preis** gezählt.

> Ein Preis mit früherem Gültigkeitsdatum kann vergangene Schätzungen ändern. Exportieren Sie eine CSV-Datei, wenn Sie eine Zahl zu einem bestimmten Zeitpunkt benötigen.

Auf dem Reiter Qualität sehen Administratoren außerdem **Kosten je belegtem Auftrag**, je abgeschlossenem und je von Menschen zusammengeführtem Auftrag, jeweils mit der Anzahl der zugrunde liegenden Aufträge.

## Wer Geldbeträge sieht {#visibility}

| Rolle | Projekte | Geld |
|---|---|---|
| Administrator | **Alle Projekte** oder jedes einzelne Projekt | Gemeldete Kosten, Geschätzte Kosten, Nutzung ohne Preis, Kosten je Auftrag, Kosten pro Revision, Kostenspalten und die Finanzfelder in CSV-Exporten |
| Dev | Nur zugewiesene Projekte; kein **Alle Projekte** | Keine. Devs sehen Auftragszahlen, Token, Dauer und Qualitätskennzahlen, nie ein Finanzfeld. |

Preise werden nur von Administratoren festgelegt und gesehen; die schreibgeschützten Einstellungen eines Dev enthalten keine Finanzeinstellungen.
