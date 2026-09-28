# Så fungerar Digitala i praktiken — daterad översikt

Skriven 2026-09-27 av kedjedrivaren (sessionen nortropic-repos-f0) för ägaren, enligt tilläggen till HELHET-20260927
(avsnitt 5 respektive 9). Lästa revisioner: Digitala main 0c5e987 (PR 4 intervju mergad före publiceringsvägen fanns; PR 5 webbläsarvägen, PR 6
start/fortsätt-vägen, PR 7 efterarbete och PR 8 slutprovets fynd genom publiceringsvägen; PR 9 är Kundstart-uppdragets
verktyg, inte HELHET:s); kontoret main 8e6ecf8 (HELHET-RESULTAT-20260927); Runtime main 3d74733 med aktiv konfiguration eb102e4e (runtime
3bea86ef, övergång 18 aktiverad av ägaren 2026-09-27 10:44Z). Två vyer, tydligt skilda: **A** den ordinarie arbetsvägen (vad systemet ska göra, enligt dokumentation och
kod), **B** en faktiskt genomförd körning (vad systemet gjorde, med belägg). Tekniska referenser står intill i
kursiv eller i bilagan sist. Inga hemligheter, kunduppgifter eller råspår.

## Kort förklaring

Digitala är Nortropics förvaltning för digitala upplevelser (webbplatser och det som hör till dem: synlighet, mätning,
drift). Tre funktioner samverkar. **Kontoret** (repot nortropic-projektkontor) tar emot beställningen, bereder den med
problemformulering, metodstöd, mandat och proportion, och registrerar besluten. **Digitala** (repot nortropic-digitala)
bär yrkeskunnandet: stegen, professionsunderlagen, kundintervjun, researchen, briefen, bygget, kontrollerna, kanalerna
och rapporten. **Runtime** (repot Nortropic Runtime) är motorn som kör mätning, kritik, besökarprov och läsande
granskning som kvitterade körningar med pinnade verktyg. En modellsession (Claude Code eller Codex) är utföraren som
går vägen; verktygen i Digitala laddar rätt underlag per steg, binder körningar till kvitton och bokför läget så att en
annan utförare kan ta över. Ägaren ser färdig privat sida och rapport och tar ställning efteråt; inga rutinmässiga
ägarstopp däremellan.

## Kompakt stegkarta (vy A)

| # | Steg | Vad det åstadkommer | Indata | Ansvarig / utförarväg | Namngivna resurser (form) | Produceras och kontrolleras | Vidare vid underkänt |
|---|---|---|---|---|---|---|---|
| 0 | Beställning och beredning | rätt problem, proportion, metodval, kanalbehov, interventionsbeslut | ägarens ord, kundens befintliga underlag | kontoret (AP-06 med `forvaltning.problem`) med Digitalas `kunskap/beredning.md` laddat | beredning.md (metodunderlag; metodtabell: NN/g, McGovern, Rosenfeld m.fl.) | beställningspost med kanalbehov → `KANALBEHOV.json` i kundmappen | saknad substans = gap-koder i beredningen, inte stopp |
| 1 | Uppstart | läsa lärdomar, mandat, arbetssätt, kedja | repots filer | session; `fortsatt.py` laddar | LARDOMAR.md, MANDAT.md, ARBETSSATT.md, KEDJA.md (text) | laddningskvitto `LADDNING.json` | — |
| 2 | Intervju | kundens bild av mål, besökare, flöden, system, material, synlighet, förvaltning, ramar | kundmapp (VERKSAMHET.json, tidigare svar) | Digitala leder; session skickar omgångar i beställningens kanal | `intervju.py` (verktyg), kundintervju.md (metod) | frågeomgångar, svar ordagrant, fakta med status, motsägelser, sektion 19 till research.md | luckor ställs igen; uteblivna svar bokförs som beroende, arbetet fortsätter |
| 3 | Research | faktaunderlag i 19 sektioner, sökintention, kanalobservationer, referensjakt | intervjun, publika källor, kundens tillåtna data | session | research-underlag.md, referensjakt.md (metod); gallerier (referens) | `research.md` med kontrollrad och användbarhetsfrågor | OFULLSTÄNDIG-status, öppna frågor med ägare |
| 4 | Brief | motiverade val: uppgifter, struktur, handlingar, kanaler, röst, riktning, bild, teknik, juridik, bedömningsplan | research, beredning | session | brief-mall.md, juridikflaggor.md, bild.md, integrationer.md, frontend-design (utvalda delar), prototype (metod) | `PROJECT-BRIEF.md` §0–§13; kedjekontroll (redaktionellt-pass del 2) | konfliktrad; ingen ägarfråga för det som ryms i uppdraget |
| 5 | Koncept | lösningsalternativ utreds internt, en riktning väljs med skäl | brief | session | Taste (utvalda §), frontend-design, prototype-metod; referenser-professionella.md (faktisk jämförelse vid ny formgivning/omarbetning) | komps; kritik genom Runtimes kritikprofil | omprov av riktningen |
| 6 | Bygge | semantisk, tillgänglig, snabb, säker implementation i kundrepot med DESIGN.md | brief, riktning | session i kundrepot (Claude eller Codex); Vercel-förhandsvisning bakom skydd | bygge-referens.md, mobile-native, emil-design-eng (vid rörelse), formularsakerhet.md, bild.md + `bild/treatment.mjs`, `brand.mjs`, design.md-lint (paket), webbläsarvägen `inspektera.mjs` | kod, förhandsvisning, inspektioner under bygget | fynd → rättning → omprov |
| 7 | Redaktionellt pass | faktatrohet och redaktionell kvalitet | innehåll, brief §6 | session | redaktionellt-pass.md, copy-kontroll.md + `copy_kontroll.py` (rapport) | rättad text; rapport | fynd rättas eller motiveras |
| 8 | SEO | struktur, teknik, strukturerad data som sanning; lokal SEO bara om lokalt | brief §5, VERKSAMHET.json | session | seo.md, seo-lokal.md, `seo_kontroll.py` | rapport utan fynd i rätt läge | fynd rättas |
| 9 | Mätning | modellfri mätning: vyer, axe, Lighthouse, detektor | förhandsvisning | Runtime mätprofil via `kor_profil.py` | Runtime D034–D037 (pinnade axe, Lighthouse, Impeccable-detektor) | kvitto med hashar | mätvärden under kravnivå → åtgärd |
| 10 | Kritik | renderingsläsning, designkritik, femsekunderstest (modellbedömning) | skärmbilder, brief (bara till briefstyrd kritik) | Runtime kritikprofil (Claude eller Codex som läsare) | kritik/-mallarna; Hallmark (valfri lins); frontend-design | schemaprövat svar | fynd → rättning → omprov |
| 11 | Granskning D | kodläsning mot gränssnittsregler, tillgänglighet, mobil, formulär | kundrepot | Runtime läsarprofil | WIG, web-quality-audit, accessibility, mobile-native (utvalda delar) | fyndlista | rättning |
| 12 | QA | utforskande prov i riktig webbläsare: felvägar, tangentbord, meny, 404, bakåt; regressionsprov | förhandsvisning | `utforska.mjs` (motor) eller session genom Playwright MCP | Playwright 1.63.0, Playwright MCP 0.0.82 (verktyg) | `UTFORSKNING.md`, `REGRESSION.json` | rättning; regressionsproven körs om |
| 13 | Provare | avskärmad besökare löser en uppgift; kontrollant bedömer | förhandsvisning, uppgift utan brief/kod | Runtime provarprofil (Puppeteer) eller `besok.mjs` (Playwright MCP i egen session) | AGENTS-provare.md; webblasare.md | kvitto, spår, kontrollantens bedömning | fynd → rättning |
| 14 | Uppföljning, annonsberedning, lokal synlighet | mätplan, kampanjutkast (PAUSED), datablad för företagsprofil — när kanalbehovet säger det | brief §5, §11, VERKSAMHET.json | session | uppfoljning.md, annonser.md, lokal-synlighet.md + verktygen | planer, utkast, kontroller | externa åtkomster = namngivna beroenden |
| 15 | Prelaunch | åtta grindar som rapport; juridik avgörs av människa | mät- och provarkvitton, huvuden, audit | session | prelaunch.md + `prelaunch.py` | `PRELAUNCH.md` | FAIL → diagnos → åtgärd → omprov av grinden |
| 16 | Leverans | kvalitetsbild i tre kolumner, överlämning, lärdomspost, användningsnoter, förslagsrad, färdig privat sida | alla kvitton | session; kontorspost | KVALITET.md, `kvalitetsbild.py` | rapport till ägaren | — (ägaren tar ställning efteråt) |
| 17 | Lansering, sökkonsol, drift | bara med lanseringsmandat: kontroll på lanseringsdagen, sökkonsolens steg, driftkontroll | beställning som namnger lansering | session; `sokkonsol.py --live` med åtkomst | lansering.md, sokkonsol.md, drift.md + verktygen | kvitton | incident → diagnos → återgång enligt mandat |

Vägen bärs av `verktyg/fortsatt.py`: den binder beställningen (kundmappens `BESTALLNING.json`, ett hashat utdrag ur
beslutsposten med omfattning och eventuellt lanseringsmandat), avgör nästa steg, laddar underlaget, skriver `NASTA.md`,
bokför utfall och sidoeffekter i fallets `LAGE.json`, gör omprov vid underkänt och bokför saknade externa beroenden
(`vantar`) utan att stoppa resten; en färsk utförare kör `status` och `fortsatt`.
Integration i Digitala-repot begärs med primäringångens `verktyg/publicera.py --task ID`: en separat adopterad privat
hållare verifierar förseglad uppgift/kandidat, isolerade prov och granskning samt Appbundna checks före skyddad PR-väg.
Kandidatkopian får inte köras som publicerare. Mekaniskt verkställt: laddningens versionskontroll och kvitton, Runtimes profiler och kvitton,
kontextpolicyn som håller brief och facit borta från den avskärmade bedömaren, ursprungsgränsen i webbläsarvägen,
fiktiv-spärren i kanalverktygen, rulesetet på main. Sessionsburet: tolkningen av underlagen, valen i brief och koncept,
bygget, att utfallen rapporteras sant.

### En kort uppgift och ett större webbuppdrag — samma väg, olika proportion

En liten rättning på en levererad sajt (proportion liten): beredningen anger liten proportion utan metodskäl; intervju
och research körs inte om (`fortsatt.py klart --utfall inte-tillampligt` med skäl); bygge, redaktionellt pass, mätning,
QA och leverans körs på rättningen; kanalstegen är inte tillämpliga enligt kanalbehovet. Ett nytt webbuppdrag
(proportion mellan eller stor): hela vägen, intervjun som normalväg, kanalsteg efter kanalbehovet, prelaunch före
leverans, lansering bara med mandat. Ingen ny process: samma steg, samma verktyg, olika val bokförda i LAGE.json.

### Kanalförmågorna — integrationsläge, tillämplighet och beroenden (skilt från fallet)

| Förmåga | Byggt och prövat | Live-integration | Extern aktivering som återstår |
|---|---|---|---|
| SEO | seo.md, seo-lokal.md, `seo_kontroll.py` (prov mot lokala byggen) | inte tillämpligt (läser filer) | — |
| Search Console | sokkonsol.md, `sokkonsol.py`: anropsplan alltid; live-anrop byggda mot Googles API-dokumentation och prövade mot inspelade svar | inte körd: åtkomst saknas | Google Cloud-projekt med Site Verification API och Search Console API, OAuth-klient eller tjänstekonto; kundens egendom |
| Google-företagsprofil | lokal-synlighet.md, `lokal_synlighet.py` (datablad, NAP-kontroll) | ingen API-väg (profilen skapas av behörig människa) | kundens Google-konto; verifiering |
| Google Ads, Meta Ads | annonser.md, `annonsberedning.py` och `annonsadapter.py`: PAUSED-utkast, avgränsad `overfor`/`aterlas` samt resultatläsning ur export | överförings-/återläsningsväg implementerad och prövad med testtransport; ingen verklig överföring i det fiktiva fallet | behörig kontokonfiguration och uttryckligt mandat för PAUSED-överföring; Google Ads-utvecklartoken + OAuth + kund-id respektive Meta-token + annonskonto. Spenderingsmandat gäller aktivering, inte enbart tillåten PAUSED-beredning/överföring; verktyget har ingen aktiveringsväg. |
| Mätning och uppföljning | uppfoljning.md, `uppfoljning.py` (mätplan, kontroll mot bygge, UTM, läsning av export) | beror på kundens verktyg | samtycke; verktygets felsökningsläge |
| Drift | drift.md, `drift_kontroll.py` (kvitto, exit 1 vid incident) | manuell kontroll samt temporärt kvalificerad Runtime/Office-kedja | Runtime/Office har en avgränsad operationskandidat, provad med verkliga schemastarter och separat health-bindning; ännu inte aktiv kunddrift. Kontorets plan äger införande, release och befintlig operatörsövergång. En lokal värd kan sova eller vara offline. |

## Vy B — en faktiskt genomförd körning (slutprovet 2026-09-27, tydligt märkt testdata)

Fallet **Provfirma Trädgård (TESTFALL)**: fiktiv verksamhet, syntetisk intervju (testdialog), platshållarbilder märkta
TESTBILD, beställning märkt `testfall: true`, sajten serverad lokalt (127.0.0.1) och aldrig driftsatt. Allt nedan är
belagt i kontorets privata kundmapp `evidence/digitala/local/testfall-helhet-20260927/` (fall/LAGE.json: 38 körhändelser
plus en rättelsehändelse bokförd i efterhand, kvitton per steg). Inget av det är kundbevis eller kvalitetsreferens; det visar vad kedjan gör när den körs.

| # | Steg | Utförare · modell | Vad som gjordes (verktyg) | Kontroll som följde | Belagt genom |
|---|---|---|---|---|---|
| 1–2 | uppstart, beredning | session (claude) | `fortsatt.py` laddade stegen; BEREDNING.json (proportion mellan, kanalbehov) | — | LAGE.json, laddningskvitton |
| 3 | intervju | session · testdialog | `intervju.py start/svar/fakta/nasta/research`: 2 omgångar, 11 svar registrerade (5 svar i omgång 2 med fel fråge-id avvisades), 8 fakta (4 ur verksamhetsuppgifterna, 4 ur svaren), luckor kvar; fallets not från 15:08Z angav fel siffror och är rättad med en rättelsehändelse i LAGE.json | fynd: bokningsregeln missade "bokade … kalender" → rättad (PR 6) | INTERVJU.json, research-intervju.md, LAGE.json |
| 4–5 | research, brief | session | research.md (19 sektioner, kontrollrad OFULLSTÄNDIG), PROJECT-BRIEF.md §0–§14 | kedjekontroll (del 2) i §14 | kund/ |
| 6 | koncept | session + **Runtime kritikprofil (claude-sonnet-5)** | två kompar K1/K2 inspekterade (`inspektera.mjs`), kritiserade genom `kor_profil.py kritik` (designkritik-komp) | kritiken avgjorde riktningen "Text och foto sida vid sida" | KORNING kritik-koncept-k1/k2, KONCEPT.md |
| 7 | bygge | session | statisk sajt + `server.py` (CSP, servervalidering, honeypot, en klocka); DESIGN.md lintad (@google/design.md 0.4.0, 0 fel); `inspektera.mjs` 390/768/1440 | fynd under bygget: inline-stilar bröt CSP → rättat | sajt/, INSPEKTION-bygge-* |
| 8 | redaktionellt pass | session | `copy_kontroll.py` med briefens fraser och krav ur VERKSAMHET.json: 3 metalängder → 0 | REDAKTIONELLT-PASS-*.md | COPY-2.json |
| 9 | seo | session | `seo_kontroll.py` (förhandsvisning, LocalBusiness utan adress): 13 fynd → 0 | — | SEO-2.json |
| 10 | matning | **Runtime mätprofil** (modellfri) | `kor_profil.py matning` mot lokal adress ×3 (D037-parametrar): axe 0, Lighthouse 100/100/100/58 (seo: noindex), handling i vyn, detektor 3 fynd (platshållare, radavstånd) | radavstånd rättat, ommätt | KORNING matning-testfall-bygge(-2,-3) |
| 11 | kritik | **Runtime kritikprofil (claude-sonnet-5)** | renderingsläsning (godkänd, 4 förbättringar) och femsekunderstest (avskärmat, bara bilder) | "schaktmassor" borttagen, tack-sidan inspekterad | KORNING kritik-testfall-rendering/-femsek |
| 12 | granskning D | session | kodläsning mot WIG/web-quality-audit/accessibility/mobile-native/formularsakerhet: 4 fynd | till qa-steget | GRANSKNING-D.md |
| 13 | qa | **Codex (Runtimes pinnade codex-0.155.1, gpt-6-astra)** efter `fortsatt.py --utforare codex` | `utforska.mjs` (5 sidor, 3 fynd, REGRESSION.json); Codex rättade dedupering, tidsfälla, hjälptext, radavstånd (59 s); regressionen omkörd | fynd i sajten: kombinerade robotsignaler gav 400 → rättat; fynd i verktyget: fyllde honeypot som en robot → rättat (L25) | CODEX-qa-2.out, QA-*, QA-regression-* |
| 14 | provare | **claude-sonnet-5 genom verklig Playwright MCP** (`besok.mjs`, avskärmad) | 13 turer, 67 s, 9 förfrågningar alla inom ursprunget, POST /skicka, lead levererad till mottagaren med exakt testdata | kontrollanten bedömde ur artefakter: lyckat (KONTROLL-besok.md) | BESOK-20260927T160628Z, KONTROLL-besok.json |
| 15 | uppfoljning | session | MATPLAN.json (verktyg "ingen"), HANDELSEPLAN.md, MATKONTROLL.json (händelser avsiktligt inte i koden) | — | fall/ |
| — | annonsberedning, lokal-synlighet, lansering, sokkonsol, drift | verktyget | markerade *inte tillämpliga* av `fortsatt.py` (kanalbehov false; inget lanseringsmandat); omprövas om beställningen utvidgas | — | LAGE.json |
| 16 | prelaunch | session | `prelaunch.py` (rättad i slutprovet, L24): grind 0–5 och 7 PASS; 6 MANNISKA (ingen JURIDIK.json) → inte redo | avsiktligt: juridik avgörs av människa | PRELAUNCH.json |
| 17 | leverans | session | `kvalitetsbild.py` (7 Runtime-körningar, alla ok), användningsnoter, lärdomsposter L24–L27; leveransen = privat lokal förhandsvisning | vägen slutade: "alla tillämpliga steg klara: färdig privat leverans" | KVALITETSBILD.md, LAGE.json |

Integration under provet (samma dag): fyra kandidater publicerade genom `publicera.py` utan manuellt PR-godkännande
(PR 5–8; intervjun PR 4 mergades dessförinnan genom PR-vägen innan verktyget fanns), varje gång efter separat
läsargranskning (Runtime läsarprofil, claude-opus-5; nio rundor på de fyra — webbläsarvägen tre, fortsätt-vägen två, efterarbetet två, slutprovets fynd två — varav fem
underkända och rättade). Direkt push till main nekades av rulesetet (bevis i kontoret).

### Resurser i slutprovet — belagt, rapporterat, inte kört, inte tillämpligt (tillägg 1, avsnitt 5)

- **Verifierat använda med körspår**: `fortsatt.py`, `ladda_steg.py`, `intervju.py`, `kor_profil.py` (mät- och kritikprofilen
  ×7), `inspektera.mjs`, `utforska.mjs`, `besok.mjs` (verklig MCP), `copy_kontroll.py`, `seo_kontroll.py`, `uppfoljning.py`,
  `prelaunch.py`, `kvalitetsbild.py`, `publicera.py`, `pinna.py`, `verksamhetsuppgifter.py`; texterna brief-mall, research-
  underlag, kundintervju, bild, bygge-referens, formularsakerhet, copy-kontroll, seo/seo-lokal, redaktionellt-pass,
  webblasare, uppfoljning, prelaunch, KVALITET, MANDAT, LARDOMAR; externa: Taste §0/§4, frontend-design, emil-prototype
  (metod), mobile-native, WIG, web-quality-audit, accessibility, google-design.md (lint körd).
- **Närvarande men inte använda i provet**: `sokkonsol.py`, `lokal_synlighet.py`, `annonsberedning.py`, `lansering.py`,
  `drift_kontroll.py` (kanalbehov/mandat saknades — verktygen har egna prov), `bild/treatment.mjs` och `brand.mjs` (inga
  riktiga foton), Hallmark-linsen och emil-design-eng (inte motiverade av briefen), PICKER (ingen bläddringsyta),
  Runtimes provarprofil (Playwright-vägen kördes i stället; profilen prövad i Norrglänta samma dag).
- **Återstående kopplingar (externa aktiveringar, ägarpunkter)**: Google Cloud/OAuth för Search Console, Ads-
  utvecklartoken och Meta-token, företagsprofil genom behörig människa, schemalagd driftkontroll genom Runtime (eget
  mandat), verklig skyddad förhandsvisning (Vercel) för webbläsarvägen, juridisk genomgång av människa före lansering.

## Bilaga — tekniska referenser

- Stegen och underlagen: `steg/steg.json` (pinnade versioner i `steg/PINNAR.sha256`), laddning `verktyg/ladda_steg.py`.
- Vägen: `verktyg/fortsatt.py` (LAGE.json, NASTA.md); integration `verktyg/publicera.py`; Runtime-körningar
  `verktyg/kor_profil.py`; kvalitetsbild `verktyg/kvalitetsbild.py`.
- Resursernas ursprung, form och vad som inte följer med: `kunskap/REGISTER.md` (§A–§G) och resursspårningen
  (kontorets privata `RESURSSPAR-20260927.md`, sammanfattad i HELHET-ETAPP1-RESULTAT-20260927).
- Vad som verkställs mekaniskt respektive bärs av sessionen: `KEDJA.md`.
- Runtime: aktiv konfiguration `eb102e4e` (mät-, kritik-, provar- och läsarprofiler, D034–D037).
