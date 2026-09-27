# Kontroll av scenario {{SCENARIO}} — fylls av kontrollanten, aldrig av provaren

Regel (L20, L22): tre roller i en provrunda — provaren rapporterar, kontrollanten bedömer ur artefakter, en separat
granskare prövar ändringar av gränsen. Raden "observerat slutläge" fylls ur sista skärmbild, sidtext och spårets sista
adress, aldrig ur provarens rapport. Vid varje oväntat tillstånd: vilken handling utlöste det, reproducerad modellfritt
innan fyndet sorteras som produktfel.

| Fält | Värde |
|---|---|
| Körkatalog (Runtimes provarprofil) | {{KORKATALOG}} |
| Kvittots utfall | {{UTFALL}} (klar · tidsgrans · inget_slut · leverantorsfel · ofullstandig_session · start_misslyckades · vagrad) |
| Bindningar (commit, driftsättning, testdata, laddning) | {{BINDNINGAR}} |
| Handlingar: antal, vägrade, gränshändelser | {{HANDLINGAR}} |
| Observerat slutläge (ur artefakter) | {{SLUTLAGE}} |
| Utlösande handling vid oväntat tillstånd | {{UTLOSANDE}} |
| Målen nådda (per mål, ur artefakter) | {{MAL}} |
| Produktfynd (fel att rätta) | {{FEL}} |
| Produktiakttagelser (noteras, inte fel) | {{IAKTTAGELSER}} |
| Verktygsfel (provvägen, inte sajten) | {{VERKTYGSFEL}} |
| Bedömning: lyckat · misslyckat · ej bedömbart | {{BEDOMNING}} |
