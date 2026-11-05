# Setările proiectului

Fila Setări a unui proiect listează regulile de lucru pe care ADORE le aplică: ce tichete preia, limitele, cum publică și ce agent folosește. Administratorii modifică mai multe setări și le salvează împreună; dezvoltatorii le citesc.

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
| Agent și model | Furnizorul, modelul, autentificarea și **Testează conexiunea AI** [Executori și modele](/help/executors). |
| Detalii tehnice | Valori de instalare doar pentru citire, precum dosarul de stare al lucrărilor, calea repository-ului local și folderele de lucru ale lucrărilor. Se modifică în `config.toml` al proiectului, pe server, iar schimbarea unei căi nu mută datele existente. |

## Valori și ajutor {#values}

Fiecare rând are o etichetă, o descriere mereu vizibilă, o **Valoare activă** și o **Valoarea implicită ADORE**. Descrierea spune ce controlează setarea, unitatea sau valorile permise și ce efect are modificarea, sau că este rezervată și nefolosită. Nu există un buton de ajutor separat.

O insignă **Implicit** înseamnă că `config.toml` al proiectului nu setează valoarea, deci se aplică valoarea implicită ADORE. Modificarea ei scrie o valoare doar pentru acest proiect. Un rând marcat **Nu se poate modifica aici** se modifică în `config.toml` pe server. Un rând marcat **Se aplică doar cu preluarea în pauză și fără lucrări active** are nevoie de condiția suplimentară descrisă mai jos.

Alegeți **Instalat pe server** pentru Pi administrat de ADORE sub contul curent al sistemului. **PATH pentru uneltele proiectului** selectează opțional directoarele cu unelte. Vedeți [Instalarea Pi pe server](/help/executors#installed-executors).

## Editare {#editing}

1. Alege **Editează** lângă fiecare valoare de modificat. Poți edita mai multe setări din grupuri diferite.
2. Folosește unicul buton **Salvează** deasupra grupurilor. Se activează doar când există valori schimbate și toate modificările sunt valide.
3. Pentru schimbări importante, **Confirmă modificările importante** arată proiectul, valorile schimbate și efectele. Alege **Salvează modificările**, sau **Continuă editarea** pentru a reveni fără salvare.

Reguli aplicabile:

- **Renunță la modificări** elimină toate editările nesalvate. Anularea confirmării le păstrează fără să creeze un candidat salvat.
- Salvarea este legată de configurația editată. O revizie depășită oprește salvarea și păstrează datele introduse; renunță și reîmprospătează înainte de o nouă editare. Modificările simultane produc un conflict.
- Serverul verifică întreaga configurație și salvează toate modificările împreună. Salvarea revizuită doar a bugetelor permite și joburi în așteptarea clarificărilor, fără conductor activ sau operații neterminate. Alte setări cer joburi încheiate. O eroare păstrează datele introduse și candidatul pregătit.
- Schimbările de identitate sau mediu cer și monitorizare în pauză. Alege **Pune monitorizarea în pauză** în Sumar și așteaptă terminarea lucrărilor active; pauza nu întrerupe un job.
- Bugetele se aplică înaintea următoarei încercări sau reluări și păstrează consumul și progresul. Vezi [Bugetele jobului](#budgets).

Navigarea sau Reîmprospătează cere confirmare înainte de a pierde modificările nesalvate. Blocajele scurte de fișier Windows sunt reîncercate automat; dacă salvarea eșuează, verifică accesul la fișier și reîncearcă **Salvează**.

## TOML original {#toml}

Lângă titlul Setările proiectului, administratorii au **Previzualizare configurație originală** și **Descarcă configurația originală**. Previzualizarea deschide un dialog care se poate închide și păstrează textul doar în memorie. Descărcarea oferă `config.toml` salvat exact așa cum este stocat, cu comentarii, formatare și eventualele secrete inline, deci tratați-l ca pe un secret. Niciuna nu include un candidat în așteptare, valorile implicite rezolvate, fișiere `.env` separate sau credențiale externe. Dezvoltatorii nu le pot folosi. Un fișier descărcat poate fi înrolat din nou cu [Importă configurația proiectului](/help/projects#import-project) după ce secretele lui sunt înlocuite cu referințe la variabile de mediu.

## Pachetele de sistem ale agentului {#system-packages}

**Permite agentului instalarea pachetelor de sistem**

În Setări → Agent și model, administratorii activează permisiunea cu **Salvează** și confirmă efectul. Implicit este oprită și apare pentru proiecte în container. Reconstruiți sau alegeți întâi o imagine compatibilă cu sudo, apoi porniți o lucrare nouă. Agentul execută direct comenzile, citește erorile și adaptează pașii în limitele lucrării.

Accesul la rețea rămâne separat: open permite sursele accesibile, allowlist-proxy domeniile HTTP/HTTPS permise, iar none numai sursele locale disponibile. Scripturile pachetelor au drepturi administrative în container; directoarele montate ale proiectului rămân partajate cu serverul. Pachetele de sistem se păstrează la reluarea aceluiași container; un container nou cere reevaluare și instalare.

## Bugetele jobului {#budgets}

Detaliile afișează **Lansări executor** (de exemplu 9 / 20) și **Lucru activ (secunde)** lângă limitele actuale ale proiectului, independent de statisticile de tokenuri. La 90% apare avertizarea de apropiere; la limită se cere majorarea înainte de reluare. Limita implicită este 20 în înrolare și `adore init`.

Administratorii pot urma **Ajustează bugetele în Setările proiectului**, deschide **Implementare**, modifica doar bugete, alege **Salvează** și confirma valorile exacte. Salvarea revizuită numai a bugetelor este permisă când joburile așteaptă clarificări, fără conductor activ sau operații neterminate. Celelalte setări păstrează verificările obișnuite de repaus și pauză; dezvoltatorii au acces doar la citire.

Bugetele sunt recitite înaintea fiecărei încercări, inclusiv la reluare și reîncercare. Încercarea în curs își păstrează limita de timp. Lucrul activ se cumulează între reîncercări, răspunsuri și revizii; așteptarea este exclusă. Majorarea păstrează consumul, taskul și progresul salvat. Un job eșuat prin epuizarea bugetului cere în continuare **Reia** după ajustare. Configurația nevalidă sau lipsă oprește încercările următoare până la corectare.

Dacă limitele actuale nu pot fi citite, detaliile păstrează consumul salvat, dovezile și acțiunile de recuperare. Limitele arată — cu un mesaj explicit de indisponibilitate; nu se presupune o valoare implicită. Corectează configurația înainte de o nouă execuție.
