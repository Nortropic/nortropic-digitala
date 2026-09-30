# Lansering — procedur, kontroll, oåterkalleligt och återgång

Professionsfil (HELHET-20260927, avsnitt 4 "Leverans, drift och förbättring"), återvunnen ur det arkiverade repots
cutover-flöde och lanseringssteg. Laddas i steget `lansering`. Verktyg: `verktyg/lansering.py` (plan och läsande
kontroll), `verktyg/sokkonsol.py` (sökkonsolens skrivande steg), värdplattformens CLI (driftsättning, domän, återgång).
Lansering sker bara enligt gällande mandat: en beställning som namnger lansering och domän (MANDAT.md §2); privat
förhandsvisning och slutrapport levereras alltid först.

## Före lanseringsdagen

Lanseringskonfiguration skild från förhandsvisningen (noindex och robots-blockering bara i förhandsvisningen);
kanonisk domänvariant vald, den andra omdirigerar; e-postdomänen kontrollerad och den gamla sajten arkiverad enligt
stegen nedan **före DNS-omläggning och före omdirigeringar från gammal sajt prövas**; sökkonsolens META-token
renderad; prelaunch-rapport redo; domän och certifikat hos värden; återgångsvägen känd (föregående driftsättning
pekas tillbaka med värdplattformens CLI).

### E-postdomän — läsande kontroll före lanseringen

Kör `python3 -B verktyg/lansering.py epostkontroll --verksamhet VERKSAMHET.json
--avsandardoman kundens-avsandningsdoman --dkim-selektor leverantorens-selektor
--mandat POST-ID --ut EPOST-DNS.json` och spara det nya kvittot i kundmappen (0600; befintlig fil vägras). Domänen avser formulärnotiser eller kvitton,
inte automatiskt webbdomänen. Verktyget läser TXT via den fasta resolvern
`https://cloudflare-dns.com/dns-query`: SPF på domänen, DKIM under leverantörens selektor
och `_dmarc`. Det skriver inget hos DNS- eller e-postleverantören. Fiktiv eller okänd verksamhet
ger okänt före nätåtkomst. Uppslagsfel ger alltid »kunde inte kontrolleras« och aldrig klart.

Saknas både SPF och DKIM blir det fynd; saknad DMARC blir anmärkning. Flera SPF-poster är
ett fynd. Kontrollen avser förekomst av publicerade poster, inte fullständig syntaxvalidering,
faktisk signering, alignment eller leverans till inkorgen. Kontrollera också leverantörens
egna verifieringsbesked. Gmail kräver minst SPF eller DKIM av alla avsändare och SPF, DKIM
och DMARC vid fler än 5 000 meddelanden per dygn till personliga Gmail-konton; Google
rekommenderar alla tre även för övriga. Volymkravet bedöms för kundens faktiska utskick.

### Arkiv av den gamla sajten

Före omdirigeringar och DNS-omläggning: kör `node verktyg/webblasare/arkivera.mjs
--adress https://gamla-domänen --kund KUNDMAPP --intervju INTERVJU.json --ut NY-ARKIVKATALOG`.
Utdata måste vara en ny katalog i kundmappen utanför Digitalas repo. Verktyget förenar sitemapens
adresser med intervjuns `migrering_adresser` (MIG1) och sparar HTML, inbäddad HAR och
helsidesskärmbild per hämtad sida. `MANIFEST.json` anger varje adress, ursprung, status, fel,
filstorlek och SHA-256; misslyckade adresser försvinner aldrig tyst. Läs alla fel och spara
eventuellt kompletterande material innan den gamla sajten försvinner.

Arkivet är privat kundmaterial, inklusive HAR och bilder. Bara samma ursprung, GET/HEAD och
färska webbläsarkontexter tillåts; externa resurser och WebSockets blockeras och redovisas.
Gränserna är 500 sidor och 20 sitemapfiler med ett indexled; överskridna gränser redovisas som
ofullständighet. Arkivet ger inget lanseringsmandat och ingen garanti att allt innehåll har
hittats. Inget WARC-verktyg eller nytt beroende ingår. Se `webblasare.md` för begränsningar.

Källor, lästa 2026-09-30: [Gmail Email sender guidelines](https://support.google.com/a/answer/81126?hl=en),
[Cloudflare DNS JSON](https://developers.cloudflare.com/1.1.1.1/encryption/dns-over-https/make-api-requests/dns-json/),
[Playwright Browser.newContext, recordHar](https://playwright.dev/docs/api/class-browser#browser-new-context).
Omfattning och prov: OVL-20260930-dbbdd8-digitala M1–M2.

## Lanseringsdagen

1. Driftsätt lanseringskonfigurationen; startsidan svarar 200 med rätt innehåll.
2. `lansering.py kontrollera --adress https://<domän>/ --omdirigeringar REDIRECTS.json --ut KONTROLL.json`:
   noindex borta (meta och X-Robots-Tag), verifieringstaggen synlig, sitemap 200,
   robots tillåter, kanonisk variant. Samma `gamla`-lista med `fran` och `till` som
   SEO-kontrollens offlineprov prövas nu live med GET: första svaret ska vara
   301/308 och högst fem hopp ska landa på exakt målet med 200. Status, slutadress,
   hopp och fynd per gammal adress finns i kvittot (OVL-20260930-b17920-digitala).
   Spara också bokningens, betalningens och formulärets verkliga slutadresser som
   `forvantad_slutadress` i DRIFT.json; driftverktyget skriver dem inte åt dig.
3. Sökkonsol: `sokkonsol.py verifiera --live`, sedan `inspektera --live` för start och de viktigaste sidorna
   (extern åtkomst krävs, sokkonsol.md).
4. Bing Webmaster Tools: importera egenskapen (människa). IndexNow om värden stöder det (valfritt).
5. Mätning: konverteringshändelser syns i felsökningsläget på produktionsdomänen.

## Oåterkalleligt

Första indexeringen av fel innehåll; ägarskap i sökkonsolen; omdirigeringar som ändrat inkommande länkars mål;
e-post som skickats till verkliga mottagare. Därför: noindex-kontrollen före sökkonsolen, och testdata bara i
förhandsvisning.

## Återgång

Peka produktionsdomänen till föregående driftsättning; återställ noindex om innehållet inte får indexeras; not i
`ARBETSLOGG.md` med tid, orsak och vem som beslutade; ny prelaunch-runda före nytt försök.

## Efter lansering

Veckorna 1–2: sökkonsolens indexeringsrapport var 2–3 dag; driftkontrollen (drift.md) igång; månadsrutinen
(uppfoljning.md). Lanseringen redovisas i slutrapporten med tid, revision, driftsättning och kontrollkvittot.
