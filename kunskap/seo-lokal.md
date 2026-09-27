# Lokal SEO — bara när uppdraget är lokalt

Professionsfil (HELHET-20260927, avsnitt 4), återvunnen ur det arkiverade repots lokala SEO-skill och paketet lokal-se.
Laddas i steget `seo` när briefen §5 anger SEO-läge `lokal` eller `hybrid`. Lokala krav tvingas inte på nationella
eller icke-lokala uppdrag; för `varumärke/portfölj` gäller `seo.md` ensamt.

## Tre ben som bär samma verksamhetsuppgifter

1. **Sajten**: sidor per tjänst och, med genuint innehåll, per ort; `LocalBusiness`-undertyp i strukturerad data ur
   `VERKSAMHET.json` (adressregeln: publik adress → `PostalAddress`; dold → `areaServed`); telefonnumret som läsbar
   text på varje sida; öppettider som är sanna.
2. **Google-företagsprofil**: lokal-synlighet.md (skapas och sköts av behörig människa; aldrig för fiktiv verksamhet).
3. **Citationer och omdömen**: samma NAP i kataloger (hitta.se, eniro.se, Bing Places, Apple Business Connect,
   branschkataloger; auto-poster verifieras, skapas inte); omdömesvägen i lokal-synlighet.md.

## Sökordsstruktur

Sökningar av formen "[tjänst] [ort]" och "[tjänst] i [ort]" är vanliga för lokala tjänster (research §15 visar
vilka som faktiskt gäller); en sida per tjänst med huvudorten, en sida per ort bara med verkligt lokalt innehåll;
long tail i frågor ("vad kostar …", "gäller ROT-avdraget …"). Å, ä och ö behålls i text och rubriker; i adresser
används translitterering (`/omraden/taby`).

## Metadata för lokala sidor (mall, inte lag)

Title: tjänst + ort + verksamhet, omkring 60 tecken. Description: vad, var, ett verkligt belägg (betyg med källa,
fast pris, år) och en kontaktväg, omkring 155 tecken. Inga superlativ.

## Kontroller

`verktyg/seo_kontroll.py --verksamhet VERKSAMHET.json` prövar schema mot verksamhetsuppgifterna;
`verktyg/lokal_synlighet.py kontrollera` prövar NAP över sajtens alla scheman; `verktyg/copy_kontroll.py --krav`
prövar att telefon, organisationsnummer, serviceområde och publik adress står i texten.
