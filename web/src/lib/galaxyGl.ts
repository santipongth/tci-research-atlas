/**
 * Article galaxy (R8, Ruling 13): every published article as one point on the topic map, drawn with raw WebGL2 —
 * one gl.POINTS draw call, colour per point from its field's `cat-NN` token, size by zoom, devicePixelRatio aware.
 * Filters (year range, field) run in the vertex shader, so a filter change never rebuilds a buffer: points outside the
 * filter are drawn small and grey behind the others (depth test), keeping the shape of the whole collection in view.
 *
 * galaxy.json is columnar and aligned with the search doc ordinals: x, y quantised 0 … scale over `bounds` (−1 = no
 * coordinate), t = index into `topics` (−1 = none), yr = year. Bounds are the topic map's own coordinates (topics.json
 * x/y), so field and topic names from topics.json sit on the same picture.
 *
 * The pure parts (quantising, the view transform, the CPU grid for nearest-point picking, the point shade) are unit
 * tested in galaxyGl.test.ts; the GL part needs a browser and is covered by the e2e check.
 */
import type { GalaxyFile } from '../data/types'

export interface Bounds {
  x0: number
  y0: number
  x1: number
  y1: number
}

/** World (bounds units) → CSS pixels: screen = world × k + t. */
export interface GalaxyView {
  k: number
  tx: number
  ty: number
}

/** The visitor's zoom (s) and pan (dx, dy, CSS px) on top of the fitted view. */
export interface UserView {
  s: number
  dx: number
  dy: number
}

export const MIN_ZOOM = 0.8
export const MAX_ZOOM = 48
export const RESET_VIEW: UserView = { s: 1, dx: 0, dy: 0 }
/** Colour slots in the shader; the last one is the neutral tint (no field, or a field beyond the slots). */
export const COLOR_SLOTS = 64
export const NEUTRAL_SLOT = COLOR_SLOTS - 1

// ---- quantising ---------------------------------------------------------------------------------------------------

/** A quantised coordinate (0 … scale) back to bounds units. */
export function dequantise(q: number, lo: number, hi: number, scale: number): number {
  return lo + (q / scale) * (hi - lo)
}

/** A coordinate in bounds units → 0 … scale (rounded, clamped) — the pipeline's encoding. */
export function quantise(v: number, lo: number, hi: number, scale: number): number {
  if (hi === lo) return 0
  return Math.max(0, Math.min(scale, Math.round(((v - lo) / (hi - lo)) * scale)))
}

// ---- view ---------------------------------------------------------------------------------------------------------

/** The whole bounds centred in a width × height viewport (aspect kept, `pad` px margin). */
export function fitView(b: Bounds, width: number, height: number, pad = 16): GalaxyView {
  const sx = b.x1 - b.x0 || 1
  const sy = b.y1 - b.y0 || 1
  const k = Math.max(1e-6, Math.min((width - 2 * pad) / sx, (height - 2 * pad) / sy))
  return { k, tx: (width - sx * k) / 2 - b.x0 * k, ty: (height - sy * k) / 2 - b.y0 * k }
}

export function combineView(fit: GalaxyView, user: UserView, width: number, height: number): GalaxyView {
  const cx = width / 2
  const cy = height / 2
  return { k: fit.k * user.s, tx: (fit.tx - cx) * user.s + cx + user.dx, ty: (fit.ty - cy) * user.s + cy + user.dy }
}

/** Zoom by `factor` keeping the screen point (px, py) over the same world point; zoom clamped to MIN_ZOOM … MAX_ZOOM. */
export function zoomAt(user: UserView, factor: number, px: number, py: number, width: number, height: number): UserView {
  const s = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, user.s * factor))
  const f = s / user.s
  const cx = width / 2
  const cy = height / 2
  return { s, dx: px - cx - f * (px - cx - user.dx), dy: py - cy - f * (py - cy - user.dy) }
}

export function toScreen(v: GalaxyView, wx: number, wy: number): [number, number] {
  return [wx * v.k + v.tx, wy * v.k + v.ty]
}

export function toWorld(v: GalaxyView, sx: number, sy: number): [number, number] {
  return [(sx - v.tx) / v.k, (sy - v.ty) / v.k]
}

/**
 * The vertex shader's transform: a coordinate read as a normalised unsigned short (q / 65535) → clip space,
 * clip = u × scale + offset. `fileScale` is galaxy.json's `scale` (65535 by contract; another value is honoured).
 */
export function clipTransform(v: GalaxyView, b: Bounds, width: number, height: number, fileScale = 65535): { scale: [number, number]; offset: [number, number] } {
  const r = 65535 / fileScale
  const sx = (b.x1 - b.x0) * v.k * r
  const sy = (b.y1 - b.y0) * v.k * r
  return {
    scale: [(2 * sx) / width, (-2 * sy) / height],
    offset: [(2 * (b.x0 * v.k + v.tx)) / width - 1, 1 - (2 * (b.y0 * v.k + v.ty)) / height],
  }
}

/** Point diameter in CSS px: smaller for a bigger collection, growing with zoom (√), capped. */
export function pointSize(n: number, zoom: number): number {
  const base = Math.max(2, Math.min(7, 8 - 1.6 * Math.log10(Math.max(1, n) / 100)))
  return Math.min(16, base * Math.sqrt(Math.max(MIN_ZOOM, zoom)))
}

/** Point opacity: denser collections overplot more, so each point is fainter. */
export function pointAlpha(n: number): number {
  return Math.max(0.45, Math.min(0.85, 0.9 - 0.12 * Math.log10(Math.max(1, n) / 100)))
}

// ---- points -------------------------------------------------------------------------------------------------------

/** Only the points that have a coordinate, in doc-ordinal order; `ord[i]` is the search doc ordinal of point i. */
export interface GalaxyPoints {
  count: number
  /** articles in galaxy.json, with or without a coordinate */
  total: number
  bounds: Bounds
  scale: number
  ord: Uint32Array
  /** interleaved quantised x, y (the GL position buffer) */
  q: Uint16Array
  /** world coordinates (bounds units), for picking */
  wx: Float32Array
  wy: Float32Array
  /** colour slot (field) */
  slot: Uint8Array
  yr: Uint16Array
  /** index into file.topics, −1 = none */
  topic: Int32Array
}

/**
 * galaxy.json → GL-ready arrays. `slotOfTopic(code)` gives the colour slot of a topic code (its field's index, or
 * NEUTRAL_SLOT); points without a topic take NEUTRAL_SLOT. Malformed rows (missing year, coordinate out of range) are
 * dropped rather than drawn in the wrong place.
 */
export function preparePoints(file: GalaxyFile, slotOfTopic: (code: string) => number): GalaxyPoints {
  const n = Math.min(file.x.length, file.y.length, file.t.length, file.yr.length)
  const scale = file.scale || 65535
  const b = file.bounds
  const topicSlot = file.topics.map((code) => {
    const s = slotOfTopic(code)
    return s >= 0 && s < NEUTRAL_SLOT ? s : NEUTRAL_SLOT
  })
  let count = 0
  for (let i = 0; i < n; i++) if (file.x[i] >= 0 && file.y[i] >= 0 && file.x[i] <= scale && file.y[i] <= scale) count++
  const out: GalaxyPoints = {
    count, total: n, bounds: b, scale,
    ord: new Uint32Array(count), q: new Uint16Array(2 * count), wx: new Float32Array(count), wy: new Float32Array(count),
    slot: new Uint8Array(count), yr: new Uint16Array(count), topic: new Int32Array(count),
  }
  let j = 0
  for (let i = 0; i < n; i++) {
    const x = file.x[i]
    const y = file.y[i]
    if (!(x >= 0 && y >= 0 && x <= scale && y <= scale)) continue
    const t = file.t[i]
    const hasTopic = t >= 0 && t < file.topics.length
    out.ord[j] = i
    out.q[2 * j] = Math.round(x * (65535 / scale))
    out.q[2 * j + 1] = Math.round(y * (65535 / scale))
    out.wx[j] = dequantise(x, b.x0, b.x1, scale)
    out.wy[j] = dequantise(y, b.y0, b.y1, scale)
    out.slot[j] = hasTopic ? topicSlot[t] : NEUTRAL_SLOT
    out.yr[j] = Math.max(0, Math.min(65535, file.yr[i] | 0))
    out.topic[j] = hasTopic ? t : -1
    j++
  }
  return out
}

export interface PointFilter {
  from: number | null
  to: number | null
  /** colour slot of the chosen field, or null = all */
  slot: number | null
}

export function inFilter(p: GalaxyPoints, i: number, f: PointFilter): boolean {
  const y = p.yr[i]
  return (f.from === null || y >= f.from) && (f.to === null || y <= f.to) && (f.slot === null || p.slot[i] === f.slot)
}

// ---- picking: a uniform CPU grid ----------------------------------------------------------------------------------

export interface PickGrid {
  x0: number
  y0: number
  cell: number
  cols: number
  rows: number
  /** CSR layout: the points of cell c are items[start[c] … start[c + 1] − 1] */
  start: Uint32Array
  items: Uint32Array
  wx: Float32Array
  wy: Float32Array
}

/** Square cells over the bounds sized for about `perCell` points each (8 … 1024 cells along the longer side). */
export function buildGrid(wx: Float32Array, wy: Float32Array, b: Bounds, perCell = 4): PickGrid {
  const n = wx.length
  const spanX = b.x1 - b.x0 || 1
  const spanY = b.y1 - b.y0 || 1
  const across = Math.max(8, Math.min(1024, Math.ceil(Math.sqrt(n / perCell))))
  const cell = Math.max(spanX, spanY) / across
  const cols = Math.max(1, Math.ceil(spanX / cell))
  const rows = Math.max(1, Math.ceil(spanY / cell))
  const cellOf = (i: number) => {
    const cx = Math.max(0, Math.min(cols - 1, Math.floor((wx[i] - b.x0) / cell)))
    const cy = Math.max(0, Math.min(rows - 1, Math.floor((wy[i] - b.y0) / cell)))
    return cy * cols + cx
  }
  const start = new Uint32Array(cols * rows + 1)
  for (let i = 0; i < n; i++) start[cellOf(i) + 1]++
  for (let c = 0; c < cols * rows; c++) start[c + 1] += start[c]
  const fill = start.slice(0, cols * rows)
  const items = new Uint32Array(n)
  for (let i = 0; i < n; i++) items[fill[cellOf(i)]++] = i
  return { x0: b.x0, y0: b.y0, cell, cols, rows, start, items, wx, wy }
}

/**
 * The point nearest (x, y) within `radius` (world units) that `accept` allows, or −1. Ties go to the lower index
 * (= the lower doc ordinal), so a pick never depends on grid order.
 */
export function nearest(g: PickGrid, x: number, y: number, radius: number, accept?: (i: number) => boolean): number {
  const cx = Math.floor((x - g.x0) / g.cell)
  const cy = Math.floor((y - g.y0) / g.cell)
  const reach = Math.ceil(radius / g.cell)
  let best = -1
  let bd = radius * radius
  for (let gy = Math.max(0, cy - reach); gy <= Math.min(g.rows - 1, cy + reach); gy++) {
    for (let gx = Math.max(0, cx - reach); gx <= Math.min(g.cols - 1, cx + reach); gx++) {
      const c = gy * g.cols + gx
      for (let k = g.start[c]; k < g.start[c + 1]; k++) {
        const i = g.items[k]
        const dx = g.wx[i] - x
        const dy = g.wy[i] - y
        const d = dx * dx + dy * dy
        if ((d < bd || (d === bd && (best < 0 || i < best))) && (!accept || accept(i))) {
          best = i
          bd = d
        }
      }
    }
  }
  return best
}

// ---- colour -------------------------------------------------------------------------------------------------------

export type Rgb = [number, number, number]

/** "#rrggbb", "#rgb" or "rgb(r, g, b[, a])" (as getComputedStyle returns custom properties) → 0–255 channels. */
export function parseCssColor(value: string): Rgb | null {
  const v = value.trim()
  const long = /^#([0-9a-f]{6})$/i.exec(v)
  if (long) {
    const n = parseInt(long[1], 16)
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
  }
  const short = /^#([0-9a-f]{3})$/i.exec(v)
  if (short) return [0, 1, 2].map((i) => parseInt(short[1][i] + short[1][i], 16)) as Rgb
  const fn = /^rgba?\(([^)]+)\)$/i.exec(v)
  if (fn) {
    const parts = fn[1].split(/[\s,/]+/).filter(Boolean).slice(0, 3).map(Number)
    if (parts.length === 3 && parts.every((p) => Number.isFinite(p))) return parts as Rgb
  }
  return null
}

const lin = (c: number) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)
const unlin = (c: number) => (c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055)

function toOklab([r8, g8, b8]: Rgb): [number, number, number] {
  const [r, g, b] = [lin(r8 / 255), lin(g8 / 255), lin(b8 / 255)]
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
  return [0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s, 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s, 0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s]
}

function fromOklab([L, a, b]: [number, number, number]): Rgb {
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
  const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
  const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3
  const rgb = [4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s, -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s, -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s]
  return rgb.map((c) => Math.round(Math.max(0, Math.min(1, unlin(Math.max(0, c)))) * 255)) as Rgb
}

/**
 * The point colour of a field: its `cat-NN` tint is terrain (pale on white, deep on dark), too faint for a 3 px dot,
 * so the dot keeps the tint's hue and takes a fixed OKLab lightness per theme with the chroma raised (capped) —
 * mid-tone dots on white, light dots on the dark page, ≥ 3:1 against either page. The tint stays the source of truth.
 */
export function pointShade(tint: Rgb, theme: 'light' | 'dark'): Rgb {
  const [, a, b] = toOklab(tint)
  const c = Math.min(0.16, Math.hypot(a, b) * 2.2)
  const h = Math.atan2(b, a)
  return fromOklab([theme === 'dark' ? 0.72 : 0.58, c * Math.cos(h), c * Math.sin(h)])
}

export const rgbCss = ([r, g, b]: Rgb) => `rgb(${r}, ${g}, ${b})`

export interface Palette {
  /** COLOR_SLOTS point colours (0–255): slot i = taxonomy group i, NEUTRAL_SLOT = no field */
  slots: Rgb[]
  /** the grey of points outside the filter */
  dim: Rgb
  /** packed for the shader (0–1) */
  gl: Float32Array
  glDim: Float32Array
}

/**
 * Point colours for the groups' tint tokens (`cat-NN`, or the neutral `dot`), read through `cssVar` (getComputedStyle of
 * the root, so the current theme's values) and shaded for dots. Groups beyond the slots share the neutral colour.
 */
export function resolvePalette(tokens: readonly string[], theme: 'light' | 'dark', cssVar: (name: string) => string): Palette {
  const read = (token: string): Rgb => parseCssColor(cssVar(`--${token}`)) ?? parseCssColor(cssVar('--dot')) ?? [199, 203, 206]
  const neutral = pointShade(read('dot'), theme)
  const slots = Array.from({ length: COLOR_SLOTS }, (_, i) => (i < NEUTRAL_SLOT && i < tokens.length ? pointShade(read(tokens[i]), theme) : neutral))
  const dim = read('dot')
  const gl = new Float32Array(3 * COLOR_SLOTS)
  slots.forEach((c, i) => c.forEach((v, k) => (gl[3 * i + k] = v / 255)))
  return { slots, dim, gl, glDim: new Float32Array(dim.map((v) => v / 255)) }
}

// ---- WebGL2 -------------------------------------------------------------------------------------------------------

/** WebGL2 is available here (a throwaway canvas; its context is released straight away). */
export function supportsWebGL2(): boolean {
  if (typeof document === 'undefined') return false
  try {
    const gl = document.createElement('canvas').getContext('webgl2')
    if (!gl) return false
    gl.getExtension('WEBGL_lose_context')?.loseContext()
    return true
  } catch {
    return false
  }
}

const VERT = `#version 300 es
layout(location = 0) in vec2 a_pos;
layout(location = 1) in uint a_slot;
layout(location = 2) in uint a_year;
uniform vec2 u_scale;
uniform vec2 u_offset;
uniform float u_size;
uniform uint u_from;
uniform uint u_to;
uniform int u_slot;
uniform float u_alpha;
uniform vec3 u_colors[${COLOR_SLOTS}];
uniform vec3 u_dim;
out vec4 v_color;
void main() {
  bool on = a_year >= u_from && a_year <= u_to && (u_slot < 0 || int(a_slot) == u_slot);
  // points outside the filter sit behind (depth) and stay small and grey
  gl_Position = vec4(a_pos * u_scale + u_offset, on ? 0.0 : 0.5, 1.0);
  gl_PointSize = on ? u_size : max(1.0, u_size * 0.55);
  v_color = on ? vec4(u_colors[int(a_slot)], u_alpha) : vec4(u_dim, 0.55);
}`

const FRAG = `#version 300 es
precision mediump float;
in vec4 v_color;
out vec4 o_color;
void main() {
  vec2 d = gl_PointCoord * 2.0 - 1.0;
  float r2 = dot(d, d);
  if (r2 > 1.0) discard;
  float a = v_color.a * (1.0 - smoothstep(0.6, 1.0, r2));
  o_color = vec4(v_color.rgb * a, a);
}`

export interface DrawParams {
  view: GalaxyView
  width: number
  height: number
  dpr: number
  /** point diameter, CSS px */
  size: number
  alpha: number
  filter: PointFilter
  palette: Palette
}

export interface GalaxyRenderer {
  draw(p: DrawParams): void
  dispose(): void
}

interface Resources {
  gl: WebGL2RenderingContext
  program: WebGLProgram
  vao: WebGLVertexArrayObject
  buffers: WebGLBuffer[]
  u: Record<string, WebGLUniformLocation | null>
}

function compile(gl: WebGL2RenderingContext, type: number, src: string): WebGLShader {
  const sh = gl.createShader(type)
  if (!sh) throw new Error('createShader failed')
  gl.shaderSource(sh, src)
  gl.compileShader(sh)
  if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS) && !gl.isContextLost()) {
    const log = gl.getShaderInfoLog(sh)
    gl.deleteShader(sh)
    throw new Error(`shader: ${log}`)
  }
  return sh
}

function setup(gl: WebGL2RenderingContext, pts: GalaxyPoints): Resources {
  const vs = compile(gl, gl.VERTEX_SHADER, VERT)
  const fs = compile(gl, gl.FRAGMENT_SHADER, FRAG)
  const program = gl.createProgram()
  gl.attachShader(program, vs)
  gl.attachShader(program, fs)
  gl.linkProgram(program)
  gl.deleteShader(vs)
  gl.deleteShader(fs)
  if (!gl.getProgramParameter(program, gl.LINK_STATUS) && !gl.isContextLost()) throw new Error(`program: ${gl.getProgramInfoLog(program)}`)
  const vao = gl.createVertexArray()
  gl.bindVertexArray(vao)
  const buffer = (data: AllowSharedBufferSource) => {
    const b = gl.createBuffer()
    gl.bindBuffer(gl.ARRAY_BUFFER, b)
    gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW)
    return b
  }
  const pos = buffer(pts.q)
  gl.enableVertexAttribArray(0)
  gl.vertexAttribPointer(0, 2, gl.UNSIGNED_SHORT, true, 0, 0)
  const slot = buffer(pts.slot)
  gl.enableVertexAttribArray(1)
  gl.vertexAttribIPointer(1, 1, gl.UNSIGNED_BYTE, 0, 0)
  const year = buffer(pts.yr)
  gl.enableVertexAttribArray(2)
  gl.vertexAttribIPointer(2, 1, gl.UNSIGNED_SHORT, 0, 0)
  gl.bindVertexArray(null)
  const names = ['u_scale', 'u_offset', 'u_size', 'u_from', 'u_to', 'u_slot', 'u_alpha', 'u_colors', 'u_dim']
  const u = Object.fromEntries(names.map((nm) => [nm, gl.getUniformLocation(program, nm)]))
  return { gl, program, vao, buffers: [pos, slot, year], u }
}

/**
 * One renderer per canvas. Context loss: drawing stops (`onLost`), the browser is asked to restore the context, and on
 * restore the program and buffers are rebuilt from the same points and the last frame is drawn again (`onRestored`).
 * Returns null when the canvas has no WebGL2 context.
 */
export function createRenderer(canvas: HTMLCanvasElement, pts: GalaxyPoints, events: { onLost?: () => void; onRestored?: () => void } = {}): GalaxyRenderer | null {
  const gl = canvas.getContext('webgl2', { antialias: false, premultipliedAlpha: true, alpha: true, depth: true, preserveDrawingBuffer: false })
  if (!gl) return null
  let res: Resources | null = null
  let last: DrawParams | null = null
  try {
    res = setup(gl, pts)
  } catch {
    return null
  }

  const render = (p: DrawParams) => {
    if (!res || gl.isContextLost()) return
    const pw = Math.max(1, Math.round(p.width * p.dpr))
    const ph = Math.max(1, Math.round(p.height * p.dpr))
    if (canvas.width !== pw || canvas.height !== ph) {
      canvas.width = pw
      canvas.height = ph
    }
    gl.viewport(0, 0, pw, ph)
    gl.clearColor(0, 0, 0, 0)
    gl.clearDepth(1)
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT)
    if (pts.count === 0) return
    gl.enable(gl.BLEND)
    gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA)
    gl.enable(gl.DEPTH_TEST)
    gl.depthFunc(gl.LEQUAL)
    gl.useProgram(res.program)
    const t = clipTransform(p.view, pts.bounds, p.width, p.height, 65535)
    const { u } = res
    gl.uniform2f(u.u_scale, t.scale[0], t.scale[1])
    gl.uniform2f(u.u_offset, t.offset[0], t.offset[1])
    gl.uniform1f(u.u_size, p.size * p.dpr)
    gl.uniform1ui(u.u_from, p.filter.from ?? 0)
    gl.uniform1ui(u.u_to, p.filter.to ?? 65535)
    gl.uniform1i(u.u_slot, p.filter.slot ?? -1)
    gl.uniform1f(u.u_alpha, p.alpha)
    gl.uniform3fv(u.u_colors, p.palette.gl)
    gl.uniform3fv(u.u_dim, p.palette.glDim)
    gl.bindVertexArray(res.vao)
    gl.drawArrays(gl.POINTS, 0, pts.count)
    gl.bindVertexArray(null)
  }

  const onLost = (e: Event) => {
    e.preventDefault() // ask the browser to restore the context
    res = null
    events.onLost?.()
  }
  const onRestored = () => {
    try {
      res = setup(gl, pts)
    } catch {
      return
    }
    if (last) render(last)
    events.onRestored?.()
  }
  canvas.addEventListener('webglcontextlost', onLost)
  canvas.addEventListener('webglcontextrestored', onRestored)

  return {
    draw(p) {
      last = p
      render(p)
    },
    dispose() {
      canvas.removeEventListener('webglcontextlost', onLost)
      canvas.removeEventListener('webglcontextrestored', onRestored)
      if (res && !gl.isContextLost()) {
        for (const b of res.buffers) gl.deleteBuffer(b)
        gl.deleteVertexArray(res.vao)
        gl.deleteProgram(res.program)
      }
      res = null
      last = null
    },
  }
}
