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

## Överföring och återläsning

`annonsberedning.py overfor --kanal google|meta --verksamhet ... --kanalplan ... --bygge ...
--konfiguration /privat/konto.json --ut /privat/KVITTO.json` använder begränsade API-adaptrar. Fiktivspärren
prövas först. Öppna beredningsfynd stoppar all överföring. Konfigurationsfilen ska ligga utanför repot med
rättighet 0600; inga standardhemligheter eller konton söks. Inga värden får kopieras till leveransdokument.

Konfiguration: schema `digitala-annonskonto/1`, `kanal`, `verksamhet`, `plan_sha256` (kanonisk hash genom
annonsadapter.sha av exakt kanalplan), `tillat_paused_overforing: true`, namngivet `mandat`, `valuta: SEK`,
`api_version`, `access_token`, samt `kampanjer` med planens kampanjnamn som nycklar. Google kräver dessutom
`developer_token`, `customer_id` och valfritt `login_customer_id`. Meta kräver `ad_account_id` utan act_-prefix.
Alla id och API-versioner anges explicit; inget konto skapas. Token skickas enbart till respektive plattforms
fasta HTTPS-värd, aldrig genom omdirigering. Felbody med möjliga känsliga värden skrivs inte ut.

Google stöder Search med manuell CPC, pausad kampanj/grupp/responsiv annons och positiva sökord, negativa
sökord samt explicit geo-/språk-id. Varje kampanjmapping kräver `geo_ids`, `language_ids`, `cpc_bid_micros`
och sakbeslutet `eu_politiskt_innehall: false`; andra politiska klassningar stöds inte av adaptern.
Meta stöder webbtrafik med pausad kampanj/adset/annons. Mapping kräver befintlig `page_id`, uppladdad
`image_hash`, `bildrattighet` och verifierad `targeting` inklusive `geo_locations`. Creative byggs av den
bundna planens text och UTM-länk. Andra Meta-mål vägras: lead/sales kräver separat konto-, händelse- och
konverteringskontrakt. Ingen adapter verifierar mottagna konverteringar eller tillskriver annonser resultat.

Kontots valuta återläses före skrivning. Varje anropsavsikt sparas före HTTP, skapade id och råsvar bevaras,
och kampanj/grupp/annons återläses efteråt med samma id/konto och PAUSED-status. Ingen aktiveringsväg finns.
Befintligt utkvittot stoppar nytt skapande. `aterlas --konfiguration ... --ut befintligt-kvitto.json` läser bara;
en partiell överföring blir aldrig komplett enbart för att dess återstående objekt är pausade. Tappat svar
med okänt skapandeutfall kräver avstämning mot plattformen, inte blind POST-retry. Testtransport märks tydligt;
en lyckad sådan körning bevisar inget om kontoåtkomst eller extern mottagning.

Tekniska primärkällor: [Google REST mutate](https://developers.google.com/google-ads/api/rest/common/mutate),
[Google REST examples/search](https://developers.google.com/google-ads/api/rest/examples) och
[Metas officiella AdAccount SDK-kontrakt](https://github.com/facebook/facebook-python-business-sdk/blob/main/facebook_business/adobjects/adaccount.py).
Granskade 2026-09-28. Liveacceptans återstår tills behörig kontokonfiguration, explicit överföringsmandat och
plattformens verkliga svar finns. Åtkomst är ett namngivet beroende, ingen allmän utsaga om vilka konton som finns.
