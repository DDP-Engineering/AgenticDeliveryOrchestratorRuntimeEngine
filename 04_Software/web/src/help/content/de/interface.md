# Rundgang durch die Oberfläche

Die Oberfläche hat eine dunkle Seitenleiste zum Wechseln zwischen den Seiten und eine obere Leiste, die die aktuelle Seite nennt und häufige Aktionen anbietet. Diese Seite beschreibt die Seiten, die Schaltflächen in der Kopfzeile, die Projektzentrale und die Statuslabels.

## Navigation {#navigation}

| Seite | Was Sie dort tun |
|---|---|
| Übersicht | **Handlungsbedarf** und **Aktive Aufträge** für die Projekte sehen, auf die Sie Zugriff haben. **Details** öffnet einen Auftrag unter Aufträge. |
| [Projekte](/projects) | Eingerichtete Projekte mit Repository, Forge, Überwachungsstatus, Anzahl der Aufträge und letzter Aktivität durchsuchen. Ein Projekt öffnen, um seine Zentrale zu erreichen. Administratoren sehen außerdem **Neues Projekt registrieren** oder **Originalkonfiguration importieren**. |
| [Aufträge](/jobs) | Einen **Jobbereich** wählen und dann im Unterreiter **Tickets** Forge-Tickets lesen und starten oder im Unterreiter **Aufträge** Aufträge suchen und ihre Details öffnen. |
| [Statistiken](/metrics) | Nutzung, Qualität und Trends für einen Berichtszeitraum lesen. Siehe [Statistiken und Kosten](/help/statistics). |
| Verwaltung | Nur für Administratoren. Sie öffnet drei Seiten: [Systemstatus](/admin/status), [Benutzer](/admin/users) und [Änderungsverlauf](/admin/audit). Siehe [Verwaltung](/help/administration). |
| [Mein Konto](/account) | Sprache und Design wählen und das Passwort ändern. |

Die Seitenleiste zeigt außerdem Ihren Namen und Ihre Rolle sowie **Abmelden**. Auf einem schmalen Bildschirm öffnet **Menü** die Navigation, und die Auswahl einer Seite schließt sie wieder.

Ein Dev sieht nur die Projekte, die ein Administrator zugewiesen hat, und hat keinen Eintrag Verwaltung. Jede Seite hat eine eigene Adresse, daher behalten Lesezeichen, Zurück, Vorwärts und Neuladen Ihre Position bei.

## Kopfzeile {#header}

Die obere Leiste zeigt den Seitentitel und diese Bedienelemente.

- **Projekt**: eine Auswahl, nur auf der Übersicht. Sie beschränkt **Handlungsbedarf** und **Aktive Aufträge** auf ein Projekt; Standard sind alle Projekte, auf die Sie Zugriff haben. Aufträge hat eine eigene Auswahl **Jobbereich**, und Statistiken hat in der Zeile des Berichtszeitraums eine Auswahl **Projekt**.
- **Aktualisieren** und **Zuletzt aktualisiert** stehen im Kopfbereich der Seite Benutzer.
- **Über ADORE**: die ADORE-Version mit **Neuigkeiten** (Versionshinweise je Version, die neueste zuerst, gruppiert nach Neu, Verbessert und Behoben), **Lizenz** und **Hinweise zu Drittanbietern**.
- **So funktioniert ADORE**: öffnet dieses Hilfezentrum.

## Projektzentrale {#project-hub}

Wenn Sie ein Projekt unter Projekte öffnen, sehen Sie seinen Namen und den Repository-Pfad über diesen Reitern.

| Reiter | Was er enthält |
|---|---|
| Zusammenfassung | Containertyp, Executor, Überwachung, Umgebungsprüfung, Auftragszahlen sowie kompakte Tabellen für Handlungsbedarf und aktive Aufträge. Administratoren erhalten außerdem **Überwachung pausieren** oder **Überwachung aktivieren**, **Projekt archivieren** oder **Projekt wiederherstellen**, **Host-Voraussetzungen prüfen** und **Repository-Zugang**. |
| Einstellungen | Die wirksamen Einstellungen des Projekts in Gruppen. Administratoren ändern jeweils eine Einstellung über eine geprüfte Änderung; Devs lesen sie ohne Geheimnisse. Siehe [Projekteinstellungen](/help/settings). |
| Aufträge | Die Unterreiter Tickets und Aufträge für dieses Projekt, ohne Projektauswahl. |
| Statistiken | Derselbe Berichtszeitraum, dieselben Reiter und Exporte wie auf der Seite Statistiken, nur für dieses Projekt. |
| Verlauf | Aufgezeichnete Änderungen am Projekt und seine abgeschlossenen Aufträge. |
| Zugriff | Nur für Administratoren: den Zugriff eines Entwicklers gewähren oder entziehen. |

Pausierte Überwachung verhindert, dass neue Tickets aufgenommen werden; bereits gestartete Aufträge laufen weiter.

Überwachung, Archivieren, Wiederherstellen und Löschen nutzen die aktuelle Projektidentität und den Zustand. Beim Verlassen des Projekts oder bei geänderten oder fehlerhaften Projektdaten wird die alte Browserübermittlung abgebrochen, nicht ein bereits angenommener Serverbefehl. Unveränderte Updates erhalten Löschbestätigung und eingegebenen Namen. Ändern sich Name oder Zustand, brechen Sie die Bestätigung ab und öffnen sie vor dem Senden erneut. Ein entferntes Projekt führt mit einem Nicht-verfügbar-Hinweis zu Projekte, nicht zur Zusammenfassung eines anderen Projekts.

## Statuslabels und Badges {#statuses}

Badges tragen neben der Farbe auch ein Symbol, und Auftragslisten zeigen die aktuelle Phase neben dem Status.

| Auftragsstatus | Bedeutung |
|---|---|
| In Arbeit | ADORE steuert eine Phase. |
| Veröffentlichung | ADORE veröffentlicht einen freigegebenen Kandidaten. |
| Wartet auf Klärung | Der Agent braucht eine Antwort im Repository-Ticket. |
| Wartet auf Freigabe | Ein Mensch muss den Kandidaten in der Forge freigeben. |
| Menschliche Prüfung | Ein MR/PR-Entwurf ist offen; Menschen entscheiden über das Zusammenführen. |
| Übergabe läuft | Eine Übergabe an einen Menschen wartet auf einen sicheren Zeitpunkt. |
| Übergeben | Ein Mensch hat übernommen; die automatische Arbeit ist beendet. |
| Abgeschlossen | Der Auftrag ist beendet. Das allein zeigt nicht, dass jemand zusammengeführt hat. Kompakte Listen nennen ihn Fertig. |
| Fehlgeschlagen | Der Auftrag wurde mit erhaltenen Nachweisen gestoppt; ein berechtigter Benutzer kann ihn mit **Wiederholen** erneut anstoßen. |
| Abgebrochen | Der Auftrag wurde abgebrochen. |
| Veraltet | Der Auftrag ist als veraltet markiert; prüfen Sie sein gespeichertes Ergebnis. |

Unter Aufträge beschränkt **Status** die Liste auf **Aktive Aufträge**, **Wartend**, **Menschliche Prüfung** oder **Beendete Jobs**. Das Überwachungs-Badge eines Projekts lautet **Aktiv** oder **Pausiert**, ein archiviertes Projekt zeigt **Archiviert**. Die Umgebungsprüfung lautet **Geprüft**, **Teilweise geprüft**, **Prüfung fehlgeschlagen**, **Prüfung veraltet** oder **Ungeprüft**; Ungeprüft bedeutet, dass kein aktueller Nachweis vorliegt, nicht dass eine Prüfung fehlgeschlagen ist.

Nach **Starten**, **Wiederholen** oder **Abbrechen** meldet ein Hinweis den Befehl als eingereiht, laufend, abgeschlossen, fehlgeschlagen oder ungewiss. Prüfen Sie einen ungewissen Befehl, bevor Sie ihn erneut senden. Ein fehlgeschlagener oder ungewisser Befehl nennt außerdem den Grund, wenn die Engine einen angibt, und zeigt die letzten Zeilen der Engine.

## Automatische Aktualisierung, Sprache und Design {#preferences}

Übersicht, Projekte, Aufträge, Einstellungen, Zugriff und Verlauf eines Projekts sowie der Änderungsverlauf laden ihre Daten alle 15 Sekunden neu, solange der Browser-Tab sichtbar ist. Die Einstellungen pausieren bei ungespeicherten Änderungen sowie beim Speichern oder Verwerfen. Statistiken und Systemstatus aktualisieren sich ebenfalls automatisch. Beim Wechsel zurück zum Tab werden die Aktualisierungen fortgesetzt. Fehlgeschlagene Abfragen blenden betroffene Daten normalerweise bis zur nächsten erfolgreichen Abfrage aus. Statistiken behält Bericht und Steuerung bei Hintergrundabfragen mit **Aktualisieren** in der Ansicht und Zeiten je Quelle. Nach Verbindungsfehlern oder abgelaufener Lesefrist kann ein deutlich markierter älterer Bericht mit **Wiederholen** bleiben; ungültige oder nicht autorisierte Daten bleiben ausgeblendet. Siehe [Statistiken und Kosten](/help/statistics). Beide Änderungsnachweis-Ansichten behalten ebenfalls die Seite bei Abfragen und bieten **Aktualisieren**, Erfolgszeit und markierte ältere Nachweise mit **Wiederholen** nach Verbindungsfehlern oder Fristablauf; siehe [Verwaltung](/help/administration#change-history).

Ein beobachtetes Befehlsergebnis startet neue Abfragen der angezeigten Nachweise in Statistiken, Aufträge und Verlauf und bricht davor begonnene Abfragen ab. Tabellen, Reiter und Exportbereiche bleiben offen; nur geprüfte Ersatzdaten aktualisieren sie. Aufträge benötigt neue Listen- und Detailnachweise vor einem weiteren davon abhängigen Befehl. Andere Einstellungsentwürfe und gültige Prüfungen bleiben geschützt.

Unter [Mein Konto](/account) enthält **Darstellung** die Auswahl **Sprache** (English, Français, Deutsch, Română) und **Design** (**System**, **Hell**, **Dunkel**). Jede Auswahl wird in Ihrem Konto gespeichert und folgt Ihnen in andere Browser; vor der Anmeldung merkt sich die Anmeldeseite die Auswahl im Browser. **Passwort ändern** erfordert Ihr aktuelles Passwort und ein neues mit mindestens 8 Zeichen.

**Abmelden** blendet private Ansichten sofort aus und bricht ihre Browserabfragen ab. Warten Sie vor einer neuen Anmeldung auf das Ende; der Browser wartet höchstens 30 Sekunden. Ein erkannter Zugriffs- oder Sitzungsfehler entfernt ebenfalls die alte Ansicht. Eine geänderte Sitzung wird erneut geprüft; andernfalls melden Sie sich ausdrücklich neu an. Ein erforderlicher Passwortwechsel öffnet sein Formular. Der Abbruch einer Browseranfrage macht einen bereits vom Server angenommenen Befehl nicht rückgängig.

Das ursprüngliche Administratorkonto sieht eine Erinnerung, bis das Anfangskennwort geändert wurde. **Passwort ändern** in der Erinnerung öffnet Mein Konto. Solange die Erinnerung gilt, wird die Sitzung im sichtbaren Tab alle 15 Sekunden geprüft; laufende Abfragen werden geteilt. Änderungen an Konto, Rolle, Projektzugriff oder Passwort entfernen den bisherigen Kontext.

Geben Sie beim Ändern das neue Passwort zweimal ein. Die Schaltflächen zeigen oder verbergen jede Eingabe. Mindestens 8 Zeichen sind erforderlich.
