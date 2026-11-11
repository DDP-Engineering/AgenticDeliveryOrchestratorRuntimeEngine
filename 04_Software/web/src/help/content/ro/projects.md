# Adăugarea unui repository

Adăugați un repository ca proiect pentru ca ADORE să poată prelua tichetele lui pregătite, să ruleze un agent de programare pe ele și să publice MR/PR-uri ciornă pe care oamenii să le revizuiască. Doar administratorii adaugă proiecte, iar ADORE nu integrează niciodată modificările.


O verificare actuală a mediului se transferă proiectului creat. Cerințele neverificate rămân parțiale; schimbarea configurației învechește rezultatul. Dacă verificarea expiră, ruleaz-o din nou.


O autentificare CLI externă reușită rămâne parțială deoarece se poate schimba în afara ADORE fără o modificare observabilă. Conectați accesul la repository și verificați din nou pentru a lega credențialele proiectului.

## Înainte de a începe {#before-you-start}

Pregătiți următoarele:

- Adresa repository-ului (https sau ssh) pe care contul serverului ADORE o poate citi. ADORE îl clonează în propriul dosar când creați proiectul.
- AEGIS instalat în repository (`.agentic/aegis.py` și `.agentic/aegis.toml`). ADORE îl folosește așa cum este instalat și nu îl modifică niciodată. Comenzile sale de test rulează în containerul Linux, așa că scrieți-le pentru container.
- Un cont GitLab, GitHub sau Gitea care poate citi și actualiza tichetele și poate crea cereri de revizuire ciornă.
- Numele etichetelor ready și de aprobare. O persoană adaugă eticheta ready pentru ca un tichet să devină eligibil; vezi [Tichete pentru preluare automată](/help/tickets#labels).
- ID-ul modelului pentru agentul de programare Pi și, pentru un proiect în container, o imagine de pe server construită din imaginea de bază ADORE, care conține Pi. Vezi [Executori și modele](/help/executors).

## Înrolarea unui proiect nou {#add-project}

Alegeți **Înrolează un proiect nou** în [Proiecte](/projects). Asistentul ghidat începe cu Repository și identitate și are cinci pași, iar schimbarea oricărui răspuns face ca validările și verificările anterioare să devină învechite.

| Pas | Ce cere |
|---|---|
| Repository și identitate | **URL-ul repository-ului** și **Citește repository-ul**: ADORE completează **Forge**, **Depozit**, **Gitea tea login**, **Ramură țintă** și ID-ul proiectului, pentru confirmare, și propune o **Calea clonei locale** pe care o puteți schimba. **Continuă** rămâne dezactivat până când repository-ul a fost citit. **Nume afișat** pornește de la numele repository-ului; **Descriere** este opțională. |
| Agent și model | Alegeți **Furnizor**, **Model** și detaliile endpointului, dacă este necesar. Pentru container, alegeți runtime-ul și imaginea. Salvați cheia furnizorului în Setări după creare. Pentru **Instalat pe server** apar contul curent al sistemului și opțional **PATH pentru uneltele proiectului**. |
| Eligibilitate, recenzori și limite | **Etichetă ready**, **Etichetă de aprobare**, **Revizori (separați prin virgulă)** opționali și patru limite per lucrare: lansări ale executorului, secunde active, cost raportat în USD și fișiere modificate. O limită de cost 0 dezactivează acea limită; nu înseamnă gratuit. |
| Verificare | **Validează configurarea** verifică structura și folderele de pe server. **Verifică mediul** testează Git, accesul la forge și fișierele AEGIS. Pentru execuția nativă, **Pi pe server** afișează erorile locale, inclusiv versiunile Node incompatibile. Pentru execuția în container, se verifică motorul și Pi din imaginea locală. Nu se publică nimic. **Continuă** deschide revizuirea după ce configurarea este validă. |
| Revizuire și creare | Afișează candidatul exact și locațiile de pe server, plus o listă restrânsă **Setări lăsate la valorile implicite** cu valoarea implicită a fiecărei alte setări (doar citire; le schimbați în Setări după creare). **Modifică** revine la un pas. **Creează cu preluarea oprită** clonează întâi repository-ul (dintr-un URL), verifică AEGIS și ramura țintă, apoi salvează proiectul și, dacă nu debifați **Creează etichetele ADORE în repository**, creează etichetele ADORE lipsă și arată rezultatul; urmează **Deschide proiectul**. |

Pentru execuția locală nativă alegeți **Rulează în → Instalat pe server**. Configurările specializate de container folosesc metoda avansată cu TOML de server de mai jos.

Alegeți **Instalat pe server** pentru Pi administrat de ADORE sub contul curent al sistemului. **PATH pentru uneltele proiectului** selectează opțional directoarele cu unelte. Vedeți [Instalarea Pi pe server](/help/executors#installed-executors).

**Locație automată** păstrează calea propusă pentru clonă. Alege **Locație personalizată** și **Alege folderul…** pentru a răsfoi folderele gazdei ADORE. Un clic selectează rândul; dublu-clic sau Enter deschide folderul. Folosește Înapoi sau Folderul părinte, apoi **Selectează folderul** pentru a confirma exact folderul existent. Introdu o destinație nouă direct în câmpul căii clonei din formularul principal. Selectorul nu creează nimic; legăturile și căile de rețea sunt refuzate. **Anulează** păstrează schița. Calea tastată în timpul încărcării listei rămâne în bara de adrese.

**Ramură țintă** listează ramurile remote pentru GitHub, GitLab și Gitea, inclusiv instanțe proprii. Ramura implicită a repository-ului este selectată și marcată **implicită**. Alegeți altă ramură dacă este nevoie. **Citește repository-ul** actualizează lista și păstrează o selecție explicită dacă ramura mai există. Schimbarea URL-ului șterge opțiunile anterioare. Dacă nu este raportată o ramură implicită, alegeți una; dacă repository-ul nu are ramuri, adăugați una acolo și recitiți-l. Se folosește accesul Git al contului ADORE; tipul forge necunoscut se selectează în continuare manual.

## Importă configurația brută {#import-project}

În [Proiecte](/projects), alegeți **Importă configurația brută** și selectați în dialog ZIP-ul exportat sau fișierul UTF-8 `config.toml`. ADORE verifică automat fișierul, căile de pe server, dosarul de stare și secretele incluse. Corectați problemele semnalate în fișier și selectați-l din nou. Alegeți **Importă** după validare. Proiectul nou pornește cu monitorizarea în pauză și păstrează configurația octet cu octet.

Selectează direct ZIP-ul exportat complet: configurația și definițiile imaginilor sunt importate împreună. ADORE verifică și graful surselor, corespondența imaginii și definițiile existente. O definiție diferită care folosește deja numele imaginii principale este refuzată. Fișierele TOML pot avea până la 512 KiB, iar ZIP-urile până la 18 MiB. Construiește imaginile separat pe serverul destinație, folosind fișierul Compose inclus. Vezi [Setări → Exportă configurația brută](/help/settings#toml).


Un proiect nou începe cu monitorizarea oprită. Dezvoltatorii îl văd după ce un administrator acordă accesul în fila **Acces** a proiectului. În fila **Rezumat**:

1. Alegeți **Acces la repository**. Introduceți adresa serverului forge și un token de acces creat pe forge, apoi **Verifică și conectează**. Aceasta confirmă contul și accesul de citire la repository. Tokenul rămâne pe server, niciodată în browser. Alternativ, autentificați instrumentul forge sub contul de serviciu ADORE.
2. Alegeți **Verifică cerințele gazdei**. Detaliile acoperă Git, instrumentul de linie de comandă al repository-ului, autentificarea în repository, motorul de containere, Pi din imagine și fișierele AEGIS, plus autentificarea ChatGPT a serverului pentru un abonament ChatGPT, imaginea proxyului de rețea când [accesul la internet](/help/executors#internet) este dezactivat și cheia de căutare web când Brave sau Tavily are nevoie de una. Pentru un proiect care rulează direct pe server, **Execuție locală** înlocuiește rândurile pentru motorul de containere și imagine: verifică versiunea compatibilă de Node, Pi administrat de ADORE și credențialele furnizorului. Aceasta nu este o lucrare completă și nu dovedește permisiunea de push.
3. Rulați **Testează conexiunea AI** în Setări, așa cum este descris în [Executori și modele](/help/executors#test-connection).
4. Alegeți **Activează monitorizarea**. Cardul Monitorizare trece din În pauză în Activă, iar ADORE începe să preia tichetele care poartă eticheta ready. **Pune monitorizarea în pauză** oprește preluările noi, dar nu întrerupe o lucrare în curs.

## Arhivare, restaurare și ștergere {#lifecycle}

Administratorii găsesc aceste butoane în fila Rezumat.

- **Arhivează proiectul** funcționează după încheierea lucrărilor și golirea cererilor din coadă. Păstrează setările, istoricul, metricile și înregistrările de audit și oprește lucrul nou. **Restaurează proiectul** îl readuce.
- **Șterge proiectul** apare doar pentru proiectele arhivate și vă cere să tastați numele proiectului. Elimină setările ADORE ale proiectului, istoricul lucrărilor, metricile, containerele și worktree-urile. Păstrează repository-ul și ramurile sale, worktree-urile lucrărilor predate unei persoane, un dosar de stare al lucrărilor din afara directorului ADORE și jurnalul de audit. Ștergerea este refuzată cât timp există lucru în coadă sau neterminat. **Elimină și clona locală** (nebifat) șterge și clona făcută de ADORE în dosarul său `repos`; opțiunea apare doar pentru o clonă curată a repository-ului acestui proiect, pe care nu o folosește alt proiect și de care nu mai are nevoie niciun worktree păstrat la ștergere, altfel fereastra spune de ce se păstrează clona.

> Ștergerea nu poate fi anulată. Pentru a ajusta un proiect după aceea, vezi [Setările proiectului](/help/settings).

## Autentificare Gitea pe acest calculator {#gitea-sign-in}

ADORE folosește mai întâi conexiunea salvată a proiectului. Altfel reutilizează configurația tea a contului curent. Dacă tea raportează un login lipsă, ADORE verifică locațiile standard Windows sau Linux și selectează loginul configurat, un singur login implicit sau singurul login disponibil. Mai multe conturi fără o selecție clară necesită o conexiune explicită.

Detectarea respectă `XDG_CONFIG_HOME`. Pe Windows verifică și directoarele Local AppData, Roaming AppData și `.config` din home-ul contului; pe Linux verifică directorul `.config` din home. Nu caută în cache-urile private ale aplicațiilor și nu copiază credențiale între calculatoare.

1. Deschide fila **Rezumat** a proiectului și alege **Acces la repository**.
2. Completează **Serverul depozitului** cu adresa de bază Gitea, inclusiv portul dacă este necesar.
3. Creează pe serverul Gitea un token pentru contul cu drept de citire/actualizare a tichetelor și creare de cereri de revizuire în draft și introdu-l în **Token de acces**.
4. Apasă **Verifică și conectează**. Un server HTTP necesită confirmarea afișată. O verificare eșuată păstrează conexiunea salvată.
5. Verifică din nou cerințele gazdei. Credențialele Git pentru clone/push se configurează separat.

Pe alt calculator, pregătește autentificarea CLI locală sau folosește acest formular de conectare. Arhiva de livrare nu conține tokenurile utilizatorilor.
