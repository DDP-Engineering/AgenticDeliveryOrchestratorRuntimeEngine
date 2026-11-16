# Ciclul de viață al lucrării

O lucrare este munca pe care o face ADORE pentru un tichet, de la preluare până la o modificare integrată. Acest articol arată etapele ei și unde participați dumneavoastră. Etichetele și eligibilitatea sunt în [Tichete pentru preluare automată](/help/tickets).


Confirmați **Anulează**. Curățarea încearcă să elimine mediul și directorul de lucru, inclusiv modificările nepublicate; pot rămâne resurse. Starea și dovezile rămân. Ștergerea este separată.

Deschide **Acțiuni job**, lângă etapa curentă, pentru **Reîncearcă**, **Anulează** sau recuperarea confirmată într-un job nou, când sunt disponibile. Apar doar comenzile permise pentru acest job.

Pornirea este confirmată după admiterea durabilă și preluarea lucrării de către serviciu. Lucrarea are apoi propriul progres și rezultat. O comandă în coadă sau în curs nu confirmă singură admiterea. Anularea este confirmată numai după oprirea lucrării cu un rezultat de anulare salvat. Punerea cererii în coadă sau trimiterea semnalului de oprire nu confirmă anularea. Dacă rezultatul este incert, verifică lucrarea înainte de reluare.

Fiecare proiect are o singură limită de lucrări simultane, comună pornirii, reîncercării, repornirii de la zero și reluării. Pauza monitorizării oprește preluarea automată și păstrează pornirea explicită. Reducerea limitei lasă lucrările existente să continue. Comenzile în coadă și așteptările stabilizate de clarificare, aprobare sau review nu ocupă un executor; inițializarea și curățarea păstrează locul până la eliberarea sigură. Așteptarea înainte de execuție nu consumă timp de lucru activ.

Lucrările simultane au dosare de lucru, resurse, credențiale și ieșiri separate. Anularea uneia lasă celelalte lucrări active. Actualizările comune pot aștepta; agenții cu resurse pregătite continuă.

Proiectele progresează independent. La limita de două, două lucrări pot rula împreună, iar următoarea pornire așteaptă un loc. Oprirea aplicației oprește lucrătorii și joburile; munca întreruptă cu rezultat incert cere verificare înainte de o reîncercare explicită.

După reducerea limitei, lucrările admise care nu au început așteaptă un loc conform noii limite. Lucrările deja în execuție continuă, chiar peste limita redusă, iar curățarea păstrează locul până la eliberarea sigură. Setările altui proiect și administrarea serverului rămân disponibile.

## Etape {#stages}

ADORE parcurge etapele AEGIS pe rând, fiecare încercare într-o sesiune nouă de executor. Executorii nu fac niciodată push, nu deschid un MR/PR și nu integrează.

| Etapă | Ce se întâmplă |
|---|---|
| Încadrare | Se stabilește domeniul, iar executorul înregistrează dacă lucrarea urmează calea completă sau cea rapidă. |
| Specificare | Se scrie cerința. |
| Proiectare | Se scrie o notă scurtă de proiectare pentru lucrările netriviale. |
| Construire | Agentul implementează tichetul și alege verificările potrivite conform instrucțiunilor repository-ului. |
| Validare | Agentul raportează verificările conform instrucțiunilor repository-ului, inclusiv cele rezervate CI și nerulate local, și închide task-ul AEGIS. ADORE urmărește finalizarea fără să reia testele. |

Calea rapidă parcurge Încadrare, Construire și Validare. După Validare, lucrarea afișează etapa **Finalizată** cât timp așteaptă aprobarea, este publicată și se află în revizie umană. AEGIS poate reveni la orice etapă anterioară de pe calea aleasă, inclusiv din Proiectare în Specificare. ADORE salvează etapa și continuă în aceeași conversație a jobului, în limitele existente. O sarcină finalizată revine la Validare când este necesară o verificare nouă. O etapă primește implicit trei încercări eșuate (**Încercări eșuate permise per etapă**).

## Joburi directe {#direct-evidence}

Lista și pagina jobului arată **Flux de lucru**: **AEGIS** sau **Direct**, conform înregistrării jobului. Un job direct folosește **Implementare** (`build`), **Validare** (`validate`), apoi **Finalizată**. Nu are Încadrare, Specificare, Proiectare sau task AEGIS. Cronologia arată numai evenimente salvate, nu pași presupus terminați.

**Ultima încercare înregistrată** arată ultima lansare înregistrată a agentului. Fără una, apare **Încercare indisponibilă**. Agentul raportează testele și verificările; ADORE nu le execută independent.

**Implementare** directă folosește limita `build` din `workflow.stage_timeout_overrides`, cu revenire la `budgets.per_gate_timeout_seconds`. **Validare** (`validate`) înregistrează candidatul pentru aprobare fără o comandă de test separată.

## Clarificare {#clarification}

Când executorul cere informații, ADORE publică pe tichet un comentariu de clarificare cu întrebările și adaugă `agent-clarify`. Jobul arată așteptarea clarificării. **Citește întrebarea** deschide întrebarea în **Detalii job**, iar **Răspunde pe tichet** folosește locația salvată.

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

Joburile în container păstrează imaginea și resursa alese la pornire, chiar fără pregătire. Dacă resursa este înlocuită, pornește un job nou. Pregătirea rămâne opțională.

## Renunță și pornește din nou {#restart}

Pentru un job eșuat, **Renunță și repornește cu AEGIS** sau **Renunță și repornește fără AEGIS** șterge starea salvată, worktree-ul cu lucrul nepublicat și branchul remote propriu nemodificat. Citește avertismentul și confirmă. ADORE verifică proprietatea înainte de curățare și pornește același tichet deschis cu setările curente doar după curățarea completă. Monitorizarea rămâne în pauză dacă era oprită. Administratorii și dezvoltatorii alocați pot folosi acțiunea.

Reîncercarea nu poate corecta mediul de execuție sau setările stabile schimbate; detaliile jobului explică situația și oferă acțiunea confirmată. Restabilește setările salvate pentru a păstra lucrul existent. Reîncercarea poate revalida schimbările volatile ale mediului nativ, inclusiv variabilele procesorului după redimensionarea unui VM.

Resursele străine, alt calculator sau cont, dovezile de proprietate corupte ori un branch remote modificat blochează recuperarea. Curățarea parțială păstrează dovezile rămase fără un job nou. Dacă jobul se schimbă după confirmare, reîncarcă detaliile și verifică din nou. Lockul CLI poate aparține workerului web: pune monitorizarea în pauză din Rezumatul proiectului și așteaptă încheierea jobului limitat. Nu șterge un lock activ.

Dacă un job șters anterior a lăsat un branch fără checkpoint înregistrat, ADORE îl păstrează și folosește o generație nouă. Un checkpoint cunoscut modificat blochează în continuare recuperarea. Sunt încercate cel mult trei nume alternative, iar regulile depozitului trebuie să permită un nume liber; altfel recuperarea se oprește înainte de curățare. Rezultatul explică păstrarea unui branch vechi.

## Urmărirea lucrărilor {#following-jobs}

Citirile automate păstrează rândurile, consumul, comenzile tabelului și detaliile lucrării deschise. **Reîmprospătează** folosește aceeași citire în fundal; **Ultima actualizare reușită** arată când s-a încheiat. O eroare temporară de conexiune a listei sau a consumului poate păstra instantaneul anterior cu un avertisment de învechire și **Reîncearcă**. Dovezile invalide sau un instantaneu expirat al paginării cer în continuare recuperare ori reîncărcarea primei pagini; informațiile învechite nu autorizează acțiuni asupra lucrării.

Folosește **Lucrări** din meniul lateral sau fila separată **Lucrări** a proiectului. Tabelul are următoarele coloane:

| Coloană | Conținut |
|---|---|
| Tichet | Numărul și titlul; deschide detaliile lucrării. |
| Proiect | Proiectul căruia îi aparține. |
| Stare | Starea, Flux de lucru înregistrat, Etapa curentă și un link către tichet sau MR/PR când o persoană trebuie să acționeze. |
| Ultima activitate | Momentul ultimului eveniment salvat. |
| Consum | Tokenurile folosite de lucrare. |

Faceți clic pe un antet de coloană pentru a sorta. **Caută joburi** potrivește titluri, numere, proiecte, ID-uri de lucrare, stare, etapă sau rezultat. Filtrul **Stare** oferă Lucrări active, În așteptare, Revizie umană și Joburi încheiate. Pagina se reîmprospătează singură cât timp este vizibilă.

Detaliile înlocuiesc lista din care au fost deschise. Deasupra titlului sunt **Activitate**, **Sesiunile agentului** și **Detalii job**, cu **Arată tichetul** și **Închide** în dreapta. Statusul, etapa și workflow-ul sunt sub titlu. Bugetele și consumul ocupă coloana din dreapta. Acțiunile necesare pentru întrebare, aprobare și review rămân vizibile. **Închide** restaurează pagina, selecția proiectului, căutarea, filtrele și paginarea.

**Activitate** este un tabel paginat cu ora, activitatea, etapa și sesiunea. Alege 10, 25, 50 sau Toate și folosește Anterior/Următor. **Deschide conversația** deschide sesiunea exactă atunci când etapa și încercarea identifică o singură lansare înregistrată; evenimentele fără o asociere sigură nu au legătură. Revenirea păstrează pagina. Bugetele și consumul sunt în coloana din dreapta, sub conținut pe ecrane înguste.

## Istoricul sesiunilor agentului {#agent-sessions}

**Sesiunile agentului** deschide sesiunea curentă sau ultima sesiune încheiată. Conversația arată promptul inițial, răspunsurile agentului, mesajele utilizatorului și apelurile/rezultatele instrumentelor care pot fi extinse. Răspunsurile folosesc Markdown lizibil. Mesajele apar direct, cu un singur autor; raționamentul și instrumentele pot fi extinse. Consumul rămâne în panoul din dreapta.

Pi păstrează o conversație de implementare pentru job între etape, continuări și corecții. Procesele pot reporni la checkpointuri; conversația se reia cu contextul și compactarea automată Pi. Selectorul arată în continuare încercările înregistrate, fiecare cu activitatea și consumul propriu. Revizuirile independente folosesc contexte separate când politica repository-ului le cere.

Sesiune, selectorul și activitatea în direct sunt pe același rând, deasupra conversației, aliniate cu lățimea acesteia. Conversația folosește înălțimea disponibilă și se derulează în interior când apar mesaje noi. Butoanele de trimitere sunt în dreapta câmpului pe ecrane late și sub el pe ecrane înguste.

Istoricul se încarcă progresiv fără scurtarea textului păstrat. Mesajele noi sunt urmărite automat doar când ești la final; **Mesaje noi** te aduce înapoi. Selectorul păstrează celelalte încercări, iar **Sesiunea curentă** revine la lucrul în direct.

Lansările noi păstrează explicit prompturile trimise și ora mesajelor. Sesiunile vechi arată doar ce a fost înregistrat. Drepturile administratorilor și dezvoltatorilor alocați rămân aceleași; costurile structurate rămân doar pentru administratori.

**Maximizează** folosește toată pagina pentru sesiune. **Restabilește** sau Escape revine la afișarea normală. Sesiunea selectată, mesajele și mesajul netrimis se păstrează.

### Trimiterea instrucțiunilor {#instructions}

Introdu un **Mesaj pentru agent** la baza conversației curente. **Trimite acum** îl transmite la următorul punct sigur al agentului; **Pune mesajul în așteptare** așteaptă încheierea lucrului curent. Între sesiuni, punerea în așteptare rămâne disponibilă cât timp jobul lucrează. Conversațiile istorice sunt doar pentru citire.

Mesajul apare în conversație cu **În așteptare**, **Primit de agent** sau eroare. Primit confirmă recepția, nu finalizarea lucrului. Erorile de introducere sunt explicate la trimitere: 1–4000 de caractere fără NUL și cel mult 256 de instrucțiuni păstrate pe job.

Instrucțiunile neconfirmate rămân în așteptare pentru o sesiune ulterioară. Primirea confirmată este salvată în job și publicată pe tichet; erorile temporare ale comentariului sunt reîncercate separat.

## Bugetele jobului {#budgets}

Detaliile afișează **Lansări executor** (de exemplu 9 / 20) și **Lucru activ (secunde)** lângă limitele actuale ale proiectului, independent de statisticile de tokenuri. La 90% apare avertizarea de apropiere; la limită se cere majorarea înainte de reluare. Limita implicită este 20 în înrolare și `adore init`.

Administratorii pot urma **Ajustează bugetele în Setările proiectului**, deschide **Implementare**, modifica doar bugete, alege **Salvează** și confirma valorile exacte. Salvarea revizuită numai a bugetelor este permisă când joburile așteaptă clarificări, fără conductor activ sau operații neterminate. Celelalte setări păstrează verificările obișnuite de repaus și pauză; dezvoltatorii au acces doar la citire.

Bugetele sunt recitite înaintea fiecărei încercări, inclusiv la reluare și reîncercare. Încercarea în curs își păstrează limita de timp. Lucrul activ se cumulează între reîncercări, răspunsuri și revizii; așteptarea este exclusă. Majorarea păstrează consumul, taskul și progresul salvat. Un job eșuat prin epuizarea bugetului cere în continuare **Reia** după ajustare. Configurația nevalidă sau lipsă oprește încercările următoare până la corectare.

Dacă limitele actuale nu pot fi citite, detaliile păstrează consumul salvat, dovezile și acțiunile de recuperare. Limitele arată — cu un mesaj explicit de indisponibilitate; nu se presupune o valoare implicită. Corectează configurația înainte de o nouă execuție.

## Detalii job și diagnostic {#operational-evidence}

**Detalii job** arată o singură dată rezultatul salvat, **Branch**, **Ultimul commit publicat** când există, legătura MR/PR și rundele de review separat. Un branch absent apare ca **Neînregistrat**. Commitul publicat este ultimul checkpoint trimis și verificat, nu amprenta unui candidat.

Când este necesară clarificarea, **Citește întrebarea** deschide această filă. Întrebarea folosește Markdown lizibil, legăturile nesigure sunt inactive și imaginile nu sunt încărcate automat. Acțiunile de răspuns, aprobare și review rămân vizibile lângă status când sunt necesare. Întrebarea originală este în **Diagnostic**.

**Diagnostic** este inițial restrâns. Deschide-l pentru identificatorii interni ai proiectului și jobului, **Încercări eșuate în etapa curentă**, dovezi ale încercării directe sau pregătirii și ultima ieșire a executorului. Rundele de review sunt separate de erorile etapei curente.

**Date indisponibile** numește tichetul, istoricul, titlul sau ora activității doar când aceste surse lipsesc. Acestea descriu dovezile disponibile, nu consumul de tokenuri. Consumul rămâne în dreapta.

Ultima ieșire a executorului prezintă stdout/stderr operaționale normalizate, cu ora, încercarea, etapa și codul de ieșire. Conținutul privat este ascuns; sunt păstrate cel mult 500 de înregistrări în 64 KiB pe flux. Dovezile lipsă sau corupte sunt semnalate, iar datele modificate oferă Reîncearcă.

**Activitate** este singurul tabel de evenimente. Codul publicat este accesibil prin legătura MR/PR. Detaliile folosesc dovezile salvate fără să creeze fișiere sau să pornească executorul.

## Capacitatea proiectului {#project-capacity}

**Rezumat** arată limita lucrărilor paralele, locurile libere și lucrările în așteptare alături de informațiile operaționale. Lucrări și Tichete sunt file separate în proiect, fără subfilă Capacitate. Pagina globală Lucrări păstrează tabelul Capacitate cu limite, locuri libere, coadă, monitorizare și paginarea existentă.

Coada numără cererile trimise și joburile admise care așteaptă lansarea, nu tichetele necerute. Un proiect ocupat nu blochează alte proiecte. Setările păstrează **Ultimele tale operații** și rezultatele salvate; În coadă și În desfășurare nu înseamnă Confirmat.

O limită redusă pregătită oprește deja pornirile și reluările noi până când ocuparea scade sub ea; joburile deja pornite continuă; rezervările în coadă așteaptă un loc de execuție. Nu mărește niciodată limita activă. Aplicarea sigură așteaptă în continuare lucrul neterminat; valoarea salvată și candidatul rămân vizibile până la Salvează sau Renunță la modificări.

## Alegerea fluxului de lucru {#workflow-choice}

În **Acțiuni job**, alegeți **Renunță și repornește cu AEGIS** sau **Renunță și repornește fără AEGIS** pentru un job nou, apoi acceptați confirmarea scurtă a browserului privind ștergerea lucrului existent. Lipsa AEGIS dezactivează acea acțiune. Tichetele păstrează selectorul **Flux de lucru** înainte de **Pornește**. Reîncercarea, continuarea și corecțiile de review păstrează fluxul salvat și aceeași conversație Pi.
