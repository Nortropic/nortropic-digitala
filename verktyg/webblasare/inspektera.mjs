#!/usr/bin/env node
// Utvecklarinspektion (användning 1): rendera adressen i valda vyer med brief- och kodkontext bifogad som lista med
// hashar, ta skärmbilder (första vyn och hela sidan), tillgänglighetsträd, konsol, nätverk, tillstånd (hover, fokus,
// tangentbord, reflow 320, meny, omladdning, bakåt/framåt), spår. Skärmbilder kompletterar interaktionen; ett textträd
// är inte bildseende — bedöm layout i bilderna.
//   node inspektera.mjs --adress URL --ut DIR [--vyer 390,1440] [--tillat ORIGIN;ORIGIN] [--undantag-fil F]
//        [--hemligheter FIL] [--kontext FIL,FIL] [--hover SEL] [--fokus SEL] [--meny SEL] [--tillstand tangentbord,reflow,reload,bakat]
import { args, oppna, origin, horisontellSpill, tangentbord, skriv, sha256, nu, lasUndantag, hemligheter } from './gemensamt.mjs';
import { readFileSync } from 'node:fs';
import { join, basename } from 'node:path';

const a = args(process.argv.slice(2));
if (!a.adress || !a.ut) { console.error('användning: --adress URL --ut DIR [...]'); process.exit(2); }
const tillat = [origin(a.adress), ...(a.tillat ? String(a.tillat).split(';').filter(Boolean) : [])];
const undantag = lasUndantag(a['undantag-fil']);
const hemliga = hemligheter(a.hemligheter);
const vyer = String(a.vyer || '390,1440').split(',');
const tillstand = new Set(String(a.tillstand || 'tangentbord,reflow,reload,bakat').split(',').filter(Boolean));
const kontext = (a.kontext ? String(a.kontext).split(',') : []).map(f => ({ fil: f, namn: basename(f), sha256: sha256(readFileSync(f)), byte: readFileSync(f).length }));
const rapport = { schema: 1, verktyg: 'inspektera', adress: a.adress, tid: nu(), tillatna_ursprung: tillat, undantag: !!undantag, kontext, vyer: {}, not: 'utvecklarinspektion med kontext; skärmbilderna avgör layout (textträdet är inte bildseende); mobilvyerna är emulerade, inte fysisk enhet' };
for (const vy of vyer) {
  const b = await oppna({ vy, tillat, undantag, hemliga, spar: true, mal: a.adress });
  const r = { namn: b.vy.namn, sidor: [], tillstand: {} };
  try {
    const svar = await b.page.goto(a.adress, { waitUntil: 'load', timeout: 45000 });
    r.status = svar?.status() ?? null; r.titel = await b.page.title();
    await b.page.waitForTimeout(500);
    r.forsta_vyn = skriv(a.ut, `vy-${vy}-forsta.png`, ''); await b.page.screenshot({ path: r.forsta_vyn });
    r.hela_sidan = join(a.ut, `vy-${vy}-hela.png`); await b.page.screenshot({ path: r.hela_sidan, fullPage: true });
    r.tillganglighetstrad = skriv(a.ut, `vy-${vy}-aria.txt`, await b.page.locator('body').ariaSnapshot());
    r.h1 = await b.page.locator('h1').count();
    r.spill = await horisontellSpill(b.page);
    if (a.hover) { await b.page.hover(a.hover, { timeout: 5000 }).catch(e => { r.tillstand.hover_fel = e.message.slice(0, 120); }); r.tillstand.hover = join(a.ut, `vy-${vy}-hover.png`); await b.page.screenshot({ path: r.tillstand.hover }); }
    if (a.fokus) { await b.page.focus(a.fokus, { timeout: 5000 }).catch(e => { r.tillstand.fokus_fel = e.message.slice(0, 120); }); r.tillstand.fokus = join(a.ut, `vy-${vy}-fokus.png`); await b.page.screenshot({ path: r.tillstand.fokus }); }
    if (a.meny) { const ok = await b.page.click(a.meny, { timeout: 5000 }).then(() => true).catch(() => false); await b.page.waitForTimeout(400); r.tillstand.meny = { klickad: ok, expanded: ok ? await b.page.locator(a.meny).getAttribute('aria-expanded').catch(() => null) : null, bild: join(a.ut, `vy-${vy}-meny.png`) }; await b.page.screenshot({ path: r.tillstand.meny.bild }); }
    if (tillstand.has('tangentbord')) { await b.page.goto(a.adress, { waitUntil: 'load' }); r.tillstand.tangentbord = await tangentbord(b.page, 25); r.tillstand.tangentbord_utan_synlig_fokus = r.tillstand.tangentbord.filter(s => !s.synligFokus).length; }
    if (tillstand.has('reflow')) { await b.page.setViewportSize({ width: 320, height: 640 }); await b.page.waitForTimeout(300); r.tillstand.reflow_320 = await horisontellSpill(b.page); await b.page.screenshot({ path: join(a.ut, `vy-${vy}-reflow320.png`) }); await b.page.setViewportSize(b.vy.viewport); }
    if (tillstand.has('reload')) { const s2 = await b.page.reload({ waitUntil: 'load' }); r.tillstand.reload_status = s2?.status() ?? null; }
    if (tillstand.has('bakat')) { const lank = b.page.locator('a[href^="/"], a[href^="' + origin(a.adress) + '"]').first(); if (await lank.count()) { const href = await lank.getAttribute('href'); await lank.click({ timeout: 5000 }).catch(() => null); await b.page.waitForLoadState('load').catch(() => null); const efter = b.page.url(); await b.page.goBack({ waitUntil: 'load' }).catch(() => null); const tillbaka = b.page.url(); await b.page.goForward({ waitUntil: 'load' }).catch(() => null); r.tillstand.bakat = { lank: href, efter_klick: efter, efter_bakat: tillbaka, efter_framat: b.page.url() }; } }
  } catch (e) { r.fel = String(e.message).slice(0, 300); }
  r.konsol = b.logg.konsol; r.sidfel = b.logg.sidfel; r.dialoger = b.logg.dialoger; r.natverk = { antal: b.logg.natverk.length, fel: b.logg.natverk.filter(x => x.status === null || x.status >= 400), blockerade: b.logg.blockerade };
  r.spar = join(a.ut, `vy-${vy}-spar.zip`); await b.stang(r.spar);
  rapport.vyer[vy] = r;
}
rapport.spar_privat = !!undantag;
if (undantag) rapport.not += '; spårfilerna bär skyddsundantaget i nätverksposter och är privata (delas aldrig); JSON-loggen är redigerad';
skriv(a.ut, 'INSPEKTION.json', rapport);
const md = ['# Inspektion — ' + a.adress + ' (' + rapport.tid + ')', '', 'Kontext bifogad: ' + (kontext.map(k => k.namn + ' ' + k.sha256.slice(0, 12)).join(', ') || 'ingen'), ''];
for (const [vy, r] of Object.entries(rapport.vyer)) md.push(`## Vy ${vy} — ${r.namn}`, '', `- status ${r.status}, titel "${r.titel}", h1 ${r.h1}, horisontell spill ${r.spill?.spill}`, `- konsol ${r.konsol.length} (fel: ${r.konsol.filter(x => x.typ === 'error').length}), sidfel ${r.sidfel.length}, nätverksfel ${r.natverk.fel.length}, blockerade ${r.natverk.blockerade.length}`, `- tangentbord: ${r.tillstand.tangentbord?.length ?? '-'} steg, utan synlig fokus ${r.tillstand.tangentbord_utan_synlig_fokus ?? '-'}; reflow 320 spill ${r.tillstand.reflow_320?.spill ?? '-'}`, `- bilder: ${r.forsta_vyn}, ${r.hela_sidan}; träd ${r.tillganglighetstrad}; spår ${r.spar}`, '');
md.push(rapport.not);
skriv(a.ut, 'INSPEKTION.md', md.join('\n') + '\n');
console.log(JSON.stringify({ ut: a.ut, vyer: Object.keys(rapport.vyer), blockerade: Object.values(rapport.vyer).reduce((s, r) => s + r.natverk.blockerade.length, 0), fel: Object.values(rapport.vyer).filter(r => r.fel).length }));
