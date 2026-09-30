# Digitalas arbetssätt — steg, proportion och verktyg

Stegen är ett förråd, inte en pipeline. Uppgiften avgör vilka steg som körs och hur tungt. En liten uppgift ska inte
tvingas igenom en stor uppgifts process; en stor uppgift får inte hoppa över det som gör resultatet bra.

## Stegen (definierade i `steg/steg.json`)

| Steg | Mandat | Vad | Runtime | Var arbetet sker |
|---|---|---|---|---|
| uppstart | stående | lärdomar, mandat, arbetssätt | — | läsning |
| beredning | stående | problemformulering, proportion, metodval efter problem, interventionsbeslut (kontorets beredning laddar steget) | — | kontorets beredning och kundmappen |
| intervju | beställning | adaptiv kundintervju i beställningens kanal: omgångar, följdfrågor ur svaren, svar ordagrant, fakta med status, motsägelser, avsnitt 19 | — (intervju.py) | kundmappen (INTERVJU.json, INTERVJU/) |
| research | stående | faktaunderlag i 19 sektioner (referensjakten en del), sökintention, kanalobservationer, verksamhetsuppgifter | — | kundmappen (research.md, VERKSAMHET.json) |
| brief | beställning | samlad brief, riktning, kedjekontroll på briefen | läsare för granskning | kundmappen (PROJECT-BRIEF.md); inget ägarstopp |
| koncept | beställning | lösningsalternativ utreds internt, en motiverad riktning väljs utan ägarstopp (antal alternativ efter uppgiften; Design Read och namngivna axlar är metoder, inte universella värden) | kritikprofilen (designkritik-komp) | privat etappmapp |
| bygge | beställning | bygget i kundrepot | — (dagens byggväg) | kundrepot |
| redaktionellt-pass | beställning | faktatrohet och redaktionell kvalitet; copykontrollens rapport | läsare | kundrepot (content) |
| seo | beställning | sökintention, struktur, teknisk och innehållsmässig SEO, strukturerad data; lokal SEO bara vid lokal/hybrid | — (seo_kontroll.py) | kundrepot; rapport i fallet |
| matning | stående | modellfri mätning: vyer, rubrikrader, handling, axe, Lighthouse, detektor | mätprofilen | körkatalog i Runtime, pekare i fallet |
| kritik | stående | renderingsläsning, designkritik, femsekunderstest | kritikprofilen | körkatalog i Runtime |
| granskning-d | stående | kodläsning mot gränssnittsregler, tillgänglighet, mobil, formulär | läsare | privat arbetsyta |
| qa | stående | utforskande QA i riktig webbläsare: fynd med reproduktion, regressionsprov; browsergranskning under bygget | — (utforska.mjs, inspektera.mjs) | fallet (QA-, INSPEKTION-kataloger; spår privata vid undantag) |
| provare | stående | scenario i riktig webbläsare, kontrollant avgör | provarprofilen | körkatalog i Runtime + KONTROLL.md i fallet |
| uppfoljning | beställning | mätplan, händelser, konverteringskedja, kampanjmärkning, kontroll mot bygget, läsning | — (uppfoljning.py) | kundmappen (MATPLAN.json) |
| annonsberedning | beställning | kampanjutkast för Google Ads och Meta Ads, PAUSED; resultatläsning | — (annonsberedning.py) | kundmappen (KANALPLAN.json, ANNONSER/) |
| lokal-synlighet | beställning | datablad för företagsprofil och citationer; NAP-kontroll | — (lokal_synlighet.py) | kundmappen; profilen hos behörig människa |
| prelaunch | stående | åtta grindar som rapport (juridik avgörs av människa) | mät- och provarkvitton in | fallet (PRELAUNCH.json/.md) |
| leverans | beställning | kvalitetsbild, överlämning, lärdomspost, användningsnoter, förslagsrad | — | kontorspost + privat fall |
| lansering | beställning (namnger lansering och domän) | plan, lanseringsdagens kontroll, sökkonsolens steg, återgång | — (lansering.py, sokkonsol.py) | produktionsdomänen; kvitto i fallet |
| sokkonsol | beställning | anropsplan, ägarskap, egenskap, sitemap, inspektion, sökdata, tolkning | — (sokkonsol.py) | kundmappen (kvitton); egenskapen hos Google |
| drift | stående | driftkontroll med kvitto, incident, beroendeunderhåll, förbättring | schemaläggning genom Runtime återstår (etapp 5) | fallet (DRIFT/) |

Steg som kräver en beställnings beslutspost (`mandat: bestallning` i `steg/steg.json`): **intervju, brief, koncept, bygge,
redaktionellt-pass, seo, uppfoljning, annonsberedning, lokal-synlighet, leverans, lansering, sokkonsol**. Steg inom stående
mandat: uppstart, beredning, research, matning, kritik, granskning-d, qa, provare, prelaunch, drift. Kanalstegen (seo,
sokkonsol, lokal-synlighet, annonsberedning, uppfoljning) används när kundens uppdrag motiverar dem (beredningens
kanalbehov); alla kunder får inte alla kanaler.

## Proportion — tre storlekar

| Storlek | Exempel | Steg som körs | Vad som INTE körs |
|---|---|---|---|
| **Liten** (ändring inom befintligt innehåll och komposition) | rätta en trasig länk, ett stavfel, en kontrast | uppstart (kort) → [beställning] → bygge (avgränsat) → matning (berörd sida) → granskning-d (kort, berörd kod) → leverans (kort) | brief, koncept, kritik, provare |
| **Mellan** (ny sida eller ny sektion inom gällande riktning) | ny landningssida | uppstart → [beställning] → brief-avsnitt → bygge → redaktionellt-pass → matning → kritik (renderingsläsning) → granskning-d → provare (ett scenario) → leverans | koncept, om riktningen är beslutad |
| **Stor** (ny riktning, ny informationsarkitektur, ny kund) | omformning, ny kund | alla steg, med koncept före bygge och kontorets beredning (behov, osäkerheter, metodval, beslutsunderlag) | — |

Också en liten uppgift på en levererad sajt kräver en beställnings beslutspost, med ett undantag: de faktarättelser
kunden själv lämnar inom underhållsformen (öppettider, telefonnummer, pris) ryms i stående
mandat för en riktig kund med en lanserad sajt (`MANDAT.md` §1, `kunskap/drift.md`, DIGITALA-UNDERHALL-20260929). Ett
stavfel eller en trasig länk som kunden inte själv lämnat som faktarättelse är alltså fortfarande en beställning, och
fiktiva testbyggen förvaltas inte efter leveransen.

Kontoret bidrar vid mellan och stor uppgift med problemformulering, osäkerheter, proportionerligt metodval och
beslutsunderlag genom sin beredning (AP-06, fältet `forvaltning`); Digitalas sakkunskap får påverka både
problemformuleringen och metodvalet. Vid liten uppgift behövs inget av det.

## Ordinarie start- och fortsättningsväg

En beställning bär hela uppdraget till färdig privat leverans. Beställningen binds i kundmappens `BESTALLNING.json`
(utdrag ur beslutsposten: `post`, `kalla`, `kund` = VERKSAMHET.json:s namn, `omfattning` = `privat-leverans`, `helhet`
eller en steglista, `lanseringsmandat` = post-id eller null, `utdrag` ordagrant, `testfall: true` bara för fiktiv
verksamhet); vägen bokför filens sha256 och en ombindning när den ändras. `python3 -B verktyg/fortsatt.py --kund KUNDMAPP
--fall FALL [--bestallning POST-ID] --utforare claude|codex` avgör nästa steg i stegens ordning (beställningssteg bara
inom omfattningen; kanalstegen efter kundmappens `KANALBEHOV.json` ur beredningen; lansering, sokkonsol och drift bara
med lanseringsmandat, annars slutar vägen vid leverans; verktygets egna markeringar omprövas varje körning, så ett
lanseringsmandat eller ett kanalbehov som kommer senare återöppnar stegen automatiskt — en utvidgad beställning anger då
`omfattning` `helhet` eller en steglista som tar med lansering, sokkonsol och drift, inte bara lanseringsmandatet),
laddar stegets underlag i fallet (ett redan laddat steg återupptas utan ny laddning),
skriver `NASTA.md` (beställning, syfte, anvisning, arbetsyta, redan utförda
sidoeffekter, väntande beroenden, hur utfallet rapporteras) och bokför allt i fallets `LAGE.json` (0600) med händelselogg
per utförare. `klart --steg S --utfall klar|underkand|inte-tillampligt|vantar --not … [--bevis FIL] [--kvitto FIL] [--sidoeffekt …]
[--beroende …] [--lost-beroende …]` tar emot utfallet för det laddade steget; underkänt ger omprov av samma steg (diagnos → åtgärd → omprov)
utan ägarfråga; `vantar --beroende "vad"` bokför ett saknat externt beroende så att oberoende arbete kan fortsätta, och `omprova
--steg S --not …` öppnar steget igen när beroendet finns. En färsk utförare kör `status` och `fortsatt` och tar över
utan att ägaren återberättar. Klar/N/A kräver kandidat-, miljö- och konfigurationsbundet råbevis enligt
[kunskap/bevis-och-fortsattning.md](kunskap/bevis-och-fortsattning.md). Ändrade bevis eller nödvändiga förutsättningar
återöppnar aktuellt godkännande; väntan är aldrig färdig leverans. Utförarbyte till Codex utanför Runtime görs med Runtimes pinnade binär (`Nortropic
Runtime/.runtime/bin/codex-<version>`, samma modell som Runtimes konfiguration anger), inte med den CLI som råkar ligga i
PATH: i slutprovet vägrade ägarens äldre CLI modellen medan den pinnade körde (L27).

## Så används verktygen i varje steg

1. `python3 -B verktyg/ladda_steg.py --steg STEG --ut ARBETSYTA [--kund KUNDMAPP] [--bestallning POST-ID]` — laddar
   stegets obligatoriska och valfria underlag med versionskontroll och skriver `UNDERLAG.md`, `LADDNING.json` (kvitto)
   och `ANVANDNINGSNOTER.md` (skelett). Läs `UNDERLAG.md` först; den är den fullständiga listan.
2. `python3 -B verktyg/kor_profil.py matning|kritik|provare --laddning ARBETSYTA/LADDNING.json …` — kör Runtimes profil
   som den aktiva releasens egen kopia, med Digitalas val ur den laddade arbetsytans `matning/PROFIL.json` och
   `kritik/`-mallar (de laddade versionerna, verifierade mot kvittot), och
   skriver `KORNING-<tid>.json` i fallet med körkatalog, utfall och laddningskvittots hash.
3. `python3 -B verktyg/kvalitetsbild.py --fall FALL --ut FALL/KVALITETSBILD.md` — samlar körningarnas kvitton till
   kvalitetsbilden (tekniskt prövat · professionellt bedömt · ej observerat hos verkliga användare).
4. `python3 -B verktyg/verksamhetsuppgifter.py kontrollera|nap|krav VERKSAMHET.json` — kundens verksamhetsuppgifter (NAP, räckvidd,
   öppettider; `fiktiv: true` spärrar de verkliga externa åtgärder som verktygen `sokkonsol.py` och `lokal_synlighet.py` gör eller förbereder, och kontrolleras av annonsberedningen); `python3 -B verktyg/copy_kontroll.py --kalla … --ut RAPPORT.json`
   — copykontrollens rapport (fraser, strukturer, platshållare, metalängder, obligatoriska element; ingen poäng);
   `node verktyg/bild/treatment.mjs`, `brand.mjs` — bildbehandling och varumärkesfiler i kundrepot (kräver `sharp` där).
   `python3 -B verktyg/intervju.py start|svar|fakta|avgor|nasta|status|research --kund KUNDMAPP …` — kundintervjun (tillstånd i
   kundmappen; verktyget skickar inget, sessionen använder beställningens kanal).
   `python3 -B verktyg/kundstart.py skapa|status|hamta|lank|aterkalla --kund KUNDMAPP …` — Kundstart-länken som kanal
   (avsnittet Kanal och form i kundintervju.md; kräver KUNDSTART_BAS_URL och nyckelfil 0600; för in exporten i INTERVJU.json).
   `node verktyg/webblasare/inspektera.mjs|utforska.mjs|besok.mjs …` — webbläsarvägen (Playwright 1.63.0 och Playwright MCP 0.0.82
   pinnade i verktyg/webblasare/package.json; `npm ci` där först): utvecklarinspektion med kontext, utforskande QA med
   regressionsprov, avskärmat besökarprov i egen session med efterkontroll av nätverksloggen (`natverk.jsonl`; ingen spårfil).
   `python3 -I -B ~/nortropic-repos/nortropic-digitala/verktyg/publicera.py --task ID` — integration genom den
   integrerade primäringången, aldrig kandidatens kopia. Bara värdens förseglade uppgifts-id lämnas till Runtimes
   fasta privata launcher. Separat adoption av launcherns exakta bytes kontrolleras före start. Den betrodda hållaren
   verifierar uppgift, kandidat, acceptans, verklig isolerad helsvit, pinnar och separat granskning samt kör fryst
   acceptans credential-isolerat före Appbundna checks och skyddad PR/squash/återläsning. Kommandot kör inga
   kandidatprov/pinnverktyg/gh och skapar inga egna godkännanden. Saknad hållare eller försegling är ett namngivet
   beroende. Äldre --gren/--granskning/--torr/--ingang-syntax är ersatt; historiska publiceringskvitton bevaras.
   Kanaler, lansering och drift: `seo_kontroll.py`, `sokkonsol.py` (plan utan åtkomst, --live med åtkomst), `lokal_synlighet.py`,
   `annonsberedning.py`, `uppfoljning.py`, `prelaunch.py`, `lansering.py`, `drift_kontroll.py` — alla skriver rapport eller kvitto;
   inget av dem startar annonsering, skapar profiler eller lanserar av sig självt.
5. Bygget görs i kundrepot med dagens byggväg (Claude Code eller Codex, Vercel CLI); det ingår i kedjan genom att
   laddningskvittot, mätningarna och kritiken binds till commit och driftsättning (L9).

## Lärande per fall (rytmen)

Varje fall lämnar: lärdomspost (eller "inga nya lärdomar" med skäl) i `kunskap/LARDOMAR.md`; användningsnot per
laddat underlag (fyra utfall) i fallets `ANVANDNINGSNOTER.md`, sammanfattad i kontorsposten; förslagsrad till planens
block "FÖRSLAG ATT PRÖVA I NÄSTA FALL". Användningsnoterna följs upp per underlag; ingen mängd tillämpningar gör något till
praxis av sig själv. Erfarenhet klassas som observation, kundpreferens, hypotes eller dokumenterad felorsak
(`kunskap/LARDOMAR.md`), och ett gemensamt arbetssätt behöver egen motivering, tillämpningsområde, stöd och prövning
innan det skrivs in här eller i `KVALITET.md`. Ett arbetssätt blir inte ogiltigt bara för att det också användes i
Norrglänta.

## Inga rutinmässiga ägarstopp

En beställning bär hela uppdraget till färdig privat förhandsvisning (`MANDAT.md` §2). Brief, koncept, interna
kvalitetsval och vanliga rättningar går inte via ägaren; en intern gransknings- och rättningsloop (`KVALITET.md`)
avgör omtag. Ägaren får den färdiga leveransen och rapporten och lämnar därefter sin bedömning.

Bedömningskontrakt `digitala-kvalitet/2` i `kritik/BEDOMNING-v2.md` gäller nya bedömningar. Kundbehov och
mandat står över intern brief; professionell otillräcklighet kan blockera trots gröna teknikprov. Frys kriterier
före kandidatgranskning, bind faktisk kandidat och öppnade referensbilder; tidigare acceptanser ändras inte.


## Beslut 2026-09-28: bildfält i kritikens svarskontrakt

För nya kvalificerade kritikstarter begränsas den laddade schemamallen, efter manifestkontroll, till exakta
bildplatser per roll och manifestets proveniensvärden. Orsak: ett faktiskt läst bildpaket kan annars ge ett
formgiltigt svar med flera filnamn i samma fält som den semantiska konsumenten korrekt vägrar. Mallarna
anger därför ett bildpar per jämförelseobjekt och ordagrann proveniens. Runtimes schemadialekt kan inte
koppla metadata villkorligt till en viss bild; den befintliga domkontrollen gör fortsatt den kontrollen.
Detta är en transportprecisering, inte en ändring av kvalitetskriterier, stilnivå eller godkännandefilter.
Schema, fråga och domkodspinnar versionsbinds för nya körningar. Frysta laddningar, råsvar och pågående
körningar bevaras; inget gammalt svar normaliseras eller får ett nytt godkännande av denna ändring.


## Beslut 2026-09-28: exakta platser också i seen_files

Ett senare native kontraktsprov genererade exakta bildpar men kommenterade bildplatserna i seen_files.
För nya kvalificerade starter binds därför listans tillåtna värden till det färdigbyggda Runtime-underlaget,
inklusive profilens dokumenterade FILES.md/AGENTS.md. Läsomfång anges i saktext. Detta förebygger formatfel;
enum innebär inte att en fil lästs, och faktisk bildleverans samt den semantiska domkontrollen ändras inte.
Tidigare domar och råsvar lämnas orörda. Beslutet tillhör ett senare delta efter föregående kodgranskning.

## Beslut DIGITALA-YRKESFORMAGA-20260928 — från research till skapande

De tidigare aktiva referensfiltren för lokalitet, företagsbetyg, galleri och konkurrent ersätts av
uppgiftsmotiverade källroller (referensjakt.md). Aktuella kundkällor följer research/brief/koncept/bygge;
research får även hashbundna materialutdrag, uttryckligen obetrodda och inte redan lästa.

Briefarbetet lämnar ett kort skapandeuppdrag och SKAPARUNDERLAG.json vid ny formgivning/större omarbetning.
Vanliga laddaren kopierar valda bilder/tillgångar med hash och skriver SKAPARPAKET.md först i läsordningen.
Obligatoriska kriterier, kundfakta och säkerhetskrav består som fördjupning. Valfria externa resurser kräver
ett motiverat val; ingen automatisk dump av Taste, prototype, PICKER eller Hallmark. Resursens historiska
beslut läses och hel skill/plugin, metod, anpassning, utdrag eller verktyg avgörs för uppgiften. Laddaren
installerar/anropar inget; faktisk användning och påverkan dokumenteras separat.

Tidigt skapas en representativ upplevelse med verkligt innehåll och relevant interaktion på mobil/större vy.
Alternativa riktningar följer osäkerheten, inte fast kvot/enaxelkrav. Granskning jämför faktisk kandidat
med öppnade professionella referenser. Omprov får ett fokuserat konsekvensunderlag, medan bedömningskontrakt
v2 och fastställd täckning gäller oförändrat. Befintliga körspår används för sann resursredovisning; ingen
ny full läsning bara för att samla godkännanden. Skapandeunderlag.md och konsekvensgranskning.md anger formen.


### Behovsval till fungerande integrationsprov

Research/brief laddar daterade standardvägar; välj bara kundens relevanta behov och dokumentera
plan, konto, kostnad, begränsningar och ansvar. Bygge/prov använder `verktyg/integrationer.py`
och dess exempel, samt befintliga kanalverktyg via delegaten. Kontraktsprov, provider-test och
verklig integration är skilda nivåer. Prelaunch/leverans/drift återläser vad som faktiskt
fungerar och vilket externt led som återstår, utan att gömma saknad kod bakom en token.

### Övergång till starkare kundbindning 2026-09-28

Äldre klarmarkeringar vars kvitton saknar aktuellt intag, skaparpaket eller integrationsval återöppnas vid första kontrollen. Historik, kvitton och utförda sidoeffekter bevaras; publicera/skicka inte samma sak igen. Läs orsaken och ompröva relevant underlag, inte hela historiken av slentrian. research-intervju.md är intervjuns intag; researchsteget skriver sin syntes i research.md. Nytt intag kräver vanlig omladdning.

Vid skrivande Kundstart-import normaliseras också äldre falska motsägelser mellan
okänt och en strikt senare, fortfarande aktuell kundutsaga från samma fråga.
Föregående intervju, intagsutdrag och arbetsuppgift sparas privat före ändringen;
motsägelsen avgörs med skäl och källrevision, den raderas inte. Råexporter och
kvitterade signaler skickas inte om. Aktuellt intagsutdrag ändras och ordinarie
faktabindning omprövar research/följdsteg. Två kända motstridiga uppgifter och
rena statusläsningar lämnas orörda. Okänt skapar inte i sig en ny sakmotsägelse.

Normaliseringen kräver att båda svaren återfinns ordagrant i senast importerade,
hashbundna exporten. Behov och öppen täckning bevaras i det gemensamma intagsutdraget.
Äldre motsägelser i omvänd riktning eller med en senare ersatt utsaga prövas via
vanlig `intervju avgor`; de autoavgörs inte. En skadad föregångarkopia bevaras och
återställs från verifierat underlag före omprov, aldrig genom att radera historiken.

## Beslut 2026-09-28: överför arbetsresultat med lästa filbytes

Fortsättningsuppdragets bevarade assistans visar att ett privat provskript fyllde tre
null-hashar och kopierade en modellvald bilaga. Den gemensamma vägen får därför
`fortsatt.py overfor --fall FALL --steg research|brief`: bevara modelloriginal, validera
alla valda filer före skrivning, bind faktiskt lästa bytes, bevara tidigare kundfiler
och återuppta avbrott utan nya externa handlingar. `klart` och dess sak-/beviskrav
gäller fortfarande. Detta gäller avskilda laddade arbetsytor, inte kundspecifika designval.
Researchunderlaget skiljer dessutom uttrycklig kunduppgift från extern verifiering och
från okänt. Rättningen motiveras av den observerade felklassningen i kundfortsättningen;
modellens allmänna semantiska förmåga är inte därmed verifierad.

Kompositionsprecisering i samma fortsättning: tidigare keramik-/energiprov visade
obalanserade bild/textkolumner och mindre genomarbetad mobilprioritering trots vald
referens. Skapandeunderlaget kräver därför ett konkret kompositionsbeslut och ett
avgränsat renderat omprov med verkligt innehåll före utbyggnad. Metoden prövas på
befintligt material; de egna proven blir ingen estetisk mall och inför inga stilkrav.

## Beslut 2026-09-28: avgränsad formåterhämtning av kritik

Ordinarie profilkonsument och kvalitetsbild får återhämta ett komplett tidigare sakligt
råsvar när endast ett tillåtet prosafälts form är ogiltig. Exakta originalbindningar
till kandidat, fråga, schema, bilder, kriterier och domkod består; originalet bevaras.
En liten formrättning och separat innebördskontroll måste lyckas. Ändrad dom, blockerare,
risk, bevisräckvidd eller semantisk domkod vägras. Historiska kodbytes används endast
som hashunderlag; ingen äldre godtycklig kod importeras. Ny pinnversion gäller den
ändrade konsumentkopplingen, inte en ändring av professionens v2-bedömningskriterier.

Separat kundpaketgranskning B1–B3/O1–O7 preciserar överföringen: valfritt skaparpaket i brief, historisk omladdning utan förfalskad färskhet, kanoniska filnamn/bevispekare, dynamiskt skiftlägesoberoende skrivskydd, symlinkfri historik och validerade valfria research-/integrationsutdata. Oförändrade sak-/beviskrav kvarstår. Ny pinnversion binder denna rättning; ingen kundpreferens eller produktsida blir metodpraxis.

Separat formgranskning skärper samma återhämtningsväg: konsumentens aktuella kodbindning skiljs från ursprunglig bedömningsbindning; råström, sessionsbevis och Runtime-proveniens jämförs. Kvalitetsbilden visar att ursprungssessionen saknade terminal och att innebördskontrollen är en modellbedömning. Pinnuppdateringen omfattar dessa konsumenträttningar och historikladdaren; gränser, sakdom och beviskrav ändras inte.

## Beslut 2026-09-28: aktuell materialkälla också i brief

Ett faktiskt kontinuitetsprov visade att briefsteget fick intern research men inte kundmaterialets
utdrag och sedan skärpte en verifieringsuppgift till ett obelagt existenspåstående. Samma befintliga
hash- och sökvägskontroll för aktuella materialutdrag gäller därför både research och brief. Utdragen
är obetrodda, laddade och inte redan lästa; koncept/bygge får fortfarande det motiverade urvalet via
skaparpaketet. Historiska körningar och kundfiler ändras inte.

Briefens bevisregel prioriterar aktuell kundkälla före intern syntes, skiljer verifieringsbehov från
belagt innehåll och binder en saknad uppgift till just dess beroende åtgärd. Oberoende arbete inom
accepterad omfattning fortsätter utan generell spärr på hela projektet. Detta är en generell
käll- och proportioneringsrättning, ingen kundspecifik innehållsregel eller visad modellaccept.
Ny läsning av briefmallen och laddarens kontrollmotivering ligger till grund för berörda nya pinnar.

Separat kundpaketgranskning r2 prövar också omladdning efter historiska schema-/resursfel:
brief bevarar originalpaketet som råhistorik utan valauktoritet och markerar fel; otillgängliga
val aktiveras inte och osäkra källor följs inte. Koncept/bygge behåller strikt validering med
anvisning att ompröva brief. En ändrad historisk fil får en separat hash av nu observerade bytes,
aldrig ny godkänd paketbindning, så omarbetning kan skydda mot ännu en samtidig ändring.
Överföringen bokför förberedd historik före första kundskrivning och återläser dess bindningar
före avbrottsåterhämtning; befintliga filrättigheter bevaras och valda bevispekare får kanoniska namn.

Samma återhämtningsproveniens visas även i kvalitetsbildens publika JSON-utdata: ursprunglig
konsumentbindning samt Runtimes format-/sessionsmetadata följer med statusraden. Denna
pinnuppdatering rättar en utelämnad projektion, utan ändrad sakdom eller godkännanderegel.


## Beslut DIGITALA-KREATIV-ARBETSKEDJA-20260928 — skapande och första återkoppling

Vid ny riktning eller kvalitetsomarbetning tillämpas skapandeunderlag.md:s första arbetsvarv
från det vanliga genererade SKAPARPAKET.md. Behov, verkligt innehåll, bild/representation och
handling styr kompositionen före tokenplan; externa original behålls och egna anpassningar
är märkta. Kundkrav, interna designhypoteser och provbegränsningar hålls isär. Skaparen ska
få faktisk browseråterkoppling under konceptarbetet, själv eller genom uttrycklig intern
överlämning. Separat produktkritik prövar helheten innan utbyggnad. Metodens stöd är den
riktade diagnosen av befintliga produktioners faktiska läs- och beslutsspår; detta är ingen
allmän effektgaranti, stilregel eller ny Runtime-mekanism. Avgränsat arbetsprov och kvarstående
osäkerhet redovisas privat i samma Digitala-uppdrags kreativ-rattning-r1.

## Beslut 2026-09-30 — formkrav och primärkällor (OVL-20260930-b35d4f-digitala)

Backloggens genomförandemandat omfattar K1–K5 och A1–A6: kundrättelser av telefon
eller öppettider får gemensamma formkrav och modellfri diffkontroll. Den stängda
listan vidgas inte och prisets klassning lämnas oförändrad. LPTT och samtycke är
juridikflaggor; licensregister, CSP per rutt, TBT och HTML-prov utan JavaScript
kompletterar befintliga kontroller. Primärkällorna omlästa 2026-09-30 enligt
REGISTER.md och respektive professionsfil. Pinnuppdateringen gäller dessa lästa
ändringar. Ingen kundsajt, ny rättighet eller extern aktivering ingår.

## Beslut 2026-09-30 — betalval, drift och hitta hit (OVL-20260930-ac1914-digitala)

Backloggens genomförandemandat omfattar S1–S3, D1–D4 och H1. Daterade Stripe-villkor
och Swish-kontraktsprov kompletterar standardvägen; ett saknat faktiskt sandboxprov
redovisas EJ_MATT enligt beställningens uttryckliga undantag. Drift får sidrutter,
handlingslänkar och okänt utan ändrade gamla incidentfält eller exit-koder. Hitta hit
har text/länk som bas och valstyrd extern karta eller licensbelagd statisk bild.
Ändrade professionsfiler pinnas efter ny källäsning 2026-09-30. Inga nya konton,
avgifter, villkor, kundändringar eller Runtime-aktiveringar omfattas.

## Beslut 2026-09-30 — läsande länkkontroll (OVL-20260930-b17920-digitala)

Genomförandemandatet omfattar L1–L6 efter D1–D4:s integration. Slutadress,
felsidetitel, avgränsade omförsök och total HTTP-tidsgräns kompletterar kvittot;
lanseringskontrollen prövar gamla adresser med GET. Tredjeparts osäkra lägen enligt
D3 behålls som okända, medan egna tidsfel är incidenter. Sitemapens budget räknar
också hopp/omförsök, med ursprungsgränsen kvar. Ingen kundkontakt, leverantörsskrivning,
schemaläggning eller ändring i DRIFT.json ingår. Prov använder bara lokala fejkservrar.

Ny pinne gäller detta beslut i ARBETSSATT.md samt drift.md, lansering.md **och** den obligatoriska lärdomsposten i
LARDOMAR.md: den sistnämnda är redan pinnad i steg/PINNAR.sha256 och kan därför
inte ändras med bibehållen gammal hash. Detta är en teknisk anpassning av L5:s
tvåradsformulering för att också uppfylla beställningens klart-när, inte nya ägarord.

## Beslut 2026-09-30 — e-postkontroll och migreringsarkiv (OVL-20260930-dbbdd8-digitala)

Genomförandemandatet omfattar M1–M2, inklusive de tidigare uppskjutna punkterna inför första
riktiga kund. Lanseringsplanen får läsande e-postkontroll och privat arkiv före migrering.
DNS läses med standardbiblioteket och befintlig tidsbegränsad transport; Playwright används
utan nya beroenden. Prov använder injicerad DNS och lokala syntetiska sidor. Kundens verkliga
DNS, leverantörskonto och sajt lämnas till respektive kundbeställning. Ny läsning av Gmail,
Cloudflare DNS JSON och Playwrights HAR-dokumentation 2026-09-30 ligger till grund för
REGISTER.md, professionsfilerna och deras nya pinnar. DNS-förekomst och ett avgränsat arkiv
är inga bevis för faktisk e-postleverans eller fullständig bevaring av hela webbplatsen.
