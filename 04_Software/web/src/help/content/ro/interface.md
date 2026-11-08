# Prezentarea interfeței

Interfața are o bară laterală întunecată pentru navigarea între pagini și o bară de sus care numește pagina curentă și oferă acțiunile uzuale. Această pagină enumeră paginile, butoanele din antet, pagina proiectului și etichetele de stare.

## Navigare {#navigation}

| Pagină | Ce faceți acolo |
|---|---|
| Prezentare generală | Vedeți **Necesită intervenție** și **Lucrări active** pentru proiectele la care aveți acces. **Detalii** deschide o lucrare în Lucrări. |
| [Proiecte](/projects) | Parcurgeți proiectele înrolate cu repository-ul, forge-ul, starea monitorizării, numărul de lucrări și ultima activitate. Deschideți un proiect pentru a ajunge la pagina lui. Administratorii văd și **Înrolează un proiect nou**, **Importă configurația proiectului** și **Clonează configurația proiectului**. |
| [Lucrări](/jobs) | Alegeți din **Domeniul joburilor**, apoi folosiți sub-fila **Tichete** pentru a citi tichetele de pe forge și a le porni, sau sub-fila **Lucrări** pentru a căuta lucrări și a deschide detaliile lor. |
| [Statistici](/metrics) | Citiți utilizarea, calitatea și tendințele pentru o perioadă de raportare. Vezi [Statistici și costuri](/help/statistics). |
| Administrare | Doar pentru administratori. Deschide trei pagini: [Starea sistemului](/admin/status), [Utilizatori](/admin/users) și [Istoricul modificărilor](/admin/audit). Vezi [Administrare](/help/administration). |
| [Contul meu](/account) | Alegeți limba și tema și schimbați parola. |

Bara laterală afișează și numele și rolul dumneavoastră, precum și **Deconectare**. Pe un ecran îngust, **Meniu** deschide navigarea, iar alegerea unei pagini o închide.

Un Dev vede doar proiectele atribuite de un administrator și nu are intrarea Administrare. Fiecare pagină are propria adresă, astfel că marcajele, Înapoi, Înainte și reîncărcarea vă păstrează locul.

## Antet {#header}

Bara de sus afișează titlul paginii și aceste comenzi.

- **Proiect**: un selector doar în Prezentare generală. Restrânge **Necesită intervenție** și **Lucrări active** la un singur proiect; implicit sunt toate proiectele la care aveți acces. Lucrări are propriul selector **Domeniul joburilor**, iar Statistici are un selector **Proiect** în rândul perioadei de raportare.
- **Reîmprospătează**: afișat, împreună cu ora **Ultima actualizare**, doar pe paginile care nu se actualizează singure: Utilizatori, Istoricul modificărilor și filele Setări, Acces și Istoric ale unui proiect.
- **Despre**: versiunea ADORE, cu **Noutăți** (notele de versiune pe versiuni, cele mai noi primele, grupate în Nou, Îmbunătățit și Corectat), **Licență** și **Notificări despre componente terțe**.
- **Cum funcționează ADORE**: deschide acest centru de ajutor.

## Pagina proiectului {#project-hub}

Deschiderea unui proiect din Proiecte afișează numele și calea repository-ului deasupra acestor file.

| Filă | Ce conține |
|---|---|
| Rezumat | Tipul de container, executorul, monitorizarea, verificarea mediului, numărul de lucrări și tabele compacte Necesită intervenție și Lucrări active. Administratorii primesc și **Pune monitorizarea în pauză** sau **Activează monitorizarea**, **Arhivează proiectul** sau **Restaurează proiectul**, **Verifică cerințele gazdei** și **Acces la repository**. |
| Setări | Setările efective ale proiectului, pe grupuri. Administratorii modifică câte o setare pe rând printr-o modificare revizuită; Dev-ii le citesc fără secrete. Vezi [Setările proiectului](/help/settings). |
| Lucrări | Sub-filele Tichete și Lucrări pentru acest proiect, fără selector de proiect. |
| Statistici | Aceeași perioadă de raportare, aceleași file și exporturi ca pagina Statistici, doar pentru acest proiect. |
| Istoric | Modificările înregistrate ale proiectului și lucrările lui încheiate. |
| Acces | Doar pentru administratori: acordați sau retrageți accesul unui dezvoltator. |

Monitorizarea în pauză oprește preluarea tichetelor noi; lucrările deja pornite continuă.

## Etichete și insigne de stare {#statuses}

Insignele au un simbol, nu doar culoare, iar listele de lucrări arată etapa curentă lângă stare.

| Starea lucrării | Semnificație |
|---|---|
| În lucru | ADORE conduce o etapă. |
| Publicare | ADORE publică un candidat aprobat. |
| Așteaptă clarificări | Agentul are nevoie de un răspuns în tichetul din repository. |
| Așteaptă aprobarea | O persoană trebuie să aprobe candidatul pe forge. |
| Revizie umană | Un MR/PR ciornă este deschis; oamenii decid dacă îl integrează. |
| Predare în curs | O predare către o persoană așteaptă un punct sigur. |
| Predat | O persoană a preluat lucrarea; munca automată s-a încheiat. |
| Finalizat | Lucrarea s-a încheiat. Aceasta singură nu arată că cineva a integrat modificarea. Listele compacte îi spun Finalizată. |
| Eșuate | Lucrarea s-a oprit, păstrându-se dovezile; un utilizator autorizat o poate **Reîncerca**. |
| Anulată | Lucrarea a fost anulată. |
| Învechit | Lucrarea este marcată ca învechită; consultați rezultatul ei salvat. |

Pe pagina Lucrări, **Stare** restrânge lista la **Lucrări active**, **În așteptare**, **Revizie umană** sau **Joburi încheiate**. Insigna Monitorizare a unui proiect afișează **Activă** sau **În pauză**, iar un proiect arhivat afișează **Arhivat**. Verificarea mediului afișează **Verificat**, **Verificat parțial**, **Verificare eșuată**, **Verificare învechită** sau **Neverificat**; Neverificat înseamnă că nu există dovezi curente, nu că o verificare a eșuat.

După **Pornește**, **Reîncearcă** sau **Anulează**, o notificare raportează comanda ca fiind în coadă, în execuție, finalizată, eșuată sau incertă. Verificați o comandă incertă înainte de a o trimite din nou. O comandă eșuată sau incertă spune și motivul, când motorul îl numește, și arată ultimele linii ale motorului.

## Actualizări automate, limbă și temă {#preferences}

Prezentare generală, Proiecte și Lucrări își reîncarcă datele la fiecare 15 secunde cât timp fila browserului este vizibilă; Statistici și Starea sistemului se actualizează și ele singure. O filă ascunsă nu se mai actualizează și se reîmprospătează imediat ce reveniți. Dacă o actualizare eșuează, cifrele afectate rămân ascunse până la următoarea reușită.

În [Contul meu](/account), **Aspect** conține **Limbă** (English, Français, Deutsch, Română) și **Temă** (**Sistem**, **Luminoasă**, **Întunecată**). Fiecare alegere este salvată în contul dumneavoastră și vă urmează în toate browserele; înainte de autentificare, pagina de autentificare reține alegerea în browser. **Schimbă parola** cere parola curentă și una nouă de cel puțin 8 caractere.
