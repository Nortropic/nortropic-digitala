# Mätning och uppföljning — händelser, konverteringskedja, kampanjmärkning, felsökning och återkoppling

Professionsfil (HELHET-20260927, avsnitt 4 "Mätning och uppföljning"). Laddas i steget `uppfoljning` och vid
leverans (bedömningsplanen). Verktyg: `verktyg/uppfoljning.py` (mätplan, kontroll mot bygget, UTM, läsning av
export). Verklig affärsnytta (offert, bokning, besvarat samtal, köp) hålls isär från proxyvärden (sidvisningar,
klick, tid på sidan).

## Mätplan (`MATPLAN.json`, briefen §11)

- Verktyg: kakfri analys (t.ex. Vercel Analytics, Plausible, Matomo utan kakor) utan samtyckesruta, eller GA4 med
  Consent Mode v2 (nekat som standard) bara när briefen motiverar det. Serverbaserad spårning ändrar inte kravet.
- Händelser: namn i snake_case, utlösare, var, om händelsen är en konvertering, parametrar. Minst en konvertering.
- Kedjan från besök till affärsutfall (besök → sida → handling → leverans → svar), så att brott i kedjan kan hittas.
- Affärsmått som kunden känner igen (offertförfrågningar per vecka, bokningar); proxyvärden som stöd.

## Kampanjmärkning

`utm_source`, `utm_medium`, `utm_campaign` (och `utm_content`) på varje kampanjlänk, små bokstäver, konsekventa
värden; Google-företagsprofilens länk märks `google/organic/gbp` om verktyget läser UTM. Aldrig UTM på interna länkar.

## Felsökning av mätningen

En händelse i koden är inte en mätt händelse. Före lansering: händelsen syns i verktygets felsökningsläge och i
webbläsarens nätverkslogg (webbläsarverktyget, etapp 4) när handlingen utförs; formulärets leverans bekräftas i
mottagarens inkorg (leveransen är provet). Efter lansering: dag 1 kontroll av att konverteringar registreras;
avvikelser mellan plattform och verkligt inflöde utreds, inte förklaras bort.

## Återkoppling till innehåll och upplevelse

Månadsrutin: sökkonsolens frågor och sidor (sokkonsol.md), kampanjdata (annonser.md), händelsedata och kundens
verkliga inflöde läses tillsammans; varje avvikelse blir en hypotes med åtgärd i innehåll, struktur eller upplevelse,
provad och följd upp. Rapporter för sin egen skull skrivs inte.

## Samtycke, integritet och plattformskrav

Inget spårande skript före samtycke när samtycke krävs; nekat som standard; neka lika lätt som acceptera;
integritetspolicyn beskriver verktyget och mottagarna; inga personuppgifter i händelseparametrar; plattformarnas
egna villkor (Googles och Metas policyer för konverteringsdata) följs. Juridiken avgörs av människa
(juridikflaggor.md).
