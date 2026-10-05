<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Sigla pentru panoul închis

Rezultat ales: DDP_Engineering_logo_dark.png, randat din DDP_Engineering_logo_dark.svg, folosind contururile sursei existente. Fond transparent, verde pal, fără placă albă. Varianta albastră și extragerea inițială sunt păstrate separat.

O probă cu instrumentul integrat image_gen, în modul edit cu transparent_background=true, a produs margini nedorite. Nu a fost aleasă și nu este utilizată de prototip. Nu a fost folosit fallback CLI/API.

## Promptul exact al probei neutilizate

Use case: background-extraction. Asset type: an existing company logo used at small size in a dark web dashboard sidebar. Input image: edit target, the supplied DDP Engineering logo. Edit this image only: remove the white textured paper background completely and deliver genuine transparent alpha. Recolor the existing logo foreground to a restrained light sage/ivory palette suited to sidebar background #102F29: main gear, circuit tracks and custom DDP glyphs #BDD9CD, waveform and underline a slightly muted mint #8FBEAA, ENGINEERING lettering #BCD2C8. Preserve the exact distinctive DDP lettering silhouettes, half gear outline, every circuit track and node, waveform shape, original horizontal composition, relative spacing and proportions. Text verbatim: DDP, ENGINEERING. Do not redesign or substitute a typeface, do not add or remove marks. Flat clean edges, no glow, shadow, bevel, paper texture, border, rectangular panel, checkerboard or dark backdrop. Keep a tightly fitted wide canvas with only small transparent margins. The background and inner negative spaces must be transparent.

## Adaptarea finală

În SVG, filtrul feColorMatrix fixează RGB la (0.7216, 0.8196, 0.7686) și calculează alpha din luminanța rasterului, eliminând fondul aproape alb. Geometria nu este regenerată. Fundalul panoului este #102F29. Asset-ul final PNG 630×300 este randat cu alpha; fișierele consumate de prototip sunt în același director.

