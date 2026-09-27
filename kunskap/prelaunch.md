# Prelaunch — åtta grindar före lansering, som rapport med belägg

Professionsfil (HELHET-20260927, avsnitt 4 "Leverans"), återvunnen ur det arkiverade repots prelaunch-skill utan dess
fixloop-räknare, agenter och Vercel-specifika steg. Laddas i steget `prelaunch`. Verktyg: `verktyg/prelaunch.py`.
Varje grind får PASS, FAIL, EJ_MATT eller MANNISKA; EJ_MATT är inte PASS; verktyget godkänner aldrig juridik. Gröna
verktygsprov bevisar inte mänsklig användbarhet eller affärsresultat.

| Grind | Vad som prövas | Belägg |
|---|---|---|
| 0 byggintegritet | bygget finns och renderar; inga platshållare (lorem ipsum, TODO-markörer, `[OSÄKER]`); inga hemligheter i bygget; `.env.example` dokumenterar miljövariabler | bygget, repot |
| 1 viktiga handlingar | varje handling ur briefen §4 prövad från början till slut (formulär → leverans till mottagare; länk → samtal; bokning → extern tjänst nådd); felväg visar alternativ | `HANDLINGAR.json` med provkvitton (Runtimes provarprofil eller manuellt prov med datum) |
| 2 prestanda | Lighthouse mobil mot kravnivån i briefen (standard: prestanda ≥ 90, tillgänglighet, best practices, SEO ≥ 95), LCP < 2,5 s, CLS < 0,1; INP mäts inte av navigations-Lighthouse (EJ_MATT tills fältdata) | Runtimes mätkvitto |
| 3 responsivitet | vyerna ur mätprofilen utan horisontell spill; layout bedömd i skärmbilder (390, 768, 1280 och fler efter behov) | mätkvitto + skärmbilder |
| 4 tillgänglighet | axe utan violations i varje vy; manuella kontroller (tangentbord, fokus, kontrast, alt, formulärfel, rörelse) | mätkvitto + manuell notering |
| 5 SEO-beredskap | `seo_kontroll.py` utan fynd i rätt läge (förhandsvisning: noindex; lansering: index) | SEO-rapporten |
| 6 juridik | basen och satta flaggor (juridikflaggor.md); rapporteras, avgörs av människa | `JURIDIK.json` + människans beslut |
| 7 säkerhet | säkerhetsrubriker (CSP med frame-ancestors, HSTS, nosniff, Referrer-Policy), beroenden utan high/critical (`npm audit`), formulärskydd (formularsakerhet.md), inga nycklar i bunten | svarshuvuden (sparade eller live), auditfil |

Helheten är "redo" bara när grind 0–5 och 7 är PASS, JURIDIK.json är lämnad (människans genomgång av basen och
flaggorna) och juridiken saknar ohanterade flaggor. Ett underkännande
går till diagnos → åtgärd → omprov av den berörda grinden (KVALITET.md:s loop), inte till ett ägarstopp.
