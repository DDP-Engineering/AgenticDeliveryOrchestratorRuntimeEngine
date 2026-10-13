# Adăugarea unui repository

Adăugați un repository ca proiect pentru ca ADORE să poată prelua tichetele lui pregătite, să ruleze un agent de programare pe ele și să publice MR/PR-uri ciornă pe care oamenii să le revizuiască. Doar administratorii adaugă proiecte, iar ADORE nu integrează niciodată modificările.

## Înainte de a începe {#before-you-start}

Pregătiți următoarele:

- Adresa repository-ului (https sau ssh) pe care contul serverului ADORE o poate citi. ADORE îl clonează în propriul dosar când creați proiectul.
- AEGIS instalat în repository (`.agentic/aegis.py` și `.agentic/aegis.toml`). ADORE îl folosește așa cum este instalat și nu îl modifică niciodată. Comenzile sale de test rulează în containerul Linux, așa că scrieți-le pentru container.
- Un cont GitLab, GitHub sau Gitea care poate citi și actualiza tichetele și poate crea cereri de revizuire ciornă.
- Numele etichetelor ready și de aprobare. O persoană adaugă eticheta ready pentru ca un tichet să devină eligibil; vezi [Tichete pentru preluare automată](/help/tickets#labels).
- Agentul de programare, ID-ul modelului său și o imagine de container de pe server care conține agentul. Vezi [Executori și modele](/help/executors).

## Înrolarea unui proiect nou {#add-project}

Alegeți **Înrolează un proiect nou** în [Proiecte](/projects). Asistentul ghidat începe cu Repository și identitate și are cinci pași, iar schimbarea oricărui răspuns face ca validările și verificările anterioare să devină învechite.

| Pas | Ce cere |
|---|---|
| Repository și identitate | **URL-ul repository-ului** și **Citește repository-ul**: ADORE completează **Forge**, **Depozit**, **Gitea tea login**, **Ramură țintă** și ID-ul proiectului, pentru confirmare, și propune o **Calea clonei locale** pe care o puteți schimba. **Continuă** rămâne dezactivat până când repository-ul a fost citit. **Nume afișat** pornește de la numele repository-ului; **Descriere** este opțională. |
| Agent și model | **Executor** (opencode, codex, pi sau qwen), **Model**, **Rulează în** (**Container** sau **Instalat pe server**), **Autentificare model** (api-key sau host-auth, doar pentru OpenCode și Codex) și **Referințe de mediu pentru credențiale**: nume de variabile precum LOCAL_API_KEY, niciodată valori; lăsați-le goale când imaginea sau executorul instalat se autentifică singur. Pentru Container urmează **Motor de containere** (docker sau podman) și **Imagine executor**: text liber cu sugestii din imaginile de pe serverul ADORE și un aviz când imaginea introdusă nu este acolo. Pentru Instalat pe server apar comanda nativă a executorului și câmpurile contului local. |
| Eligibilitate, recenzori și limite | **Etichetă ready**, **Etichetă de aprobare**, **Revizori (separați prin virgulă)** opționali și patru limite per lucrare: lansări ale executorului, secunde active, cost raportat în USD și fișiere modificate. O limită de cost 0 dezactivează acea limită; nu înseamnă gratuit. |
| Verificare | **Validează configurarea** verifică structura și folderele de pe server. **Verifică mediul** testează apoi Git, instrumentul forge și autentificarea, motorul de containere, agentul din imagine, fișierele AEGIS și, unde este posibil, endpointul modelului. Nu se publică nimic. |
| Revizuire și creare | Afișează candidatul exact și locațiile de pe server. **Modifică** revine la un pas. **Creează cu preluarea oprită** clonează întâi repository-ul (dintr-un URL), verifică AEGIS și ramura țintă, apoi salvează proiectul și, dacă nu debifați **Creează etichetele ADORE în repository**, creează etichetele ADORE lipsă și arată rezultatul; urmează **Deschide proiectul**. |

Pentru execuția locală nativă alegeți **Rulează în → Instalat pe server**. Configurările specializate de container folosesc metoda avansată cu TOML de server de mai jos.

## Importul configurației unui proiect {#import-project}

Alegeți **Importă configurația proiectului** în [Proiecte](/projects) pentru a înrola un `config.toml` ADORE existent exact așa cum este, de exemplu unul creat din linia de comandă sau salvat anterior cu **Descarcă configurația originală** în Setările unui proiect. Fișierul (UTF-8, până la 512 KiB) trebuie să aibă căi absolute pe server și niciun secret inclus: revizuirea le listează pe cele găsite, deci înlocuiți-le mai întâi cu referințe la variabile de mediu. ID-ul proiectului și dosarul de stare nu trebuie să aparțină unui proiect înrolat. ADORE copiază fișierul octet cu octet și se încheie cu **Înrolează cu preluarea oprită**. Istoricul apare doar dacă datele lui există deja în dosarul de stare declarat.

## Clonarea configurației unui proiect {#clone-project}

Alegeți **Clonează configurația proiectului** în [Proiecte](/projects) pentru a porni un proiect nou cu regulile de lucru ale altuia. **Dintr-un proiect de pe acest server** citește un proiect la care aveți acces; **Dintr-un fișier de setări portabile** citește un fișier JSON portabil (până la 64 KiB) din aceeași versiune ADORE. Se preiau doar 15 reguli de lucru (interogare periodică, pregătire, recuperare, bugete ale lucrărilor); identitatea, repository-ul, etichetele, credențialele, endpointurile, imaginile și istoricul nu se copiază niciodată. Alegeți **Revizuiește regulile sursei**, apoi **Configurează ținta nouă** și parcurgeți pașii ghidați. Verificați fișierele necunoscute: suma de control detectează modificările, dar nu dovedește autorul.

## După creare {#after-creation}

Un proiect nou începe cu monitorizarea oprită. Dezvoltatorii îl văd după ce un administrator acordă accesul în fila **Acces** a proiectului. În fila **Rezumat**:

1. Alegeți **Conectează depozitul**. Introduceți adresa serverului forge și un token de acces creat pe forge, apoi **Verifică și conectează**. Aceasta confirmă contul și accesul de citire la repository. Tokenul rămâne pe server, niciodată în browser. Alternativ, autentificați instrumentul forge sub contul de serviciu ADORE.
2. Alegeți **Verifică cerințele gazdei**. Detaliile acoperă Git, instrumentul de linie de comandă al repository-ului, autentificarea în repository, motorul de containere, agentul din imagine, fișierele AEGIS și conexiunea la modelul AI. Aceasta nu este o lucrare completă și nu dovedește permisiunea de push.
3. Rulați **Testează conexiunea AI** în Setări, așa cum este descris în [Executori și modele](/help/executors#test-connection).
4. Alegeți **Activează monitorizarea**. Cardul Monitorizare trece din În pauză în Activă, iar ADORE începe să preia tichetele care poartă eticheta ready. **Pune monitorizarea în pauză** oprește preluările noi, dar nu întrerupe o lucrare în curs.

## Arhivare, restaurare și ștergere {#lifecycle}

Administratorii găsesc aceste butoane în fila Rezumat.

- **Arhivează proiectul** funcționează după încheierea lucrărilor și golirea cererilor din coadă. Păstrează setările, istoricul, metricile și înregistrările de audit și oprește lucrul nou. **Restaurează proiectul** îl readuce.
- **Șterge proiectul** apare doar pentru proiectele arhivate și vă cere să tastați numele proiectului. Elimină setările ADORE ale proiectului, istoricul lucrărilor, metricile, containerele și worktree-urile. Păstrează repository-ul și ramurile sale, worktree-urile lucrărilor predate unei persoane, un dosar de stare al lucrărilor din afara directorului ADORE și jurnalul de audit. Ștergerea este refuzată cât timp există lucru în coadă sau neterminat. **Elimină și clona locală** (nebifat) șterge și clona făcută de ADORE în dosarul său `repos`; opțiunea apare doar pentru o clonă curată a repository-ului acestui proiect, pe care nu o folosește alt proiect și de care nu mai are nevoie niciun worktree păstrat la ștergere, altfel fereastra spune de ce se păstrează clona.

> Ștergerea nu poate fi anulată. Pentru a ajusta un proiect după aceea, vezi [Setările proiectului](/help/settings).
