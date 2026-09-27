# Bygge — referens för produktion (val, inte fast stack)

Professionsfil (HELHET-20260927, avsnitt 4 "Produktion"), återvunnen och generaliserad ur det arkiverade repots
stack- och initskills. Laddas i steget `bygge`. Ingen fast stack: valet motiveras i briefen §9 av uppgiften,
kundens förvaltning och driftmiljön. Det som följer är krav på resultatet och beprövade mönster.

## Krav på resultatet (oavsett stack)

- Semantisk HTML (landmärken, rubrikordning, listor, knappar som knappar, länkar som länkar); `<html lang="sv">`.
- Responsivt utan horisontell spill i 320–1920 px; layoutvyns bredd lika med fönstret på mobil.
- Tangentbord: allt nåbart och användbart; synligt fokus; hopp-länk; meny och dialoger stängs med Escape.
- Tillgänglighet WCAG 2.2 AA som krav (axe utan violations är nödvändigt, inte tillräckligt; manuella kontroller
  enligt `externa/addyosmani-accessibility-SKILL.md`).
- Prestanda: Core Web Vitals-mål (LCP < 2,5 s, CLS < 0,1, INP < 200 ms) på mobil; bilder med mått, AVIF/WebP,
  första vyns bild prioriterad; typsnitt självhostade (högst två familjer); ingen tredjeparts-CDN för typsnitt.
- Säkerhet: säkerhetsrubriker (Content-Security-Policy, Strict-Transport-Security, X-Content-Type-Options,
  Referrer-Policy, frame-ancestors), inga hemligheter i klientbunten, servervalidering av varje formulärfält,
  formulärskydd enligt `formularsakerhet.md`, beroenden granskade (`npm audit` utan high/critical i produktion).
- Formulär: fält motiverade i briefen §4; fel-, tom- och laddningslägen; alternativ kontaktväg vid fel; leverans
  till mottagare ur miljövariabel (namn i briefen, aldrig värden i repot).
- Innehållsmodell efter behov: när kunden ska redigera själv, en innehållskälla (filer eller CMS) med dokumenterat
  redigeringsflöde; annars innehåll som data i repot, inte inbakat i komponenter.
- Sammanhängande övergångar och rörelse enligt briefens motion-nivå; `prefers-reduced-motion` respekteras alltid.
- Fel- och 404-sidor på svenska med kontaktväg.

## Beprövade mönster (välj med skäl)

- **Statisk eller hybrid sajt** (t.ex. Next.js med statisk generering, Astro): innehåll som data, sidor genererade,
  formulär som serverfunktion. Passar de flesta informations- och kontaktsajter.
- **Innehållsmodell**: en typ per innehållsslag (tjänst, område, person, omdöme, fråga) med fält; varje sida byggs
  ur typerna; inga sidor utan genuint innehåll.
- **Formulärleverans**: serverfunktion → e-posttjänst (mottagare `LEAD_TO_EMAIL`, avsändare `LEAD_FROM_EMAIL` på
  verifierad domän, nyckel `RESEND_API_KEY` eller motsvarande) med honeypot, tidsfälla på en klocka och
  servervalidering; leveransen är testet, inte svarskoden.
- **Miljövariabler**: dokumenterade i `.env.example` med namn och ändamål; värden bara i värdplattformen;
  `NEXT_PUBLIC_`-prefix bara för det som får nå klienten.
- **Analys och samtycke**: kakfri analys utan samtyckesruta; GA4/pixlar bara efter samtycke (Consent Mode v2, nekat
  som standard); serverbaserad spårning är ingen genväg runt samtycket.
- **Förhandsvisning och lansering**: förhandsvisning bakom skydd och `noindex`; lanseringskonfiguration skild
  (`lansering.md`); domän, canonical och sitemap växlar vid lansering, inte före.
- **GitHub-först**: kundrepot privat under organisationen; huvudgren skyddad; driftsättning från huvudgren;
  förhandsvisning per gren.

## Riktningsfil och lint

Briefens §7 skrivs som `DESIGN.md` i kundrepot (formatet `@google/design.md`, README i `kunskap/externa/`), så att
tokens, typografi, färg och komponentregler är läsbara för varje utförare; `npx -p @google/design.md@0.4.0 designmd lint
--format json DESIGN.md` hittar föräldralösa tokens och kontrastvarningar (etapp 4 fann två tokens och en varning).
Formatet beskriver riktningen; det bestämmer den inte.

## Browsergranskning under bygget

Rendera och interagera i riktig webbläsare medan du bygger, inte bara efteråt: första vyn i 390 och 1440,
tangentbordsväg genom menyn och formuläret, felvägar, konsol och nätverk (`verktyg/webblasare/`, HELHET etapp 4).
Skärmbilder kompletterar interaktionen; ett textträd är inte bildseende.

## Arbetslogg

Byggets beslut (vad som valdes, varför, vad som förkastades) skrivs kort i kundrepots `ARBETSLOGG.md` per steg, så
att en annan utförare kan fortsätta (etapp 5: start/fortsätt-vägen läser den).
