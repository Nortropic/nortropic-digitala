# Täckningskarta — kundrepots generiska prov mot Runtimes mätprofil (version 1, 2026-09-27)

Regel (ägarens ombyggnadsbesked, etapp 4): ta inte bort gamla prov förrän motsvarande täckning har visats på samma
driftsättning; liknande verktygsnamn är inte bevis för likvärdig täckning. Sajtspecifika produktprov stannar hos
kunden. Kartan nedan är kedjedrivarens läsning av `kund-demo-norrglanta/scripts/prov/` (gren etapp4, 2026-09-27) mot
`runtime.web_measure` (D034–D036). Täckning "visad" kräver en jämförelse av två körningar mot samma driftsättning,
bokförd i fallet; tills dess är raden en hypotes.

| Kundrepots prov | Vad det mäter | Mätprofilen | Täckning | Åtgärd |
|---|---|---|---|---|
| `axe.mjs` | axe-core (låst) på sex sidor, mobil och dator, plus formulärets fel- och slutläge och den öppna mobilmenyn; samma taggar som profilen | `axe` per vy för en adress per körning; inga formulär- eller menylägen | delvis: sidor ja (en körning per sida), lägen nej | behåll tills lägena täcks; sidorna kan gå genom profilen efter visad täckning |
| `lighthouse.mjs` | Lighthouse (låst) på sex sidor, mobil och dator | `lighthouse` mobil och dator för en adress per körning | bedömt 2026-09-27, inte visad: sannolikt full per sida | jämför poäng och kategorier på samma driftsättning; sedan förslagsrad |
| `skarmbilder.mjs` | helsida och första vy per sida och vy | `skarm`: första vy, sektioner, hela sidan per vy | bedömt 2026-09-27, inte visad: sannolikt full per sida | som ovan |
| Impeccable `detect` på spegel | detektorn på byggd HTML med stilmallar | `detektor` på självbärande ögonblicksbild per vy i sandlådan | okänt: annan indata (ögonblicksbild kontra spegel) | jämför antal och typer på samma driftsättning |
| `forsta-vyn.mjs` | h1 ≤ 2 rader, en solgul handling, toppjustering, planens handling och notis i vyn, hover på konturknappar | `rubrik`: h1-rader och namngiven handling i vyn | delvis: h1 och handling ja; antal primära handlingar, justering, notis, hover nej | behåll |
| `kontrast-hero.mjs`, `malytor.mjs`, `natverk.mjs`, `rorelse.mjs`, `spill.mjs`, `text.mjs`, `lagen.mjs`, `formular.mjs`, `tidsfalla.mjs`, `kedja.mjs`, `bakat.mjs`, `flytknapp.mjs`, `plan-tangentbord.mjs`, `rubriker.mjs`, `faktakontroll.mjs` | sajtspecifika produktprov (kontrast per block, tappytor, nätverk, rörelse, spill och layoutvy, text, rubriker, formulärkedjan, tidsfällan, bakåt, flytknapp, tangentbord, svarshuvuden, faktakontroll) | inget | ingen | stannar hos kunden (Runtimes mandat: verksamhetsspecifika funktioner hör till målrepot) |
| `agentlage.mjs`, `agentlage-browser.mjs` | den egna webbläsarvägens handlingskommando och hållare | provarprofilen har egen hållare, grammatik och vakt | annan väg med samma gräns | behåll tills provarprofilen använts i ett fall; jämför spår |

Att visa täckning: kör `verktyg/kor_profil.py matning` mot samma oföränderliga driftsättningsadress som kundrepots
prov kördes mot, en körning per sida, och jämför axe-violations (id per vy), Lighthouse-kategorier (inom
körningsvariansen), skärmbildernas omfång och detektorns fynd. Bokför jämförelsen i fallet och i denna fil som
"visad" med datum och körkataloger. Först därefter får en förslagsrad föreslå att kundrepots motsvarande prov tas bort,
och borttaget görs av den som driver kundrepot.
