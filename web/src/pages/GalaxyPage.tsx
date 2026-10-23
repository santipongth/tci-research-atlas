import { useEffect, useMemo, useRef, useState, type KeyboardEvent, type PointerEvent as ReactPointerEvent } from 'react'
import { Link } from 'react-router'
import { galaxyPicks } from '../charts/editorLayout'
import { DataTable, type Column } from '../components/DataTable'
import { EmptyState } from '../components/EmptyState'
import { Figure } from '../components/Figure'
import { ModuleFile } from '../components/ModuleFile'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { TopicLink } from '../components/TopicLink'
import { useReleaseFile, type FileState } from '../data/atlasContext'
import { groupName, hasModule, MODULE_FILES, searchDocsPath, type AtlasRelease } from '../data/release'
import type { GalaxyFile, SearchDocShard, SearchMeta, Topic } from '../data/types'
import { placeCentered, tintTokens } from '../features/atlas/mapSpace'
import { fmtInt } from '../lib/format'
import {
  buildGrid, combineView, createRenderer, fitView, inFilter, nearest, NEUTRAL_SLOT, pointAlpha, pointSize, preparePoints, resolvePalette, rgbCss,
  RESET_VIEW, supportsWebGL2, toScreen, toWorld, zoomAt, type GalaxyPoints, type GalaxyRenderer, type Palette, type PickGrid, type PointFilter, type UserView,
} from '../lib/galaxyGl'
import { useI18n, useStrings } from '../lib/i18n'
import { textWidth } from '../lib/measure'
import { LABEL_PX } from '../lib/labelSizes'
import { rowToDoc } from '../lib/searchClient'
import { docShardOf } from '../lib/searchTokens'
import { useTheme } from '../lib/theme'
import { galaxyCodec } from '../lib/urlState'
import { useElementSize } from '../lib/useElementSize'
import { useFontsVersion } from '../lib/useFontsVersion'
import { useUrlState } from '../lib/useUrlState'
import { galaxy } from '../strings/galaxy'

/** Thai script (U+0E00–U+0E7F), built from code points: the codebase never writes a backslash-u escape. */
const THAI = new RegExp(`[${String.fromCodePoint(0x0e00)}-${String.fromCodePoint(0x0e7f)}]`)
const langOf = (text: string) => (THAI.test(text) ? 'th' : 'en')
const PAN: Record<string, [number, number]> = { ArrowLeft: [60, 0], ArrowRight: [-60, 0], ArrowUp: [0, 60], ArrowDown: [0, -60] }
/** hover / tap reach around the pointer (CSS px); Enter looks a little further around the centre */
const PICK_PX = 12
const CENTRE_PX = 36
/** the card follows the pointer after it rests this long (doc shards are fetched on demand) */
const HOVER_MS = 120
/** from this zoom on, topic names replace field names */
const TOPIC_LABEL_ZOOM = 2.5

export default function GalaxyPage() {
  const s = useStrings(galaxy)
  return (
    <RequireRelease title={s('title')}>
      {(release) => (
        <ModuleFile<GalaxyFile> release={release} module="galaxy" path={MODULE_FILES.galaxy} title={s('title')}>
          {(file) => <Galaxy release={release} file={file} />}
        </ModuleFile>
      )}
    </RequireRelease>
  )
}

function Galaxy({ release, file }: { release: AtlasRelease; file: GalaxyFile }) {
  const [gl] = useState(supportsWebGL2)
  return gl ? <GalaxyBody release={release} file={file} /> : <NoWebGL />
}

function NoWebGL() {
  const s = useStrings(galaxy)
  return (
    <div className="container">
      <PageHeader title={s('title')} />
      <EmptyState title={s('nogl.h')}>
        <p>{s('nogl.body')}</p>
        <p><Link to="/atlas">{s('nogl.link')}</Link></p>
      </EmptyState>
    </div>
  )
}

interface LabelSpot {
  id: string
  text: string
  x: number
  y: number
  n: number
}

/** Size-weighted centre of each group's topics (topics.json coordinates = galaxy bounds). */
function fieldSpots(release: AtlasRelease, lang: 'th' | 'en', present: ReadonlySet<string>): LabelSpot[] {
  const acc = new Map<string, { x: number; y: number; n: number }>()
  for (const t of release.topics) {
    if (!present.has(t.group)) continue
    const w = Math.max(1, t.size)
    const a = acc.get(t.group) ?? { x: 0, y: 0, n: 0 }
    acc.set(t.group, { x: a.x + t.x * w, y: a.y + t.y * w, n: a.n + w })
  }
  return [...acc].map(([id, a]) => ({ id, text: groupName(release, id, lang), x: a.x / a.n, y: a.y / a.n, n: a.n })).sort((a, b) => b.n - a.n)
}

function GalaxyBody({ release, file }: { release: AtlasRelease; file: GalaxyFile }) {
  const s = useStrings(galaxy)
  const { t, lang } = useI18n()
  const [state, update] = useUrlState(galaxyCodec)
  const theme = useTheme()
  const groups = release.taxonomy.groups
  const tokens = useMemo(() => tintTokens(groups), [groups])
  const slotOf = useMemo(() => new Map(groups.map((g, i) => [g.id, i < NEUTRAL_SLOT ? i : NEUTRAL_SLOT])), [groups])
  const points = useMemo(
    () => preparePoints(file, (code) => {
      const tp = release.topicById.get(code)
      return tp ? (slotOf.get(tp.group) ?? NEUTRAL_SLOT) : NEUTRAL_SLOT
    }),
    [file, release, slotOf],
  )
  const grid = useMemo(() => buildGrid(points.wx, points.wy, points.bounds), [points])
  // the theme's token values: re-read whenever the theme changes (explicit toggle or the OS preference)
  const palette = useMemo(() => {
    const css = getComputedStyle(document.documentElement)
    return resolvePalette(tokens, theme, (name) => css.getPropertyValue(name))
  }, [tokens, theme])

  const slot = state.g && slotOf.has(state.g) ? (slotOf.get(state.g) as number) : null
  const filter = useMemo<PointFilter>(() => ({ from: state.from, to: state.to, slot }), [state.from, state.to, slot])
  const years = useMemo(() => [...new Set(points.yr)].sort((a, b) => a - b), [points])
  const perSlot = useMemo(() => {
    const n = new Map<number, number>()
    for (let i = 0; i < points.count; i++) n.set(points.slot[i], (n.get(points.slot[i]) ?? 0) + 1)
    return n
  }, [points])
  const shown = useMemo(() => {
    let n = 0
    for (let i = 0; i < points.count; i++) if (inFilter(points, i, filter)) n++
    return n
  }, [points, filter])
  const fields = useMemo(
    () => groups.map((g, i) => ({ g, slot: slotOf.get(g.id) as number, n: perSlot.get(i) ?? 0 })).filter((f) => f.n > 0 && f.slot !== NEUTRAL_SLOT).sort((a, b) => b.n - a.n),
    [groups, slotOf, perSlot],
  )
  const noField = perSlot.get(NEUTRAL_SLOT) ?? 0
  const present = useMemo(() => new Set(fields.map((f) => f.g.id)), [fields])
  const spots = useMemo(() => fieldSpots(release, lang, present), [release, lang, present])
  const topicSpots = useMemo(
    () => release.topics.map((tp) => ({ id: tp.id, text: lang === 'en' ? tp.en || tp.th : tp.th || tp.en, x: tp.x, y: tp.y, n: tp.size })).sort((a, b) => b.n - a.n),
    [release, lang],
  )

  const meta = useReleaseFile<SearchMeta>(hasModule(release, 'search') ? MODULE_FILES.search : null)
  const [sel, setSel] = useState<number | null>(null)
  const [hover, setHover] = useState<number | null>(null)
  const [preview, setPreview] = useState<number | null>(null)
  const [missed, setMissed] = useState(false)
  const timer = useRef(0)
  useEffect(() => () => window.clearTimeout(timer.current), [])
  const onHover = (i: number | null) => {
    setHover(i)
    window.clearTimeout(timer.current)
    timer.current = window.setTimeout(() => setPreview(i), HOVER_MS)
  }
  const onPick = (i: number | null, fromKeyboard = false) => {
    setSel(i)
    setMissed(fromKeyboard && i === null)
  }
  const cardPoint = sel ?? preview
  // three example articles from the largest fields, for the empty side panel
  const picks = useMemo(() => galaxyPicks(points, fields.map((f) => f.slot), 3), [points, fields])

  const filtering = state.from !== null || state.to !== null || slot !== null
  const rel = release.overview.release
  const tableRows = slot === null ? release.topics : release.topics.filter((tp) => slotOf.get(tp.group) === slot)
  const columns: Column<Topic>[] = [
    { key: 'topic', header: s('tbl.topic'), cell: (tp) => <TopicLink topic={tp} />, sortValue: (tp) => (lang === 'en' ? tp.en || tp.th : tp.th || tp.en), rowHeader: true, csvCols: [{ header: 'topic_id', value: (tp) => tp.id }, { header: 'name_th', value: (tp) => tp.th }, { header: 'name_en', value: (tp) => tp.en }] },
    { key: 'field', header: s('tbl.field'), cell: (tp) => groupName(release, tp.group, lang), sortValue: (tp) => groupName(release, tp.group, lang), csvHeader: 'group', csv: (tp) => tp.group },
    { key: 'articles', header: s('tbl.articles'), cell: (tp) => fmtInt(tp.size), sortValue: (tp) => tp.size, numeric: true, csvHeader: 'size' },
  ]

  const legend = (
    <div className="gx-legend">
      <p className="gx-legend-h" id="gx-legend-h">{s('legend')}</p>
      <ul className="gx-keys" aria-labelledby="gx-legend-h">
        {fields.map((f) => (
          <li key={f.g.id} className={slot !== null && slot !== f.slot ? 'is-dim' : undefined}>
            <span className="gx-swatch" style={{ background: rgbCss(palette.slots[f.slot]) }} aria-hidden="true" />
            <span>{lang === 'en' ? f.g.en || f.g.th : f.g.th || f.g.en}</span>
            <span className="gx-key-n">{fmtInt(f.n)}</span>
          </li>
        ))}
        {noField > 0 ? (
          <li className={slot !== null ? 'is-dim' : undefined}>
            <span className="gx-swatch" style={{ background: rgbCss(palette.slots[NEUTRAL_SLOT]) }} aria-hidden="true" />
            <span>{s('legend.none')}</span>
            <span className="gx-key-n">{fmtInt(noField)}</span>
          </li>
        ) : null}
      </ul>
      {fields.length > 8 ? <p className="hint">{s('legend.note')}</p> : null}
    </div>
  )

  return (
    <div className="container">
      <PageHeader title={s('title')} lede={s('lede', { n: fmtInt(points.total) })} />
      <fieldset className="j-tools gx-filters">
        <legend className="sr-only">{s('f.h')}</legend>
        <label>
          {s('f.from')}
          <select value={state.from ?? ''} onChange={(e) => update({ from: e.target.value ? Number(e.target.value) : null })}>
            <option value="">{s('f.any')}</option>
            {years.map((y) => <option key={y} value={y}>{y}</option>)}
          </select>
        </label>
        <label>
          {s('f.to')}
          <select value={state.to ?? ''} onChange={(e) => update({ to: e.target.value ? Number(e.target.value) : null })}>
            <option value="">{s('f.any')}</option>
            {years.map((y) => <option key={y} value={y}>{y}</option>)}
          </select>
        </label>
        <label>
          {s('f.group')}
          <select value={slot === null ? '' : state.g} onChange={(e) => update({ g: e.target.value })}>
            <option value="">{s('f.any')}</option>
            {fields.map((f) => <option key={f.g.id} value={f.g.id}>{`${lang === 'en' ? f.g.en || f.g.th : f.g.th || f.g.en} (${fmtInt(f.n)})`}</option>)}
          </select>
        </label>
        {filtering ? <button type="button" className="btn-secondary" onClick={() => update({ from: null, to: null, g: '' })}>{s('f.reset')}</button> : null}
      </fieldset>
      <p className="gx-count" role="status">
        {filtering ? s('shown', { shown: fmtInt(shown), n: fmtInt(points.count) }) : s('shownAll', { n: fmtInt(points.count) })}
      </p>
      {points.total > points.count ? <p className="hint">{s('noCoord', { n: fmtInt(points.total - points.count) })}</p> : null}

      <div className="gx-sec">
        <Figure
          id="gx"
          number={1}
          title={s('fig.title')}
          source={t('source.line', { release: rel })}
          view={state.view}
          onView={(v) => update({ view: v })}
          chart={
            <div className="gx-layout">
              <Stage
                points={points}
                grid={grid}
                palette={palette}
                filter={filter}
                sel={sel}
                hover={hover}
                onHover={onHover}
                onPick={onPick}
                fields={spots}
                topics={topicSpots}
              />
              <aside className="gx-side" aria-labelledby="gx-card-h">
                <h2 className="gx-card-h" id="gx-card-h">{s('card.h')}</h2>
                {cardPoint === null ? (
                  <>
                    <p className="gx-card-empty" aria-live="polite">{missed ? s('card.none') : s('card.empty')}</p>
                    {picks.length ? (
                      <div className="gx-try">
                        <p className="gx-try-h" id="gx-try-h">{s('try.h')}</p>
                        <p className="hint">{s('try.intro')}</p>
                        <ul className="gx-try-list" aria-labelledby="gx-try-h">
                          {picks.map((i) => {
                            const tp = release.topicById.get(file.topics[points.topic[i]])
                            if (!tp) return null
                            return (
                              <li key={i}>
                                <button type="button" className="gx-try-btn" onClick={() => onPick(i)}>
                                  <span className="gx-swatch" style={{ background: rgbCss(palette.slots[points.slot[i]]) }} aria-hidden="true" />
                                  <span className="gx-try-t">{s('try.pick', { t: lang === 'en' ? tp.en || tp.th : tp.th || tp.en })}</span>
                                  <span className="gx-try-f">{groupName(release, tp.group, lang)} · {points.yr[i]}</span>
                                </button>
                              </li>
                            )
                          })}
                        </ul>
                      </div>
                    ) : null}
                  </>
                ) : (
                  <Card key={cardPoint} release={release} file={file} points={points} index={cardPoint} meta={meta} palette={palette} pinned={sel !== null} onClear={() => onPick(null)} />
                )}
                {legend}
              </aside>
            </div>
          }
          table={
            <DataTable
              caption={t('table.n', { n: 1, title: s('tbl.title') })}
              rows={tableRows}
              columns={columns}
              rowKey={(tp) => tp.id}
              defaultSort={{ key: 'articles', dir: 'desc' }}
              csvFilename={`atlas-${rel}-galaxy-topics.csv`}
              empty={s('tbl.empty')}
            />
          }
        />
      </div>
    </div>
  )
}

function Stage({ points, grid, palette, filter, sel, hover, onHover, onPick, fields, topics }: {
  points: GalaxyPoints
  grid: PickGrid
  palette: Palette
  filter: PointFilter
  sel: number | null
  hover: number | null
  onHover: (i: number | null) => void
  onPick: (i: number | null, fromKeyboard?: boolean) => void
  fields: readonly LabelSpot[]
  topics: readonly LabelSpot[]
}) {
  const s = useStrings(galaxy)
  const [wrapRef, size, wrapEl] = useElementSize<HTMLDivElement>()
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const renderer = useRef<GalaxyRenderer | null>(null)
  const [user, setUser] = useState<UserView>(RESET_VIEW)
  const [lost, setLost] = useState(false)
  const [failed, setFailed] = useState(false)
  const fontsVersion = useFontsVersion()
  const W = size.width
  const H = size.height
  const view = useMemo(() => (W > 0 && H > 0 ? combineView(fitView(points.bounds, W, H), user, W, H) : null), [W, H, user, points.bounds])
  const pointers = useRef(new Map<number, { x: number; y: number }>())
  const gesture = useRef<{ kind: 'pan'; x: number; y: number; from: UserView; moved: boolean } | { kind: 'pinch'; d0: number; from: UserView; mx: number; my: number } | null>(null)
  const frame = useRef(0)
  const next = useRef<UserView | null>(null)

  // one renderer per canvas and point set; GL resources are released on unmount
  useEffect(() => {
    const cv = canvasRef.current
    if (!cv) return
    const r = createRenderer(cv, points, { onLost: () => setLost(true), onRestored: () => setLost(false) })
    renderer.current = r
    if (!r) {
      const id = requestAnimationFrame(() => setFailed(true))
      return () => cancelAnimationFrame(id)
    }
    return () => {
      r.dispose()
      renderer.current = null
    }
  }, [points])
  useEffect(() => () => cancelAnimationFrame(frame.current), [])

  // draw on every change of view, size, filter or colours (one draw call; cheap)
  useEffect(() => {
    const r = renderer.current
    if (!r || !view) return
    r.draw({ view, width: W, height: H, dpr: Math.min(2, window.devicePixelRatio || 1), size: pointSize(points.count, user.s), alpha: pointAlpha(points.count), filter, palette })
  }, [view, W, H, points, user.s, filter, palette, lost])

  // Ctrl/⌘ + wheel (and a trackpad pinch) zooms about the pointer; a plain wheel keeps scrolling the page, as on /atlas
  useEffect(() => {
    if (!wrapEl) return
    const onWheel = (e: WheelEvent) => {
      if (!(e.ctrlKey || e.metaKey)) return
      e.preventDefault()
      const r = wrapEl.getBoundingClientRect()
      const f = Math.exp(-Math.max(-60, Math.min(60, e.deltaY)) * 0.006)
      const x = e.clientX - r.left - wrapEl.clientLeft
      const y = e.clientY - r.top - wrapEl.clientTop
      setUser((u) => zoomAt(u, f, x, y, wrapEl.clientWidth, wrapEl.clientHeight))
    }
    wrapEl.addEventListener('wheel', onWheel, { passive: false })
    return () => wrapEl.removeEventListener('wheel', onWheel)
  }, [wrapEl])

  const schedule = (u: UserView) => {
    next.current = u
    if (!frame.current) {
      frame.current = requestAnimationFrame(() => {
        frame.current = 0
        if (next.current) setUser(next.current)
      })
    }
  }
  const local = (e: ReactPointerEvent<HTMLDivElement>) => {
    const el = e.currentTarget
    const r = el.getBoundingClientRect()
    // the canvas fills the padding box: measure from inside the border
    return { x: e.clientX - r.left - el.clientLeft, y: e.clientY - r.top - el.clientTop }
  }
  const pickAt = (x: number, y: number, px: number) => {
    if (!view) return -1
    const [wx, wy] = toWorld(view, x, y)
    return nearest(grid, wx, wy, px / view.k, (i) => inFilter(points, i, filter))
  }
  const zoom = (factor: number) => setUser((u) => zoomAt(u, factor, W / 2, H / 2, W, H))

  const onPointerDown = (e: ReactPointerEvent<HTMLDivElement>) => {
    const p = local(e)
    pointers.current.set(e.pointerId, p)
    e.currentTarget.setPointerCapture(e.pointerId)
    if (pointers.current.size === 1) gesture.current = { kind: 'pan', x: p.x, y: p.y, from: user, moved: false }
    else if (pointers.current.size === 2) {
      const [a, b] = [...pointers.current.values()]
      gesture.current = { kind: 'pinch', d0: Math.max(1, Math.hypot(a.x - b.x, a.y - b.y)), from: user, mx: (a.x + b.x) / 2, my: (a.y + b.y) / 2 }
    }
  }
  const onPointerMove = (e: ReactPointerEvent<HTMLDivElement>) => {
    const p = local(e)
    const g = gesture.current
    if (pointers.current.has(e.pointerId)) pointers.current.set(e.pointerId, p)
    if (g?.kind === 'pan') {
      const mx = p.x - g.x
      const my = p.y - g.y
      if (!g.moved && Math.abs(mx) + Math.abs(my) < 4) return
      g.moved = true
      if (hover !== null) onHover(null)
      schedule({ ...g.from, dx: g.from.dx + mx, dy: g.from.dy + my })
    } else if (g?.kind === 'pinch' && pointers.current.size >= 2) {
      const [a, b] = [...pointers.current.values()]
      schedule(zoomAt(g.from, Math.hypot(a.x - b.x, a.y - b.y) / g.d0, g.mx, g.my, W, H))
    } else if (!g && e.pointerType === 'mouse') {
      const i = pickAt(p.x, p.y, PICK_PX)
      const found = i >= 0 ? i : null
      if (found !== hover) onHover(found)
    }
  }
  const onPointerUp = (e: ReactPointerEvent<HTMLDivElement>) => {
    const g = gesture.current
    pointers.current.delete(e.pointerId)
    if (g?.kind === 'pan' && !g.moved) {
      const p = local(e)
      const i = pickAt(p.x, p.y, e.pointerType === 'mouse' ? PICK_PX : PICK_PX * 2)
      onPick(i >= 0 ? i : null)
    }
    if (pointers.current.size === 0 || g?.kind === 'pinch') gesture.current = null
  }
  const onPointerCancel = (e: ReactPointerEvent<HTMLDivElement>) => {
    pointers.current.delete(e.pointerId)
    gesture.current = null
  }
  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.target !== e.currentTarget) return
    const move = PAN[e.key]
    if (move) {
      e.preventDefault()
      setUser((u) => ({ ...u, dx: u.dx + move[0], dy: u.dy + move[1] }))
    } else if (e.key === '+' || e.key === '=') {
      e.preventDefault()
      zoom(1.5)
    } else if (e.key === '-' || e.key === '_') {
      e.preventDefault()
      zoom(1 / 1.5)
    } else if (e.key === '0') {
      e.preventDefault()
      setUser(RESET_VIEW)
    } else if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      const i = pickAt(W / 2, H / 2, CENTRE_PX)
      onPick(i >= 0 ? i : null, true)
    } else if (e.key === 'Escape') {
      onPick(null)
    }
  }

  // field names (or, zoomed in, topic names) centred on their place; a name that would collide or leave the frame is dropped
  const labels = useMemo(() => {
    if (!view) return []
    const zoomed = user.s >= TOPIC_LABEL_ZOOM
    const px = zoomed || W < 600 ? LABEL_PX.label : LABEL_PX.strong
    const weight = zoomed ? 600 : 700
    const pool = zoomed ? topics : fields
    const cands = pool
      .map((l) => {
        const [x, y] = toScreen(view, l.x, l.y)
        return { id: l.id, text: l.text, width: textWidth(l.text, px, weight), height: px, x, y }
      })
      .filter((c) => c.x > -c.width && c.x < W + c.width && c.y > 0 && c.y < H + c.height)
      .slice(0, zoomed ? 40 : 30)
    return placeCentered(cands, { x: 8, y: 8, w: W - 16, h: H - 16 }).map((l) => ({ ...l, cls: zoomed ? 'gx-tlabel' : 'gx-flabel' }))
    // eslint-disable-next-line react-hooks/exhaustive-deps -- fontsVersion re-measures text once Sarabun has loaded
  }, [view, user.s, fields, topics, W, H, fontsVersion])

  const ring = (i: number | null, cls: string) => {
    if (i === null || !view) return null
    const [x, y] = toScreen(view, points.wx[i], points.wy[i])
    if (x < -20 || y < -20 || x > W + 20 || y > H + 20) return null
    const r = pointSize(points.count, user.s) / 2 + (cls === 'gx-sel' ? 6 : 4)
    return (
      <g className={cls} transform={`translate(${x.toFixed(1)},${y.toFixed(1)})`}>
        <circle r={r + 2} className="gx-ring-out" />
        <circle r={r} className="gx-ring-in" />
      </g>
    )
  }

  return (
    <div className="gx-frame">
      <div
        ref={wrapRef}
        className={hover !== null ? 'gx-stage is-over' : 'gx-stage'}
        tabIndex={0}
        role="group"
        aria-label={s('fig.label')}
        aria-describedby="gx-hint"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerCancel}
        onPointerLeave={(e) => {
          if (e.pointerType === 'mouse' && !gesture.current) onHover(null)
        }}
        onKeyDown={onKeyDown}
      >
        <canvas ref={canvasRef} className="gx-canvas" aria-hidden="true" />
        {view ? (
          <svg className="gx-ov" width={W} height={H} viewBox={`0 0 ${W} ${H}`} aria-hidden="true">
            {labels.map((l) => (
              <text key={l.id} x={l.x} y={l.y} textAnchor="middle" className={l.cls}>{l.text}</text>
            ))}
            {hover !== sel ? ring(hover, 'gx-hover') : null}
            {ring(sel, 'gx-sel')}
          </svg>
        ) : null}
        <span className="gx-cross" aria-hidden="true" />
        {lost || failed ? <p className="gx-lost" role="status">{failed ? s('failed') : s('lost')}</p> : null}
      </div>
      <div className="zoom gx-zoom" role="group" aria-label={s('zoom.group')}>
        <button type="button" aria-label={s('zoom.in')} onClick={() => zoom(1.5)}>
          <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path d="M8 2v12M2 8h12" stroke="currentColor" strokeWidth="2" /></svg>
        </button>
        <button type="button" aria-label={s('zoom.out')} onClick={() => zoom(1 / 1.5)}>
          <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path d="M2 8h12" stroke="currentColor" strokeWidth="2" /></svg>
        </button>
        <button type="button" aria-label={s('zoom.reset')} onClick={() => setUser(RESET_VIEW)}>
          <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path d="M2.5 6V2.5H6M13.5 10v3.5H10M2.5 2.5l4 4M13.5 13.5l-4-4" fill="none" stroke="currentColor" strokeWidth="1.8" /></svg>
        </button>
      </div>
      <p className="map-hint" id="gx-hint">{s('hint')}</p>
    </div>
  )
}

function Card({ release, file, points, index, meta, palette, pinned, onClear }: {
  release: AtlasRelease
  file: GalaxyFile
  points: GalaxyPoints
  index: number
  meta: FileState<SearchMeta>
  palette: Palette
  pinned: boolean
  onClear: () => void
}) {
  const s = useStrings(galaxy)
  const { t, lang } = useI18n()
  const ord = points.ord[index]
  const year = points.yr[index]
  const ti = points.topic[index]
  const topic = ti >= 0 ? release.topicById.get(file.topics[ti]) : undefined
  const docs = useReleaseFile<SearchDocShard>(meta.status === 'ready' ? searchDocsPath(docShardOf(ord, meta.data.docs_per_shard)) : null)
  const row = docs.status === 'ready' ? docs.data.docs[ord - docs.data.start] : undefined
  const doc = row && meta.status === 'ready' ? rowToDoc(row, ord, meta.data.journals) : null
  const [main, sub] = doc ? (lang === 'en' ? [doc.titleEn || doc.titleTh, doc.titleEn ? doc.titleTh : ''] : [doc.titleTh || doc.titleEn, doc.titleTh ? doc.titleEn : '']) : ['', '']
  const loading = meta.status === 'loading' || (meta.status === 'ready' && docs.status === 'loading')
  const failed = meta.status === 'error' || docs.status === 'error' || (docs.status === 'ready' && !row)
  return (
    <div className="gx-card" aria-live={pinned ? 'polite' : 'off'}>
      {doc ? (
        <>
          <p className="gx-title" lang={langOf(main)}>{main}</p>
          {sub ? <p className="gx-sub" lang={langOf(sub)}>{sub}</p> : null}
        </>
      ) : loading ? (
        <p className="loading">{s('card.loading')}</p>
      ) : failed ? (
        <p className="note">{s('card.error')}</p>
      ) : (
        <p className="hint">{s('card.noDocs')}</p>
      )}
      <dl className="gx-facts">
        {doc?.journal ? (
          <div><dt>{s('card.journal')}</dt><dd>{doc.journal}</dd></div>
        ) : null}
        <div><dt>{s('card.year')}</dt><dd>{year}</dd></div>
        <div><dt>{s('card.topic')}</dt><dd>{topic ? <TopicLink topic={topic} /> : s('card.noTopic')}</dd></div>
        {topic ? (
          <div>
            <dt>{s('card.field')}</dt>
            <dd className="gx-field">
              <span className="gx-swatch" style={{ background: rgbCss(palette.slots[points.slot[index]]) }} aria-hidden="true" />
              {groupName(release, topic.group, lang)}
            </dd>
          </div>
        ) : null}
      </dl>
      {doc?.url || doc?.doi || pinned ? (
        <div className="gx-actions">
          {doc?.url ? (
            <a className="btn" href={doc.url} target="_blank" rel="noopener noreferrer">{s('card.read')}<span className="sr-only"> {t('newTab')}</span></a>
          ) : null}
          {doc?.doi ? (
            <a href={`https://doi.org/${doc.doi}`} target="_blank" rel="noopener noreferrer">{s('card.doi')} {doc.doi}<span className="sr-only"> {t('newTab')}</span></a>
          ) : null}
          {pinned ? <button type="button" className="btn-secondary" onClick={onClear}>{s('card.clear')}</button> : null}
        </div>
      ) : null}
    </div>
  )
}
