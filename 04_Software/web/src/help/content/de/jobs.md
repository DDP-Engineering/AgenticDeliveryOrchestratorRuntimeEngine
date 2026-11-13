# Lebenszyklus eines Auftrags

Ein Auftrag ist die Arbeit, die ADORE für ein Ticket leistet, von der Aufnahme bis zur zusammengeführten Änderung. Dieser Artikel zeigt seine Phasen und wo Sie mitwirken. Labels und Eignung stehen unter [Tickets für die automatische Aufnahme](/help/tickets).


Bestätigen Sie **Abbrechen**. Die Bereinigung versucht Laufzeit und Arbeitsverzeichnis einschließlich unveröffentlichter Arbeit zu entfernen; Ressourcen können bleiben. Status und Nachweise bleiben. Löschen ist eine separate Aktion.

Öffnen Sie **Jobaktionen** neben der aktuellen Phase für **Wiederholen**, **Abbrechen** oder den bestätigten Neustart, soweit verfügbar. Nur für diesen Job zulässige Befehle werden angezeigt.

## Phasen {#stages}

ADORE führt die AEGIS-Phasen nacheinander aus, jeden Versuch in einer neuen Executor-Sitzung. Executoren übertragen nie, öffnen keinen MR/PR und führen nie zusammen.

| Phase | Was geschieht |
|---|---|
| Rahmen | Der Umfang wird abgestimmt, und der Executor hält fest, ob der Auftrag den vollen oder den schnellen Pfad nimmt. |
| Spezifikation | Die Anforderung wird geschrieben. |
| Entwurf | Für nicht triviale Arbeit wird eine kurze Entwurfsnotiz geschrieben. |
| Umsetzung | Der Agent implementiert das Ticket und wählt passende Prüfungen gemäß den Repository-Anweisungen. |
| Validierung | Der Agent meldet Prüfungen gemäß den Repository-Anweisungen, einschließlich nur in CI ausführbarer Prüfungen, und schließt die AEGIS-Aufgabe. ADORE beobachtet den Abschluss ohne erneute Tests. |

Der schnelle Pfad durchläuft Rahmen, Umsetzung und Validierung. Nach der Validierung zeigt der Auftrag die Phase **Fertig**, während er auf Freigabe wartet, veröffentlicht wird und in menschlicher Prüfung ist. AEGIS kann zu jeder früheren Phase des gewählten Pfads zurückkehren, auch vom Entwurf zur Spezifikation. ADORE speichert die Phase und fährt in einer neuen Sitzung innerhalb der bestehenden Grenzen fort. Eine fertige Aufgabe kehrt zur erneuten Prüfung zur Validierung zurück. Eine Phase erhält standardmäßig drei Fehlversuche (**Erlaubte Fehlversuche je Phase**).

Historische Aufträge ohne gespeicherten Workflow bleiben lesbar, wenn ihre AEGIS-Aufgaben oder Phasen ihn erkennen lassen. Das Lesen bewahrt Verlauf und Statusdateien; mehrdeutige oder beschädigte Daten erfordern weiterhin die Prüfung durch den Betreiber.

## Direkte Jobs {#direct-evidence}

Liste und Jobseite zeigen **Workflow**: **AEGIS** oder **Direkt**, wie für den Job gespeichert. Ein direkter Job verwendet **Implementierung** (`build`), **Validierung** (`validate`), dann **Fertig**. Er hat weder Rahmen, Spezifikation, Entwurf noch eine AEGIS-Aufgabe. Der Verlauf zeigt nur gespeicherte Ereignisse, keine angenommenen abgeschlossenen Schritte.

**Letzter gespeicherter Versuch** zeigt den letzten gespeicherten Agentenstart. Andernfalls erscheint **Versuch nicht verfügbar**. Tests und Prüfungen meldet der Agent; ADORE führt sie nicht zusätzlich aus.

Direkte **Implementierung** nutzt `build` aus `workflow.stage_timeout_overrides`, sonst `budgets.per_gate_timeout_seconds`. **Validierung** (`validate`) speichert den Kandidaten zur Freigabe ohne separaten Testbefehl.

## Klärung {#clarification}

Braucht der Executor Informationen, postet ADORE einen Ticketkommentar, Klärung erforderlich für die Phase, der die Fragen auflistet, und setzt `agent-clarify`. Der Auftrag zeigt **Wartet auf Klärung**, und seine Details bieten **Im Ticket antworten**. Wählen Sie **Frage lesen**, um **Frage des Agenten** zu öffnen, dann **Im Ticket antworten**, wenn ein gespeicherter Ort vorliegt.

Antworten Sie mit einem normalen Kommentar am Ticket und setzen Sie dann `agent-answered`. Beides ist nötig; Kommentare von ADORE selbst zählen nicht. ADORE entfernt beide Labels und setzt die Arbeit fort. Fragen zählen nicht als Fehlversuche. **Maximale Rückfragerunden** (standardmäßig 3) begrenzt, wie oft ein Auftrag fragen darf, und **Wartezeit auf eine menschliche Antwort** (standardmäßig 72 Stunden) lässt den Auftrag bei Ablauf fehlschlagen.

## Freigabe {#approval}

Die menschliche Freigabe vor Veröffentlichung ist standardmäßig aktiv. Administratoren können **Menschliche Freigabe vor PR/MR verlangen** in Einstellungen ändern. Ohne diese Freigabe prüft ADORE vor Veröffentlichung Kandidat und Ziel auf Aktualität; Repository-Tests bleiben Aufgabe des Agenten.

Wenn der Agent seinen Workflow beendet, speichert ADORE den Kandidaten, entfernt das alte Freigabelabel und fordert eine neue menschliche Freigabe an. Prüfungen im Journal wurden vom Agenten gemeldet.

Prüfen Sie ihn und setzen Sie dann `agent-approved` erneut; nur ein frisches Setzen zählt. Die Freigabe ist an diesen Kandidaten und den Commit des Zielbranches gebunden. Ändert sich eines von beiden, ist die Freigabe ungültig, und ADORE integriert, validiert und fragt erneut. Dieses Warten hat keinen Timer. Die Auftragsdetails bieten **Kandidat auf der Forge prüfen**.

Ist die Option deaktiviert, prüft ADORE den validierten Kandidaten und das Ziel und veröffentlicht ohne Label. ADORE führt nie zusammen.

## Veröffentlichung und Prüfung {#review}

Nach Validierung und gegebenenfalls Freigabe überträgt ADORE den Branch und öffnet den MR/PR gegen den Zielbranch, fordert bei den Konten unter **Review anfordern von** ein Review an und setzt `agent-mr`. **PR/MR-Status bei Veröffentlichung** wählt Entwurf (Standard) oder Bereit zur Prüfung. Der Auftrag zeigt **Veröffentlichung** und dann **Menschliche Prüfung**. ADORE führt nie zusammen. Nachdem ein Mensch zusammengeführt hat, setzt ADORE `agent-done`, der Auftrag zeigt **Abgeschlossen**, und standardmäßig wird der Remote-Branch entfernt. Ein ohne Merge geschlossener MR/PR lässt den Auftrag fehlschlagen.

Um Änderungen anzufordern, setzt ein Reviewer `agent-revise` am MR/PR. ADORE entfernt das Label, startet neue Arbeit auf demselben Branch (eine neue Aufgabe bei AEGIS) und wiederholt Validierung und frische Freigabe, bevor es überträgt. **Maximale Überarbeitungsrunden** (standardmäßig 5) begrenzt das. Eine Anfrage über das Limit hinaus lässt den Auftrag fehlschlagen.

Schlagen CI-Prüfungen am MR/PR fehl, entscheidet **Aktion bei fehlgeschlagenen PR/MR-CI-Prüfungen**: Automatisch reparieren (Standard) startet eine Überarbeitung, Nur benachrichtigen postet einen Kommentar, und Ignorieren überspringt den CI-Status. Automatische Reparaturen teilen sich das Überarbeitungsbudget; ist es aufgebraucht, postet ADORE einen Hinweis, und der Auftrag bleibt in der Prüfung.

## Fehler und Wiederherstellung {#failures}

Schlägt eine Phase fehl, hält ADORE einen Störungskommentar am Ticket aktuell, mit Phase, Versuch, Fehlercode, Nachweisen und nächster Aktion; hat der Agent beendet, ohne die Phase voranzubringen, zeigen die Nachweise auch seine letzten Fehlerausgabezeilen. Nach dem letzten Versuch postet es einen abschließenden Kommentar, setzt `agent-failed`, stoppt den Container, behält den Worktree und gibt den Platz frei. Weitere Ursachen sind eine abgelaufene Antwortzeit, ein gelöschtes Quellticket und ein überschrittenes Limit wie Kosten oder geänderte Dateien. Das Schließen des Quelltickets, während ein Auftrag wartet, bricht ihn ab.

Unter Aufträge zeigt ein fehlgeschlagener Auftrag **Fehlgeschlagen**, und seine Details erklären, dass Wiederherstellungsnachweise erhalten bleiben. **Wiederholen** bittet den Worker, den Auftrag wiederherzustellen; es umgeht weder Validierung noch erforderliche Freigabe. In der Ticketansicht ersetzt Wiederholen das Starten. Das Entfernen von `agent-failed` löst keine Wiederholung aus. **Abbrechen** erscheint bei unbeendeten Aufträgen und bittet den Worker, zu stoppen und aufzuräumen. Beendete Aufträge können nicht abgebrochen werden. Administratoren und zugewiesene Entwickler können beides nutzen. Ein eingereihter Befehl zeigt seinen Fortschritt, etwa Befehl eingereiht oder Befehl abgeschlossen. Ein fehlgeschlagener oder ungewisser Befehl nennt außerdem den Grund, wenn die Engine einen angibt, und zeigt die letzten Zeilen der Engine.

Bei lokalen Aufträgen prüft **Wiederholen** den installierten Executor erneut und akzeptiert ein aktualisiertes Programm oder eine geänderte geerbte Umgebung auf demselben Computer und Konto. Aufgabe, Worktree, Branch, Verlauf und kumulative Grenzen bleiben erhalten. Die automatische Überwachung tut dies nicht. Geänderte Ausführungseinstellungen oder beschädigte Wiederherstellungsnachweise müssen korrigiert werden. Scheitert der Neustart, zeigt der Vorgang den gespeicherten Grund: fehlendes Programm, ungültige Version, Befehlsfehler oder Zeitüberschreitung. Diese Versionsprüfung sendet keine Modellanfrage; verwenden Sie dafür **KI-Verbindung testen**.

Überschreitet ein Container-Befehl sein Zeitlimit, stoppt ADORE den Container vor dem nächsten Befehl. Der nächste zulässige Versuch startet denselben Container mit installierten Abhängigkeiten und Dateien; der Netzwerkzugriff bleibt unverändert. Lässt sich sicheres Stoppen oder Starten nicht bestätigen, schlägt der Auftrag fehl und bewahrt Nachweise zur Prüfung vor **Wiederholen**. Eine fehlgeschlagene Vorbereitung benötigt weiterhin ihre ausdrückliche Wiederherstellung.

## Verwerfen und neu starten {#restart}

Bei einem fehlgeschlagenen Auftrag löscht **Verwerfen und neu starten** den gespeicherten Zustand, die Arbeitskopie samt unveröffentlichter Arbeit und den unveränderten eigenen Remote-Branch. Lesen und bestätigen Sie die Warnung. ADORE prüft die Eigentümerschaft vor der Bereinigung und startet dasselbe offene Ticket mit aktuellen Einstellungen erst nach erfolgreicher Bereinigung. Eine pausierte Überwachung bleibt pausiert. Administratoren und zugewiesene Entwickler dürfen diese Aktion nutzen.

Wiederholen behebt keine geänderte Ausführungsart oder feste Einstellungen; die Jobdetails erklären dies und bieten die bestätigte Aktion an. Stellen Sie gespeicherte Einstellungen wieder her, um Arbeit zu behalten. Wiederholen kann veränderliche native Umgebungswerte weiterhin neu prüfen, auch Prozessorvariablen nach einer VM-Größenänderung.

Fremde Ressourcen, andere Rechner oder Konten, beschädigte Eigentumsnachweise und geänderte Remote-Branches blockieren die Wiederherstellung. Eine Teilbereinigung behält restliche Nachweise ohne neuen Auftrag. Bei Änderungen nach der Bestätigung aktualisieren und prüfen Sie die Details erneut. Eine CLI-Sperre kann dem Web-Worker gehören: Überwachung in der Projektübersicht pausieren und das Ende des begrenzten Auftrags abwarten. Keine aktive Sperrdatei löschen.

Hat ein früher gelöschter Auftrag einen Branch ohne gespeicherten Checkpoint hinterlassen, behält ADORE ihn und nutzt eine neue Generation. Ein geänderter bekannter Checkpoint blockiert weiterhin die Wiederherstellung. Höchstens drei alternative Namen werden geprüft; die Repository-Regeln müssen einen freien Namen erlauben. Andernfalls stoppt die Wiederherstellung vor der Bereinigung. Das Ergebnis nennt einen behaltenen alten Branch.

## Aufträge verfolgen {#following-jobs}

Verwenden Sie **Aufträge** in der Seitenleiste oder den Reiter **Aufträge** eines Projekts und dann den Unterreiter **Aufträge**. Die Tabelle hat diese Spalten:

| Spalte | Inhalt |
|---|---|
| Ticket | Nummer und Titel; öffnet die Auftragsdetails. |
| Projekt | Das zugehörige Projekt. |
| Status | Der Zustand, der gespeicherte Workflow, die aktuelle Phase und ein Link zum Ticket oder MR/PR, wenn ein Mensch handeln muss. |
| Letzte Aktivität | Zeitpunkt des letzten gespeicherten Ereignisses. |
| Verbrauch | Vom Auftrag verbrauchte Token. |

Klicken Sie auf eine Spaltenüberschrift, um zu sortieren. **Jobs suchen** findet Titel, Nummern, Projekte, Auftrags-IDs, Status, Phase oder Ergebnis. Der Filter **Status** bietet Aktive Aufträge, Wartend, Menschliche Prüfung und Beendete Jobs. Die Seite aktualisiert sich selbst, solange sie sichtbar ist.

Die Details ersetzen die Jobliste, solange sie geöffnet sind. Die kompakte Überschrift vereint Ticketnummer und Titel. **Was gerade geschieht** zeigt Status, Zuständigkeit und **Nächster Schritt**. Budgets und Verbrauch stehen auf breiten Bildschirmen daneben, auf schmalen darunter. **Aktivität** listet gespeicherte Ereignisse vom neuesten zum ältesten. **Frage des Agenten** enthält die aktive Rückfrage; andere Zustände zeigen **Nachweise und Artefakte**. **Technische Details** enthält Kennungen, Executor-Ausgabe und aufklappbare **Gespeicherte Originalereignisse**. **Schließen** kehrt zur Liste mit ihren Filtern zurück. Frühere Ereignisse werden nicht zu aktuellen Handlungsaufforderungen.

## Jobbudgets {#budgets}

Jobdetails zeigen **Executorstarts** (zum Beispiel 9 / 20) und **Aktive Arbeit (Sekunden)** neben den aktuellen Projektgrenzen, unabhängig von Tokenstatistiken. Ab 90 % erscheint ein Hinweis; bei Erreichen soll die Grenze vor dem Fortsetzen erhöht werden. Die Startvorgabe ist 20 bei Registrierung und `adore init`.

Administratoren können **Budgets in den Projekteinstellungen anpassen** wählen, **Implementierung** öffnen, nur Budgets ändern, **Speichern** wählen und die genauen Werte bestätigen. Solche geprüften Budgetänderungen sind bei wartenden Rückfragen erlaubt, ohne aktiven Conductor oder unfertigen Vorgang. Andere Einstellungen behalten die üblichen Ruhe- und Pausenprüfungen; Entwickler haben Lesezugriff.

Budgets werden vor jedem Versuch, Fortsetzen und Wiederholen neu gelesen. Ein laufender Versuch behält sein Zeitlimit. Aktive Arbeit wird über Wiederholungen, Rückfrageantworten und Überarbeitungen summiert; Wartezeit zählt nicht. Eine Erhöhung erhält Verbrauch, Aufgabe und Fortschritt. Ein wegen Budgetüberschreitung fehlgeschlagener Job braucht danach weiterhin **Wiederholen**. Ungültige oder fehlende Konfiguration sperrt weitere Versuche bis zur Korrektur.

Sind aktuelle Grenzen nicht lesbar, bleiben Verbrauch, Nachweise und Wiederherstellung sichtbar. Grenzen zeigen — mit einem ausdrücklichen Hinweis; Standardwerte werden nicht angenommen. Vor erneutem Ausführen die Projektkonfiguration korrigieren.

## Status und Executor-Nachweise {#operational-evidence}

**In Arbeit** bedeutet, dass ADORE die gespeicherte Phase steuert; derzeit ist keine menschliche Aktion angefordert. **Klärung ausstehend** benötigt eine Antwort im Ticket. **Fehlgeschlagen** hält autonome Arbeit an und bewahrt Wiederherstellungsnachweise. Die Statuskarte zeigt Fehlversuche der aktuellen Phase auch bei laufendem Job.

Fragen erscheinen unter **Frage des Agenten** als Markdown mit Listen, Tabellen und Code. Führende HTML-Kommentare fehlen in der lesbaren Ansicht; **Originalfrage und Nachweise** bewahrt die genaue Quelle. Sonstiges HTML bleibt Text, unsichere Links bleiben inaktiv und Bilder laden nicht automatisch. Breite Tabellen und Code scrollen innerhalb der Frage.

Zeitleistenphasen stammen aus der gespeicherten Phase, dem Phasenkontext oder dem Übergangsziel des Ereignisses; andere Ereignisse bleiben unbekannt. Jobzeiten enthalten Sekunden. Ein Ereignis ist ein gespeicherter Nachweis, kein Live-Fortschritt.

Unter **Technische Details** wählen Sie **Letzte Executor-Ausgabe anzeigen**. Operative Ausgaben des letzten abgeschlossenen Starts werden vom Host erfasst, einschließlich fehlender Module und Testsummen. Prompts, Gedankengänge, Skripte, Konfiguration, Pfade, Zugangsdaten und Finanzdaten bleiben verborgen. Unbekannte Ausgaben werden durch einen Hinweis oder eine Diagnosekategorie ersetzt. Höchstens die letzten 500 Diagnoseeinträge je Stream innerhalb von 64 KiB bleiben erhalten.

Die Zusammenfassung zeigt Versuch, Aufzeichnungszeit, Ergebnis und Exitcode. Klappen Sie **stdout** oder **stderr** bei vorhandenen Einträgen auf. Einen laufenden Start zeigt die Ansicht zusammen mit der letzten abgeschlossenen Ausgabe. Ändert sich das Journal beim Lesen, wählen Sie **Wiederholen**. Der letzte geprüfte Stand ist als möglicherweise veraltet gekennzeichnet.

Ein Start ohne belegte Erfassung oder mit gelöschtem Snapshot ist ausdrücklich nicht verfügbar; rohe Archive werden nie ersatzweise gelesen. Beschädigte Nachweise werden abgelehnt. Bestehende Jobs können bis zu einem späteren Start ohne Ausgabe bleiben; diese Ansicht startet nichts.

Wenn **Verbrauch** nicht lädt, nutzen Sie **Verbrauch aktualisieren** neben dem Fehler. Jobnachweise und Wiederherstellung bleiben getrennt. Beschädigte Quellen erfordern weiterhin eine Untersuchung durch den Betreiber.
