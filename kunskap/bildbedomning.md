# Bildunderlag och kvalitetsdom v2

Kundmappens `BEDOMNINGSUNDERLAG.json` är obligatoriskt i kritiksteget. Bilderna ska ligga i kundmappen;
relativa sökvägar får inte lämna den. Detta är ett uppgiftsunderlag, aldrig offentlig kundinformation i Digitala.
Frys före kritik. Kör först `ladda_steg.py --steg kritik …`, därefter vanlig `kor_profil.py kritik` med laddningen.
Bildfiler kopieras av laddaren och följer automatiskt med kvalificerad kritik. `--filer` kan innehålla kompletterande
text-/mätbevis; de får inte ersätta de obligatoriska bilderna. Femsekunderstestet får bara sina avskärmade bilder,
inte manifestet, briefen, kriterierna eller kandidatidentiteten.

Manifestet innehåller:

- `schema: "digitala-bildbedomning/2"`, `kriterieversion: "digitala-kvalitet/2"` och `kriterier_sha256`: SHA256 av
  beslutad `kritik/BEDOMNING-v2.md`. `steg/PINNAR.sha256` och LADDNING.json bevarar versionen som faktiskt används.
- `rackvidd`: vad domen avser, exempelvis en namngiven komp eller en privat produkt, och vad den inte kan avgöra.
- `sammanhang`: `kandidat`, `miljo`, `konfiguration` enligt `bevis-och-fortsattning.md`. Kandidaten är ren gitcommit
  med träd eller en uttrycklig lista av filer med hashar. Miljön har namn/typ; konfigurationen är hashbundna filer
  eller uttryckligt sakskäl för N/A. Körkonfiguration utan redovisad bindning räcker inte.
- `tackning`: lista `{id, beskrivning, na_skal?}` bestämd före bilderna bedöms. En produkt omfattar startsida,
  faktiska tjänste-/undersidor, relevanta språk, kontakt-/handlingsresa, fel/tom/laddning och redaktörsvyer där
  sådana finns, på mobil och dator. En komp anger vad den faktiskt visar; icke byggt beteende förblir ej bedömt.
  N/A kräver sakskäl per rad. Saknad tid, bild eller åtkomst är inte N/A.
- `bilder`: både kandidat och professionella referenser. Varje post har `fil` (relativ kundmappen), `sha256`,
  `plats` (exempel `VYER/kontakt-390.png` eller `REFERENSER/typografi-1440.png`), `roll: kandidat|referens|dagens`,
  `kalla` (ursprung), `tid` (fångsttid), `vy` (mått), `drag` (varför bilden behövs). Kandidatbilder har `tacker`:
  listan över täcknings-id som de faktiskt visar. Referensbilder återger faktisk rendering, inte en URL-lista.

Laddaren kontrollerar filgräns, hash, bildformat och täckning. Profilen kontrollerar att manifestets kriteriehash
är samma som den laddade och skickar en maskinskriven `UNDERLAG/BEDOMNINGSBINDNING.json`. Bedömaren kopierar dess
fält till svaret, anger faktiskt sedda bilder och jämför med minst en relevant öppnad referens. Det är ett minsta
belägg för jämförelse, inte ett fast antal koncept eller ett universellt stilideal.

Schemat tillåter tom jämförelselista för `rejected`/`ej_bedombart`, så att saknade referenser aldrig måste hittas
på. Den semantiska konsumenten vägrar `approved` utan faktisk jämförelse, korrekt proveniens, tomma blockerande
fynd och komplett Runtime-bildkvitto. `svar_giltigt` betyder endast att JSON-schemat följts. Heuristikens värden
är icke summerbara bedömningar; `okant` och `inte-tillampligt` förhindrar påhittade beteendepoäng från en statisk komp.

## Fördefinierade krav, föregående kandidat och integritet

Manifestet kräver dessutom `kravfil` (relativ kundmappen) och `krav_sha256`. Filen ska vara ett separat fryst
`digitala-beviskrav/1` med `version` och `bildbedomning: {typ: "produkt"|"komp", faststalld_av, faststalld_tid,
tackning: [...]}`. Täckningsraderna har `id`, `beskrivning`, `kategorier: [...]` och eventuellt fastställt
`na_skal`. För produkt ska kategorierna tillsammans omfatta `start`, `undersidor`, `sprak`, `handlingsresa`,
`fel`, `tom`, `laddning`, `redaktor`, `mobil`, `dator`. Manifestets `tackning` måste vara identisk med den frysta
listan; fria N/A avvisas. Fastställelsen är ett spårbart sakbeslut, inte ett verktygsbevis att någon verkligen
valt rätt scope. Varje enskild faktiskt förekommande sida/tillstånd ska fortfarande namnges.

Exempel: fallet ligger under kundmappen `omarbetning/fall/`, och manifestets kravfil är
`omarbetning/fall/BEVISKRAV.json`. Laddaren kopierar även den filen. Om referensjakten har sparat bilder utanför
kundmappen kopieras de med oförändrade bytes till en namngiven underkatalog i kundmappen före manifestfrysningen;
ursprung och hash bevaras. Ingen symlänk ut ur kundmappen används.

Tidigare kandidat får `roll: "dagens"`, `plats: "DAGENS/...png"`, samma hash och proveniens som övriga bilder.
Dessa bilder följer automatiskt med; de ersätter inte professionella referenser. Båda kritikmallarna får
`krav_sha256` och `domkod_sha256` i den maskinskrivna bedömningsbindningen. `pinna.py --skriv` skriver både
professionspinnar och domkodens separata hashlista som del av ett nytt beslut.

Kvalitetsbilden visar varje genomförd kritik inklusive rejected/ej_bedombart. Den verifierar aktuellt laddat
manifest, dess obligatoriska bildrader och kriterier, Runtime-kvittot mot sin obligatoriska integritetsrad och
värdet som bokförts vid körningstillfället, samt råsvar/ström/start mot Runtime-kvittots output-hashar.
Bildbeläggets metod visas: Claude Read-spår respektive Codex argv-bilagor. Bifogad bild betyder inte
självständigt verifierad bildläsning. Femsekunderstest räknas separat, inte som kritikens kvalitetsgodkännande.

## Förhandsbeslut för DAGENS och arkiv

Både `BEVISKRAV.json` under `bildbedomning.dagens` och manifestets `dagens` har samma objekt:

```json
{"tackning":[{"id":"dagens-mobil","beskrivning":"Föregående kandidats första vy på mobil"},
             {"id":"dagens-dator","beskrivning":"Föregående kandidats första vy på dator"}],"na_skal":""}
```

DAGENS-bildernas `tacker` hänvisar till dessa id. Båda dommallarna har `dagensjamforelser`, med
`kandidatbild`, `dagensbild`, `kalla`, `tid`, `vy`, `drag`, `observation`, `konsekvens`, `beslut_och_skal`.
Källa/tid/vy måste motsvara den hashbundna DAGENS-bilden. Alla fastställda DAGENS-id måste jämföras för approved;
en bild med rollen referens kan inte ersätta föregångaren. Om föregångare saknas fastställs i stället
`{"tackning":[],"na_skal":"Ingen föregående kandidat finns; första nybygget."}` före bedömningen.
Saknad bild eller åtkomst är inte skäl för N/A. Beslutet tillförs som en ny kravversion med historiken kvar;
produktens befintliga täckningsrader behöver inte ändras. Verktyget binder beslutet, granskningen bedömer dess saklighet.

Laddningsarbetsytan och LADDNING.json är arkivmaterial. Bevara dem på bokförd plats med oförändrade bytes
även efter körningen; de ska inte rensas som temporära filer. Kvalitetsbilden återläser dem och kräver även
att KORNING-postens profil motsvarar Runtime-kvittots `profile`.


## Exakta bildfält vid nya kritikstarter

Varje `kandidatbild`, `referensbild` och `dagensbild` är en enda exakt `bilder[].plats` med motsvarande roll.
Flera bildpar skrivs som separata jämförelseobjekt. Prosa hör till observationsfälten. `kalla`, `tid` och `vy`
kopieras ordagrant från samma referens-/DAGENS-post som bildfältet anger.

`kor_profil.py` begränsar den laddade schemamallen med rollbundna enums från det kontrollerade manifestet
innan schemafilen skickas till Runtime; schemats faktiska hash bokförs även i KORNING. Proveniensfälten får
rollens tillåtna värden. Dessa enums bevisar inte att tre värden kommer från samma bild: den oförändrade
semantiska domkontrollen verifierar det paret. Finns inga DAGENS-bilder tillåter schemat endast tom
`dagensjamforelser`, utan en påhittad enum. Avskärmade femsekundersprov ändras inte. En gammal fri-strängsdom
med sammansatta bildfält förblir ogiltigt bunden även om alla bilder faktiskt lästs och verdict är approved.


`seen_files` binds först när hela kritikpaketets filförteckning är byggd, inklusive den maskinskrivna
bedömningsbindningen. Tillåtna värden är exakt dessa paketplatser plus Runtime-profilens automatiska
`FILES.md` och `AGENTS.md`. Ange bara faktiskt lästa filer. Parenteser, radintervall och olästa filer hör
inte i listan; beskriv läsomfång i saktext. Enum kontrollerar endast platsformat/tillhörighet, aldrig om
läsning skett. Den oförändrade konsumenten kräver fortsatt exakt listning och Runtime-belagd bildläsning.
