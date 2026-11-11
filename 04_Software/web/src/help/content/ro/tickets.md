# Tichete pentru preluare automată

ADORE preia tichete din repository-ul dumneavoastră de pe forge (GitHub, GitLab sau Gitea) când poartă etichetele potrivite, iar dumneavoastră puteți porni și manual unul. Acest articol acoperă etichetele, eligibilitatea și vizualizarea Tichete.


Tichetele cu eticheta configurată pentru epic nu sunt preluate sau pornite. Pornirea manuală rămâne disponibilă pentru tichetele eligibile când monitorizarea este în pauză.

## Cum funcționează preluarea {#how-pickup-works}

Fiecare proiect are o stare **Monitorizare**, afișată ca **Activă** sau **În pauză** în tabelul Proiecte și în fila Rezumat a proiectului. Cât timp monitorizarea este Activă, ADORE verifică repository-ul pentru tichete pregătite la un interval regulat (60 de secunde implicit; vezi **Interval de verificare (secunde)** în [Setările proiectului](/help/settings)). Preia mai întâi tichetul eligibil cu cea mai mare prioritate (P1, apoi P2, apoi P3), apoi pe cel cu numărul cel mai mic, și avansează o lucrare pe rând.

Un administrator poate folosi **Pune monitorizarea în pauză** și **Activează monitorizarea** în fila Rezumat a proiectului. Monitorizarea în pauză oprește preluările automate; lucrările în curs continuă.

## Creați mai întâi etichetele {#labels}

GitHub și Gitea resping un nume de etichetă necunoscut, așa că o etichetă lipsă face ca actualizările de stare să eșueze. Toate etichetele de mai jos trebuie să existe în repository-ul de pe forge înainte de prima rulare. ADORE le creează pe cele lipsă la adăugarea unui proiect (**Creează etichetele ADORE în repository**, bifată implicit în Revizuire și creare) sau când apăsați **Creează etichetele lipsă** în Setări → Repository; nu modifică și nu șterge niciodată etichetele existente și arată ce a creat, ce exista deja și ce a eșuat (de exemplu când contul de forge al serverului nu poate crea etichete). Numele sunt cele implicite; redenumiți una doar împreună cu setarea ei din proiect.

| Etichetă | Scop |
|---|---|
| `agent-ready` | O adăugați dumneavoastră pentru a oferi un tichet spre preluare. ADORE o înlocuiește cu eticheta de lucru când lucrarea pornește. |
| `agent-working` | O setează ADORE cât timp lucrează, publică și așteaptă aprobarea dumneavoastră. |
| `agent-clarify` | O setează ADORE când a pus o întrebare și așteaptă un răspuns. |
| `agent-answered` | O adăugați dumneavoastră după ce ați răspuns la o întrebare. |
| `agent-mr` | O setează ADORE după publicarea MR/PR-ului, cât timp așteaptă revizuirea umană. |
| `agent-failed` | O setează ADORE când o lucrare eșuează. |
| `agent-done` | O setează ADORE după ce o persoană a integrat MR/PR-ul. |
| `agent-approved` | O adăugați dumneavoastră pe tichet pentru a aproba publicarea candidatului prezentat. |
| `agent-revise` | Un recenzor o adaugă pe MR/PR pentru a cere o rundă de revizie. |

ADORE elimină la fiecare actualizare de stare etichetele de ciclu de viață pe care nu le aplică, așa că toate trebuie să existe. Adăugarea manuală a unei etichete de stare nu schimbă lucrarea.

## Ce face un tichet eligibil {#eligible-tickets}

Un tichet este preluat doar când toate regulile sunt îndeplinite. Ele sunt verificate în această ordine:

1. Tichetul este deschis.
2. Are eticheta ready (`agent-ready`).
3. Nu are eticheta de blocare (`agent-hold`). Eliminarea etichetei de blocare face tichetul din nou eligibil.
4. Nu are eticheta de excludere (`no-agent`, setarea **Eticheta de excludere de la preluare**). Ea are prioritate față de eticheta ready. Eliminarea ei restabilește eligibilitatea; adăugarea ei nu oprește o lucrare deja pornită.
5. ADORE nu are încă nicio lucrare pentru tichet.
6. Are o etichetă de prioritate: `P1`, `P2` sau `P3`. **Cere etichetă de prioritate pentru tichet** este activată implicit.
7. Dacă **Cere criterii de acceptare pentru tichet** este activată, descrierea conține cuvintele acceptance criteria (indiferent de majuscule) sau un element de sarcină nebifat, `- [ ]`. Această verificare este dezactivată implicit.

Etichetele opționale modelează lucrarea: `bug` sau `fix` produce o sarcină de corecție, `change` o sarcină de modificare, iar orice alt tichet o sarcină de funcționalitate. `agent-quick` este doar o sugestie; executorul alege între calea completă și cea rapidă și înregistrează motivul.

## Revizuirea și pornirea tichetelor {#tickets-view}

Deschideți un proiect din Proiecte, alegeți fila **Lucrări** și rămâneți pe sub-fila **Tichete**. Pagina globală **Lucrări** din bara laterală are aceleași două sub-file și un selector **Domeniul joburilor**. Cu **Toate proiectele**, tabelul primește o coloană Proiect, iar fiecare rând acționează asupra propriului proiect.

Nimic nu se citește până nu apăsați **Citește tichetele**. Încarcă până la 500 de tichete deschise. Peste 10 tichete se afișează pe pagini: alegeți 10, 25, 50 sau Toate în **Rânduri pe pagină** și navigați cu **Înapoi** și **Înainte**; se afișează numărul paginii din numărul de pagini. Fiecare rând afișează numărul într-o coloană îngustă, alături de titlu, etichete, Stare și acțiuni. Starea numește ce blochează un tichet:

| Stare | Semnificație |
|---|---|
| Gata de pornire | Toate regulile sunt îndeplinite. |
| Lipsește eticheta ... | Eticheta ready lipsește. |
| În așteptare sau Exclus din ADORE | Este prezentă eticheta de blocare sau de excludere. |
| Lipsește eticheta de prioritate | Nu există etichetă de prioritate. |
| Lipsesc criteriile de acceptare | Textul cerut nu a fost găsit. |
| Are o lucrare sau Lucrare: ... | ADORE are deja o lucrare; se afișează starea ei. |
| Nu este deschis | Tichetul este închis. |

**Pornește** pune o lucrare în coadă; workerul aplică în continuare verificările obișnuite. Dacă tichetului îi lipsește eticheta ready sau o etichetă de prioritate, ADORE vă cere confirmarea, vă lasă să alegeți o prioritate, iar **Adaugă etichetele și pornește** le adaugă mai întâi în repository. Pornirea nu este disponibilă pentru tichetele închise, blocate sau excluse, pentru tichetele fără criteriile de acceptare cerute și pentru tichetele care au o lucrare. **Reia** înlocuiește Pornește când lucrarea a eșuat. **Oprește** cere confirmare, anulează o lucrare neterminată și elimină eticheta ready, pentru ca monitorizarea să nu mai preia tichetul. **Detalii** afișează descrierea și comentariile.

**Pornește** pornește manual doar tichetul selectat, inclusiv cu **Monitorizare** **În pauză**, și păstrează monitorizarea în pauză. Se aplică în continuare limita de lucrări, fluxul din repository, eligibilitatea, blocarea conductorului și aprobările. O operație eșuată afișează motivul concret; dacă rezultatul este invalid sau incert, consultă logurile gazdei înainte de reluare.

Pe desktop, Pornește sau Reia, Oprește și Detalii sau Ascunde detaliile rămân pe același rând. Pe ecrane înguste, butoanele pot trece pe rândul următor pentru a rămâne în pagină.

## Citirea descrierilor și comentariilor {#reading-bodies}

**Detalii** deschide implicit descrierile și comentariile în Markdown **Randat**. Titlurile, evidențierile, codul, listele imbricate, sarcinile doar pentru citire, citatele, tabelele și linkurile sunt formatate; o descriere goală păstrează **Fără descriere.**

Folosiți **Afișarea conținutului** în dreapta titlului **Descriere**, cu eticheta și selectorul pe aceeași linie pentru a alege **Randat** sau **Sursă Markdown** pentru toate descrierile și comentariile deschise. Sursa arată textul exact primit din repository, inclusiv spațiile și liniile noi. Contul păstrează alegerea salvată între proiecte, reîncărcări și browsere; alt browser autentificat o citește la următoarea autentificare sau reîncărcare. Dacă salvarea eșuează, apare o eroare și revine ultimul mod salvat; alegeți din nou pentru a reîncerca.

HTML-ul rămâne text vizibil, nu conținut executabil. Doar linkurile absolute http, https și mailto sunt accesibile și se deschid separat. Imaginile nu se încarcă automat: apar **Imagine neîncărcată** și textul alternativ, dacă există. Codul, sursa și tabelele late derulează în zone proprii, accesibile cu tastatura. Bifele sarcinilor nu pot modifica tichetul.

## Listă de verificare pentru primul tichet {#checklist}

1. Creați toate cele nouă etichete în repository-ul de pe forge.
2. Pentru preluare automată, verifică Monitorizarea Activă; pentru Pornește manual, poate rămâne În pauză.
3. Scrieți un titlu clar și o descriere cu criterii de acceptare.
4. Adăugați o etichetă de prioritate și, opțional, `bug`, `fix`, `change` sau `agent-quick`.
5. Adăugați `agent-ready` ultima.
6. Așteptați următoarea verificare sau apăsați **Citește tichetele** și **Pornește**.
7. Urmăriți lucrarea în [Ciclul de viață al lucrării](/help/jobs). Termenii sunt în [Glosar](/help/glossary).
