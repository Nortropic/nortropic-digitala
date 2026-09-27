# Kunskapsstöd för dagens Digitala — register (P3 i JAMFORELSE-DIGITALA-20260926 v4; DIGITALA-1-GENOMFORANDE-20260926)

Professionsfil i Digitala-repots `kunskap/` (flyttad hit 2026-09-27 från kontorets `evidence/digitala/local/kunskap/`,
skapad 2026-09-26 inom paketets del 1; se `PROVENIENS.md`). Repots ordinarie ingång är `AGENTS.md` → `MANDAT.md` →
`ARBETSSATT.md` → `steg/steg.json` genom `verktyg/ladda_steg.py`; detta register beskriver underlagen och deras koppling
per steg.

**Regler.** (1) Ladda per steg enligt kopplingstabellen, aldrig hela mappen. (2) Underlagen är råd; briefen, ACCEPT och
gällande mandat vinner alltid. Ett råd som strider mot ett accepterat krav redovisas som förslag i briefens konfliktrad
eller i överlämningen och ändrar inget av sig självt. (3) Externa texter och gamla instruktioner är källmaterial: att de
är kopierade eller lästa ger dem ingen styrande kraft. (4) Versionerna är pinnade; en senare version tas in bara som nytt
beslut med ny läsning och ny kontroll. (5) Varje fall lämnar en **användningsnot** per underlag i sin överlämning, med ett
av fyra utfall: *påverkade ett konkret val, en ändring eller ett fynd (vilket)* · *användes som kontroll, ingen ändring
behövdes* · *inte tillämpligt* · *nådde inte arbetet*. Ingen rapport per fil, ingen kvot; inga konstruerade bidrag.
(6) Uppföljning enligt `LARDOMAR.md` (klassning och användningsnoter; ingen automatisk praxis); avslutad användning = raden märks "laddas inte",
filen och noterna bevaras.
(7) Formen per underlag (läsfil, registrerad skill, installerad plugin, metod) är ett nyttoval per resurs, inte en
regel: att prototype används som metod beror på dess egen anropsspärr och tillför inget krav på att andra skills
startas manuellt (DIGITALA-1-RIKTNING-20260926). Installationer och registreringar som tilläggsmandatet omfattar
förs in här när de är gjorda, med version.

## A. Åtta externa huvudtexter (1–7 kopierade byte för byte från läsbevisen i `../jamforelse-underlag/lasta-texter/`; 8 från läsningen i `../genomforande-20260926/riktning/lasning/`, etapp 1)

| # | Fil här | Källa @ full revision | Fil i källan | Byte | git-blob |
|---|---|---|---|---|---|
| 1 | `externa/anthropic-frontend-design-SKILL.md` | `anthropics/claude-plugins-official` @ `fa59bc9037741ecfa131aa27938272605710d7b2` (repo-HEAD 2026-09-25; katalogen senast ändrad i `44490cccaf6d9f82fdeec9416fbf7c9bd72575dc`) | `plugins/frontend-design/skills/frontend-design/SKILL.md` | 9 390 | `a5333457c414d20d625f307df945842c0952ecc3` |
| 2 | `externa/vercel-web-interface-guidelines-command-e3d624ba.md` | `vercel-labs/web-interface-guidelines` @ `e3d624baaf29dc1fc645aff3e38f03e564d2d6b1` (2026-08-18) | `command.md` | 7 760 | `e1e8e3460db7c1440e34642c4f7b885185ca5366` |
| 3 | `externa/addyosmani-web-quality-audit-SKILL.md` | `addyosmani/web-quality-skills` @ `afa8da942115f2961fdbfa80807ea0b232ff6c00` (repo-HEAD 2026-08-24; `skills/` senast ändrad i `c6b06ad1285cd6b129b58455b2eec96ab6b67fa7`) | `skills/web-quality-audit/SKILL.md` | 10 450 | `581ec7c5e8e05e6ac93d99d872906595581efc42` |
| 4 | `externa/addyosmani-accessibility-SKILL.md` | samma som 3 | `skills/accessibility/SKILL.md` | 14 358 | `22a244430f890fe44cbd7a50590d5cbf8528c77b` |
| 5 | `externa/emil-emil-design-eng-SKILL.md` | `emilkowalski/skills` @ `d16ebe60d09a5ba2afcb7054ede9d0a10c9f6128` (repo-HEAD 2026-09-23; `skills/` senast ändrad i `85e8e2363b713506e1d5b6e07a0eb2da66be1bc3`) | `skills/emil-design-eng/SKILL.md` | 27 123 | `62ce902af8dd32c590ea7203e9ab2edb1d6ef81a` |
| 6 | `externa/emil-mobile-native-SKILL.md` | samma som 5 | `skills/mobile-native/SKILL.md` | 16 838 | `94bba21fcb990b850e06effbf5709c96a07446ad` |
| 7 | `externa/emil-prototype-SKILL.md` | samma som 5 | `skills/prototype/SKILL.md` (frontmatter `disable-model-invocation: true`; används som **metod**, alternativ A — ingen skill registreras, ingen spärr ändras, inget manuellt startsteg läggs på ägaren; kedjedrivaren utför variantsteget själv) | 7 830 | `dbcc1a23c66933f7372c0aacbce2b0d7cc6100b6` |
| 8 | `externa/leonxlnx-taste-SKILL-ce26fc25.md` | `Leonxlnx/taste-skill` @ `ce26fc25c0e5e8cab638f883de62d9a86ee5e45b` (repo-HEAD 2026-09-26T09:01Z) | `skills/taste-skill/SKILL.md` (frontmatter `name: design-taste-frontend`; **läsunderlag, ingen skill registreras** — §3 och §5 skriver egna stackkonventioner och kanoniska skelett som skulle styra bygget mot dess mall) | 87 253 | `b72132fcd466da605623ffe96e370b3991fc5285` |

## B. Licensfiler och referensfil (följer med; läses inte per steg)

| Fil här | Gäller | Källa @ revision | Fil i källan | Byte | git-blob |
|---|---|---|---|---|---|
| `externa/anthropic-frontend-design-LICENSE.txt` | 1 | som 1 | `plugins/frontend-design/skills/frontend-design/LICENSE.txt` (Apache-2.0) | 10 174 | `f433b1a53f5b830a205fd2df78e2b34974656c7b` |
| `externa/vercel-web-interface-guidelines-LICENSE-e3d624ba.txt` | 2 | som 2 | `LICENSE` (MIT) | 1 068 | `b3575a3c1358eac4b9ee36a4c851872d81417760` |
| `externa/addyosmani-web-quality-LICENSE.txt` | 3–4 | som 3 | `LICENSE` (MIT) | 1 068 | `90715bb429f374dcc4e05c35535b049d3c077313` |
| `externa/emil-LICENSE.txt` | 5–7 | som 5 | `LICENSE` (MIT) | 1 070 | `57b46f1fd11dc62351ea548104a88aa3f659c11b` |
| `externa/emil-prototype-PICKER-d16ebe60.md` | 7 (referens) | som 5 | `skills/prototype/PICKER.md` — referensmaterial för en live-bläddringsyta; inget krav att bygga den | 7 548 | `aaa88c0eba38eb01c00d4eb2b144e39f808fc26a` |
| `externa/leonxlnx-taste-LICENSE-ce26fc25.txt` | 8 | som 8 | `LICENSE` (MIT) | 1 065 | `48a2f6640b81ff8eca9ce7f6a96337692713ef5b` |

**Följer inte med** (medvetet): accessibility:s `references/A11Y-PATTERNS.md` och `references/WCAG.md`, web-quality-audit:s
`../performance/references/MEASUREMENT.md` och `scripts/analyze.sh` — axe, Lighthouse och den manuella listan täcker
behovet och inga skript körs. Licensvillkoren är lästa, inte juridiskt bedömda.

Kontrollsummor (sha256) för alla fjorton filer och kontrollen mot läsbevisen: `KONTROLL.sha256` och `KONTROLL.txt`.

## C. Egna, härledda arbetsunderlag (skrivna av kedjedrivaren; "härlett ur" med källa och rad står i varje fil)

| Fil här | Härlett ur | Form | Roll | Följer inte med |
|---|---|---|---|---|
| `referensjakt.md` | webbgrundens `skills/nortropic-plan/references/inspirationskallor.md` @ `e4c8c52` (rad 1–60), Norrgläntas brief §5 och jämförelsens §3.3 | metodunderlag | Research: kandidater, budget som frågor, sedd/läst, betyg som filter | — |
| `redaktionellt-pass.md` | copy-blocklistens strukturregler och content-designerns sidregler (webbgrunden @ `e4c8c52`), frontend-design "More on writing in design" (fil 1), Norrgläntas fynd | metodunderlag | Redaktionellt pass (P2) och fråga i granskning D | — |
| `formularsakerhet.md` | webbgrundens `skills/nortropic-prelaunch/references/security-checklist.md` @ `e4c8c52` §3 (rad 70–82), Norrgläntas brief §3 och den riktade kontrollens område 2 | metodunderlag | Bygge av formulär; kodläsningsfrågor i granskning D | — |
| `LARDOMAR.md` | Norrgläntas leverans och riktade kontroll, jämförelsens §2.5, preciseringen | lärdomsfil | Uppstart av nästa fall (P4); klassning och uppföljning | — |
| `beredning.md` | HELHET-20260927 avsnitt 3; det arkiverade repots interventionsbeslut (`agents/project-planner.md` @ `e4c8c52` process 0) och input gate; etablerad metodlitteratur namngiven i filen | metodunderlag | Beredning: elva svar, proportion, metodval efter problem; laddas av kontorets beredning (AP-06 `forvaltning.problem`) | det gamla repots input gate, kapacitetskatalog och maskinläsbara plannerschema (agentbundna) |
| `research-underlag.md` | det arkiverade repots forskningskontrakt v3.1.0 (`skills/nortropic-plan/references/research-kontrakt-v3.md` @ `e4c8c52`), generaliserat; sökintention och kanalobservationer nya | metodunderlag (kontrakt utan pinning) | Research och intervju: ryggrad i 19 sektioner, status per uppgift, faktadisciplin, kontrollrad, användbarhet | hash-pinning av kontraktet, paketmoduler (lokal-se som paket), kapacitetssignaler |
| `juridikflaggor.md` | det arkiverade repots `skills/nortropic-plan/references/juridikflaggor.md` och `nortropic-prelaunch/references/legal-requirements-se.md` @ `e4c8c52` | metodunderlag | Brief §10 och prelaunch: rapportera, aldrig avgöra | modulstatus 'hanterad/ohanterad' som grind; nod-3-stoppet |
| `brief-mall.md` | det arkiverade repots briefstruktur (`agents/project-planner.md` @ `e4c8c52` §1–§7 och kalibreringsprofilen), omgjord till §0–§13 utan fast primärhandling, fast sidmall eller assurance-rad | mall | Brief: mall med bevisregel | fast primärhandling, fast sidmall, assurance-rad, maskinläsbart output-schema |
| `bild.md` | det arkiverade repots `skills/nortropic-bild` (SKILL, behandling.md, slot-schema.md) @ `e4c8c52`; verktygen `verktyg/bild/*.mjs` kopierade därifrån | metodunderlag + körbara verktyg (`verktyg/bild/treatment.mjs`, `brand.mjs`, oförändrade) | Brief §8 och bygge: anspråk, licens, art direction, beskärning, storlekar, optimering | `fetch-images.mjs` (generering via fal.ai), `score.mjs` (poängande gallring), bildbiblioteket utanför repot |
| `bygge-referens.md` | det arkiverade repots `skills/nortropic-stack` (+references), `agents/stack-builder.md`, `nortropic-init` @ `e4c8c52`, generaliserat från fast stack till krav och mönster | metodunderlag | Bygge: krav på resultatet, mönster med skäl, browsergranskning under bygget | fast stack (Next.js 15/Tailwind 4/shadcn), `profile.ts`/`business.ts`-kontrakten, scaffold-skript, arbetsloggens format |
| `copy-kontroll.md` | det arkiverade repots `skills/nortropic-antislop/references/copy-blocklist.md` och `agents/content-designer.md` @ `e4c8c52`, från lag till rapport; verktyget `verktyg/copy_kontroll.py` | metodunderlag + körbart verktyg (`verktyg/copy_kontroll.py`, nyskrivet) | Redaktionellt pass: rapport att rätta eller motivera | poängen och avdragen, content-humanizer-skillen, sentence-case som regel |
| `seo.md` | det arkiverade repots `skills/nortropic-seo-lokal/SKILL.md` @ `e4c8c52`, generaliserat från lokal formel till sökintention och lägen; verktyget `verktyg/seo_kontroll.py` (nyskrivet) | metodunderlag + körbart verktyg | Steget seo: struktur, teknik, strukturerad data som sanning, rapport | "[tjänst] i [stad]" som universell formel; ortssidor som krav; agentens lägen |
| `seo-lokal.md` | samma skill och `packs/lokal-se` @ `e4c8c52` (skärpningar) | metodunderlag (villkorat: lokal/hybrid) | Steget seo när briefen är lokal | paketmaskineriet, grindlinser, `business.ts` som källa (nu VERKSAMHET.json) |
| `sokkonsol.md` | det arkiverade repots `scripts/gsc-setup.mjs` och `gsc-launch-steps.md` @ `e4c8c52`; Googles API-dokumentation (2026-09-27); verktyget `verktyg/sokkonsol.py` (nyskrivet, stdlib) | metodunderlag + körbart verktyg | Steget sokkonsol och lansering | googleapis-beroendet, `verification.ts`-skrivningen, DNS-varianten som standard |
| `lokal-synlighet.md` | det arkiverade repots `gbp-checklist.md` och `swedish-directories.md` @ `e4c8c52`; verktyget `verktyg/lokal_synlighet.py` (nyskrivet) | metodunderlag + körbart verktyg | Steget lokal-synlighet | branschspecifika kategoriexempel som regel; TESTKLIENT-fältet (nu `fiktiv`) |
| `annonser.md` | nyskrivet (fanns inte i det arkiverade repot); Google Ads- och Meta Marketing-API:ernas objektformer; verktyget `verktyg/annonsberedning.py` | metodunderlag + körbart verktyg | Steget annonsberedning | live-överföring (kräver åtkomst som saknas) |
| `uppfoljning.md` | det arkiverade repots spridda mätregler (händelser, Consent Mode, UTM på företagsprofilens länk) @ `e4c8c52`, samlade; verktyget `verktyg/uppfoljning.py` (nyskrivet) | metodunderlag + körbart verktyg | Steget uppfoljning; leveransens bedömningsplan | Vercel Analytics som standardval |
| `prelaunch.md` | det arkiverade repots `skills/nortropic-prelaunch` (Gate 0–7, lighthouse-targets, security-checklist, legal-requirements-se) @ `e4c8c52`; verktyget `verktyg/prelaunch.py` (nyskrivet) | metodunderlag + körbart verktyg | Steget prelaunch | fixloopens rundräknare, agenterna, Vercel-bypass, Resend-konstanter, `profile.ts`-läsningen |
| `lansering.md` | det arkiverade repots `workflows/nortropic-cutover.js` (fas 1–3) och `gsc-launch-steps.md` @ `e4c8c52`; verktyget `verktyg/lansering.py` (nyskrivet) | metodunderlag + körbart verktyg | Steget lansering | de aldrig byggda faserna 4–7 som stubbar; operatörsemitterade kommandon |
| `drift.md` | det arkiverade repots efterförvaltning (steward, retro, final-touches) @ `e4c8c52`, omgjort till driftkontroll utan agenter; verktyget `verktyg/drift_kontroll.py` (nyskrivet) | metodunderlag + körbart verktyg | Steget drift | systemdoktor, nattskift, självförbättringstrappan |
| `kundintervju.md` | ägarens tillägg 2 (2026-09-27, avsnitt 3–4 och 7–8); det arkiverade repots input gate och research-kontraktets §16-frågor som frågebank-underlag @ `e4c8c52`; verktyget `verktyg/intervju.py` (nyskrivet) | metodunderlag + körbart verktyg | Steget intervju: omgångar, följdfrågor, svar ordagrant, fakta med status, motsägelser, avsnitt 19 | nod-3-stoppet, det maskinläsbara plannerschemat, obligatoriskt briefgodkännande |
| `integrationer.md` | ägarens tillägg 2 (avsnitt 6); det arkiverade repots `extern-bokning.md`, lead-server-action-mönstret och Gate 1 @ `e4c8c52`, generaliserade till leveranskrav och kontroller | metodunderlag | Brief §4/§9, bygge, prelaunch grind 1 | Resend/Vercel-konstanter, `/api/puls`, fast primärhandling |
| `webblasare.md` | HELHET-20260927 avsnitt 6; det arkiverade repots qa-launcher-linser och Puppeteer-provarens gränser (D034) som förlaga; Playwright 1.63.0 och @playwright/mcp 0.0.82 (Apache-2.0) pinnade i `verktyg/webblasare/package.json`; verktygen `inspektera.mjs`, `utforska.mjs`, `besok.mjs`, `gemensamt.mjs` (nyskrivna) | körbara verktyg + metodunderlag | Bygge (användning 1), qa (2), provare (3) | chrome-devtools-MCP, agent-browser, den gamla provarens startare (Runtimes provarprofil finns kvar) |
| `referenser-professionella.md` | det arkiverade repots `skills/nortropic-antislop/references/premium-checklist.md` och `premium-bevis.md` @ `e4c8c52` (exemplar verifierade 2026-07-27) | referensbibliotek (valfritt) | Koncept och kritik: jämförelse med motivering, inte kopiering | PK-poängen, F-filtret som grind, design-blocklistan |

## D. Koppling per underlag — steg och utförare · när det läses och vilka delar · uppgift eller kontroll · vid konflikt

| Underlag | Steg och utförare | När det läses; vilka delar | Uppgift eller kontroll | Vid konflikt med brief eller mandat |
|---|---|---|---|---|
| `KEDJA.md` (repots rot) | uppstart, båda utförarna | hela, vid uppstart av ett fall eller en etapp (obligatoriskt i `steg/steg.json`) | kontroll: vad Runtime skyddar mekaniskt och vad sessionen själv bär | beskrivande; ingen konflikt möjlig |
| 1 frontend-design | Brief §7 (kedjedrivaren); bygge; redaktionellt pass | Vid tokenplan och pass 2: "Design principles", "Process: plan, review against the brief, build, critique", "Restraint and self-critique"; vid passet: "More on writing in design" (hela filen är 9 KB) | Tvåpass-syntesen, klusterlistan mot AI-generiska mönster, skrivråden | Briefen och ACCEPT vinner; avvikelsen skrivs i briefens konfliktrad |
| 2 WIG `command.md` | Granskning D (Runtimes läsare); bygge (kedjedrivaren) | Vid kodgranskning: "Accessibility", "Focus States", "Forms", "Animation", "Typography", "Content Handling", "Images", "Hydration Safety", "Anti-patterns (flag these)"; inte "Output Format" | Kodläsningslista för gränssnitt: formulär, fokus, reduced motion, bilder | Ett råd som strider mot ett accepterat krav (t.ex. briefens längdregel) redovisas som förslag och ändrar inget |
| 3 web-quality-audit | Granskning D; mätsteget (kedjedrivaren) | "How it works", "Audit categories", "Severity levels", "Audit output format" (Verification-punkterna); inte "Tool routing" (Chrome DevTools MCP används inte) | Bevistyper (fält, lab, statisk), allvarlighetsgrader, "aggregerad poäng är inte målet" | — |
| 4 accessibility | Granskning D; bygge | "Evidence-led audit workflow", kriterierna under Perceivable–Robust vid behov, "Testing checklist › Manual testing"; automatiken täcks av pinnade axe och Lighthouse | Manuella tillgänglighetskontroller utöver axe: fokusordning, rubriker, namn | ACCEPT:s krav står över |
| 5 emil-design-eng | Bygge, bara när briefens motion-nivå är över `ingen` | "The Animation Decision Framework" 1–4, "Component Building Principles"; inte "Initial Response" eller "Review Format" (skill-krom) | Rörelse med avsikt vid signaturelement; komponentkänsla | Briefens motion-nivå vinner |
| 6 mobile-native | Bygge (kedjedrivaren); granskning D | "The Symptom Table", "The Fixes" 1–11, "Baseline", "Never Ship"; inte "Initial Response", "Output", "Tone" | Mobilkontroll bortom målytor och viewport | — |
| 7 prototype (+ PICKER.md) | Variantsteget P1 (kedjedrivaren), när det görs | "Operating Posture", "Hard Rules" 1–3, "Workflow" fas 1–5; inte "Invocation Variants" (ingen skill) och inte fas 6 (befordran sker genom det vanliga bygget); PICKER.md bara om en live-bläddringsyta efterfrågas | Divergens på namngiven axel, riktigt innehåll, isolerad yta | Briefens fasta mål vinner; varianter rör bara prövbara detaljer |
| 8 Taste | Konceptsteget och komps (kedjedrivaren), etapp 2 och nästa fall | Vid Design Read: §0 "Brief Inference" (0.A–0.D) och §1 "The Three Dials" (1.A–1.C) som en metod bland flera, inte universella värden; före komp: §4.1–4.3 (typografi, färg, layoutdiversifiering) och §4.7–4.8 (layoutdisciplin, bild); inte §2 (designsystemkarta), §3 (stackkonventioner), §5 (kanoniska skelett), §6–9 (dubblerar fil 1, 2 och 4) | En Design Read ur briefen före komparna; axlar och värden efter uppgiften, inga universella; biaskorrigering mot mallmönster | Briefen och ACCEPT vinner; Taste är råd och mall-varning, inte mall |
| `referensjakt.md` | Research (kedjedrivaren) | Hela (kort) | Kandidater, budget som frågor, sedd/läst | — |
| `redaktionellt-pass.md` | Redaktionellt pass (kedjedrivaren); granskning D som fråga | Hela (en sida) | Redaktionell kvalitet och kedjans innebörd | Stöd för bedömning, inte förbud |
| `formularsakerhet.md` | Bygge av formulär (kedjedrivaren); granskning D | Hela (kort) | Honeypot, en klocka, servervalidering, fel | ACCEPT:s demogränser vinner (ingen sändning) |
| `LARDOMAR.md` | Uppstart av nästa fall (kedjedrivaren) | Hela | P4 | — |
| P-C Hallmark (`externa/hallmark-SKILL-13ac0ec7.md`) | Kritik (valfritt; följer med manifestet för designkritik och renderingsläsning) | Kritikröstens metod (S5) | En lins bland flera; fynd bedöms mot KVALITET.md | ingen egen stilregel; briefen vinner |
| P-A design.md (`externa/google-design-md-README-9bf8eae6.md`) | Bygge (valfritt) | "The Format", "lint" | DESIGN.md som riktningsfil i kundrepot; lint med pinnat paket 0.4.0 | formatet beskriver, bestämmer inte |
| `beredning.md` | Beredning (kontorets beredare och kedjedrivaren) | Hela | Elva svar, proportion, metodval efter problem | ägarens accepterade uppdrag vinner |
| `research-underlag.md` | Research; intervju (kedjedrivaren eller Codex) | Hela; referensjakt.md för sektion 13 och 7; vid intervju status per uppgift, sektion 19 och användbarhet | Ryggrad, faktadisciplin, kontrollrad | — |
| `juridikflaggor.md` | Brief §10; prelaunch | Tabellen och reglerna | Flaggor sätts på observation; rapporteras, avgörs av människa | ingen konflikt möjlig: rapport |
| `brief-mall.md` | Brief (kedjedrivaren) | Hela | Briefens §0–§13 med bevisregel | briefens konfliktrad |
| `bild.md` | Brief §8; bygge | Anspråk, val och licens, art direction; vid bygget beskärning, storlekar, verktygen | Bildkompetensens sju delar | kundens rättighetsläge vinner |
| `bygge-referens.md` | Bygge (kedjedrivaren eller Codex) | Hela | Krav på resultatet; mönster med skäl | briefens §9 vinner |
| `copy-kontroll.md` | Redaktionellt pass | Hela | Rapporten rättas eller motiveras | kundens röst vinner med motivering |
| `referenser-professionella.md` | Koncept (valfritt); kritik | Jämförelsedimensionerna och urvalet | Jämförelse med motivering | briefen vinner; ett drag kan vara "gäller inte" |
| `kundintervju.md` | Steget intervju (kedjedrivaren eller Codex) | Hela | Intervju i beställningens kanal; svar ordagrant; fakta med status | ingen konflikt möjlig: kundens svar är kundens; tolkningen märks |
| `integrationer.md` | Brief §4/§9; bygge; prelaunch | Hela; vid prelaunch formulär och leads | Leveranskrav och kontroller per integrationsnivå | briefens §4 vinner; nivån väljs efter behov |
| `webblasare.md` | Bygge; qa; provare (kedjedrivaren eller Codex; besökaren i egen session) | Hela | Tre användningar, tillstånd, gränser, spår, regressionsprov | ingen konflikt möjlig; skärmbilderna avgör layout |
| `seo.md`, `seo-lokal.md` | Steget seo (kedjedrivaren) | Hela; seo-lokal bara vid lokal/hybrid | Struktur, teknik, strukturerad data; rapport ur seo_kontroll.py | briefens §5 vinner |
| `sokkonsol.md` | Steget sokkonsol; lansering | Hela | Plan, live med åtkomst, tolkning | fiktiv verksamhet: vägras |
| `lokal-synlighet.md` | Steget lokal-synlighet | Hela | Datablad, NAP-kontroll | inte tillämpligt utanför lokal räckvidd |
| `annonser.md` | Steget annonsberedning | Hela | Kanalplan → PAUSED-utkast; resultatläsning | inget mandat: ingen spendering |
| `uppfoljning.md` | Steget uppfoljning; leverans | Hela | Mätplan, kontroll mot bygget, läsning | samtycke före spårning |
| `prelaunch.md` | Steget prelaunch | Hela | Åtta grindar som rapport | juridik: människa |
| `lansering.md` | Steget lansering; drift | Hela | Plan, kontroll, återgång | bara med beställning som namnger lansering |
| `drift.md` | Steget drift | Hela | Driftkontroll, incident, beroendeunderhåll | ingen självläkning |

**Laddning per steg** (typisk last): research 1 fil (kort) · brief §5 fil 1 (9 KB) + ev. 7 (8 KB) · bygge 1, 6 (17 KB), ev. 5
(27 KB) och `formularsakerhet.md` · redaktionellt pass `redaktionellt-pass.md` + fil 1:s skrivavsnitt · granskning D 2, 3,
4, 6 som frågor (≈ 49 KB) · uppstart `LARDOMAR.md`, `MANDAT.md`, `ARBETSSATT.md` och `KEDJA.md` (steg.json) · konceptsteg och komps 8 (§0–§1, §4.1–4.3, §4.7–4.8; ≈ 30 KB av 87). Aldrig allt i en
session.

## E. Läge

Alla underlag är **tillgängliga och kopplade** (denna fil). Ingen är **prövad med observerad nytta**; det kan bara
användningsnoter över fall visa. Mottagarprovet (en färsk läsarsession hittar rätt underlag från ordinarie ingång utan
filnamn) redovisas i `MOTTAGARPROV.md` (kontorets ingång 2026-09-26; repots egen ingång 2026-09-27, Claude och Codex).

## F. Installerat och registrerat (etapp 1, DIGITALA-1-TILLAGGSMANDAT-BESLUT-20260926, 2026-09-26)

Formen per resurs är ett nyttoval (regel 7). Hemvistfrågan (kontoret, ett eget repo eller operatörens användarnivå)
var öppen vid installationen och är avgjord genom kontorets beslutspost OMBYGGNAD-20260927 (`docs/decisions.md`): detta repo. Skills på användarnivå och Impeccable i
kundrepot ligger kvar som leveransformer tills en förslagsrad prövar dem. Versioner byts bara som nytt
beslut med ny läsning (regel 4). Råmaterial: `../genomforande-20260926/etapp1/`.

| Resurs | Form | Version eller revision | Plats | Licens | Kontroll |
|---|---|---|---|---|---|
| **frontend-design** (fil 1) | plugin på användarnivå: `claude plugin install frontend-design@claude-plugins-official --scope user` (2.1.280) | marknadsplatsens commit `fa59bc9037741ecfa131aa27938272605710d7b2` = den pinnade läsningen; `plugin.json` bär ingen versionssiffra, så commit-sha:t är versionen | `~/.claude/plugins/cache/claude-plugins-official/frontend-design/fa59bc903774/` (5 filer) | Apache-2.0 | installerad `SKILL.md` byte-identisk med fil 1 (sha256 `d9197063…`); mottagarprov etapp 1: anropad av byggsessionen själv (`frontend-design:frontend-design`) |
| **emil-design-eng** (fil 5) | skill på användarnivå: kopia av fil 5 + `LICENSE.txt` + `KALLA.txt` | `emilkowalski/skills` @ `d16ebe60d09a5ba2afcb7054ede9d0a10c9f6128` | `~/.claude/skills/emil-design-eng/` | MIT | sha256 lika med fil 5 (`ffbe68e6…`); mottagarprov etapp 1: listad som tillgänglig i sessionen, **inte anropad** på uppgiften — anropas uttryckligen (`/emil-design-eng`) när steget kräver det (L14) |
| **mobile-native** (fil 6) | skill på användarnivå, som ovan | som ovan | `~/.claude/skills/mobile-native/` | MIT | sha256 lika med fil 6 (`888b7651…`); tillgänglig, **inte anropad** — anropas uttryckligen (`/mobile-native`) vid mobilkontroll (L14) |
| **Impeccable** | skill i kundrepot som pilot **utan hook** och utan de fyra underagenterna (skillens `reference/degraded/` täcker frånvaron); kopierad ur källrepots `.claude/skills/impeccable/` eftersom npm-paketets (4.1.0) installerare gav HTTP 404 på skillpaketet — release-tillgången `skill-v4.4.0` finns inte, senaste paketrelease är `skill-v4.3.1` (README:s reservväg "Copy from Repository") | `pbakaus/impeccable` @ `9d715cc4f5564a990ca8345abfdd5df6dc9b41c8` = GitHub HEAD 2026-09-26 (noll commits sedan 2026-09-25); skill 4.4.0; motor `engine-v0.1.6` (`scripts/VERSION`) | kundrepots `.claude/skills/impeccable/` (54 filer, 2,1 MB; commit `a963c73`, ingår inte i driftsättningen); motorn hämtad en gång av launchern till `~/.impeccable/bin/0.1.6/`; README:s ignoreblock i kundrepots `.gitignore` | Apache-2.0 | hookmanifestet ur källans `.claude/settings.json` läst och sparat (`etapp1/impeccable-hookmanifest-9d715cc4.settings.json`): SessionStart, PostToolUse på Edit och Write samt Stop kör `scripts/impeccable hook`; hooken är **av** och slås på bara som namngiven ändring; `npx impeccable@4.1.0 detect` modellfritt på byggd HTML vid `ada775e` med stilmallar: 12 varningar (10 `side-tab`, 1 `cramped-padding`, 1 `flat-type-hierarchy`) = golvet (`etapp1/detect-ada775e-med-css.json`); utan stilmallar 7 falska `flat-type-hierarchy` — kör alltid mot en spegel med `_next/static`; `/impeccable init` körd som egen session (98 s, 0,55 USD) med briefens svar i prompten: `PRODUCT.md` (6,3 KB, svenska) skriven i kundrepot utan andra ändringar, live-läge och buildPath inte konfigurerade, tre punkter uttryckligen öppna (pris, mottagande i skarpt läge, fler orter eller tjänster); commit i kundrepot; sessionen körde egna läskommandon (`ls`, `cat`, `head`, `git status`) utöver launchern utan att nekas i acceptEdits-läget — noterat för etapp 3 (`etapp1/impeccable-init-1/UTFALL.md`) |
| **Taste** (fil 8) | läsunderlag i registret, ingen skill | `ce26fc25…` | `externa/` | MIT | git-blob kontrollerad mot källan (`KONTROLL.txt`) |

## G. Etapp 4 — de fyra accepterade proven P-A, P-C, P-D (DIGITALA-1-AGARBESLUT-20260926, 2026-09-27)

Formen per resurs är ett nyttoval (regel 7); versionerna är pinnade (regel 4). Råmaterial och utfall:
`../genomforande-20260926/etapp4/` (UTFALL-ETAPP4.md har användningsnoterna).

| Resurs | Form | Version eller revision | Plats | Kontroll | Användning i etapp 4 |
|---|---|---|---|---|---|
| **P-A @google/design.md** (CLI + format) | paket hämtat med `npm pack`, installerat isolerat med `--ignore-scripts` (93 paket), inget globalt | 0.4.0; tarball sha256 `c23ee409…`; formatets README `google-labs-code/design.md` @ `9bf8eae6` | `../genomforande-20260926/etapp4/verktyg/designmd-run/`; README-kopia `externa/google-design-md-README-9bf8eae6.md` (13 148 byte, sha256 `0cb92429…`) | `lint --format json` 0/0 på etapp 4:s DESIGN.md | riktningsfilen `etapp4/DESIGN.md`; linten fann två föräldralösa tokens och en kontrastvarning |
| **P-C Hallmark** | läsunderlag (SKILL.md) för en kritiksession, ingen skill, inga referensfiler | blob `645221da` (inventeringens pin) | `externa/hallmark-SKILL-13ac0ec7.md` (67 460 byte, sha256 `59469635…`) | git-blob mot inventeringens pin | kritikröst S5 över förhandsvisningen |
| **P-D canvas-design** | läsunderlag, ingen skill | blob `9f63fee8` | `externa/canvas-design-SKILL-33375500.md` (11 939 byte, sha256 `a1f28807…`) | git-blob mot pin | inte tillämpligt: riktningen är ren typografi, ingen egen grafik behövdes |
| **Impeccable detect** | som i F | 4.1.0 (npx) | kundrepot | spegel med `_next/static` | 12 varningar = golvet, inga nya |
