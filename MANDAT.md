# Digitalas mandat — stående mandat, beställningar och namngivna saknade gränser

Härlett ur ägarens registrerade beslut i kontorets `docs/decisions.md`. Ingen rad här är ett nytt beslut: varje rad
har en källa. Där en gräns saknas står det som en namngiven behörighetsfråga, inte som en uppfunnen regel.

## 1. Ryms i det stående mandatet (ingen ny beställning per operation)

| Arbete | Källa |
|---|---|
| Uppstart, läsning av lärdomar, register och plan; research och referensjakt utan att kopiera | FORVALTNINGAR-LOPANDE-UTVECKLING-BESLUT-20260926 (rytm per fall); DIGITALA-1-ACCEPT-20260925 §2 |
| Mätning mot kundens skyddade förhandsvisning eller produktion med befintligt undantag (privat nyckelfil), aldrig utskriven | DIGITALA-1-ACCEPT-20260925 §4; DIGITALA-1-AGARBESLUT-20260926 (P-B, C9: en nyckel per verktyg); RUNTIME-PROFILER-OVERGANG-AKTIV-20260927 |
| Kritik-, läsar- och femsekunderssessioner genom Runtimes läsar- och kritikprofil inom abonnemanget | DIGITALA-1-AGARBESLUT-20260926 (P-C); D034 |
| Scenarioprov med den egna webbläsarvägen mot skyddad sajt; kontrollanten avgör utfallet | DIGITALA-1-ETAPP3-RESULTAT-20260926; DIGITALA-1-AGARBESLUT-20260926 ("alla fyra prov") |
| Separat granskning genom Runtimes läsare före integration och publicering | kontorets AGENTS.md; DIGITALA-1-ACCEPT-20260925 §7 |
| Lärdomsposter, användningsnoter, förslagsrad; månadsbevakning enligt inventeringens del b från oktober 2026 | FORVALTNINGAR-LOPANDE-UTVECKLING-BESLUT-20260926; DIGITALA-1-AGARBESLUT-20260926 (C5) |
| Registrering av resultat som kontorspost med planrad, efter separat granskning | kontorets AGENTS.md |
| Underhåll av en lanserad sajt hos en riktig kund enligt underhållsformen: veckokontroll, hämtning av kundens poster, och de faktarättelser kunden själv lämnar — öppettider, telefonnummer och pris — kontrollerade genom ordinarie kedja, med besked efteråt till kunden och i veckobeskedet. Bara telefondelen av kontaktvägarna ryms här; en ändrad formulärsökväg eller e-postadress är ett förslag. En personaländring är ett förslag tills ägaren avgör den frågan | DIGITALA-UNDERHALL-20260929 |
| Veckobesked till ägaren om gjorda rättelser, väntande förslag och förbrukning | DIGITALA-UNDERHALL-20260929 |

Ram: taket för stående arbete är 20 läsande modellsessioner per kalendermånad, redovisade i månadsomgången
(DIGITALA-UNDERHALL-20260929). Talet är kedjedrivarens förslag i OMBYGGNAD-AGARSVAR-20260927, som ägaren godtog
2026-09-29; det står inte i hans egna ord. Varje fall anger dessutom sin egen ram (antal modellsessioner,
tid) i kontorsposten och redovisar förbrukningen; abonnemangets kvot är den yttre gränsen (D030: kvotbrist är väntan,
aldrig köp). Taket räknas per kund i `UNDERHALL.json` av `verktyg/underhall.py sessioner`, som vägrar en bokföring över
taket utan en beställning; veckokontrollen kostar inga modellsessioner.
"Ägaren deltar inte i prov" (DIGITALA-1-AGARBESLUT-20260926) gäller allt stående arbete.

## 2. Kräver en beställning (beslutspost i kontoret)

| Arbete | Källa |
|---|---|
| Ändring av kundens sajt: brief, koncept, bygge, redaktionell ändring, driftsättning och befordran — utom de faktarättelser underhållsformen namnger (§1) | DIGITALA-1-RIKTNING-20260926 §1 ("ger inget mandat att bygga om den driftsatta sajten"); DIGITALA-1-AGARBESLUT-20260926 (etapp 4 som beställning); DIGITALA-UNDERHALL-20260929 (undantaget) |
| Allt kunden önskar utöver en faktarättelse: ny sida, ny tjänst, ändrad text eller design, personuppgifter (även en medarbetare som slutat, tills ägaren avgör frågan), annan kontaktväg än telefonnummer, allt som kostar. Digitala skriver ett förslag med omfattning och uppskattat antal sessioner; ägaren säger ja eller nej | DIGITALA-UNDERHALL-20260929 |
| Underhåll av ett fiktivt testbygge efter leveransen (Norrglänta, Vikskär, testfall och kommande fiktiva fall) — underhållsformen gäller bara riktiga kunder med en lanserad sajt | DIGITALA-UNDERHALL-20260929 (ägarens ord: "det är till riktiga kunder, inte fiktiva test byggen") |
| Ny kund eller nytt fiktivt fall | DIGITALA-1-ACCEPT-20260925 §7 ("inga fler företag väljs … innan den första leveransen har bedömts") |
| Installation eller registrering av nya resurser, verktyg, skills eller versioner | DIGITALA-1-RIKTNING-20260926 §3 och §6; registrets regel 4 |
| Allt som kostar utöver den inkluderade Pro-krediten; betalda tillägg; analys- eller fältmätning som debiteras | DIGITALA-1-AGARBESLUT-20260926 (C6, C10, kreditvalet) |
| Lansering, egen domän, DNS, annonsering, delbar länk till utomstående, riktiga mottagare | DIGITALA-1-ACCEPT-20260925 §2 och §4 |
| Mänskliga användarprov och prov där ägaren deltar | DIGITALA-1-AGARBESLUT-20260926 (C4) |
| Ändring av Runtime, AP-10 eller modellvalet | ägarens ombyggnadsbesked 2026-09-27 §4 etapp 4; D029 |

En beställning bär hela det accepterade uppdraget: beredning, brief, koncept, bygge, kontroll, rättning och färdig privat
förhandsvisning. Normala operationer och omtag inom samma uppdrag kräver inga nya beslutsposter, och det finns inga
rutinmässiga ägarstopp före färdig sida: brief, koncept, interna kvalitetsval och vanliga rättningar går inte via
ägaren. Ägaren får färdig leverans och rapport och lämnar därefter sin bedömning och sina synpunkter (arbetsordern HELHET-20260927, assistentformulerad ur ägarens besked 2026-09-27 och sparad ordagrant i kontoret).
Lansering, egen domän, DNS, annonsstart eller annonsbudget, delbar länk och riktiga mottagare ligger utanför
uppdraget tills ett uttryckligt mandat ger dem.

Steg i `steg/steg.json` bär mandatklassen (`staende` eller `bestallning`); `verktyg/ladda_steg.py` vägrar ett
beställningssteg utan `--bestallning POST-ID`, och fortsättningsvägen (`verktyg/fortsatt.py`) binder beställningen som
ett hashat utdrag ur beslutsposten i kundmappens `BESTALLNING.json` (post, källa, kund, omfattning, lanseringsmandat,
ordagrant utdrag) och markerar steg utanför omfattningen som inte tillämpliga tills beställningen utvidgas. Ett beställnings-id är namnet på beslutsposten i kontorets
`docs/decisions.md` som ger mandatet (till exempel `DIGITALA-1-AGARBESLUT-20260926`).

## 3. Namngivna gränser (två öppna behörighetsfrågor för ägaren, två besvarade; inte uppfunna regler)

Två av de tre gränserna nedan är besvarade av ägaren 2026-09-29 och står kvar här bara som avslutad historik;
underhållsformen och taket gäller enligt §1 och §2 och `kunskap/drift.md`. Underhållsformen lämnade i sin tur en ny
öppen fråga, om en medarbetare som slutat, som står som egen punkt nedan och som egen rad i kontorets ÄGARENS TUR.

- **Underhåll av en levererad sajt mellan beställningar** — BESVARAD 2026-09-29 (DIGITALA-UNDERHALL-20260929).
  Underhållsformen gäller riktiga kunder med en lanserad sajt: veckokontroll, kundens poster i det öppna
  Kundstart-ärendet, faktarättelser kunden själv lämnar inom stående mandat (öppettider, telefonnummer, pris),
  allt annat som förslag till ägaren. Om en medarbetare som slutat hör till stående mandat är en egen öppen fråga.
  Tidigare läge (2026-09-27, OMBYGGNAD-AGARSVAR-20260927): ägaren arbetade fram formen och varje ändring var en
  beställning. Ägarens ombyggnadsbesked om att inget underhållsåtagande för Norrglänta ska uppfinnas gäller
  oförändrat: fiktiva testbyggen förvaltas inte efter leveransen.
- **Tak för stående arbete per månad** — BESVARAD 2026-09-29 (DIGITALA-UNDERHALL-20260929): 20 läsande
  modellsessioner per kalendermånad, redovisade i månadsomgången. Se §1.
- **En medarbetare som slutat**: ÖPPEN (DIGITALA-UNDERHALL-20260929). Den godtagna texten räknar upp den som
  faktarättelse, men formens del 4 och §2 i detta dokument lägger personuppgifter i förslagsvägen, och en fri textrad
  går inte att skilja mekaniskt från att en medarbetare tillkommit. Tills ägaren avgör frågan är en personaländring
  ett förslag.
- **Nästa kund**: ÖPPEN. Beslutet är ägarens efter bedömningen av Norrglänta (DIGITALA-1-ACCEPT-20260925 §7); ägaren tar
  fram nästa fiktiva fall (2026-09-27). Underhållsformen ändrar inte detta och gäller inte fiktiva fall.

## 4. Gränser som alltid gäller

Norrglänta är av ägaren underkänt som kvalitetsresultat (arbetsordern HELHET-20260927, assistentformulerad ur ägarens besked 2026-09-27 och sparad ordagrant i kontoret): det är inte positiv
kvalitetsreferens, designmall eller professionspraxis, och ingen egen leverans definierar hur Digitala bygger. Dess
tekniska körbevis (mätningar, laddningar, integrationsprov) och felreproduktioner får användas; ett lyckat
integrationsprov är inte ett godkännande av sajten.

Demoreglerna för fiktiva kunder (DIGITALA-1-ACCEPT-20260925 §1–§2, PRODUCT.md hos kunden); "uppmätt · bedömt · ej
prövat" hålls isär (§7); den gamla webbförvaltningen är källmaterial, aldrig körväg (DIGITALA-1-KORRIGERING-20260926);
inga nya abonnemang, modeller, betalvägar eller organisationsbehörigheter; privat material stannar privat.

## 5. Kunddialog inom uppdraget

Inom en accepterad beställning får Digitala be kunden om verksamhetsinformation genom den kontaktväg beställningen
anger (kundintervju.md): frågor om mål, erbjudande, flöden, system, material, synlighet, förvaltning och ramar.
Det är informationsinhämtning, inte designgodkännande, och inte ett ägarstopp. Digitala frågar aldrig efter lösenord
eller nycklar i dialogen; åtkomst ordnas på säker väg. Ingen prospektering, ingen ny kundverksamhet, ingen obeställd
masskontakt: bara den kund, kontakt och kanal uppdraget omfattar. Uteblivna svar döljs inte: beroendet redovisas i
leveransen och arbetet fortsätter med det som inte beror på svaret.
