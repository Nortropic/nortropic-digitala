# Beredning — problemformulering, proportion och metodval före bygget

Professionsfil (HELHET-20260927, avsnitt 3). Laddas i steget `beredning` av kontorets beredning (AP-06, delen
`forvaltning.problem`) och av Digitalas egen uppstart av ett fall. Underlaget är råd; ägarens accepterade uppdrag och
mandatet vinner. Ett ifyllt schema är inte leverans: värdet ligger i att rätt problem är formulerat och att metoden
följer av problemet.

## 1. Vad beredningen ska ge

Elva svar, som kontorets beredning bär vidare i briefen (fältnamnen är kontorets):

| Fält | Fråga | Krav på svaret |
|---|---|---|
| `verksamhetsmal` | Vad vill verksamheten att den digitala upplevelsen ska ändra? | Mätbart eller åtminstone falsifierbart ("fler offertförfrågningar från X"), inte "en modern sajt". |
| `malgrupper` | Vilka kommer, och vilka av dem är viktigast för målet? | Namngivna segment med belägg (research §3); antaganden märkta. |
| `uppgifter` | Vilka två till fem uppgifter måste besökaren kunna lösa? | Toppuppgifter i besökarens ord, rangordnade; motstridiga signaler skrivs ut. |
| `erbjudande` | Vad erbjuds, i verksamhetens egna ord? | Ur research §2; inga omskrivningar som lovar mer. |
| `positionering` | Varför denna verksamhet i stället för de faktiska alternativen? | Mot 2–3 verkliga alternativ (konkurrent, annan lösning, att inte göra något). |
| `befintligt_underlag` | Vad finns redan: sajt, Google-profil, sociala kanaler, texter, bilder, data, omdömen, system? | Inventerat med rättighetsläge; "finns inte" är ett giltigt svar. |
| `osakerheter` | Vad vet vi inte, och vem kan svara? | Varje osäkerhet med källa som kan avgöra (kund som sakexpert, användare, mätning). |
| `kanalbehov` | Vilka kanaler motiverar uppgiften: sök, lokal synlighet, annonser, e-post, sociala, ingen? | Per kanal: varför den behövs eller varför inte; alla kunder ska inte få alla kanaler. |
| `framgangskriterier` | Hur vet vi efteråt om det lyckades? | Affärsutfall (leads, bokningar) skilt från användarutfall (uppgiften löst); ordagrant nog för att kunna visa sig fel. |
| `anvandarinsikt` | Var kommer bilden av användarna ifrån? | `intervjuer`, `observationer`, `data`, `antaganden` eller `saknas`. Saknas intervjuer sägs det rakt ut; påhittade insikter är förbjudna. |
| `interventionsbeslut` | Är en (ny) sajt rätt åtgärd? | `ny-sajt`, `forbattra-befintlig`, `annan-kanal`, `ingen-atgard` eller `oavgjort`, med skäl ur underlaget. |

Kedjan som briefen ska visa, länk för länk: **problem → underlag → metod → beslut → producerad upplevelse →
bedömning**. Saknas en länk står det "saknas" där, inte en ifylld fras.

## 2. Interventionsbeslutet

Läs det befintliga först (skrivskyddat: befintlig sajt, Google-profil, sociala kanaler, omdömen, svarstider som går
att observera). Fyra utfall utöver oavgjort:

- **ny-sajt** — det befintliga finns inte eller går inte att bygga vidare på.
- **forbattra-befintlig** — grunden fungerar; problemet är innehåll, struktur eller en bruten handling. En ny sajt
  kastar då bort upparbetat sökvärde och länkar.
- **annan-kanal** — problemet ligger utanför sajten: verksamhetsuppgifterna i Google, svarstider, prissättning,
  att telefonen inte besvaras, en kanal som inte används.
- **ingen-atgard** — det kunden beskriver löses inte av digitalt arbete just nu, eller vi är fel leverantör.

Kundens önskemål är inte detsamma som användarens behov, och affärsutfall är inte detsamma som användarutfall;
båda skrivs ut. Ett annat utfall än `ny-sajt` är briefens viktigaste rad och redovisas för ägaren i leveransen; inom
ett accepterat uppdrag stoppar det inte arbetet med det som ändå ska göras.

## 3. Proportion

`liten` (en avgränsad ändring, en sida, en rättning): verksamhetsmål, uppgifter och framgångskriterier räcker;
metodskäl behövs inte. `mellan` (en sajt eller en etapp med flera sidor): alla elva svar och metodskäl. `stor`
(flera kanaler, migrering, innehållsmodell, integrationer): som mellan, plus en bedömningsplan per kanal.

## 4. Metodval efter problem — inget obligatoriskt ramverk

Välj den eller de metoder som problemet motiverar; skriv skälet. Tabellen är ett urval av etablerade metoder med
sina källor, inte en trappa som alla kunder går.

| Problem/osäkerhet | Metod | Källa (etablerad) | Kräver |
|---|---|---|---|
| Vilka uppgifter som betyder mest | Toppuppgiftsanalys (kort lista, rangordning) | McGovern, *Top Tasks* (2018); NN/g om task analysis | Användare eller åtminstone kundens observationer; annars antaganden märkta |
| Varför kunden anlitar (motiv, situation) | Jobs to be done-intervjuer | Christensen m.fl., *Competing Against Luck* (2016) | Intervjuer; utan dem: antaganden |
| Hur besökaren rör sig från behov till handling | Användarresa (start, hinder, slut) | NN/g, *Journey Mapping 101* | Research §4 och §9 |
| Vad som ska finnas och hur det hänger ihop | Innehållsinventering och innehållsstruktur; informationsarkitektur | Rosenfeld, Morville & Arango, *Information Architecture* (4:e uppl.); Halvorson & Rach, *Content Strategy for the Web* | Befintligt innehåll, uppgifterna |
| Om strukturen begrips | Kortsortering/trädtest (bara om användare finns), annars heuristisk läsning | NN/g om card sorting och tree testing | Deltagare; utan dem märks resultatet `antaganden` |
| Om gränssnittet är begripligt och användbart | Heuristisk utvärdering; användningstest (mänskligt) | Nielsen, *10 Usability Heuristics*; Krug, *Don't Make Me Think* | Ett prov att bedöma; mänskligt test kräver deltagare |
| Vad besökaren förstår på fem sekunder | Femsekunderstest | UsabilityHub/NN/g-form | Mänskliga deltagare; Runtimes modellbaserade variant är en modellbedömning, inte ett uppmätt mänskligt test |
| Vad besökarna söker efter | Sökintentionsläsning (sökordsformer, resultatsidans form, frågor) | Google Search Central, *SEO Starter Guide*; Moz/Ahrefs intentklasser som läsram | Sökningar utförda och dokumenterade; inga rankningslöften |
| Om sajten är tillgänglig | WCAG 2.2 AA som krav; axe som verktyg (täcker en del), manuella kontroller | W3C WCAG 2.2; WAI-ARIA APG | Renderat resultat |
| Om sajten är snabb | Core Web Vitals (LCP, INP, CLS) | web.dev/vitals | Mätning genom Runtimes mätprofil; INP mäts inte av navigations-Lighthouse |
| Vad som händer efter lansering | Mätplan (händelser, konverteringskedja) och läsning av sök- och kampanjdata | GA4/Consent Mode-dokumentation; Search Console-hjälpen | Samtycke och plattformskrav uppfyllda |

Regler: (1) välj efter problemet, aldrig efter vana; (2) en metod utan deltagare eller data ger antaganden, som
skrivs som antaganden; (3) primärdokumentation (leverantörens aktuella dokumentation) går före andrahandskällor;
(4) skriv i briefen vilken metod som användes för vilket svar, så att bedömningen kan gå tillbaka till källan.

## 5. Vad beredningen aldrig gör

Den väljer inte design, skriver inte copy, lovar inte rankning eller resultat, hittar inte på användare, och
öppnar inga konton eller kanaler. Den begär inte ägarens ställningstagande till sådant som ryms i uppdraget;
verkliga vägval om mandat, kostnad eller rättighet går till ägaren som namngivna frågor med rekommendation.
