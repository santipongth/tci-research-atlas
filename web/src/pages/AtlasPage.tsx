import { useMemo, useRef } from 'react'
import { SeeAll } from '../components/dashboard/Card'
import { Icon } from '../components/dashboard/Icon'
import { PageBar } from '../components/dashboard/PageBar'
import { EmptyState } from '../components/EmptyState'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { StatusChip, StatusGlyph } from '../components/StatusGlyph'
import { TopicName } from '../components/TopicName'
import { TopicTip } from '../components/TopicTip'
import { groupName, type AtlasRelease } from '../data/release'
import { TopicList } from '../features/atlas/TopicList'
import { groupCentroids, gridRef, MAP_H, MAP_W, tintTokens, toMapPoints } from '../features/atlas/mapSpace'
import { TerrainMap, type MapGroup, type TerrainMapHandle } from '../features/atlas/TerrainMap'
import { buildTerrain } from '../features/atlas/terrain'
import { fmtInt, fmtShare } from '../lib/format'
import { useI18n, useStrings, nameIn } from '../lib/i18n'
import { prefersReducedMotion } from '../lib/scroll'
import { STATUSES, type StatusId } from '../lib/status'
import { growthText, statusName } from '../lib/topicText'
import { atlasCodec, LAYERS } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'
import { atlas } from '../strings/atlas'

export default function AtlasPage() {
  const sa = useStrings(atlas)
  return <RequireRelease title={sa('map.title')}>{(release) => <Atlas release={release} />}</RequireRelease>
}

/**
 * One card for the whole map: the statuses to show and the map layers on top; the list of topics (the map in words)
 * and the selected topic on the left; the map on the right; the field colours and symbol key underneath. Picking a
 * topic in either place selects it in both.
 */
function Atlas({ release }: { release: AtlasRelease }) {
  const { t, other, otherLang, lang } = useI18n()
  const sa = useStrings(atlas)
  const [state, update] = useUrlState(atlasCodec)
  const mapRef = useRef<TerrainMapHandle>(null)
  const points = useMemo(() => toMapPoints(release.topics, release.taxonomy.groups), [release])
  const terrain = useMemo(
    () => buildTerrain(points.map((p) => ({ x: p.x, y: p.y, r: p.r, w: Math.max(0, p.share) ** 0.75, g: p.groupIndex })), release.taxonomy.groups.length),
    [points, release],
  )
  const centroids = useMemo(() => groupCentroids(points), [points])
  const tints = useMemo(() => tintTokens(release.taxonomy.groups), [release])
  const names = useMemo(() => new Map(release.topics.map((tp) => [tp.id, nameIn(tp, lang)])), [release, lang])
  if (points.length === 0) {
    return (
      <div className="container">
        <PageHeader title={sa('map.title')} />
        <EmptyState title={sa('map.empty')} />
      </div>
    )
  }
  const groups: MapGroup[] = release.taxonomy.groups.map((g, i) => ({
    name: nameIn(g, lang),
    color: tints[i],
    cx: centroids.get(i)?.x ?? MAP_W / 2,
    cy: centroids.get(i)?.y ?? MAP_H / 2,
    n: centroids.get(i)?.n ?? 0,
  }))
  const hidden = new Set<StatusId>(state.hide)
  const layers = new Set(state.layers)
  const counts = Object.fromEntries(STATUSES.map((s) => [s, release.topics.filter((tp) => tp.status === s).length])) as Record<StatusId, number>
  const sel = state.sel ? (release.topicById.get(state.sel) ?? null) : null
  const selPoint = sel ? points.find((p) => p.id === sel.id) : undefined
  const pick = (id: string) => {
    update({ sel: id })
    mapRef.current?.reveal(id)
    // phones: the map sits above the list — bring it into view
    document.getElementById('atlas-map')?.scrollIntoView({ block: 'nearest', behavior: prefersReducedMotion() ? 'auto' : 'smooth' })
  }
  const refOf = new Map(points.map((p) => [p.id, gridRef(p.x, p.y)]))
  const shown = new Set(STATUSES.filter((s) => !hidden.has(s)))
  const toggle = (st: StatusId) => update({ hide: hidden.has(st) ? state.hide.filter((s) => s !== st) : [...state.hide, st] })
  return (
    <>
      <PageBar
        title={sa('map.title')}
        sub={sa('map.sub', { n: fmtInt(release.topics.length), g: fmtInt(groups.filter((g) => g.n > 0).length) })}
        info={[sa('map.lede', { n: fmtInt(release.topics.length) }), `${sa('map.read.1t')}: ${sa('map.read.1b')}`, `${sa('map.read.2t')}: ${sa('map.read.2b')}`, `${sa('map.read.3t')}: ${sa('map.read.3b')}`, sa('map.hint')].join(' · ')}
      />
      <div className="dash">
        <section className="card atlas-board" aria-labelledby="atlas-fig-title">
          <h2 className="sr-only" id="atlas-fig-title">{sa('map.fig', { release: release.overview.release })}</h2>
          <div className="ab-bar">
            <div className="ab-chips" role="group" aria-label={sa('map.key.statuses')}>
              {STATUSES.map((st) => (
                <button key={st} type="button" className={`ab-chip is-${st}`} aria-pressed={!hidden.has(st)} onClick={() => toggle(st)}>
                  <StatusGlyph status={st} size={12} />
                  {statusName(t, st)}
                  <span className="ab-chip-n">{fmtInt(counts[st])}</span>
                </button>
              ))}
            </div>
            <div className="ab-layers" role="group" aria-label={sa('map.key.layers')}>
              {LAYERS.map((ly) => (
                <button key={ly} type="button" className="ab-chip is-layer" aria-pressed={layers.has(ly)} onClick={() => update({ layers: layers.has(ly) ? state.layers.filter((x) => x !== ly) : [...state.layers, ly] })}>
                  {sa(`layer.${ly}` as const)}
                </button>
              ))}
            </div>
          </div>
          <div className="ab-body">
            <div className="ab-side">
              {sel ? (
                <div className="ab-sel" id="atlas-selection" aria-live="polite">
                  <div className="ab-sel-head">
                    <StatusChip status={sel.status} label={statusName(t, sel.status)} small />
                    <button type="button" className="icon-btn" aria-label={sa('map.sel.clear')} onClick={() => update({ sel: null })}>
                      <Icon name="close" size={18} />
                    </button>
                  </div>
                  <p className="ab-sel-name"><TopicName topic={sel} /></p>
                  {other(sel) !== nameIn(sel, lang) ? <p className="ab-sel-alt" lang={otherLang}>{other(sel)}</p> : null}
                  <dl className="ab-sel-facts">
                    <div><dt>{t('tp.growth')}</dt><dd>{growthText(t, sel.metrics)}</dd></div>
                    <div><dt>{t('tp.share')}</dt><dd>{fmtShare(sel.metrics.share_recent, 2)}</dd></div>
                    <div><dt>{t('col.field')}</dt><dd>{groupName(release, sel.group, lang)}</dd></div>
                    {selPoint ? <div><dt>{sa('map.grid')}</dt><dd><span className="g-ref">{gridRef(selPoint.x, selPoint.y)}</span></dd></div> : null}
                  </dl>
                  <SeeAll to={`/topics/${sel.id}`} label={sa('map.sel.open')} />
                </div>
              ) : (
                <p className="ab-hint" id="atlas-selection" aria-live="polite">{sa('map.sel.none')}</p>
              )}
              <TopicList release={release} refOf={refOf} shown={shown} by={state.by} onBy={(by) => update({ by })} selected={state.sel} onPick={pick} />
            </div>
            <div className="ab-map" id="atlas-map">
              <p className="sr-only" id="atlas-desc">{sa('map.desc')}</p>
              <TerrainMap
                ref={mapRef}
                points={points}
                groups={groups}
                terrain={terrain}
                hidden={hidden}
                layers={layers}
                selected={state.sel}
                onSelect={(id) => update({ sel: id })}
                describe={(p) => `${names.get(p.id) ?? p.id} · ${statusName(t, p.status)} · ${sa('map.grid')} ${gridRef(p.x, p.y)}`}
                tipFor={(id) => {
                  const tp = release.topicById.get(id)
                  return tp ? <TopicTip topic={tp} ciLevel={release.ciLevel} /> : null
                }}
                names={names}
                label={sa('map.aria')}
                describedBy="atlas-desc"
                controls={{ zoomIn: sa('map.zoomIn'), zoomOut: sa('map.zoomOut'), reset: sa('map.reset'), group: sa('map.zoomGroup'), hint: sa('map.hint') }}
              />
            </div>
          </div>
          <div className="ab-foot">
            <ul className="ab-fields" aria-label={sa('map.key.fields')}>
              {groups.filter((g) => g.n > 0).map((g) => (
                <li key={g.name}>
                  <i className="swatch" style={{ background: `var(--${g.color})` }} aria-hidden="true" />
                  {g.name}
                </li>
              ))}
            </ul>
            <ul className="ab-keys">
              <li>
                <svg width="34" height="18" viewBox="0 0 34 18" aria-hidden="true" focusable="false">
                  {[2.5, 4.5, 7].map((r, i) => <circle key={r} cx={[4, 12, 25][i]} cy={9} r={r} fill="none" stroke="currentColor" strokeWidth="1.2" />)}
                </svg>
                {sa('map.key.size')}
              </li>
              <li>
                <svg width="34" height="18" viewBox="0 0 34 18" aria-hidden="true" focusable="false">
                  <path d="M2 13c6-8 13-8 19-3s9 3 12-2" fill="none" stroke="var(--map-contour)" strokeWidth="1.5" />
                </svg>
                {sa('map.key.contour')}
              </li>
              <li>{sa('map.scale')}</li>
            </ul>
          </div>
        </section>
      </div>
    </>
  )
}
