# Kunder — pekare, ingen sanning

Kundens sanning bor hos kunden: research, brief, referenser, bildposter, innehåll och kod i kundens repo och i
kontorets privata kundmapp (`nortropic-projektkontor/evidence/digitala/local/<kund>/`). Nycklar ligger i
`~/.nortropic-hemligheter/<kund>/` med rättighet 600 och skrivs aldrig ut.

Verktygen tar kundmappen som `--kund SÖKVÄG`; den måste ligga utanför detta repo. Kundfiler laddas i klassen `kund`,
aldrig i klassen `profession`, och pinnas inte här.

| Kund | Kundmapp | Kundrepo | Status |
|---|---|---|---|
| Norrglänta Utemiljö (fiktiv kvalitetsdemo) | kontorets `evidence/digitala/local/norrglanta/` | `Nortropic/kund-demo-norrglanta` (privat) | avslutad 2026-09-27: etapp 4 levererad (DIGITALA-1-ETAPP4-RESULTAT-20260927) och godtagen av ägaren som ett första bygge; ägarens ändringar tas till nästa fiktiva fall (DIGITALA-1-AGARBEDOMNING-20260927); av ägaren underkänd som kvalitetsresultat (arbetsordern HELHET-20260927): inte referens, mall eller praxis; tekniska körbevis och felreproduktioner får användas |
