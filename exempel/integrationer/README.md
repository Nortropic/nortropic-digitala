# Körbara standardexempel

Python 3.9+, endast standardbibliotek. Ingen paketinstallation, inget nytt konto.
Kör från Digitala-repots rot. Sätt `PROV` till en egen privat katalog **utanför
Git-repot**. Exempellänkarna måste ersättas; de är inte registrerade konton.

```sh
PROV=/absolut/privat/prov-integrationer
python3 -B verktyg/integrationer.py plan --val exempel/integrationer/VAL.json --ut "$PROV/val"
python3 -B exempel/integrationer/server.py --inkorg "$PROV/inbox.sqlite" --port 3182
```

Öppna `http://127.0.0.1:3182` och använd endast syntetiska uppgifter. Formuläret
valideras på servern, sparar först och ger ett sant besked. Om ett svar försvinner
kan samma uppgifter skickas med samma idempotensnyckel; ändrad kropp ger 409.
Webbservern är uttryckligen en lokal demonstration. Biblioteksfunktionerna importeras
i kundens vanliga server, med dennas lagring, trafikskydd, loggning och rättigheter.
Demot har inga produktionsroller, ingen antispamtjänst och ingen extern avisering.

Ett motsvarande körbart HTTP-anrop:

```sh
curl --fail-with-body http://127.0.0.1:3182/lead \
  -H 'Origin: http://127.0.0.1:3182' -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: eget-syntetiskt-prov-1' \
  --data '{"name":"Testperson","email":"test@example.invalid","message":"Endast eget syntetiskt prov"}'
python3 -B verktyg/integrationer.py crm-export --inkorg "$PROV/inbox.sqlite" --ut "$PROV/crm.csv"
```

En export är inte leverans till ett CRM. `source_id` är importnyckeln; mappa
ansvarig och uppföljning till det befintliga systemets fält och återläs där.
CSV skyddar mot formelinjektion men kundens importer kan ha egna regler.

## Resend: begränsad verklig tjänsteväg

Endast efter att befintlig åtkomst och testmottagning kvalificerats. Rånyckelfilen
ska vara 0600 utanför repot; innehållet anges aldrig i argument eller loggar.
En API-testförfrågan räknas mot leverantörens mejlkvot.

```sh
python3 -B verktyg/integrationer.py resend-test \
  --nyckel-fil /privat/RESEND_TEST.secret --konto kundens-testkonto \
  --journal "$PROV/resend.sqlite" --idempotens eget-notisprov-1 \
  --mottagare delivered@resend.dev --aterlas --ut "$PROV/resend-1.json"
```

Vill du prova hela sparad-fråga → testnotis, lägg till `--inkorg
"$PROV/inbox.sqlite" --lead-key eget-syntetiskt-prov-1 --ansvarig Provansvarig`.
Det kräver att just frågan är lagrad. Endast en hashreferens läggs i testmejlet;
personuppgifter kopieras inte. Ansvarig måste motsvara serverns konfiguration.

Kör samma kommando med en **ny kvittofil** för senare återläsning. Accepterad
journalpost skickas inte igen. Vid okänt tidigare utfall kan `--retry-okant`
användas med samma nyckel/kropp; ändrat innehåll och för gammal osäker post vägras.
`provider_accepted`, `delivered_test` och `received_by_person:false` är olika
uppgifter. E-post till kundens riktiga mottagare är inte implementerad av denna
testadapter och får inte utlovas från provet.

## Stripe: leverantörskassa, ingen egen reservation

En redan skapad test-Payment Link kan användas via `plan`. När en kundreferens
behövs skapas en hostad Checkout-session från ett **befintligt testpris**:

```sh
python3 -B verktyg/integrationer.py stripe-checkout-test \
  --nyckel-fil /privat/STRIPE_TEST.secret --konto kundens-sandbox \
  --version 2025-08-27.basil --pris price_ERSATT_MED_TESTPRIS \
  --success-url https://kundens-testhost.example/tack \
  --cancel-url https://kundens-testhost.example/avbrutet \
  --journal "$PROV/stripe.sqlite" --idempotens test-order-1 --ut "$PROV/checkout-1.json"
```

Versionen ovan är en explicit exempelpinnning, inte ett påstående om kontots
senaste version. Välj en stödd version från kontot och bind webhooken till samma
kontrakt. Kassa/retur-URL skapas men inget kort provas av CLI:t. Öppna testkassan
och prova leverantörens dokumenterade testkort för lyckat/avvisat/avbrutet flöde;
återläs därefter samma session. Inget av dessa steg kan ersättas med fixtureutfall.
Förnyad CLI-körning med samma argument och ny kvittofil återanvänder sessionen.
`paid:false` efter `complete` är möjligt. Fulfilment ingår inte i inkorgen.

## Cal: använd bokningstjänstens hela kundresa

Beredd Cal-länk leder till dess bokningsvy. I ett kvalificerat testevent: boka,
kontrollera kalender och bekräftelse, omboka via dess länk och avboka. Spara
faktiska UI-/kalender-/meddelandebevis för varje led. API-återläsningen är separat:

```sh
python3 -B verktyg/integrationer.py cal-aterlas \
  --nyckel-fil /privat/CAL_TEST.secret --uid-fil /privat/BOOKING_UID.secret \
  --konto kundens-testkonto --version 2024-08-13 --ut "$PROV/cal-1.json"
```

UID behandlas som en åtkomsthemlighet och ligger i egen 0600-fil. Standardversionen
ska stämmas mot den valda endpointens aktuella dokumentation. Ingen bokning skapas
av detta kommando. Gruppkapacitet, personalpooler och kalenderkonflikter måste
prövas om de faktiskt behövs; en attendees-array får inte användas som totalsaldo.

## Signerade webhooks

Starta loopbackservern med `--webhook-config /privat/webhooks.json` för lokala
kontraktsprov. Konfigfilen ska vara 0600; verkliga leverantörer behöver en HTTPS-
adress hos kundens host eller sin officiella testforwarder. Ingen tunnel eller
leverantörsregistrering skapas här. Bibliotekets `webhook(provider, raw, headers,
config)` och `Inkorg.receive(event)` kan monteras i befintlig hostad app.

Konfigurationens form (platshållare, aldrig faktisk hemlighet i repo):

```json
{
  "cal": {"secret":"ERSATT_MED_HEMLIGHET", "version":"2021-10-20", "event_type_id":123},
  "stripe": {"secret":"ERSATT_MED_HEMLIGHET", "api_version":"2025-08-27.basil", "reference_prefix":"test-"},
  "tally": {"secret":"ERSATT_MED_HEMLIGHET", "form_id":"ERSATT", "owner":"Provansvarig", "follow_up":"Nästa arbetsdag", "fields":{"name":"question_name","email":"question_email","message":"question_message"}}
}
```

Bevara råa request-bytes fram till signaturkontrollen. Endpoints är
`/webhook/cal`, `/webhook/stripe`, `/webhook/tally`. Tally-payloaden motsvarar dess
JSON.stringify-serialisering: ändra inte mellanslag/tal innan kontroll. Cal är
pinnad till äldre, fortfarande dokumenterade standardpayload `2021-10-20`;
den nya `2026-07-27` eller egna mallar vägras avsiktligt tills de kvalificerats.
Stripe accepterar bara test-Checkout-event för den egna kontodestinationen,
inte Connect/Thin Events. Händelser lagras utan att hävda leverans eller senaste
status; dubblett är 200, samma event-id med ändrat innehåll är 409. Tallys
submissionslänkar med token sparas aldrig i inkorgen.

## Befintliga kanalverktyg

```sh
python3 -B verktyg/integrationer.py kanal matning utm --url https://example.invalid/kontakt --kalla google --medium cpc --kampanj prov
python3 -B verktyg/integrationer.py kanal gsc --help
python3 -B verktyg/integrationer.py kanal gbp --help
python3 -B verktyg/integrationer.py kanal annonser --help
python3 -B verktyg/integrationer.py kanal seo --help
```

De är direktdelegat till befintlig kod och behåller dess spärrar. Google/Meta
har redan PAUSED-adaptrar; denna modul skapar ingen ersättare. GBP-vägen skapar
datablad och kontrollerar lämplighet, inte ett falskt kvitto på publicerad profil.

## Regression och känd provgräns

```sh
python3 -B -m unittest discover -s verktyg -p 'test_integrationer.py' -v
```

Proven omfattar faktiska lokala HTTP-svar/SQLite-fel och kontraktsdubbler för
externa API:er. De skapar aldrig leverantörsobjekt. Positiva/negativa prov skiljer
bl.a. ogiltig signatur, annan form/version, dubblett, ändrad nyckel, okänt svar,
retryfönster, 429, fel identitet och syntetisk leverans från riktig personmottagning.
Ett sådant kvitto är inte ett test av Cal/Stripe/Tallys konto eller UI.

Kunddrift kräver kundens verkliga host, beständig lagring, åtkomst/ägarskap,
gallring, reservkontakt, övervakning och återgång. Lokalservern saknar
produktionshärdning och ska aldrig publiceras som färdig kundprodukt.
