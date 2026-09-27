# Annonser (Google Ads och Meta Ads) — kanal- och kampanjberedning utan spendering

Professionsfil (HELHET-20260927, avsnitt 4 "Google Ads och Meta Ads"; nytt, fanns inte i det arkiverade repot).
Laddas i steget `annonsberedning`. Verktyg: `verktyg/annonsberedning.py` (utkast/pausade objekt ur en kanalplan;
resultatläsning ur export). Ingen automatisk annonseringsstart eller spendering utan befintligt uttryckligt mandat
(ordern avsnitt 4 och 9): allt som byggs har status PAUSED, och en beställning som namnger budget och period krävs
före aktivering. En fiktiv verksamhet får kampanjutkast för systemprov men aldrig en verklig överföring.

## Beredningens delar (kanalplanen, `KANALPLAN.json`)

1. **Mål**: `leads`, `samtal`, `bokningar`, `kop`, `besok_i_butik`, `kannedom` eller `trafik` — ur beredningens
   verksamhetsmål; ett mål per plan.
2. **Målgrupp**: ur briefen §2 (vem, var, när); geografi ur räckvidden; för Meta intressen bara med skäl.
3. **Budskap**: samma löfte som landningssidan; sanna påståenden (copy-kontroll.md gäller annonstext).
4. **Kreativa tillgångar**: rubriker och beskrivningar inom plattformens gränser (Google: rubrik ≤ 30, beskrivning
   ≤ 90 tecken, minst tre rubriker och två beskrivningar; Meta: primär text visas avkortad över ~125 tecken, rubrik
   ≤ 40, beskrivning ≤ 30); bilder och video med rättigheter (bild.md); genererade personer aldrig som verkliga.
5. **Landningssidans överensstämmelse**: annons och sida säger samma sak; sidan finns i bygget och bär budskapets
   ord (verktyget mäter ordöverlapp som indikator, inte som facit); sidan uppfyller uppgiften utan omvägar.
6. **Spårning**: UTM per kampanj (`utm_source`, `utm_medium`, `utm_campaign`, `utm_content` vid varianter);
   konverteringshändelser ur mätplanen (uppfoljning.md); plattformens konverteringsimport bara med samtycke.
7. **Konverteringsdefinitioner**: vilka händelser räknas, med värde när det finns; en per affärsutfall.
8. **Budgetvillkor**: valuta SEK, högsta dagsbudget, och villkoret som namnger mandatet; utan villkor byggs inget.
9. **Utkast/pausade objekt**: `google-ads.json` (kampanj, annonsgrupp, sökord med matchtyp, negativa sökord,
   responsiv sökannons, konverteringsåtgärder) och `meta-ads.json` (kampanj, annonsuppsättning, annons) i
   plattformarnas objektform, `BEREDNING.md` för läsning.
10. **Resultatläsning**: `rapport --export` läser plattformens export; affärsnytta (konverteringar, kostnad per
    konvertering) skilt från proxy (klick, visningar); plattformens attribution jämförs med kundens verkliga inflöde.

## Överföring och aktivering — externa beroenden

Google Ads API: utvecklartoken (ansökan), OAuth-klient, kund-id under ett förvaltarkonto; Meta Marketing API:
app med behörighet ads_management, systemanvändartoken, annonskonto. **Ingen av dessa finns (2026-09-27).**
Utkasten är kompletta objekt som kan föras över av en behörig människa i plattformarnas gränssnitt eller av ett
senare verktyg med åtkomst; status PAUSED tills mandatet säger annat. Ett utkast är inte en körd kampanj.
