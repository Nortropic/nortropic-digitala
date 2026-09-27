# Bedömningskontrakt v2 — 2026-09-27

Version: `digitala-kvalitet/2`. Beslutet ändrar framtida bedömningar, aldrig tidigare krav, acceptanser eller prov.
Frys kriteriernas innehåll och hash före kandidatbedömningen. Knyt varje ny dom till kriterieversion, kandidat
(commit eller innehållshash), faktiskt öppnade bilder, miljö, konfiguration och bedömningens räckvidd.

## Auktoritet och metod

Kundens styrkta behov, sakuppgifter och ägarens mandat är överordnade den internt skrivna briefen. Briefen är en
spårbar syntes, inte bevis för att behov som den tappat saknas. Märk kundkrav, sakregler och interna designhypoteser
var för sig. Om en intern hypotes ger ett svagt resultat ska den kunna omprövas med skäl och konsekvenskontroll;
bevara tidigare version och länka ändringen till behovet. Att följa en svag brief är inget kvalitetsgodkännande.
Briefmallens §5 gäller sök och kanaler; §7 gäller designriktning. Historiska briefers numrering ändras inte.

Enaxelprov är en valbar experimentmetod när en isolerad fråga behöver besvaras. Öppen konceptutveckling får ändra
bildstrategi, struktur, typografi, färg och rytm tillsammans när behoven motiverar det. Redovisa vad som ändras,
vad som hålls fast och varför. Varken antal alternativ eller en viss palett är ett generellt kvalitetskrav.

## Professionell miniminivå och smak

Smak är en preferens mellan professionellt fungerande alternativ. Professionell otillräcklighet är blockerande
även när länkar, axe, prestanda och formulär fungerar. Bedöm helheten och relevanta sidor/lägen, inte bara en hero.
Gör ingen stilpoäng till facit. Följande frågor kompletterar KVALITET.md:

- Bildhantverk: har bilderna relevant innehåll, trovärdig proveniens och avsiktlig beskärning, storlek och placering?
  Generiska ersättningsbilder, oavsiktlig repetition eller tomma bildytor som försvagar tjänstens förklaring kan
  blockera. Illustration och fotografi bedöms efter uppgiften; ingen bildtyp är obligatorisk. Demo märks tydligt.
- Komposition: samverkar typografi, hierarki, rytm och luft? Är variationen meningsfull och håller systemet på mobil?
  En utbytbar sektionsmall som döljer innehållets skillnader är en möjlig yrkesbrist, inte automatiskt smak.
- Innehåll: blir faktiska tjänster, priser, skillnader och nästa steg begripliga i rätt ordning? Är status-, test-
  och fiktionsinformation sann, lätt att hitta och proportionerlig så att besökarens uppgift fortfarande går fram?
- Sammanhang: håller huvud- och undersidor, formulär, fel-, tom- och laddningslägen samt redaktörsvyer ihop där de
  ingår? Bedöm både mobil och dator och skilj en statisk komps potential från en prövad produkt.

Ett blockerande fynd anger kriterium, exakt bild/del eller kod-/textställe, den observerade bristen, konsekvens för
besökaren eller verksamheten och en prövbar rättning. En motiverad preferens utan sådan brist är en förbättring.
Saknade nödvändiga bilder eller referenser ger `ej bedömbart` och hindrar ett helt kvalitetsgodkännande; det är
inte samma sak som att den osedda produkten är underkänd. Begränsade delar kan fortfarande bedömas uttryckligen.

## Faktisk jämförelse

Vid ny formgivning och kvalitetsomarbetning ingår professionell referensjämförelse även om den äldre briefen
utelämnade den. Välj relevanta referenser utifrån uppgiften; inget fast antal eller ensam stilförebild gäller.
Öppna aktuella renderade bilder och ange källa, tid, vy och vilket konkret drag som jämförs. En länklista, HTML
eller laddat filnamn är inte en sedd bild. Skriv kandidatens lösning, referensens lösning, skillnaden, och vad som
behålls/ändras med skäl. Referenser är jämförelser, inte licens att kopiera eller ändra kundfakta.

## Dom och underlag

Skilj tekniskt prövat, professionellt bedömt och ej observerat hos verkliga användare. Ange läst, öppnat och ej
prövat var för sig. Samma modellfamilj ger separat läsning, inte oberoende modellfamiljsbevis. En godkänd privat
kandidat innebär inte verifierad drift, ägaracceptans eller nya externa befogenheter. En annan kandidat behöver
ny bindning och omprov av påverkade delar; återbruk motiveras med konkret oförändrad omfattning och giltighet.

## Körbart bild- och domskontrakt

Före kritik skapas kundmappens `BEDOMNINGSUNDERLAG.json` enligt `kunskap/bildbedomning.md`. Där fryses
sid-/läges-/vytäckning, räckvidd, kandidat, miljö, konfiguration och denna fils fulla SHA256. Kriteriehashen binds
före bedömningen; `steg/PINNAR.sha256` anger professionens beslutade version och LADDNING.json binder den laddade.
`ladda_steg.py` vägrar saknat obligatoriskt manifest/bild och kopierar bilderna med deras hashar. `kor_profil.py`
väljer dessa kopior, kontrollerar kandidat och kriteriehash, och binder modellen till en exakt bedömningspost.
Efteråt krävs både semantisk approved-dom och Runtimes kvitto på obligatoriska bilder: Claude öppnade med Read
enligt bevarat spår; Codex fick dem bifogade enligt argv. Bifogat betyder inte självständigt verifierad mänsklig
bildläsning. `ej_bedombart` hålls isär från `rejected`; `svar_giltigt` är endast format. Kvalitetsbilden räknar
inte en dom med fel bindning, saknad jämförelse eller otillräckligt bildunderlag som godkänd leveransbedömning.

### Exekverbar kedja och räckvidd

För kvalificerad kvalitetsdom används `ladda_steg` → `kor_profil` → `kvalitetsbild`. Ett direkt Runtime-svar
har formstatus och blir inte på egen hand produktgodkännande. Domlogiken binds med `steg/DOMKOD.sha256`;
ändrad logik kräver ny beslutad pinning och nytt omprov. Bindningen omfattar även separat fördefinierade bildkrav.

Produktens fasta täckning ligger i BEVISKRAV.json:s `bildbedomning`, fastställd före kandidatbedömningen, och
omfattar start, undersidor, språk, handlingsresa, fel, tomt läge, laddning, redaktör samt mobil och dator.
Sakligt icke tillämpliga kategorier kräver fastställt skäl där; manifestet får inte lägga till undantag eller
krympa listan. Kompar har egen uppdragstyp och får inget funktionsgodkännande från statiska bilder.
DAGENS/ är en separat bildroll för faktisk jämförelse med föregående kandidat. BEVISKRAV fastställer vilka
föregående vyer som ska jämföras eller ett sakligt N/A när föregångare saknas. Manifestet kopierar beslutet
oförändrat. Båda dommallarna kräver separata dagensjamforelser som binds till DAGENS-bildernas proveniens och
täcker de fastställda vyerna. Saknat underlag eller jämförelse hindrar approved.

Rapporten återbinder manifest och bilder till LADDNING, modellen till Runtime-kvittots bildhashar och det
faktiska svaret till kvittots output-hash. KVITTO.sha256 krävs och dess värde bokförs i KORNING vid utfallet.
Det är filintegritet och spårbarhet, ingen kryptografiskt oberoende attest mot en aktör som kan skriva om hela kedjan.
Read-spår och argv-bilagor redovisas var för sig. Underkännande och ej bedömbart visas som genomförda domar med
sina fynd/begränsningar även när de inte får användas som godkänt leveransbevis. Femsekunderstestet är ett
avskärmat begriplighetsprov, aldrig en professionell kvalitetsdom.

LADDNING.json och dess arbetsyta är arkivmaterial för beviskedjan, inte tillfälliga byggfiler. Bevara hela
laddningen på den bokförda platsen; den får inte städas bort efter en körning. Utan oförändrad laddning kan
domen inte återbindas och räknas inte som aktuellt leveransbevis.
