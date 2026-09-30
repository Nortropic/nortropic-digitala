# Mätning och uppföljning — händelser, konverteringskedja, kampanjmärkning, felsökning och återkoppling

Professionsfil (HELHET-20260927, avsnitt 4 "Mätning och uppföljning"). Laddas i steget `uppfoljning` och vid
leverans (bedömningsplanen). Verktyg: `verktyg/uppfoljning.py` (mätplan, kontroll mot bygget, UTM, läsning av
export). Verklig affärsnytta (offert, bokning, besvarat samtal, köp) hålls isär från proxyvärden (sidvisningar,
klick, tid på sidan).

## Mätplan (`MATPLAN.json`, briefen §11)

- Verktyg väljs efter behov och bedömning av faktisk datainsamling, lagring och åtkomst i
  terminalen. Kakfri analys är inte automatiskt undantagen från samtycke; osäkerhet blir
  **samtycke [OSÄKER]** i JURIDIK.json. Se verktygsbedömningen nedan.
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


## Verktygsbedömning för samtycke — omläst 2026-09-30

Grunden är [LEK 9 kap. 28 §](https://www.riksdagen.se/sv/dokument-och-lagar/dokument/svensk-forfattningssamling/lag-2022482-om-elektronisk-kommunikation_sfs-2022-482/):
information och samtycke krävs vid lagring/åtkomst i terminalen, med undantag för överföring
eller nödvändig tjänst som användaren uttryckligen begärt.
[EDPB Guidelines 2/2023, version 2.0, punkterna 4 och 56](https://www.edpb.europa.eu/system/files/documents/2024-10/edpb_guidelines_202302_technical_scope_art_53_eprivacydirective_v2_en_0.pdf)
beskriver teknisk räckvidd även utanför kakor; undantagen behöver bedömas för varje användning.
Leverantörens beskrivning är underlag, ingen generell svensk juridisk slutsats.

| Verktyg | Teknisk grund och bedömning | Läst |
|---|---|---|
| Vercel Analytics | [Request-baserad identifiering och sidvisningsdata](https://vercel.com/docs/analytics/privacy-policy). Utred vilka terminaluppgifter skriptet läser; [OSÄKER] tills den aktuella konfigurationen prövats mot LEK/EDPB. | 2026-09-30 |
| Plausible | [Daglig hash av bland annat IP och User-Agent](https://plausible.io/data-policy), inga kakor. Avsaknad av permanent identifierare avgör inte samtyckesfrågan; [OSÄKER] för användningen tills bedömd. | 2026-09-30 |
| Matomo utan kakor | [disableCookies och konfigurationsberoende insamling](https://matomo.org/faq/general/faq_157/). Pröva kvarvarande insamling och nationella undantag; [OSÄKER], inte automatiskt samtyckesfritt. | 2026-09-30 |
| GA4 med Consent Mode v2 | [Taggbeteendet ändras med samtyckesval](https://developers.google.com/tag-platform/security/concepts/consent-mode); nekat lagringssamtycke kan fortfarande ge mätanrop. Utred faktisk nättrafik, håll samtycke nekat som standard och blockera spårning som kräver samtycke. [OSÄKER] före bedömd konfiguration. | 2026-09-30 |
