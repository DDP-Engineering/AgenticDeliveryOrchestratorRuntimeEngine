# Glosar

Aprobarea umană înainte de publicare este activată implicit. Administratorii pot modifica **Cere aprobare umană înainte de PR/MR** în Setări. Când este dezactivată, ADORE verifică actualitatea candidatului și a țintei înainte de publicare; testele repository-ului rămân responsabilitatea agentului.

Aceștia sunt termenii folosiți în interfața web ADORE și în aceste subiecte de ajutor.

## Termeni {#terms}

| Termen | Semnificație |
|---|---|
| Lucrare | Un tichet din repository, lucrat și verificat într-un mediu izolat. |
| Proiect înrolat | Un repository existent configurat pe gazda ADORE, cu acces acordat echipei sale. |
| Monitorizare | Setarea unui proiect pentru preluarea tichetelor noi, afișată ca **Activă** sau **În pauză**. Administratorii o schimbă cu **Pune monitorizarea în pauză** și **Activează monitorizarea** în fila Rezumat a proiectului. |
| Preluare oprită | ADORE nu mai preia tichete noi pentru acest proiect. Aceasta nu pune în pauză o lucrare activă. Este starea pe care Monitorizarea o afișează ca **În pauză**. |
| Tichet | O sarcină (issue) de pe forge. ADORE o preia când poartă eticheta ready a proiectului și o etichetă de prioritate, nu este blocată sau exclusă și are criterii de acceptare, dacă proiectul le cere. |
| Agent de programare / Executor | Instrumentul AI în linie de comandă care face munca pentru o lucrare într-un mediu izolat: Pi, singurul agent de programare pe care îl rulează ADORE. Nu are credențiale forge și nu face niciodată commit sau push și nu deschide ori integrează un MR/PR. |
| Model | ID-ul modelului la furnizorul ales, de exemplu gpt-5.4 pentru OpenAI. Se setează împreună cu furnizorul în Setări → Agent și model, iar prețurile estimate aparțin unei perechi executor–model. |
| AEGIS | Fluxul instalat în repository care încadrează, specifică, proiectează, construiește și validează o modificare. ADORE îl conduce o etapă pe rând (Încadrare, Specificare, Proiectare, Construire, Validare) și publică rezultatul aprobat; o modificare mică poate sări peste Specificare și Proiectare. |
| Flux direct | Un repository fără AEGIS este implementat direct de agent. Agentul își conduce verificările; ADORE urmărește progresul și cere aprobarea umană. |
| Candidat | Rezultatul validat al unei lucrări, pe care ADORE îl prezintă spre aprobare, identificat printr-o amprentă și commit-ul țintă. Aprobarea se aplică exact acelui candidat și expiră dacă se schimbă candidatul sau ramura sa țintă. |
| Așteaptă clarificări | Agentul are nevoie de un răspuns pentru a continua. Răspundeți la întrebarea sa în tichetul din repository. |
| Așteaptă aprobarea | Rezultatul este validat și așteaptă autorizarea publicării de către o persoană. Aprobarea se înregistrează pe forge pentru candidatul curent. |
| MR/PR ciornă | Cererea MR/PR deschisă după validare și aprobarea necesară. Oamenii o revizuiesc. |
| Revizie umană | Un MR/PR este disponibil pentru revizie umană. Integrarea rămâne o decizie umană. |
| Rundă de revizie | O nouă trecere a agentului după modificări cerute sau erori CI. Fiecare rundă repetă validarea și respectă politica de aprobare. |
| Forge | Platforma de găzduire unde se află tichetele, etichetele, aprobările și MR/PR-urile: GitHub, GitLab sau Gitea. |

> ADORE nu are nicio operație de integrare. Integrarea este întotdeauna decizia unei persoane, pe forge.
