# Executori și modele

Un executor este ceea ce ADORE lansează pentru fiecare lucrare: agentul de programare Pi și modelul AI pe care îl folosește. Administratorii aleg modelul în Setările unui proiect.

## Ce este un executor {#what}

Pentru fiecare lucrare, ADORE pornește Pi, singurul său agent de codare, într-o copie de lucru izolată, iar Pi parcurge etapele AEGIS ale repository-ului cu furnizorul și modelul configurate. Pi nu face commit, nu face push și nu vede credențiale de forge; ADORE se ocupă de acestea. În container, ADORE folosește Pi inclus în imaginea executorului; pentru un proiect instalat pe server, Pi trebuie să fie deja instalat pentru contul serverului. Modificările se aplică doar lucrărilor noi.

## Alegerea furnizorului și a modelului {#agent-and-model}

Deschideți **Setări → Agent și model**. Rândurile sunt **Furnizor**, **Model**, **Comanda de lansare a executorului** și, pentru un endpoint, **Adresa de bază a endpointului** și **Tipul API al endpointului**. **Modifică** pe oricare dintre rândurile de furnizor, model sau endpoint deschide un singur editor pentru toate, revizuite și aplicate ca o singură modificare.

- **Furnizor**: unul dintre furnizorii Pi cu cheie API (OpenAI, Anthropic, Google Gemini, OpenRouter, Mistral și alții), **Abonament ChatGPT** sau **Endpoint compatibil OpenAI**.
- **Model**: alegeți din lista Pi pentru acel furnizor sau scrieți orice ID de model acceptat de furnizor, de exemplu `gpt-5.4`. Lista vine cu versiunea Pi livrată de ADORE și se citește fără acces la internet. Nu există un model implicit universal.
- **Abonament ChatGPT**: Pi folosește contul ChatGPT Plus sau Pro cu care este autentificat acest server ADORE, vezi [Autentificare cu ChatGPT](#chatgpt). Lista conține modelele servite de un abonament ChatGPT, de exemplu `gpt-5.6-luna`.

**Pregătește candidatul** arată valoarea activă și propusă a fiecărui câmp, iar **Aplică** le scrie; așteptați-vă să opriți mai întâi monitorizarea, vedeți [Setările proiectului](/help/settings#editing). În container, ADORE pornește singur Pi inclus în imagine, prin modul său RPC cu setări fixe, și îl oprește la limita de timp a etapei sau la anulare; comanda de lansare nu este folosită acolo, deci este oferită doar presetarea Pi. Pentru un proiect instalat pe server, comanda de lansare pornește Pi instalat, are implicit valoarea `pi -p --mode json --model {model} {prompt}` (`{model}` devine furnizor/model), trebuie să conțină `{prompt}` și nu trebuie să folosească `--auto`.

## Endpoint compatibil OpenAI {#endpoint}

Pentru un model servit în propria rețea, de exemplu LM Studio, Ollama sau vLLM, alegeți **Endpoint compatibil OpenAI** și completați:

- **Adresa de bază a endpointului**: adresa văzută din container, de exemplu `http://192.168.1.20:1234/v1`. `localhost` este containerul însuși. `host.docker.internal` ajunge la gazdă doar cu Docker Desktop; cu Docker Engine pe Linux sau în WSL folosiți adresa de rețea a gazdei, iar pentru un server pe Windows accesat din Docker în WSL, gateway-ul implicit al WSL.
- **Tipul API al endpointului**: `openai-completions` pentru LM Studio, Ollama și vLLM; sunt acceptate și `openai-responses`, `anthropic-messages` și `google-generative-ai`.
- **Model**: ID-ul modelului servit de endpoint.

Cheia endpointului este opțională: salvați-o la Autentificare ca ADORE_ENDPOINT_API_KEY. ADORE descrie endpointul lui Pi pentru fiecare lucrare; adresa nu conține niciodată nume de utilizator, parolă sau interogare. Cu [accesul la internet](#internet) dezactivat, ADORE permite singur adresa endpointului. Un endpoint este disponibil doar pentru proiectele în container.

## Autentificare {#credentials}

Deschideți **Autentificare** în același grup.

- **Cheia API a furnizorului.** Panoul numește variabila de care are nevoie furnizorul configurat, de exemplu OPENAI_API_KEY pentru OpenAI sau ANTHROPIC_API_KEY pentru Anthropic. Introduceți **Cheie API** și alegeți **Salvează cheia API**. ADORE o păstrează privat în depozitul de credențiale al proiectului pe server, niciodată în fișierul de configurare, o transmite lui Pi doar ca acea variabilă și nu o mai afișează niciodată; **Deconectează cheia API a proiectului** o elimină. Schimbarea unei chei cere monitorizarea oprită, un proiect inactiv și nicio propunere în așteptare și nu testează cheia.
- **Autentificarea existentă a contului.** Doar pentru un proiect instalat pe server: Pi folosește propria autentificare pentru contul serverului, configurată în afara interfeței web. Un proiect în container folosește cheia API a furnizorului sau, pentru un abonament ChatGPT, un token de acces de scurtă durată din [autentificarea ChatGPT](#chatgpt) a serverului; nicio autentificare nu este copiată în container.
- **Valori gestionate de mediu.** O variabilă deja setată în mediul serverului ADORE poartă eticheta **Setată pe serverul ADORE; administrată extern**. Interfața web nu o poate suprascrie.
- **Cheia de căutare web.** Cu accesul la internet activat și căutarea web Brave sau Tavily, panoul listează și BRAVE_API_KEY sau TAVILY_API_KEY, salvată la fel, și pentru un abonament ChatGPT.
- **Variabile de autentificare suplimentare.** Doar nume (**Adaugă o variabilă de autentificare**) ale unor secrete suplimentare primite de Pi pe lângă cheia furnizorului; majoritatea proiectelor nu au nevoie de ele.

Valorile credențialelor nu apar niciodată în fișierul de configurare, în revizuiri, în înregistrările de audit, în jurnale sau în exporturi.

## Autentificare cu ChatGPT {#chatgpt}

Un singur cont ChatGPT Plus sau Pro servește toate proiectele de pe acest server ADORE al căror furnizor este **Abonament ChatGPT**. Administratorii se autentifică în **Autentificare** a unui astfel de proiect; ADORE rulează autentificarea OpenAI a lui Pi, deci serverul nu are nevoie de browser.

1. Alegeți **Autentificare cu ChatGPT**.
2. Deschideți **Deschide pagina de autentificare ChatGPT** pe calculatorul dumneavoastră și autentificați-vă cu contul ChatGPT. Linkul este valabil 15 minute.
3. Browserul afișează apoi o pagină de eroare la `127.0.0.1:1455`. Este normal: copiați adresa completă din bara de adrese.
4. Lipiți-o în **Adresa de redirecționare** și alegeți **Finalizează autentificarea**.

Starea este **Autentificat**, **Neautentificat** sau **Autentifică-te din nou**. **Autentifică-te din nou** înseamnă că OpenAI nu mai acceptă autentificarea salvată; lucrările eșuează până când un administrator se autentifică din nou. O adresă de la un link mai vechi este refuzată, iar autentificarea așteaptă în continuare; **Anulează** o încheie. Când OpenAI refuză contul, de exemplu pentru că abonamentul lui nu poate fi partajat, autentificarea se încheie cu acest motiv. **Deconectează ChatGPT** șterge autentificarea salvată.

Autentificarea rămâne într-un dosar privat pe serverul ADORE. Înaintea fiecărei etape, ADORE obține din ea un token de acces nou, valabil aproximativ o oră, și transmite lui Pi doar acest token; autentificarea însăși nu intră niciodată în containerul lucrării. De aceea un proiect ChatGPT rulează în container, limitele de timp ale etapelor sunt de cel mult 3000 de secunde, iar imaginea lui trebuie construită din imaginea curentă a executorului ADORE. Doar administratorii văd sau modifică autentificarea; înregistrările de audit numesc acțiunea, niciodată un token sau o adresă.

> ADORE este gratuit astăzi. Oferirea lui ca serviciu găzduit sau plătit cu autentificare ChatGPT ar necesita mai întâi formularul de interes al OpenAI.

## Testarea conexiunii AI {#test-connection}

Administratorii aleg **Testează conexiunea AI** la **Conexiune AI**. Testul pornește Pi o dată într-un container temporar, sau într-un dosar temporar pentru Pi instalat pe server, îi cere să ruleze o comandă shell și apoi să răspundă cu un text fix și poate genera costuri la furnizor. Proiectul trebuie să fie inactiv, cu setări salvate valide și fără propunere în așteptare; pentru un proiect în container, imaginea configurată trebuie să existe pe server.

Rezultatul este **Model AI conectat** doar dacă comanda shell a rulat și răspunsul a sosit. Altfel, **Conexiunea AI nu a putut fi verificată** vine cu îndrumări proprii pentru: nicio credențială salvată, nicio autentificare ChatGPT, un abonament ChatGPT care nu poate fi partajat, o limită de utilizare ChatGPT atinsă, o cheie respinsă de furnizor, un furnizor sau endpoint la care Pi nu a putut ajunge, un model necunoscut furnizorului sau endpointului, o limită de rată, altă eroare a furnizorului, depășirea timpului, o imagine sau un Pi lipsă, ori o comandă shell pe care Pi nu a putut-o rula. Nu pornește nicio lucrare. Rezultatul salvat este legat de furnizorul, modelul, setările și credențialele actuale și apare în verificările gazdei din Rezumat. Dezvoltatorii îl văd, dar nu pot rula testul.

## Acces la internet pentru agent {#internet}

**Acces la internet pentru agent** din Setări → Agent și model decide ce poate accesa containerul unei lucrări. Implicit este **Dezactivat**.

- **Dezactivat**: containerul ajunge doar la furnizorul modelului. ADORE permite singur adresele furnizorului, pentru un endpoint compatibil OpenAI adresa acestuia, printr-un proxy de rețea separat pentru fiecare lucrare. Căutarea web, citirea paginilor și descărcările precum `curl`, `npm install` sau `pip install` eșuează, iar Pi este anunțat.
- **Activat**: containerul are rețea deschisă. Pi poate căuta pe web, citi pagini și descărca biblioteci cu `curl`, `npm` sau `pip`.

**Căutare web** alege serviciul de căutare cât timp accesul este activat: **Exa (fără cheie)**, implicit, **Brave (necesită cheie)**, **Tavily (necesită cheie)** sau **Niciuna** (fără căutare web sau citirea paginilor). Pentru Brave sau Tavily, salvați BRAVE_API_KEY sau TAVILY_API_KEY la **Autentificare**.

> Cu accesul la internet activat, o pagină web rău intenționată ar putea încerca să facă agentul să trimită cheia API sau tokenul ChatGPT. Preferă chei limitate și de scurtă durată.

Ambele setări se schimbă prin **Pregătește candidatul** și **Aplică**, ca celelalte. Cu accesul la internet dezactivat, imaginea proxyului trebuie să existe pe serverul ADORE; **Verifică cerințele gazdei** o raportează, la fel și cheia de căutare când este necesară. Pentru un proiect instalat pe server, comutatorul apare ca **Neaplicat**: Pi ajunge oriunde ajunge serverul.

## Unde rulează lucrările {#where-jobs-run}

| | Container | Execuție locală nativă |
|---|---|---|
| Rulează în | Un container Docker sau Podman temporar pe serverul ADORE | Chiar serverul ADORE, sub contul de sistem de operare al serviciului, într-un worktree dedicat |
| Mediu | O imagine de proiect pregătită de administrator | Unelte, versiuni și biblioteci pe care le instalați singuri pe acel server |
| Autentificare | Cheia API a furnizorului sau, pentru un abonament ChatGPT, un token de acces de scurtă durată din autentificarea ChatGPT a serverului | Cheia API a furnizorului sau autentificarea Pi existentă pe acel cont, reutilizată pe loc |
| Setările agentului | Pi inclus în imagine, cu setări stabilite de ADORE; setările și abilitățile Pi personale nu sunt citite | Pi instalat pentru acel cont, pornit cu comanda de lansare și cu setările Pi ale acelui cont |
| Izolare | Container; cu accesul la internet dezactivat ajunge doar la furnizorul modelului | Doar worktree-ul; comenzile pot ajunge oriunde poate ajunge contul, deci folosiți un cont dedicat cu privilegii minime |
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
