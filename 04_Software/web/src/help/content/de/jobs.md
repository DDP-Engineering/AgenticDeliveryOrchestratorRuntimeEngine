# Lebenszyklus eines Auftrags

Ein Auftrag ist die Arbeit, die ADORE für ein Ticket leistet, von der Aufnahme bis zur zusammengeführten Änderung. Dieser Artikel zeigt seine Phasen und wo Sie mitwirken. Labels und Eignung stehen unter [Tickets für die automatische Aufnahme](/help/tickets).

## Phasen {#stages}

ADORE führt die AEGIS-Phasen nacheinander aus, jeden Versuch in einer neuen Executor-Sitzung. Executoren übertragen nie, öffnen keinen MR/PR und führen nie zusammen.

| Phase | Was geschieht |
|---|---|
| Rahmen | Der Umfang wird abgestimmt, und der Executor hält fest, ob der Auftrag den vollen oder den schnellen Pfad nimmt. |
| Spezifikation | Die Anforderung wird geschrieben. |
| Entwurf | Für nicht triviale Arbeit wird eine kurze Entwurfsnotiz geschrieben. |
| Umsetzung | Zuerst kommt ein fehlschlagender Test, dann die Implementierung, bis die Tests bestehen. |
| Validierung | Review, die vollständige Testsuite und eine strenge Prüfung, die ADORE anschließend selbst wiederholt. |
| Lieferung | Nach Ihrer Freigabe werden Freigabe und Abschluss festgehalten und der MR/PR wird veröffentlicht. |

Der schnelle Pfad durchläuft Rahmen, Umsetzung, Validierung und Lieferung. AEGIS kann zu jeder früheren Phase des gewählten Pfads zurückkehren, auch vom Entwurf zur Spezifikation. ADORE speichert diese Phase und fährt in einer neuen Sitzung innerhalb der bestehenden Grenzen fort. Aufträge zeigt die gespeicherte Phase. Abgeschlossene Aufgaben bleiben endgültig. Eine Phase erhält standardmäßig drei Fehlversuche (**Erlaubte Fehlversuche pro Phase**).

## Klärung {#clarification}

Braucht der Executor Informationen, postet ADORE einen Ticketkommentar, Klärung erforderlich für die Phase, der die Fragen auflistet, und setzt `agent-clarify`. Der Auftrag zeigt **Wartet auf Klärung**, und seine Details bieten **Im Ticket antworten**.

Antworten Sie mit einem normalen Kommentar am Ticket und setzen Sie dann `agent-answered`. Beides ist nötig; Kommentare von ADORE selbst zählen nicht. ADORE entfernt beide Labels und setzt die Arbeit fort. Fragen zählen nicht als Fehlversuche. **Maximale Rückfragerunden** (standardmäßig 3) begrenzt, wie oft ein Auftrag fragen darf, und **Wartezeit auf eine menschliche Antwort** (standardmäßig 72 Stunden) lässt den Auftrag bei Ablauf fehlschlagen.

## Freigabe {#approval}

Besteht die strenge Validierung, entfernt ADORE `agent-approved`, postet die Nachweise am Ticket und wartet. Der Auftrag zeigt **Wartet auf Freigabe**, und das Ticket behält `agent-working`. Die Nachweise nennen den genauen Kandidaten und alle Abweichungen, die der Executor festgehalten hat.

Prüfen Sie ihn und setzen Sie dann `agent-approved` erneut; nur ein frisches Setzen zählt. Die Freigabe ist an diesen Kandidaten und den Commit des Zielbranches gebunden. Ändert sich eines von beiden, ist die Freigabe ungültig, und ADORE integriert, validiert und fragt erneut. Dieses Warten hat keinen Timer. Die Auftragsdetails bieten **Kandidat auf der Forge prüfen**.

## Veröffentlichung und Prüfung {#review}

Nach der Freigabe überträgt ADORE den Branch und öffnet den MR/PR gegen den Zielbranch, fordert bei den Konten unter **Review anfordern von** ein Review an und setzt `agent-mr`. **PR/MR-Status bei Veröffentlichung** wählt Entwurf (Standard) oder Bereit zur Prüfung. Der Auftrag zeigt **Veröffentlichung** und dann **Menschliche Prüfung**. ADORE führt nie zusammen. Nachdem ein Mensch zusammengeführt hat, setzt ADORE `agent-done`, der Auftrag zeigt **Abgeschlossen**, und standardmäßig wird der Remote-Branch entfernt. Ein ohne Merge geschlossener MR/PR lässt den Auftrag fehlschlagen.

Um Änderungen anzufordern, setzt ein Reviewer `agent-revise` am MR/PR. ADORE entfernt das Label, startet eine neue Aufgabe auf demselben Branch und wiederholt Validierung und frische Freigabe, bevor es überträgt. **Maximale Überarbeitungsrunden** (standardmäßig 5) begrenzt das. Eine Anfrage über das Limit hinaus lässt den Auftrag fehlschlagen.

Schlagen CI-Prüfungen am MR/PR fehl, entscheidet **Aktion bei fehlgeschlagenen PR/MR-CI-Prüfungen**: Automatisch reparieren (Standard) startet eine Überarbeitung, Nur benachrichtigen postet einen Kommentar, und Ignorieren überspringt den CI-Status. Automatische Reparaturen teilen sich das Überarbeitungsbudget; ist es aufgebraucht, postet ADORE einen Hinweis, und der Auftrag bleibt in der Prüfung.

## Fehler und Wiederherstellung {#failures}

Schlägt eine Phase fehl, hält ADORE einen Störungskommentar am Ticket aktuell, mit Phase, Versuch, Fehlercode, Nachweisen und nächster Aktion. Nach dem letzten Versuch postet es einen abschließenden Kommentar, setzt `agent-failed`, stoppt den Container, behält den Worktree und gibt den Platz frei. Weitere Ursachen sind eine abgelaufene Antwortzeit, ein gelöschtes Quellticket und ein überschrittenes Limit wie Kosten oder geänderte Dateien. Das Schließen des Quelltickets, während ein Auftrag wartet, bricht ihn ab.

Unter Aufträge zeigt ein fehlgeschlagener Auftrag **Fehlgeschlagen**, und seine Details erklären, dass Wiederherstellungsnachweise erhalten bleiben. **Wiederholen** bittet den Worker, den Auftrag wiederherzustellen; es umgeht weder Validierung noch Freigabe. In der Ticketansicht ersetzt Wiederholen das Starten. Das Entfernen von `agent-failed` löst keine Wiederholung aus. **Abbrechen** erscheint bei unbeendeten Aufträgen und bittet den Worker, zu stoppen und aufzuräumen. Beendete Aufträge können nicht abgebrochen werden. Administratoren und zugewiesene Entwickler können beides nutzen. Ein eingereihter Befehl zeigt seinen Fortschritt, etwa Befehl eingereiht oder Befehl abgeschlossen.

Bei lokalen Aufträgen prüft **Wiederholen** den installierten Executor erneut und akzeptiert ein aktualisiertes Programm oder eine geänderte geerbte Umgebung auf demselben Computer und Konto. Aufgabe, Worktree, Branch, Verlauf und kumulative Grenzen bleiben erhalten. Die automatische Überwachung tut dies nicht. Geänderte Ausführungseinstellungen oder beschädigte Wiederherstellungsnachweise müssen korrigiert werden. Scheitert der Neustart, zeigt der Vorgang den gespeicherten Grund: fehlendes Programm, ungültige Version, Befehlsfehler oder Zeitüberschreitung. Diese Versionsprüfung sendet keine Modellanfrage; verwenden Sie dafür **KI-Verbindung testen**.

Überschreitet ein Container-Befehl sein Zeitlimit, stoppt ADORE den Container vor dem nächsten Befehl. Der nächste zulässige Versuch startet denselben Container mit installierten Abhängigkeiten und Dateien; der Netzwerkzugriff bleibt unverändert. Lässt sich sicheres Stoppen oder Starten nicht bestätigen, schlägt der Auftrag fehl und bewahrt Nachweise zur Prüfung vor **Wiederholen**. Eine fehlgeschlagene Vorbereitung benötigt weiterhin ihre ausdrückliche Wiederherstellung.

## Aufträge verfolgen {#following-jobs}

Verwenden Sie **Aufträge** in der Seitenleiste oder den Reiter **Aufträge** eines Projekts und dann den Unterreiter **Aufträge**. Die Tabelle hat diese Spalten:

| Spalte | Inhalt |
|---|---|
| Ticket | Nummer und Titel; öffnet die Auftragsdetails. |
| Projekt | Das zugehörige Projekt. |
| Status | Der Zustand, die aktuelle Phase und ein Link zum Ticket oder MR/PR, wenn ein Mensch handeln muss. |
| Letzte Aktivität | Zeitpunkt des letzten gespeicherten Ereignisses. |
| Verbrauch | Vom Auftrag verbrauchte Token. |

Klicken Sie auf eine Spaltenüberschrift, um zu sortieren. **Jobs suchen** findet Titel, Nummern, Projekte, Auftrags-IDs, Status, Phase oder Ergebnis. Der Filter **Status** bietet Aktive Aufträge, Wartend, Menschliche Prüfung und Beendete Jobs. Die Seite aktualisiert sich selbst, solange sie sichtbar ist.

Die Details zeigen **Was gerade geschieht**, **Wer handelt**, **Wo** und **Was folgt**, danach Verbrauch, einen Verlauf (Datum, Ereignis, Phase), Links unter **Nachweise und Artefakte** und **Technische Details**. Der Verlauf listet nur gespeicherte Ereignisse. Alte Aktivität allein belegt nicht, dass die Arbeit gestoppt hat.
