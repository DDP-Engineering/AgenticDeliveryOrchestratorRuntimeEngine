# Glossar

Die menschliche Freigabe vor Veröffentlichung ist standardmäßig aktiv. Administratoren können **Menschliche Freigabe vor PR/MR verlangen** in Einstellungen ändern. Ohne diese Freigabe prüft ADORE vor Veröffentlichung Kandidat und Ziel auf Aktualität; Repository-Tests bleiben Aufgabe des Agenten.

Diese Begriffe werden in der ADORE-Weboberfläche und in diesen Hilfethemen verwendet.

## Begriffe {#terms}

| Begriff | Bedeutung |
|---|---|
| Auftrag | Ein Repository-Ticket, das in einer isolierten Umgebung bearbeitet und geprüft wird. |
| Eingerichtetes Projekt | Ein vorhandenes Repository auf dem ADORE-Host mit Zugriff für sein Team. |
| Überwachung | Die Einstellung eines Projekts für die Aufnahme neuer Tickets, angezeigt als **Aktiv** oder **Pausiert**. Administratoren ändern sie mit **Überwachung pausieren** und **Überwachung aktivieren** auf dem Reiter Zusammenfassung des Projekts. |
| Übernahme gestoppt | ADORE übernimmt keine neuen Tickets für dieses Projekt. Ein aktiver Auftrag wird dadurch nicht angehalten. Es ist der Zustand, den die Überwachung als **Pausiert** anzeigt. |
| Ticket | Ein Ticket in der Forge. ADORE nimmt es auf, wenn es das Bereitschaftslabel des Projekts und ein Prioritätslabel trägt, nicht angehalten oder ausgeschlossen ist und Akzeptanzkriterien hat, falls das Projekt sie verlangt. |
| Coding-Agent / Executor | Das KI-Kommandozeilenwerkzeug, das die Arbeit für einen Auftrag in einer isolierten Umgebung erledigt: Pi, der einzige Coding-Agent, den ADORE startet. Es hat keine Forge-Zugangsdaten und committet, überträgt, öffnet oder führt nie zusammen. |
| Modell | Die Modell-ID beim gewählten Anbieter, z. B. gpt-5.4 für OpenAI. Sie wird mit dem Anbieter unter Einstellungen → Agent und Modell festgelegt, und Schätzpreise gehören zu einem Paar aus Executor und Modell. |
| AEGIS | Der im Repository installierte Workflow, der eine Änderung rahmt, spezifiziert, entwirft, umsetzt und validiert. ADORE steuert ihn Phase für Phase (Rahmen, Spezifikation, Entwurf, Umsetzung, Validierung) und veröffentlicht das freigegebene Ergebnis; eine kleine Änderung kann Spezifikation und Entwurf überspringen. |
| Direkter Workflow | Ein Repository ohne AEGIS wird direkt vom Agenten bearbeitet. Der Agent führt seine Prüfungen durch; ADORE beobachtet den Fortschritt und fordert menschliche Freigabe an. |
| Kandidat | Das validierte Ergebnis eines Auftrags, das ADORE zur Freigabe vorstellt, gekennzeichnet durch einen Fingerabdruck und den Ziel-Commit. Die Freigabe gilt für genau diesen Kandidaten und verfällt, wenn sich der Kandidat oder sein Zielbranch ändert. |
| Wartet auf Klärung | Der Agent benötigt eine Antwort. Beantworten Sie seine Frage im Repository-Ticket. |
| Wartet auf Freigabe | Das geprüfte Ergebnis wartet auf die menschliche Freigabe zur Veröffentlichung. Die Freigabe erfolgt auf der Forge für den aktuellen Kandidaten. |
| Entwurf MR/PR | Der Merge- oder Pull-Request nach Validierung und gegebenenfalls Freigabe. Menschen prüfen ihn. |
| Menschliche Prüfung | Ein MR/PR steht zur menschlichen Prüfung bereit. Das Zusammenführen bleibt eine menschliche Entscheidung. |
| Überarbeitungsrunde | Ein weiterer Agentendurchgang nach Änderungswunsch oder CI-Fehler. Jede Runde wiederholt die Validierung und folgt der Freigaberegel. |
| Forge | Die Hosting-Plattform, auf der Tickets, Labels, Freigaben und MR/PRs liegen: GitHub, GitLab oder Gitea. |

> ADORE hat keine Merge-Operation. Das Zusammenführen ist immer die Entscheidung eines Menschen in der Forge.
