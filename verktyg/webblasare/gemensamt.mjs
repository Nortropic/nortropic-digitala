// Gemensamt för Digitalas webbläsarväg (Playwright 1.63, pinnad i package.json): start, vyer, värdverkställd
// ursprungsgräns, logg med redigerade hemligheter, spår. Ingen modell här; modellen (utvecklare, QA eller avskärmad
// besökare) sitter i sessionen som anropar verktygen.
import { chromium } from 'playwright';
import { createHash } from 'node:crypto';
import { readFileSync, statSync, mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

export const VYER = { '390': { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, namn: 'mobil (emulerad, inte fysisk enhet)' },
                      '768': { viewport: { width: 768, height: 1024 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, namn: 'surfplatta (emulerad)' },
                      '1440': { viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1, isMobile: false, hasTouch: false, namn: 'dator' },
                      '320': { viewport: { width: 320, height: 640 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, namn: 'reflow 320 px (WCAG 1.4.10)' } };
const HEMLIGA_NAMN = /^(authorization|cookie|set-cookie|x-vercel-protection-bypass|x-vercel-set-bypass-cookie|proxy-authorization)$/i;
const HEMLIGA_PARAM = /^(x-vercel-protection-bypass|x-vercel-set-bypass-cookie|token|key|api_key|apikey|secret|password)$/i;

export function args(argv) {
  const ut = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const [k, v] = a.slice(2).split(/=(.*)/s);
      if (v !== undefined) ut[k] = v;
      else if (argv[i + 1] !== undefined && !argv[i + 1].startsWith('--')) ut[k] = argv[++i];
      else ut[k] = true;
    } else ut._.push(a);
  }
  return ut;
}

export function sha256(buf) { return createHash('sha256').update(buf).digest('hex'); }
export function nu() { return new Date().toISOString().replace(/\.\d+Z$/, 'Z'); }

/** Skyddsundantag: privat fil (rättighet 0600, en rad ≥ 16 tecken, utanför tmp). Värdet skrivs aldrig ut. */
export function lasUndantag(fil) {
  if (!fil) return null;
  const st = statSync(fil);
  if ((st.mode & 0o077) !== 0) throw new Error('undantagsfilen ska ha rättighet 0600');
  if (/^\/(tmp|etc|var\/folders)\//.test(fil) || fil.startsWith('/private/tmp')) throw new Error('undantagsfilen får inte ligga i tmp, etc eller var/folders');
  const v = readFileSync(fil, 'utf8').trim().split('\n')[0].trim();
  if (v.length < 16) throw new Error('undantagsfilen ska bära en rad om minst 16 tecken');
  return v;
}

export function hemligheter(fil) {
  if (!fil) return [];
  return readFileSync(fil, 'utf8').split('\n').map(l => l.trim()).filter(l => l && !l.startsWith('#')).map(l => l.split('=').slice(1).join('=').trim()).filter(v => v.length >= 8);
}

export function redigerare(varden) {
  return (text) => {
    let t = String(text);
    for (const v of varden) if (v) t = t.split(v).join('[REDIGERAT]');
    return t;
  };
}

export function redigeraUrl(url) {
  try {
    const u = new URL(url);
    for (const k of [...u.searchParams.keys()]) if (HEMLIGA_PARAM.test(k)) u.searchParams.set(k, 'REDIGERAT');
    return u.toString();
  } catch { return url; }
}

export function origin(url) { return new URL(url).origin; }

/** Startar webbläsare + kontext för en vy med värdverkställd ursprungsgräns (route-nivå: allt utanför tillåtna ursprung
 *  avbryts och loggas som blockerat), skyddsundantag som header bara mot målets ursprung, logg och spår. */
export async function oppna({ vy = '1440', tillat = [], undantag = null, hemliga = [], spar = null, extra = {} }) {
  const v = VYER[vy]; if (!v) throw new Error('okänd vy: ' + vy + ' (390, 768, 1440, 320)');
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: v.viewport, deviceScaleFactor: v.deviceScaleFactor, isMobile: v.isMobile, hasTouch: v.hasTouch, locale: 'sv-SE', timezoneId: 'Europe/Stockholm', ...extra });
  const red = redigerare([undantag, ...hemliga].filter(Boolean));
  const logg = { konsol: [], natverk: [], blockerade: [], dialoger: [], sidfel: [] };
  const tillatna = new Set(tillat.map(o => origin(o)));
  await ctx.route('**/*', async (route) => {
    const req = route.request(); const u = req.url();
    let o; try { o = origin(u); } catch { return route.abort('blockedbyclient'); }
    if (u.startsWith('data:') || u.startsWith('blob:')) return route.continue();
    if (tillatna.size && !tillatna.has(o)) {
      logg.blockerade.push({ metod: req.method(), url: redigeraUrl(u), typ: req.resourceType(), tid: nu() });
      return route.abort('blockedbyclient');
    }
    const headers = { ...req.headers() };
    if (undantag && tillatna.has(o)) headers['x-vercel-protection-bypass'] = undantag;
    return route.continue({ headers });
  });
  ctx.on('page', p => {
    p.on('console', m => logg.konsol.push({ typ: m.type(), text: red(m.text()).slice(0, 500), tid: nu() }));
    p.on('pageerror', e => logg.sidfel.push({ text: red(e.message).slice(0, 500), tid: nu() }));
    p.on('dialog', async d => { logg.dialoger.push({ typ: d.type(), text: red(d.message()).slice(0, 200) }); await d.dismiss().catch(() => {}); });
    p.on('response', r => logg.natverk.push({ metod: r.request().method(), url: redigeraUrl(r.url()), status: r.status(), typ: r.request().resourceType() }));
    p.on('requestfailed', r => logg.natverk.push({ metod: r.method(), url: redigeraUrl(r.url()), status: null, fel: r.failure()?.errorText, typ: r.resourceType() }));
  });
  if (spar) await ctx.tracing.start({ screenshots: true, snapshots: true, sources: false });
  const page = await ctx.newPage();
  return { browser, ctx, page, logg, vy: v, red, stang: async (sparFil) => { if (spar && sparFil) { await ctx.tracing.stop({ path: sparFil }); } else if (spar) { await ctx.tracing.stop(); } await browser.close(); } };
}

export async function horisontellSpill(page) {
  return page.evaluate(() => ({ spill: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1, scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth }));
}

/** Tangentbordsväg: Tab genom de första N fokuserbara elementen; registrerar element, synlig fokusmarkering och ordning. */
export async function tangentbord(page, n = 25) {
  const steg = [];
  for (let i = 0; i < n; i++) {
    await page.keyboard.press('Tab');
    const info = await page.evaluate(() => {
      const el = document.activeElement; if (!el || el === document.body) return null;
      const cs = getComputedStyle(el); const r = el.getBoundingClientRect();
      const synlig = (cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0) || cs.boxShadow !== 'none';
      return { tagg: el.tagName.toLowerCase(), text: (el.innerText || el.getAttribute('aria-label') || el.getAttribute('alt') || el.value || '').trim().slice(0, 60), synligFokus: synlig, iVy: r.bottom > 0 && r.top < innerHeight, storlek: [Math.round(r.width), Math.round(r.height)] };
    });
    if (!info) break;
    if (steg.length && steg[steg.length - 1].tagg === info.tagg && steg[steg.length - 1].text === info.text) break;
    steg.push(info);
  }
  return steg;
}

export function skriv(dir, namn, data) {
  mkdirSync(dir, { recursive: true });
  const p = join(dir, namn);
  writeFileSync(p, typeof data === 'string' ? data : JSON.stringify(data, null, 1) + '\n');
  return p;
}
