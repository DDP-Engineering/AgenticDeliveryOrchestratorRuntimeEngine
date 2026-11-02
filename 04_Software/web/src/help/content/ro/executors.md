# Executori și modele

Un executor este ceea ce ADORE lansează pentru fiecare lucrare: agentul de programare Pi și modelul AI pe care îl folosește. Administratorii aleg modelul în Setările unui proiect.

## Ce este un executor {#what}

Pentru fiecare lucrare, ADORE pornește Pi, singurul său agent de programare, într-o copie de lucru izolată, iar Pi parcurge etapele AEGIS ale repository-ului cu modelul configurat. Pi nu face niciodată commit sau push și nu vede credențialele forge; acestea le face ADORE. ADORE nu preia liste de modele. Într-un container, ADORE folosește Pi inclus în imaginea executorului; pentru un proiect instalat pe server, Pi trebuie să fie deja instalat pentru contul serverului. Modificările se aplică doar lucrărilor noi.

## Alegerea modelului {#agent-and-model}

Deschideți **Setări → Agent și model**. Rândurile sunt **Identificatorul modelului executorului** și **Comanda de lansare a executorului**.

Introduceți singuri ID-ul modelului: modelul Pi în forma `provider/model`, de exemplu `openai/gpt-5.4`. Nu există o valoare implicită universală. Într-un container, ADORE pornește singur Pi inclus în imagine, prin modul său RPC cu setări fixe, și îl oprește la limita de timp a etapei sau la anulare; acolo comanda de lansare nu este folosită, deci se oferă doar presetarea Pi. Pentru un proiect instalat pe server, comanda de lansare pornește Pi instalat, are implicit valoarea `pi -p --mode json --model {model} {prompt}`, trebuie să conțină `{prompt}` și nu poate folosi `--auto`. Fiecare rând este o setare obișnuită: **Pregătește candidatul** o revizuiește, iar **Aplică** o scrie. Așteptați-vă să puneți mai întâi monitorizarea în pauză; vezi [Setările proiectului](/help/settings#editing).

Un model servit în propria rețea printr-un endpoint compatibil OpenAI, de exemplu LM Studio, nu poate fi configurat în această versiune.

## Autentificare {#credentials}

Deschideți **Autentificare** în același grup. Un proiect se poate autentifica în trei moduri.

- **Chei API de furnizor.** Alegeți o **Variabilă credențiale** (de exemplu OPENAI_API_KEY sau ANTHROPIC_API_KEY), introduceți **Cheie API** și alegeți **Salvează cheia API**. ADORE o stochează privat pe server și nu o mai afișează niciodată; **Deconectează cheia API a proiectului** o elimină. Variabila trebuie mai întâi listată în **Variabile de autentificare permise**, care conține doar nume (**Adaugă o variabilă de autentificare**). Schimbarea unei chei cere monitorizarea în pauză, un proiect inactiv și nicio modificare în așteptare, și nu testează cheia.
- **Autentificarea existentă a contului.** Doar pentru un proiect instalat pe server: Pi folosește propria autentificare pentru contul serverului, configurată în afara interfeței web. Un proiect în container folosește întotdeauna chei API de furnizor; nicio autentificare nu este copiată în container.
- **Valori gestionate de mediu.** O variabilă deja setată în mediul serverului ADORE este etichetată **Setată pe serverul ADORE; administrată extern**. Interfața web nu o poate suprascrie.

Valorile credențialelor nu apar niciodată în revizuiri, înregistrări de audit sau exporturi. O listă goală de variabile este validă pentru un proiect instalat pe server care folosește autentificarea existentă a contului.

## Testarea conexiunii AI {#test-connection}

Administratorii aleg **Testează conexiunea AI** sub **Conexiune AI**. Aceasta trimite o singură cerere scurtă prin Pi, într-un container temporar sau, pentru Pi instalat pe server, într-un dosar temporar, ceea ce poate genera costuri la furnizor. Proiectul trebuie să fie inactiv, cu setări salvate valide și fără modificări în așteptare; pentru un proiect în container, imaginea configurată trebuie să existe pe server.

Rezultatul este **Model AI conectat** sau **Conexiunea AI nu a putut fi verificată**, cu îndrumări pentru o depășire a timpului, o imagine sau un Pi lipsă, credențiale greșite, un model indisponibil sau o comandă shell pe care Pi nu a putut-o rula. Într-un container, Pi răspunde fără să folosească unelte, deci testul dovedește doar accesul la model. Pentru Pi instalat pe server, cererea îi cere lui Pi să ruleze și o comandă shell, iar rezultatul este conectat doar dacă acea comandă a rulat. Nu pornește nicio lucrare. Rezultatul salvat este legat de modelul, setările și credențialele curente și apare în verificările gazdei din Rezumat. Dezvoltatorii îl văd, dar nu pot rula testul.

## Unde rulează lucrările {#where-jobs-run}

| | Container | Execuție locală nativă |
|---|---|---|
| Rulează în | Un container Docker sau Podman temporar pe serverul ADORE | Chiar serverul ADORE, sub contul de sistem de operare al serviciului, într-un worktree dedicat |
| Mediu | O imagine de proiect pregătită de administrator | Unelte, versiuni și biblioteci pe care le instalați singuri pe acel server |
| Autentificare | Chei API de furnizor listate | Chei API de furnizor listate sau autentificarea Pi existentă pe acel cont, reutilizată pe loc |
| Setările agentului | Pi inclus în imagine, cu setări stabilite de ADORE; setările și abilitățile Pi personale nu sunt citite | Pi instalat pentru acel cont, pornit cu comanda de lansare și cu setările Pi ale acelui cont |
| Izolare | Container cu politică de rețea | Doar worktree-ul; comenzile pot ajunge oriunde poate ajunge contul, deci folosiți un cont dedicat cu privilegii minime |
| Alegere | **Rulează în** → **Container**, implicit, la pasul 2 al înrolării sau în Setări → Agent și model | **Rulează în** → **Instalat pe server**, sau în profilul serverului ori prin înrolare TOML |

Modificările din Setări trec prin **Pregătește candidatul**, revizuire și **Aplică**. **Instalat pe server** afișează comanda nativă a executorului și câmpurile contului local (contul `current`, directorul home, PATH și, pe Linux, rădăcina cgroup), împreună cu avizul despre execuția locală.

Verificările gazdei pentru un proiect local omit motorul de containere și verifică Pi instalat și autentificarea sau cheia API a acestuia.

## Imaginea proiectului {#project-image}

Pentru un proiect cu container, Setări → Agent și model afișează **Executorul rulează într-un container**, **Imagine utilizată** și o secțiune **Instrucțiuni pentru pregătirea mediului**. Interfața web nu definește și nu construiește imaginea, iar adăugarea unui Dockerfile în repository nu pornește nicio construire. Administratorul o pregătește pe server:

1. Creați `executor/Dockerfile` în repository, pornind de la imaginea de bază ADORE, fără credențiale. Imaginea de bază conține deja Python, sh și Pi la versiunea fixată.
2. Construiți-o cu Docker sau Podman de pe server și verificați versiunile uneltelor.
3. Selectați imaginea în interfața web, așa cum este descris mai jos, sau, cu monitorizarea în pauză și fără lucrări active, setați `execution.backend`, `container.image` și `container.required_tool_checks` în `config.toml` al proiectului (administratorii văd calea lui în secțiunea de instrucțiuni), apoi validați profilul.

```
FROM adore-executor-base:1.0.0
USER root
# RUN ... install the project's system tools
USER adore
```

Pentru a folosi imaginea, alegeți **Motor de containere** (Docker sau Podman) și **Imagine executor** la pasul 2 al înrolării sau modificați aceleași rânduri în Setări. Imaginea este un câmp liber cu sugestii citite din imaginile de pe serverul ADORE pentru acel motor (doar administratori); apare un aviz când imaginea introdusă nu este pe server și altul când lista nu poate fi citită.

Apoi confirmați cu **Verifică cerințele gazdei** și **Testează conexiunea AI**.
