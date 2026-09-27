# Drift och förbättring — övervakning, incident, beroendeunderhåll, återgång

Professionsfil (HELHET-20260927, avsnitt 4 "Leverans, drift och förbättring"). Laddas i steget `drift`. Verktyg:
`verktyg/drift_kontroll.py` (läsande kontroll med kvitto, exit 1 vid incident). Förmågorna kopplas till befintlig
Runtime och kunduppdrag, inte till månadsrubriker som kräver att någon minns dem.

## Vad som faktiskt körs

- **Driftkontroll** per lanserad sajt (`DRIFT.json` i kundmappen: adresser, förväntad text, svarstidsgräns, sitemap,
  certifikatets minsta återstående dagar). Körs av hand (`drift_kontroll.py --plan … --ut …`) eller schemalagt.
  **Schemaläggning (2026-09-27):** Runtimes schemalagda körning (AP-10) finns för kontorets bevakning; en
  motsvarande schemalagd driftkontroll för Digitala är ett namngivet återstående steg i etapp 5 (Runtime-kandidat),
  inte något som redan sker. Tills dess körs kontrollen av sessionen vid varje ordinarie rytm (KEDJA.md).
- **Vad som händer när värdmaskinen är otillgänglig:** ingen kontroll körs och inget larm kommer; sajten ligger
  hos värdplattformen och påverkas inte. När en integration är otillgänglig (sökkonsol, plattform) skriver
  kontrollen incident med felklass; ingen automatisk åtgärd.

## Mandat

Inom stående mandat: kontroll, diagnos och rapport. Ändringar (beroendeuppdatering som driftsätts, återgång,
ompekning av domän, innehållsrättelser) kräver beställning eller den underhållsform ägaren beslutar (MANDAT.md §2–§3);
en akut återgång vid incident förbereds som förslag med kommandon och verkställs enligt samma regel.

## Incident

Kvitto → läs felet → värdplattformens status → återgång enligt lansering.md om innehållet eller driftsättningen är
orsaken → not i `ARBETSLOGG.md` → kunden informeras enligt avtal. Ingen självläkning i kod.

## Beroendeunderhåll

Månadsvis i kundrepot (kontroll inom stående mandat, åtgärd enligt Mandat ovan): `npm audit` (high/critical
rapporteras och åtgärdas när mandat finns), pinnade versioner uppdateras i egen gren med förhandsvisning, prelaunch-grind
0, 2, 4 och 7 körs om före driftsättning; Runtimes egna verktygspinnar byts bara
genom Runtimes releaseväg.

## Kontinuerlig förbättring

Uppföljningens återkoppling (uppfoljning.md) ger hypoteser; varje ändring går genom samma kedja (brief-tillägg,
bygge, kontroll, prelaunch-delgrind, driftsättning) i proportion till ändringen (ARBETSSATT.md); resultatet följs
upp och skrivs som lärdom med klass (LARDOMAR.md). Fungerande arbete bevaras; återgångsvägen finns alltid.
