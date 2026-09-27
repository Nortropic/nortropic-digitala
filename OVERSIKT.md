# Så fungerar Digitala i praktiken — daterad översikt

Skriven 2026-09-27 av kedjedrivaren (sessionen nortropic-repos-f0) för ägaren, enligt tilläggen till HELHET-20260927
(avsnitt 5 respektive 9). Lästa revisioner: Digitala main df6cf8c (intervjukandidaten mergad som PR 4) med kandidaterna webbläsarvägen (gren
helhet/webblasare, i PR-vägen) och start/fortsätt-vägen (denna gren); kontoret main 30ebc08; Runtime main 3d74733 med
aktiv konfiguration eb102e4e (runtime 3bea86ef, övergång 18 aktiverad av ägaren 2026-09-27 10:44Z). Två vyer, tydligt skilda: **A** den ordinarie arbetsvägen (vad systemet ska göra, enligt dokumentation och
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
| 5 | Koncept | lösningsalternativ utreds internt, en riktning väljs med skäl | brief | session | Taste (utvalda §), frontend-design, prototype-metod; referenser-professionella.md (valfri jämförelse) | komps; kritik genom Runtimes kritikprofil | omprov av riktningen |
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
Integration i Digitala-repot sker genom `verktyg/publicera.py` (PR-vägen, bara med godkänd separat granskning bunden
till exakt commit). Mekaniskt verkställt: laddningens versionskontroll och kvitton, Runtimes profiler och kvitton,
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
| Google Ads, Meta Ads | annonser.md, `annonsberedning.py` (PAUSED-utkast i plattformarnas objektform, resultatläsning ur export) | inte körd: ingen överföringsväg | Google Ads-utvecklartoken + OAuth + kund-id; Meta-app med ads_management + annonskonto; mandat att spendera |
| Mätning och uppföljning | uppfoljning.md, `uppfoljning.py` (mätplan, kontroll mot bygge, UTM, läsning av export) | beror på kundens verktyg | samtycke; verktygets felsökningsläge |
| Drift | drift.md, `drift_kontroll.py` (kvitto, exit 1 vid incident) | körs av hand | schemalagd körning genom Runtime (etapp 5, namngivet steg) |

## Vy B — en faktiskt genomförd körning

Skrivs i etapp 6 ur slutprovet med tydligt märkta testunderlag (inget kundfall finns beställt än): vilka resurser som
verkligen användes, i vilka steg, av vilken utförare och modell, med vilka underlag, vilken kontroll som följde, och
per resurs om det är belagt (körspår, kvitto), rapporterat, inte kört eller inte tillämpligt. Tills dess gäller
etapp 4-körningen på Norrglänta (DIGITALA-1-ETAPP4-RESULTAT-20260927) som det senaste verkliga arbetsfallet, med sina
användningsnoter — Norrglänta är underkänt som kvalitetsresultat och används här bara som belägg för vad som kördes.

## Bilaga — tekniska referenser

- Stegen och underlagen: `steg/steg.json` (pinnade versioner i `steg/PINNAR.sha256`), laddning `verktyg/ladda_steg.py`.
- Vägen: `verktyg/fortsatt.py` (LAGE.json, NASTA.md); integration `verktyg/publicera.py`; Runtime-körningar
  `verktyg/kor_profil.py`; kvalitetsbild `verktyg/kvalitetsbild.py`.
- Resursernas ursprung, form och vad som inte följer med: `kunskap/REGISTER.md` (§A–§G) och resursspårningen
  (kontorets privata `RESURSSPAR-20260927.md`, sammanfattad i HELHET-ETAPP1-RESULTAT-20260927).
- Vad som verkställs mekaniskt respektive bärs av sessionen: `KEDJA.md`.
- Runtime: aktiv konfiguration `eb102e4e` (mät-, kritik-, provar- och läsarprofiler, D034–D037).
