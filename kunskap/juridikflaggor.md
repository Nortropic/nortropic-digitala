# Juridikflaggor — rapportera, aldrig avgöra

Professionsfil (HELHET-20260927, avsnitt 3–4), återvunnen ur det arkiverade repots flagglista. Laddas i steget
`brief` (flaggorna sätts ur research §11) och i steget `prelaunch` (juridikkontrollen rapporterar per flagga).
Juridiska frågor avgörs av människor (ägaren, kunden, vid behov juridiskt ombud); Digitala rapporterar fynd med
källa och lämnar dem till beslut. Inom ett accepterat uppdrag stoppar en flagga inte det övriga arbetet: fyndet går in
i leveransrapporten och i ägarens tur som namngiven fråga.

| Flagga | När den sätts | Vad som ska rapporteras och bevakas |
|---|---|---|
| **hälsa/kropp/medicin** | Behandlingar, kost, kroppsvård med hälsopåståenden | Patientsäkerhetslagens och marknadsföringslagens gränser; beviskrav för påståenden; friskrivningar; aldrig utfallslöften |
| **livsmedel** | Servering, produktion, försäljning av livsmedel | Livsmedelsinformation, allergener, tillstånd |
| **finans/försäkring** | Rådgivning, förmedling, krediter, försäkring | Tillståndskrav (Finansinspektionen), rådgivningsgränser, riskinformation |
| **barn som primär målgrupp** | Verksamheter riktade till barn | Skärpt marknadsföringsregim, samtycke, bilder på barn |
| **alkohol/tobak** | Försäljning eller marknadsföring | Marknadsföringsförbud och begränsningar |
| **e-handel/distansavtal** | Köp, betalning, leverans på sajten | Distansavtalslagen, ångerrätt, betalflöden, villkor; ofta bättre i en handelsplattform än i eget bygge |
| **bokning/inloggning/medlemsdata** | Bokning, konton, personuppgifter i system | Personuppgiftsbehandling, biträdesavtal, extern bokningstjänst som standardval; egen databas och inloggning är systemutveckling med egna krav |
| **ingen flagga (basen)** | Alla | Integritetspolicy (vad som samlas, ändamål, rättslig grund, lagring, rättigheter, kontakt), samtyckesläge för kakor och spårning (inget spårande före samtycke), företagsuppgifter (namn, organisationsnummer, adress eller ort, kontakt), verifierbara påståenden (betyg med källa, "auktoriserad/certifierad" mot register, tillgänglighetslöften), priser inklusive moms mot konsumenter, ROT/RUT-påståenden korrekta |

Regler:

1. En flagga sätts på observation (citat ur research), inte på gissning. Osäkert läge: flaggan sätts med `[OSÄKER]`.
2. Flaggans status i briefen: `rapporterad` (fynd finns, beslut väntar), `hanterad` (beslut och åtgärd dokumenterade
   av människa), `utanför uppdraget` (rekommenderad hänvisning).
3. Juridiska fynd rättas aldrig automatiskt; en text som påstår något som inte kan beläggas tas bort eller märks
   som förslag tills belägg finns, vilket är en redaktionell rättelse, inte en juridisk bedömning.
4. Prelaunch-kontrollen (`verktyg/prelaunch.py`) listar basens punkter och varje satt flagga med fyndrad; den
   godkänner aldrig juridik på egen auktoritet.


## LPTT vid e-handel mot konsument (läst 2026-09-30)

Flagga **LPTT [OSÄKER]** sätts när research/JURIDIK.json anger e-handel eller distansavtal
mot konsument (`e_handel_mot_konsument: true` eller befintlig e-handelsflagga). Människan
bedömer tillämpning och undantag; en teknisk grön rapport avgör inte detta.
[Lag (2023:254), 2, 4 och 10 §§](https://www.riksdagen.se/sv/dokument-och-lagar/dokument/svensk-forfattningssamling/lag-2023254-om-vissa-produkters-och-tjansters_sfs-2023-254/)
omfattar bland annat e-handelstjänster för konsumenter. Mikroföretag — färre än tio
anställda och årsomsättning eller årlig balansomslutning högst två miljoner euro —
är undantagna från tjänsternas tillgänglighetskrav. Undantaget beslutas inte av verktyget.
[PTS har tillsyn över e-handel](https://pts.se/digital-inkludering/lagkrav/introduktion-till-tillganglighetsdirektivet/branschspecifika-krav/)
och beskriver kravet på [information om tjänstens tillgänglighet](https://www.pts.se/digital-inkludering/lagkrav/introduktion-till-tillganglighetsdirektivet/administrativa-krav/).
Prelaunch grind 6 visar flaggan även när den äldre e-handelsflaggan redan hanterats.
