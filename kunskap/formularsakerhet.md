# Formulärsäkerhet — principer för bygge och kodläsning

Härlett underlag (kedjedrivaren, 2026-09-26). Källa: webbgrundens `skills/nortropic-prelaunch/references/security-checklist.md`
@ `e4c8c52`, avsnitt 3 "Formulärmissbruk" (rad 70–82), samt Norrgläntas brief §3 och den riktade kontrollens område 2
(`norrglanta/RIKTAD-KONTROLL-RESULTAT-20260926.md`). Checklistan var skriven för en sajt som skickar leads med mejl;
Digitalas demoregler (ACCEPT) säger att **ingen förfrågan skickas** och att slutbeskedet ska säga det, så punkterna om
mottagare och sändning är principer för en verklig kund, inte krav på demon. Briefen avgör trösklar.

## Principerna (a)–(e), som stöd

| | Princip | Ur källan (rad 74–79, i sak) | I dagens Digitala |
|---|---|---|---|
| a | **Honeypot** | dolt fält; ifyllt → tyst framgång utan åtgärd, boten lär sig inget | `webbplats`-fältet i Norrglänta; prov h |
| b | **Tidsfälla med EN klocka** | *"Förfluten tid MÄTS PÅ EN ENDA KLOCKA (klientens: mount → submit) och skickas som en varaktighet i ms — ALDRIG en rå `startedAt`-tidsstämpel som servern jämför mot sin egen `Date.now()`. Klockskillnad klient/server tappar då riktiga leads tyst."* och *"Jämför aldrig en klientstämpel mot serverns `Date.now()`."* Saknat eller 0-värde (direkt-POST förbi formuläret) är inte ett fynd; fältet är ett botfilter, inte autentisering, och ska fail-open. Källans tröskel 1,5 s med hänsyn till autofyll. | Norrglänta bröt regeln i `2a84fd3` (serverjämförelse av klientstämpel) och rättades i `0f8322a` (`fylltid` = klientmätt varaktighet med `performance.now()`); briefens golv 2,5 s; fail-open vid saknat värde; snabb människa avvisas tyst — redovisad begränsning |
| c | **Servervalidering av alla fält** | längdtak, format, enum | server action med längdtak; briefens längdregel för kontaktfältet är en accepterad begränsning (K1/K2 är förslag) |
| d | **Fast mottagare** | mottagaradress ur miljön, aldrig ur request body — annars ett öppet spam-relay | ej tillämplig på demon (inget skickas); krav för en verklig kund |
| e | **Generiska fel** | klienten får bara generiska felkoder; ingen diagnostik, inga miljönamn | ja; fel förklarar vad besökaren kan göra (se `redaktionellt-pass.md`) |

Rate limiting: plattformsnivå som tillval för en verklig kund; ingen egen databas.

## Kodläsningsfrågor för granskning D (ställs varje gång formulärkoden ändrats)

1. Vilka **klockor** använder koden? Jämförs någonsin en klientstämpel med serverns tid? (Rätt: en varaktighet mätt på
   klientens klocka; fail-open vid saknat värde.)
2. Vilka **antaganden om klient och server** gör koden (hydrering, JavaScript avstängt, dubbla inskick, tillbaka-knappen)?
3. Vilka **felvägar** finns, vad ser besökaren i var och en, och lovar texten något som koden inte gör?
4. Vad kontrollerar **proven faktiskt** — fältvärden eller innebörd? Vilken väg tar en snabb människa, en bot, en
   direkt-POST?
5. Följer erbjudandets innebörd med från valet till slutbeskedet (se `redaktionellt-pass.md` del 2)?

## Lärdom bakom underlaget

Regeln om en klocka fanns två gånger (källans rad 75 och Norrgläntas brief §3) och koden bröt ändå mot den, eftersom inget
steg läste koden mot regeln. En regel hjälper bara om ett steg läser mot den; därför är frågorna ovan bundna till
granskning D, inte till en checklista som bara bockas av.
