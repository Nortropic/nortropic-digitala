# Bevis och fortsatt arbete

`fortsatt.py klart --bevis FIL` kräver ett typat `digitala-stegbevis/1` för `klar` och manuellt N/A. Varken en
sökväg, en fri not, gammalt godkännande eller `svar_giltigt` räcker. Väntan och underkännande får rapporteras utan
framgångsbevis. De bevarar råkvitton och sidoeffekter. Nödvändig väntan hindrar färdig leverans; oberoende steg kan
fortsätta. Koncept som väntar får inte användas som klar förutsättning för bygge.

Före provet definierar utföraren fallets privata `BEVISKRAV.json` (schema `digitala-beviskrav/1`, `version`, `steg`).
Varje steg har `niva` (`dokument`, `statik`, `lokal`, `privat-preview`, `drift`), `sammanhang` och `kontroller`, ett
objekt med obligatoriska kontroll-id och förväntat innehåll. Tillämplighet får inte ändras för att dölja ett fel.
En kontrolls `na_skal` är ett uttryckligt sakskäl bestämt före bedömningen; hela stegets N/A kräver också dess eget
`na_skal`. Åtkomst, kostnad, okänd regel eller uteblivet prov ska redovisas som väntan/ej prövat, inte N/A.

`sammanhang` innehåller tre objekt:

- `kandidat`: antingen `{typ: "git", rot: absolut_katalog, commit: full_SHA, tree: full_träd_SHA}` med ren arbetsyta,
  eller `{typ: "filer", filer: [{fil: absolut_sökväg, sha256: SHA256}]}` med minst en konkret kandidatfil.
- `miljo`: `{namn: konkret_namn, typ: konkret_typ}`. Miljön och provnivån måste vara samma som i de fördefinierade
  kraven, det rapporterade beviset och de faktiskt refererade råresultaten.
- `konfiguration`: `{filer: [{fil, sha256}]}` eller `{filer: [], ej_tillampligt: sakskäl}`. Hemliga värden läggs
  aldrig i rapporten; säkra konfigurationsbevis kan ange versionsidentitet utan behörighetsvärden.

Stegbeviset innehåller `schema`, `steg`, `kund` (absolut kundmapp), `krav_sha256`, `laddning_sha256`, `utfall`
(`klar`/`inte-tillampligt`), `genomfort: true`, `utforare`, `omfattning`, `niva`, `sammanhang` och `kontroller`.
Varje godkänd kontroll anger `id`, `utfall: "godkant"`, konkret `observerat`, ett faktiskt JSON-råresultat med
`fil`/`sha256`, `utfallspekare` (lista av nycklar/index till verkligt utfall), samt `bindningspekare` med nycklarna
`kandidat`, `miljo`, `konfiguration` och deras pekare i råresultatet. Exakt `PASS`, `passed`, `approved`, `godkant`,
`godkänd` eller boolean true accepteras, aldrig prefix, exitkod, tomt svar eller formstatus. Ett manuellt omdöme
måste märkas med sin faktiska metod och räckvidd i råresultatet; kuvertet bevisar inte att påståendet är sant.

`HANDLINGAR.json` i prelaunch använder samma väg: toppnivå `fall`, `kund`, `bygge_sha256` (ur prelaunch.bygg_hash för exakt byggkatalog), `handlingar`; varje handling har
`namn`, `typ`, `bevis` (stegbevisfil) och `kontroll_id` för obligatoriskt faktiskt prov. Äldre fria statussträngar
står som EJ_MATT. Kontrollraden anger också `byggpekare` till samma bygginnehållshash i det faktiska råresultatet;
att byta hash enbart i HANDLINGAR.json kan inte återanvända ett prov på en äldre byggnad. Ett dokumentprov får aldrig presenteras som verifierad extern leverans.

Vid fortsatt/status kontrolleras kandidat, konfiguration, krav per steg, råfiler, laddningskvitto och relevanta
kundfakta. Ändring återöppnar berörda godkännanden och deras nödvändiga efterföljare; historik och sidoeffekter
bevaras. En oförändrad del behåller giltigheten när en annan del av kravfilen ändras. Äldre fall utan sådana bevis
återöppnas uttryckligen; deras gamla kvitton uppgraderas aldrig automatiskt. Inget historiskt prov skrivs om.

Lös ett aktivt beroende med `klart … --lost-beroende "exakt beroendetext" --not "hur det har verifierats"`.
Det får då historisk löst-status med utförare/tid/skäl. Ny väntan B kan rapporteras medan A markeras löst; status
visar bara aktiva hinder. `omprova` i sig betyder inte att ett beroende är löst. Verktygsskapade hinder stängs när
deras konkreta förutsättning åter är uppfylld. Utförd extern effekt får inte upprepas bara för att ett prov öppnas.
