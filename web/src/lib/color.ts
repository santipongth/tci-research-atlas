/**
 * Colour maths for the palette test (not used at run time): WCAG 2 contrast and OKLab ΔE ×100,
 * optionally under the Machado, Oliveira & Fernandes (2009) severity-1.0 colour-vision-deficiency
 * simulation — the same model and thresholds as the dataviz skill's validator
 * (CVD target ≥ 8, normal-vision floor ≥ 15, marks ≥ 3:1).
 */
export type Cvd = 'protan' | 'deutan' | 'tritan'

type Row = readonly [number, number, number]
const MACHADO: Record<Cvd, readonly [Row, Row, Row]> = {
  protan: [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
  deutan: [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.01182, 0.04294, 0.968881]],
  tritan: [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.3039]],
}

function linear(hex: string): [number, number, number] {
  const h = hex.trim().replace(/^#/, '')
  if (!/^[0-9a-f]{6}$/i.test(h)) throw new Error(`not a #rrggbb colour: ${hex}`)
  const ch = (i: number) => {
    const c = parseInt(h.slice(i, i + 2), 16) / 255
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
  }
  return [ch(0), ch(2), ch(4)]
}

function luminance(hex: string): number {
  const [r, g, b] = linear(hex)
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

export function contrastRatio(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (hi + 0.05) / (lo + 0.05)
}

function oklab([r, g, b]: [number, number, number]): [number, number, number] {
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
  return [
    0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s,
    1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s,
    0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s,
  ]
}

function simulate(rgb: [number, number, number], cvd: Cvd): [number, number, number] {
  const M = MACHADO[cvd]
  const clamp = (c: number) => Math.max(0, Math.min(1, c))
  return [0, 1, 2].map((i) => clamp(M[i][0] * rgb[0] + M[i][1] * rgb[1] + M[i][2] * rgb[2])) as [number, number, number]
}

/** Euclidean distance in OKLab ×100; with `cvd`, both colours are simulated first. */
export function deltaE(a: string, b: string, cvd?: Cvd): number {
  const la = cvd ? simulate(linear(a), cvd) : linear(a)
  const lb = cvd ? simulate(linear(b), cvd) : linear(b)
  const [p, q] = [oklab(la), oklab(lb)]
  return 100 * Math.hypot(p[0] - q[0], p[1] - q[1], p[2] - q[2])
}
