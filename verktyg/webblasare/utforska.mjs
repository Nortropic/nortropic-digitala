#!/usr/bin/env node
// Utforskande QA (användning 2): väljer själv vägar inom tillåtet ursprung, klickar, skriver, provar felvägar och
// tillstånd, och skriver fynd med reproduktion. Regel: formulär skickas ALDRIG utan --formular-far-skickas och en
// testmarkering; annars provas bara klientvalidering. Fynd blir regressionsprov (REGRESSION.json) som kan köras om.
//   node utforska.mjs --adress URL --ut DIR [--max-sidor 15] [--vy 390|1440] [--tillat ORIGIN;…] [--undantag-fil F]
//        [--formular-far-skickas --testmarkering "TEST nortropic"] [--regression REGRESSION.json]
import { args, oppna, origin, horisontellSpill, tangentbord, skriv, nu, lasUndantag, hemligheter } from './gemensamt.mjs';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const a = args(process.argv.slice(2));
if (!a.adress || !a.ut) { console.error('användning: --adress URL --ut DIR [...]'); process.exit(2); }
const bas = origin(a.adress);
const tillat = [bas, ...(a.tillat ? String(a.tillat).split(';').filter(Boolean) : [])];
const undantag = lasUndantag(a['undantag-fil']);
const hemliga = hemligheter(a.hemligheter);
const maxSidor = parseInt(a['max-sidor'] || '15', 10);
const farSkicka = !!a['formular-far-skickas'];
const markering = a.testmarkering ? String(a.testmarkering) : null;
if (farSkicka && !markering) { console.error('--formular-far-skickas kräver --testmarkering TEXT'); process.exit(2); }
const regression = a.regression ? JSON.parse(readFileSync(a.regression, 'utf8')) : null;
const fynd = []; const sidor = []; const ko = [a.adress]; const sedda = new Set();
const lagg = (typ, sida, vad, repro, extra = {}) => fynd.push({ typ, sida, vad, repro, ...extra });
const b = await oppna({ vy: a.vy || '390', tillat, undantag, hemliga, spar: true });
const page = b.page;
const LANGT = 'x'.repeat(2000); const SCRIPT = '<script>alert(1)</script>'; const UNICODE = 'Åsa Öberg-Ärlig ✓ 🌱';

async function provaFormular(url, i) {
  const form = page.locator('form').nth(i);
  const falt = await form.locator('input:not([type=hidden]):not([type=submit]):not([type=checkbox]):not([type=radio]), textarea').all();
  const r = { form: i, falt: falt.length, tomt: null, langt: null, ogiltig_epost: null, script: null, skickat: false };
  const konsolFore = b.logg.konsol.length;
  const submit = form.locator('button[type=submit], input[type=submit], button:not([type])').first();
  const klickSubmit = async () => { if (!(await submit.count())) return false; await submit.click({ timeout: 5000, noWaitAfter: true }).catch(() => null); await page.waitForTimeout(600); return true; };
  // tomt inskick: klientvalidering ska stoppa; om formuläret ändå skickas utan tillåtelse är det ett fynd
  const urlFore = page.url();
  if (!farSkicka) {
    const giltigt = await form.evaluate(f => f.checkValidity()).catch(() => null);
    r.tomt = { giltigt_tomt: giltigt };
    if (giltigt === true) lagg('varning', url, 'formuläret godtar tomt inskick enligt klientvalidering (required saknas)', { steg: ['öppna ' + url, 'lämna fälten tomma', 'kontrollera form.checkValidity()'] }, { form: i });
  } else {
    await klickSubmit();
    r.tomt = { navigerade: page.url() !== urlFore, url: page.url() };
    if (page.url() !== urlFore) lagg('fel', url, 'tomt inskick gick igenom (sidan navigerade)', { steg: ['öppna ' + url, 'klicka skicka utan att fylla i'] }, { form: i });
    if (page.url() !== urlFore) await page.goto(url, { waitUntil: 'load' });
  }
  for (const [namn, varde] of [['langt', LANGT], ['script', SCRIPT], ['unicode', UNICODE]]) {
    for (const f of falt) { await f.fill(varde).catch(() => null); }
    const validering = await form.evaluate(f => [...f.querySelectorAll('input,textarea')].map(e => ({ n: e.name || e.id, ok: e.checkValidity(), msg: e.validationMessage }))).catch(() => []);
    r[namn] = { faltvalidering: validering.filter(v => !v.ok).length, av: validering.length };
    if (namn === 'script') { const html = await page.content(); if (html.includes('<script>alert(1)</script>') && !html.includes('&lt;script&gt;')) lagg('fel', url, 'skriptsträng återges oescapad i sidan', { steg: ['fyll fältet med ' + SCRIPT, 'läs sidans HTML'] }, { form: i }); }
  }
  const epost = form.locator('input[type=email]').first();
  if (await epost.count()) { await epost.fill('inte-en-adress'); r.ogiltig_epost = { giltig: await epost.evaluate(e => e.checkValidity()) }; if (r.ogiltig_epost.giltig) lagg('varning', url, 'ogiltig e-post godtas av klientvalideringen', { steg: ['fyll e-post med inte-en-adress'] }, { form: i }); }
  if (farSkicka) {
    for (const f of falt) { const typ = await f.getAttribute('type'); await f.fill(typ === 'email' ? 'test@example.com' : (markering + ' ' + UNICODE)).catch(() => null); }
    const svarFore = b.logg.natverk.length;
    await klickSubmit(); await page.waitForTimeout(1200);
    const nya = b.logg.natverk.slice(svarFore).filter(x => x.metod === 'POST');
    r.skickat = true; r.post = nya.map(x => ({ url: x.url, status: x.status, fel: x.fel }));
    const besked = await page.evaluate(() => document.body.innerText.slice(0, 4000));
    r.besked = /tack|mottag|skickat|vi hör av oss|fel|misslyck/i.test(besked) ? besked.match(/[^.\n]*(tack|mottag|skickat|vi hör av oss|fel|misslyck)[^.\n]*/i)?.[0]?.trim().slice(0, 160) : null;
    if (!r.besked) lagg('varning', url, 'inget synligt besked efter inskick (accepterad ≠ skickad ≠ bekräftad ska synas)', { steg: ['fyll i formuläret med testmarkering', 'skicka', 'läs sidans text'] }, { form: i });
    // dubbelt inskick: samma uppgifter en gång till (återförsök); mottagaren ska inte skapa ett andra ärende
    await page.goto(url, { waitUntil: 'load' }).catch(() => null);
    const form2 = page.locator('form').nth(i); const falt2 = await form2.locator('input:not([type=hidden]):not([type=submit]):not([type=checkbox]):not([type=radio]), textarea').all();
    for (const f of falt2) { const typ = await f.getAttribute('type'); await f.fill(typ === 'email' ? 'test@example.com' : (markering + ' ' + UNICODE)).catch(() => null); }
    const submit2 = form2.locator('button[type=submit], input[type=submit], button:not([type])').first();
    if (await submit2.count()) { await submit2.click({ timeout: 5000, noWaitAfter: true }).catch(() => null); await page.waitForTimeout(1000); }
    const nya2 = b.logg.natverk.slice(svarFore).filter(x => x.metod === 'POST');
    r.dubbelt = { post_antal: nya2.length, identiska_uppgifter: true };
    if (nya2.length > nya.length) lagg('observation', url, 'ett återförsök med identiska uppgifter gav ytterligare POST — mottagaren måste hantera dubbletter (integrationer.md)', { steg: ['skicka formuläret', 'gå tillbaka och skicka samma uppgifter igen'] }, { form: i });
  }
  r.konsolfel = b.logg.konsol.slice(konsolFore).filter(x => x.typ === 'error').length;
  return r;
}

async function undersok(url) {
  const s = { url, tid: nu() };
  const svar = await page.goto(url, { waitUntil: 'load', timeout: 45000 }).catch(e => { s.fel = e.message.slice(0, 200); return null; });
  s.status = svar?.status() ?? null;
  if (s.status && s.status >= 400) lagg('fel', url, 'sidan svarar ' + s.status, { steg: ['öppna ' + url] });
  if (!svar) return s;
  await page.waitForTimeout(300);
  s.titel = await page.title(); s.h1 = await page.locator('h1').count();
  if (s.h1 !== 1) lagg('varning', url, 'h1-antal ' + s.h1, { steg: ['öppna ' + url, 'räkna h1'] });
  s.spill = await horisontellSpill(page); if (s.spill.spill) lagg('fel', url, 'horisontell spill i vyn ' + (a.vy || '390'), { steg: ['öppna ' + url + ' i vy ' + (a.vy || '390'), 'jämför scrollWidth och clientWidth'] }, s.spill);
  s.bild = join(a.ut, 'sida-' + sidor.length + '.png'); await page.screenshot({ path: s.bild }).catch(() => null);
  const lankar = await page.locator('a[href]').evaluateAll(els => els.map(e => e.href));
  s.lankar = lankar.length;
  for (const l of lankar) { try { const u = new URL(l); if (u.origin === bas && !sedda.has(u.origin + u.pathname) && !/\.(pdf|jpg|png|zip)$/i.test(u.pathname)) ko.push(u.origin + u.pathname); } catch {} }
  const svarFore = b.logg.natverk.length;
  s.formular = []; const nForm = await page.locator('form').count();
  for (let i = 0; i < Math.min(nForm, 3); i++) { s.formular.push(await provaFormular(url, i)); await page.goto(url, { waitUntil: 'load' }).catch(() => null); }
  const meny = page.locator('button[aria-expanded], button[aria-controls]').first();
  if (await meny.count()) { const fore = await meny.getAttribute('aria-expanded'); await meny.click({ timeout: 4000 }).catch(() => null); await page.waitForTimeout(300); const efter = await meny.getAttribute('aria-expanded'); s.meny = { fore, efter }; if (fore === efter) lagg('varning', url, 'menyknappens aria-expanded ändras inte vid klick', { steg: ['klicka menyknappen', 'läs aria-expanded'] }); await page.keyboard.press('Escape'); }
  s.tangentbord = await tangentbord(page, 20); s.utan_synlig_fokus = s.tangentbord.filter(x => !x.synligFokus).map(x => x.tagg + ':' + x.text);
  if (s.utan_synlig_fokus.length) lagg('varning', url, 'fokuserbara element utan synlig fokusmarkering: ' + s.utan_synlig_fokus.slice(0, 5).join(', '), { steg: ['öppna ' + url, 'tryck Tab upprepade gånger', 'kontrollera outline/box-shadow'] });
  const efter = b.logg.natverk.slice(svarFore).filter(x => x.status === null || x.status >= 400);
  if (efter.length) lagg('varning', url, 'misslyckade förfrågningar: ' + efter.slice(0, 3).map(x => x.url + ' ' + (x.status ?? x.fel)).join('; '), { steg: ['öppna ' + url, 'läs nätverksloggen'] });
  const fel = b.logg.konsol.filter(x => x.typ === 'error'); s.konsolfel = fel.length;
  return s;
}

try {
  if (regression) {
    for (const r of regression.prov || []) { const s = await undersok(r.sida); sidor.push(s); }
  } else {
    while (ko.length && sidor.length < maxSidor) { const url = ko.shift(); const nyckel = url.replace(/#.*$/, ''); if (sedda.has(nyckel)) continue; sedda.add(nyckel); sidor.push(await undersok(url)); }
    const svar404 = await page.goto(bas + '/finns-inte-' + Date.now(), { waitUntil: 'load' }).catch(() => null);
    const sida404 = { status: svar404?.status() ?? null, text: await page.evaluate(() => document.body.innerText.slice(0, 200)).catch(() => '') };
    if (sida404.status !== 404) lagg('varning', bas, 'okänd adress svarar ' + sida404.status + ' i stället för 404', { steg: ['öppna en adress som inte finns'] });
    if (!/tel:|kontakt|hem|start/i.test(sida404.text)) lagg('observation', bas, '404-sidan saknar synlig väg vidare (kontakt, start)', { steg: ['öppna en adress som inte finns', 'läs sidan'] });
    const verkliga = sidor.filter(s => s.url.startsWith('http') && s.status && s.status < 400);
    if (verkliga.length > 1) { await page.goto(verkliga[0].url); await page.goto(verkliga[1].url); await page.goBack(); const bak = page.url(); await page.goForward(); const fram = page.url(); if (bak.replace(/\/$/, '') !== verkliga[0].url.replace(/\/$/, '')) lagg('varning', bas, 'bakåt landar inte på föregående sida', { steg: ['gå från ' + verkliga[0].url + ' till ' + verkliga[1].url, 'bakåt'] }, { bak, fram }); }
    sidor.push({ url: 'okänd adress', ...sida404 });
  }
} finally {
  const spar = join(a.ut, 'utforskning-spar.zip'); await b.stang(spar);
  const ut = { schema: 1, verktyg: 'utforska', adress: a.adress, tid: nu(), vy: a.vy || '390', tillatna_ursprung: tillat, formular_skickade: farSkicka, testmarkering: markering, undantag: !!undantag, sidor, fynd, blockerade: b.logg.blockerade, spar, spar_privat: !!undantag,
    not: 'självvalt testförlopp inom tillåtna ursprung; inga konton, köp eller riktiga meddelanden; formulär skickas bara med --formular-far-skickas och testmarkering; blockerade förfrågningar listas så att de inte misstas för produktens beteende; mobilvyn är emulerad' };
  skriv(a.ut, 'UTFORSKNING.json', ut);
  skriv(a.ut, 'REGRESSION.json', { schema: 1, kalla: a.adress, tid: nu(), prov: fynd.filter(f => f.typ !== 'observation').map(f => ({ sida: f.sida, vad: f.vad, repro: f.repro })) });
  const md = ['# Utforskande QA — ' + a.adress + ' (' + ut.tid + ', vy ' + ut.vy + ')', '', `Sidor: ${sidor.length} · fynd: ${fynd.length} (fel ${fynd.filter(f => f.typ === 'fel').length}, varningar ${fynd.filter(f => f.typ === 'varning').length}, observationer ${fynd.filter(f => f.typ === 'observation').length}) · blockerade förfrågningar: ${b.logg.blockerade.length} · formulär skickade: ${farSkicka}`, '', '| Typ | Sida | Vad | Reproduktion |', '|---|---|---|---|', ...fynd.map(f => `| ${f.typ} | ${f.sida} | ${f.vad.replace(/\|/g, '/')} | ${(f.repro.steg || []).join(' → ').replace(/\|/g, '/')} |`), '', ut.not];
  skriv(a.ut, 'UTFORSKNING.md', md.join('\n') + '\n');
  console.log(JSON.stringify({ ut: a.ut, sidor: sidor.length, fynd: fynd.length, blockerade: b.logg.blockerade.length }));
}
