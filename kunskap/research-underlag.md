# Research — faktaunderlag före brief

Professionsfil (HELHET-20260927, avsnitt 3–4), återvunnen och generaliserad ur det arkiverade repots
forskningskontrakt (v3.1.0). Laddas i steget `research` tillsammans med `referensjakt.md` (referensjakten är en del av
researchen, inte hela). Kundens research skrivs i kundmappens `research.md`.

## Faktadisciplin

- Belägg per påstående: varje faktauppgift bär en källnot (kundens svar, befintlig sajt, Google-profil, sociala
  kanaler, register, egen sökning, egen observation med datum).
- Allt obelagt märks `[OSÄKER]`. Konflikter mellan källor registreras som konflikter, aldrig tyst upplösta.
- Research är skrivskyddad: inga formulär skickas, inga meddelanden till kundens kunder, inga kontoinloggningar,
  inga inköp. Främmande sajter renderas och läses; observationer fabriceras aldrig ("kunde inte öppnas" är ett svar).
- Fakta är inte strategi: research svarar på vad som är, briefen på vad som ska göras.
- Kundens material som är skyddat (adresser till skyddade förhandsvisningar, nycklar) skrivs aldrig in i research.

## Ryggraden — sektioner i fast ordning

Numreringen är stabil; ett fall får lägga till underrubriker, aldrig ta bort en sektion (skriv "inte tillämpligt"
eller "inte undersökt").

1. **Organisation och typade kontaktvägar.** Juridiskt namn, organisationsform, organisationsnummer om det finns;
   varje kontaktväg typad (telefon · formulär · direktmeddelande · bokningssystem · fysisk plats) med belägg;
   adressens roll (verksamhetsställe, besöksadress, enbart registrerad hemvist) och om adressen får visas.
2. **Erbjudande** i organisationens egna ord.
3. **Användare och målgrupper** — vilka som faktiskt kommer, med belägg; segment som antas märks.
4. **Toppuppgifter och handlingskandidater** — vad besökaren vill göra; kandidater till sajtens viktigaste
   handlingar med belägg; motstridiga signaler: båda noteras.
5. **Räckvidd och språk** — geografisk räckvidd och dess roll (arbetsområde, marknad, enbart hemvist); nationell
   eller gränsöverskridande räckvidd är ett giltigt svar; språk.
6. **Förtroende och evidens** — de kvitton som faktiskt bär förtroende i just denna verksamhet (certifikat,
   utbildning, försäkring, garanti, omdömen med plattform och exakt antal, portfölj, år, kundcase, partner) med
   bevisformat; saknas kvitton skrivs bevisläget ut; meriter lånas aldrig.
7. **Innehåll och bildmaterial** — befintliga texter; bildinventering (antal, användbara, motivtyper, liggande
   kandidater för första vyn, porträtt); rättighetsläget alltid; vad som kräver original från kunden.
8. **Röst** — 1–2 exempel ur kundens egna texter, 2–3 exempel på branschens språk.
9. **Transaktioner och data** — betalning, bokning, inloggning, personuppgifter, som rå observation.
10. **Integrationer** — bokning, kassa, CRM, nyhetsbrev, kartor, befintliga verktyg.
11. **Juridik- och riskobservationer** — råa observationer med citat (hälsa/kropp, livsmedel, finans/försäkring,
    barn som målgrupp, alkohol/tobak, e-handel, medlemsdata/inloggning); bedömningen görs inte här utan mot
    `juridikflaggor.md` i briefen.
12. **Konkurrenter och alternativ** — 2–3 faktiska alternativ (konkurrent, annan lösningsklass, att inte göra
    något) med adress, en mening om styrka/svaghet och synligt anseende; frånvaro skrivs ut.
13. **Designreferenser** — kundens egna och egen jakt enligt `referensjakt.md`; per referens adress och 2–3
    meningars motivering knuten till denna kunds material och röst.
14. **Framgångsmått** — mätbart; affärsutfall skilt från användarutfall.
15. **Sökintention** — vilka sökningar som gjordes (ordagrant), vilken avsikt de visar (informations-, navigations-,
    transaktionssökning, lokal), vad resultatsidan innehåller (lokala paket, frågor, kartor, annonser), vilka
    sidor som svarar mot vilken avsikt. Inga rankningslöften; ingen uppskattning av sökvolym utan verktyg och källa.
16. **Kanalobservationer** — var målgruppen faktiskt finns; befintlig Google-företagsprofil (finns/verifierad/ägs av
    vem), sociala kanaler (aktivitet), annonsering som syns, e-post/nyhetsbrev; observationer, inte planer.
17. **Öppna frågor** — allt `[OSÄKER]` samt standardfrågorna: vilka omdömen eller referenser får publiceras och med
    vilken attribution; finns högupplösta original och godkännande; domänönskemål; bokningskanal; för nystartade:
    vilka löften vågar verksamheten stå för.
18. **Kontrollrad** (maskinläsbar, sist i filen):

```
RESEARCH-KONTROLL v1 | org=<ja|nej> | kontaktvag=<ja|nej> | erbjudande=<ja|nej> | rackvidd=<ja|nej>
| handling=<kandidat|motstridig|OSÄKER> | framgangsmatt=<ja|OSÄKER> | sokintention=<ja|nej|inte tillämpligt>
| osakra=<antal> | konflikter=<antal> | status=<KOMPLETT|OFULLSTÄNDIG>
```

`status=KOMPLETT` kräver `ja` på org, kontaktvag, erbjudande och rackvidd; `osakra` och `konflikter` nollställs
aldrig av sig själva; OFULLSTÄNDIG skrivs överst i filen; ett oundersökt fält är `OSÄKER`, aldrig `nej`.

## Skärpningar när uppdraget är lokalt

Gäller bara när sektion 5 visar lokal eller regional räckvidd med fysisk närvaro: NAP (namn, adress, telefon) exakt
lika i alla kanaler; lokala kvitton (fysisk plats, lokala omdömen, lokala samarbeten); bokningsvägen; säsong.
Lokala krav tvingas inte på nationella eller icke-lokala uppdrag.

## Vad research aldrig gör

Ingen strategi, ingen juridisk bedömning, ingen bildnedladdning utan rättighetsläge, ingen kontakt med kundens
kunder, inga inskick, inga nya konton. Research pinnas inte här: kundens `research.md` bor i kundmappen.
