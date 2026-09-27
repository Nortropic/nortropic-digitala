# Bild — val, licens, autenticitet, art direction, beskärning, storlekar och optimering

Professionsfil (HELHET-20260927, avsnitt 5). Laddas i steget `brief` (§8) och `bygge`. Verktygen i `verktyg/bild/`
(`treatment.mjs`, `brand.mjs`, `score.mjs`) är återvunna ur det arkiverade repot (revision `e4c8c52`, 2026-09-10) och
körs i kundrepot med `sharp` som kundrepots beroende; anskaffning genom bildgenereringstjänst (det gamla
`fetch-images.mjs`, fal.ai) är inte återinförd: den kräver konto och kostnad och är ett ägarbeslut per kund.

## Anspråk avgör vad en bild får vara

| Anspråk (`claim`) | Betyder | Får komma från |
|---|---|---|
| `none` | dekor, stämning | kundens foton, licensierad stock, generering |
| `illustrative` | illustrerar tjänsten eller miljön utan att påstå att det är kundens | kundens foton, licensierad stock, generering, alltid märkt i platsplanen |
| `depicts_client_work` | visar kundens faktiska arbete | bara kundens egna foton med rättigheter |
| `depicts_client_people` | visar kundens personer | bara kundens egna foton med samtycke |

Genererade eller köpta bilder framställs aldrig som kundens verkliga personer, projekt, meriter eller omdömen
(ordern avsnitt 5). Ett fotouppdrag till kunden ("ta en sådan här, fast er egen") skrivs när material saknas.

## Val och licens

Kundens eget material först; rättighetsläget per bild (vem tog den, vem äger den, får den publiceras, finns
samtycke). Stock med licens som tillåter kommersiell webbpublicering; licensen sparas i kundmappen
(`bilder/LICENSER.md`). Bilder med okänt ursprung används inte.

## Art direction

Bildspår ur briefen: foto-först (kunden har bärande foton), bevis-först (arbetet talar: före/efter, resultat,
detaljer), typografi-först (bilder är stöd, typografin bär). Ett spår är ett val med skäl, inte en tröskeltabell.
Presetbehandling (`duotone`, `dokumentar`, `ljus` i `treatment.mjs`) är alternativ som ger sammanhållning över
bilder av olika ursprung; ingen är standard, och ett kundmaterial som redan håller ihop behandlas inte.

## Beskärning, storlekar och optimering

Platsplan i briefen §8: bildplats (`hero-*`, `env-*`, `proof-*`, `people-*`, `detail-*`), sida, källa, anspråk,
status. Filnamn `<plats>__<beskrivning>.<ext>`. Beskärningar per plats (första vyn 16:9 och 4:5 för mobil, 3:2 för
miljö, kvadrat för porträtt) och responsiva storlekar med `sizes`; AVIF/WebP med kvalitetsloop mot en viktbudget
(förslag: första vyns bild ≤ 150 kB, porträtt ≤ 100 kB, övriga ≤ 120 kB; budgeten sätts i briefen §9, inte här).
Explicita mått på varje bild (ingen layoutförskjutning), `loading="lazy"` utom första vyns bild, alt-text på svenska
som beskriver innehållet (tom alt bara för dekor).

## Verktygen

- `node verktyg/bild/treatment.mjs --in raw --ref ref --out public/images [--preset NAMN] [--ink #hex --accent #hex]` —
  normalisering (vitbalans, exponering) en gång till `ref/`, sedan behandling och beskärning per plats till
  utkatalogen; rapport `BILDRAPPORT.json` med budgetvarningar. Paletten ges som flaggor eller läses ur kundens egna
  tokens; utan palett körs neutral behandling med varning, aldrig gissad färg.
- `node verktyg/bild/brand.mjs [--marke monogram|symbol] [--markfil fil.svg] [--namn "Företag"]` — ikoner, favicon,
  manifest och logotypfiler ur kundens logotyp (`raw/brand__*`); utan logotyp monogram; rapportrad per fil.
- `score.mjs` — mekanisk gallring av kandidater (entropi, kontrast i rubrikzon); ingen smak.

Verktygen är körbara instrument, inte krav: en kund med färdig bildbank och egen bildbehandling behöver dem inte.
