# Standardvägar för integrationer

Version 1, sakuppgifter kontrollerade 2026-09-28. Komplement till `integrationer.md`.
Läs vid research/brief när ett behov finns, vid bygge för vald koppling och vid
prelaunch/leverans/drift för dess faktiska prov. Detta är ingen obligatorisk
produktstack och ersätter inte kundens befintliga verktyg.

Behov och källställe avgör lösningen: en ensam konsults bokningslänk, en skolas
resursschema och en gruppkurs med betalning är olika uppdrag. Välj lägsta nivå
som uppfyller behovet. En historisk kundregel om 15 minuters gemensam reservation
är inte en standardregel för nästa kund. För sammanhängande bokning/betalning
prövas i första hand bokningstjänstens egen betalningskoppling. En separat
Payment Link låser ingen kalenderplats.

## Daterade val, inte produktlöften

| Behov | Första kandidat | Varför / viktig gräns |
|---|---|---|
| En persons bokningar | Cal.coms egen bokningsvy | Gratis individplan har obegränsade möten, eventtyper och kalendrar. Fler personers gemensamma tillgänglighet och borttagen branding kräver rätt plan. |
| Kund har redan TidyCal | Behåll tjänsten om villkoren passar | Gratis vy är inte gratis API. API kräver betald plan och egna webhooks saknas. Kommersiella villkor behöver klarläggas, se nedan. |
| Personal/resurser, kund har SimplyBook.me | Befintlig widget och tjänstens hantering | Räkna både bokningar, personal och valda extrafunktioner. En gratis funktionsplats räcker inte automatiskt till alla kombinationer. |
| Fristående engångsbetalning | Stripe Payment Link | Leverantören håller kassan. Checkout API först när egen referens/dynamik faktiskt behövs. Ingen egen hantering av kortuppgifter. |
| Kontaktformulär | Befintlig formtjänst eller Tally | Form → ansvarig mottagning → uppföljning. Egen UI kan använda den lilla mottagningsadaptern bakom kundens befintliga host. |
| Transaktionsnotis | Befintlig e-posttjänst, Resend som prövbar kandidat | API-acceptans, leveranshändelse och läsning av en människa hålls isär. Testmottagare betyder syntetisk leverans. |

Cal:s [prislista](https://cal.com/pricing) och [FAQ](https://cal.com/faq) stödjer
individvägen; Teams anges till 12 USD/användare/mån vid årsbetalning. Hosted
kommersiell tjänst skiljs från AGPL/kommersiella källlicenser vid egen drift.
Att källkod finns innebär inte kostnadsfri hostning, kalenderkoppling eller drift.

TidyCals [FAQ](https://help.tidycal.com/article/739-faq) anger Free 0 USD,
Individual Lifetime 29 USD, Agency Lifetime 79 USD och Pro 12 USD/mån eller
99 USD/år. Free har en kalender; Individual tio. Pro tar bort branding;
Free/Lifetime har 1 procent TidyCal-avgift på Stripe-bokningar utöver Stripe.
Samtidigt kräver [ToS §6.b.i](https://tidycal.com/tos) skriftligt tillstånd för
kommersiell användning, trots tjänstens marknadsföring av betalda bokningar.
Det är en konkret olöst villkorskonflikt. Presentera inte TidyCal som generellt
godkänd gratis företagsstandard innan leverantören klarlagt tillämpningen.

SimplyBooks [prislista](https://simplybook.me/pricing) anger Free: 50 bokningar/mån,
en premiumfunktion och en utförare; månadsförnyelse krävs. Basic: 13,90 USD/mån
eller 11,90 USD/mån årsbetalt, 100 bokningar, tre funktioner, fem utförare.
Premiums borttagna sidfotsbranding är inte en Free-egenskap. 14-dagars provperiod
är inte ett permanent gratisvillkor. API-funktionen måste kvalificeras ihop med
övriga valda funktioner på det verkliga kontot.

Stripe [svenska standardpriser](https://stripe.com/se/pricing) har ingen fast
månadsavgift för standardbetalningar; standardkort från EES anges till
1,5 procent + 1,80 SEK, premiumkort 2,8 procent + 1,80 SEK. Andra kort, växling,
tvister och tillägg har andra avgifter. Betalning är alltså inte gratis även när
en Payment Link saknar abonnemangskostnad. Kontrollera land, valuta, skattekonfiguration
och aktuellt pris vid varje kundval.

Tallys [planer](https://tally.so/help/plans-and-pricing) erbjuder gratis formulär
inom fair use; Pro 29 USD/mån tar bort branding, Business 89 USD/mån ger bl.a.
retentionsstyrning. [API](https://tally.so/help/api) och
[webhooks](https://tally.so/help/webhooks) är tillgängliga även gratis.
Resends [aktuella plan](https://resend.com/pricing) har 3 000 mejl/mån, 100/dag,
tre domäner och en webhook på Free. Pro börjar vid 20 USD/mån. Lås inte framtida
val till dessa kvoter; läs om den valda planen före kundaktivering.

## Körbar väg

`python3 -B verktyg/integrationer.py --help` ger de ordinarie kommandona.
`exempel/integrationer/README.md` innehåller exakta lokala kommandon och
kontrakt. Verktyget kan bereda leverantörslänkar, köra Resend-test till syntetisk
mottagare, skapa/återläsa Stripe Checkout i testläge, återläsa Cal-bokning och
exportera mottagna förfrågningar till CSV för kundens befintliga CRM.

`integrationer_mottagning.py` verifierar signerade Stripe-, Cal- och Tally-event,
validerar förfrågningar och sparar mottagningen atomärt med deduplicering.
Händelser skrivs som observationer: ett sent webhookevent får inte förvandlas
till ett påstått aktuellt boknings- eller betalningsläge. Cal-version och eventtyp,
Tally-form och fältmappning, Stripe-version/testläge/referensrymd binds uttryckligen.
Ingen gruppkapacitet räknas fram ur Cal:s attendees-lista.

Resend-exemplet kan bara skicka fasta syntetiska uppgifter till `resend.dev`.
Stripe-exemplet vägrar live-nycklar och läser först ett befintligt aktivt testpris.
Den privata journalen lagrar avsikt före nätanropet. Efter okänt utfall krävs
explicit retry med samma nyckel och kropp inom 23 timmar; därefter krävs faktisk
avstämning. Ingen ny idempotensnyckel skapas automatiskt för att kringgå ett fel.
Lyckad retursida betyder inte betalt, och `complete` kan fortfarande vara `unpaid`.

## Befintliga kanaler, CRM och redigering

`integrationer.py kanal` anropar befintliga verktyg direkt och behåller deras
fiktivspärrar, åtkomstkrav och kvitton:

| Kanal | Återanvänd verktyg | Gräns |
|---|---|---|
| SEO | `seo_kontroll.py` | Förhandsvisning/noindex och lansering bedöms olika. |
| GSC | `sokkonsol.py` | Plan, verifiering, sitemap, URL-inspektion och sökdata; live kräver faktisk domän/åtkomst. |
| GBP | `lokal_synlighet.py` | Underlag och behörighetsbedömning; inte påstådd API-publicering. |
| Google/Meta | `annonsberedning.py` + `annonsadapter.py` | Befintlig PAUSED-överföring/återläsning, rätt konto/mandat; ingen aktivering eller spendering här. |
| Mätning | `uppfoljning.py` | Händelseplan/samtycke/observerad mottagning, inte bara installerad kod. |

CRM-exporten innehåller käll-id, motiverade kontaktfält, ansvarig och uppföljning.
Importera till kundens befintliga system enligt dess kontrakt, återläs samma id
och prova en faktisk uppföljningshandling innan CRM-ledet kallas levererat.
CSV skapad är inte CRM mottaget. Ingen ny generell CRM-produkt ingår här.

För CMS används kundens befintliga plattform eller den redan valda redaktörsvägen.
Koppla ett faktiskt innehållsobjekt till rätt roll: ändra, förhandsvisa separat,
publicera och återställ. Bevara publicerat innehåll vid fel/409 och osparade
ändringar. Leverantörens API finns är inte ett prov av redaktörens uppgift.
Om kontot saknas kan en tillämpad adapter/kontraktsväg visas, men ingen hostad
redaktörsfunktion tillskrivs den. Bygg inget nytt CMS för att fylla en provtabell.

## Bevis, drift och ansvar

Redovisa per valt led: **dokumenterat**, **lokalt kontraktsprovat**,
**leverantörens sandbox/testrecipient faktiskt prövad**, eller **faktisk kundintegration**.
Nivåerna summeras inte till ett helhetsgodkännande. Bind källa/kandidat,
API-/webhookversion, miljö, kontoetikett, konfiguration, handling, resultat och
råbevis utan hemligheter. Bevara avvisat försök och senare rättning var för sig.

Kundfunktioner körs hos leverantören eller kundens host. Loopbackservern är ett
körbart kontraktsexempel, inte JohnnyMac som produktionsserver. SQLite-exemplet
behöver beständig disk; flyktig serverless-disk duger inte. Anslut till värdens
befintliga beständiga lagring när den saknar sådan disk och återprova atomaritet,
replay, förlorat svar och återgång. Inga e-post-/webhookarbeten får vara beroende
av en pågående agent- eller byggsession.

Begränsa data till uppgiften. Konfigurera gallring, åtkomst, rättelse/export och
personuppgiftsansvar före riktig drift. Tally lagrar formdata i Europa enligt
sin policy; Resends DPA anger huvudsaklig behandling i USA. Välj inte geografisk
eller juridisk lämplighet enbart från ett marknadsfört GDPR-märke. Det nya
underlaget ersätter inte `juridikflaggor.md` eller kundens dokumenterade beslut.
