# nortropic-digitala — Digitala, Nortropics webbförvaltning

Det här repot är Digitalas gemensamma hem: **mandat, professionskunskap, metoder, kvalitetskriterier, prov, verktyg
och lärdomar** för att skapa och förvalta digitala upplevelser åt kunder. Det är professionsgemensamt. Kundspecifik
sanning (research, brief, innehåll, bildposter, kod, nycklar, adresser) bor hos respektive kund: i kundens repo och i
kontorets privata kundmapp. Här finns bara pekare dit (`kunder/README.md`).

Börja i [`AGENTS.md`](AGENTS.md) (ordinarie ingång för utförare, Claude Code och Codex lika). Läsordning:
`MANDAT.md` → `ARBETSSATT.md` → `steg/steg.json` genom `verktyg/ladda_steg.py` → `kunskap/LARDOMAR.md`.

## Vad som finns

| Del | Innehåll |
|---|---|
| `MANDAT.md` | Stående mandat härlett ur ägarens beslut (med källor), vad som kräver en beställning, namngivna saknade gränser |
| `ARBETSSATT.md` | Stegen, proportionen (liten · mellan · stor uppgift) och hur Runtime och kundrepot används i varje steg |
| `KVALITET.md` | Kvalitetskriterier och kvalitetsbilden: tekniskt prövat · professionellt bedömt · ej observerat hos verkliga användare |
| `steg/steg.json` | Maskinläsbar bindning steg → obligatoriska och valfria underlag (profession och kund), mandatklass och anvisning |
| `steg/PINNAR.sha256` | Versionspinnar för varje professionsunderlag; ändras bara som nytt beslut (`verktyg/pinna.py`) |
| `kunskap/` | Registret, lärdomarna (P4-form), härledda texter och de pinnade externa texterna med licenser |
| `kritik/` | Frågemallar och slutna JSON-scheman för Runtimes kritikprofil (designkritik av komp, renderingsläsning, femsekunderstest) |
| `provare/` | Uppgifts- och kontrollmall för scenarioprov samt provarens instruktion |
| `matning/` | Digitalas val för Runtimes mätprofil (vyer, axe-taggar, delar) och täckningskartan mot sajtspecifika prov |
| `verktyg/` | `ladda_steg.py` (underlagsladdning med kvitto), `kor_profil.py` (Runtimes profiler med Digitalas val), `kvalitetsbild.py`, `pinna.py`, prov |
| `.claude/skills/digitala-steg/` och `adaptrar/codex/` | Leveransformer för respektive CLI; filerna ovan är bäraren, adaptrarna bara vägen dit |
| `PROVENIENS.md` | Varifrån det migrerade materialet kommer, byte för byte, med sha256 |

## Snabbstart

```sh
python3 -B verktyg/ladda_steg.py --steg matning --ut /privat/arbetsyta/matning-1
python3 -B verktyg/ladda_steg.py --steg kritik --kund /privat/kundmapp --ut /privat/arbetsyta/kritik-1
python3 -B verktyg/kor_profil.py matning --laddning /privat/arbetsyta/matning-1/LADDNING.json --mal https://… --etikett x --fall /privat/fall
python3 -B verktyg/kvalitetsbild.py --fall /privat/fall --ut /privat/fall/KVALITETSBILD.md
python3 -B -m unittest discover -s verktyg -p 'test_*.py'
```

Arbetsytor och fall ligger alltid utanför repot (kontorets privata evidens eller en privat katalog). Repot bär aldrig
nycklar, adresser till skyddade sajter, kunduppgifter eller körningars utdata.
