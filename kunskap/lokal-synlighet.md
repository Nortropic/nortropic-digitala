# Lokal synlighet — Google-företagsprofil, kataloger och omdömen

Professionsfil (HELHET-20260927, avsnitt 4 "Google Business Profile och lokal synlighet"), återvunnen ur det
arkiverade repots profilchecklista och kataloglista. Laddas i steget `lokal-synlighet`. Verktyg:
`verktyg/lokal_synlighet.py` (datablad ur verksamhetsuppgifterna; NAP-kontroll mot sajten).

## Tillämplighet först

Tillämpligt vid lokal eller regional räckvidd (fysisk plats eller serviceområde). Inte tillämpligt vid nationell
eller gränsöverskridande räckvidd utan lokal förankring. Förbjudet för fiktiva verksamheter: ingen verklig profil,
inga citationer, inga omdömesförfrågningar (ordern avsnitt 4; `fiktiv: true`). Tillämpligheten skrivs i briefen §5.

## Behörig åtkomstväg

Profilen skapas, görs anspråk på och verifieras av en behörig människa i business.google.com med kundens Google-konto
som primär ägare; kontoret som hanterare vid avtal. Business Profile API kräver ett godkänt Google Cloud-projekt och
används inte för att skapa profiler; **ingen sådan åtkomst finns (2026-09-27)** och den behövs inte för
databladet och kontrollerna. Verifiering (vykort, telefon, video) tar dagar till veckor: börja tidigt.

## Korrekta uppgifter (samma som på sajten)

Namn exakt som verksamheten heter (ingen nyckelordsstoppning); primär kategori = den exakta branschkategorin,
sekundära bara genuint tillämpliga; adress exakt som sajten eller dold med serviceområden per ort; telefon = sajtens
nummer (inget spårningsnummer); öppettider som sajten, jour bara om bemannad, helgdagar angivna; tjänster ur sajtens
tjänstesidor; beskrivning ur briefen (750 tecken, de första 250 bär budskapet); bilder: logotyp, omslag, personer,
lokal eller fordon, utfört arbete — verkliga foton med rättigheter (bild.md); länkar: webbplats (UTM-märkt om
mätverktyget läser UTM) och kontakt- eller bokningssida.

## Citationer

Samma NAP överallt, kopierad ur `VERKSAMHET.json`. Nivå 1: Google-företagsprofil, hitta.se, eniro.se, Bing Places,
Apple Business Connect. Nivå 2 (branschberoende): reco.se, branschorganisationers register, betalda leadtjänster bara
om kunden redan använder dem. Nivå 3 (auto-poster ur Bolagsverket/SCB): allabolag, merinfo, proff, ratsit — verifiera
adress, SNI-kod och webbadress; skapa inte.

## Omdömen

Direktlänk från profilen till kunden (faktura, SMS, QR); be i leveransögonblicket; svara inom sju dagar på svenska,
sakligt vid kritik; aldrig incitament, urval eller köpta omdömen (Googles policy och marknadsföringslagen). Sajten
visar riktigt aggregat och namngivna citat bara med tillstånd; betyg utan källa visas inte.

## Uppföljning

Efter lansering minst ett inlägg per månad; insikter (samtal, vägbeskrivningar, webbklick) månadsvis in i
kunduppföljningen (uppfoljning.md); kvartalsvis NAP-audit: sök företagsnamn + ort och telefonnumret i citattecken,
rätta vid källkatalogen. Varningstecken: nyckelordsstoppat namn, virtuell adress, dubbla profiler, kategoribyten,
recensioner i klump.
