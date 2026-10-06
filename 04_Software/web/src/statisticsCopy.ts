/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import type { Locale } from "./i18n";
const en = {
  legend: "— = Not available. 0 = Measured zero. Known token amounts may be partial subtotals.",
  evidence: "Selected-period evidence", allTime: "All time", interval: "Selected period", started: "Started jobs", completed: "Completed jobs", failed: "Failed jobs",
  total: "Known total tokens", unavailable: "Not available", zero: "Measured zero", partial: "Partial · known subtotal", measured: "Known measurement",
  coverage: "Measurement coverage", coverageHelp: "Known tokens sum recorded observations. Missing observations can make these subtotals incomplete; they are not a complete bill.",
  stock: "Current state · active now", stockHelp: "Current stock is independent of the selected period. These are jobs active now, not jobs started during the interval.",
  boundaries: "From and Through include their local calendar dates. The server uses [from,to): From midnight included, next local midnight after Through excluded. DST can make a day 23 or 25 hours.",
  lifecycle: "Started means the job was first picked up. Completed includes all terminal jobs (done, failed, cancelled or handed off); failed jobs use their own final failure event. Counts use each event’s actual time.",
  duration: "Duration samples: valid terminal elapsed spans ending in this period, including waits and measured zero. Jobs without a recorded start/end pair are excluded.",
  messages: "Messages", messageHelp: "Actual message evidence is not collected yet. Executor launches are not messages.",
  jobs: "Job consumption", lifetime: "Lifetime", selected: "Selected period", undated: "Unallocated", source: "Source", events: "Usage observations", projectId: "Project ID", runId: "Run ID",
  jobHelp: "Every row identifies an immutable project and job. Lifetime includes known undated observations; selected-period values use actual consumption times. Unallocated timestamps cannot be assigned to a date. These are known subtotals; observation counts do not prove complete measurement coverage.",
  sourceJournal: "Recorded usage observations", sourceSummary: "Legacy recorded summary · date unavailable", sourceUnavailable: "No reported consumption",
  missingJob: "No consumption projection is available for this job in the selected scope.",
  reported: "Reported cost", estimated: "Estimated cost", moneyHelp: "Reported cost comes from observed evidence. Estimates use the saved executor/model price effective on the UTC consumption date. They remain separate; missing prices or cost are unavailable.",
  trend: "Job trend chart", table: "Trend data · accessible equivalent", empty: "No dated events in this scope.",
  unallocatedHelp: "Unallocated observations have no usable timestamp. They are shown separately, never guessed into a date bucket.",
  periodHelp: "Change the reporting period in Statistics. This job uses the same dates, timezone and grouping.",
};
type Copy = typeof en;
const fr: Copy = {
  legend: "— = Non disponible. 0 = Zéro mesuré. Les jetons connus peuvent être des sous-totaux partiels.",
  evidence: "Données de la période sélectionnée", allTime: "Toute la période", interval: "Période sélectionnée", started: "Jobs démarrés", completed: "Jobs terminés", failed: "Jobs échoués",
  total: "Total connu des jetons", unavailable: "Non disponible", zero: "Zéro mesuré", partial: "Partiel · sous-total connu", measured: "Mesure connue",
  coverage: "Couverture des mesures", coverageHelp: "Les jetons connus additionnent les observations enregistrées. Les observations manquantes peuvent rendre ces sous-totaux incomplets ; ce n'est pas une facture complète.",
  stock: "État actuel · actifs maintenant", stockHelp: "Le stock actuel est indépendant de la période sélectionnée. Ce sont les jobs actifs maintenant, pas les démarrages de la période.",
  boundaries: "Du et Jusqu'au incluent les dates locales. Le serveur utilise [from,to) : minuit de début inclus, minuit local suivant la fin exclu. Le changement d'heure peut donner 23 ou 25 heures.",
  lifecycle: "Les démarrages utilisent le premier événement de prise en charge. Les jobs terminés comprennent tous les états terminaux (réussi, échoué, annulé ou remis) ; les échecs utilisent leur événement final. Chaque événement garde son heure réelle.",
  duration: "Échantillons de durée : temps écoulés terminaux valides finissant dans la période, attentes et zéro mesuré inclus. Les jobs sans début/fin enregistré sont exclus.",
  messages: "Messages", messageHelp: "Les données réelles des messages ne sont pas encore collectées. Les lancements d'exécuteurs ne sont pas des messages.",
  jobs: "Consommation du job", lifetime: "Durée de vie", selected: "Période sélectionnée", undated: "Non attribué", source: "Source", events: "Observations d'utilisation", projectId: "ID du projet", runId: "ID du job",
  jobHelp: "Chaque ligne identifie un projet et un job immuables. Le total historique inclut les observations non datées ; la période utilise les heures réelles de consommation. Une date inutilisable reste non attribuée. Ce sont des sous-totaux connus ; le nombre d’observations ne prouve pas une couverture complète.",
  sourceJournal: "Observations enregistrées", sourceSummary: "Résumé historique · date indisponible", sourceUnavailable: "Aucune consommation déclarée",
  missingJob: "Aucune projection de consommation pour ce job dans ce périmètre.", reported: "Coût déclaré", estimated: "Coût estimé",
  moneyHelp: "Le coût déclaré vient des observations. Les estimations utilisent le prix sauvegardé exécuteur/modèle à la date UTC de consommation. Ils restent séparés ; un prix ou coût manquant est indisponible.",
  trend: "Graphique des jobs", table: "Données de tendance · équivalent accessible", empty: "Aucun événement daté dans ce périmètre.",
  unallocatedHelp: "Les observations non attribuées n'ont pas de date utilisable. Elles restent séparées des groupes de dates.", periodHelp: "Modifiez la période dans Statistiques. Ce job utilise les mêmes dates, fuseau et regroupement.",
};
const de: Copy = {
  legend: "— = Nicht verfügbar. 0 = Gemessene Null. Bekannte Token können teilweise Teilsummen sein.",
  evidence: "Nachweise im gewählten Zeitraum", allTime: "Gesamter Zeitraum", interval: "Gewählter Zeitraum", started: "Gestartete Jobs", completed: "Abgeschlossene Jobs", failed: "Fehlgeschlagene Jobs",
  total: "Bekannte Token insgesamt", unavailable: "Nicht verfügbar", zero: "Gemessene Null", partial: "Teilweise · bekannte Teilsumme", measured: "Bekannte Messung",
  coverage: "Messabdeckung", coverageHelp: "Bekannte Token summieren aufgezeichnete Beobachtungen. Fehlende Beobachtungen können diese Teilsummen unvollständig machen; sie sind keine vollständige Rechnung.",
  stock: "Aktueller Zustand · jetzt aktiv", stockHelp: "Der aktuelle Bestand ist unabhängig vom gewählten Zeitraum. Dies sind jetzt aktive Jobs, keine Jobstarts im Intervall.",
  boundaries: "Von und Bis schließen lokale Kalendertage ein. Der Server nutzt [from,to): Startmitternacht eingeschlossen, nächste lokale Mitternacht nach Bis ausgeschlossen. Zeitumstellung kann 23 oder 25 Stunden ergeben.",
  lifecycle: "Jobstarts nutzen das erste Übernahmeereignis. Abgeschlossen umfasst alle Endzustände (fertig, fehlgeschlagen, abgebrochen oder übergeben); Fehler nutzen ihr letztes Fehlerereignis. Jedes Ereignis zählt zu seiner tatsächlichen Zeit.",
  duration: "Dauerstichproben: gültige abgeschlossene Zeitspannen mit Ende im Zeitraum, einschließlich Wartezeiten und gemessener Null. Jobs ohne aufgezeichneten Start/Ende werden ausgeschlossen.",
  messages: "Nachrichten", messageHelp: "Echte Nachrichtennachweise werden noch nicht erfasst. Executorstarts sind keine Nachrichten.",
  jobs: "Jobverbrauch", lifetime: "Gesamtlaufzeit", selected: "Gewählter Zeitraum", undated: "Nicht zugeordnet", source: "Quelle", events: "Verbrauchsbeobachtungen", projectId: "Projekt-ID", runId: "Job-ID",
  jobHelp: "Jede Zeile bezeichnet ein unveränderliches Projekt und einen Job. Die Gesamtsumme enthält undatierte Beobachtungen; der Zeitraum nutzt tatsächliche Verbrauchszeiten. Unbrauchbare Zeitstempel bleiben nicht zugeordnet. Dies sind bekannte Teilsummen; Beobachtungszahlen beweisen keine vollständige Messabdeckung.",
  sourceJournal: "Aufgezeichnete Verbrauchsbeobachtungen", sourceSummary: "Historische Zusammenfassung · Datum nicht verfügbar", sourceUnavailable: "Kein gemeldeter Verbrauch",
  missingJob: "Für diesen Job ist im gewählten Bereich kein Verbrauchsnachweis verfügbar.", reported: "Gemeldete Kosten", estimated: "Geschätzte Kosten",
  moneyHelp: "Gemeldete Kosten stammen aus Beobachtungen. Schätzungen nutzen den gespeicherten Executor-/Modellpreis am UTC-Verbrauchsdatum. Sie bleiben getrennt; fehlende Preise oder Kosten sind nicht verfügbar.",
  trend: "Jobtrend-Diagramm", table: "Trenddaten · zugängliche Entsprechung", empty: "Keine datierten Ereignisse in diesem Bereich.",
  unallocatedHelp: "Nicht zugeordnete Beobachtungen haben keinen brauchbaren Zeitstempel. Sie bleiben getrennt von Datumsgruppen.", periodHelp: "Ändern Sie den Berichtszeitraum unter Statistik. Dieser Job nutzt dieselben Daten, Zeitzone und Gruppierung.",
};
const ro: Copy = {
  legend: "— = Indisponibil. 0 = Zero măsurat. Tokenii cunoscuți pot fi subtotaluri parțiale.",
  evidence: "Dovezi din perioada selectată", allTime: "Tot istoricul", interval: "Perioada selectată", started: "Joburi începute", completed: "Joburi terminate", failed: "Joburi eșuate",
  total: "Total tokeni cunoscuți", unavailable: "Indisponibil", zero: "Zero măsurat", partial: "Parțial · subtotal cunoscut", measured: "Măsurătoare cunoscută",
  coverage: "Acoperirea măsurătorilor", coverageHelp: "Tokenii cunoscuți însumează observațiile înregistrate. Observațiile lipsă pot face subtotalurile incomplete; nu reprezintă o factură completă.",
  stock: "Stare curentă · active acum", stockHelp: "Stocul curent este independent de perioada selectată. Acestea sunt joburile active acum, nu joburile începute în interval.",
  boundaries: "De la și Până la includ datele calendaristice locale. Serverul folosește [from,to): miezul nopții de început inclus, următorul miez al nopții după Până la exclus. Schimbarea orei poate produce zile de 23 sau 25 de ore.",
  lifecycle: "Joburile începute folosesc primul eveniment de preluare. Cele terminate includ toate stările terminale (finalizat, eșuat, anulat sau predat); eșecurile folosesc propriul eveniment final. Fiecare eveniment are momentul său real.",
  duration: "Eșantioane de durată: intervale terminale valide încheiate în perioadă, inclusiv așteptările și zero măsurat. Joburile fără pereche început/sfârșit înregistrată sunt excluse.",
  messages: "Mesaje", messageHelp: "Dovezile reale ale mesajelor nu sunt încă colectate. Lansările executorilor nu sunt mesaje.",
  jobs: "Consumul jobului", lifetime: "Tot istoricul jobului", selected: "Perioada selectată", undated: "Nealocat", source: "Sursă", events: "Observații de consum", projectId: "ID proiect", runId: "ID job",
  jobHelp: "Fiecare rând identifică proiectul și jobul imuabile. Istoricul include observațiile fără dată; perioada folosește momentele reale de consum. Momentele inutilizabile rămân nealocate. Acestea sunt subtotaluri cunoscute; numărul observațiilor nu dovedește acoperirea completă a măsurătorilor.",
  sourceJournal: "Observații de consum înregistrate", sourceSummary: "Sumar istoric · dată indisponibilă", sourceUnavailable: "Niciun consum raportat",
  missingJob: "Nu există o proiecție de consum pentru acest job în selecția curentă.", reported: "Cost raportat", estimated: "Cost estimat",
  moneyHelp: "Costul raportat provine din observații. Estimările folosesc prețul salvat al executorului/modelului la data UTC a consumului. Rămân separate; prețurile sau costurile lipsă sunt indisponibile.",
  trend: "Graficul joburilor", table: "Date de tendință · echivalent accesibil", empty: "Nu există evenimente datate în selecție.",
  unallocatedHelp: "Observațiile nealocate nu au un moment utilizabil. Sunt afișate separat și nu sunt atribuite presupus unei date.", periodHelp: "Schimbă perioada în Statistici. Acest job folosește aceleași date, fus orar și grupare.",
};
export const statisticsCopy: Record<Locale, Copy> = { en, fr, de, ro };
