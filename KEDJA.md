# Kedjan — vad Runtime verkställer mekaniskt och vad som bärs av en utförarsession och dokumenterade regler

Ägarens ombyggnadsbesked (etapp 4): "Redovisa exakt vilka delar Runtime verkställer mekaniskt och vilka som fortfarande
bärs av en utförarsession och dokumenterade regler. Beskriv inte den senare vägen som mekaniskt skyddad." Läst mot
Runtime main `b603d91` (aktiv release `03e776bd`), kontoret och detta repo 2026-09-27.

| Led i Digitalas kedja | Mekaniskt (Runtime eller annan mekanism) | Sessionsburet + dokumenterade regler |
|---|---|---|
| Mandat och beställning | — | ägarens ord i kontorets logg; `MANDAT.md`; laddningen vägrar ett beställningssteg utan post-id (verktyg, inte spärr: sessionen kan låta bli att köra verktyget) |
| Underlagsladdning per steg | `verktyg/ladda_steg.py`: versionspinnar, klasser, kvitto, vägran vid saknat/fel/sammanblandning | att verktyget körs och `UNDERLAG.md` läses är sessionens ansvar (`AGENTS.md`); ingen mekanism tvingar en byggsession att ladda |
| Research, brief, koncept, bygge, redaktionellt pass | — | helt sessionsburet i kundrepot och kundmappen; Vercel-driftsättning bakom inloggning är plattformens skydd, inte Runtimes |
| Mätning | Runtimes mätprofil: pinnade verktyg, sandlådad detektor, hemlighetsregler, kvitto med hashar; från D037 Digitalas vyer och taggar som parametrar | valet av adress och driftsättning; grep efter nyckeln i utdata (regel L23) |
| Kritik och läsning | Runtimes kritikprofil: skrivskyddad läsare (Read + StructuredOutput respektive sandlåda), schemaprövning av svarets form, kvitto | frågans och schemats innehåll (mallarna här); tolkningen av svaret |
| Scenarioprov | Runtimes provarprofil: proxygräns, vakt eller sandlåda, grammatik, spår, hemlighetsregler, kvitto | uppgiftens text; kontrollantens bedömning ur artefakter (`KONTROLL-MALL.md`) |
| Separat granskning | Runtimes läsarprofil (bara Read); kontorets publicerare kräver granskningskvitto för samma commit och byte | vad granskaren får läsa; samma modellfamilj = separat läsning, inte oberoende omdöme |
| Publicering av kontorsposter och Runtime-ändringar | `publish_construction`: hela sviten på exakt kandidat, granskningskvitto, värdkontrollkvitto (Runtime), skyddad main, exakt squash | postens innehåll |
| Ändringar i detta repo | git-historik; prov (`verktyg/test_*.py`); **grenskydd genom ruleset `main-skydd`** (sedan 2026-09-27: radering och forcerad push nekas, ändringar bara genom pull request, inga manuella godkännanden krävs; den tidigare uppgiften att gratisplanen vägrade skydd gällde klassiskt grenskydd, rulesets gick att skapa) | separat granskning före sammanslagning enligt `AGENTS.md`; granskningskvittot bokförs i kontorets post; pull request skapas och slås samman maskinellt |
| Beställnings-id vid laddning | `ladda_steg.py` prövar bara att id:t finns och har rätt form | att posten finns i kontorets `docs/decisions.md` och ger mandatet läser utföraren själv; verktyget läser inte kontorets repo |
| Modell- och utförarval | Runtime: `development.models`/`executors` i frysta releasen, identitetskontroll, fråga vid kapacitetsbrist; profilerna tar modellen som parameter | byggsessionens modell är operatörens CLI-inställning, utanför Runtime |
| Kontinuitet | Runtime: motorns historik för uppgifter | kontorets plan, privata `LAGE.md`, laddningskvitton, `KORNING-*.json`; ny session läser och tar över |
| Lärande | — | `LARDOMAR.md`, `ANVANDNINGSNOTER.md`, förslagsraden; rytmen i kontoret |

Kundrepot är inte ett Runtime-mål och blir det inte genom ombyggnaden; bygget och driftsättningen är sessionsburna.
