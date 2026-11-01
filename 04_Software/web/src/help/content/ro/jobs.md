# Ciclul de viață al lucrării

O lucrare este munca pe care o face ADORE pentru un tichet, de la preluare până la o modificare integrată. Acest articol arată etapele ei și unde participați dumneavoastră. Etichetele și eligibilitatea sunt în [Tichete pentru preluare automată](/help/tickets).

## Etape {#stages}

ADORE parcurge etapele AEGIS pe rând, fiecare încercare într-o sesiune nouă de executor. Executorii nu fac niciodată push, nu deschid un MR/PR și nu integrează.

| Etapă | Ce se întâmplă |
|---|---|
| Încadrare | Se stabilește domeniul, iar executorul înregistrează dacă lucrarea urmează calea completă sau cea rapidă. |
| Specificare | Se scrie cerința. |
| Proiectare | Se scrie o notă scurtă de proiectare pentru lucrările netriviale. |
| Construire | Mai întâi un test care eșuează, apoi implementarea, până când testele trec. |
| Validare | Revizuire, suita completă de teste, o verificare strictă și raportul AEGIS; sarcina AEGIS se închide. ADORE repetă apoi singur verificarea strictă înainte să ceară aprobarea. |

Calea rapidă parcurge Încadrare, Construire și Validare. După Validare, lucrarea afișează etapa **Finalizată** cât timp așteaptă aprobarea, este publicată și se află în revizie umană. Pe calea completă, validarea poate trimite o lucrare înapoi la Specificare, Proiectare sau Construire; pe calea rapidă, doar înapoi la Construire. O etapă primește implicit trei încercări eșuate (**Încercări eșuate permise per etapă**).

## Clarificare {#clarification}

Când executorul are nevoie de informații, ADORE postează un comentariu pe tichet, „Clarification required for stage” (în engleză, așa cum îl publică ADORE), care listează întrebările, și setează `agent-clarify`. Lucrarea afișează **Așteaptă clarificări**, iar detaliile ei oferă **Răspunde pe tichet**.

Răspundeți cu un comentariu obișnuit pe tichet, apoi adăugați `agent-answered`. Ambele sunt necesare; comentariile ADORE nu contează. ADORE elimină ambele etichete și reia lucrul. Întrebările nu se numără ca încercări eșuate. **Numărul maxim de runde de întrebări** (3 implicit) limitează de câte ori poate întreba o lucrare, iar **Timpul acordat unui răspuns uman** (72 de ore implicit) face lucrarea să eșueze când expiră.

## Aprobare {#approval}

Când validarea strictă reușește, ADORE elimină `agent-approved`, postează dovezile pe tichet și așteaptă. Lucrarea afișează **Așteaptă aprobarea**, iar tichetul păstrează `agent-working`. Dovezile numesc candidatul exact și eventualele abateri înregistrate de executor.

Revizuiți-l, apoi adăugați din nou `agent-approved`; contează doar o adăugare nouă. Aprobarea este legată de acel candidat și de commit-ul ramurii țintă. Dacă oricare dintre ele se schimbă, aprobarea devine nulă, iar ADORE integrează, validează și cere din nou aprobarea. Această așteptare nu are temporizator. Detaliile lucrării oferă **Verifică versiunea pe platforma Git**.

## Publicare și revizuire {#review}

După aprobare, ADORE face push ramurii și deschide MR/PR-ul către ramura țintă, cere review de la conturile din **Solicită review de la** și setează `agent-mr`. **Starea PR/MR la publicare** alege Draft (implicit) sau Pregătit pentru review. Lucrarea afișează **Publicare**, apoi **Revizie umană**. ADORE nu integrează niciodată. După ce o persoană integrează, ADORE setează `agent-done`, lucrarea afișează **Finalizat**, iar implicit ramura remote este ștearsă. Un MR/PR închis fără integrare face lucrarea să eșueze.

Pentru a cere modificări, un recenzor adaugă `agent-revise` pe MR/PR. ADORE elimină eticheta, pornește o sarcină nouă pe aceeași ramură și repetă validarea și o nouă aprobare înainte de push. **Numărul maxim de runde de revizie** (5 implicit) limitează acest proces. O cerere peste limită face lucrarea să eșueze.

Dacă verificările CI eșuează pe MR/PR, decide **Acțiune când verificările CI ale PR/MR eșuează**: Reparare automată (implicit) pornește o revizie, Doar notificare postează un comentariu, iar Ignoră sare peste starea CI. Reparările automate consumă același buget de revizii; după epuizare, ADORE postează o notificare, iar lucrarea rămâne în revizuire.

## Eșec și recuperare {#failures}

Când o etapă eșuează, ADORE ține la zi un singur comentariu de incident pe tichet, cu etapa, încercarea, codul erorii, dovezile și următoarea acțiune; dacă agentul s-a oprit fără să avanseze etapa, dovezile arată și ultimele lui linii de ieșire de eroare. După ultima încercare postează un comentariu final, setează `agent-failed`, oprește containerul, păstrează worktree-ul și eliberează locul. Alte cauze sunt un timp de răspuns expirat, un tichet sursă șters și o limită depășită, precum costul sau fișierele modificate. Închiderea tichetului sursă cât timp o lucrare așteaptă o anulează.

În Lucrări, o lucrare eșuată afișează **Eșuate**, iar detaliile ei explică faptul că dovezile de recuperare sunt păstrate. **Reîncearcă** cere workerului să recupereze lucrarea; nu ocolește validarea sau aprobarea. În vizualizarea Tichete, Reia înlocuiește Pornește. Eliminarea `agent-failed` nu reîncearcă. **Anulează** apare pentru lucrările neterminate și cere workerului să se oprească și să curețe. Lucrările încheiate nu pot fi anulate. Administratorii și dezvoltatorii atribuiți le pot folosi pe ambele. O comandă din coadă își arată progresul, de exemplu Comandă în coadă sau Comandă terminată. O comandă eșuată sau incertă spune și motivul, când motorul îl numește, și arată ultimele linii ale motorului.

## Urmărirea lucrărilor {#following-jobs}

Folosiți **Lucrări** din bara laterală sau fila **Lucrări** a unui proiect, apoi sub-fila **Lucrări**. Tabelul are aceste coloane:

| Coloană | Conținut |
|---|---|
| Tichet | Numărul și titlul; deschide detaliile lucrării. |
| Proiect | Proiectul căruia îi aparține. |
| Stare | Starea, Etapa curentă și un link către tichet sau MR/PR când o persoană trebuie să acționeze. |
| Ultima activitate | Momentul ultimului eveniment salvat. |
| Consum | Tokenurile folosite de lucrare. |

Faceți clic pe un antet de coloană pentru a sorta. **Caută joburi** potrivește titluri, numere, proiecte, ID-uri de lucrare, stare, etapă sau rezultat. Filtrul **Stare** oferă Lucrări active, În așteptare, Revizie umană și Joburi încheiate. Pagina se reîmprospătează singură cât timp este vizibilă.

Detaliile afișează **Ce se întâmplă acum**, **Cine intervine**, **Unde** și **Ce urmează**, apoi Consum, o Cronologie (Dată, Eveniment, Etapă), linkurile **Dovezi și artefacte** și **Detalii tehnice**. Cronologia listează doar evenimentele salvate. O activitate veche, singură, nu arată că lucrul s-a oprit.
