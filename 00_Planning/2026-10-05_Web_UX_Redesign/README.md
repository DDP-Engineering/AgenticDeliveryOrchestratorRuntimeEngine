<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# ADORE Web — analiză și direcție UX

Acest director conține exclusiv material de planificare autorizat pentru analiza din 5 octombrie 2026. Nu modifică aplicația, configurația sau datele ADORE și nu folosește workflow-ul AEGIS.

Începe cu [propunerea completă](./Propunere_UX.md), apoi deschide [prototipul HTML navigabil](./Prototip.html) într-un browser. Prototipul funcționează ca fișier local, fără instalare, server sau acces la internet. Toate datele și operațiile sunt demonstrative.

Păstrează DDP_Engineering_logo_dark.png lângă fișierul HTML pentru afișarea identității firmei.

Pentru evaluarea importului: Proiecte → Importă setări → Continuă → Folosește fișierul demonstrativ. Pentru configurația TOML existentă, alege opțiunea Avansat în primul pas. Revizuirea finală permite revenirea la alegeri.

| Ecran | Implementarea actuală, date fixture | Direcția propusă, date fictive |
| --- | --- | --- |
| Overview | [Captură actuală](./current-overview.png) | [Captură propusă](./proposal-overview.png) |
| Înrolare | [Captură actuală](./current-enrolment.png) | [Pas repository](./proposal-enrolment.png), [Recapitulare](./proposal-review.png) |
| Import | [Captură actuală](./current-import.png) | [Import portabil](./proposal-import.png), [TOML existent](./proposal-toml-import.png), [Mobil](./proposal-import-mobile.png) |
| Configurare | [Captură actuală](./current-configuration.png) | [Diferență înainte/după](./proposal-configuration.png) |
| Job-uri | [Captură actuală](./current-jobs.png) | [Detaliu și următorul pas](./proposal-job.png) |
| Statistici | [Captură actuală](./current-metrics.png) | [Scope și acoperire](./proposal-statistics.png) |
| Utilizatori | [Captură actuală](./current-users.png) | Pagina Utilizatori în prototip |
| Istoric | [Captură actuală](./current-audit.png) | Pagina Istoric modificări în prototip |

Prototipul a fost parcurs în browser pentru înrolare nouă, clonare, import portabil și TOML existent. S-au verificat păstrarea datelor la Înapoi, blocarea continuării fără exemplu, filtrele statistice demonstrative și alegerea admin/dev. Aspectul importului a fost verificat la 1440 px și 390 px, fără overflow orizontal în acele ecrane.

Aceste verificări privesc documentul HTML. Nu sunt teste de integrare ADORE, nu verifică mediul operatorului și nu demonstrează încă înțelegerea fluxului de către utilizatori nefamiliarizați.

## Sigla DDP Engineering

Sigla din [PNG pentru interfață](./DDP_Engineering_logo.png) a fost izolată din stratul grafic încorporat în DDP_REGENERAT_FATA_layout.svg, din directorul furnizat de utilizator: D:/ProjectsDDP/DDP_Engineering/Carti de vizita/BunDeTipar3/.

Metodă: [SVG de extragere](./DDP_Engineering_logo.svg) cu viewport x=80, y=205, lățime=630, înălțime=300 în coordonatele rasterului sursă 1533×1026; apoi randare PNG 630×300. Datele raster încorporate în SVG au fost păstrate neschimbate. Nu a fost folosită regenerare AI, redesenare sau vectorizare. Desenul, culorile și fondul deschis texturat provin din materialul furnizat. PNG-ul nu este transparent, iar SVG-ul este un container pentru raster, nu o siglă vectorială.

SHA-256 al SVG-ului sursă: 0fb248353b7844cc08a5e500593b81021cf9b1c862055ed2ca37e63989a1b9e3.

Acest PNG albastru este păstrat ca sursă; SVG-ul mai mare este păstrat pentru trasabilitate. Materialele sursă nu au fost modificate. Un master vectorial autentic ar permite ulterior scalare independentă de rezoluție.

După integrare au fost verificate încărcarea siglei, proporțiile și aspectul pe desktop și mobil. Capturile proposal-*.png includ această identitate.

### Varianta pentru panoul închis

La cererea utilizatorului, fundalul deschis și chenarul au fost eliminate. Prototipul folosește [PNG cu transparență](./DDP_Engineering_logo_dark.png), 630×300 px, cu verde pal (#B8D1C4) pe fondul panoului #102F29.

[SVG-ul de adaptare](./DDP_Engineering_logo_dark.svg) încorporează PNG-ul albastru neschimbat și aplică un filtru nativ: RGB constant, iar alpha este clamp(1.8 × (0.92 − luminanța sRGB), 0, 1). Fondul aproape alb devine transparent, iar geometria originală a siglei este păstrată. PNG-ul final este randat din SVG cu fundalul paginii omis, păstrând alpha. Aceasta nu transformă sursa într-o siglă vectorială.

O probă realizată cu instrumentul integrat image_gen a fost respinsă la verificare pentru urme nedorite pe margini și nu este utilizată în prototip. Varianta finală este adaptarea deterministă descrisă mai sus. Promptul probei este păstrat în [nota de variantă](./Sigla_varianta.md).
