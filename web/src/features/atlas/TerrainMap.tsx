import { useEffect, useImperativeHandle, useMemo, useRef, useState, type ReactNode, type Ref } from 'react'
import { textWidth } from '../../lib/measure'
import { glyphPath, isSignal, type StatusId } from '../../lib/status'
import { useTheme } from '../../lib/theme'
import { useTooltip } from '../../lib/tooltip'
import type { Layer } from '../../lib/urlState'
import { useElementSize } from '../../lib/useElementSize'
import { useFontsVersion } from '../../lib/useFontsVersion'
import { combineView, COLS, fitScreen, MAP_H, MAP_W, NEUTRAL_TINT, placeCentered, placeLabels, ROWS, zoomAt, type MapPoint, type UserView } from './mapSpace'
import type { Terrain } from './terrain'

export interface TerrainMapHandle {
  /** Pan so that topic `id` is inside the view (used when a gazetteer row is picked). */
  reveal(id: string): void
}

/** A field as drawn on the map; its array index is MapPoint.groupIndex. */
export interface MapGroup {
  name: string
  /** design-token key from taxonomy.json, e.g. "cat-03" (or the neutral tint for fallback groups) */
  color: string
  cx: number
  cy: number
  n: number
}

export interface MapControls {
  zoomIn: string
  zoomOut: string
  reset: string
  group: string
  hint: string
}

const ROW_H = MAP_H / ROWS
const PRIORITY: Record<StatusId, number> = { EMERGING: 0, WATCH: 1, HOT: 2, DECLINING: 3, STABLE: 4, LOW_DATA: 5 }
const PAN: Record<string, [number, number]> = { ArrowLeft: [60, 0], ArrowRight: [-60, 0], ArrowUp: [0, 60], ArrowDown: [0, -60] }
const RESET: UserView = { s: 1, dx: 0, dy: 0 }

function rgb(value: string): [number, number, number] {
  const v = value.trim()
  const hex = /^#([0-9a-f]{6})$/i.exec(v)
  if (hex) {
    const n = parseInt(hex[1], 16)
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
  }
  const parts = v.match(/[\d.]+/g)
  return parts && parts.length >= 3 ? [Number(parts[0]), Number(parts[1]), Number(parts[2])] : [200, 200, 200]
}

/** Hypsometric field tints as a small image (one pixel per terrain cell), dimmed outside the focused field. */
function tintCanvas(terrain: Terrain, colors: readonly [number, number, number][], focus: number | null): HTMLCanvasElement {
  const cv = document.createElement('canvas')
  cv.width = terrain.gw
  cv.height = terrain.gh
  const ctx = cv.getContext('2d')
  if (!ctx) return cv
  const img = ctx.createImageData(terrain.gw, terrain.gh)
  for (let c = 0; c < terrain.band.length; c++) {
    const b = terrain.band[c]
    const o = terrain.owner[c]
    if (!b || o < 0) continue
    const col = colors[o] ?? [200, 200, 200]
    let a = Math.min(0.92, 0.28 + b * 0.085)
    if (focus !== null && o !== focus) a *= 0.28
    img.data[c * 4] = col[0]
    img.data[c * 4 + 1] = col[1]
    img.data[c * 4 + 2] = col[2]
    img.data[c * 4 + 3] = Math.round(a * 255)
  }
  ctx.putImageData(img, 0, 0)
  return cv
}

/**
 * Cartographic sheet: canvas (grid, tints, contours, dots for STABLE/LOW_DATA) under an SVG overlay
 * (grid references, field names, focusable markers for signal topics and the selection, collision-free labels).
 * Keyboard: Tab to markers (in grid order, A1 → J6), Enter/Space to select; on the sheet itself arrows pan, + − zoom, 0 resets.
 */
export function TerrainMap({ ref, points, groups, terrain, hidden, layers, selected, onSelect, describe, tipFor, names, label, describedBy, controls }: {
  ref?: Ref<TerrainMapHandle>
  points: readonly MapPoint[]
  groups: readonly MapGroup[]
  terrain: Terrain
  hidden: ReadonlySet<StatusId>
  layers: ReadonlySet<Layer>
  selected: string | null
  onSelect: (id: string) => void
  describe: (p: MapPoint) => string
  tipFor: (id: string) => ReactNode
  names: ReadonlyMap<string, string>
  label: string
  describedBy: string
  controls: MapControls
}) {
  const [wrapRef, size, wrapEl] = useElementSize<HTMLDivElement>()
  const canvasRef = useRef<HTMLCanvasElement>(null)
  // tint images per theme and hovered field, for the current terrain only
  const tints = useRef<{ terrain: Terrain | null; byKey: Map<string, HTMLCanvasElement> }>({ terrain: null, byKey: new Map() })
  const drag = useRef<{ x: number; y: number; dx: number; dy: number } | null>(null)
  const [user, setUser] = useState<UserView>(RESET)
  const [hover, setHover] = useState<{ id: string | null; group: number | null }>({ id: null, group: null })
  const theme = useTheme()
  const tip = useTooltip()
  const fontsVersion = useFontsVersion() // label boxes are measured in Sarabun: measure again once it has loaded
  const W = size.width
  const H = size.height
  const view = useMemo(() => (W > 0 && H > 0 ? combineView(fitScreen(W, H), user, W, H) : null), [W, H, user])
  const frame = useRef(0) // pending requestAnimationFrame of a pointer-driven pan
  const panTo = useRef<{ dx: number; dy: number } | null>(null)
  useEffect(() => () => cancelAnimationFrame(frame.current), [])

  // Redraw the canvas after every render (pan, zoom, hover, layers, theme all change the picture).
  useEffect(() => {
    const cv = canvasRef.current
    if (!cv || !view) return
    const dpr = Math.min(2, window.devicePixelRatio || 1)
    const pw = Math.round(W * dpr)
    const ph = Math.round(H * dpr)
    if (cv.width !== pw || cv.height !== ph) {
      cv.width = pw
      cv.height = ph
    }
    const ctx = cv.getContext('2d')
    if (!ctx) return
    const css = getComputedStyle(cv)
    ctx.setTransform(1, 0, 0, 1, 0, 0)
    ctx.clearRect(0, 0, pw, ph)
    ctx.setTransform(dpr * view.k, 0, 0, dpr * view.k, dpr * view.tx, dpr * view.ty)
    ctx.strokeStyle = css.getPropertyValue('--map-grid').trim()
    ctx.lineWidth = 1 / view.k
    ctx.beginPath()
    for (let gx = 0; gx <= MAP_W; gx += 100) {
      ctx.moveTo(gx, 0)
      ctx.lineTo(gx, MAP_H)
    }
    for (let r = 0; r <= ROWS; r++) {
      ctx.moveTo(0, r * ROW_H)
      ctx.lineTo(MAP_W, r * ROW_H)
    }
    ctx.stroke()
    if (layers.has('tints')) {
      if (tints.current.terrain !== terrain) tints.current = { terrain, byKey: new Map() }
      const key = `${theme}|${hover.group ?? ''}`
      let tc = tints.current.byKey.get(key)
      if (!tc) {
        const neutral = css.getPropertyValue(`--${NEUTRAL_TINT}`)
        tc = tintCanvas(terrain, groups.map((g) => rgb(css.getPropertyValue(`--${g.color}`).trim() || neutral)), hover.group)
        tints.current.byKey.set(key, tc)
      }
      ctx.imageSmoothingEnabled = true
      ctx.drawImage(tc, 0, 0, MAP_W, MAP_H)
    }
    if (layers.has('contours')) {
      ctx.strokeStyle = css.getPropertyValue('--map-contour').trim()
      terrain.segs.forEach((s, li) => {
        const heavy = li % 3 === 2
        ctx.globalAlpha = heavy ? 0.85 : 0.5
        ctx.lineWidth = (heavy ? 1.5 : 0.85) / view.k
        ctx.beginPath()
        for (let i = 0; i < s.length; i += 4) {
          ctx.moveTo(s[i], s[i + 1])
          ctx.lineTo(s[i + 2], s[i + 3])
        }
        ctx.stroke()
      })
      ctx.globalAlpha = 1
    }
    ctx.fillStyle = css.getPropertyValue('--map-dot').trim()
    for (const p of points) {
      if (isSignal(p.status) || hidden.has(p.status) || p.id === selected) continue
      if (hover.group !== null && p.groupIndex !== hover.group) continue
      ctx.beginPath()
      ctx.arc(p.x, p.y, Math.max(1.4 / view.k, Math.min(p.r * 0.4, 3.6 / view.k)), 0, Math.PI * 2)
      ctx.fill()
    }
  })

  // Ctrl/⌘ + wheel zooms about the pointer; a plain wheel keeps scrolling the page.
  useEffect(() => {
    if (!wrapEl) return
    const onWheel = (e: WheelEvent) => {
      if (!(e.ctrlKey || e.metaKey)) return
      e.preventDefault()
      const r = wrapEl.getBoundingClientRect()
      setUser((u) => zoomAt(u, e.deltaY < 0 ? 1.15 : 1 / 1.15, e.clientX - r.left, e.clientY - r.top, r.width, r.height))
    }
    wrapEl.addEventListener('wheel', onWheel, { passive: false })
    return () => wrapEl.removeEventListener('wheel', onWheel)
  }, [wrapEl])

  useImperativeHandle(
    ref,
    () => ({
      reveal(id: string) {
        const p = points.find((q) => q.id === id)
        if (!p || !view) return
        const sx = p.x * view.k + view.tx
        const sy = p.y * view.k + view.ty
        if (sx < 40 || sx > W - 40 || sy < 40 || sy > H - 40) setUser((u) => ({ ...u, dx: u.dx + W / 2 - sx, dy: u.dy + H / 2 - sy }))
      },
    }),
    [points, view, W, H],
  )

  // Only markers on the visible sheet are drawn and focusable (focus never scrolls the clipped sheet); Tab follows the grid.
  // Markers and field names depend on the view, the filters and the font; names also on hover and selection — memoised so a
  // redraw caused by anything else (tooltip, drag frames between renders) does not redo the collision search.
  const small = W < 600
  const fieldSize = small ? 13 : 16
  const markers = useMemo(
    () =>
      view
        ? points
            .filter((p) => !hidden.has(p.status) && (isSignal(p.status) || p.id === selected))
            .map((p) => ({ p, sx: p.x * view.k + view.tx, sy: p.y * view.k + view.ty, r: Math.max(5.5, Math.min(18, p.r * view.k * 0.9)) }))
            .filter((m) => m.sx >= 0 && m.sx <= W && m.sy >= 0 && m.sy <= H)
            .sort((a, b) => Math.floor(a.p.y / ROW_H) - Math.floor(b.p.y / ROW_H) || a.p.x - b.p.x)
        : [],
    [view, points, hidden, selected, W, H],
  )
  const fieldLabels = useMemo(
    () =>
      view
        ? placeCentered(
            groups
              .map((g, gi) => ({ g, gi }))
              .sort((a, b) => b.g.n - a.g.n)
              .map(({ g, gi }) => ({ id: String(gi), text: g.name, width: textWidth(g.name, fieldSize, 700), height: fieldSize, x: g.cx * view.k + view.tx, y: g.cy * view.k + view.ty })),
            { x: 20, y: 18, w: W - 26, h: H - 22 },
            markers.map((m) => ({ x: m.sx - m.r, y: m.sy - m.r, w: 2 * m.r, h: 2 * m.r })),
          )
        : [],
    // eslint-disable-next-line react-hooks/exhaustive-deps -- fontsVersion re-measures text once Sarabun has loaded
    [view, groups, markers, fieldSize, W, H, fontsVersion],
  )
  const nameLabels = useMemo(() => {
    if (!view) return []
    const force = new Set([selected, hover.id].filter((v): v is string => v !== null))
    const ranked = [...markers].sort((a, b) => PRIORITY[a.p.status] - PRIORITY[b.p.status] || b.p.share - a.p.share)
    const named = [...ranked.filter((m) => force.has(m.p.id)), ...ranked.filter((m, i) => !force.has(m.p.id) && layers.has('names') && i < (small ? 4 : 25))]
    return placeLabels(
      named.map((m) => {
        const text = names.get(m.p.id) ?? m.p.id
        return { id: m.p.id, text, width: textWidth(text, 13, 600), height: 13, x: m.sx, y: m.sy, radius: m.r }
      }),
      [...markers.map((m) => ({ id: m.p.id, x: m.sx - m.r, y: m.sy - m.r, w: 2 * m.r, h: 2 * m.r })), ...fieldLabels.map((f) => f.box)],
      { x: 18, y: 18, w: W - 22, h: H - 22 },
      force,
    )
    // eslint-disable-next-line react-hooks/exhaustive-deps -- fontsVersion re-measures text once Sarabun has loaded
  }, [view, markers, fieldLabels, names, layers, selected, hover.id, small, W, H, fontsVersion])
  const zoom = (factor: number) => setUser((u) => zoomAt(u, factor, W / 2, H / 2, W, H))
  const enter = (p: MapPoint) => setHover({ id: p.id, group: p.groupIndex >= 0 ? p.groupIndex : null })
  const leave = () => setHover({ id: null, group: null })

  return (
    <div className="sheet">
      <div
        ref={wrapRef}
        className="sheet-in"
        tabIndex={0}
        role="group"
        aria-label={label}
        aria-describedby={describedBy}
        onScroll={(e) => {
          // the sheet clips (overflow: hidden) but a focused edge marker could still scroll it: keep it pinned
          e.currentTarget.scrollTop = 0
          e.currentTarget.scrollLeft = 0
        }}
        onPointerDown={(e) => {
          if ((e.target as Element).closest('.mnode')) return
          drag.current = { x: e.clientX, y: e.clientY, dx: user.dx, dy: user.dy }
          e.currentTarget.setPointerCapture(e.pointerId)
        }}
        onPointerMove={(e) => {
          const d = drag.current
          if (!d) return
          const mx = e.clientX - d.x
          const my = e.clientY - d.y
          if (Math.abs(mx) + Math.abs(my) < 3) return
          tip.hide()
          // at most one redraw per frame, however fast the pointer reports
          panTo.current = { dx: d.dx + mx, dy: d.dy + my }
          if (!frame.current) {
            frame.current = requestAnimationFrame(() => {
              frame.current = 0
              const to = panTo.current
              if (to) setUser((u) => ({ ...u, dx: to.dx, dy: to.dy }))
            })
          }
        }}
        onPointerUp={() => {
          drag.current = null
        }}
        onPointerCancel={() => {
          drag.current = null
        }}
        onKeyDown={(e) => {
          if (e.target !== e.currentTarget) return
          const move = PAN[e.key]
          if (move) {
            e.preventDefault()
            setUser((u) => ({ ...u, dx: u.dx + move[0], dy: u.dy + move[1] }))
          } else if (e.key === '+' || e.key === '=') {
            e.preventDefault()
            zoom(1.4)
          } else if (e.key === '-') {
            e.preventDefault()
            zoom(1 / 1.4)
          } else if (e.key === '0') {
            e.preventDefault()
            setUser(RESET)
          }
        }}
      >
        <canvas ref={canvasRef} className="terrain" aria-hidden="true" />
        {view ? (
          <svg className="ov" width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
            <g aria-hidden="true">
              {COLS.split('').map((c, i) => {
                const sx = (i * 100 + 50) * view.k + view.tx
                return sx < 12 || sx > W - 12 ? null : (
                  <g key={c}>
                    <rect x={sx - 9} y={0} width={18} height={16} className="gridref-bg" />
                    <text x={sx} y={12} textAnchor="middle" className="gridref">{c}</text>
                  </g>
                )
              })}
              {Array.from({ length: ROWS }, (_, r) => {
                const sy = (r * ROW_H + ROW_H / 2) * view.k + view.ty
                return sy < 12 || sy > H - 12 ? null : (
                  <g key={r}>
                    <rect x={0} y={sy - 9} width={16} height={18} className="gridref-bg" />
                    <text x={8} y={sy + 4} textAnchor="middle" className="gridref">{r + 1}</text>
                  </g>
                )
              })}
              {fieldLabels.map((f) => (
                <text key={f.id} x={f.x} y={f.y} textAnchor="middle" className={`flabel${hover.group === null ? '' : String(hover.group) === f.id ? ' on' : ' dim'}`} style={{ fontSize: fieldSize }}>
                  {f.text}
                </text>
              ))}
            </g>
            <g>
              {markers.map(({ p, sx, sy, r }) => (
                <g
                  key={p.id}
                  data-id={p.id}
                  className="mnode"
                  transform={`translate(${sx.toFixed(1)},${sy.toFixed(1)})`}
                  role="button"
                  tabIndex={0}
                  aria-label={describe(p)}
                  aria-pressed={p.id === selected}
                  onClick={() => onSelect(p.id)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      onSelect(p.id)
                    }
                  }}
                  onPointerEnter={(e) => {
                    enter(p)
                    tip.show(tipFor(p.id), e.clientX, e.clientY)
                  }}
                  onPointerLeave={() => {
                    leave()
                    tip.hide()
                  }}
                  onFocus={(e) => {
                    enter(p)
                    tip.showAt(tipFor(p.id), e.currentTarget)
                  }}
                  onBlur={() => {
                    leave()
                    tip.hide()
                  }}
                >
                  {p.id === selected ? (
                    <>
                      <circle r={r + 12} className="sel-ring2" />
                      <circle r={r + 7} className="sel-ring" />
                    </>
                  ) : null}
                  <circle r={Math.max(r + 5, 14)} className="hit" />
                  <path className={`mk mk-${p.status}`} d={glyphPath(p.status, r)} />
                </g>
              ))}
            </g>
            <g aria-hidden="true">
              {nameLabels.map((l) => (
                <text key={l.id} x={l.x} y={l.y} textAnchor={l.anchor} className={l.id === hover.id ? 'mlabel hover' : 'mlabel'}>
                  {l.text}
                </text>
              ))}
            </g>
          </svg>
        ) : null}
      </div>
      <div className="zoom" role="group" aria-label={controls.group}>
        <button type="button" aria-label={controls.zoomIn} onClick={() => zoom(1.4)}>
          <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path d="M8 2v12M2 8h12" stroke="currentColor" strokeWidth="2" /></svg>
        </button>
        <button type="button" aria-label={controls.zoomOut} onClick={() => zoom(1 / 1.4)}>
          <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path d="M2 8h12" stroke="currentColor" strokeWidth="2" /></svg>
        </button>
        <button type="button" aria-label={controls.reset} onClick={() => setUser(RESET)}>
          <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path d="M2.5 6V2.5H6M13.5 10v3.5H10M2.5 2.5l4 4M13.5 13.5l-4-4" fill="none" stroke="currentColor" strokeWidth="1.8" /></svg>
        </button>
      </div>
      <p className="map-hint">{controls.hint}</p>
    </div>
  )
}
