---
name: digitala-steg
description: Ladda ett Digitala-stegs obligatoriska underlag med versionskontroll och kvitto innan steget utförs (uppstart, beredning, research, brief, koncept, bygge, redaktionellt-pass, seo, matning, kritik, granskning-d, provare, uppfoljning, annonsberedning, lokal-synlighet, prelaunch, leverans, lansering, sokkonsol, drift). Använd när ett Digitala-steg ska påbörjas i detta repo eller i ett kundrepo.
---

Detta är en leveransform för Claude Code. Bäraren är filerna i repot (`steg/steg.json`, `MANDAT.md`, `ARBETSSATT.md`);
Codex når samma sak genom `AGENTS.md`. Gör så här:

1. Läs `MANDAT.md` om steget är märkt `bestallning`; då krävs `--bestallning POST-ID`.
2. Kör från repots rot:
   `python3 -B verktyg/ladda_steg.py --steg STEG --ut ARBETSYTA [--kund KUNDMAPP] [--bestallning POST-ID] --utforare claude`
   där ARBETSYTA är en ny katalog utanför repot.
3. Läs `ARBETSYTA/UNDERLAG.md` först (fullständig lista, delar att läsa, anvisning). Läs bara de delar som anges.
4. Utför steget. Skriv användningsnoterna i `ARBETSYTA/ANVANDNINGSNOTER.md` när steget är klart.
5. Ett vägrat kommando (exit 2) betyder saknat obligatoriskt underlag, fel version, kundfil i fel klass, okänt steg
   eller steg utanför stående mandat: rätta orsaken; ersätt aldrig underlaget med egna antaganden.
