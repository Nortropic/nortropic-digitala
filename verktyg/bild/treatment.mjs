/**
 * Nortropic — behandlingssteget (treatment, trestegs)
 *
 *   public/images/raw/  →  [NORMALISERING]  →  public/images/ref/  →  [LOOK+BESKÄRNING]  →  public/images/
 *                          adaptiv, per bild,                          fast, per preset,
 *                          körs EN gång, lagras                        körs varje bygge
 *
 * Körs som prebuild (kör --stage=both). Paletten har ETT hem — läskedjan:
 *   1. --nortropic-ink / --nortropic-accent i (src/)app/globals.css   ← normalfallet
 *   2. tokens-fältet i SLOTS.json                                     ← ENDAST äldre repon
 *   3. ingen träff → degradering med WARNING — ALDRIG gissad palett:
 *      ink saknas → #000000 + overlay-alpha −20 % · accent saknas vid
 *      duotone → tint-steget hoppas (ren normaliserad gråskala)
 *
 * CLI:
 *   node treatment.mjs                          --stage=both (default)
 *   node treatment.mjs --stage=normalise        raw/ → ref/ (idempotent: hoppar ref nyare än rå)
 *   node treatment.mjs --stage=look             ref/ → public/images/
 *   node treatment.mjs --compare                kontaktkarta: original|normaliserad|3 presets
 *   node treatment.mjs --preset=ljus            tvinga preset (annars SLOTS.json bildbehandling)
 *   node treatment.mjs --ink=#0B0E11 --accent=#C97B4A   explicit palett (testprotokollet)
 *   node treatment.mjs --in=raw --ref=ref --out=ut      katalog-overrides (test/diagnostik)
 */

import sharp from 'sharp'
import { readdirSync, existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from 'fs'
import { basename, extname, join } from 'path'
import { pathToFileURL } from 'url'

// ─────────────────────────────────────────────────────────────
// Steg 1 — Normalisering (branschoberoende, adaptiv per bild)
// ─────────────────────────────────────────────────────────────

const WB_CAP = 0.45      // max vitbalanskorrigering per kanal
const EXP_CAP = 0.60     // max exponeringskorrigering
const TARGET_LUMA = 132  // målexponering, sRGB 8-bit
const PCT = 0.98         // percentil för vitpunkt
const DEADBAND = 20      // exponering rörs inte inom detta band

const clamp = (v, cap) => Math.max(1 - cap, Math.min(1 + cap, v))

/**
 * Vitpunkt ur ljusaste percentilen. Robust mot färgstarka motiv:
 * ett färgstick färgar även högdagrarna, ett rött blomsterhav gör det inte.
 * Rapporterar också andelen klippta pixlar — vid urblåsta högdagrar
 * döljs sticket och metoden blir opålitlig.
 */
async function whitePoint(src) {
  const { data, info } = await sharp(src)
    .resize(240, 240, { fit: 'inside' })
    .raw()
    .toBuffer({ resolveWithObject: true })

  const n = info.width * info.height
  const ch = info.channels
  const lum = new Float32Array(n)
  for (let i = 0; i < n; i++)
    lum[i] = 0.2126 * data[i*ch] + 0.7152 * data[i*ch+1] + 0.0722 * data[i*ch+2]

  const cut = [...lum].sort((a, b) => a - b)[Math.floor(n * PCT)]
  let r = 0, g = 0, b = 0, k = 0, clipped = 0
  for (let i = 0; i < n; i++) {
    if (lum[i] >= cut) { r += data[i*ch]; g += data[i*ch+1]; b += data[i*ch+2]; k++ }
    if (data[i*ch] > 250 || data[i*ch+1] > 250 || data[i*ch+2] > 250) clipped++
  }
  const R = r/k, G = g/k, B = b/k
  const mx = Math.max(R,G,B), mn = Math.min(R,G,B)
  const wpChroma = mx > 0 ? (mx - mn) / mx : 1
  return k ? { r: R, g: G, b: B, clipped: clipped/n, wpChroma } : null
}

export async function analyse(src) {
  const st = await sharp(src).stats()
  const [r, g, b] = st.channels.slice(0, 3).map(c => c.mean)
  return { r, g, b, luma: 0.2126*r + 0.7152*g + 0.0722*b, entropy: st.entropy }
}

/**
 * Hybrid vitbalans: vitpunkt när högdagrarna är rena, gråvärld när de är klippta.
 * Sedan exponering mot TARGET_LUMA. Båda takade — en bild som kräver mer
 * korrigering än taket ska hellre bli delvis rättad än förvriden.
 */
export async function normalise(src) {
  const wp = await whitePoint(src)
  const s = await analyse(src)

  // Vitpunkten får bara vägas in i den mån den FAKTISKT ÄR NEUTRAL. Hög egen
  // färgmättnad (blå himmel, gult gräs, röd fasad) betyder att de ljusaste
  // pixlarna inte är vita — då ska gråvärld ta över, eftersom den är mildare
  // och inte förstärker motivets egen färg.
  const w = wp
    ? Math.max(0, 1 - wp.clipped * 3) * Math.max(0, 1 - wp.wpChroma * 4)
    : 0

  const gGrey = (s.r + s.g + s.b) / 3
  const gw = [gGrey/s.r, gGrey/s.g, gGrey/s.b]

  const wGrey = wp ? (wp.r + wp.g + wp.b) / 3 : 1
  const pw = wp ? [wGrey/wp.r, wGrey/wp.g, wGrey/wp.b] : [1, 1, 1]

  // Saknas neutral referens i bilden går den inte att vitbalansera automatiskt
  // (vitpunkten färgad OCH scenens genomsnitt färgat — båda metoderna pekar åt
  // samma håll, hybriden hjälper inte). Då lämnas bilden orörd i färg och bara
  // exponeringsnormaliseras — hellre en bild som avviker i ton än en bild med
  // förvriden färg. Looken i steg två drar ändå ihop serien.
  const sceneChroma = (Math.max(s.r,s.g,s.b) - Math.min(s.r,s.g,s.b)) / Math.max(s.r,s.g,s.b)
  const ingenReferens = wp && wp.wpChroma > 0.18 && sceneChroma > 0.12

  const wb = ingenReferens
    ? [1, 1, 1]
    : [0,1,2].map(i => clamp(pw[i]*w + gw[i]*(1-w), WB_CAP))

  const wbLuma = 0.2126*s.r*wb[0] + 0.7152*s.g*wb[1] + 0.0722*s.b*wb[2]
  const exp = Math.abs(wbLuma - TARGET_LUMA) < DEADBAND
    ? 1
    : clamp(TARGET_LUMA / wbLuma, EXP_CAP)

  return sharp(src).linear(wb.map(k => k * exp), [0, 0, 0])
}

// ─────────────────────────────────────────────────────────────
// Look (fast per preset, branschvald)
// ─────────────────────────────────────────────────────────────

export const PRESETS = {
  duotone: {
    branscher: 'el, bygg, industri, konsult, mark, anläggning',
    princip: 'färgen är irrelevant → tas bort. Formen och ytan bär.',
    apply: (p, t) => t.accent
      ? p.greyscale().linear(1.12, -14).tint(t.accent).modulate({ saturation: 0.55 })
      : p.greyscale().linear(1.12, -14),   // degraderad: accent saknas → ingen tint
    overlay: { hero: 0.55, ovrigt: 0.30 },
  },

  dokumentar: {
    branscher: 'hantverkare, transport, fastighet, verkstad',
    princip: 'färgen är verklig → normaliseras, inte tas bort. Sakligt, inte stiliserat.',
    apply: (p) => p
      .linear(1.06, -8)
      .modulate({ saturation: 0.85 }),
    overlay: { hero: 0.42, ovrigt: 0.12 },
  },

  ljus: {
    branscher: 'blomster, frisör, café, hunddagis, terapeut, fotograf',
    princip: 'färgen ÄR innehållet → bevaras. Koherensen kommer ur ljus och luft.',
    apply: (p) => p
      .linear(0.92, 22)
      .modulate({ saturation: 1.04, brightness: 1.02 })
      .gamma(1.05),
    overlay: { hero: 0.28, ovrigt: 0.06 },
  },
}

// q55 är ett TAK av kompressionsskäl, inte en smakinställning: uppmätt klippa
// q55→q60 (dokumentar 59→206 kB, ljus 71→278 kB). Sätts aldrig högre utan ny mätning.
const AVIF_TAK = 55
const WEBP_Q = 72
const AVIF_GOLV = 35

/** Budget per slot-prefix, kB på avif-filen. Dokumenterad i lighthouse-targets.md. */
export const BUDGET_KB = { hero: 150, people: 100, ovrigt: 120 }

export const CROPS = {
  hero:   [2400, 1350],  // 16:9
  env:    [1600, 1067],  // 3:2
  proof:  [1600, 1067],
  detail: [1600, 1067],
  people: [1080, 1350],  // 4:5
  // og finns inte längre som slot — OG-bilden genereras av app/opengraph-image.tsx
  // (Next-konventionen) ur REF-versionen; se behandling.md "OG-bilden läser ref/".
}

function flat(w, h, hex, alpha) {
  const r = parseInt(hex.slice(1,3), 16)
  const g = parseInt(hex.slice(3,5), 16)
  const b = parseInt(hex.slice(5,7), 16)
  return sharp({ create: { width: w, height: h, channels: 4,
    background: { r, g, b, alpha } } }).png().toBuffer()
}

/** Slot-id ur filnamn: `proof-01__takbyte-lulea.jpg` → { prefix:'proof', id:'proof-01' } */
export function parseSlot(filename) {
  const base = basename(filename, extname(filename))
  const id = base.split('__')[0]
  return { id, prefix: id.split('-')[0] }
}

// ─────────────────────────────────────────────────────────────
// Palettkedjan — ETT hem, ärlig degradering, aldrig gissad default
// ─────────────────────────────────────────────────────────────

const HEX = /#[0-9a-fA-F]{6}/
const cssToken = (css, name) =>
  css.match(new RegExp(`--nortropic-${name}:\\s*(${HEX.source})`))?.[1] ?? null

export function readTokens(cli = {}) {
  let ink = HEX.test(cli.ink ?? '') ? cli.ink : null
  let accent = HEX.test(cli.accent ?? '') ? cli.accent : null
  let kalla = (ink || accent) ? 'cli' : null

  if (!ink || !accent) {
    const cssPath = ['src/app/globals.css', 'app/globals.css'].find(p => existsSync(p))
    if (cssPath) {
      const css = readFileSync(cssPath, 'utf8')
      ink ??= cssToken(css, 'ink')
      accent ??= cssToken(css, 'accent')
      if (ink || accent) kalla ??= cssPath
    }
  }

  if ((!ink || !accent) && existsSync('SLOTS.json')) {
    try {
      const t = JSON.parse(readFileSync('SLOTS.json', 'utf8')).tokens ?? {}
      ink ??= HEX.test(t.ink ?? '') ? t.ink : null          // bakåtkompat — äldre repon
      accent ??= HEX.test(t.accent ?? '') ? t.accent : null
      if (ink || accent) kalla ??= 'SLOTS.json (bakåtkompat)'
    } catch { /* trasig SLOTS.json ändrar inte degraderingsvägen */ }
  }

  return { ink, accent, kalla }
}

function readPreset(cli = {}) {
  if (cli.preset) return { preset: cli.preset, kalla: 'cli' }
  if (existsSync('SLOTS.json')) {
    try {
      const p = JSON.parse(readFileSync('SLOTS.json', 'utf8')).bildbehandling
      if (p) return { preset: p, kalla: 'SLOTS.json' }
    } catch { /* faller till default nedan */ }
  }
  return { preset: 'dokumentar', kalla: 'default (osäkerhetsvalet, §5)' }
}

// ─────────────────────────────────────────────────────────────
// Stegen
// ─────────────────────────────────────────────────────────────

const IMG_RE = /\.(jpe?g|png|webp|tiff?)$/i

/** raw/ → ref/: normalisera EN gång per bild, lagra. Hoppar ref nyare än råfilen. */
export async function stageNormalise(RAW, REF) {
  if (!existsSync(RAW)) { console.log(`  (${RAW} saknas — inget att normalisera)`); return 0 }
  mkdirSync(REF, { recursive: true })
  let n = 0
  for (const f of readdirSync(RAW).filter(f => IMG_RE.test(f))) {
    // Varumärkesmaterial går ALDRIG genom behandlingen — brand.mjs äger det.
    // (Känt-men-inte-behandlings; okända prefix kastar fortfarande högt i look-steget.)
    if (/^brand__/i.test(f)) { console.log(`  ${f}  →  hoppas (varumärkesmaterial — brand.mjs äger det)`); continue }
    const src = join(RAW, f)
    const ref = join(REF, basename(f, extname(f)) + '.jpg')
    if (existsSync(ref) && statSync(ref).mtimeMs > statSync(src).mtimeMs) {
      console.log(`  ${f}  →  hoppas (ref nyare än råfilen)`)
      continue
    }
    await (await normalise(src)).jpeg({ quality: 95 }).toFile(ref)
    console.log(`  ${f}  →  ${ref}  [normaliserad]`)
    n++
  }
  return n
}

/** ref/ → public/images/: look + beskärning per preset. Normaliserar ALDRIG om. */
export async function stageLook(REF, OUT, presetName, tokens) {
  const P = PRESETS[presetName]
  if (!P) throw new Error(`Okänt preset: ${presetName}`)
  if (!existsSync(REF)) { console.log(`  (${REF} saknas — kör --stage=normalise först)`); return 0 }
  mkdirSync(OUT, { recursive: true })

  let ink = tokens.ink, alphaFaktor = 1
  if (!ink) {
    ink = '#000000'; alphaFaktor = 0.8
    console.warn('  WARNING: --nortropic-ink saknas — overlay körs #000000 med alpha −20 %. Sätt token i globals.css.')
  }
  if (presetName === 'duotone' && !tokens.accent) {
    console.warn('  WARNING: ACCENT SAKNAS — DUOTONE KÖRS SOM REN NORMALISERAD GRÅSKALA (TINT-STEGET HOPPAT). PALETTEN GISSAS ALDRIG — SÄTT --nortropic-accent I GLOBALS.CSS.')
  }

  let n = 0
  const budgetWarns = []
  for (const f of readdirSync(REF).filter(f => IMG_RE.test(f))) {
    if (/^brand__/i.test(f)) { console.log(`  ${f}  →  hoppas (varumärkesmaterial i ref/ — städa bort, brand.mjs äger det)`); continue }
    const { id, prefix } = parseSlot(f)
    // Okänt prefix får ALDRIG falla tyst till env-beskärning — en logotyp i raw/
    // skulle förstöras utan varning. Högt fel i stället.
    if (!CROPS[prefix]) throw new Error(
      `Okänt slot-prefix "${prefix}" (fil: ${f}). Giltiga: ${Object.keys(CROPS).join(', ')}. ` +
      `Filer i raw/ ska bära slot-id enligt slot-schema.md.`)
    const [w, h] = CROPS[prefix]
    const alpha = (prefix === 'hero' ? P.overlay.hero : P.overlay.ovrigt) * alphaFaktor
    const out = join(OUT, `${id}.avif`)

    let p = sharp(join(REF, f)).resize(w, h, { fit: 'cover', position: 'attention' })
    p = P.apply(p, tokens)
    if (alpha > 0) {
      p = p.composite([{ input: await flat(w, h, ink, alpha), blend: 'multiply' }])
    }

    // Koda en gång till master-buffer, avif-koda därifrån — budgetloopen ska
    // aldrig räkna om normalisering/look per kvalitetssteg.
    const master = await p.png().toBuffer()
    const budgetKb = BUDGET_KB[prefix] ?? BUDGET_KB.ovrigt

    let q = AVIF_TAK
    let avif = await sharp(master).avif({ quality: q }).toBuffer()
    while (avif.length > budgetKb * 1024 && q - 5 >= AVIF_GOLV) {
      q -= 5
      avif = await sharp(master).avif({ quality: q }).toBuffer()
    }
    writeFileSync(out, avif)
    await sharp(master).webp({ quality: WEBP_Q }).toFile(out.replace(/\.avif$/, '.webp'))

    const kb = Math.round(avif.length / 1024)
    if (avif.length > budgetKb * 1024) {
      budgetWarns.push({ typ: 'budget', slot: id, fil: `${id}.avif`,
        storlekKb: kb, budgetKb, kvalitet: q,
        varning: `över budget vid golvkvalitet q${AVIF_GOLV}` })
      console.warn(`  WARNING: ${id}.avif ${kb} kB > budget ${budgetKb} kB trots golv q${q}`)
    }
    console.log(`  ${f}  →  ${out}  [${prefix} · ${presetName} · avif q${q} · ${kb} kB]`)
    n++
  }
  if (budgetWarns.length || existsSync('BILDRAPPORT.json')) skrivBudgetWarns(budgetWarns)
  return n
}

/** Budget-WARNs in i BILDRAPPORT.json (skapas vid behov, tidigare budgetrader ersätts). Felar aldrig. */
function skrivBudgetWarns(warns) {
  try {
    let rapport = []
    if (existsSync('BILDRAPPORT.json')) {
      const r = JSON.parse(readFileSync('BILDRAPPORT.json', 'utf8'))
      if (Array.isArray(r)) rapport = r.filter(rad => rad.typ !== 'budget')
    }
    rapport.push(...warns)
    writeFileSync('BILDRAPPORT.json', JSON.stringify(rapport, null, 2))
  } catch (e) {
    console.warn(`  (kunde inte skriva budget-WARNs till BILDRAPPORT.json: ${e.message})`)
  }
}

// ─────────────────────────────────────────────────────────────
// CLI
// ─────────────────────────────────────────────────────────────

// win32: naiva `file://${argv[1]}` matchar aldrig (backslash-sökväg) — pathToFileURL krävs
const isMain = process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href

if (isMain) {
  const cli = Object.fromEntries(process.argv.slice(2)
    .map(a => a.replace(/^--/, '').split('=')).map(([k, v]) => [k, v ?? true]))

  const RAW = cli.in ?? 'public/images/raw'
  const REF = cli.ref ?? 'public/images/ref'
  const OUT = cli.out ?? 'public/images'

  const tokens = readTokens(cli)
  const { preset, kalla: presetKalla } = readPreset(cli)

  if (cli.compare) {
    // Kontaktkarta: original | normaliserad | duotone | dokumentar | ljus
    // Diagnostikläge (testprotokollet): läser --in (default raw/), skriver --out (default ut/)
    const IN = cli.in ?? 'raw'
    const UT = cli.out === 'public/images' || !cli.out ? 'ut' : cli.out
    mkdirSync(UT, { recursive: true })
    const t = { ink: tokens.ink ?? '#000000', accent: tokens.accent }
    if (!tokens.ink) console.warn('  WARNING: ink saknas — kontaktkartans overlay körs #000000. Ange --ink=#RRGGBB.')
    if (!tokens.accent) console.warn('  WARNING: ACCENT SAKNAS — DUOTONE-KOLUMNEN VISAS UTAN TINT. ANGE --accent=#RRGGBB.')
    const files = readdirSync(IN).filter(f => IMG_RE.test(f))
    for (const f of files) {
      const src = join(IN, f)
      const cells = []
      const W = 420, H = 280
      cells.push(await sharp(src).resize(W, H, { fit: 'cover' }).toBuffer())
      cells.push(await (await normalise(src)).resize(W, H, { fit: 'cover' }).toBuffer())
      for (const name of Object.keys(PRESETS)) {
        const P = PRESETS[name]
        let p = (await normalise(src)).resize(W, H, { fit: 'cover' })
        p = P.apply(p, t)
        p = p.composite([{ input: await flat(W, H, t.ink, P.overlay.ovrigt), blend: 'multiply' }])
        cells.push(await p.toBuffer())
      }
      await sharp({ create: { width: W * cells.length, height: H, channels: 3,
          background: { r: 12, g: 14, b: 17 } } })
        .composite(cells.map((input, i) => ({ input, left: W * i, top: 0 })))
        .jpeg({ quality: 88 })
        .toFile(join(UT, `jamfor-${basename(f, extname(f))}.jpg`))
      console.log(`  ${f} → ${UT}/jamfor-${basename(f, extname(f))}.jpg`)
    }
    console.log('\nKolumner: original | normaliserad | duotone | dokumentar | ljus')
    console.log('Kolumn två = innehållet i ref/ (referensutrymmet).')
  } else {
    const stage = cli.stage ?? 'both'
    if (!['normalise', 'look', 'both'].includes(stage)) throw new Error(`Okänt --stage: ${stage}`)
    console.log(`Behandling — stage: ${stage} · preset: ${preset} (${presetKalla})` +
      (tokens.kalla ? ` · palett: ${tokens.kalla}` : ' · palett: SAKNAS (degradering)'))
    if (stage === 'normalise' || stage === 'both') await stageNormalise(RAW, REF)
    if (stage === 'look' || stage === 'both') await stageLook(REF, OUT, preset, tokens)
  }
}
