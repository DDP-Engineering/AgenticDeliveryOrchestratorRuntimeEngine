# Statistici și costuri

Statistici arată cât a lucrat ADORE, ce a consumat și cât de bine au rezistat rezultatele. Costurile sunt afișate doar administratorilor, iar costurile estimate nu sunt facturi.

## Perioada raportării și exportul {#period}

Deschideți **Statistici** din bara laterală pentru a vedea toate proiectele la care aveți acces sau deschideți fila **Statistici** a unui proiect pentru a-l vedea doar pe acela. Ambele folosesc aceeași structură: un rând **Perioada raportării** deasupra a patru file.

| Control | Ce face |
|---|---|
| Proiect | Doar pagina Statistici. Administratorii încep cu **Toate proiectele**; un Dev alege dintre proiectele atribuite. Fila proiectului nu are selector. |
| De la și Până la | Prima și ultima zi incluse. **Până la** include întreaga zi respectivă. |
| Grupare după | Intervale de **Zi**, **Săptămână** sau **Lună**, folosite de fila Tendințe și de exporturi. |
| Tot istoricul | Șterge ambele date. Lăsarea ambelor date goale înseamnă tot istoricul. |
| Exportă CSV | Deschide un meniu de descărcări pentru proiectul, datele și gruparea curente. |

Datele și intervalele folosesc UTC, dacă adresa paginii nu poartă alt fus orar. Datele se aplică fiecărei file și fiecărui export. Schimbarea proiectului păstrează perioada și fila în care vă aflați.

Meniul **Exportă CSV** oferă **Indicatorii proiectului**, **Utilizarea proiectului** și **Consumul jobului** pentru un singur proiect, sau **Indicatorii tuturor proiectelor**, **Utilizarea tuturor proiectelor** și **Consumul jobului** pentru **Toate proiectele**. Apare după încărcarea datelor. Dacă o cerere eșuează, pagina afișează **Datele nu au putut fi încărcate** și reține totalurile și exporturile.

O liniuță înseamnă că valoarea este necunoscută. Sub o valoare, **Zero măsurat** înseamnă că ADORE a observat zero, **Indisponibil** înseamnă că nu s-a înregistrat nimic, iar **Parțial · subtotal cunoscut** înseamnă că cifra acoperă doar utilizarea care a raportat tokenuri.

## Cele patru file {#tabs}

### Rezumat {#tab-summary}

Carduri pentru **Joburi începute**, **Joburi terminate**, **Joburi eșuate**, **Tokenuri de intrare**, **Tokenuri de ieșire** și **Total tokeni cunoscuți**. Terminate numără fiecare lucrare încheiată, indiferent de rezultat. Totalul cere ca ambele direcții de tokenuri să fie cunoscute. Administratorii văd și cardurile **Cost raportat** și **Cost estimat**. Cu **Toate proiectele**, un tabel **Compararea proiectelor** listează lucrările începute, terminate și eșuate și durata medie pe proiect, cu repository-ul sub numele fiecărui proiect.

### Utilizare {#tab-usage}

**Utilizare după executor și model** începe cu totaluri compacte: evenimente de utilizare, tokenuri de intrare și de ieșire, cache citit și cache scris, precum și durata lucrărilor (**Lucrări măsurate**, **Durata medie**, **Durata mediană**). Tabelul de dedesubt listează utilizarea după dată, executor și model; faceți clic pe un antet de coloană pentru a sorta. Cu **Toate proiectele** urmează un tabel pe proiecte. Administratorii văd și coloanele de cost.

### Calitate {#tab-quality}

**Calitatea livrării** afișează **Refaceri cerute la revizie**, **Validare reușită din prima**, **Îmbinare fără refacere la revizie**, **Revizii încă deschise**, **Eșecuri de etapă** și **Reîncercări de operator**. Fiecare rată arată numărătorul și numitorul. **Revizii încă deschise** reflectă starea curentă și ignoră perioada. Dedesubt sunt **Revizii MR/PR cerute de om** și **Reparații de pipeline**, cu un tabel zilnic al zilelor active. Cu **Toate proiectele**, un tabel pe proiecte adaugă rundele de revizie.

### Tendințe {#tab-trends}

Acoperirea utilizării și **Consum fără dată de atribuire** apar ca valori compacte. Un tabel are un rând pe interval (zi, săptămână sau lună) cu lucrările începute, terminate și eșuate ca bare proporționale, plus tokenurile de intrare și de ieșire și, pentru administratori, costul raportat și estimat.

Dacă domeniul nu are încă lucrări, Calitate și Tendințe spun asta și vă trimit la Lucrări → Tichete pentru a porni una.

## Costuri raportate și estimate {#costs}

Două cifre de cost sunt ținute separat, iar niciuna nu este o factură.

- **Cost raportat** este ceea ce a raportat executorul, luat ca dovadă observată. Dacă nu a raportat nimic, valoarea afișează **Indisponibil**.
- **Cost estimat** este numărul de tokenuri înregistrat înmulțit cu prețurile setate de administratori. Este o estimare, nu o factură și nu un plafon de cheltuieli.

Administratorii înregistrează prețurile în **Setări → Agent și model** al unui proiect, sub **Prețuri estimative**: alegeți **Valabil de la**, apoi introduceți **USD intrare / 1 mil. tokenuri** și **USD ieșire / 1 mil. tokenuri** și **Salvează**. Un preț se aplică agentului de programare selectat și modelului lui configurat, deci setați mai întâi modelul. Fiecare eveniment de utilizare este evaluat după executor, model și ziua în care a fost consumat. Evenimentele fără preț potrivit sunt numărate ca **Utilizări fără preț** în totalurile Utilizării.

> Un preț introdus cu o dată de intrare în vigoare anterioară poate schimba estimările din trecut. Exportați un CSV dacă aveți nevoie de o cifră la un anumit moment.

În fila Calitate, administratorii văd și **Cost per lucrare cu dovezi**, per lucrare finalizată și per lucrare integrată de o persoană, fiecare cu numărul de lucrări din spatele lui.

## Cine vede valorile monetare {#visibility}

| Rol | Proiecte | Bani |
|---|---|---|
| Administrator | **Toate proiectele** sau orice proiect individual | Cost raportat, Cost estimat, Utilizări fără preț, cost per lucrare, cost pe revizie, coloanele de cost și câmpurile financiare din exporturile CSV |
| Dev | Doar proiectele atribuite; fără **Toate proiectele** | Niciuna. Dev-ii văd numărul de lucrări, tokenurile, durata și cifrele de calitate, niciodată un câmp financiar. |

Prețurile sunt setate și vizibile doar administratorilor; Setările doar pentru citire ale unui Dev omit setările financiare.
