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
