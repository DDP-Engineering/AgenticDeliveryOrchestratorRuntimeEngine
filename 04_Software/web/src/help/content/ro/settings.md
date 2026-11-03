# Setările proiectului

Fila Setări a unui proiect listează regulile de lucru pe care ADORE le aplică: ce tichete preia, limitele, cum publică și ce agent folosește. Administratorii le modifică printr-un flux revizuit, o setare pe rând; dezvoltatorii le citesc.

## Unde găsiți Setările {#where}

Deschideți [Proiecte](/projects), alegeți un proiect și selectați fila **Setări**. Filele sunt Rezumat, Setări, Lucrări, Statistici, Istoric și, pentru administratori, Acces.

Administratorii pot edita. Dezvoltatorii cu acces la proiect văd **Setări doar pentru citire**, fără butoane Modifică și fără secrete sau setări financiare. Fiecare proiect are propriile setări; capacitatea globală și păstrarea auditului aparțin Administrării. Setări nu se reîmprospătează singure, așa că folosiți Reîmprospătează din antet pentru a le citi din nou.

## Grupuri de setări {#groups}

Fiecare grup este închis când deschideți Setări, iar numărul de lângă numele lui numără rândurile sale.

| Grup | Ce controlează |
|---|---|
| Repository | Forge-ul și repository-ul, login-ul Gitea, **Ramura de integrare** (baza lucrărilor noi și destinația PR/MR-urilor), șablonul numelui ramurii lucrării, cu o regulă opțională de denumire și un exemplu în timp real, precum și numele afișat al agentului, numele resursei și e-mailul autorului commit-urilor. |
| Tichete | **Eticheta pentru preluare**, **Eticheta de excludere de la preluare**, **Etichete de stare** (pliate), cât de des verifică ADORE forge-ul, dacă tichetele cer criterii de acceptare sau o etichetă de prioritate și tipul implicit de sarcină. Vezi [Tichete pentru preluare automată](/help/tickets#labels). |
| Implementare | Limite per lucrare: **Limita lucrărilor active**, **Numărul maxim de lansări ale executorului per job**, **Limita timpului de lucru activ (secunde)**, **Plafonul costului jobului (USD)**, **Numărul maxim de fișiere modificate per job** și **Limita timpului pentru o încercare de etapă (secunde)**. Conține și **Clarificări**, **Recuperare după erori**, **Limite avansate de timp pe etapă**, **Publică commituri de progres** și eticheta de sugestie pentru traseul rapid. |
| PR/MR și review | **Solicită review de la**, **Starea PR/MR la publicare** (Draft sau Pregătit pentru review), eticheta de aprobare, **Șterge ramura după integrarea făcută de o persoană**, rundele de revizie și **Acțiune când verificările CI ale PR/MR eșuează** (Reparare automată, Doar notificare sau Ignoră). |
| Statistici | **Înregistrează măsurătorile lucrărilor finalizate** și **Înregistrează tokenurile raportate de agent**. **Fișierul bazei de date pentru statistici** este afișat doar cu titlu informativ. |
| Agent și model | Modelul, comanda de lansare, autentificarea și **Testează conexiunea AI**. Vezi [Executori și modele](/help/executors). |
| Detalii tehnice | Valori de instalare doar pentru citire, precum dosarul de stare al lucrărilor, calea repository-ului local și folderele de lucru ale lucrărilor. Se modifică în `config.toml` al proiectului, pe server, iar schimbarea unei căi nu mută datele existente. |

## Valori și ajutor {#values}

Fiecare rând are o etichetă, o descriere mereu vizibilă, o **Valoare activă** și o **Valoarea implicită ADORE**. Descrierea spune ce controlează setarea, unitatea sau valorile permise și ce efect are modificarea, sau că este rezervată și nefolosită. Nu există un buton de ajutor separat.

O insignă **Implicit** înseamnă că `config.toml` al proiectului nu setează valoarea, deci se aplică valoarea implicită ADORE. Modificarea ei scrie o valoare doar pentru acest proiect. Un rând marcat **Nu se poate modifica aici** se modifică în `config.toml` pe server. Un rând marcat **Se aplică doar cu preluarea în pauză și fără lucrări active** are nevoie de condiția suplimentară descrisă mai jos.

Detectarea pornește automat când alegi execuția locală; schimbarea executorului folosește lista detectată. Deschide **Avansate** pentru **Detectează executorii instalați** dacă vrei să o reîmprospătezi. Pentru execuție locală, alege o instalare detectată sau introdu calea unui executabil; vezi [Detectarea executorilor instalați](/help/executors#installed-executors). Deschide **Avansate** pentru comanda completă, calea manuală a executabilului, suprascrierile directorului/PATH și delegarea cgroup Linux. Lasă directorul și PATH goale pentru valorile automate. PATH înseamnă directoare cu unelte, nu fișierul executabil. Numele contului din Setări doar verifică identitatea curentă, fără să schimbe utilizatorul.

## Modificarea {#editing}

1. Alegeți **Modifică** lângă valoarea activă, introduceți valoarea nouă și alegeți **Pregătește candidatul**. Aceasta scrie doar un candidat în așteptare; configurația activă rămâne neschimbată.
2. Panoul **Configurație în așteptare** apare deasupra grupurilor și listează doar valorile modificate. Un candidat care nu schimbă nimic nu poate fi aplicat. Deschideți **Detalii tehnice** pentru comparația completă, efect, ora pregătirii, ambele revizii și **Copiază recenzia fără secrete**. Valorile credențialelor sunt ascunse.
3. Alegeți **Aplică** pentru a-l trimite sau **Renunță la modificare** pentru a elimina doar candidatul.

Reguli care se aplică:

- O singură setare odată: celelalte butoane Modifică rămân dezactivate până când candidatul este aplicat sau eliminat.
- Revizuirea este legată de revizii. Aplicarea trimite reviziile de bază și de candidat revizuite, deci, dacă fișierul activ s-a schimbat între timp, trebuie să renunțați, să reîmprospătați și să pregătiți din nou. Doi administratori care editează simultan primesc un conflict, în loc să se suprascrie reciproc. Modificările făcute direct în fișierul de pe server ocolesc această protecție.
- La Aplică, serverul verifică din nou că nicio lucrare nu este activă și nicio operație nu este neterminată. O aplicare blocată păstrează candidatul și explică cum vă puteți recupera.
- Setările care schimbă identitatea sau mediul de execuție cer și monitorizarea în pauză. Alegeți **Pune monitorizarea în pauză** în Rezumat și lăsați lucrul activ să se încheie; punerea în pauză nu întrerupe o lucrare în curs.
- Valorile noi se aplică lucrărilor ulterioare. Lucrările existente își păstrează configurația.

Blocajele scurte ale fișierului pe Windows sunt reîncercate automat. Dacă setările tot nu pot fi salvate, propunerea verificată rămâne disponibilă: verificați accesul la fișier și reîncercați **Aplică**.

## TOML original {#toml}

Lângă titlul Setările proiectului, administratorii au **Previzualizare configurație originală** și **Descarcă configurația originală**. Previzualizarea deschide un dialog care se poate închide și păstrează textul doar în memorie. Descărcarea oferă `config.toml` salvat exact așa cum este stocat, cu comentarii, formatare și eventualele secrete inline, deci tratați-l ca pe un secret. Niciuna nu include un candidat în așteptare, valorile implicite rezolvate, fișiere `.env` separate sau credențiale externe. Dezvoltatorii nu le pot folosi. Un fișier descărcat poate fi înrolat din nou cu [Importă configurația proiectului](/help/projects#import-project) după ce secretele lui sunt înlocuite cu referințe la variabile de mediu.

## Pachetele de sistem ale agentului {#system-packages}

**Permite agentului instalarea pachetelor de sistem**

În Setări → Agent și model, administratorii activează separat permisiunea prin Pregătește candidatul și Aplică schimbarea. Implicit este oprită și apare pentru proiecte în container. Reconstruiți sau alegeți întâi o imagine compatibilă cu sudo, apoi porniți o lucrare nouă. Agentul execută direct comenzile, citește erorile și adaptează pașii în limitele lucrării.

Accesul la rețea rămâne separat: open permite sursele accesibile, allowlist-proxy domeniile HTTP/HTTPS permise, iar none numai sursele locale disponibile. Scripturile pachetelor au drepturi administrative în container; directoarele montate ale proiectului rămân partajate cu serverul. Pachetele de sistem se păstrează la reluarea aceluiași container; un container nou cere reevaluare și instalare.
