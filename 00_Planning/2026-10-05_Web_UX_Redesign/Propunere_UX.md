<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# ADORE Web — propunere de interfață și fluxuri

Data: 5 octombrie 2026. Bază analizată: branch task/adore-web-interface, commit 6fed00c.

Statut: propunere de proiectare. Nu modifică implementarea și nu deschide un task AEGIS. Conține decizii propuse, nu comportamente deja implementate.

## Recomandarea

Păstrăm direcția vizuală a Overview, dar reorganizăm interfața în jurul întrebărilor utilizatorului: **Ce lucrează acum? Ce așteaptă intervenția mea? Ce va face acest proiect? Cât a consumat?**

Folosim un wizard pentru înrolare/import, unde utilizatorul ia decizii succesive cu consecințe clare. Pentru monitorizare și modificări uzuale folosim pagini directe, cu context și explicații vizibile. Un wizard pus peste formularul actual, fără schimbarea vocabularului și a modelului de import, ar muta confuzia între mai multe ecrane.

Primul rezultat urmărit: un utilizator nou poate înrola un proiect, explica de ce un job așteaptă și identifica următoarea acțiune fără să citească documentația ADORE sau AEGIS. Acest lucru trebuie verificat cu utilizatori; prototipul nu dovedește singur că obiectivul este atins.

## Ce am analizat

- Codul React, traducerile, stilurile, rutele și agregarea metricilor din 04_Software/web/src/.
- API-ul, verificarea configurației, importul, controlul accesului, comenzile și auditul din 04_Software/adore/web/.
- Contractele de stare și metrici relevante pentru reprezentarea corectă a job-urilor.
- Paginile actuale într-o instanță locală izolată, cu date sintetice și executori/servicii externe simulate: Overview, înrolare, import, configurare, Jobs, Metrics, Users și Audit.

Capturile current-*.png din acest director documentează acea instanță. Nu reprezintă proiectele reale ale operatorului, măsurători de producție sau verificări live ale unui forge/container. Unele combinații din datele fixture, cum ar fi un job finalizat cu o etapă implicită, nu sunt folosite drept constatări despre comportamentul real.

## Diagnosticul implementării actuale

| Zonă | Constatare | Efect pentru un utilizator nou |
| --- | --- | --- |
| Overview | Direcție vizuală calmă, navigare consistentă și carduri utile. Unele informații au scope global, altele de proiect. | Este cel mai bun punct de plecare. Scope-ul trebuie afișat fără ambiguitate. |
| Înrolare | Formularul prezintă simultan circa 12 câmpuri: platformă Git, cale clonă, reviewers, executor, model, runtime, imagine, autentificare etc. | Utilizatorul trebuie să înțeleagă infrastructura înainte să înțeleagă rezultatul înrolării. |
| Import | Trei câmpuri și un fișier TOML, însă importul cere căi absolute de pe host și copiază fișierul neschimbat. | Formularul este scurt, dar decizia este dificilă: „De unde obțin fișierul? Ce se copiază? Unde ajung datele? Merge de pe alt server?” |
| Configurare | Setări frecvente urmate de multe grupuri tehnice și chei TOML; ajutorul se află frecvent în zone expandabile. Modificarea este pregătită și apoi aplicată pe o revizie verificată. | Protecțiile sunt valoroase, dar utilizatorul vede formatul intern înaintea scopului setării. Efectul și diferența față de valoarea curentă sunt greu de scanat. |
| Jobs | Filtre tehnice numeroase, status și etapă în coloane distincte; pornirea manuală prin număr de ticket are vizibilitate mare. | Ecranul nu răspunde suficient de direct la „de ce stă?” și „cine trebuie să facă ce?”. |
| Metrics | Totaluri istorice, perioadă, usage, calitate, tendințe și comparații coexistă. Totalurile istorice sunt etichetate explicit, dar filtrul de dată nu le transformă în totaluri de perioadă. | Utilizatorul poate atribui aceleași filtre tuturor cardurilor. Explicația existentă ajută, însă arhitectura vizuală cere atenție suplimentară. |
| Users | Creare cont și administrare acces există, dar acordarea proiectelor este un pas separat. | Legătura „dev = aceste proiecte” nu este centrală în crearea contului. |
| Audit | Acțiunile interne și detaliile compacte domină tabelul; politica de retenție este în fața istoricului. | Este greu de răspuns la „cine a schimbat această limită, din cât în cât, și când a devenit activă?”. |

Puncte de păstrat: administrarea pe proiect, separarea rolurilor, redactarea secretelor, verificarea reviziilor configurației, aplicarea controlată, jurnalul de operații, limitele de rulare și explicațiile deja existente. Problema nu se rezolvă eliminând aceste protecții.

Repere de cod pentru constatări:

- 04_Software/web/src/App.tsx: formularul de înrolare în jurul liniei 1037, configurarea în jurul liniei 1079, metricile în jurul liniei 1133; stările sunt mapate în jurul liniei 75.
- 04_Software/adore/web/app.py: previzualizarea importului în jurul liniei 752; rutele import-preview/import în jurul liniei 1781; configurația și candidatul în jurul liniilor 2000–2214.
- Același API: _run_view în jurul liniei 1348 nu include token-uri în lista de job-uri; auditul configurației înregistrează cheia în mai multe operații, nu un istoric complet before/after.
- 04_Software/web/src/App.tsx în jurul liniei 1133 și app.py în jurul liniei 1252: totalurile istorice și agregatele de perioadă sunt concepte distincte.

## Direcția grafică

**Un panou de operare clar, cu spațiu pentru explicații scurte.** Menținem verdele ADORE ca accent și folosim un fundal gri foarte deschis, suprafețe albe și text închis. Verde pentru acțiunea principală și succes; albastru pentru lucru în desfășurare; chihlimbar pentru așteptare/intervenție; roșu pentru eșec. Fiecare stare are text și simbol, nu doar culoare.

Identitatea firmei: sigla **DDP Engineering** apare direct pe fondul închis al navigării, fără placă sau chenar alb, urmată de numele produsului ADORE. La cererea utilizatorului, varianta de interfață are fond transparent și culoare verde pal (#B8D1C4), pentru un contrast mai discret. Forma și proporțiile provin din materialul furnizat; un filtru SVG elimină fondul de hârtie și adaptează culoarea fără redesenarea contururilor. Pe mobil, sigla și numele produsului împart antetul. Varianta albastră extrasă inițial este păstrată separat. Sigla este raster, inclusiv în fișierul SVG furnizat; detaliile extragerii și adaptării sunt în README.

Ierarhia fiecărei pagini:

1. Nume simplu, proiect/perioadă și o propoziție despre scop.
2. O acțiune principală contextuală.
3. Ce cere atenție, dacă există.
4. Datele de lucru: listă, formular sau grafic.
5. Detalii tehnice deschise la cerere.

Reguli vizuale propuse:

- Coloană de navigare stabilă; zona principală cu lățime confortabilă, nu formulare pe tot ecranul.
- Carduri pentru sumar și decizii, tabele pentru liste comparabile. Evităm carduri uriașe cu trei câmpuri și mult spațiu gol.
- Titlu 28–32 px, text uzual 15–16 px, explicații cu contrast lizibil; ținte de interacțiune de aproximativ 44 px ca obiectiv de design.
- Etichete deasupra câmpurilor; exemple și explicații esențiale permanent vizibile. Placeholder-ul nu înlocuiește eticheta.
- Grupuri de setări cu nume de scop; cheia tehnică apare în detalii/copiere pentru utilizatorii avansați.
- Butoane care descriu efectul: „Verifică și continuă”, „Creează proiectul cu preluarea oprită”, „Aplică modificarea”.
- Empty/loading/error sunt stări proiectate: „Niciun job în această perioadă” diferă de „Nu am putut încărca job-urile”.
- Pe mobil, navigarea se compactează, wizard-ul devine o coloană, iar tabelele primesc un sumar lizibil și acces la detalii. Nu ascundem statusul sau acțiunea necesară.
- Tema întunecată rămâne disponibilă în implementare, cu contraste verificate separat. Prototipul ilustrează tema luminoasă.

Ținta de accesibilitate este WCAG 2.2 AA: tastatură, focus vizibil, etichete, mesaje de eroare legate de câmpuri, anunțarea schimbărilor de stare, contrast și reflow. Nu pretindem că prototipul sau aplicația actuală sunt certificate conforme.

## Navigare și pagini

Navigare principală: **Privire de ansamblu · Proiecte · Job-uri · Statistici**. Administratorul vede suplimentar **Administrare**, cu Utilizatori, Istoric modificări și Starea sistemului. Contul și preferințele stau în partea de jos a navigării.

„Job” este introdus contextual ca „o încercare ADORE de a rezolva un ticket”. „Proiect înrolat” înseamnă „un repository conectat la ADORE, cu propriile reguli de lucru”. Nu cerem utilizatorului să cunoască numele etapelor AEGIS pentru navigare.

### Privire de ansamblu

Păstrăm structura utilă actuală și punem pe primul plan **Necesită atenție**: aprobare solicitată, clarificare solicitată, eșec, verificare necesară. Fiecare rând indică proiectul, ticket-ul, motivul, cine poate interveni și acțiunea disponibilă.

Cardurile globale spun explicit „Toate proiectele la care ai acces”. Un card de proiect nu apare fără numele proiectului. Activitatea recentă folosește titlul ticket-ului și rezultatul, cu acces la detalii.

Pentru primul proiect: un bloc scurt „Conectează repository-ul → Alege regulile → Verifică → Activează preluarea”. Pentru un dev fără proiecte: „Nu ai proiecte alocate. Cere administratorului acces.” Nu afișăm un formular de înrolare inaccesibil.

### Proiecte

Lista: nume, repository/platformă, **preluare ticket-uri**, verificare mediu, job-uri active, atenționări, ultima activitate. Separăm „preluare oprită” de „mediu neverificat”; ambele pot fi adevărate simultan.

Pagina unui proiect: **Rezumat · Job-uri · Statistici · Setări · Acces · Istoric**. Rezumatul explică „ADORE urmărește ticket-urile eligibile din repository, lucrează în mediu izolat, verifică rezultatul și cere aprobările prevăzute. Livrarea produce un draft MR/PR; integrarea rămâne o decizie umană.”

Setările, accesul și istoricul administrativ respectă rolurile. Dev vede informația permisă și explicația limitărilor, fără controale administrative. Categoriile financiare rămân rezervate admin conform contractului actual; accesul dev la costuri ar necesita o decizie separată.

## Înrolare ghidată

Propun șase pași scurți, fiecare cu o decizie coerentă, nu câte o pagină pentru fiecare câmp. Înapoi păstrează răspunsurile. Pașii finalizați sunt accesibili; pașii dependenți sunt revalidați dacă schimbăm sursa.

### 1. Cum adaugi proiectul?

Trei opțiuni explicate:

- **De la început:** conectezi un repository și alegi regulile.
- **Pornind de la un proiect existent:** copiezi reguli de lucru; alegi un repository și un mediu propriu. Job-urile, accesul și istoricul nu se copiază.
- **Dintr-un fișier:** import de setări portabile sau, în secțiunea avansată, configurație TOML existentă pentru acest server.

Clonarea și pachetul portabil sunt funcții noi, nu variante pe care API-ul actual le oferă deja.

### 2. Repository și identitate

Nume afișat, descriere opțională, platformă Git, repository și branch țintă. Ajutorul explică „GitHub/GitLab/Gitea este locul unde se află codul și ticket-urile”. Dacă API-ul cere identificator owner/repo, îl solicităm exact și arătăm un exemplu; o adresă URL care se transformă automat în identificator necesită parser/backend dedicat.

În API-ul actual, numele este și identificator de profil, cu caractere restrânse și fără spații; nu este un nume afișat liber. Propun separarea numelui uman „Portal clienți” de ID-ul stabil „portal-clienti”, cu generarea și verificarea disponibilității ID-ului înainte de creare. Aceasta cere suport backend. Într-o livrare doar frontend păstrăm identificatorul existent și explicăm formatul acceptat; nu trimitem numele cu spații către API-ul actual și nu redenumim implicit profiluri existente.

Câmpul pentru clonă se numește **„Folderul copiei de lucru de pe serverul ADORE”**. Explicație: „Codul trebuie să existe în acest folder pe server. Acesta nu este folderul calculatorului din care ai deschis browserul.” În prima livrare păstrăm cerința clonei existente. Un asistent care clonează efectiv repository-ul este un proiect separat, cu progres, autorizare și tratarea erorilor.

### 3. Mediul de lucru

„Cu ce agent și model se lucrează?” și „În ce mediu izolat rulează?”. Oferim profiluri de mediu configurate de administrator când există o sursă reală de inventar, nu liste care pretind că imagini/executori inexistenți sunt instalați.

Rezumatul arată executorul, modelul/provider-ul, runtime-ul și imaginea. „Personalizează” deschide opțiunile avansate. Alegerea explică dependențele: compatibilitatea unui endpoint cu executorul, imagine existentă, numele variabilei de mediu pentru autentificare. Nu solicităm secrete în formular sau în fișierul portabil.

### 4. Reguli și limite

Grupuri: „Ce ticket-uri poate prelua?”, „Cine verifică rezultatul?”, „Cât poate lucra înainte să se oprească?”. Refolosim reguli și valori realmente suportate de backend. Explicăm limitele în unități umane, cu intervalul și consecința lor. Nu introducem implicit etichete sau aprobatori dacă nu au fost aleși/verificați.

### 5. Verificare

Verificare structurală locală și verificare explicită a mediului sunt distincte:

- **Configurație validă:** tipuri, obligatorii, căi, limite și incompatibilități.
- **Verifică mediul:** acțiune solicitată explicit, care poate contacta platforma Git sau verifica runtime-ul/containerul. Explicăm ce va face înainte de pornire; nu declanșăm probe externe la fiecare tastare.

Rezultatele spun concret: „Folderul nu există pe server”, „Imaginea nu este disponibilă”, „Credențialul de acces lipsește”. Fiecare are câmpul relevant, remedierea și „Verifică din nou”. O eroare de schemă/fișier corupt blochează înrolarea; nu ghicim valori și nu reinițializăm date.

### 6. Recapitulare și creare

Repository, agent/model, mediu, limite, verificatori, locații și ce începe imediat. Link „Modifică” pentru fiecare secțiune. Propun ca **toate înrolările noi să înceapă cu preluarea oprită**; astăzi acest comportament este explicit pentru import, nu trebuie presupus pentru toate metodele.

După creare: „Proiectul este înrolat. Preluarea de ticket-uri este oprită.” Un buton separat „Activează preluarea” apare când verificările și autorizarea permit. Explicăm: „Activarea permite preluarea de ticket-uri eligibile; nu înseamnă că pornește imediat un anumit ticket.”

Draft-ul wizard-ului trebuie păstrat fără secrete și fără efecte asupra orchestratorului. Începutul poate păstra datele doar în memorie, cu avertizare la părăsire. Salvarea durabilă cere un draft server-side legat de utilizator, cu expirare și acces verificat. Nu depozităm credențiale în localStorage.

## Import: două intenții, două contracte

### A. Import portabil de setări — recomandat pentru transfer între proiecte/servere

Format propus: un pachet versionat, exportat de ADORE, cu reguli și opțiuni portabile. Conține manifest cu versiune de schemă și compatibilitate. Nu este arhivă completă de proiect.

Flux:

1. Alegi fișierul și vezi ce fel de fișier este acceptat și ce conține.
2. Vezi setările recunoscute, cele incompatibile și informațiile care trebuie completate pe serverul țintă.
3. Completezi identitatea noului proiect, repository-ul, clona și mediul. Nicio cale veche nu se aplică automat.
4. Vezi tabel „Din fișier / Pe acest server / Efect”; verifici configurația și, explicit, mediul.
5. Recapitulezi și creezi proiectul cu preluarea oprită.

Credentialele, directoarele de stare și worktree, job-urile, utilizatorii, grants, auditul și reviziile pending nu sunt transferate. Referințele la credențiale/endpoint-uri pot necesita reconfirmare; nu presupunem că același nume de variabilă este sigur pe alt server. Cheile necunoscute și versiunea incompatibilă produc probleme explicite, fără ignorare tăcută. Alegerea formatului concret rămâne o decizie de implementare; un JSON versionat este o variantă simplă.

Importul într-un proiect existent, dacă este dorit, este o acțiune separată **„Înlocuiește setări din fișier”**, cu diff, candidat și aceleași condiții de aplicare ca editarea. Nu îl confundăm cu înrolarea unui proiect nou.

### B. Înrolează o configurație TOML existentă — opțiune avansată

Este intenția API-ului actual. Eticheta propusă evită „Import project” fără explicație:

> Ai deja un config.toml pentru acest server? Îl poți înrola aici. Fișierul este copiat neschimbat. Căile trebuie să existe sau să fie valide pe serverul ADORE. Istoricul poate fi citit numai dacă datele aferente există la locațiile configurate; fișierul singur nu transferă job-uri.

Arătăm calea sursă declarată pentru repository, worktree, state și metrici, plus validarea fiecăreia. Cerem căi absolute, păstrăm interdicția de a folosi rădăcina volumului și detectarea suprapunerii directoarelor de stare cu alte proiecte. Fișierul cu secrete, invalid sau schimbat după preview este respins.

Nu oferim în acest mod o editare care promite copiere neschimbată. „Adaptează pentru un proiect nou” deschide explicit fluxul portabil, când parserul/conversia sunt implementate. Confirmarea include numele, locațiile și faptul că preluarea începe oprită. Preview și confirmare rămân legate de aceeași revizie a fișierului.

## Setări: configurația exprimată ca intenție

Propun categorii:

- **Repository și ticket-uri:** sursa, branch, criterii de eligibilitate.
- **Agent și model:** executor, provider/model, endpoint, referințe de autentificare.
- **Mediu izolat:** runtime, imagine, directoare, acces la rețea.
- **Reguli și aprobări:** verificări, reviewers și regulile suportate de orchestrator.
- **Limite și recuperare:** iterații, durată, retry-uri, limite de cost/fișiere când sunt disponibile.
- **Măsurare și notificări:** metrici și destinații acceptate.
- **Avansat:** chei tehnice și informațiile suportate care nu încap util în categoriile de mai sus.

Exemplu: „Număr maxim de încercări după un eșec”, nu doar cheia internă. Sub câmp: „ADORE oprește recuperarea după această limită și păstrează dovezile pentru operator.” Valoarea curentă și valoarea implicită sunt distincte. Tipul, intervalul și editabilitatea provin din contractul real.

Fluxul de modificare: **Editezi → Pregătești → Revizuiești diferența → Aplici**. Afișăm „Valoare actuală → Valoare propusă”, motivul, utilizatorul, momentul și condițiile de aplicare. Schimbările de identitate/runtime cer preluarea oprită; aplicarea candidatului cere proiect fără activitate și fără lock, conform API-ului. Dacă e blocată, afișăm motivul și acțiunea disponibilă, nu un buton care eșuează inexplicabil.

Păstrăm protecția împotriva reviziilor depășite. La conflict: „Setările au fost schimbate între timp. Reîncarcă și compară din nou.” Nu suprascriem automat. În prima etapă păstrăm limita reală a candidatului existent; un candidat cu mai multe editări atomice este o extensie backend, nu doar o grupare vizuală.

„Clonează setări” și „Exportă setări” se află în meniul proiectului. Înainte de export enumerăm ce se include/exclude și verificăm dreptul admin. Nu prezentăm exportul CSV al metricilor ca export de configurație.

## Job-uri: stare, motiv și următorul pas

Lista globală suportă mai multe proiecte autorizate, căutare după ticket/titlu și grupuri simple: **În lucru · Necesită intervenție · Finalizate · Eșuate · Anulate**. Substările exacte rămân vizibile. Filtrele avansate pentru executor, etapă, outcome și intervale se deschid la cerere.

Coloane: Ticket și titlu, Proiect, Stare cu motiv scurt, Activitate recentă, Durată, Token-uri când există date. Numărul de ticket singur este insuficient. „Pornește un ticket” este acțiune secundară contextuală, cu explicație și confirmarea proiectului selectat.

Detalii job: rezultat/scop, un bloc **„Ce se întâmplă acum”**, **„Cine intervine și unde”**, acțiunea permisă, apoi timeline și artefactele/logurile. Etapele pot fi explicate „Clarifică cerința → Stabilește soluția → Implementează → Verifică → Pregătește livrarea”, însă timeline-ul păstrează maparea exactă frame/specify/design/build/validate/deliver în detalii, inclusiv pași omişi prin quick path. Nu inventăm progres procentual din numărul etapelor.

| Stare reală | Prezentare propusă | Următorul pas |
| --- | --- | --- |
| working | În lucru; etapa și ultima activitate | Monitorizare; anulare numai conform autorizării și contractului existent. |
| parked-clarification | Așteaptă o clarificare; întrebarea când există în date | Răspuns în ticket-ul platformei Git, cu link. Afișarea întrebării complete poate cere date suplimentare în API. |
| awaiting-approval | Așteaptă aprobarea rezultatului verificat | Link către locul real al aprobării pe forge. Aprobarea trebuie să corespundă candidatului curent. |
| publishing | Publică rezultatul | Progres și eventuale erori; fără acțiune de merge. |
| in-review | Draft MR/PR disponibil pentru verificare | Deschide draft-ul pe platforma Git. Nu înseamnă integrat. |
| handoff-pending / handed-off | Predare în curs / Predat | Explicație din dovezile predării și contractul operației. Nu le etichetăm automat drept succes sau integrare. |
| done | Finalizat, cu outcome explicit | Rezultat și artefact. „Integrat” apare numai dacă există dovadă de merge uman. |
| failed | Oprit cu eroare; motiv și ultima operație | Retry dacă este permis, după explicarea efectului; păstrează dovezile încercării anterioare. |
| cancelled | Anulat | Motiv și resurse, conform dovezilor operației de anulare. |

„Proiect cu preluarea oprită” nu este „job în pauză”. Oprirea preluării blochează noi selecții de ticket-uri și nu pune job-urile active în pauză. UI-ul trebuie să scrie această consecință lângă control. Nu propunem buton de pause/resume arbitrar pe job, aprobare în UI sau merge în UI fără un nou contract autorizat; merge-ul rămâne exclus permanent pentru orchestrator.

## Statistici care au același scope

Un singur antet persistă: **proiecte autorizate + perioadă + fus orar + definiția intervalului**. Toate cardurile, graficele, tabelele și exportul din această pagină folosesc acel scope. „Toată perioada disponibilă” este o alegere explicită, nu un set de totaluri plasat lângă un filtru care se aplică în altă parte.

Rezumat inițial: job-uri pornite/finalizate/eșuate, token-uri input/output și total, durată, acoperirea măsurătorilor. Costurile raportate și estimate se disting și sunt vizibile doar admin. Apoi: evoluție în timp, pe proiect, pe job; calitatea și recuperarea într-o secțiune secundară.

Definiții necesare:

- Job-uri pornite/finalizate în perioadă sunt evenimente după propriul timestamp. Stocul „active acum” este separat, nu un total de perioadă.
- Token-uri pe perioadă: evenimente de consum timestampate în interval, indiferent când a început job-ul. Token-uri pe job: suma evenimentelor sale. Job-uri fără consum cunoscut nu devin zero măsurat.
- Job traversând două perioade contribuie cu fiecare eveniment în perioada lui; totalul pe job poate diferi de suma afișată pentru perioada selectată.
- Timestamp-uri lipsă/invalide: „neatribuit unei perioade”, cu număr și acoperire, nu repartizare ghicită.
- Medii și rate au numărător, numitor și eșantion vizibile. Cost estimat nu devine cost raportat.
- Eșecul încărcării este eroare, nu tabel gol și card cu 0.

**Mesaje:** în datele examinate există lansări de executor și evenimente de usage, dar acestea nu sunt un număr de mesaje. Pentru a livra cerința trebuie definită sursa: mesaje conversaționale ale executorului, comentarii pe ticket/MR ori ambele separat. Recomand două serii distincte, fără total amestecat implicit. Capturarea conversațiilor depinde de capabilitățile fiecărui executor; inaccesibil înseamnă „Nedisponibil”, nu 0.

Contract nou pentru contorizare: identificator unic/source, run și project, timestamp, categorie și autor/rol unde sunt disponibile, deduplicare la replay/retry. Conținutul mesajelor nu trebuie colectat doar pentru a număra. Un „apel de model” nu este neapărat un mesaj; orice derivare trebuie denumită ca atare.

API-ul actual are agregate de perioadă pentru anumite măsuri. Refolosim ce este compatibil și extindem contractul pentru rate, outcome-uri și detalii lipsă; nu recalculem metrici semantice prin filtrarea aproximativă a cardurilor în browser.

## Utilizatori și istoric

Creare utilizator: **Identitate → Rol și proiecte → Recapitulare**. Admin: toate proiectele și administrarea. Dev: selecție explicită a proiectelor, cu rezumat „Va putea vedea și opera aceste proiecte conform permisiunilor dev”. Autentificarea/parolele urmează mecanismele existente; nu inventăm invitație email sau resetare prin email.

Modificarea accesului arată înainte/după și se aplică pe server. Filtrarea vizuală nu este control de acces: liste, detalii, metrici, exporturi, clone și importuri trebuie verificate pe fiecare endpoint. Dev nu primește metadate despre proiecte nealocate.

Istoricul are filtre Utilizator, Proiect, Tip, Perioadă. Rând: **cine / ce / proiect / când / rezultat**, de exemplu „Ana a aplicat limita de încercări: 2 → 3”. Detaliul separă „pregătit” de „aplicat” și arată reviziile, operația corelată și valorile redactate. Schimbarea este auditată în backend; traducerea unei acțiuni raw în text nu produce retroactiv dovezi before/after.

Extensie propusă: evenimente structurate cu diff redactat, rezultat și corelare. Istoricul vechi afișează sincer „Valoarea anterioară nu este înregistrată”. Politica de retenție merge în Setări administrare, cu impact clar; istoricul rămâne conținutul principal al paginii.

## Exemple de text în interfață

| Concept actual | Text propus | Explicație vizibilă |
| --- | --- | --- |
| Import project | Adaugă un proiect dintr-un fișier | Alege între setări portabile și o configurație existentă pentru acest server. |
| Local clone path | Folderul codului pe serverul ADORE | Copia repository-ului trebuie să fie deja disponibilă aici. |
| Executor image | Mediul izolat pentru agent | Imaginea trebuie să fie instalată pe server și compatibilă cu agentul ales. |
| Reviewers | Persoane care verifică rezultatul | Folosește identitățile de pe platforma Git, potrivit regulilor proiectului. |
| Pickup paused | Preluarea de ticket-uri este oprită | Job-urile care rulează continuă. Nu sunt preluate ticket-uri noi. |
| Stage change | Pregătește modificarea | Setările active rămân în vigoare până când aplici candidatul revizuit. |
| stale_config_revision | Setările au fost schimbate între timp | Reîncarcă și compară modificarea cu noua versiune. |
| Usage coverage | Cât de complete sunt măsurătorile? | Avem date de consum pentru 18 din 20 de job-uri. Celelalte două nu sunt considerate consum zero. |

## Ce cere implementare și în ce ordine

| Etapă propusă | Rezultat | Dependențe reale |
| --- | --- | --- |
| 1. Claritate imediată | Vocabular, stări explicate, scope vizibil, grupare setări, import TOML explicat, job „motiv/următor pas” unde există dovezi | În principal frontend; date absente afișate ca absente, fără promisiuni false. |
| 2. Înrolare și configurare | Wizard nou, recapitulare, verificări explicite, creare cu preluarea oprită, review before/after | Refolosire API actual + contract pentru înrolare uniform oprită; diff/candidat multiplu dacă intră în scope. |
| 3. Portabilitate | Clonează, exportă, importă setări cu schemă versionată și reguli de mapare | Backend și teste trust boundary: schemă, paths, secrete, acces, revizii, integritate și incompatibilități. |
| 4. Date și administrare | Scope statistic consistent, token-uri pe job, mesaje definite, audit structurat, creare cont cu proiecte | Contracte backend/telemetrie și migrarea controlată a stocării unde este necesară. |
| 5. Verificare UX | Ajustări pe utilizatori nefamiliarizați și accesibilitate | Scenarii demonstrative, observație și criterii de acceptare. |

Prima implementare recomandată după validarea direcției: **import/înrolare + detaliu job + configurare**, cu adaptările de vocabular comune. Overview primește ajustări limitate. Nu reconstruim toate paginile înainte să verificăm dacă oamenii înțeleg primele trei fluxuri.

La implementare, App.tsx poate fi împărțit în pagini și componente de domeniu: wizard/draft, listă job-uri, explicație stare, review configurație și filtre de statistici. Facem această separare în pași, păstrând testele și rutele existente. Nu propunem schimbarea framework-ului sau o bibliotecă grafică nouă ca precondiție.

Alte dependențe care nu trebuie mascate printr-o machetă:

- Lista de job-uri actuală este furnizată pe proiect; o listă globală cu paginare și filtre consistente cere agregare autorizată. Evităm combinarea în browser a primelor pagini ale proiectelor și prezentarea lor drept listă completă.
- Titlul ticket-ului, motivul detaliat al așteptării și consumul per job nu sunt toate în răspunsul compact _run_view. Extindem proiecția din dovezi persistate, fără apeluri live la forge pentru fiecare refresh și fără titluri inventate.
- Maparea erorilor de import pe câmpuri și locații poate necesita răspunsuri structurate, în locul unei liste de coduri generice. Validarea autoritară rămâne pe server.
- „Dev” este denumirea produsului propusă pentru rolul developer existent în backend. Un redesign de vocabular nu schimbă implicit modelul de permisiuni.

## Criterii de acceptare propuse

Test exploratoriu cu 5 persoane nefamiliarizate cu ADORE/AEGIS, cu date sigure și sarcini comune. Pragurile de mai jos sunt obiective inițiale, de validat; nu rezultate măsurate:

- Minimum 4/5 explică în maximum un minut diferența dintre preluare oprită și job care așteaptă clarificare, fără ajutor.
- Minimum 4/5 înrolează un proiect folosind un mediu pregătit în maximum 10 minute, fără instrucțiuni verbale. Necesitatea de a pregăti infrastructura se măsoară separat.
- Minimum 4/5 identifică unde se dă aprobarea și înțeleg că ADORE nu face merge.
- Minimum 4/5 pot spune ce se copiază, ce nu se copiază și ce trebuie completat într-un import portabil.
- Toți pot vedea ce se schimbă înainte să aplice configurația și pot reveni la corectarea unei alegeri.
- La schimbarea perioadei, fiecare total afectat are aceeași definiție de scope; datele lipsă și zero măsurat sunt distincte.
- Dev nu vede proiecte nealocate, date financiare sau acțiuni admin nici prin URL direct/export/API.

Verificări tehnice viitoare: flux happy path și negative la granițele de încredere; fișiere invalide/incompatibile/cu secrete, suprapunere directoare, revizie schimbată după preview, autorizare, inaccesibilitate mediu, date incomplete, replay duplicat. Browser: Înapoi păstrează datele, validarea arată câmpul, focus și tastatură, ecran îngust, loading/empty/error, acces direct la rute. Unit tests rămân offline; verificările live sunt acțiuni explicite ale operatorului.

## Decizii de confirmat înaintea implementării

1. Ce numărăm drept mesaje și ce executori pot furniza acele date? Recomand serii separate pentru conversații și comentarii forge.
2. Ce profiluri de mediu există realmente și cine le administrează? Wizard-ul simplificat trebuie alimentat din această sursă.
3. Importul vizează prioritar proiect nou sau și înlocuirea setărilor unuia existent? Prima livrare propusă: proiect nou.
4. Păstrăm rolurile actuale și costurile exclusiv admin? Recomand păstrarea lor în redesign-ul inițial.
5. Unde se păstrează draft-urile? Prima versiune poate fi în memorie; reluare după închiderea browserului cere suport backend.

Aceste întrebări nu împiedică propunerea vizuală. Ele delimitează ce nu trebuie ghicit în implementare.

## Prototip și capturi

- [Prototip navigabil](./Prototip.html): document HTML local, cu date demonstrative. Deschide-l într-un browser, păstrând fișierul DDP_Engineering_logo_dark.png în același director. Nu apelează ADORE, nu clonează repository-uri, nu încarcă fișiere pe server și nu modifică proiecte. Butoanele de finalizare simulează rezultatul, indicat explicit.
- Vizualizează Privire de ansamblu, Proiecte, un job care așteaptă aprobare, Statistici, Setări, Utilizatori și Istoric. „Adaugă proiect”/„Importă setări” deschid wizard-ul. Modurile portabil și TOML existent au explicații distincte.
- Capturi current-*.png: interfața actuală cu date fixture. Capturi proposal-*.png: direcția propusă, date fictive.

Prototipul comprimă validarea tehnică și nu implementează toate ramurile de eroare, permisiunile sau sursele de date. Valorile illustrative nu reprezintă recomandări verificate pentru infrastructura utilizatorului. Scopul lui este compararea graficii și a ordinii deciziilor.

Verificări efectuate pentru documentul demonstrativ: încărcare și navigare în browser, import cu exemplu, blocarea continuării fără exemplu, păstrarea numelui la Înapoi, recapitulare și finalizare simulate, filtrele statistice demonstrative și afișare la 1440 px/390 px fără overflow orizontal în ecranele verificate. Nu sunt teste ale implementării ADORE și nu constituie test de utilizabilitate cu persoane noi.

## Referințe de design

Folosim pași organizați în jurul unor întrebări coerente și explicații vizibile, adaptând recomandările [GOV.UK pentru pagini de întrebări](https://design-system.service.gov.uk/patterns/question-pages/). Nu copiem mecanic regula unei întrebări per ecran într-un panou tehnic.

Recapitularea înaintea unei operații cu efect și legăturile de corectare urmează principiile [GOV.UK Check answers](https://design-system.service.gov.uk/patterns/check-answers/).

Etichetele și instrucțiunile vizibile răspund principiilor [W3C WCAG — Labels or Instructions](https://www.w3.org/WAI/WCAG22/Understanding/labels-or-instructions). Aceste surse susțin direcția propusă; rezultatul pentru ADORE trebuie validat prin testare cu utilizatori.
