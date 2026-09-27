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

Ram: ägaren har inte satt något tak för stående arbete. Varje fall anger sin egen ram (antal modellsessioner, tid) i
kontorsposten och redovisar förbrukningen; abonnemangets kvot är den yttre gränsen (D030: kvotbrist är väntan, aldrig
köp). "Ägaren deltar inte i prov" (DIGITALA-1-AGARBESLUT-20260926) gäller allt stående arbete.

## 2. Kräver en beställning (beslutspost i kontoret)

| Arbete | Källa |
|---|---|
| Ändring av kundens sajt: brief, koncept, bygge, redaktionell ändring, driftsättning och befordran | DIGITALA-1-RIKTNING-20260926 §1 ("ger inget mandat att bygga om den driftsatta sajten"); DIGITALA-1-AGARBESLUT-20260926 (etapp 4 som beställning) |
| Ny kund eller nytt fiktivt fall | DIGITALA-1-ACCEPT-20260925 §7 ("inga fler företag väljs … innan den första leveransen har bedömts") |
| Installation eller registrering av nya resurser, verktyg, skills eller versioner | DIGITALA-1-RIKTNING-20260926 §3 och §6; registrets regel 4 |
| Allt som kostar utöver den inkluderade Pro-krediten; betalda tillägg; analys- eller fältmätning som debiteras | DIGITALA-1-AGARBESLUT-20260926 (C6, C10, kreditvalet) |
| Lansering, egen domän, DNS, annonsering, delbar länk till utomstående, riktiga mottagare | DIGITALA-1-ACCEPT-20260925 §2 och §4 |
| Mänskliga användarprov och prov där ägaren deltar | DIGITALA-1-AGARBESLUT-20260926 (C4) |
| Ändring av Runtime, AP-10 eller modellvalet | ägarens ombyggnadsbesked 2026-09-27 §4 etapp 4; D029 |

Steg i `steg/steg.json` bär mandatklassen (`staende` eller `bestallning`); `verktyg/ladda_steg.py` vägrar ett
beställningssteg utan `--bestallning POST-ID`. Ett beställnings-id är namnet på beslutsposten i kontorets
`docs/decisions.md` som ger mandatet (till exempel `DIGITALA-1-AGARBESLUT-20260926`).

## 3. Namngivna saknade gränser (behörighetsfrågor för ägaren, inte uppfunna regler)

- **Underhåll av en levererad sajt mellan beställningar** (till exempel en trasig länk eller ett stavfel på
  Norrglänta): inget beslut ger Digitala rätt att ändra sajten utan beställning. Tills ägaren beslutar är det en
  beställning. Ägarens ombyggnadsbesked säger uttryckligen att inget nytt underhållsåtagande för Norrglänta ska
  uppfinnas.
- **Tak för stående arbete per månad** (modellsessioner, tid): inget ägarbeslut; fallets ram gäller, förbrukning
  redovisas i kontorsposten.
- **Nästa kund**: beslutet är ägarens efter bedömningen av Norrglänta (DIGITALA-1-ACCEPT-20260925 §7).

## 4. Gränser som alltid gäller

Demoreglerna för fiktiva kunder (DIGITALA-1-ACCEPT-20260925 §1–§2, PRODUCT.md hos kunden); "uppmätt · bedömt · ej
prövat" hålls isär (§7); den gamla webbförvaltningen är källmaterial, aldrig körväg (DIGITALA-1-KORRIGERING-20260926);
inga nya abonnemang, modeller, betalvägar eller organisationsbehörigheter; privat material stannar privat.
