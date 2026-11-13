# Ce face ADORE

ADORE transformă un tichet pregătit de pe forge-ul de cod într-un MR/PR ciornă (merge request sau pull request) pe care oamenii îl revizuiesc. Această pagină explică fluxul și cele două roluri; celelalte subiecte acoperă fiecare ecran.

## Ce face ADORE {#what-adore-does}

ADORE urmărește proiectele înrolate de un administrator. Când un tichet de pe forge (GitHub, GitLab sau Gitea) este pregătit pentru preluare, ADORE pornește pentru el o **lucrare**:

- Rulează un agent de programare (executorul) într-un mediu izolat: o ramură dedicată, un folder de lucru și un container.
- Agentul urmează fluxul AEGIS al repository-ului, o etapă pe rând: Încadrare, Specificare, Proiectare, Construire și Validare. O modificare mică poate urma o cale rapidă, fără Specificare și Proiectare.
- ADORE urmărește rezultatul raportat de agent și cere unei persoane să aprobe candidatul.
- După aprobare, ADORE publică un MR/PR ciornă pe care oamenii îl revizuiesc. Un proiect poate fi setat să publice în schimb un MR/PR pregătit pentru review.

> ADORE nu integrează niciodată modificările. Nu are nicio operație de integrare (merge); decizia de a integra aparține unei persoane, pe forge.

Interfața web arată ce rulează și ce necesită atenție. Vă permite, de asemenea, să porniți tichete, să reîncercați sau să anulați lucrări și, ca administrator, să configurați proiecte și conturi.

Dacă starea lucrărilor unui proiect nu poate fi citită, secțiunea **Necesită intervenție** indică proiectul afectat. Datele lucrărilor din celelalte proiecte selectate rămân vizibile.

## De la tichet la integrare {#flow}

| Pas | Starea afișată | Cine acționează | Ce se întâmplă |
|---|---|---|---|
| 1. Pregătire | Încă nicio lucrare | O persoană | Tichetul primește eticheta ready și o etichetă de prioritate, sau apăsați **Pornește** în Lucrări → Tichete, ceea ce adaugă etichetele lipsă după confirmarea dumneavoastră. |
| 2. Lucru | În lucru | ADORE și agentul de programare | ADORE creează lucrarea, iar agentul parcurge etapele AEGIS. |
| 3. Clarificare | Așteaptă clarificări | O persoană | Doar dacă agentul are o întrebare. Răspundeți în tichetul din repository și adăugați eticheta de răspuns. |
| 4. Validare | În lucru | Agentul de programare | Agentul raportează verificările conform instrucțiunilor repository-ului, inclusiv cele rezervate CI și nerulate local, și închide task-ul AEGIS. ADORE urmărește finalizarea fără să reia testele. |
| 5. Aprobare | Așteaptă aprobarea | O persoană | ADORE prezintă candidatul pe forge. O persoană adaugă eticheta de aprobare. Aprobarea este legată de exact acel candidat. |
| 6. Publicare | Publicare | ADORE | ADORE trimite ramura (push) și deschide MR/PR-ul ciornă. |
| 7. Revizuire | Revizie umană | O persoană | Oamenii revizuiesc. Cererea unei modificări pornește o nouă rundă de revizie, care necesită o aprobare nouă. |
| 8. Integrare | Finalizat | O persoană | O persoană integrează pe forge. ADORE nu o face. |

Dacă după aprobare se schimbă candidatul sau ramura sa țintă, aprobarea nu se mai aplică, iar lucrarea se validează din nou. Termenii sunt explicați în [glosar](/help/glossary).

## Roluri {#roles}

| Rol | Ce vede | Ce poate face |
|---|---|---|
| Administrator (Admin) | Toate proiectele curente și viitoare, plus Administrare și costurile | Tot ce poate face un Dev, precum și: înrolează proiecte, modifică setările proiectelor prin modificări revizuite, pune în pauză sau reia monitorizarea, arhivează sau restaurează proiecte, gestionează utilizatorii și accesul la proiecte, setează păstrarea auditului, citește istoricul modificărilor și vede și setează costurile |
| Dev | Doar proiectele atribuite de un administrator | Pornește și oprește tichete, reîncearcă sau anulează lucrări, citește statisticile proiectelor atribuite și citește setările proiectului (doar pentru citire, fără secrete și fără setări financiare) |

Un Dev nu vede niciodată valori monetare și nu poate deschide paginile de Administrare. Dacă nu are proiecte atribuite, Prezentarea generală îi indică să ceară acces unui administrator. Dacă nu există proiecte, un Admin poate alege **Înrolează un proiect nou** din Prezentare generală.

## Primii pași {#getting-started}

1. Administratorii înrolează repository-ul: [Adăugarea unui repository](/help/projects).
2. Alegeți modelul folosit de agentul de programare Pi: [Executori și modele](/help/executors).
3. Pregătiți tichetele pentru ca ADORE să le poată prelua: [Tichete pentru preluare automată](/help/tickets).
4. Urmăriți fiecare lucrare până la MR/PR-ul ciornă: [Ciclul de viață al lucrării](/help/jobs).

Dezvoltatorii încep de la pasul 3, după ce un administrator le-a dat acces la un proiect.

## Unde găsiți mai multe informații {#topics}

- [Ce face ADORE](/help/overview): această pagină.
- [Prezentarea interfeței](/help/interface): bara laterală, antetul, pagina proiectului și etichetele de stare.
- [Adăugarea unui repository](/help/projects): înrolarea unui proiect.
- [Setările proiectului](/help/settings): ce controlează fiecare grup de setări.
- [Executori și modele](/help/executors): agentul de programare Pi, modele și autentificare.
- [Tichete pentru preluare automată](/help/tickets): etichete și pornirea tichetelor.
- [Ciclul de viață al lucrării](/help/jobs): stări, stări de așteptare, reîncercare și anulare.
- [Statistici și costuri](/help/statistics): utilizare, calitate, tendințe și costuri estimate.
- [Administrare](/help/administration): utilizatori, acces, starea sistemului și istoricul modificărilor.
- [Glosar](/help/glossary): termenii folosiți în interfață.
