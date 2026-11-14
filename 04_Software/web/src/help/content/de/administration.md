# Verwaltung

Die Verwaltung umfasst Benutzerkonten, Projektzugriff, Systemzustand und das Protokoll der Änderungen. Sie ist nur für Administratoren: Ein Dev sieht das Verwaltungsmenü nicht, und wer als Dev eine ihrer Adressen öffnet, wird zur Übersicht geleitet.

> Alles auf dieser Seite erfordert die Rolle Administrator.

Der Systemstatus trennt **Supervisor**, **Konfigurationsdienst**, **Projektdienst** und aktive Auftrags-/Steuerungsdienste. Aktueller Kontakt beweist weder einen freien Platz noch einen erfolgreichen Vorgang. Aktivität ist Beschäftigt, Inaktiv oder unbekannt. Ein fehlender Projektdienst betrifft nur das genannte Projekt. Die Serverbereitschaft nennt den fehlenden Supervisor oder Konfigurationsdienst; Projektfehler bleiben lokal.

## Benutzer {#users}

Öffnen Sie unter **Verwaltung** die Seite [Benutzer](/admin/users). Sie hat ein Feld **Benutzer hinzufügen** und eine Liste **Benutzer**.

So legen Sie ein Konto an:

1. Wählen Sie **Benutzer hinzufügen** über der Liste, um den Dialog zu öffnen. Geben Sie **Benutzername** und **Passwort** ein (mindestens 8 Zeichen) und füllen Sie **Neues Passwort wiederholen** mit demselben Wert aus. Die Augen-Schaltflächen zeigen oder verbergen das jeweilige Feld. Wählen Sie **Weiter zum Zugriff**. Nach **Identität korrigieren** geben Sie die Wiederholung erneut ein. Das Passwort erscheint nicht in der Prüfung.
2. Wählen Sie die **Rolle** und, für einen Dev, die Projekte. **Admin** gewährt alle aktuellen und künftigen Projekte, die Systemverwaltung und Kosten. **Dev** gewährt nur die Projekte, die Sie ankreuzen, jeweils mit Namen, Forge und Repository-Pfad aufgeführt. Um einen Dev ohne Projekt anzulegen, kreuzen Sie bewusst **Dev ohne Projektzugriff erstellen** an.
3. Wählen Sie **Konto prüfen**, kontrollieren Sie Identität und genauen Zugriff und wählen Sie dann **Geprüftes Konto erstellen**. **Identität korrigieren** und **Zugriff korrigieren** führen zurück, ohne etwas anzulegen.

Konto und Zugriff werden zusammen angelegt oder gar nicht. Ein doppelter Benutzername oder ein inzwischen geändertes Projekt lässt die Anfrage scheitern; korrigieren Sie das und prüfen Sie erneut.

In der Liste **Benutzer** bietet jedes Konto diese Aktionen.

- **Zugewiesene Projekte** (Dev-Konten): Projekte an- oder abwählen, **Speichern** wählen, **Vorher** und **Nachher** vergleichen und dann **Geprüften Zugriff anwenden** wählen. **Zugriff korrigieren** bricht die Prüfung ab.
- **Deaktivieren** oder **Aktivieren**: Ein deaktiviertes Konto kann sich nicht anmelden, und seine Sitzungen enden. Sie können Ihr eigenes Konto nicht deaktivieren, und der letzte aktive Administrator kann nicht deaktiviert werden.
- **Passwort zurücksetzen**: Wählen Sie die Aktion in der Zeile des Kontos. Prüfen Sie den Kontonamen, geben Sie ein **Neues Passwort** mit mindestens 8 Zeichen ein und füllen Sie **Neues Passwort wiederholen** aus. Die Augen-Schaltflächen zeigen oder verbergen die Eingaben. Wählen Sie bei Übereinstimmung **Speichern** oder verwerfen Sie die Eingaben mit **Schließen**. Beim Speichern enden alle Sitzungen des Kontos. Bei der nächsten Anmeldung muss ein neues Passwort gewählt werden. Es gibt keine Wiederherstellung per E-Mail.

## Projektzugriff {#project-access}

Der Reiter **Zugriff** eines Projekts listet jedes Entwicklerkonto mit **Hat Zugriff** oder **Kein Zugriff**. Wählen Sie neben einem Entwickler **Zugriff gewähren** oder **Zugriff entziehen**, vergleichen Sie **Vorher** und **Nachher** und wählen Sie dann **Geprüften Zugriff anwenden**. Die Änderung lässt die anderen Projekte des Entwicklers unberührt und wird im Änderungsverlauf festgehalten. Die Zugriffsliste wird alle 15 Sekunden aktualisiert, solange der Browser-Tab sichtbar ist.

Ein Entwickler mit Zugriff sieht das Projekt und kann dessen Aufträge starten, wiederholen oder abbrechen. Administratoren haben immer Zugriff.

## Systemstatus {#system-status}

Öffnen Sie unter **Verwaltung** den [Systemstatus](/admin/status). Er aktualisiert sich selbst.

- **Dienste** trennt Server- und Projektrollen mit Kontakt und Aktivität. Freie Plätze zeigt Projektkapazität.
- **Speicherplatz** lautet **Platz verfügbar**, **Wenig Speicherplatz** oder **Speicherprüfung fehlgeschlagen**. Es misst den freien Speicherplatz für die ADORE-Kontendatenbank und den Auftragsstatus-Ordner jedes Projekts, gruppiert nach physischem Datenträger. Eine gemeinsame Platte erhält eine einzige Zeile; mehrere Platten erhalten eine Tabelle mit **Datenträger**, **Frei** und **Status**. Weniger als 1 GiB frei gilt als wenig, und eine fehlgeschlagene Messung wird nie als freier Platz angezeigt.
- **Audit-Aufbewahrung** legt fest, wie lange der Änderungsverlauf aufbewahrt wird. Die aktuellen Limits (oder **Unbegrenzt**) stehen über dem Formular. Legen Sie **Aufbewahrung (Tage)** (ganze Tage, 0 bis 36500) und **Limit für Auditdaten (MiB)** (0 bis 1024, Bruchteile erlaubt) fest und wählen Sie **Speichern**. Null oder leer bedeutet unbegrenzt. Die beiden Limits gelten unabhängig voneinander, und die ältesten Ereignisse werden zuerst entfernt. Der Hinweis nach dem Speichern meldet, wie viele Ereignisse gelöscht wurden. Das Größenlimit zählt gespeicherten Audit-Text, nicht die Datenbankdatei auf dem Datenträger. Aufträge, Lauf-Journale und Konten bleiben erhalten.

## Änderungsverlauf {#change-history}

Öffnen Sie unter **Verwaltung** den [Änderungsverlauf](/admin/audit), um zu sehen, wer was wann geändert hat und mit welchem Ergebnis. Der Reiter **Verlauf** eines Projekts zeigt dieselben Nachweise nur für dieses Projekt, zusammen mit seinen abgeschlossenen Aufträgen. Beide Ansichten aktualisieren sich alle 15 Sekunden, solange sie sichtbar sind. Filter, Seite und geöffnete Nachweise bleiben erhalten. Im globalen Änderungsverlauf lädt **Aktualisieren** die Liste sofort neu.

Der Verlauf unterscheidet Tickets und Aufträge von Vorgangsnummern. Fehlgeschlagene Vorgänge zeigen **Fehlgeschlagen**, abgelehnte **Abgelehnt**. Löschungen per CLI zeigen CLI als Akteur und bleiben nach dem Entfernen des Auftrags sichtbar. Eine unterbrochene Löschung bleibt bis zur Bestätigung **Ungewiss**.

Filter:

- **Akteur-ID**: die Nummer neben einem Kontonamen.
- **Projekt**: ein beliebiges Projekt oder **Alle Projekte**.
- **Änderungstyp**: der exakte Aktionscode.
- **Von (UTC)** schließt seinen Zeitpunkt ein; **Bis (UTC, exklusiv)** nicht.

Wählen Sie **Filter anwenden**; das führt zur ersten Seite zurück. Die Seite meldet, wie viele Ereignisse passten, und **Zeilen pro Seite** bietet 10, 25, 50 oder Alle mit **Zurück** und **Weiter**.

Jede Zeile zeigt **Wer**, **Was**, **Wann** und **Ergebnis**: **Vorbereitet**, **Angewendet**, **Verworfen**, **Abgelehnt** oder **Ungewiss**. Vorbereitet bedeutet, dass ein Kandidat bereitgestellt, aber nicht angewendet wurde. **Ungewiss** bedeutet, dass der Host den Abschluss nicht bestätigen konnte; prüfen Sie die tatsächliche Ressource, bevor Sie wiederherstellen. **Nachweis** öffnet unter dem Ereignis eine Zeile mit **Vorher**, **Nachher / Kandidat**, dem **Vorgang** sowie, sofern aufgezeichnet, **Basisrevision** und **Kandidatenrevision**. **Vorheriger Wert nicht erfasst** bedeutet unbekannt, nicht leer. Passwörter und Umgebungswerte werden nie angezeigt.

Der Änderungsverlauf wird unbegrenzt aufbewahrt, sofern Sie unter [Systemstatus](#system-status) keine Limits festlegen. Es gibt keinen Download oder Export des Änderungsverlaufs. Ein Dev sieht betriebliche Änderungen nur für zugewiesene Projekte; Konto-, Zugriffs-, Preis- und Richtlinienereignisse bleiben den Administratoren vorbehalten.
