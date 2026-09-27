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
mandat: uppstart, beredning, research, matning, kritik, granskning-d, provare, prelaunch, drift. Kanalstegen (seo,
sokkonsol, lokal-synlighet, annonsberedning, uppfoljning) används när kundens uppdrag motiverar dem (beredningens
kanalbehov); alla kunder får inte alla kanaler.

## Proportion — tre storlekar

| Storlek | Exempel | Steg som körs | Vad som INTE körs |
|---|---|---|---|
| **Liten** (ändring inom befintligt innehåll och komposition) | rätta en trasig länk, ett stavfel, en kontrast | uppstart (kort) → [beställning] → bygge (avgränsat) → matning (berörd sida) → granskning-d (kort, berörd kod) → leverans (kort) | brief, koncept, kritik, provare |
| **Mellan** (ny sida eller ny sektion inom gällande riktning) | ny landningssida | uppstart → [beställning] → brief-avsnitt → bygge → redaktionellt-pass → matning → kritik (renderingsläsning) → granskning-d → provare (ett scenario) → leverans | koncept, om riktningen är beslutad |
| **Stor** (ny riktning, ny informationsarkitektur, ny kund) | omformning, ny kund | alla steg, med koncept före bygge och kontorets beredning (behov, osäkerheter, metodval, beslutsunderlag) | — |

Också en liten uppgift på en levererad sajt kräver en beställnings beslutspost: underhåll mellan beställningar är en
namngiven saknad gräns i `MANDAT.md` §3, inte stående mandat.

Kontoret bidrar vid mellan och stor uppgift med problemformulering, osäkerheter, proportionerligt metodval och
beslutsunderlag genom sin beredning (AP-06, fältet `forvaltning`); Digitalas sakkunskap får påverka både
problemformuleringen och metodvalet. Vid liten uppgift behövs inget av det.

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
