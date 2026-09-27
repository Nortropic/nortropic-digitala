import sharp from 'sharp'

/** Mekanisk gallring av genererade kandidater. Alla mått är beräkningsbara — ingen smak.
 *  Körs på NORMALISERADE kandidater (ref-versioner) — måtten är exponeringskänsliga,
 *  så alla bedöms mot samma skala (trestegsordningen: generera → normalisera → score). */
export async function score(src, slotPrefix) {
  const { data, info } = await sharp(src).greyscale().resize(320, 320, { fit: 'fill' })
    .raw().toBuffer({ resolveWithObject: true })
  const W = info.width, H = info.height
  const st = await sharp(src).stats()

  const band = (y0, y1) => {
    let s = 0, s2 = 0, n = 0
    for (let y = y0; y < y1; y++) for (let x = 0; x < W; x++) { const v = data[y*W+x]; s += v; s2 += v*v; n++ }
    const m = s/n
    return { mean: m, sd: Math.sqrt(s2/n - m*m) }
  }
  const top = band(0, Math.floor(H/3)), rest = band(Math.floor(H/3), H)

  // lokal högfrekvens = detaljrus / textliknande struktur
  let hf = 0
  for (let y = 1; y < H-1; y++) for (let x = 1; x < W-1; x++) {
    const i = y*W+x
    hf += Math.abs(4*data[i] - data[i-1] - data[i+1] - data[i-W] - data[i+W])
  }
  hf /= (W-2)*(H-2)

  const m = {
    entropi: st.entropy,
    rubrikzon_sd: top.sd,                       // låg = plats för text
    zonkontrast: Math.abs(top.mean - rest.mean),
    hogfrekvens: hf,                            // hög = detaljrus, avslöjar genererat
  }

  const inom = (v, lo, hi) => v >= lo && v <= hi ? 1 : 0
  const krav = slotPrefix === 'hero'
    ? [inom(m.entropi, 4.0, 7.2), inom(m.rubrikzon_sd, 0, 28), inom(m.hogfrekvens, 0, 14)]
    : [inom(m.entropi, 4.0, 7.4), 1,                            inom(m.hogfrekvens, 0, 18)]

  return { ...m, poang: krav.reduce((a,b)=>a+b,0), godkand: krav.every(Boolean) }
}
