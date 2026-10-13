# Tickets für die automatische Aufnahme

ADORE nimmt Tickets aus Ihrem Forge-Repository (GitHub, GitLab oder Gitea) auf, wenn sie die richtigen Labels tragen, und Sie können ein Ticket auch von Hand starten. Dieser Artikel behandelt Labels, Eignung und die Ticketansicht.

## So funktioniert die Aufnahme {#how-pickup-works}

Jedes Projekt hat einen Status der **Überwachung**, der in der Projekttabelle und auf dem Reiter Zusammenfassung des Projekts als **Aktiv** oder **Pausiert** angezeigt wird. Solange die Überwachung Aktiv ist, prüft ADORE das Repository in regelmäßigen Abständen auf bereite Tickets (standardmäßig alle 60 Sekunden; siehe **Abfrageintervall (Sekunden)** unter [Projekteinstellungen](/help/settings)). Es nimmt zuerst das geeignete Ticket mit der höchsten Priorität (P1, dann P2, dann P3), danach mit der niedrigsten Nummer, und bearbeitet jeweils einen Auftrag.

Ein Administrator kann auf dem Reiter Zusammenfassung des Projekts **Überwachung pausieren** und **Überwachung aktivieren** verwenden. Pausierte Überwachung stoppt neue Aufnahmen; laufende Aufträge laufen weiter.

## Zuerst die Labels anlegen {#labels}

ADORE setzt und entfernt Labels, legt sie aber nie an. GitHub und Gitea lehnen einen unbekannten Labelnamen ab, sodass ein fehlendes Label Statusaktualisierungen fehlschlagen lässt. Legen Sie alle folgenden Labels im Forge-Repository an, bevor Sie zum ersten Mal starten. Die Namen sind Standardwerte; benennen Sie eines nur gemeinsam mit seiner Projekteinstellung um.

| Label | Zweck |
|---|---|
| `agent-ready` | Sie setzen es, um ein Ticket zur Aufnahme anzubieten. ADORE ersetzt es beim Start des Auftrags durch das Arbeitslabel. |
| `agent-working` | ADORE setzt es, solange es arbeitet, veröffentlicht und auf Ihre Freigabe wartet. |
| `agent-clarify` | ADORE setzt es, wenn es eine Frage gestellt hat und auf eine Antwort wartet. |
| `agent-answered` | Sie setzen es, nachdem Sie auf eine Frage geantwortet haben. |
| `agent-mr` | ADORE setzt es nach der Veröffentlichung des MR/PR, solange es auf die menschliche Prüfung wartet. |
| `agent-failed` | ADORE setzt es, wenn ein Auftrag fehlschlägt. |
| `agent-done` | ADORE setzt es, nachdem ein Mensch den MR/PR zusammengeführt hat. |
| `agent-approved` | Sie setzen es am Ticket, um die Veröffentlichung des vorgestellten Kandidaten freizugeben. |
| `agent-revise` | Ein Reviewer setzt es am MR/PR, um eine Überarbeitungsrunde anzufordern. |

ADORE entfernt bei jeder Statusaktualisierung die Lebenszyklus-Labels, die es nicht setzt, daher müssen alle existieren. Ein von Hand gesetztes Statuslabel ändert den Auftrag nicht.

## Wann ein Ticket geeignet ist {#eligible-tickets}

Ein Ticket wird nur aufgenommen, wenn jede Regel erfüllt ist. Sie werden in dieser Reihenfolge geprüft:

1. Das Ticket ist offen.
2. Es hat das Bereitschaftslabel (`agent-ready`).
3. Es hat nicht das Sperrlabel (`agent-hold`). Das Entfernen des Sperrlabels macht das Ticket wieder geeignet.
4. Es hat nicht das Ausschlusslabel (`no-agent`, Einstellung **Label zum Ausschluss von der Aufnahme**). Es hat Vorrang vor dem Bereitschaftslabel. Das Entfernen stellt die Eignung wieder her; das Setzen stoppt keinen bereits gestarteten Auftrag.
5. ADORE hat noch keinen Auftrag für das Ticket.
6. Es hat ein Prioritätslabel: `P1`, `P2` oder `P3`. **Prioritätslabel am Ticket verlangen** ist standardmäßig aktiv.
7. Ist **Akzeptanzkriterien im Ticket verlangen** aktiv, enthält die Beschreibung die Wörter acceptance criteria (beliebige Schreibweise) oder einen nicht abgehakten Aufgabenpunkt, `- [ ]`. Diese Prüfung ist standardmäßig aus.

Optionale Labels formen den Auftrag: `bug` oder `fix` ergibt eine Fehlerbehebung, `change` eine Änderung und jedes andere Ticket eine Funktion. `agent-quick` ist nur ein Hinweis; der Executor entscheidet zwischen vollem und schnellem Pfad und hält den Grund fest.

## Tickets prüfen und starten {#tickets-view}

Öffnen Sie ein Projekt unter Projekte, wählen Sie seinen Reiter **Aufträge** und bleiben Sie im Unterreiter **Tickets**. Die globale Seite **Aufträge** in der Seitenleiste hat dieselben beiden Unterreiter und eine Auswahl **Jobbereich**. Bei **Alle Projekte** erhält die Tabelle eine Spalte Projekt, und jede Zeile wirkt auf ihr eigenes Projekt.

Es wird nichts gelesen, bis Sie **Tickets lesen** drücken. Das lädt bis zu 500 offene Tickets. Mehr als 10 Tickets werden seitenweise angezeigt: Wählen Sie 10, 25, 50 oder Alle unter **Zeilen pro Seite** und blättern Sie mit **Zurück** und **Weiter**; Seitennummer und Seitenzahl werden angezeigt. Jede Zeile zeigt Nummer, Titel, Labels, Status und Aktionen. Der Status nennt, was ein Ticket blockiert:

| Status | Bedeutung |
|---|---|
| Startbereit | Jede Regel ist erfüllt. |
| Label ... fehlt | Das Bereitschaftslabel fehlt. |
| Angehalten oder Von ADORE ausgeschlossen | Das Sperr- oder Ausschlusslabel ist vorhanden. |
| Prioritätslabel fehlt | Kein Prioritätslabel. |
| Akzeptanzkriterien fehlen | Erforderlicher Text nicht gefunden. |
| Hat einen Auftrag oder Auftrag: ... | ADORE hat bereits einen Auftrag; der Auftragsstatus wird angezeigt. |
| Nicht offen | Das Ticket ist geschlossen. |

**Starten** reiht einen Auftrag ein; der Worker wendet weiterhin die üblichen Prüfungen an. Fehlt dem Ticket das Bereitschafts- oder ein Prioritätslabel, bittet ADORE um Bestätigung, lässt Sie eine Priorität wählen, und **Labels hinzufügen und starten** ergänzt sie zuerst im Repository. Starten ist nicht verfügbar für geschlossene, angehaltene oder ausgeschlossene Tickets, für Tickets ohne erforderliche Akzeptanzkriterien und für Tickets mit einem Auftrag. **Wiederholen** ersetzt Starten, wenn der Auftrag fehlgeschlagen ist. **Stoppen** fragt nach Bestätigung, bricht einen unvollständigen Auftrag ab und entfernt das Bereitschaftslabel, damit die Überwachung das Ticket nicht erneut aufnimmt. **Details** zeigt Beschreibung und Kommentare.

## Checkliste für ein erstes Ticket {#checklist}

1. Legen Sie alle neun Labels im Forge-Repository an.
2. Prüfen Sie, dass die Überwachung Aktiv ist.
3. Schreiben Sie einen klaren Titel und eine Beschreibung mit Akzeptanzkriterien.
4. Setzen Sie ein Prioritätslabel und optional `bug`, `fix`, `change` oder `agent-quick`.
5. Setzen Sie `agent-ready` zuletzt.
6. Warten Sie auf die nächste Prüfung oder drücken Sie **Tickets lesen** und **Starten**.
7. Verfolgen Sie den Auftrag unter [Lebenszyklus eines Auftrags](/help/jobs). Begriffe stehen im [Glossar](/help/glossary).
