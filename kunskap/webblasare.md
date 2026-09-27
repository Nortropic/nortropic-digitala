# Webbläsarvägen — utvecklarinspektion, utforskande QA och avskärmat besökarprov med Playwright

Professionsfil (HELHET-20260927, avsnitt 6; etapp 4). Laddas i stegen `bygge`, `qa` och `provare`. Verktygen i
`verktyg/webblasare/` bygger på Playwright 1.63.0 och Playwright MCP 0.0.82 (båda Apache-2.0, pinnade i
`package.json` med `package-lock.json`; `npm ci` i katalogen; webbläsarbinären hämtas av Playwright till användarens
cache). Ingen egen webbläsarmotor: Playwright är motorn, Digitala bär tre användningar, gränser och bevisform.
Runtimes provarprofil (Puppeteer, D034) står kvar för besökarprov genom motorn; den här vägen ger utvecklaren och
QA:n riktig interaktion och ger besökarprovet en Playwright-väg med samma avskärmning.

## Tre användningar i samma instrumentarium

| Användning | Verktyg | Vem väljer vägen | Får kontext | Ger |
|---|---|---|---|---|
| 1. Utvecklaren eller designern undersöker renderingen under arbetet | `inspektera.mjs` | verktyget (fasta vyer och tillstånd) | ja: brief och kodfiler bifogas som lista med hashar (`--kontext`) och läses av sessionen | skärmbilder (första vyn, hela sidan, hover, fokus, meny, reflow 320), tillgänglighetsträd, konsol, sidfel, nätverk med blockerade förfrågningar, tangentbordsväg med synlig fokus, omladdning, bakåt/framåt, spår |
| 2. Utforskande QA väljer själv vägar | `utforska.mjs` (heuristisk motor) och sessionen genom Playwright MCP (`mcp.json` ur `besok.mjs --torr` utan avskärmning) | motorn (crawl inom ursprunget, formulärens felvägar, meny, tangentbord, 404, bakåt) eller sessionen | ja, inom testmandatet | fynd typade fel/varning/observation med reproduktion, `REGRESSION.json` som körs om med `--regression`, spår |
| 3. Avskärmad förstagångsbesökare löser en uppgift | `besok.mjs` (Playwright MCP i egen session: claude eller codex) | modellen, inom gränsen | nej: uppgiften avskärmas (brief, kod, facit, kritik, filnamn vägras), inga andra verktyg | besökets svar (utfall, steg, hinder), MCP-session och spår, efterkontroll av ursprung |

Skärmbilder kompletterar interaktionen och ersätter den inte; layout bedöms i bilderna — ett textträd är inte
bildseende. Mobilvyer (390, 768, 320) är emulerade, inte prov på fysisk enhet; det står i varje rapport. En
modellbaserad besökare är inte en människa, och ett modellbaserat femsekunderstest är inte ett uppmätt mänskligt.

## Tillstånd som stöds

hover (`--hover SEL`), fokus (`--fokus SEL`), tangentbord (Tab-sekvens med synlig fokusmarkering: outline eller
box-shadow), zoom/reflow (320 px utan horisontell spill), mobil (390, 768), meny (`--meny SEL`, aria-expanded),
formulärvalidering (tomt, långt, ogiltig e-post, skriptsträng, unicode), bakåt/framåt, omladdning, okänd adress (404),
laddning (nätverksfel listas), dialoger (avvisas och loggas). Legitima popup- och tredjepartsberoenden ges som tillåtna
ursprung (`--tillat`); allt annat blockeras på route-nivå och listas som blockerat så att det inte misstas för
produktens beteende.

## Gränser och hemligheter

- Värdverkställd ursprungsgräns i användning 1 och 2: förfrågningar utanför tillåtna ursprung avbryts av verktyget.
  I användning 3 är MCP:s `--allowed-origins` ingen säkerhetsgräns (dokumenterat av Playwright); därför sparas
  spåret och efterkontrolleras: alla begärda ursprung ska ligga inom gränsen, annars underkänns körningen.
- Isolerade kontexter (inga sparade profiler, inga konton, inga köp, inga riktiga meddelanden); formulär skickas i
  QA bara med `--formular-far-skickas` och en testmarkering i fälten, mot kontrollerad mottagare.
- Skyddsundantag för förhandsvisningar: privat fil (0600, utanför tmp) ges med `--undantag-fil`; headern sätts bara
  mot målets ursprung; värdet skrivs aldrig ut; JSON-loggar redigerar det och kända hemliga huvuden och parametrar.
  Spårfiler och MCP-sessioner kan bära headern i nätverksposter och är därför privata när undantag använts
  (`spar_privat: true`), aldrig bilagor till granskning utanför kontoret.
- Säkerhetsbrister döljs inte med promptinstruktioner: ett fynd om oescapad indata, saknad validering eller
  blockerad resurs står i rapporten.

## Fynd blir regressionsprov

`utforska.mjs` skriver `REGRESSION.json` (sida, vad, reproduktion) för fel och varningar; `--regression FIL` kör om
just dessa sidor efter en rättning. Ett fynd som rättats och passerar stannar i filen med sin reproduktion tills
leveransen är klar; kvalitetsbilden pekar på körningen.

## Körbevis

`test_webblasare.py` kör alla tre verktygen mot en lokal provsajt (inspektion med kontext, gräns, tillstånd och
redigerat undantag; QA som hittar 404, dubbla h1, osynlig fokus, inte skickar utan tillåtelse, skickar med
testmarkering och fångar dubbelt inskick, kör om regressionsprov; besökarprovets avskärmning, MCP-konfiguration och
efterkontroll mot ett syntetiskt spår). En verklig modellkörning av besökarprovet (claude -p med MCP) redovisas som
eget körbevis när den gjorts; utan den är användning 3 prövad i torrläge.
