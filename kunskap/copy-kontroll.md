# Copykontroll — fraser, strukturer och obligatoriska element som rapport

Professionsfil (HELHET-20260927, avsnitt 4–5), återvunnen ur det arkiverade repots copy-blocklista och
content-designerns regler, omgjord från lag till rapport. Laddas i steget `redaktionellt-pass` tillsammans med
`redaktionellt-pass.md`. Verktyget `verktyg/copy_kontroll.py` skriver rapporten; människan eller sessionen rättar
eller motiverar varje fynd. Ingen poäng, inget godkännande, ingen stilregel: en fras kan vara rätt i en kunds röst.

## Vad rapporten tar upp

| Typ | Vad | Riktning |
|---|---|---|
| fras | utfyllnads- och byråfraser på svenska ("vi förstår att", "skräddarsydda lösningar", "kvalitet i fokus", obevisbara superlativ) | säg vad som görs, för vem, när och till vilket pris; belägg eller stryk |
| engelskt läckage | lånad marknadsföringsjargong (seamless, elevate, world-class …) på svensk sajt | skriv svenska |
| platshållare | lorem ipsum, TODO-markörer, `[OSÄKER]` i levererad text | fakta beläggs eller texten tas bort |
| hälsningsrubrik | "Välkommen till …" som rubrik | första vyn säger vad som erbjuds och för vem |
| tankstreckskedja | två eller fler tankstreck i samma stycke | högst ett per stycke; variera konstruktionen (fråga, kolon, relativsats) |
| utropstecken | fler än ett per sida | högst ett, helst inget |
| spegelöppningar | tre stycken i rad som börjar med "Vi" | skriv om besökaren och uppgiften; variera subjektet |
| metalängd | title över 60 tecken, description över 155 | sanningsenlig och kort; inga superlativ i metadata |
| saknat element | obligatoriska element ur verksamhetsuppgifterna saknas (telefon på varje sida, organisationsnummer, serviceområde, publik adress) | elementen kommer ur `VERKSAMHET.json` (`verktyg/verksamhetsuppgifter.py krav`), inte ur en branschmall |

Bransch- och kundspecifika fraser (briefens §6) ges som `--fraser FIL`, en fras per rad; de rapporteras som
"kund-/branschfras ur briefen".

## Redaktionella regler bakom fynden

Konkret, lugn, direkt svenska; korta meningar; siffror och ortnamn i stället för adjektiv; besökaren avgör på
sekunder om sidan gäller hen. Varje löfte om tillgänglighet ("jour", "svar inom en timme") ska vara bemannat och sant.
Varje förtroendepåstående bär ett kvitto med rätt attribution (utbildning redovisas som utbildning, inte som
certifikat; betyg med plattform och antal). Rubriker i satsform, inte versaler. FAQ-frågor är frågor som kunder
faktiskt ställer. Humanisering (varierad meningslängd, konkreta exempel, kundens egna ord) är en läsning av texten
högt, inte en regel om vissa ord.

## Vad kontrollen inte gör

Den bedömer inte röst, ton eller sanningshalt; den mäter inte läsbarhet; den ersätter inte faktakontrollen i
`redaktionellt-pass.md` del 1 eller kedjekontrollen i del 2. Ett fynd som motiveras i kundens röst står kvar med
motivering i det redaktionella passets not.
