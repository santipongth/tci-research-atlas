import { useCallback, useMemo, useRef, useState } from 'react'
import { VIEW_H, VIEW_W, type AtlasNode } from '../data/atlas'
import { STR, fmt, pct, type Lang } from '../lib/i18n'
import type { AtlasData } from '../lib/loader'

interface Props {
  lang: Lang
  selected: string | null
  onSelect: (id: string | null) => void
  data: AtlasData
}

interface ViewT { k: number; x: number; y: number }
interface Tip { node: AtlasNode; left: number; top: number }

const ACCENT = '#FF5F1F'
const INK = '#161611'

export const STATUS_STYLE: Record<string, { th: string; en: string; color: string }> = {
  EMERGING: { th: 'กำลังเกิดใหม่', en: 'Emerging', color: '#FF5F1F' },
  HOT: { th: 'กำลังร้อน', en: 'Hot', color: '#E5484D' },
  DECLINING: { th: 'กำลังลดลง', en: 'Declining', color: '#697177' },
  STABLE: { th: 'คงที่', en: 'Stable', color: '#30A46C' },
}

export default function AtlasMap({ lang, selected, onSelect, data }: Props) {
  const { groups: GROUPS, nodes: NODES, links: LINKS, totalArticles: TOTAL_ARTICLES } = data
  const [view, setView] = useState<ViewT>({ k: 1, x: 0, y: 0 })
  const [tip, setTip] = useState<Tip | null>(null)
  const svgRef = useRef<SVGSVGElement>(null)
  const wrapRef = useRef<HTMLDivElement>(null)
  const drag = useRef<{ px: number; py: number; moved: boolean } | null>(null)

  const nodeById = useMemo(() => new Map(NODES.map((n) => [n.id, n])), [NODES])
  const selNode = selected ? nodeById.get(selected) ?? null : null
  const selGroupId = selNode ? (selNode.kind === 'group' ? selNode.id : selNode.group!) : null

  const clampK = (k: number) => Math.min(4, Math.max(0.55, k))

  const zoomAt = useCallback((clientX: number, clientY: number, factor: number) => {
    const svg = svgRef.current
    if (!svg) return
    const rect = svg.getBoundingClientRect()
    const sx = ((clientX - rect.left) / rect.width) * VIEW_W
    const sy = ((clientY - rect.top) / rect.height) * VIEW_H
    setView((v) => {
      const k = clampK(v.k * factor)
      return { k, x: sx - ((sx - v.x) * k) / v.k, y: sy - ((sy - v.y) * k) / v.k }
    })
  }, [])

  // non-passive wheel listener
  const wheelCb = useCallback(
    (e: WheelEvent) => {
      e.preventDefault()
      zoomAt(e.clientX, e.clientY, e.deltaY < 0 ? 1.15 : 1 / 1.15)
    },
    [zoomAt],
  )
  const svgCallbackRef = useCallback(
    (el: SVGSVGElement | null) => {
      if (svgRef.current) svgRef.current.removeEventListener('wheel', wheelCb)
      svgRef.current = el
      if (el) el.addEventListener('wheel', wheelCb, { passive: false })
    },
    [wheelCb],
  )

  const onPointerDown = (e: React.PointerEvent) => {
    drag.current = { px: e.clientX, py: e.clientY, moved: false }
    ;(e.target as Element).setPointerCapture?.(e.pointerId)
  }
  const onPointerMove = (e: React.PointerEvent) => {
    const svg = svgRef.current
    if (!drag.current || !svg) return
    const rect = svg.getBoundingClientRect()
    const dx = ((e.clientX - drag.current.px) / rect.width) * VIEW_W
    const dy = ((e.clientY - drag.current.py) / rect.height) * VIEW_H
    if (Math.abs(e.clientX - drag.current.px) + Math.abs(e.clientY - drag.current.py) > 3) drag.current.moved = true
    drag.current.px = e.clientX
    drag.current.py = e.clientY
    setView((v) => ({ ...v, x: v.x + dx, y: v.y + dy }))
  }
  const onPointerUp = () => {
    if (drag.current && !drag.current.moved) onSelect(null)
    drag.current = null
  }

  const showTip = (n: AtlasNode, e: React.MouseEvent) => {
    const wrap = wrapRef.current
    if (!wrap) return
    const rect = wrap.getBoundingClientRect()
    setTip({ node: n, left: e.clientX - rect.left + 14, top: e.clientY - rect.top - 10 })
  }

  const isDim = (n: AtlasNode) => {
    if (!selNode) return false
    if (n.id === selNode.id) return false
    if (selNode.kind === 'group') return n.kind === 'field' && n.group !== selNode.id
    return n.id !== selGroupId
  }

  const label = (n: AtlasNode) => (lang === 'th' ? n.th : n.en)

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_370px]">
      {/* ---- map stage ---- */}
      <div
        ref={wrapRef}
        className="atlas-dotgrid atlas-enter relative h-[62vh] min-h-[420px] overflow-hidden rounded-lg border border-[#161611]/12 lg:h-[76vh]"
      >
        <svg
          ref={svgCallbackRef}
          viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
          className="h-full w-full cursor-grab touch-none select-none active:cursor-grabbing"
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerLeave={() => { onPointerUp(); setTip(null) }}
          role="img"
          aria-label={STR.brandSub[lang]}
        >
          <g transform={`translate(${view.x} ${view.y}) scale(${view.k})`}>
            {/* ghost watermark */}
            <text
              x={VIEW_W - 30}
              y={VIEW_H - 26}
              textAnchor="end"
              className="font-mono-data"
              fontSize={150}
              fontWeight={600}
              fill={INK}
              opacity={0.045}
            >
              {fmt(TOTAL_ARTICLES)}
            </text>
            {/* links */}
            {LINKS.map((l, i) => {
              const a = nodeById.get(l.s)
              const b = nodeById.get(l.t)
              if (!a || !b) return null
              const hot = selNode && (l.s === selNode.id || (selNode.kind === 'group' && l.t === selNode.id))
              return (
                <line
                  key={i}
                  x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                  stroke={hot ? ACCENT : INK}
                  strokeOpacity={hot ? 0.55 : selNode ? 0.05 : 0.12}
                  strokeWidth={hot ? 1.6 : 1}
                />
              )
            })}
            {/* nodes: fields first, hubs on top */}
            {[...NODES].sort((a, b) => (a.kind === b.kind ? 0 : a.kind === 'field' ? -1 : 1)).map((n) => {
              const dim = isDim(n)
              const isSel = selNode?.id === n.id
              const fs = n.kind === 'group' ? Math.min(26, Math.max(14, n.r * 0.24)) : 12
              const showLabel = n.kind === 'group' || n.r >= 15
              // flip label above the node when it would clip the bottom edge
              const below = n.y + n.r + (n.kind === 'group' ? 44 : 20)
              const flip = below > VIEW_H - 14
              const ly = flip ? n.y - n.r - (n.kind === 'group' ? 26 : 10) : n.y + n.r + (n.kind === 'group' ? 20 : 15)
              return (
                <g
                  key={n.id}
                  className="atlas-node"
                  opacity={dim ? 0.15 : 1}
                  onClick={(e) => { e.stopPropagation(); onSelect(isSel ? null : n.id) }}
                  onMouseMove={(e) => showTip(n, e)}
                  onMouseLeave={() => setTip(null)}
                >
                  {isSel && (
                    <circle cx={n.x} cy={n.y} r={n.r + 6} fill="none" stroke={ACCENT} strokeWidth={2.5} />
                  )}
                  <circle
                    cx={n.x} cy={n.y} r={n.r}
                    fill={n.color}
                    fillOpacity={n.kind === 'group' ? 0.92 : 0.78}
                    stroke={INK}
                    strokeOpacity={0.4}
                    strokeWidth={n.kind === 'group' ? 1.2 : 0.7}
                  />
                  {/* emerging marker: small orange dot on topic's top-right */}
                  {n.status === 'EMERGING' && (
                    <circle cx={n.x + n.r * 0.75} cy={n.y - n.r * 0.75} r={Math.max(3, n.r * 0.16)}
                      fill={ACCENT} stroke="#f5f6f2" strokeWidth={1.5} />
                  )}
                  {showLabel && (
                    <text
                      x={n.x}
                      y={ly}
                      textAnchor="middle"
                      fontSize={fs}
                      fontWeight={n.kind === 'group' ? 600 : 400}
                      fill={INK}
                      className="atlas-label"
                      style={{ fontFamily: "'IBM Plex Sans Thai', sans-serif" }}
                    >
                      {label(n)}
                    </text>
                  )}
                  {n.kind === 'group' && (
                    <text
                      x={n.x}
                      y={flip ? ly + 17 : n.y + n.r + 38}
                      textAnchor="middle"
                      fontSize={12}
                      fill={INK}
                      opacity={0.55}
                      className="atlas-label font-mono-data"
                    >
                      {fmt(n.articles)}
                    </text>
                  )}
                </g>
              )
            })}
          </g>
        </svg>

        {/* tooltip */}
        {tip && (
          <div
            className="pointer-events-none absolute z-20 max-w-[260px] rounded-md border border-[#161611]/15 bg-white px-3 py-2 shadow-[8px_16px_16px_rgba(0,0,0,0.12)]"
            style={{ left: Math.min(tip.left, (wrapRef.current?.clientWidth ?? 400) - 280), top: tip.top }}
          >
            <div className="text-[13px] font-semibold leading-snug">{label(tip.node)}</div>
            <div className="text-[11.5px] text-[#161611]/55">{lang === 'th' ? tip.node.en : tip.node.th}</div>
            <div className="font-mono-data mt-1 text-[12px]">
              {fmt(tip.node.articles)} {STR.articles[lang]} · {pct(tip.node.articles, TOTAL_ARTICLES)}
            </div>
            {tip.node.status && (
              <div className="mt-1 text-[11px] font-medium" style={{ color: STATUS_STYLE[tip.node.status].color }}>
                ● {STATUS_STYLE[tip.node.status][lang]}
              </div>
            )}
          </div>
        )}

        {/* zoom controls */}
        <div className="absolute right-3 top-3 z-10 flex flex-col overflow-hidden rounded-md border border-[#161611]/15 bg-white">
          {[
            { label: '+', act: () => setView((v) => ({ ...v, k: clampK(v.k * 1.3) })), aria: 'zoom in' },
            { label: '−', act: () => setView((v) => ({ ...v, k: clampK(v.k / 1.3) })), aria: 'zoom out' },
            { label: '⌂', act: () => setView({ k: 1, x: 0, y: 0 }), aria: 'reset view' },
          ].map((b) => (
            <button
              key={b.aria}
              aria-label={b.aria}
              onClick={b.act}
              className="flex h-10 w-10 cursor-pointer items-center justify-center border-b border-[#161611]/10 font-mono-data text-[15px] text-[#161611]/70 transition-colors last:border-b-0 hover:bg-[#161611]/5 hover:text-[#161611] focus-visible:outline-2 focus-visible:outline-[#FF5F1F]"
            >
              {b.label}
            </button>
          ))}
        </div>

        {/* hint */}
        <div className="eyebrow pointer-events-none absolute bottom-3 left-4 text-[#161611]/45">
          {STR.hint[lang]}
        </div>
      </div>

      {/* ---- detail panel ---- */}
      <DetailPanel lang={lang} selNode={selNode} selGroupId={selGroupId} onSelect={onSelect} data={data} />

      {/* ---- legend ---- */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 lg:col-span-2">
        {GROUPS.map((g) => (
          <button
            key={g.id}
            onClick={() => onSelect(selGroupId === g.id ? null : g.id)}
            className={`flex min-h-[32px] cursor-pointer items-center gap-1.5 rounded-full px-2 py-1 text-[12px] transition-colors focus-visible:outline-2 focus-visible:outline-[#FF5F1F] ${
              selGroupId === g.id ? 'bg-[#161611] text-[#f5f6f2]' : 'text-[#161611]/70 hover:bg-[#161611]/5'
            }`}
          >
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ background: g.color, outline: selGroupId === g.id ? `2px solid ${ACCENT}` : 'none' }}
            />
            {lang === 'th' ? g.th : g.en}
          </button>
        ))}
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ */

function DetailPanel({
  lang, selNode, selGroupId, onSelect, data,
}: {
  lang: Lang
  selNode: AtlasNode | null
  selGroupId: string | null
  onSelect: (id: string | null) => void
  data: AtlasData
}) {
  const { groups: GROUPS, nodes: NODES, totalArticles: TOTAL_ARTICLES, totalFields, totalGroups } = data
  const group = selGroupId ? GROUPS.find((g) => g.id === selGroupId)! : null
  const members = group
    ? NODES.filter((n) => n.kind === 'field' && n.group === group.id).sort((a, b) => b.articles - a.articles)
    : []

  return (
    <aside className="h-fit rounded-lg border border-[#161611]/12 bg-white lg:sticky lg:top-20 lg:max-h-[76vh] lg:overflow-y-auto">
      {!selNode ? (
        <div className="p-5">
          <div className="eyebrow text-[#161611]/45">{STR.overview[lang]}</div>
          <div className="font-mono-data mt-3 text-[42px] font-semibold leading-none tracking-tight">
            {fmt(TOTAL_ARTICLES)}
          </div>
          <div className="mt-1 text-[13px] text-[#161611]/55">{STR.articles[lang]} · {fmt(totalFields)} {STR.fieldsUnit[lang]} · {totalGroups} {STR.groupsUnit[lang]}</div>
          <p className="mt-4 border-t border-dashed border-[#161611]/20 pt-4 text-[13.5px] leading-relaxed text-[#161611]/65">
            {STR.overviewSub[lang]}
          </p>
          <div className="mt-4 space-y-2.5">
            {GROUPS.slice(0, 5).map((g) => (
              <button
                key={g.id}
                onClick={() => onSelect(g.id)}
                className="group flex w-full cursor-pointer items-center gap-2.5 text-left focus-visible:outline-2 focus-visible:outline-[#FF5F1F]"
              >
                <span className="font-mono-data w-5 text-[11px] text-[#161611]/40">{g.rank}</span>
                <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: g.color }} />
                <span className="min-w-0 flex-1 truncate text-[13px] group-hover:underline group-hover:decoration-dashed group-hover:underline-offset-4">
                  {lang === 'th' ? g.th : g.en}
                </span>
                <span className="font-mono-data text-[12px] text-[#161611]/60">{pct(g.articles, TOTAL_ARTICLES)}</span>
              </button>
            ))}
          </div>
        </div>
      ) : selNode.kind === 'group' && group ? (
        <div className="p-5">
          <PanelHead eyebrow={`${STR.groupLabel[lang]} · ${STR.rank[lang]} ${group.rank}`} onClose={() => onSelect(null)} />
          <h3 className="font-display mt-3 text-[24px] font-semibold leading-snug">{lang === 'th' ? group.th : group.en}</h3>
          <div className="text-[13px] text-[#161611]/55">{lang === 'th' ? group.en : group.th}</div>
          <BigStat value={group.articles} lang={lang} />
          <ShareBar share={group.articles / TOTAL_ARTICLES} color={group.color} lang={lang} />
          <div className="eyebrow mt-5 text-[#161611]/45">
            {STR.memberFields[lang]} · {group.fieldCount}
          </div>
          <div className="mt-2 divide-y divide-[#161611]/8">
            {members.map((f) => (
              <button
                key={f.id}
                onClick={() => onSelect(f.id)}
                className="group flex w-full cursor-pointer items-baseline justify-between gap-3 py-2 text-left focus-visible:outline-2 focus-visible:outline-[#FF5F1F]"
              >
                <span className="min-w-0 text-[13.5px] leading-snug group-hover:underline group-hover:decoration-dashed group-hover:underline-offset-4">
                  {f.status === 'EMERGING' && <span className="mr-1.5 inline-block h-2 w-2 rounded-full align-middle" style={{ background: ACCENT }} />}
                  {lang === 'th' ? f.th : f.en}
                </span>
                <span className="font-mono-data shrink-0 text-[12px] text-[#161611]/60">{fmt(f.articles)}</span>
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="p-5">
          <PanelHead eyebrow={STR.fieldLabel[lang]} onClose={() => onSelect(null)} />
          <h3 className="font-display mt-3 text-[24px] font-semibold leading-snug">{lang === 'th' ? selNode.th : selNode.en}</h3>
          <div className="text-[13px] text-[#161611]/55">{lang === 'th' ? selNode.en : selNode.th}</div>
          {selNode.status && (
            <div className="mt-2 inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11.5px] font-medium"
              style={{ color: STATUS_STYLE[selNode.status].color, borderColor: STATUS_STYLE[selNode.status].color }}>
              ● {STATUS_STYLE[selNode.status][lang]}
              {selNode.emergingScore != null && (
                <span className="font-mono-data">· score {selNode.emergingScore}</span>
              )}
            </div>
          )}
          {selNode.description && (
            <p className="mt-3 text-[13px] leading-relaxed text-[#161611]/65">{selNode.description}</p>
          )}
          <BigStat value={selNode.articles} lang={lang} />
          <ShareBar share={selNode.articles / TOTAL_ARTICLES} color={selNode.color} lang={lang} />
          {selNode.keywords && (
            <div className="mt-4 flex flex-wrap gap-1.5">
              {selNode.keywords.split(';').map((k) => k.trim()).filter(Boolean).slice(0, 6).map((k) => (
                <span key={k} className="rounded-full bg-[#161611]/6 px-2.5 py-1 text-[11.5px] text-[#161611]/70">{k}</span>
              ))}
            </div>
          )}
          {selNode.forecast && <ForecastChart lang={lang} forecast={selNode.forecast} color={selNode.color} />}
          {group && (
            <button
              onClick={() => onSelect(group.id)}
              className="mt-5 flex min-h-[36px] w-full cursor-pointer items-center gap-2 rounded-md border border-[#161611]/15 px-3 py-2 text-left text-[13px] transition-colors hover:bg-[#161611]/5 focus-visible:outline-2 focus-visible:outline-[#FF5F1F]"
            >
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: group.color }} />
              <span className="text-[#161611]/55">{STR.belongsTo[lang]}:</span>
              <span className="font-medium">{lang === 'th' ? group.th : group.en}</span>
            </button>
          )}
        </div>
      )}
    </aside>
  )
}

/** History + forecast with confidence band (pure SVG, no chart lib). */
function ForecastChart({ lang, forecast, color }: { lang: Lang; forecast: NonNullable<AtlasNode['forecast']>; color: string }) {
  const W = 320, H = 120, PAD = 8
  const years = [...forecast.hist_years, ...forecast.fc_years]
  const allY = [...forecast.hist_counts, ...forecast.fc_mean, ...forecast.fc_hi]
  const maxY = Math.max(...allY, 1)
  const n = years.length
  const px = (i: number) => PAD + (i / (n - 1)) * (W - 2 * PAD)
  const py = (v: number) => H - PAD - (v / maxY) * (H - 2 * PAD)

  const histPts = forecast.hist_counts.map((v, i) => `${px(i)},${py(v)}`).join(' ')
  const hLen = forecast.hist_counts.length
  const fcPts = forecast.fc_mean.map((v, i) => `${px(hLen - 1 + i + 0)},${py(v)}`)
  // start forecast line at last history point
  fcPts.unshift(`${px(hLen - 1)},${py(forecast.hist_counts[hLen - 1])}`)
  const band = [
    ...forecast.fc_hi.map((v, i) => `${px(hLen + i)},${py(v)}`),
    ...forecast.fc_lo.map((v, i) => `${px(hLen + i)},${py(v)}`).reverse(),
    `${px(hLen - 1)},${py(forecast.hist_counts[hLen - 1])}`,
  ].join(' ')

  return (
    <div className="mt-5 border-t border-dashed border-[#161611]/20 pt-4">
      <div className="flex items-baseline justify-between">
        <span className="eyebrow text-[#161611]/45">{lang === 'th' ? 'แนวโน้ม + คาดการณ์' : 'Trend + forecast'}</span>
        <span className="font-mono-data text-[10.5px] text-[#161611]/40">
          {forecast.model} · MAPE {forecast.backtest_mape}%
        </span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="mt-2 w-full">
        <polygon points={band} fill={color} opacity={0.12} />
        <polyline points={histPts} fill="none" stroke={INK} strokeWidth={1.8} />
        <polyline points={fcPts.join(' ')} fill="none" stroke={color} strokeWidth={1.8} strokeDasharray="4 3" />
        {forecast.hist_counts.map((v, i) => (
          <circle key={i} cx={px(i)} cy={py(v)} r={2} fill={INK} />
        ))}
      </svg>
      <div className="mt-1 flex justify-between font-mono-data text-[10.5px] text-[#161611]/45">
        <span>{years[0]}</span>
        <span className="text-[#161611]/35">{lang === 'th' ? 'เส้นประ = คาดการณ์ ±95%' : 'dashed = forecast ±95%'}</span>
        <span>{years[years.length - 1]}</span>
      </div>
    </div>
  )
}

function PanelHead({ eyebrow, onClose }: { eyebrow: string; onClose: () => void }) {
  return (
    <div className="flex items-center justify-between">
      <div className="eyebrow text-[#161611]/45">{eyebrow}</div>
      <button
        onClick={onClose}
        aria-label="close"
        className="flex h-8 w-8 cursor-pointer items-center justify-center rounded-full text-[#161611]/50 transition-colors hover:bg-[#161611]/5 hover:text-[#161611] focus-visible:outline-2 focus-visible:outline-[#FF5F1F]"
      >
        ×
      </button>
    </div>
  )
}

function BigStat({ value, lang }: { value: number; lang: Lang }) {
  return (
    <div className="mt-4">
      <div className="font-mono-data text-[40px] font-semibold leading-none tracking-tight">{fmt(value)}</div>
      <div className="mt-1 text-[13px] text-[#161611]/55">{STR.articles[lang]}</div>
    </div>
  )
}

function ShareBar({ share, color, lang }: { share: number; color: string; lang: Lang }) {
  return (
    <div className="mt-4">
      <div className="flex items-baseline justify-between">
        <span className="eyebrow text-[#161611]/45">{STR.share[lang]}</span>
        <span className="font-mono-data text-[14px] font-semibold" style={{ color }}>{(share * 100).toFixed(2)}%</span>
      </div>
      <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-[#161611]/8">
        <div className="h-full rounded-full" style={{ width: `${Math.max(0.6, share * 100)}%`, background: color }} />
      </div>
      <div className="mt-1 text-[11.5px] text-[#161611]/45">{STR.ofTotal[lang]}</div>
    </div>
  )
}
