# SEO — sökintention, struktur, teknik och innehåll; inga rankningslöften

Professionsfil (HELHET-20260927, avsnitt 4 "SEO"), återvunnen och generaliserad ur det arkiverade repots lokala
SEO-skill. Laddas i steget `seo`. Metadata eller Lighthouse-SEO ensamt är ingen SEO-funktion; SEO-läget väljs i
briefen §5: `lokal`, `varumärke/portfölj`, `hybrid` eller `ingen`. Verktyg: `verktyg/seo_kontroll.py` (rapport).

## Sökintention och informationsstruktur

- Varje sida svarar på en sökavsikt ur research §15 (informations-, navigations-, transaktions- eller lokal
  avsikt); sidor utan genuint innehåll skapas inte ("fem verkliga sidor slår tjugofem spunna").
- Sidstruktur efter uppgifterna: tjänst per sida när tjänsterna söks var för sig; område per sida bara vid lokal
  räckvidd och genuint lokalt innehåll (verkliga arbeten, lokala förhållanden); frågor som kunder faktiskt ställer i
  ett FAQ-block på den sida de hör till.
- Intern länkning: start → tjänster; tjänst ↔ närliggande tjänst; område → tjänster; sidfot → områden och
  informationssidor; brödsmulor när djupet motiverar det.

## Teknisk SEO

- Crawlning och indexering: `robots.txt` med `Sitemap:`-rad; `sitemap.xml` ur sidorna; förhandsvisning bär
  `noindex` och `Disallow: /`, lanseringskonfigurationen tvärtom — de två hålls isär (lansering.md).
- Canonical absolut per sida; en kanonisk domänvariant (www eller apex), den andra omdirigerar 301.
- Metadata: unik `title` (omkring 60 tecken) och `description` (omkring 155) per sida, sanningsenliga, utan
  superlativ och utan ortstoppning; sociala metadata (Open Graph) med bild.
- `html lang`, en `h1` per sida, rubrikordning, alt-texter (bild.md), svenska filnamn på bilder.
- hreflang bara vid verkliga språkvarianter, bidirektionellt med `x-default`; ingen hreflang på enspråkig sajt.
- Omdirigeringar vid migrering: gamla adresser med trafik eller inkommande länkar får 301 till närmaste motsvarighet;
  listan prövas i förhandsvisning (`--omdirigeringar`).
- Prestanda och tillgänglighet är egna krav (bygge-referens.md); de mäts genom Runtimes mätprofil, inte här.

## Strukturerad data — bara sanning

- JSON-LD, ett skriptblock per objekt, serverrenderat. Typ efter verksamheten (`LocalBusiness`-undertyp bara vid
  lokal verksamhet; annars `Organization`, `Service`, `FAQPage`, `BreadcrumbList` efter innehåll).
- Fälten kommer ur `VERKSAMHET.json`: namn, telefon i E.164, adress bara när `adress.publik` är sann (annars
  `areaServed`), öppettider som på sajten, `priceRange` bara om pris anges; `aggregateRating` bara ur verklig
  plattformsdata med källa; `offers` bara vid verkligt fast pris.
- FAQ-frågor i schemat är samma som de synliga; inga platshållare får nå schemat.
- Validering: `seo_kontroll.py` prövar form och sanning mot verksamhetsuppgifterna; Googles Rich Results Test är en
  manuell kontroll efter lansering (extern).

## Innehållsmässig SEO

- Text som svarar på avsikten med kundens ord och verkliga uppgifter; ortnamn där de är sanna, aldrig som stoppning;
  interna länkar med beskrivande text; bilder med innehåll (bild.md); ingen text för sökmotorer som inte är för läsare.

## Vad SEO inte lovar

Ingen rankning, ingen indexering och inga positioner utlovas. Observationer efter lansering läses i sökkonsolen
(sokkonsol.md) och omsätts i innehålls- och strukturändringar (uppfoljning.md).
