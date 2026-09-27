# Kvalitet — kriterier och kvalitetsbilden

## Kriterier (professionens, för alla kunder)

1. **Formgivet för just denna kund**: tydlig typografi med egen röst, genomtänkt bildspråk eller grafisk identitet,
   rytm och luft, en sammanhängande mobilupplevelse; inte en generisk mall med utbytt logotyp och identiska kort
   (DIGITALA-1-ACCEPT-20260925 §2). Designspecificitet bedöms före allt annat.
2. **Tillgänglighet**: WCAG 2.2 AA är kvalitetskrav; axe utan violations i varje vy, manuella kontroller enligt
   accessibility-texten (fokusordning, rubriker, namn), läsförhållanden (mobil, utomhus, kvällstid).
3. **Prestanda och teknik**: Lighthouse över kundens kravnivå; ingen horisontell spill; layoutvyns bredd lika med
   den begärda (L21); en klocka i tidsmätningar (L3).
4. **Innehåll**: faktatrohet och redaktionell kvalitet är två kontroller (L8); kedjan val → mening → formulär →
   slutbesked hänger ihop (L2).
5. **Regler**: demoregler eller kundens regler; bildposter med licens före bygget (L5); inga riktiga uppgifter där
   sådana inte får finnas.
6. **Upplevelse**: första vyn, hierarki, en primär handling, rytmen nedanför vikningen; prövas genom kritik och
   femsekunderstest, aldrig bara genom gröna prov.

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
