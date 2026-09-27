/**
 * Nortropic — varumärkeslagret (nod 5, körs av content-designer EFTER fetch-images.mjs)
 *
 * Indata:  public/images/raw/brand__*.{png,jpg,jpeg,svg}  — kundens logotyp som den kom.
 *          Går ALDRIG genom treatment.mjs (stageNormalise hoppar brand__ explicit).
 * Utdata (EXAKT denna uppsättning, inget mer — Next 15:s filkonvention genererar taggarna;
 * skriv ALDRIG ikon-<link> för hand i layout.tsx):
 *   app/icon.svg              märket, mörkt läge via inbäddad prefers-color-scheme
 *   app/favicon.ico           16+32+48 (PNG-poster i ICO), under 10 kB
 *   app/apple-icon.png        180×180, kvadratisk, INGA förrundade hörn
 *   public/icon-192.png       manifest, purpose "any maskable"
 *   public/icon-512.png       manifest, purpose "any maskable"
 *   app/manifest.webmanifest  namn, temafärg ur tokens, de två ikonerna
 *   public/brand/logo.svg     full logotyp (eller logo.png vid raster-degradering)
 *   public/brand/logo-mark.svg  märket ensamt
 *
 * FAVICON-MÄRKET är ett DOKUMENTERAT BESLUT (ögonarbete — agenten avgör, skriptet
 * verkställer och journalför): --marke=symbol kräver --markfil=<svg> (den separerade
 * symbolen); --marke=monogram (default utan SVG-källa/markfil) genererar initialer i
 * displaytypsnittet, accent på ink. Krymp ALDRIG en ordbild till 32 px.
 *
 * Degradering (felar aldrig): rembg/vtracer saknas → rastern behålls som
 * public/brand/logo.png + rapportrad + fotouppdragsflagga (kunden tillfrågas om
 * EPS/AI/SVG oavsett). Ingen logotyp alls → monogramvägen rakt av (kräver inga
 * binärer — vägen som bär de flesta kunder). Tokens saknas → AKROMATISK degradering
 * (ink→#000000, accent→#FFFFFF) med WARNING — en varumärkesfärg GISSAS aldrig.
 *
 * Gates (i rapporten, ALDRIG launch.js): favicon.ico >10 kB → WARN ·
 * apple-icon ≠180×180 → FAIL · icon.svg utan viewBox → FAIL ·
 * källa <512 px längsta sidan och ingen SVG → WARN + fotouppdragsrad.
 *
 * CLI (cwd = byggrepots rot):
 *   node .../brand.mjs [--marke=monogram|symbol] [--markfil=path.svg]
 *                      [--initialer=AB] [--namn="Företag AB"] [--display=Archivo]
 */

import sharp from 'sharp'
import { readdirSync, readFileSync, writeFileSync, existsSync, mkdirSync, copyFileSync, statSync } from 'fs'
import { join, extname, basename } from 'path'
import { pathToFileURL } from 'url'
import { execFileSync } from 'child_process'
import { tmpdir } from 'os'

const RAW = 'public/images/raw'
const HEX = /#[0-9a-fA-F]{6}/

// ── Tokens: samma D1-kedja som treatment.mjs — globals.css → SLOTS.json → degradering ──
function lasTokens() {
  let ink = null, accent = null, kalla = null
  const cssPath = ['src/app/globals.css', 'app/globals.css'].find(p => existsSync(p))
  if (cssPath) {
    const css = readFileSync(cssPath, 'utf8')
    ink = css.match(new RegExp(`--nortropic-ink:\\s*(${HEX.source})`))?.[1] ?? null
    accent = css.match(new RegExp(`--nortropic-accent:\\s*(${HEX.source})`))?.[1] ?? null
    if (ink || accent) kalla = cssPath
  }
  if ((!ink || !accent) && existsSync('SLOTS.json')) {
    try {
      const t = JSON.parse(readFileSync('SLOTS.json', 'utf8')).tokens ?? {}
      ink ??= HEX.test(t.ink ?? '') ? t.ink : null
      accent ??= HEX.test(t.accent ?? '') ? t.accent : null
      if (ink || accent) kalla ??= 'SLOTS.json (bakåtkompat)'
    } catch { /* degraderingsvägen */ }
  }
  return { ink, accent, kalla }
}

// ── SVG-normalisering: viewBox satt, metadata strippad, fills → currentColor där entydigt ──
function normaliseraSvg(svg) {
  svg = svg.replace(/<\?xml[^?]*\?>\s*/g, '').replace(/<!--[\s\S]*?-->/g, '')
    .replace(/<metadata[\s\S]*?<\/metadata>/gi, '').replace(/<title[\s\S]*?<\/title>/gi, '')
    .replace(/<desc[\s\S]*?<\/desc>/gi, '')
  if (!/viewBox=/.test(svg)) {
    const w = svg.match(/width="?([\d.]+)/)?.[1], h = svg.match(/height="?([\d.]+)/)?.[1]
    if (w && h) svg = svg.replace(/<svg/, `<svg viewBox="0 0 ${w} ${h}"`)
  }
  const fills = [...new Set([...svg.matchAll(/fill="(#[0-9a-fA-F]{3,8})"/g)].map(m => m[1].toLowerCase()))]
  if (fills.length === 1) svg = svg.replaceAll(new RegExp(`fill="${fills[0]}"`, 'gi'), 'fill="currentColor"')
  return svg
}

// ── Monogram-SVG: initialer i displaytypsnittet, accent på ink; mörkt läge inverterar tokens ──
function monogramSvg(initialer, display, ink, accent) {
  const size = initialer.length > 1 ? 30 : 38
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <style>.bg{fill:${ink}}.fg{fill:${accent}}@media (prefers-color-scheme: dark){.bg{fill:${accent}}.fg{fill:${ink}}}</style>
  <rect class="bg" width="64" height="64"/>
  <text class="fg" x="32" y="33" text-anchor="middle" dominant-baseline="central" font-family="${display}, system-ui, sans-serif" font-weight="700" font-size="${size}" letter-spacing="-1">${initialer}</text>
</svg>\n`
}

/** Märket på ink-platta som raster (för ico/apple/manifest — maskable: märket i trygga 60 %-zonen). */
async function markPaRaster(markSvg, px, ink) {
  const inner = Math.round(px * 0.6)
  const mark = await sharp(Buffer.from(markSvg.replaceAll('currentColor', '#FFFFFF')), { density: 300 })
    .resize(inner, inner, { fit: 'inside' }).png().toBuffer()
  const [r, g, b] = [ink.slice(1, 3), ink.slice(3, 5), ink.slice(5, 7)].map(h => parseInt(h, 16))
  return sharp({ create: { width: px, height: px, channels: 4, background: { r, g, b, alpha: 1 } } })
    .composite([{ input: mark, gravity: 'centre' }]).png().toBuffer()
}

/** Minimal ICO-packare: PNG-poster (16/32/48). */
function packaIco(pngs) {
  const count = pngs.length
  const header = Buffer.alloc(6)
  header.writeUInt16LE(0, 0); header.writeUInt16LE(1, 2); header.writeUInt16LE(count, 4)
  const entries = [], blobs = []
  let offset = 6 + count * 16
  for (const { px, buf } of pngs) {
    const e = Buffer.alloc(16)
    e.writeUInt8(px >= 256 ? 0 : px, 0); e.writeUInt8(px >= 256 ? 0 : px, 1)
    e.writeUInt16LE(1, 4); e.writeUInt16LE(32, 6)
    e.writeUInt32LE(buf.length, 8); e.writeUInt32LE(offset, 12)
    offset += buf.length
    entries.push(e); blobs.push(buf)
  }
  return Buffer.concat([header, ...entries, ...blobs])
}

const harBinar = (namn) => {
  try { execFileSync(process.platform === 'win32' ? 'where' : 'which', [namn], { stdio: 'pipe' }); return true }
  catch { return false }
}

// ── CLI ──────────────────────────────────────────────────────
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const cli = Object.fromEntries(process.argv.slice(2)
    .map(a => a.replace(/^--/, '').split('=')).map(([k, v]) => [k, v ?? true]))
  const rapport = []
  const rad = (typ, niva, text, extra = {}) => { rapport.push({ typ: 'brand', niva, text, ...extra }); console.log(`  [${niva}] ${text}`) }

  // Tokens (D1) — akromatisk degradering, aldrig gissad varumärkesfärg
  const tok = lasTokens()
  let ink = tok.ink, accent = tok.accent
  if (!ink) { ink = '#000000'; rad('token', 'WARN', 'WARNING: --nortropic-ink saknas — akromatisk degradering #000000, sätt token i globals.css') }
  if (!accent) { accent = '#FFFFFF'; rad('token', 'WARN', 'WARNING: --nortropic-accent saknas — akromatisk degradering #FFFFFF (vit), varumärkesfärg gissas ALDRIG') }

  // Källa: public/images/raw/brand__*
  const kallor = existsSync(RAW) ? readdirSync(RAW).filter(f => /^brand__.*\.(png|jpe?g|svg)$/i.test(f)) : []
  const svgKalla = kallor.find(f => /\.svg$/i.test(f))
  const rasterKalla = kallor.find(f => /\.(png|jpe?g)$/i.test(f))

  // Next:s filkonventioner kräver ikonerna I app-katalogen — kundrepona använder src/app/
  const APP = existsSync('src/app') ? 'src/app' : 'app'
  mkdirSync(APP, { recursive: true }); mkdirSync('public/brand', { recursive: true })

  // Full logotyp → public/brand/
  let fullLogoSvg = null
  if (svgKalla) {
    fullLogoSvg = normaliseraSvg(readFileSync(join(RAW, svgKalla), 'utf8'))
    writeFileSync('public/brand/logo.svg', fullLogoSvg)
    rad('logo', 'OK', `logo.svg ur ${svgKalla} (normaliserad: viewBox/metadata/currentColor)`)
  } else if (rasterKalla) {
    const src = join(RAW, rasterKalla)
    const meta = await sharp(src).metadata()
    const langsta = Math.max(meta.width ?? 0, meta.height ?? 0)
    if (langsta < 512) rad('kalla', 'WARN', `källlogotypen ${langsta} px längsta sidan (<512) och ingen SVG — be om originalet`, { fotouppdrag: true })
    if (harBinar('rembg') && harBinar('vtracer')) {
      try {
        const utanBg = join(tmpdir(), `brand-nobg-${Date.now()}.png`)
        execFileSync('rembg', ['i', src, utanBg], { stdio: 'pipe' })
        const svgUt = join(tmpdir(), `brand-vec-${Date.now()}.svg`)
        execFileSync('vtracer', ['--input', utanBg, '--output', svgUt], { stdio: 'pipe' })
        fullLogoSvg = normaliseraSvg(readFileSync(svgUt, 'utf8'))
        writeFileSync('public/brand/logo.svg', fullLogoSvg)
        rad('logo', 'OK', `logo.svg vektoriserad ur ${rasterKalla} (rembg → vtracer)`)
      } catch (e) {
        copyFileSync(src, 'public/brand/logo.png')
        rad('logo', 'WARN', `vektorisering föll (${e.message.slice(0, 60)}) — rastern behållen som logo.png`, { fotouppdrag: true })
      }
    } else {
      copyFileSync(src, 'public/brand/logo.png')
      rad('logo', 'WARN', 'rembg/vtracer saknas — rastern behållen som public/brand/logo.png; be kunden om EPS/AI/SVG', { fotouppdrag: true })
    }
  } else {
    rad('logo', 'INFO', 'ingen brand__-källa i raw/ — monogramvägen rakt av (vanligt hos nystartade)')
  }

  // FAVICON-MÄRKET — dokumenterat beslut (agentens flagga journalförs)
  let marke = cli.marke ?? (cli.markfil ? 'symbol' : 'monogram')
  let markSvg
  if (marke === 'symbol') {
    const mf = cli.markfil ?? (svgKalla ? 'public/brand/logo.svg' : null)
    if (!mf || !existsSync(mf)) {
      rad('marke', 'WARN', '--marke=symbol utan läsbar --markfil — faller till monogram (krymp aldrig en ordbild till 32 px)')
      marke = 'monogram'
    } else {
      markSvg = normaliseraSvg(readFileSync(mf, 'utf8'))
      rad('marke', 'BESLUT', `märket = separerbar symbol ur ${mf} (agentens dokumenterade beslut)`)
    }
  }
  if (marke === 'monogram') {
    const namn = cli.namn ?? (existsSync('SLOTS.json') ? JSON.parse(readFileSync('SLOTS.json', 'utf8')).kund ?? '' : '')
    const initialer = (cli.initialer ?? namn.split(/[\s-]+/).map(o => o[0] ?? '').join('').slice(0, 2)).toUpperCase() || 'N'
    markSvg = monogramSvg(initialer, cli.display ?? 'system-ui', ink, accent)
    rad('marke', 'BESLUT', `märket = monogram "${initialer}" (${cli.display ?? 'system-ui'}, accent på ink — ordbild krymps aldrig till 32 px)`)
  }
  writeFileSync('public/brand/logo-mark.svg', markSvg)

  // app/icon.svg — märket med mörkt läge inbakat (monogrammet bär det redan; symbol får wrappern)
  const iconSvg = marke === 'monogram' ? markSvg
    : `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <style>.m{color:${ink}}@media (prefers-color-scheme: dark){.m{color:${accent}}}</style>
  <g class="m">${markSvg.replace(/<\/?svg[^>]*>/g, '')}</g>
</svg>\n`
  writeFileSync(join(APP, 'icon.svg'), iconSvg)

  // Raster-uppsättningen
  const ico = packaIco([
    { px: 16, buf: await markPaRaster(markSvg, 16, ink) },
    { px: 32, buf: await markPaRaster(markSvg, 32, ink) },
    { px: 48, buf: await markPaRaster(markSvg, 48, ink) },
  ])
  writeFileSync(join(APP, 'favicon.ico'), ico)
  writeFileSync(join(APP, 'apple-icon.png'), await markPaRaster(markSvg, 180, ink))
  writeFileSync('public/icon-192.png', await markPaRaster(markSvg, 192, ink))
  writeFileSync('public/icon-512.png', await markPaRaster(markSvg, 512, ink))

  const namnUt = cli.namn ?? (existsSync('SLOTS.json') ? JSON.parse(readFileSync('SLOTS.json', 'utf8')).kund ?? 'Nortropic-kund' : 'Nortropic-kund')
  writeFileSync(join(APP, 'manifest.webmanifest'), JSON.stringify({
    name: namnUt, short_name: namnUt, theme_color: ink, background_color: ink,
    display: 'browser',
    icons: [
      { src: '/icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any maskable' },
      { src: '/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' },
    ],
  }, null, 2))

  // Gates — i rapporten, ALDRIG launch.js
  const icoKb = statSync(join(APP, 'favicon.ico')).size / 1024
  if (icoKb > 10) rad('gate', 'WARN', `favicon.ico ${icoKb.toFixed(1)} kB > 10 kB`)
  const am = await sharp(join(APP, 'apple-icon.png')).metadata()
  if (am.width !== 180 || am.height !== 180) rad('gate', 'FAIL', `apple-icon.png ${am.width}×${am.height} ≠ 180×180`)
  if (!/viewBox=/.test(readFileSync(join(APP, 'icon.svg'), 'utf8'))) rad('gate', 'FAIL', 'icon.svg saknar viewBox')
  if (!rapport.some(r => r.niva === 'FAIL')) rad('gate', 'OK', `gates rena: favicon ${icoKb.toFixed(1)} kB · apple-icon 180×180 · viewBox satt`)

  // In i BILDRAPPORT.json (typ:"brand" — samma fil, tredje skrivaren; egna rader ersätts per körning)
  try {
    let alla = []
    if (existsSync('BILDRAPPORT.json')) {
      const r = JSON.parse(readFileSync('BILDRAPPORT.json', 'utf8'))
      if (Array.isArray(r)) alla = r.filter(x => x.typ !== 'brand')
    }
    writeFileSync('BILDRAPPORT.json', JSON.stringify([...alla, ...rapport], null, 2))
  } catch (e) { console.warn(`  (kunde inte skriva BILDRAPPORT.json: ${e.message})`) }
  console.log(`\n  Varumärkeslagret klart — ${rapport.filter(r => r.niva === 'WARN').length} WARN · ${rapport.filter(r => r.niva === 'FAIL').length} FAIL (se BILDRAPPORT.json)`)
}
