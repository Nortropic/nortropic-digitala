# Integrationer och redaktörsupplevelse — formulär och leads, bokning, kundregister, betalning, redigering

Professionsfil (ägarens tillägg 2, avsnitt 6). Laddas i stegen `brief` (§4, §9) och `bygge`, och vid `prelaunch`
(grind 1). Behovet styr: kundsvar eller researchfynd → motiverat leveranskrav → vald metod eller tjänst → implementation
→ kontroll → leveransbevis. En lista över API:er är inte en integration; ett mockat svar är inte en verifierad
liveanslutning; en länk, en inbäddning, en kalenderhändelse och en verifierad bokning är olika leveranser.

## Formulär och leads — en kedja, inte ett gränssnitt

| Led | Krav | Kontroll |
|---|---|---|
| Fält och validering | fält motiverade av uppgiften (brief §4); servervalidering av varje fält; honeypot och tidsfälla på en klocka (formularsakerhet.md) | prov med giltiga och ogiltiga indata |
| Mottagning | rätt mottagare eller system ur intervjun (C1, D1); reservväg när mottagaren är borta (C2) | leverans till kontrollerad testmottagare i förhandsvisning |
| Sant besked | besökaren får veta vad som faktiskt hänt: begäran accepterad ≠ meddelande skickat ≠ nästa led bekräftat | texterna prövas mot kedjans verkliga status |
| Fel | fel visas med alternativ väg (telefon, e-post); inga tysta fel | felväg provad (mottagare nere, ogiltig adress) |
| Dubbletter | dubbla inskick och återförsök ger inte dubbla ärenden (idempotensnyckel eller tidsfönster) | dubbelt inskick provat |
| Fortsatt hantering | vem gör vad efter inskick (intervju C1–C3); kundregister bara när behovet motiverar det | beskrivet i briefen §4 och prövat i slutprovet |

Leveransen är provet: ett meddelande som anlänt till testmottagaren, inte en svarskod. I produktion prövas kedjan med
kundens riktiga mottagare bara enligt mandat och med tydlig märkning av testärenden.

## Bokning och kalender

Utreds ur intervjun (BOK1–BOK4): tjänster och längder, personal och resurser, tillgänglighet och buffertar, samtidiga
försök, bekräftelse, ombokning, avbokning, tidszon, befintligt system. Integrationsnivåer, från enklast: (1) länk till
etablerad bokningstjänst; (2) inbäddad bokningsvy; (3) kalenderhändelse skapad i kundens kalender; (4) verifierad
bokning i kundens system med bekräftelse. Välj lägsta nivå som uppfyller behovet; bygg ingen egen bokningsmotor.
Kontroll: en riktig testbokning i testmiljö eller kontrollerat konto, inklusive ombokning och avbokning; verklig
räckvidd redovisas (vad som prövades, vad som inte kunde prövas).

## Kundregister, betalning och övriga verksamhetssystem

Koppla bara det uppdraget behöver: datamappning per kund (vilka fält, vart), tillåtna rättigheter (minsta åtkomst,
egen nyckel, aldrig kundens huvudinloggning), rätt miljö (test kontra produktion), felhantering och prov. Betalning
på webbplatsen sätter juridikflaggan e-handel/distansavtal (juridikflaggor.md) och görs genom etablerad betaltjänst.
Åtkomst begärs på säker väg (åtkomstfil 0600 utanför repot), aldrig i intervjusvar.

## Redaktörsupplevelse

Kunden eller Digitala ska kunna hålla innehållet aktuellt utan Git eller terminal: en redigeringsväg efter vana och
frekvens (intervju G1) — innehållsfiler redigerade av Digitala på kundens begäran, ett enkelt CMS med förhandsvisning,
eller kundens befintliga verktyg; förhandsvisning före publicering och återgång till föregående version. Innehållsmodell
efter behov (bygge-referens.md). Redigeringsvägen prövas: en ändring görs av rätt roll, förhandsvisas, publiceras och
återgås.

## Drift utanför ägarens Mac

Kundens formulär, bokningar och andra besökarfunktioner körs hos värdplattformen och tjänsterna, aldrig genom en
byggsession eller ägarens dator. Nortropics förvaltningsarbete (kontroll, rapport, ändringar enligt mandat) är skilt
från kundlösningens driftmiljö. Övervakning, ansvar och återgång står i drift.md och lansering.md.


## Körbara etablerade standardvägar – 2026-09-28

Vid relevant behov används [integrationer-standardvagar.md](integrationer-standardvagar.md) och
[exempel/integrationer/README.md](../exempel/integrationer/README.md). `verktyg/integrationer.py`
kopplar val, testad mottagning och provideradaptrar till befintliga kanalverktyg. En gratis
leverantörsvy är inte gratis API eller verifierad kundintegration. Kundens befintliga system
och riktiga krav styr valet; gruppkapacitet/resursdelning prövas separat när de behövs.
Vikskärs särskilda femtonminutersreservation är ett historiskt kundfall, ingen generell norm.

Exemplens lokala server är ett prov. Kunddrift kräver kundens host och beständig lagring;
Johnnys Mac och en byggsession får inte vara kundens mottagnings-/bokningsdrift. Bevara
redaktörsroller, preview/återgång, CRM-ansvar och faktiska kanalutfall från tidigare krav.

## Hitta hit — basväg (OVL-20260930-ac1914-digitala, 2026-09-30)

Adressen ska alltid finnas som text, tillsammans med en vanlig länk som öppnar
vägbeskrivning. En leverantörslänk kan öppna kartappen när den finns, annars dess
webbversion; ingen bestämd app garanteras.
[Google Maps URL-format](https://developers.google.com/maps/documentation/urls/get-started),
läst 2026-09-30, är ett exempel utan API-nyckel; leverantören är inget obligatoriskt val.

Om brief §4 behöver karta på sidan: välj självhostad statisk bild med belagd
användningsrätt och synlig attribution, eller skapa extern iframe först efter
besökarens uttryckliga val. Inget iframe-src, skript från kartleverantören,
preconnect eller prefetch före valet. `loading=lazy` är inte en sådan gräns.
Informera vid knappen om vilken tjänst som kontaktas. Adress/länk ska fortfarande
fungera utan JS och utan extern karta. Basen i `juridikflaggor.md` gäller; ett klick
är ingen generell rättslig garanti för leverantörens fortsatta spårning.

För en statisk bild: spara källa, licens, läsdatum, attribution och själva bilden
i kundens bildregister enligt `bild.md`. OSM är ett möjligt val: dess
[licenssida](https://www.openstreetmap.org/copyright), läst 2026-09-30, kräver
källangivelse till OpenStreetMap och dess bidragsgivare samt tydlig ODbL-information.
[Tile-policyn](https://operations.osmfoundation.org/policies/tiles/), läst samma dag,
förbjuder bulk-/förhandshämtning; fri kartdata innebär inte fri obegränsad tile-tjänst.
Kontrollera bildexportens egna villkor före användning, och hämta aldrig tile-arkiv
som genväg. Exemplet `exempel/integrationer/hitta-hit.html` använder den andra vägen,
klickladdad inbäddning med attribution intill. Browserprovet använder ett syntetiskt
svar för leverantörsadressen och visar noll externa förfrågningar före klick.
