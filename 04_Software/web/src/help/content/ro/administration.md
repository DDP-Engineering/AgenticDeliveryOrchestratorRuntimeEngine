# Administrare

Administrarea acoperă conturile de utilizator, accesul la proiecte, starea sistemului și evidența modificărilor. Este doar pentru administratori: un Dev nu vede meniul Administrare, iar un Dev care deschide una dintre adresele lui este dus la Prezentare generală.

> Tot ce se află pe această pagină cere rolul de Administrator.


Un semnal recent arată că supervisorul este disponibil. **Ocupat** înseamnă o comandă, o verificare de proiect sau o lucrare în curs; **Activitate necunoscută** înseamnă că dovada lipsește. Proiectele progresează independent, cu lucrări paralele până la limita fiecăruia. Comenzile de configurare au un lucrător separat. Pornirile așteaptă un loc; anularea autorizată poate ajunge la o lucrare activă.

## Utilizatori {#users}

Sub **Administrare**, deschideți [Utilizatori](/admin/users). Pagina are un panou **Adaugă utilizator** și o listă **Utilizatori**.

Pentru a crea un cont:

1. Alegeți **Adaugă utilizator** deasupra listei pentru a deschide formularul de creare. Introduceți **Utilizator** și **Parolă** (cel puțin 8 caractere), apoi introduceți aceeași valoare în **Repetă parola nouă**. Butoanele cu ochi afișează sau ascund fiecare câmp. Alegeți **Continuă la acces**. După **Corectează identitatea**, completați din nou confirmarea. Parola este omisă din revizuire.
2. Alegeți **Rol** și, pentru un Dev, proiectele. **Admin** acordă toate proiectele curente și viitoare, administrarea sistemului și costurile. **Dev** acordă doar proiectele bifate, fiecare listat cu numele, forge-ul și calea repository-ului. Pentru a crea un Dev fără niciun proiect, bifați intenționat **Creează Dev fără acces la proiecte**.
3. Alegeți **Revizuiește contul**, verificați identitatea și accesul exact, apoi alegeți **Creează contul revizuit**. **Corectează identitatea** și **Corectează accesul** vă readuc înapoi fără a crea nimic.

Contul și accesul lui se creează împreună sau deloc. Un nume de utilizator duplicat sau un proiect schimbat între timp respinge cererea; corectați și revizuiți din nou.

În lista **Utilizatori**, fiecare cont oferă aceste acțiuni.

- **Proiecte atribuite** (conturi Dev): bifați sau debifați proiecte, alegeți **Salvează**, comparați **Înainte** și **După**, apoi alegeți **Aplică accesul revizuit**. **Corectează accesul** anulează revizuirea.
- **Dezactivează** sau **Activează**: un cont dezactivat nu se poate autentifica, iar sesiunile lui se încheie. Nu vă puteți dezactiva propriul cont, iar ultimul administrator activ nu poate fi dezactivat.
- **Resetează parola**: alegeți acțiunea din rândul contului. Verificați numele contului, introduceți o **Parola nouă** de cel puțin 8 caractere și completați **Repetă parola nouă**. Butoanele cu ochi afișează sau ascund valorile. Alegeți **Salvează** când parolele coincid sau **Închide** pentru a renunța la datele introduse. Salvarea închide sesiunile contului și cere o parolă nouă la următoarea autentificare. Nu există recuperare prin e-mail.

## Accesul la proiecte {#project-access}

Fila **Acces** a unui proiect listează fiecare cont de dezvoltator cu **Are acces** sau **Fără acces**. Alegeți **Acordă acces** sau **Retrage accesul** lângă un dezvoltator, comparați **Înainte** și **După**, apoi alegeți **Aplică accesul revizuit**. Modificarea nu afectează celelalte proiecte ale dezvoltatorului și este înregistrată în Istoricul modificărilor. Lista de acces se actualizează la fiecare 15 secunde cât timp fila browserului este vizibilă.

Un dezvoltator cu acces vede proiectul și îi poate porni, reîncerca sau anula lucrările. Administratorii au întotdeauna acces.

## Starea sistemului {#system-status}

Sub **Administrare**, deschideți [Starea sistemului](/admin/status). Se actualizează singură.

- **Lucrătorul de control** afișează **Pregătit** în repaus, **Ocupat** în lucru, **Activitate necunoscută** fără dovadă, **Indisponibil**, **Verificarea stării a eșuat** sau **Se verifică…**. Un semnal recent nu confirmă accesul la forge, executori sau modele.
- **Stocare** afișează **Spațiu disponibil**, **Spațiu pe disc redus** sau **Verificarea stocării a eșuat**. Măsoară spațiul liber pe disc pentru baza de date de conturi ADORE și pentru dosarul de stare al lucrărilor fiecărui proiect, grupat pe volum fizic. Un singur disc partajat primește o singură linie; mai multe discuri primesc un tabel **Volum**, **Liber** și **Stare**. Sub 1 GiB liber se consideră redus, iar o măsurătoare eșuată nu este afișată niciodată ca spațiu liber.
- **Păstrarea auditului** stabilește cât timp se păstrează istoricul modificărilor. Limitele curente (sau **Nelimitat**) apar deasupra formularului. Setați **Păstrează (zile)** (zile întregi, de la 0 la 36500) și **Limită date audit (MiB)** (de la 0 la 1024, fracții permise) și alegeți **Salvează**. Zero sau gol înseamnă nelimitat. Cele două limite se aplică independent, iar cele mai vechi evenimente sunt eliminate primele. Notificarea de după salvare raportează câte evenimente au fost șterse. Limita de dimensiune numără textul de audit stocat, nu fișierul bazei de date de pe disc. Lucrările, jurnalele de execuție și conturile se păstrează.

## Istoricul modificărilor {#change-history}

Sub **Administrare**, deschideți [Istoricul modificărilor](/admin/audit) pentru a vedea cine ce a modificat, când și cu ce rezultat. Fila **Istoric** a unui proiect afișează aceleași dovezi doar pentru acel proiect, împreună cu lucrările lui încheiate. Ambele pagini se actualizează la fiecare 15 secunde cât timp sunt vizibile și păstrează filtrele, pagina și dovezile deschise. În Istoricul modificărilor global, **Actualizează** reîncarcă imediat lista.

Istoricul identifică tichetele și lucrările separat de numerele operațiilor. O operație eșuată apare ca **Eșuat**, iar una refuzată ca **Respins**. Ștergerile din CLI au autorul CLI și rămân vizibile după eliminarea lucrării. O ștergere întreruptă rămâne **Incert** până la confirmarea rezultatului.

Filtre:

- **ID autor**: numărul afișat lângă numele unui cont.
- **Proiect**: orice proiect sau **Toate proiectele**.
- **Tip modificare**: codul exact al acțiunii.
- **De la (UTC)** include momentul indicat; **Până la (UTC, exclusiv)** nu îl include.

Alegeți **Aplică filtre**; aceasta revine la prima pagină. Pagina raportează câte evenimente s-au potrivit, iar **Rânduri pe pagină** oferă 10, 25, 50 sau Toate, cu **Anterior** și **Următor**.

Fiecare rând afișează **Cine**, **Ce**, **Când** și **Rezultat**: **Pregătit**, **Aplicat**, **Eliminat**, **Respins** sau **Incert**. Pregătit înseamnă că un candidat a fost pregătit, nu aplicat. **Incert** înseamnă că gazda nu a putut confirma finalizarea; inspectați resursa reală înainte de a recupera. **Dovadă** deschide un rând sub eveniment cu **Înainte**, **După / candidat**, **Operație**, precum și **Revizie de bază** și **Revizie candidat** când sunt înregistrate. **Valoarea anterioară nu a fost înregistrată** înseamnă necunoscut, nu gol. Parolele și valorile de mediu nu sunt afișate niciodată.

Istoricul modificărilor se păstrează nelimitat, cu excepția cazului în care setați limite în [Starea sistemului](#system-status). Nu există descărcare sau export al istoricului modificărilor. Un Dev vede modificările operaționale doar pentru proiectele atribuite; evenimentele de cont, acces, preț și politică rămân la administratori.
