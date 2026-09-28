# Konsekvensgranskning — rätt underlag för ändringen

Vid omprov, skriv kundens GRANSKNINGSFOKUS.md före granskningen. Den är en läsanvisning, aldrig dispens:

- Vad ändras, från vilken kandidat till vilken, exakt diff och kandidat-/miljö-/konfigurationsbindning?
- Vilka behov, sidor, tillstånd, språk, dataflöden och gemensamma komponenter påverkas direkt eller indirekt?
- Vilka tidigare domar/bevis finns, på vilka bytes och med vilka uttryckliga begränsningar?
- Vad behöver öppnas, köras eller granskas igen och varför? Vad kan återanvändas med verklig byte-/beroendeanalys?
- Vilka osäkerheter och tidigare invändningar är öppna? Var finns fördjupningen om granskaren behöver den?

Börja med ett litet kärnpaket: behov/mandat, kandidat/diff, berörda verkliga bilder och beteendebevis, relevanta
referenser, kriterier och frågan. Lägg inte in hela drift-/systemhistoriken utan betydelse för ändringen.
En gemensam layout-/stateändring kan påverka många vyer; liten diff betyder inte liten konsekvens.

Produktens fördefinierade BEVISKRAV och quality-v2-bindning gäller fortfarande. Byt inte produkt mot komp
eller skriv N/A för att minska paketet. En snäv konsekvensdom är just snäv och ersätter inte en saknad
helhetsbedömning. Bildmottagning, formgiltig JSON och filantal är inte professionellt godkännande.

Granskaren får ifrågasätta räckvidden och begära nödvändigt underlag. Behåll avvisat/ej bedömbart synligt;
komplettera den identifierade luckan i stället för att blint upprepa samma fulla paket. Separera produkt,
kod och rapport samt tekniska minima, professionell ambition och verklig användarnytta.
