# Research — faktaunderlag före brief

Professionsfil (HELHET-20260927, avsnitt 3–4; ägarens tillägg 2, avsnitt 4–5), återvunnen och generaliserad ur det
arkiverade repots forskningskontrakt (v3.1.0). Laddas i steget `research` tillsammans med `referensjakt.md`
(referensjakten är en del av researchen, inte hela) och i steget `intervju`. Kundens research skrivs i kundmappens
`research.md`: den kundspecifika ingången för kvalificerat underlag — vad vi vet och behöver förstå; briefen
motiverar vad vi väljer att göra. Ingen konkurrerande kundsanning: research.md hänvisar till intervjun (avsnitt 19),
VERKSAMHET.json och källfilerna, och de pekar tillbaka.

## Status per nyckeluppgift

Där skillnaden påverkar lösningen bär en uppgift källa, datum och status: `kunden uppger`, `observerat` (egen
observation), `externt belagt` (register, plattform, dokumentation), `tolkning` (vår läsning av en källa), `hypotes`,
`preferens` (kundens önskemål, skilt från fakta och från en beslutad gräns) eller `okänt`. Inte varje mening
registreras — bara det som styr val. Kundens aktuella uppgift ersätts aldrig tyst av gammal webbtext; ett önskemål blir
inte ett externt belagt faktum. Motsägelser bevaras med båda uppgifterna, undersöks och följs upp med en riktad fråga
(intervju.py `fakta`/`avgor`).

## Faktadisciplin

- Belägg per påstående: varje faktauppgift bär en källnot (kundens svar, befintlig sajt, Google-profil, sociala
  kanaler, register, egen sökning, egen observation med datum).
- En uttrycklig uppgift i kundens svar eller material kan användas som `kunden uppger`, med
  exakt källpekare/citat. Att extern kontroll saknas gör inte den uppgiften `okänt`.
  Markera i stället att den inte är oberoende verifierad. `Okänt` gäller det kunden inte
  uppgett eller uttryckligen inte vet; en citerad uppgift får inte samtidigt beskrivas
  som saknad utan ett konkret skäl. Det gäller antal, omfattning och verksamhetsvillkor
  lika väl som namn. Ett källprefix eller vår egen statusetikett bevisar inte kundutsagan:
  läs den bundna källan. Tillagda detaljer utan stöd märks `[OSÄKER]` eller utelämnas.
- Bevara verkliga motsägelser och skilj äldre AI-tolkning från aktuell kundutsaga. Följ
  betalning och andra oundersökta behov som öppna frågor; okänt blir varken nej eller
  ett nytt beställt krav. Kontrollera dessa skillnader före överföring till brief.
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
18. **Kontrollrad** (maskinläsbar; blocket nedan):

```
RESEARCH-KONTROLL v1 | org=<ja|nej> | kontaktvag=<ja|nej> | erbjudande=<ja|nej> | rackvidd=<ja|nej>
| handling=<kandidat|motstridig|OSÄKER> | framgangsmatt=<ja|OSÄKER> | sokintention=<ja|nej|inte tillämpligt>
| osakra=<antal> | konflikter=<antal> | status=<KOMPLETT|OFULLSTÄNDIG>
```

`status=KOMPLETT` kräver `ja` på org, kontaktvag, erbjudande och rackvidd; `osakra` och `konflikter` nollställs
aldrig av sig själva; OFULLSTÄNDIG skrivs överst i filen; ett oundersökt fält är `OSÄKER`, aldrig `nej`.

19. **Intervju och status per uppgift** (sist i filen) — skrivs av `verktyg/intervju.py research`: kanal, omgångar,
    kundens svar ordagrant per område A–H, fakta med status och källa, motsägelser, luckor som påverkar lösningen
    (även ställda frågor utan svar), följdregler som utlöstes, och svaren på de fyra användbarhetsfrågorna: vilken
    uppgift är viktigast; vad måste formuläret åstadkomma efter inskick; vilket befintligt system ska ta emot; vad vet
    vi ännu inte. Testdialoger märks.

## Användbarhet, inte rubriker

Research.md är klar för brief när den kan besvara: vilken uppgift är viktigast för besökaren och verksamheten; vad
formuläret (eller bokningen) måste åstadkomma efter inskick och vilket system som tar emot; vilka kanaler som är
relevanta för just denna kund; vad som är tillräckligt utrett, inte tillämpligt, motsägelsefullt eller ännu okänt.
Geografisk räckvidd, kontaktkanaler och integrationer beskrivs för den aktuella kunden, inte efter ett tidigare
falls modell. Nya kundsvar slår igenom i berörda slutsatser, brief, implementation och prov; tidigare versioner bevaras
(fallets `overforing-*/fore/research.md` via ordinarie överföring; äldre research-rN.md bevaras), och ett uppdaterat research.md lämnar inga gamla antaganden styrande.

## Skärpningar när uppdraget är lokalt

Gäller bara när sektion 5 visar lokal eller regional räckvidd med fysisk närvaro: NAP (namn, adress, telefon) exakt
lika i alla kanaler; lokala kvitton (fysisk plats, lokala omdömen, lokala samarbeten); bokningsvägen; säsong.
Lokala krav tvingas inte på nationella eller icke-lokala uppdrag.

## Vad research aldrig gör

Ingen strategi, ingen juridisk bedömning, ingen bildnedladdning utan rättighetsläge, ingen kontakt med kundens
kunder, inga inskick, inga nya konton. Research pinnas inte här: kundens `research.md` bor i kundmappen.
