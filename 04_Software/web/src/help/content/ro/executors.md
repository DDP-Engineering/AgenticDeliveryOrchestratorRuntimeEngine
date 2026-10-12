# Executori și modele

Un executor este perechea pe care ADORE o lansează pentru fiecare lucrare: un agent de programare și modelul AI pe care îl folosește. Administratorii aleg ambele în Setările unui proiect.

## Ce este un executor {#what}

Pentru fiecare lucrare, ADORE pornește agentul de programare al proiectului într-o copie de lucru izolată, iar agentul parcurge etapele AEGIS ale repository-ului cu modelul configurat. Agenții sunt OpenCode, Pi, Codex și Qwen Code. Agentul nu face niciodată commit sau push și nu vede credențialele forge; acestea le face ADORE. ADORE nu instalează agenți și nu preia liste de modele, deci agentul trebuie să existe deja în imaginea proiectului sau pe server. Modificările se aplică doar lucrărilor noi.

## Alegerea agentului și a modelului {#agent-and-model}

Deschideți **Setări → Agent și model**. Rândurile sunt **Agent de programare implicit**, **Comanda de lansare a executorului** și **Identificatorul modelului executorului**.

Administratorii aleg **Modifică** pe rândul Agent de programare implicit și selectează OpenCode, Pi, Codex sau Qwen Code. Selectarea unui agent încarcă comanda și modelul lui salvate sau comanda presetată documentată. Pentru un agent nou, introduceți singuri ID-ul modelului: ID-ul pe care agentul și furnizorul dumneavoastră îl acceptă, de obicei `provider/model`. Nu există o valoare implicită universală. Comanda de lansare trebuie să conțină `{prompt}`. **Pregătește candidatul** revizuiește împreună agentul, comanda și modelul, iar **Aplică** le scrie ca o singură modificare. Așteptați-vă să puneți mai întâi monitorizarea în pauză; vezi [Setările proiectului](/help/settings#editing).

## Autentificare {#credentials}

Deschideți **Autentificare** în același grup. Un proiect se poate autentifica în trei moduri.

- **Chei API de furnizor.** Alegeți o **Variabilă credențiale** (de exemplu OPENAI_API_KEY sau ANTHROPIC_API_KEY), introduceți **Cheie API** și alegeți **Salvează cheia API**. ADORE o stochează privat pe server și nu o mai afișează niciodată; **Deconectează cheia API a proiectului** o elimină. Variabila trebuie mai întâi listată în **Variabile de autentificare permise**, care conține doar nume (**Adaugă o variabilă de autentificare**). Schimbarea unei chei cere monitorizarea în pauză, un proiect inactiv și nicio modificare în așteptare, și nu testează cheia.
- **Abonament sau autentificare pe gazdă.** Agentul folosește propria autentificare de pe serverul ADORE, sub contul de serviciu, configurată în afara interfeței web (secțiunea **Autentificare prin abonament sau browser** indică comanda). **Folosește autentificarea agentului de pe gazdă** este o punte pilot care copiază acea autentificare în container, doar pentru OpenCode și Codex. Un abonament ChatGPT nu este o cheie API OpenAI.
- **Valori gestionate de mediu.** O variabilă deja setată în mediul serverului ADORE este etichetată **Setată pe serverul ADORE; administrată extern**. Interfața web nu o poate suprascrie.

Valorile credențialelor nu apar niciodată în revizuiri, înregistrări de audit sau exporturi. O listă goală de variabile este validă cu autentificarea existentă pe server.

## Testarea conexiunii AI {#test-connection}

Administratorii aleg **Testează conexiunea AI** sub **Conexiune AI**. Aceasta trimite o singură cerere scurtă prin agentul configurat, într-un container temporar, ceea ce poate genera costuri la furnizor. Proiectul trebuie să fie inactiv, cu setări salvate valide și fără modificări în așteptare; imaginea are nevoie de Python și de agent.

Rezultatul este **Model AI conectat** sau **Conexiunea AI nu a putut fi verificată**, cu îndrumări pentru o depășire a timpului, o imagine sau un agent lipsă, credențiale greșite sau un model indisponibil. Dovedește doar accesul la model, nu și suportul pentru instrumente, și nu pornește nicio lucrare. Rezultatul salvat este legat de modelul, setările și credențialele curente și apare în verificările gazdei din Rezumat. Dezvoltatorii îl văd, dar nu pot rula testul.

## Unde rulează lucrările {#where-jobs-run}

| | Container | Execuție locală nativă |
|---|---|---|
| Rulează în | Un container Docker sau Podman temporar pe serverul ADORE | Chiar serverul ADORE, sub contul de sistem de operare al serviciului, într-un worktree dedicat |
| Mediu | O imagine de proiect pregătită de administrator | Unelte, versiuni și biblioteci pe care le instalați singuri pe acel server |
| Autentificare | Chei API listate sau autentificare pe gazdă | Autentificarea existentă a agentului pe acel cont, reutilizată pe loc |
| Izolare | Container cu politică de rețea | Doar worktree-ul; comenzile pot ajunge oriunde poate ajunge contul, deci folosiți un cont dedicat cu privilegii minime |
| Alegere | Implicit pentru proiectele adăugate aici | În afara interfeței web, în profilul serverului sau prin înrolare TOML |

Verificările gazdei pentru un proiect local omit motorul de containere și verifică agentul nativ și autentificarea lui.

## Imaginea proiectului {#project-image}

Pentru un proiect cu container, Setări → Agent și model afișează **Executorul rulează într-un container**, **Imagine utilizată** și o secțiune **Instrucțiuni pentru pregătirea mediului**. Interfața web nu definește, nu construiește și nu selectează imaginea, iar adăugarea unui Dockerfile în repository nu pornește nicio construire. Administratorul face aceasta pe server:

1. Creați `executor/Dockerfile` în repository, pornind de la imaginea de bază ADORE, fără credențiale. Imaginea are nevoie de Python, sh și agentul selectat.
2. Construiți-o cu Docker sau Podman de pe server și verificați versiunile agentului și ale uneltelor.
3. Cu monitorizarea în pauză și fără lucrări active, setați `execution.backend`, `container.image` și `container.required_tool_checks` în `config.toml` al proiectului (administratorii văd calea lui în secțiunea de instrucțiuni), apoi validați profilul.

```
FROM adore-executor-base:1.0.0
USER root
# RUN ... install the project's system tools
USER adore
```

Apoi confirmați cu **Verifică cerințele gazdei** și **Testează conexiunea AI**.

## Endpoint local pentru OpenCode {#local-endpoint}

Pentru un proiect cu container care folosește OpenCode, administratorii văd în Agent și model și **URL endpoint compatibil OpenAI**, pentru un model servit în rețeaua dumneavoastră. Introduceți URL-ul, o **Referință la variabila de acreditare** opțională, **Timp limită pentru cerere (secunde)** și, pentru HTTPS cu un CA privat, **Fișier CA în imaginea executorului**. Protocolul este fixat la OpenAI chat completions. **Pregătește candidatul** revizuiește împreună URL-ul și modelul.

URL-ul trebuie să fie accesibil din interiorul containerului executorului, unde localhost este containerul însuși, iar imaginea trebuie să conțină deja pachetul furnizorului. Salvarea nu testează accesibilitatea și nu adaugă nicio alternativă cloud; **Verifică cerințele gazdei** testează un apel de unealtă în flux dintr-un container temporar.
