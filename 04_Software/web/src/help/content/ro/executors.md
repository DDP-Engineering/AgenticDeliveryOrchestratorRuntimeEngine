# Executori și modele

Un executor este ceea ce ADORE lansează pentru fiecare lucrare: agentul de programare Pi și modelul AI pe care îl folosește. Administratorii aleg modelul în Setările unui proiect.


**Efort de raționament** oferă nivelurile acceptate de model în catalogul Pi inclus. Implicit Pi lasă alegerea în seama Pi. Modelele nelistate și endpointurile proprii nu pot pretinde niveluri neconfirmate. Alegerea se aplică lucrărilor și testului conexiunii AI.

## Ce este un executor {#what}

Pentru fiecare lucrare, ADORE pornește Pi, singurul său agent de codare, într-o copie de lucru izolată, iar Pi parcurge etapele AEGIS ale repository-ului cu furnizorul și modelul configurate. ADORE folosește Pi din imagine pentru lucrările în container și instalarea Pi administrată de ADORE pentru lucrările pe server.

## Alegerea furnizorului și a modelului {#agent-and-model}

Deschideți **Setări → Agent și model**. Editați împreună **Furnizor**, **Model** și, pentru un endpoint, **URL de bază al endpointului** și **Tip API al endpointului** ca o singură modificare revizuită.

- **Furnizor**: unul dintre furnizorii Pi cu cheie API (OpenAI, Anthropic, Google Gemini, OpenRouter, Mistral și alții), **Abonament ChatGPT** sau **Endpoint compatibil OpenAI**.
- **Model**: alegeți din lista Pi pentru acel furnizor sau scrieți orice ID de model acceptat de furnizor, de exemplu `gpt-5.4`. Lista vine cu versiunea Pi livrată de ADORE și se citește fără acces la internet. Nu există un model implicit universal.
- **Abonament ChatGPT**: Pi folosește contul ChatGPT Plus sau Pro cu care este autentificat acest server ADORE, vezi [Autentificare cu ChatGPT](#chatgpt). Lista conține modelele servite de un abonament ChatGPT, de exemplu `gpt-5.6-luna`.

**Salvează** scrie împreună setările editate după confirmarea efectelor importante; vezi [Setările proiectului](/help/settings#editing) pentru pauza monitorizării. ADORE pornește un proces Pi nou la fiecare etapă și îl oprește la expirarea timpului sau la anulare.

## Endpoint compatibil OpenAI {#endpoint}

Pentru un model servit în propria rețea, de exemplu LM Studio, Ollama sau vLLM, alegeți **Endpoint compatibil OpenAI** și completați:

- **Adresa de bază a endpointului**: adresa așa cum o vede Pi. Pentru **Container**, adresa este cea văzută din container; pentru o lucrare locală, este cea văzută de server.
- **Tipul API al endpointului**: `openai-completions` pentru LM Studio, Ollama și vLLM; sunt acceptate și `openai-responses`, `anthropic-messages` și `google-generative-ai`.
- **Model**: ID-ul modelului servit de endpoint.

Cheia endpointului este opțională: salvați-o la Autentificare ca ADORE_ENDPOINT_API_KEY. ADORE descrie endpointul lui Pi pentru fiecare lucrare; adresa nu conține niciodată nume de utilizator, parolă sau interogare. Cu [accesul la internet](#internet) dezactivat, ADORE permite singur adresa endpointului. Un endpoint este disponibil atât în container, cât și pe server.

## Autentificare {#credentials}

Deschideți **Autentificare** în același grup.

- **Cheia API a furnizorului.** Panoul numește variabila de care are nevoie furnizorul configurat, de exemplu OPENAI_API_KEY pentru OpenAI sau ANTHROPIC_API_KEY pentru Anthropic. Introduceți **Cheie API** și alegeți **Salvează cheia API**. ADORE o păstrează privat în depozitul de credențiale al proiectului pe server, niciodată în fișierul de configurare, o transmite lui Pi doar ca acea variabilă și nu o mai afișează niciodată; **Deconectează cheia API a proiectului** o elimină. Schimbarea unei chei cere monitorizarea oprită, un proiect inactiv și nicio propunere în așteptare și nu testează cheia.
- **Proiecte pe server.** Salvați **Cheia API a furnizorului** dacă este necesară. ADORE ignoră autentificarea Pi personală. Folosiți [autentificarea ChatGPT](#chatgpt) comună pentru abonament pe Windows sau Linux, inclusiv WSL2.
- **Valori gestionate de mediu.** O variabilă deja setată în mediul serverului ADORE poartă eticheta **Setată pe serverul ADORE; administrată extern**. Interfața web nu o poate suprascrie.
- **Cheia de căutare web.** Cu accesul la internet activat și căutarea web Brave sau Tavily, panoul listează și BRAVE_API_KEY sau TAVILY_API_KEY, salvată la fel, și pentru un abonament ChatGPT.
- **Variabile de autentificare suplimentare.** Doar nume (**Adaugă o variabilă de autentificare**) ale unor secrete suplimentare primite de Pi pe lângă cheia furnizorului; majoritatea proiectelor nu au nevoie de ele.

Valorile credențialelor nu apar niciodată în fișierul de configurare, în revizuiri, în înregistrările de audit, în jurnale sau în exporturi.

## Autentificare cu ChatGPT {#chatgpt}

Un singur cont ChatGPT Plus sau Pro servește toate proiectele de pe acest server ADORE al căror furnizor este **Abonament ChatGPT**. Administratorii se autentifică în **Autentificare** a unui astfel de proiect; ADORE rulează autentificarea OpenAI a lui Pi, deci serverul nu are nevoie de browser.

Pe serverul nativ, Pi poate primi direct redirecționarea browserului, iar ADORE afișează automat finalizarea. Dacă rămâne în așteptare, folosiți pașii manuali de redirecționare de mai jos.

1. Alegeți **Autentificare cu ChatGPT**.
2. Deschideți **Deschide pagina de autentificare ChatGPT** pe calculatorul dumneavoastră și autentificați-vă cu contul ChatGPT. Linkul este valabil 15 minute.
3. Browserul afișează apoi o pagină de eroare la `127.0.0.1:1455`. Este normal: copiați adresa completă din bara de adrese.
4. Lipiți-o în **Adresa de redirecționare** și alegeți **Finalizează autentificarea**.

Starea este **Autentificat**, **Neautentificat** sau **Autentifică-te din nou**. **Autentifică-te din nou** înseamnă că OpenAI nu mai acceptă autentificarea salvată; lucrările eșuează până când un administrator se autentifică din nou. O adresă de la un link mai vechi este refuzată, iar autentificarea așteaptă în continuare; **Anulează** o încheie. Când OpenAI refuză contul, de exemplu pentru că abonamentul lui nu poate fi partajat, autentificarea se încheie cu acest motiv. **Deconectează ChatGPT** șterge autentificarea salvată.

Autentificarea rămâne într-un dosar privat pe serverul ADORE. Înaintea fiecărei etape, ADORE obține din ea un token de acces nou, valabil aproximativ o oră, și transmite lui Pi doar acest token; autentificarea însăși nu intră niciodată în containerul lucrării. Proiectele ChatGPT rulează în containere sau nativ pe Windows/Linux, inclusiv WSL2. Autentificarea nativă folosește Pi administrat de ADORE fără Docker; containerele folosesc imaginea curentă a executorului ADORE. Limitele etapelor sunt de cel mult 3000 de secunde în ambele medii. Doar administratorii văd sau modifică autentificarea; înregistrările de audit numesc acțiunea, niciodată un token sau o adresă.

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

Folosește **Salvează** pentru ambele setări și confirmă efectele importante. Cu accesul la internet dezactivat, imaginea proxyului trebuie să existe pe serverul ADORE; **Verifică cerințele gazdei** o raportează, la fel și cheia de căutare când este necesară. Pentru un proiect instalat pe server, comutatorul apare ca **Neaplicat**: Pi ajunge oriunde ajunge serverul.

## Unde rulează lucrările {#where-jobs-run}

| | Container | Execuție locală nativă |
|---|---|---|
| Rulează în | Un container Docker sau Podman temporar pe serverul ADORE | Chiar serverul ADORE, sub contul de sistem de operare al serviciului, într-un worktree dedicat |
| Mediu | O imagine de proiect pregătită de administrator | Unelte, versiuni și biblioteci pe care le instalați singuri pe acel server |
| Autentificare | Cheia API a furnizorului sau, pentru un abonament ChatGPT, un token de acces de scurtă durată din autentificarea ChatGPT a serverului | Cheia furnizorului sau un token temporar din autentificarea ChatGPT a serverului |
| Setările agentului | Pi inclus în imagine, cu setări stabilite de ADORE; setările și abilitățile Pi personale nu sunt citite | Pi administrat de ADORE cu setări și extensii proprii |
| Izolare | Container; cu accesul la internet dezactivat ajunge doar la furnizorul modelului | Doar worktree-ul; comenzile pot ajunge oriunde poate ajunge contul, deci folosiți un cont dedicat cu privilegii minime |
| Alegere | **Rulează în** → **Container**, implicit, la pasul 2 al înrolării sau în Setări → Agent și model | **Rulează în** → **Instalat pe server**, sau în profilul serverului ori prin înrolare TOML |

**Instalat pe server** rulează Pi sub contul de sistem al serviciului ADORE. **PATH pentru uneltele proiectului** stabilește unde caută Pi uneltele. Un câmp gol folosește PATH-ul contului serviciului. Comanda de lansare este fixă.

**Verifică cerințele gazdei** omite motorul de containere și verifică Node, instalarea Pi administrată și credențialele furnizorului ales.

## Instalarea Pi pe server {#installed-executors}

Rulați `adore pi install` și `adore pi verify` pe serverul ADORE sub contul serviciului. Folosiți Node 22.23.4 sau ulterior din seria 22.x, cu npm. Dacă Node nu este în PATH-ul serviciului, setați `ADORE_NODE` la calea sa absolută.

Rulați din nou `adore pi install` când o versiune ADORE cere altă versiune Pi. Nu este nevoie de Pi global; setările și extensiile personale sunt ignorate.

Windows folosește unealta PowerShell; în Linux administratorul serverului configurează o rădăcină cgroup v2 delegată. Pi nu cere permisiuni. Folosiți un cont de sistem dedicat.

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

În Setări, editează **Motor de containere** ca să alegi Docker sau Podman detectat pe server, inclusiv în WSL pe Windows. Alege **Comandă manuală pentru container** ca să introduci propria comandă, apoi apasă **Salvează**. Verificarea cerințelor gazdei caută Pi în imaginea aleasă.

Pentru o comandă WSL personalizată, puneți `--` sau `--exec` înaintea comenzii containerului. Opțiunile standard Docker și Podman sunt tratate automat.

Apoi confirmați cu **Verifică cerințele gazdei** și **Testează conexiunea AI**.

## Pachete de sistem {#system-packages}

Un administrator poate revizui **Permite agentului instalarea pachetelor de sistem** în **Setări → Agent și model**. Implicit este oprită și este disponibilă doar pentru containere. Pi poate instala direct cu `sudo -n`, citi rezultatele și adapta pașii în limitele lucrării. **Acces la internet pentru agent** rămâne o alegere separată; când este oprit, sursele externe cer o gazdă permisă. Folosiți o imagine cu sudo, puneți monitorizarea în pauză și așteptați încheierea lucrului activ înainte de aplicare, apoi porniți o lucrare nouă. Pachetele rămân în acel container și nu modifică imaginea.
