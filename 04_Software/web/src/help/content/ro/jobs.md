# Ciclul de viață al lucrării

O lucrare este munca pe care o face ADORE pentru un tichet, de la preluare până la o modificare integrată. Acest articol arată etapele ei și unde participați dumneavoastră. Etichetele și eligibilitatea sunt în [Tichete pentru preluare automată](/help/tickets).


Confirmați **Anulează**. Curățarea încearcă să elimine mediul și directorul de lucru, inclusiv modificările nepublicate; pot rămâne resurse. Starea și dovezile rămân. Ștergerea este separată.

Deschide **Acțiuni job**, lângă etapa curentă, pentru **Reîncearcă**, **Anulează** sau recuperarea confirmată într-un job nou, când sunt disponibile. Apar doar comenzile permise pentru acest job.

Pornirea este confirmată după admiterea durabilă și preluarea lucrării de către serviciu. Lucrarea are apoi propriul progres și rezultat. O comandă în coadă sau în curs nu confirmă singură admiterea. Anularea este confirmată numai după oprirea lucrării cu un rezultat de anulare salvat. Punerea cererii în coadă sau trimiterea semnalului de oprire nu confirmă anularea. Dacă rezultatul este incert, verifică lucrarea înainte de reluare.

Fiecare proiect are o singură limită de lucrări simultane, comună pornirii, reîncercării, repornirii de la zero și reluării. Pauza monitorizării oprește preluarea automată și păstrează pornirea explicită. Reducerea limitei lasă lucrările existente să continue. Comenzile în coadă și așteptările stabilizate de clarificare, aprobare sau review nu ocupă un executor; inițializarea și curățarea păstrează locul până la eliberarea sigură. Așteptarea înainte de execuție nu consumă timp de lucru activ.

Lucrările simultane au dosare de lucru, resurse, credențiale și ieșiri separate. Anularea uneia lasă celelalte lucrări active. Actualizările comune pot aștepta; agenții cu resurse pregătite continuă.

Proiectele progresează independent. La limita de două, două lucrări pot rula împreună, iar următoarea pornire așteaptă un loc. Oprirea aplicației oprește lucrătorii și joburile; munca întreruptă cu rezultat incert cere verificare înainte de o reîncercare explicită.

## Etape {#stages}

ADORE parcurge etapele AEGIS pe rând, fiecare încercare într-o sesiune nouă de executor. Executorii nu fac niciodată push, nu deschid un MR/PR și nu integrează.

| Etapă | Ce se întâmplă |
|---|---|
| Încadrare | Se stabilește domeniul, iar executorul înregistrează dacă lucrarea urmează calea completă sau cea rapidă. |
| Specificare | Se scrie cerința. |
| Proiectare | Se scrie o notă scurtă de proiectare pentru lucrările netriviale. |
| Construire | Agentul implementează tichetul și alege verificările potrivite conform instrucțiunilor repository-ului. |
| Validare | Agentul raportează verificările conform instrucțiunilor repository-ului, inclusiv cele rezervate CI și nerulate local, și închide task-ul AEGIS. ADORE urmărește finalizarea fără să reia testele. |

Calea rapidă parcurge Încadrare, Construire și Validare. După Validare, lucrarea afișează etapa **Finalizată** cât timp așteaptă aprobarea, este publicată și se află în revizie umană. AEGIS poate reveni la orice etapă anterioară de pe calea aleasă, inclusiv din Proiectare în Specificare. ADORE salvează etapa și continuă într-o sesiune nouă, în limitele existente. O sarcină finalizată revine la Validare când este necesară o verificare nouă. O etapă primește implicit trei încercări eșuate (**Încercări eșuate permise per etapă**).

## Joburi directe {#direct-evidence}

Lista și pagina jobului arată **Flux de lucru**: **AEGIS** sau **Direct**, conform înregistrării jobului. Un job direct folosește **Implementare** (`build`), **Validare** (`validate`), apoi **Finalizată**. Nu are Încadrare, Specificare, Proiectare sau task AEGIS. Cronologia arată numai evenimente salvate, nu pași presupus terminați.

**Ultima încercare înregistrată** arată ultima lansare înregistrată a agentului. Fără una, apare **Încercare indisponibilă**. Agentul raportează testele și verificările; ADORE nu le execută independent.

**Implementare** directă folosește limita `build` din `workflow.stage_timeout_overrides`, cu revenire la `budgets.per_gate_timeout_seconds`. **Validare** (`validate`) înregistrează candidatul pentru aprobare fără o comandă de test separată.

## Clarificare {#clarification}

Când executorul are nevoie de informații, ADORE postează un comentariu pe tichet, „Clarification required for stage” (în engleză, așa cum îl publică ADORE), care listează întrebările, și setează `agent-clarify`. Lucrarea afișează **Așteaptă clarificări**, iar detaliile ei oferă **Răspunde pe tichet**. Alege **Citește întrebarea** pentru a deschide **Întrebarea agentului**, apoi **Răspunde pe tichet** când există un loc înregistrat.

Răspundeți cu un comentariu obișnuit pe tichet, apoi adăugați `agent-answered`. Ambele sunt necesare; comentariile ADORE nu contează. ADORE elimină ambele etichete și reia lucrul. Întrebările nu se numără ca încercări eșuate. **Numărul maxim de runde de întrebări** (3 implicit) limitează de câte ori poate întreba o lucrare, iar **Timpul acordat unui răspuns uman** (72 de ore implicit) face lucrarea să eșueze când expiră.

## Aprobare {#approval}

Aprobarea umană înainte de publicare este activată implicit. Administratorii pot modifica **Cere aprobare umană înainte de PR/MR** în Setări. Când este dezactivată, ADORE verifică actualitatea candidatului și a țintei înainte de publicare; testele repository-ului rămân responsabilitatea agentului.

Când agentul încheie fluxul, ADORE înregistrează candidatul, elimină eticheta veche de aprobare și cere o nouă aprobare umană. Verificările din jurnal sunt raportate de agent.

Revizuiți-l, apoi adăugați din nou `agent-approved`; contează doar o adăugare nouă. Aprobarea este legată de acel candidat și de commit-ul ramurii țintă. Dacă oricare dintre ele se schimbă, aprobarea devine nulă, iar ADORE integrează, validează și cere din nou aprobarea. Această așteptare nu are temporizator. Detaliile lucrării oferă **Verifică versiunea pe platforma Git**.

Când opțiunea este dezactivată, ADORE verifică candidatul validat și ținta, apoi publică fără a aștepta eticheta. ADORE nu face merge.

## Publicare și revizuire {#review}

După validare și aprobarea necesară, ADORE face push ramurii și deschide MR/PR-ul către ramura țintă, cere review de la conturile din **Solicită review de la** și setează `agent-mr`. **Starea PR/MR la publicare** alege Draft (implicit) sau Pregătit pentru review. Lucrarea afișează **Publicare**, apoi **Revizie umană**. ADORE nu integrează niciodată. După ce o persoană integrează, ADORE setează `agent-done`, lucrarea afișează **Finalizat**, iar implicit ramura remote este ștearsă. Un MR/PR închis fără integrare face lucrarea să eșueze.

Pentru a cere modificări, un recenzor adaugă `agent-revise` pe MR/PR. ADORE elimină eticheta, pornește lucru nou pe aceeași ramură (un task nou pentru AEGIS) și repetă validarea și o nouă aprobare înainte de push. **Numărul maxim de runde de revizie** (5 implicit) limitează acest proces. O cerere peste limită face lucrarea să eșueze.

Dacă verificările CI eșuează pe MR/PR, decide **Acțiune când verificările CI ale PR/MR eșuează**: Reparare automată (implicit) pornește o revizie, Doar notificare postează un comentariu, iar Ignoră sare peste starea CI. Reparările automate consumă același buget de revizii; după epuizare, ADORE postează o notificare, iar lucrarea rămâne în revizuire.

## Eșec și recuperare {#failures}

Când o etapă eșuează, ADORE ține la zi un singur comentariu de incident pe tichet, cu etapa, încercarea, codul erorii, dovezile și următoarea acțiune; dacă agentul s-a oprit fără să avanseze etapa, dovezile arată și ultimele lui linii de ieșire de eroare. După ultima încercare postează un comentariu final, setează `agent-failed`, oprește containerul, păstrează worktree-ul și eliberează locul. Alte cauze sunt un timp de răspuns expirat, un tichet sursă șters și o limită depășită, precum costul sau fișierele modificate. Închiderea tichetului sursă cât timp o lucrare așteaptă o anulează.

În Lucrări, o lucrare eșuată afișează **Eșuate**, iar detaliile ei explică faptul că dovezile de recuperare sunt păstrate. **Reîncearcă** cere workerului să recupereze lucrarea; nu ocolește validarea sau aprobarea cerută. În vizualizarea Tichete, Reia înlocuiește Pornește. Eliminarea `agent-failed` nu reîncearcă. **Anulează** apare pentru lucrările neterminate și cere workerului să se oprească și să curețe. Lucrările încheiate nu pot fi anulate. Administratorii și dezvoltatorii atribuiți le pot folosi pe ambele. O comandă din coadă își arată progresul, de exemplu Comandă în coadă sau Comandă terminată. O comandă eșuată sau incertă spune și motivul, când motorul îl numește, și arată ultimele linii ale motorului.

Pentru lucrările locale, **Reia** verifică executorul instalat și acceptă actualizarea executabilului sau a mediului moștenit pe același calculator și cont. Păstrează sarcina, worktree-ul, ramura, istoricul și limitele cumulative. Monitorizarea automată nu face această revalidare. Setările de execuție schimbate sau dovezile de recuperare corupte trebuie corectate. Dacă repornirea eșuează, comanda apare eșuată cu motivul salvat: executabil lipsă, versiune invalidă, comandă eșuată sau expirarea timpului. Verificarea versiunii nu trimite cereri modelului; folosește **Testează conexiunea IA** pentru aceasta.

Când o comandă în container depășește limita de timp, ADORE oprește containerul înaintea altei comenzi. Următoarea încercare permisă reia același container, cu dependențele și fișierele instalate; accesul la rețea rămâne neschimbat. Dacă oprirea sau repornirea sigură nu poate fi confirmată, lucrarea eșuează și păstrează dovezile pentru verificare înainte de **Reia**. Pregătirea eșuată păstrează procedura sa explicită de recuperare.

## Renunță și pornește din nou {#restart}

Pentru un job eșuat, **Renunță și pornește din nou** șterge starea salvată, worktree-ul cu lucrul nepublicat și branchul remote propriu nemodificat. Citește avertismentul și confirmă. ADORE verifică proprietatea înainte de curățare și pornește același tichet deschis cu setările curente doar după curățarea completă. Monitorizarea rămâne în pauză dacă era oprită. Administratorii și dezvoltatorii alocați pot folosi acțiunea.

Reîncercarea nu poate corecta mediul de execuție sau setările stabile schimbate; detaliile jobului explică situația și oferă acțiunea confirmată. Restabilește setările salvate pentru a păstra lucrul existent. Reîncercarea poate revalida schimbările volatile ale mediului nativ, inclusiv variabilele procesorului după redimensionarea unui VM.

Resursele străine, alt calculator sau cont, dovezile de proprietate corupte ori un branch remote modificat blochează recuperarea. Curățarea parțială păstrează dovezile rămase fără un job nou. Dacă jobul se schimbă după confirmare, reîncarcă detaliile și verifică din nou. Lockul CLI poate aparține workerului web: pune monitorizarea în pauză din Rezumatul proiectului și așteaptă încheierea jobului limitat. Nu șterge un lock activ.

Dacă un job șters anterior a lăsat un branch fără checkpoint înregistrat, ADORE îl păstrează și folosește o generație nouă. Un checkpoint cunoscut modificat blochează în continuare recuperarea. Sunt încercate cel mult trei nume alternative, iar regulile depozitului trebuie să permită un nume liber; altfel recuperarea se oprește înainte de curățare. Rezultatul explică păstrarea unui branch vechi.

## Urmărirea lucrărilor {#following-jobs}

Folosiți **Lucrări** din bara laterală sau fila **Lucrări** a unui proiect, apoi sub-fila **Lucrări**. Tabelul are aceste coloane:

| Coloană | Conținut |
|---|---|
| Tichet | Numărul și titlul; deschide detaliile lucrării. |
| Proiect | Proiectul căruia îi aparține. |
| Stare | Starea, Flux de lucru înregistrat, Etapa curentă și un link către tichet sau MR/PR când o persoană trebuie să acționeze. |
| Ultima activitate | Momentul ultimului eveniment salvat. |
| Consum | Tokenurile folosite de lucrare. |

Faceți clic pe un antet de coloană pentru a sorta. **Caută joburi** potrivește titluri, numere, proiecte, ID-uri de lucrare, stare, etapă sau rezultat. Filtrul **Stare** oferă Lucrări active, În așteptare, Revizie umană și Joburi încheiate. Pagina se reîmprospătează singură cât timp este vizibilă.

Detaliile înlocuiesc lista cât timp sunt deschise. Antetul compact reunește numărul și numele tichetului. **Ce se întâmplă acum** arată starea, cine acționează și **Pasul următor**. Bugetele și Consumul sunt alături pe ecrane late și dedesubt pe ecrane înguste. **Activitate** listează evenimentele salvate de la cel mai recent. **Întrebarea agentului** conține clarificarea activă; celelalte stări arată **Dovezi și artefacte**. **Detalii tehnice** conține identificatori, ieșirea executorului și **Evenimentele originale înregistrate**, care pot fi extinse. **Închide** revine la listă cu filtrele păstrate. Evenimentele trecute nu devin cereri curente de acțiune.

## Bugetele jobului {#budgets}

Detaliile afișează **Lansări executor** (de exemplu 9 / 20) și **Lucru activ (secunde)** lângă limitele actuale ale proiectului, independent de statisticile de tokenuri. La 90% apare avertizarea de apropiere; la limită se cere majorarea înainte de reluare. Limita implicită este 20 în înrolare și `adore init`.

Administratorii pot urma **Ajustează bugetele în Setările proiectului**, deschide **Implementare**, modifica doar bugete, alege **Salvează** și confirma valorile exacte. Salvarea revizuită numai a bugetelor este permisă când joburile așteaptă clarificări, fără conductor activ sau operații neterminate. Celelalte setări păstrează verificările obișnuite de repaus și pauză; dezvoltatorii au acces doar la citire.

Bugetele sunt recitite înaintea fiecărei încercări, inclusiv la reluare și reîncercare. Încercarea în curs își păstrează limita de timp. Lucrul activ se cumulează între reîncercări, răspunsuri și revizii; așteptarea este exclusă. Majorarea păstrează consumul, taskul și progresul salvat. Un job eșuat prin epuizarea bugetului cere în continuare **Reia** după ajustare. Configurația nevalidă sau lipsă oprește încercările următoare până la corectare.

Dacă limitele actuale nu pot fi citite, detaliile păstrează consumul salvat, dovezile și acțiunile de recuperare. Limitele arată — cu un mesaj explicit de indisponibilitate; nu se presupune o valoare implicită. Corectează configurația înainte de o nouă execuție.

## Stare și dovezi ale executorului {#operational-evidence}

**În lucru** înseamnă că ADORE conduce etapa salvată; momentan nu se cere intervenția unui om. **Așteaptă clarificare** necesită un răspuns pe tichet. **Eșuat** oprește lucrul autonom și păstrează dovezile de recuperare. Cardul afișează încercările eșuate ale etapei curente chiar când jobul rămâne În lucru.

Întrebările apar în **Întrebarea agentului** ca Markdown cu liste, tabele și cod. Comentariile HTML de la început sunt omise din vizualizarea lizibilă; **Întrebarea originală și dovezile** păstrează sursa exactă. Restul HTML rămâne text, linkurile nesigure sunt inactive și imaginile nu se încarcă automat. Tabelele late și codul se derulează în interiorul întrebării.

Etapele cronologiei provin din etapa, contextul de etapă sau destinația tranziției salvate în fiecare eveniment; evenimentele fără legătură rămân necunoscute. Orele includ secunde. Un eveniment este o dovadă salvată, nu progres în timp real.

În **Detalii tehnice**, alege **Vezi ultima ieșire a executorului**. Sunt afișate ieșirile operaționale capturate de host pentru ultima lansare încheiată, inclusiv modulele lipsă și totalurile testelor. Prompturile, raționamentul, scripturile, configurația, căile, credențialele și datele financiare sunt ascunse. Ieșirile necunoscute devin o notificare sau o categorie de diagnostic. Se păstrează cel mult ultimele 500 de diagnostice pe flux, în 64 KiB.

Rezumatul arată încercarea, ora înregistrării, rezultatul și codul de ieșire. Extinde **stdout** sau **stderr** când au înregistrări. Dacă o lansare este în curs, panoul o semnalează și păstrează ultima ieșire finalizată. Dacă jurnalul se schimbă în timpul citirii, alege **Reîncearcă**. Ultima ieșire verificată este marcată ca posibil neactualizată.

O lansare fără captură dovedită sau cu snapshotul șters este explicit indisponibilă; arhivele brute nu sunt citite ca alternativă. Dovezile corupte sunt refuzate. Joburile existente pot rămâne fără ieșire până la o lansare ulterioară; această vizualizare nu pornește niciuna.

Dacă **Consum** nu se încarcă, folosește **Actualizează consumul** lângă eroare. Dovezile și recuperarea rămân separate. O sursă coruptă necesită în continuare investigarea operatorului.


## Capacitatea proiectului {#project-capacity}

**Capacitatea proiectului** din Rezumat și Lucrări arată limita efectivă, locurile ocupate/libere, joburile în coadă și cauza: limita proiectului, worker indisponibil, operație pe același job sau limita redusă pregătită. Coada numără cererile trimise și joburile admise care așteaptă lansarea, nu tichetele nesolicitate. Un proiect plin nu le blochează pe celelalte. **Ultimele tale operații** recuperează rezultatele salvate pentru Pornește, Reîncearcă, Anulează și setări după navigare ori reîncărcare. În coadă și În desfășurare nu înseamnă Confirmat.

O limită redusă pregătită oprește deja pornirile și reluările noi până când ocuparea scade sub ea; joburile deja pornite continuă; rezervările în coadă așteaptă un loc de execuție. Nu mărește niciodată limita activă. Aplicarea sigură așteaptă în continuare lucrul neterminat; valoarea salvată și candidatul rămân vizibile până la Salvează sau Renunță la modificări.
