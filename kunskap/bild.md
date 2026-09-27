# Bild — val, licens, autenticitet, art direction, beskärning, storlekar och optimering

Professionsfil (HELHET-20260927, avsnitt 5). Laddas i steget `brief` (§8) och `bygge`. Verktygen i `verktyg/bild/`
(`treatment.mjs`, `brand.mjs`) är återvunna ur det arkiverade repot (revision `e4c8c52`, 2026-09-10) som körbara
verktyg, oförändrade i kod; fyra kommentarsrader om det gamla sammanhanget (nodnummer, slot-schema.md, launch.js) är ersatta; körbevis 2026-09-27 med `sharp` 0.34.4 (Apache-2.0, libvips 8.17.2). Inte återinförda: anskaffning
genom bildgenereringstjänst (`fetch-images.mjs`, fal.ai: kräver konto och kostnad, ägarbeslut per kund) och den
mekaniska gallringen `score.mjs` (fasta trösklar som gav en poäng och ett "godkänd"; hade ingen användning utan
genereringen och strider mot regeln om automatisk stilpoäng).

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
bilder av olika ursprung; ett kundmaterial som redan håller ihop behandlas inte. Verktygets egen standard när ingen
preset ges är `dokumentar` (kodens "osäkerhetsval"), och verktyget bär en tabell som föreslår look per bransch
(`PRESETS`): båda är det gamla flödets val, inte Digitalas — briefen §8 anger preset uttryckligen, eller ingen
behandling alls.

## Beskärning, storlekar och optimering

Platsplan i briefen §8: bildplats (`hero-*`, `env-*`, `proof-*`, `people-*`, `detail-*`), sida, källa, anspråk,
status. Filnamn `<plats>__<beskrivning>.<ext>`. Beskärningar per plats (första vyn 16:9 och 4:5 för mobil, 3:2 för
miljö, kvadrat för porträtt) och responsiva storlekar med `sizes`; AVIF/WebP med kvalitetsloop mot en viktbudget
(förslag: första vyns bild ≤ 150 kB, porträtt ≤ 100 kB, övriga ≤ 120 kB; budgeten sätts i briefen §9, inte här).
Explicita mått på varje bild (ingen layoutförskjutning), `loading="lazy"` utom första vyns bild, alt-text på svenska
som beskriver innehållet (tom alt bara för dekor).

## Verktygen (som de är; flaggor skrivs `--flagga=värde`)

- `node verktyg/bild/treatment.mjs --in=raw --ref=ref --out=public/images [--stage=both|normalise|look]
  [--preset=duotone|dokumentar|ljus] [--ink=#hex --accent=#hex] [--compare]` — normalisering (vitbalans, exponering)
  en gång från `--in` till `--ref` (hoppas när ref är nyare än råfilen), sedan look och beskärning per bildplats till
  `--out` (AVIF och WebP, kvalitetsloop mot budget); `BILDRAPPORT.json` i arbetskatalogen bär budgetvarningar. Filnamn
  i `--in` ska bära bildplats-id (`hero-01__namn.jpg`); okänt prefix vägras. Palettens läsordning: flaggorna, annars
  `--nortropic-ink`/`--nortropic-accent` i `src/app/globals.css` eller `app/globals.css`, annars `tokens` i
  `SLOTS.json`; utan palett körs overlay i svart och duotone som gråskala med varning — aldrig gissad färg.
  Standardkatalogerna (`public/images/raw`, `public/images/ref`, `public/images`) och tokennamnen är det gamla
  flödets konventioner; kundrepot väljer sina egna genom flaggorna eller genom att sätta tokens med de namnen.
- `node verktyg/bild/brand.mjs [--marke=monogram|symbol] [--markfil=fil.svg] [--namn="Företag AB"] [--initialer=AB]
  [--display=typsnitt]` (körs i kundrepots rot) — läser kundens logotyp ur `public/images/raw/brand__*` (utan logotyp:
  monogram), skriver ikoner, favicon, webbmanifest och logotypfiler på Next.js-konventionens platser (`app/icon.svg`,
  `app/favicon.ico`, `app/apple-icon.png`, `app/manifest.webmanifest`, `public/icon-192.png`, `public/icon-512.png`,
  `public/brand/logo*.svg`; `src/app/` när den finns) och läser paletten bara ur `globals.css`-tokens eller `SLOTS.json`
  (inga palettflaggor); utan tokens akromatisk degradering med varning. Bindningen till Next.js-platserna är en
  begränsning: för en annan stack används verktyget inte, eller utfilerna flyttas för hand.
- Beroende: `sharp` i kundrepot, pinnad version i kundrepots `package.json` (körbeviset: 0.34.4); valfria
  `rembg`/`vtracer` för rastervektorisering i `brand.mjs` (utan dem behålls rastern med rapportrad).

Verktygen är körbara instrument, inte krav: en kund med färdig bildbank och egen bildbehandling behöver dem inte.
