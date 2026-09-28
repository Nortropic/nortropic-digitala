# Skapandeunderlag — ett kort uppdrag med tillgänglig fördjupning

Kundens brief och källor är sanningsgrund. Skaparen behöver först den aktuella uppgiften, riktigt innehåll,
visuell ambition och valda bilder, inte hela systemets revisions- och driftshistoria. Skapa vid ny formgivning
eller större omarbetning kundens SKAPARUPPDRAG.md och SKAPARUNDERLAG.json under briefarbetet. En liten rättning
kan använda befintlig brief direkt; avsaknad av paket får aldrig påstås vara komplett skapandeberedning.

## SKAPARUPPDRAG.md

Skriv kort, med källpekare och behovs-id ur aktuellt kundunderlag:

1. **Uppgift och verkligt innehåll**: för vem, viktigaste handling, erbjudande, fakta med källa/status,
   relevant innehåll att faktiskt rendera. Öppna fakta och motstridiga uppgifter får inte bli fria påståenden.
2. **Visuell ambition och frihetsgrader**: vilket intryck och vilken förståelse som behövs, vad som får
   omprövas, vad som är kundkrav respektive intern designhypotes. Ingen förvald minimalism eller stark färg.
3. **Referensbeslut**: valda bransch-/hantverks-/UX-källor och exakt vad de påverkar. Komposition, innehåll,
   interaktion och mobilbeteende före enbart palett/typsnitt. Skriv vad som avvisas och varför.
4. **Tillgångar och produktion**: bildval, rättigheter, motivens sanningsanspråk, relevant stack/drift,
   redigeringsbehov, funktionens slutbesked och verkliga providergränser. Välj bildverktyg när uppgiften behöver dem.
5. **Första prövning**: en representativ sida eller bärande sektion med riktigt innehåll, bild och relevant
   interaktion på mobil och större skärm. Olika riktningar när osäkerheten motiverar det; ingen fast kvot eller
   obligatorisk enaxelmetod. En riktning ska synas i undersidor, formulär, tom-/fel-/laddningslägen och mobil.

Mandat och aktuella kundfakta gäller framför sammanfattningen. Vid konflikt rättas sammanfattningen och berörda
val. Oberoende arbete fortsätter vid avgränsad åtkomstbrist; ett provblockerat efterled blir aldrig fakeframgång.

## Maskinläsbar koppling till den vanliga laddaren

`SKAPARUNDERLAG.json` har exakt dessa fält (alla listor får vara tomma när sakskäl finns i uppdraget):

```json
{
 "schema": "digitala-skaparunderlag/1",
 "uppdrag": {"fil": "SKAPARUPPDRAG.md", "sha256": "<full sha256>"},
 "bilagor": [{"fil": "referenser/exempel-390.png", "sha256": "<full sha256>",
              "roll": "referensbild", "varfor": "Öppnad mobilvy som visar den jämförda hierarkin."}],
 "referenser": [{"id": "ref-a", "kalla": "https://example.org/",
                 "roller": ["bransch", "hantverk"], "urvalsskal": "Observerad tydlig tjänstehierarki.",
                 "observation": "live", "bevis": ["referenser/exempel-390.png"],
                 "paverkar": "Jämför valen av tjänst i den egna mobila sidan.",
                 "begransning": "Ingen verklig bokning eller användarstudie."}],
 "resurser": [{"fil": "kunskap/externa/emil-prototype-SKILL.md", "form": "metod",
               "delar": "Operating Posture och Workflow efter uppgiftens osäkerhet",
               "skal": "Pröva innehållshierarki och bildroll innan full utbyggnad.",
               "historik": "REGISTER §A7/§F och aktuellt resursbeslut; ingen spärr lyfts."}]
}
```

Bilageroller: `fakta`, `referensbild`, `beteende`, `tillgang`. Referensroller: `bransch`, `hantverk`, `ux`.
Observation: `live`, `galleri`, `text`, `delvis`, `otillganglig`. Referensens bevis måste vara namngivna bilagor;
live/galleri behöver bildfil, andra observerade källor minst ett underlag. Bilder visar det dokumenterade
ögonblicket; deras hash bevisar inte att utföraren har öppnat dem. Tid/vy/observerat beteende anges i bilagans
not eller uppdraget och i bedömningsmanifestet när bilden används i kritik. Samma källa får flera roller.

Alla kundfiler är relativa kundmappen, utan symlänkar, och hashkontrolleras före laddning. Resurser pekar på
befintliga pinnade filer i kunskap/externa; nya resurser kräver vanlig läsning/proveniens/versionsbeslut först.
Former: `lasunderlag`, `metod`, `skill`, `plugin`, `verktyg`, `anpassning`, `utdrag`. Valet måste motiveras.
Laddaren kopierar läsunderlaget; den installerar/anropar aldrig skill/plugin/verktyg och får inte bokföra bruk.
Hela relevanta resurser är tillåtna. `delar` är läsanvisning, inte automatisk extraktion eller tillstånd att
utelämna nödvändig säkerhet. En installerad resurs används genom dess riktiga kvalificerade anropsväg.

Koncept/bygge får automatiskt `SKAPARPAKET.md`, uppdraget, valda bilagor och valda resurser i LADDNING.json.
Obligatoriska kriterier, brief och kundkällor finns kvar som namngiven fördjupning. Valfria externa resurser
laddas endast när de valts; frånvaro betyder inte avvisad kompetens. I kritik används samma resursval men
kandidat-/referensbilder kommer endast genom BEDOMNINGSUNDERLAG.json och dess oförändrade v2-kontrakt.
Skaparpaketet ersätter aldrig fördefinierad sid-/lägestäckning eller bildbelägg.

Valen är briefutdata. Om koncept eller bygge behöver byta resurser/inriktning, ompröva briefen med skäl, uppdatera paketet och ladda om följdstegen. Kundens integrationsval ligger vid behov i INTEGRATIONSVAL.json med befintligt schema digitala-integrationsval/1; brief och senare steg laddar och hashbinder samma fil. INTEGRATIONSPLAN.json är härledd körutdata, inte en parallell sanningskälla.

## Resursbeslut och faktiskt bruk

Läs REGISTER §A/D/F/G och relevanta ursprungliga beslut före nya val. En historisk avgränsning är inte ett
permanent förbud. Prototype är metod av specifika invokationsskäl, Taste har lästs utan dess stackmallar,
Impeccable provades utan hook, Hallmark som kritikperspektiv och design.md som format/lint. Dessa är daterade
val, inte en regel att allt ska reduceras till text. Bedöm dagens uppgift och faktisk åtkomst.

Registrera namn, version, behov, vald form, licens/kostnads-/åtkomstkälla och bortvalda delar i uppdragets
resursnot. Exempelvis Claude Design/designlang, Figma eller bildgenerering får utredas när de är relevanta;
verktygsnamnet är inte en installationsorder. Verifiera aktuella villkor före nytt bruk. Ingen ny betalning
eller behörighet antas. Skilj vald → tillgänglig → laddad → läst/anropad → konkret påverkan → observerat utfall.
ANVANDNINGSNOTER.md tar bevispekare till rendering, ändring eller fynd. Rapporterat bruk utan körspår märks så.

Jämför ett avgränsat sammanhängande prov med en enklare direkt väg på samma uppgift, innehåll och tillgångar.
Redovisa tillförd kvalitet och kvarstående brister; ingen kausal effekt påstås från ett enda modellutfall.
Input/output/cache-token, pengar, modellkvot, väntetid, omtag och ägararbete är olika storheter. Använd befintliga
kvitton, markera okänt och undvik nya tunga körningar bara för att fylla en tabell.
