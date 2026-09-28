# Sökkonsol (Google Search Console) — åtkomst, egenskap, sitemap, inspektion, sökdata och tolkning

Professionsfil (HELHET-20260927, avsnitt 4 "Search Console"). Laddas i steget `sokkonsol`. Verktyg:
`verktyg/sokkonsol.py` (plan utan åtkomst; live med åtkomst; kvitto per anrop). Bara för skarpa verksamheter: en
fiktiv verksamhet (`fiktiv: true`) får ingen egenskap, och verktyget vägrar.

## Åtkomst- och ägarskapsväg

- Egenskapen är kundens tillgång. Verifiering sker med META-taggen (`token`), renderad i `<head>` på den kanoniska
  produktionsdomänen; taggen ligger kvar för alltid (tas den bort tappas verifieringen tyst). DNS-verifiering
  (domänegenskap) bara när kundens zon förvaltas av oss.
- Kontot som verifierar blir ägare; kunden läggs till som ägare (`sokkonsol_agare` i `VERKSAMHET.json`) och kontoret
  som hanterare enligt avtal; vid avslut tas kontorets konto bort.
- Åtkomst i en privat fil (0600) utanför repot: OAuth-klient med scopes `webmasters` och `siteverification`
  (refresh-token-flödet) eller tjänstekontonyckel (JWT signerad lokalt). **Extern aktivering som återstår (2026-09-27):**
  ett Google Cloud-projekt med Site Verification API och Search Console API aktiverade och en OAuth-klient eller ett
  tjänstekonto; ingen sådan åtkomst finns på maskinen. Tills dess ger verktyget anropsplanen, som är exakt vad som
  körs, och kvittot märker `live: false`.

## Egenskap, sitemap och inspektion

Ordning på lanseringsdagen (lansering.md): (1) noindex borta, verifierat; (2) `verifiera --live`: verifiering,
ägare, egenskap, sitemap; (3) `inspektera --live` för start och de viktigaste sidorna; (4) Bing Webmaster Tools
importerar egenskapen (människa). Sitemapens adress är `https://<domän>/sitemap.xml`. Egenskapen är av URL-prefix-typ:
www och apex är skilda egenskaper, därför måste den andra varianten omdirigera 301.

## Sökdata och tolkning — observationer till åtgärder

| Observation | Läsning | Åtgärd |
|---|---|---|
| "Upptäckt, för närvarande inte indexerad" > 2 veckor på viktiga sidor | Google har sett adressen men inte prioriterat den | begär indexering igen; stärk intern länkning; kontrollera att sidan har substans |
| "Genomsökt, för närvarande inte indexerad" | innehållet bedöms tunt eller dubblerat | fördjupa eller slå ihop sidor; kontrollera canonical |
| Frågor i position 5–20 med visningar | sidan svarar delvis | ta in frågans lydelse i sidan eller FAQ; förbättra rubrik |
| Visningar utan klick | titeln eller beskrivningen lockar inte | skriv om `description`, gör titeln konkret |
| Återkommande frågor om ny tjänst eller ort | ett behov utan sida | ny sida bara med genuint innehåll |
| Core Web Vitals-rapporten (fältdata) | verklig upplevelse hos besökare (saknas ofta vid låg trafik) | åtgärda LCP/CLS/INP-orsaken; Lighthouse är labbdata och inget "Googles betyg" |
| Manuella åtgärder | ska vara tom | vid post: åtgärda och begär omprövning |

Rutin: veckorna 1–2 efter lansering var 2–3 dag; därefter månadsvis (uppfoljning.md). Söktermslistan är
ofullständig (Google döljer sällsynta frågor); termer redovisas som exempel, aldrig som total. Positiva data för en
oindexerad förhandsvisning finns inte och hittas inte på.

## API-referens (läst 2026-09-27)

Site Verification API v1 (`webResource.getToken`, `insert`, `update`), Search Console API (`sites.add`,
`sitemaps.submit`, `searchanalytics.query`, `urlInspection.index.inspect`); adresserna står i verktygets kvitto.
Verktygets anrop är byggda mot dokumentationen och prövade mot inspelade svar; live-anrop är inte körda (ingen
åtkomst). Ett prov mot inspelade svar är inte en verifierad live-integration.


## Beständigt anropskvitto och okänt utfall

`--ut` är en engångsfil: en befintlig fil vägras före nätanrop och skrivs aldrig över. Verktyget sparar
anropsavsikten före transporten och status/svar före nästa steg. Timeout, namnuppslagsfel och tappat svar ger
status 0 och uttryckligt okänt utfall (exit 2), aldrig framgång. Även ett hårt avbrott lämnar den senaste
avsikten som okänd. Ett tidigare mottaget verifieringssvar finns kvar när ett senare steg fallerar.
Kvittofilen är privat (0600); authorization och tokenvärden skrivs inte ut.

Kvitto schema 2 binder verksamhetsfil, åtkomstkonfigurationens hash utan värden, verktygskod, plan och varje
faktiskt anrops metod/adress/nyttolasthash. `transport` innehåller också preflight och autentisering, med
status, sanerat svar och svarshash. `anrop` innehåller kanalstegens tolkning. `provniva: testtransport` är ett
lokalt kodprov, även om kommandot använder `--live` för att pröva den riktiga kontrollvägen. Besvarade
API-anrop bevisar varken indexering eller fungerande drift.

Efter okänt muteringsutfall ska ansvarig först läsa kvittot och stämma av leverantörens verkliga tillstånd.
Dokumentera utförare, observation, källa och beslut i kundfallet innan ett avsiktligt nytt försök med ny
kvittofil. Engångsspärren gäller den angivna filen, inte alla tänkbara filnamn eller andra klienter; att bara
byta filnamn är ingen avstämning. Verktyget återupptar inte en okänd mutation automatiskt. De begränsade
HTTP-återförsöken gäller endast uttryckligen tillåtna läsningar/idempotenta PUT och kända övergående svar,
aldrig verifierings-POST eller status 0.
