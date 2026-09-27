# Lärdomar över fall (P4) — Digitala

Privat fil i `evidence/digitala/local/kunskap/`. Läses vid uppstart av nästa fall. En post per lärdom med fälten
**observation** (vad hände, fall, bevispekare) · **möjlig generell lärdom** (formulerad som hypotes) · **lokal
preferens?** · **tillämpning** (fall och vad som gjordes) · **kvarvarande osäkerhet** · **läge**. Lägen: *observerad en
gång (fall)* · *återfunnen i ett andra fall (fall)* · *använd med konkret resultat (fall: vad)*. Två fall bekräftar inte
en generell regel eller ett orsakssamband, och det skrivs inte så. Inga statusord som OBSERVERAD/BEKRÄFTAD.

**Avstämning** efter två *relevanta* tillämpningar (inte efter två fall i kalendern), per post och per underlag i
`REGISTER.md`, med fyra utfall: *inte tillämpligt på de prövade uppgifterna* · *inte använt trots att det var relevant* ·
*använt utan tydligt ytterligare värde* · *använt med observerad nytta eller nackdel*. Kvalitet, konkret felupptäckt,
omarbete, kostnad och ägarbörda bedöms tillsammans; "förhindrade fel" räknas inte utan belägg för vad som faktiskt
hände. Ett underlag som inte ändrade kod kan ha gjort en relevant kontroll; inga fynd kan betyda en bra kandidat.
**Avslut** betyder att framtida laddning eller tillämpning stängs av (raden märks i registret); källversioner,
utvärderingar och historik bevaras; ingen mapp raderas och ingen leverans återställs blint.

Lokala preferenser skrivs inte in som lärdomar. Norrgläntas lokala preferenser (Familjen Grotesk, solgult, ledgern,
etiketten "Skicka förfrågan") står i dess brief.

---

## L1 — Ägarens ord sparas ordagrant först
- **Observation**: i Norrglänta och preciseringen sparades varje inklistrat besked som fil innan något annat gjordes;
  efter en kontextkomprimering kunde transkriptet inte läsas om (`owner-words-*.md` i `evidence/digitala/local/`).
- **Möjlig generell lärdom**: ett besked som inte sparas direkt kan inte registreras avsnitt för avsnitt senare.
- **Lokal preferens?** Nej. **Tillämpning**: Norrglänta (alla besked), preciseringen, genomförandet.
- **Kvarvarande osäkerhet**: ingen känd. **Läge**: använd med konkret resultat (Digitala 2026-09-25–26: varje besked
  registrerat mot filen).

## L2 — Briefen kan vara internt motsägelsefull; ACCEPT avgör
- **Observation**: Norrgläntas brief sade "ingår" i §1 och FAQ men "tillval" i §5 för rabattskötsel; kedjan var bruten
  tills ACCEPT §1 avgjorde (`norrglanta/RIKTAD-KONTROLL-RESULTAT-20260926.md`, område 1).
- **Möjlig generell lärdom**: kedjekontrollen (`redaktionellt-pass.md` del 2) bör köras på briefen före bygget, inte
  bara på sajten efter.
- **Lokal preferens?** Nej. **Tillämpning**: Norrglänta (rättning `0f8322a`; rättelseanteckning i briefen är ägarens
  öppna förslag).
- **Kvarvarande osäkerhet**: om kontrollen på brief-nivå fångar sådant i ett fall med fler tjänster. **Läge**: observerad
  en gång (Norrglänta).

## L3 — En klockmätning får bara använda en klocka
- **Observation**: tidsfällan jämförde en klientstämpel med serverns tid; klockskillnad tappade förfrågningar tyst.
  Regeln fanns i webbgrundens security-checklist rad 75 och i briefen §3, men inget steg läste koden mot den (område 2).
- **Möjlig generell lärdom**: en regel hjälper bara om ett steg läser koden mot den (→ `formularsakerhet.md`,
  kodläsningsfrågorna i granskning D).
- **Lokal preferens?** Nej. **Tillämpning**: Norrglänta (`0f8322a`, `tidsfalla.mjs` med klockförskjutning).
- **Kvarvarande osäkerhet**: om granskning D faktiskt ställer frågan i nästa fall. **Läge**: observerad en gång.

## L4 — Referensbudgeten måste definieras som frågor
- **Observation**: 21 laddningar mot högst 10; budgeten räknade hämtningar, inte svar (`PROJECT-BRIEF.md` §5).
- **Möjlig generell lärdom**: "en fråga per laddning" (→ `referensjakt.md` regel 1).
- **Lokal preferens?** Nej. **Tillämpning**: Norrglänta (överskridandet redovisat). **Kvarvarande osäkerhet**: om
  frågeformen håller budgeten. **Läge**: observerad en gång.

## L5 — Bildlicens ska vara fastställd före bygget
- **Observation**: tre licensosäkra bilder byttes ut före leverans (`content/images.ts`, `bilder/original/`).
- **Möjlig generell lärdom**: bildposten (motiv, påstående, källa, licens) skrivs innan bilden används i en layout.
- **Lokal preferens?** Nej. **Tillämpning**: Norrglänta. **Kvarvarande osäkerhet**: ingen känd. **Läge**: observerad en
  gång.

## L6 — Granskaren läser reservadresser fel utan nätverkslista
- **Observation**: en läsare tog `src`-reservadressen `w=3840` för laddad bild; nätverkslistan visade annat (granskning
  r1–r3, Lighthouse).
- **Möjlig generell lärdom**: ge granskaren nätverkslistan när bilder bedöms.
- **Lokal preferens?** Nej. **Tillämpning**: Norrglänta (redovisat). **Kvarvarande osäkerhet**: om nätverkslistan räcker
  när bilder laddas lat eller via CSS. **Läge**: observerad en gång.

## L7 — Kodläsning och renderingsläsning hittar olika fel
- **Observation**: tre renderingsläsningar godkände; en kodläsning fann tre bekräftade fel; proven fann sex fel som
  regler inte nämner (jämförelsen §4.3).
- **Möjlig generell lärdom**: observationssättet avgör, inte regellistan (→ P5 A–D).
- **Lokal preferens?** Nej. **Tillämpning**: Norrglänta; preciseringens P5. **Läge**: observerad en gång.

## L8 — Ett redaktionellt pass är ett eget steg
- **Observation**: löftet sju gånger på startsidan och plannerspråk i FAQ passerade faktakontroll och tre
  granskningsrundor (område 5).
- **Möjlig generell lärdom**: faktatrohet och redaktionell kvalitet är två kontroller (→ `redaktionellt-pass.md`).
- **Lokal preferens?** Nej. **Tillämpning**: Norrglänta (passet gjort, 7 → 2). **Kvarvarande osäkerhet**: hur mycket
  som kräver läsning mot räkning på en annan sajt. **Läge**: observerad en gång.

## L9 — Proven binder commit och driftsättning
- **Observation**: varje mätmapp bär commit och driftsättnings-id; en rörlig adress kunde annars peka på en annan version
  (`matning-20260926/*/adress-commit-driftsattning.txt`).
- **Möjlig generell lärdom**: prov utan bindning bevisar inget om en version.
- **Lokal preferens?** Nej. **Tillämpning**: Norrglänta; genomförandets del 3 (oföränderlig driftsättningsadress).
  **Kvarvarande osäkerhet**: ingen känd. **Läge**: använd med konkret resultat (Norrglänta: reproduktionen på `2a84fd3` skilde version från alias).

## L10 — Ett förslag som ändrar godkänt innehåll ligger i egen commit
- **Observation**: Säsongsplanens formulering (`f60bf26`) och H1-alternativet (bara visat) hölls isär från rättningarna.
- **Möjlig generell lärdom**: en B-fråga får ett eget förslag, aldrig en tyst ändring av A.
- **Lokal preferens?** Nej. **Tillämpning**: Norrglänta. **Kvarvarande osäkerhet**: om regeln håller när ett förslag
  och en rättning berör samma rad. **Läge**: observerad en gång.

## L11 — Det jag skriver som givet är ofta ett förslag
- **Observation**: i preciseringens dokument stod "samma startare" och "spärrarna gäller" som fakta; granskningen visade
  att båda var oprövade förslag (review-digitala-precisering-dokument-r1, I1–I2). Kontorsposten kallade leveransen fel
  version (resultat-r1, B1).
- **Möjlig generell lärdom**: märk förslag som förslag; skriv spärrar som något som byggs och prövas; läs den egna
  redovisningen mot filen innan den publiceras.
- **Lokal preferens?** Nej. **Tillämpning**: preciseringen (rättat före publicering). **Läge**: observerad en gång.

## L12 — Läsväggen granskar också Bash-kommandots sökvägar
- **Observation**: i genomförandets spärrprov B nekades varje anrop av provskriptet i fyra försök trots rätt regler
  och en vakt som svarade allow; CLI-binärens text visade att `blockReadsOutsideWorkingDirectories` gäller även sökvägar
  som ett Bash-kommando namnger, och provskriptet låg utanför arbetsytan (`genomforande-20260926/sparrprov-b-*`).
- **Möjlig generell lärdom**: en ny verktygsprofil måste prövas som sådan; en spärr som inte kan hävas av regler ska
  hittas i verktygets egna texter, inte gissas fram med fler modellsessioner.
- **Lokal preferens?** Nej. **Tillämpning**: genomförandet (inställningen utelämnad; vakten bär läsväggen).
- **Kvarvarande osäkerhet**: om Read utanför arbetsytan nekas även utan vakten i dontAsk-läget. **Läge**: observerad en gång.

## L13 — En läsare utan kataloglistning behöver FILES.md i prompten
- **Observation**: bildbedömningen (C) öppnade ingen bild eftersom prompten inte sade "börja med FILES.md"; läsaren
  gissade filnamn och avstod (`genomforande-20260926/bild-c-ada775e`). Samma regel fanns redan som minnesanteckning
  från AP-11 men nådde inte prompten.
- **Möjlig generell lärdom**: varje läsarprompt börjar med "Börja med FILES.md"; en mall för läsarprompter i
  provvägen skulle ta bort felet.
- **Lokal preferens?** Nej. **Tillämpning**: genomförandet (sessionen förbrukad; omkörning kräver beslut).
- **Kvarvarande osäkerhet**: ingen känd. **Läge**: återfunnen i ett andra fall (AP-11 retry-3, Digitala C-session).

## L14 — En registrerad skill är tillgänglig, inte garanterat laddad
- **Observation**: mottagarprov etapp 1 (`genomforande-20260926/etapp1/mottagarprov-1`): en färsk byggsession med
  Read, Write och Skill fick en mobil-först-uppgift utan att skills nämndes. Den anropade `frontend-design` av sig
  själv, men varken `emil-design-eng` eller `mobile-native`, trots att båda var listade som tillgängliga och
  mobile-natives beskrivning täcker uppgiften.
- **Möjlig generell lärdom**: beskrivningsdriven laddning är selektiv; en bred skill som redan täcker uppgiften
  tränger undan smalare. När ett steg behöver Emils kunnande (rörelse, mobilkänsla) anropar kedjedrivaren skillen
  uttryckligen; registrets kopplingstabell säger när.
- **Lokal preferens?** Nej. **Tillämpning**: etapp 2:s komps och kritik; nästa fall.
- **Kvarvarande osäkerhet**: en enda körning; en uppgift som ligger närmare Emils domän kan ge annat utfall.
  **Läge**: ny.

## L15 — Pinna till revision och kopieväg, inte till ett paketnummer
- **Observation**: Impeccables npm-paket 4.1.0 (pinnat i mandatet) laddar skillpaketet från GitHub-releaser med
  sha256-sidecar; releasen för skill 4.4.0 finns inte, så installeraren gav HTTP 404 och installerade inget. Repot vid
  den pinnade revisionen (`9d715cc4`, samma som HEAD) bar hela skillen i `.claude/skills/impeccable/`, och README:s egen
  reservväg (kopiera ur repot) gav exakt den pinnade versionen.
- **Möjlig generell lärdom**: en pinning ska namnge git-revision och kopieväg (repo, sökväg, blob), inte bara ett
  paketnummer vars release-tillgång kan försvinna; ägarens påpekande "allt finns på GitHub" stämde.
- **Lokal preferens?** Nej. **Tillämpning**: registrets regel 4 och alla kommande pinningar.
- **Kvarvarande osäkerhet**: ingen känd. **Läge**: ny.

## L16 — Tre riktningar visade ett element, inte tre vägar (etapp 2)
- **Observation**: komparna A "Ljuset", B′ "Arbetet" och C "Planen" (`genomforande-20260926/etapp2/`) bedömdes av
  tre separata kritiker och en samlad. Två kritiker fällde domen "specifik för Norrglänta" på samma underliggande
  element — säsongsobjektet april–oktober — fast i var sin komp; björkmotivet i A betalade inte för sig; B′ prövade
  bara halva sin hypotes eftersom fria arbetsfoton som klarar demoreglerna inte finns; alla tre försämrade den
  Säsongsplan som redan ligger i produktion (namnlösa rader, sammanslagna valgrupper, horisontell linjal på mobil);
  stapeln nedanför vikningen överlevde alla tre axlarna.
- **Möjlig generell lärdom**: (1) konstanterna i ett konceptsteg måste omfatta det som redan fungerar i produktion,
  annars mäter provet försämringar i stället för riktningar; (2) en axel per komp räcker inte om sektionsföljd och
  komposition nedanför vikningen lämnas orörda — en fjärde axel "rytm" behövs; (3) modellfri mätning i
  skärmbildsskriptet (H1-rader, CTA i vyn) hittade fel ögat missade i tre versioner; (4) detektorns tal är ingen
  rangordning — låga tal kan bero på att kompen gör minst; (5) fotohypoteser kräver egna bilder.
- **Lokal preferens?** Delvis: bäraren (säsongsobjektet) är Norrgläntas; metodlärdomarna är generella.
  **Tillämpning**: nästa omgång komps ("Ljuset med Planen") och nästa fall.
- **Kvarvarande osäkerhet**: ägarens omdöme; rörelse och verklig läsbarhet är osedda. **Läge**: ny.


## L17 — Läs tabellhuvudet innan en kolumn tolkas; läs källmeningen brett innan en siffra "rättas"
- **Observation**: del f (Vercel Pro) underkändes två gånger. Runda 1: jag "rättade" preview-suffixets pris från 100 till
  10 USD därför att mitt `grep -o` med 60 teckens fönster hade klippt "$100" till "$10". Runda 2: hela plantabellens
  "… ingår"-kolumn (50 000 analyshändelser, 5 000 bildtransformationer, 1 miljon funktionsanrop, Blob, Global Config,
  spårenheter, hastighetsbegränsning) hade tolkats som Pros fria kvoter; tabellen har kolumnerna Hobby, Pro, Enterprise
  och kvoterna är Hobbys — Pro debiteras från första enheten mot månadskrediten. Två uppgifter stod dessutom som
  "okänt" fast de lästa sidorna bar dem (Observability Plus-priset, fri domän-villkoren), eftersom jag sökte i mina
  egna utdrag, inte i sidorna.
- **Möjlig generell lärdom**: (1) en prislista läses rad för rad med kolumnhuvudet framför ögonen, och varje uppgift
  skrivs med sin kolumn ("Hobby: ingår; Pro: från första enheten"); (2) ett grep-fönster är inte en källmening — läs
  hela meningen (eller sidan) innan en siffra ändras; (3) "okänt" får bara stå efter sökning i källsidorna, inte i
  egna sammandrag; (4) när en granskare pekar på en restrisk av typen "detta står i källan", är det ett tecken på ett
  systematiskt läsfel, inte ett enstaka — kontrollera hela tabellen, inte raden.
- **Lokal preferens?** Nej, generell. **Tillämpning**: varje fakta-tabell ur dokumentation (Vercel, npm-paket,
  licenser) i bevakningsrutinen och i kommande fall.
- **Kvarvarande osäkerhet**: om runda 3 godkänner version 3. **Läge**: ny.

## L18 — Pröva målklassen modellfritt innan en modellsession, och låt uppgiftstexten bära det exakta kommandot (etapp 3)
- **Observation**: alla spärrprov var körda mot lokala http-mål på loopback. Mot det verkliga https-målet föll hållaren
  direkt (ERR_PROXY_CONNECTION_FAILED): värdregeln `MAP * ~NOTFOUND` undantog bara sajtens värdnamn, och proxyns egen
  adress 127.0.0.1 blev oupplösbar när vitlistan inte längre var loopback. Ett modellfritt driftsättningsprov fångade det
  innan någon session förbrukats; rättningen var en rad. Första skyddade scenariot föll ändå som verktygsfel: uppgiften
  sade "adressen du fått" utan adress och instruktionsfilen skrev kommandot med ellips; provaren gissade sjutton
  sökvägar och gjorde noll handlingar. Spärrprov B hade fungerat just för att dess uppgiftstext bar hela sökvägen.
- **Möjlig generell lärdom**: (1) varje ny målklass (protokoll, värdtyp, skydd) får ett modellfritt prov genom hela
  riggen före första modellsessionen; (2) det provaren behöver för sitt första kommando — exakt sökväg, startadress,
  arbetskatalog — ska stå ordagrant i uppgiften, aldrig i en ellips eller "det du fått"; (3) en vakt som prövar
  processlistan får inte matcha sin egen kommandorad (en startkörning uteblev tyst av det skälet).
- **Lokal preferens?** Nej, generell. **Tillämpning**: driftsättningsprovet före varje ny leverans som provmål; en
  uppgiftsmall med rubrikerna Startadress och Kommando. **Kvarvarande osäkerhet**: ingen. **Läge**: ny.

## L19 — agent-browser 0.38.1: domänlistan är portblind, policyn verkar på odokumenterade åtgärdsnamn, inget eget spår
- **Observation**: fyra modellfria försök och en modellsession mot samma fällor som vår hållare. Domänlistan nekar ett
  annat värdnamn men släpper samma värdnamn på annan port (localhost:B nådde B); länk, popup och omdirigering mot ett
  främmande värdnamn blockeras på förfrågningsnivå men lämnar flikar öppna; policyn "default deny" kräver `launch` och
  verkar på åtgärdsnamn (`url`, `title`, `tab_list`, `getbytext`, `screenshot`, `close`) som dokumentationens
  kategoritabell inte nämner; socketvägen får vara högst 103 byte; inget skrevs under en isolerad HOME; ingen spårfil
  finns — handlingarna rekonstrueras ur sessionens ström och vaktloggen. Snapshot med referenser är en bättre observation
  än vår elementlista.
- **Möjlig generell lärdom**: ett standardverktygs "säkerhetsfunktioner" prövas mot våra egna fällor innan de räknas
  som gräns; dokumentation är hypotes tills beteendet är sett; ett verktyg kan tas in som observationslager bakom vår
  gräns utan att ersätta gränsen.
- **Lokal preferens?** Nej. **Tillämpning**: förslagsraden för nästa Digitala-fall (agent-browser bakom vår proxy som
  observation, jämfört mot agentlage på samma uppgift). **Kvarvarande osäkerhet**: senare versioner. **Läge**: ny.

## L20 — Tre roller i en provrunda: tester, kontrollant och granskare får inte vara samma läsning
- **Observation**: i etapp 3 bar provaren sin egen rapport (slutrapport), kontrollanten (kedjedrivaren) bedömde spår,
  skärmbild och sidtext mot uppgiften och skrev KONTROLL.md, och en separat granskare prövade hållarändringen. Två gånger
  skilde sig bilderna: provarens "häckklippning kan läggas till" var sant men utan tidsangivelse (produktiakttagelse, inte
  provfel), och kartläggningsarbetsflödets egen läsning av läget släpade efter körningarna men gav den granskning av
  hållarändringen som annars uteblivit.
- **Möjlig generell lärdom**: kontrollantens rad "observerat slutläge" fylls alltid ur artefakter (sista skärmbild,
  sidtext, spårets sista adress), aldrig ur rapporten; en förändring av gränsen mellan två körningar får en egen kort
  granskning även när regressionen är grön.
- **Lokal preferens?** Nej. **Tillämpning**: KONTROLL.md-mallen och rytmen "per fall". **Kvarvarande osäkerhet**: om
  mänskliga prov (J4) ändrar rollfördelningen. **Läge**: ny.

## L21 — Mät layoutvyns bredd; en skärmbild som bara blir bredare döljer felet
- **Observation** (etapp 4, 2026-09-27): när Säsongsplanens remsa fick fyra kolumner alltid kunde `1fr`-kolumnerna inte
  krympa under rubrikordens bredd; Chrome i mobilläge vidgade då hela layoutvyn (438 px på startsidan, 404 på
  tjänstesidan) och sidan zoomades ut. Helsidesbilderna blev bara några pixlar bredare och såg riktiga ut; axe,
  Lighthouse och målytsprovet var gröna. Ett nytt prov som kräver `innerWidth == begärd bredd` och inga element utanför
  fönstret fann det på första körningen. Ett element-screenshot rullar dessutom sidan — mät läget före bilden.
- **Möjlig generell lärdom**: varje mobilprov ska först jämföra fönstrets bredd med den begärda; horisontellt spill är ett
  eget prov, inte något skärmbilder visar. Rättningen (`minmax(0, 1fr)`, mjuka bindestreck, `overflow-wrap` som sista
  utväg) är generell för grid-remsor med text i kolumnhuvuden.
- **Lokal preferens?** Nej. **Tillämpning**: `spill.mjs` i provlistan; skärmbildsskriptet mäter före element-bilder.
  **Kvarvarande osäkerhet**: 320 px-skärmar prövas inte. **Läge**: ny.

## L22 — Provarens tangent blev ett produktfynd: reproducera handlingen modellfritt före varje ändring
- **Observation**: scenario 2 (etapp 3) rapporterade att felsammanfattningen kom "efter första rullgardinen". Koden
  sätter fel bara vid skickförsök. Reproduktion med hållarens exakta handling visade orsaken: `select` skrev
  alternativet och tryckte Enter, och Chrome skickar formuläret implicit vid Enter i ett val-element — sammanfattningen
  var sajtens riktiga svar på ett skickförsök provaren inte visste att den gjort. Med Tab: inget.
- **Möjlig generell lärdom**: en hållare ska efterlikna besökarens tangenter (Tab, inte Enter, efter typeahead), och
  kontrollanten frågar vid varje "oväntat" tillstånd vilken handling som utlöste det innan fyndet sorteras som produktfel.
  Byggunderlagets fråga "reproducera innan något ändras" sparade en onödig kodändring.
- **Lokal preferens?** Nej. **Tillämpning**: agentlage.mjs avslutar `select` med Tab; KONTROLL.md-raden "observerat
  slutläge" kompletteras med "utlösande handling" vid oväntade tillstånd. **Kvarvarande osäkerhet**: andra webbläsare.
  **Läge**: ny.

## L23 — Rotera automationsnyckeln i rätt ordning, och tro inte att den kräver ny driftsättning
- **Observation**: `revoke` av den gamla nyckeln vägrades (400) tills en annan nyckel pekats ut som miljövariabeln
  (`update` med `isEnvVar`); en nygenererad nyckel gällde direkt mot den befintliga driftsättningen (läsprov 200 utan
  ny driftsättning) — inventeringens "kräver ny driftsättning" gäller bara miljövariabelns värde inne i driftsättningen,
  som sajten inte läser. API-svaren bär nycklarna som objektnycklar: varje svar sparas rått med 600 utanför repona och
  bara antal/etiketter/statuskoder skrivs ut.
- **Möjlig generell lärdom**: ordningen är generera → peka ut miljövariabel → återkalla → läsprov (utan huvud, ny nyckel,
  gammal nyckel); påståenden om vad en nyckel kräver avgörs med läsprov, inte med dokumentationens formulering.
- **Lokal preferens?** Nej (Vercel-specifikt i detaljerna, generellt i ordningen). **Tillämpning**: rotationsskriptets
  steg; en nyckel per verktyg med etikett. **Kvarvarande osäkerhet**: hur länge en återkallad nyckel cachas vid kanten
  (läsprovet gav 302 direkt). **Läge**: ny.
