# Kvalitet — kriterier och kvalitetsbilden

## Kriterier (professionens, för alla kunder; kund- och uppgiftsmotiverade, inte stilregler)

1. **Användarnytta och begriplighet**: besökaren förstår vad som erbjuds, för vem och hur man går vidare; de viktigaste
   användaruppgifterna går att lösa; första vyn och sidans hierarki tjänar uppgiften, inte en mall.
2. **Innehållets precision och trovärdighet**: faktatrohet och redaktionell kvalitet som två kontroller (L8); kedjan
   val → mening → formulär → slutbesked hänger ihop (L2); inga påhittade insikter, omdömen, meriter eller personer som
   framställs som verkliga.
3. **Formgivet för just denna kund**: typografiskt hantverk, komposition, rytm och luft, bildspråk och en sammanhängande
   mobilupplevelse som svarar mot kundens verksamhet och målgrupp. Särprägel är värdefull när den hjälper uppdraget och
   ersätter aldrig funktion eller saklighet. Inga generella stilregler (fasta färger, en obligatorisk handling ovanför
   vikningen, universella dial-värden, fast antal koncept) och ingen rangordning där särprägel går före allt annat;
   externa professionella referenser används för jämförelse med motivering, inte kopiering, och ingen ensam referens,
   egen leverans eller automatisk stilpoäng definierar god kvalitet.
4. **Tillgänglighet**: WCAG 2.2 AA är kvalitetskrav; axe utan violations i varje vy, manuella kontroller enligt
   accessibility-texten (fokusordning, rubriker, namn, tangentbord), läsförhållanden (mobil, utomhus, kvällstid).
5. **Prestanda och teknik**: Lighthouse över kundens kravnivå; ingen horisontell spill; layoutvyns bredd lika med
   den begärda (L21); en klocka i tidsmätningar (L3); semantisk, underhållbar implementation; fel-, tom- och
   laddningslägen; formulär som fungerar med tangentbord och skärmläsare.
6. **Regler**: demoregler eller kundens regler; bildposter med licens före bygget (L5); inga riktiga uppgifter där
   sådana inte får finnas; samtyckes- och integritetskrav där mätning eller kanaler ingår.
7. **Bild**: val, licens, autenticitet, art direction, beskärning, responsiva storlekar och optimering; kundens eget
   material först; genererade människor, projekt, meriter eller omdömen framställs aldrig som verkliga kundbevis.
8. **Förvaltbarhet**: innehållsmodell efter behov, dokumenterad driftsättning och återgång, beroenden pinnade.

Norrglänta är av ägaren underkänt som kvalitetsresultat och används inte som referens, mall eller praxis; dess tekniska
körbevis får användas för felreproduktion och generella teknikprov (`MANDAT.md` §4).

## Intern gransknings- och rättningsloop

Före ägarleverans granskas resultatet ur olika relevanta perspektiv med olika underlag: renderingsläsning (skärmbilder
och mätning), kodläsning (granskning D), tillgänglighet, innehåll (redaktionellt pass), SEO där uppdraget omfattar
sök, och ett avskärmat besökarprov (provare eller femsekunderstest) som inte får brief, kod eller facit. Ett underkänt
resultat leder till diagnos, åtgärd och omprov av det berörda; leverans sker först när loopen är stängd. Fler
agentnamn eller fler godkännanden ur samma antaganden är inte bättre granskning; granskare med samma underlag som
byggaren ger en separat läsning, inte ett oberoende omdöme.

## Kvalitetsbilden — tre kolumner som aldrig blandas

| Kolumn | Vad | Källa |
|---|---|---|
| **Tekniskt prövat (uppmätt)** | deterministiska mätningar och prov: axe, Lighthouse, detektor, rubrikrader, handling i vyn, sajtspecifika prov, scenariokontroller ur artefakter | mätprofilens kvitton, kundrepots prov, KONTROLL.md |
| **Professionellt bedömt** | kritik- och läsarsessioner (modell), kedjedrivarens visuella granskning, separat granskning; alltid märkt som bedömning, med bedömarens underlag | kritikprofilens svar, granskningskvitton |
| **Ej observerat hos verkliga användare** | allt som kräver en verklig kund eller människor: verkliga leads, konvertering, kundnöjdhet, läsbarhet utomhus i verkligheten, mänskliga användarprov | listas uttryckligen; aldrig PASS genom påhittade belägg |

Regler: en hög poäng eller gröna prov ersätter inte visuell bedömning; syntetiska eller fiktiva fall ger aldrig
"prövat med människor"; granskare och byggare av samma modellfamilj ger en separat läsning, inte ett oberoende
omdöme, och det skrivs så; ägarens bedömning görs på den färdiga sajten.

`verktyg/kvalitetsbild.py` bygger bilden ur fallets `KORNING-*.json` och deras kvitton; det som saknas i kvittona
står som "ej prövat" och fylls aldrig i av verktyget.
