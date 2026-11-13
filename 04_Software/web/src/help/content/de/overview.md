# Was ADORE leistet

Die menschliche Freigabe vor Veröffentlichung ist standardmäßig aktiv. Administratoren können **Menschliche Freigabe vor PR/MR verlangen** in Einstellungen ändern. Ohne diese Freigabe prüft ADORE vor Veröffentlichung Kandidat und Ziel auf Aktualität; Repository-Tests bleiben Aufgabe des Agenten.

ADORE macht aus einem vorbereiteten Ticket in Ihrer Code-Forge einen Entwurf für einen Merge Request oder Pull Request, den Menschen prüfen. Diese Seite erklärt den Ablauf und die beiden Rollen; die übrigen Themen behandeln jeweils einen Bildschirm.

## Was ADORE leistet {#what-adore-does}

ADORE beobachtet die Projekte, die ein Administrator eingerichtet hat. Ist ein Ticket in der Forge (GitHub, GitLab oder Gitea) zur Aufnahme vorbereitet, startet ADORE dafür einen **Auftrag**:

- Es führt einen Coding-Agenten (den Executor) in einer isolierten Umgebung aus: mit eigenem Branch, eigenem Arbeitsordner und eigenem Container.
- Der Agent folgt dem AEGIS-Workflow des Repositorys Phase für Phase: Rahmen, Spezifikation, Entwurf, Umsetzung und Validierung. Eine kleine Änderung kann einen Schnellpfad ohne Spezifikation und Entwurf nehmen.
- ADORE beobachtet das vom Agenten gemeldete Ergebnis und bittet einen Menschen um Freigabe.
- Nach der Freigabe veröffentlicht ADORE einen MR/PR-Entwurf, den Menschen prüfen. Ein Projekt kann stattdessen so eingestellt werden, dass ein fertiger MR/PR veröffentlicht wird.

> ADORE führt nie einen Merge aus. Es gibt keine Merge-Operation; ob zusammengeführt wird, entscheidet ein Mensch in der Forge.

Die Weboberfläche zeigt, was gerade läuft und was Aufmerksamkeit braucht. Sie erlaubt es außerdem, Tickets zu starten, Aufträge zu wiederholen oder abzubrechen und, als Administrator, Projekte und Konten einzurichten.

Wenn sich der Auftragsstatus eines Projekts nicht lesen lässt, nennt **Handlungsbedarf** das betroffene Projekt. Auftragsdaten der anderen ausgewählten Projekte bleiben sichtbar.

## Vom Ticket zum Merge {#flow}

| Schritt | Angezeigter Status | Wer handelt | Was geschieht |
|---|---|---|---|
| 1. Vorbereiten | Noch kein Auftrag | Ein Mensch | Das Ticket erhält das Bereitschaftslabel und ein Prioritätslabel, oder Sie wählen **Starten** unter Aufträge → Tickets; fehlende Labels werden nach Ihrer Bestätigung ergänzt. |
| 2. Arbeiten | In Arbeit | ADORE und der Coding-Agent | ADORE legt den Auftrag an und der Agent arbeitet die AEGIS-Phasen ab. |
| 3. Klären | Wartet auf Klärung | Ein Mensch | Nur wenn der Agent eine Frage hat. Antworten Sie im Repository-Ticket und setzen Sie das Antwortlabel. |
| 4. Validieren | In Arbeit | Coding-Agent | Der Agent meldet Prüfungen gemäß den Repository-Anweisungen, einschließlich nur in CI ausführbarer Prüfungen, und schließt die AEGIS-Aufgabe. ADORE beobachtet den Abschluss ohne erneute Tests. |
| 5. Freigeben | Wartet auf Freigabe | Ein Mensch | ADORE stellt den Kandidaten in der Forge vor. Ein Mensch setzt das Freigabelabel. Die Freigabe ist an genau diesen Kandidaten gebunden. |
| 6. Veröffentlichen | Veröffentlichung | ADORE | ADORE überträgt den Branch und öffnet den MR/PR-Entwurf. |
| 7. Prüfen | Menschliche Prüfung | Ein Mensch | Menschen prüfen. Eine Überarbeitung wiederholt die Validierung und folgt der Freigaberegel. |
| 8. Zusammenführen | Abgeschlossen | Ein Mensch | Ein Mensch führt in der Forge zusammen. ADORE tut das nicht. |

Ändert sich der Kandidat oder sein Zielbranch nach der Freigabe, gilt die Freigabe nicht mehr und der Auftrag wird erneut validiert. Begriffe erklärt das [Glossar](/help/glossary).

## Rollen {#roles}

| Rolle | Sieht | Kann |
|---|---|---|
| Administrator (Admin) | Alle aktuellen und künftigen Projekte sowie Verwaltung und Kosten | Alles, was ein Dev kann, und zusätzlich Projekte einrichten, Projekteinstellungen über geprüfte Änderungen bearbeiten, die Überwachung pausieren oder aktivieren, Projekte archivieren oder wiederherstellen, Benutzer und Projektzugriff verwalten, die Audit-Aufbewahrung festlegen, den Änderungsverlauf lesen sowie Kosten sehen und festlegen |
| Dev | Nur die Projekte, die ein Administrator zugewiesen hat | Tickets starten und stoppen, Aufträge wiederholen oder abbrechen, Statistiken zugewiesener Projekte lesen und Projekteinstellungen lesen (schreibgeschützt, ohne Geheimnisse und Finanzeinstellungen) |

Ein Dev sieht nie Geldbeträge und kann die Verwaltungsseiten nicht öffnen. Ohne zugewiesenes Projekt bittet die Übersicht den Dev, bei einem Administrator Zugriff anzufordern. Sind keine Projekte vorhanden, kann ein Admin in der Übersicht **Neues Projekt registrieren** wählen.

## Erste Schritte {#getting-started}

1. Administratoren richten das Repository ein: [Repository hinzufügen](/help/projects).
2. Modell für den Coding-Agenten Pi wählen: [Executor und Modelle](/help/executors).
3. Tickets so vorbereiten, dass ADORE sie aufnehmen kann: [Tickets für die automatische Aufnahme](/help/tickets).
4. Jeden Auftrag bis zum MR/PR-Entwurf verfolgen: [Lebenszyklus eines Auftrags](/help/jobs).

Entwickler beginnen bei Schritt 3, sobald ein Administrator ihnen Zugriff auf ein Projekt gegeben hat.

## Weitere Themen {#topics}

- [Was ADORE leistet](/help/overview): diese Seite.
- [Rundgang durch die Oberfläche](/help/interface): Seitenleiste, Kopfzeile, Projektzentrale und Statuslabels.
- [Repository hinzufügen](/help/projects): ein Projekt einrichten.
- [Projekteinstellungen](/help/settings): was jede Einstellungsgruppe steuert.
- [Executor und Modelle](/help/executors): der Coding-Agent Pi, Modelle und Authentifizierung.
- [Tickets für die automatische Aufnahme](/help/tickets): Labels und das Starten von Tickets.
- [Lebenszyklus eines Auftrags](/help/jobs): Status, Wartezustände, Wiederholen und Abbrechen.
- [Statistiken und Kosten](/help/statistics): Nutzung, Qualität, Trends und geschätzte Kosten.
- [Verwaltung](/help/administration): Benutzer, Zugriff, Systemstatus und Änderungsverlauf.
- [Glossar](/help/glossary): die in der Oberfläche verwendeten Begriffe.
