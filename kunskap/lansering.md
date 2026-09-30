# Lansering — procedur, kontroll, oåterkalleligt och återgång

Professionsfil (HELHET-20260927, avsnitt 4 "Leverans, drift och förbättring"), återvunnen ur det arkiverade repots
cutover-flöde och lanseringssteg. Laddas i steget `lansering`. Verktyg: `verktyg/lansering.py` (plan och läsande
kontroll), `verktyg/sokkonsol.py` (sökkonsolens skrivande steg), värdplattformens CLI (driftsättning, domän, återgång).
Lansering sker bara enligt gällande mandat: en beställning som namnger lansering och domän (MANDAT.md §2); privat
förhandsvisning och slutrapport levereras alltid först.

## Före lanseringsdagen

Lanseringskonfiguration skild från förhandsvisningen (noindex och robots-blockering bara i förhandsvisningen);
kanonisk domänvariant vald, den andra omdirigerar; omdirigeringar från gammal sajt prövade; sökkonsolens META-token
renderad; prelaunch-rapport redo; domän och certifikat hos värden; återgångsvägen känd (föregående driftsättning
pekas tillbaka med värdplattformens CLI).

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
