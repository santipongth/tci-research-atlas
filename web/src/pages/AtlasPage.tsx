import { TopicName } from '../components/TopicName'
import { useMemo, useRef } from 'react'
import { Link } from 'react-router'
import { EmptyState } from '../components/EmptyState'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { SourceMore } from '../components/SourceLine'
import { StatusChip, StatusGlyph } from '../components/StatusGlyph'
import { PhoneFold } from '../components/PhoneFold'
import { Steps } from '../components/Steps'
import { TopicTip } from '../components/TopicTip'
import { groupName, type AtlasRelease } from '../data/release'
import { Gazetteer } from '../features/atlas/Gazetteer'
import { groupCentroids, gridRef, MAP_H, MAP_W, tintTokens, toMapPoints } from '../features/atlas/mapSpace'
import { TerrainMap, type MapGroup, type TerrainMapHandle } from '../features/atlas/TerrainMap'
import { buildTerrain } from '../features/atlas/terrain'
import { ciPct, fmtInt, fmtPct } from '../lib/format'
import { useI18n } from '../lib/i18n'
import { prefersReducedMotion } from '../lib/scroll'
import { glyphPath, SIGNAL_STATUSES, STATUSES, type StatusId } from '../lib/status'
import { ciText, growthText, statusName } from '../lib/topicText'
import { atlasCodec, LAYERS } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'

/** Step drawings for "read this map": contour rings on a field tint, the four signal glyphs, near and far dots. */
function HillArt() {
  return (
    <svg width="64" height="36" viewBox="0 0 64 36" focusable="false">
      <ellipse cx="30" cy="20" rx="27" ry="14" className="ra-tint" />
      {[[27, 14], [19, 10], [11, 6]].map(([rx, ry], i) => (
        <ellipse key={rx} cx={30 + i * 2} cy={20 - i * 1.5} rx={rx} ry={ry} className={i === 0 ? 'ra-contour is-heavy' : 'ra-contour'} />
      ))}
    </svg>
  )
}

function SymbolArt() {
  return (
    <svg width="96" height="36" viewBox="0 0 96 36" focusable="false">
      {SIGNAL_STATUSES.map((st, i) => (
        <path key={st} className={`mk mk-${st}`} transform={`translate(${12 + i * 24},18)`} d={glyphPath(st, 4 + i)} />
      ))}
    </svg>
  )
}

function NearArt() {
  return (
    <svg width="96" height="36" viewBox="0 0 96 36" focusable="false">
      <circle cx="12" cy="18" r="5" className="ra-dot" />
      <circle cx="26" cy="15" r="5" className="ra-dot" />
      <path d="M38 18h30" className="ra-gap" />
      <circle cx="84" cy="20" r="5" className="ra-dot" />
    </svg>
  )
}

export default function AtlasPage() {
  const { t } = useI18n()
  return <RequireRelease title={t('map.title')}>{(release) => <Atlas release={release} />}</RequireRelease>
}

function Atlas({ release }: { release: AtlasRelease }) {
  const { t, other, otherLang, lang } = useI18n()
  const [state, update] = useUrlState(atlasCodec)
  const mapRef = useRef<TerrainMapHandle>(null)
  const points = useMemo(() => toMapPoints(release.topics, release.taxonomy.groups), [release])
  const terrain = useMemo(
    () => buildTerrain(points.map((p) => ({ x: p.x, y: p.y, r: p.r, w: Math.max(0, p.share) ** 0.75, g: p.groupIndex })), release.taxonomy.groups.length),
    [points, release],
  )
  const centroids = useMemo(() => groupCentroids(points), [points])
  const tints = useMemo(() => tintTokens(release.taxonomy.groups), [release])
  const names = useMemo(() => new Map(release.topics.map((tp) => [tp.id, lang === 'en' ? tp.en || tp.th : tp.th || tp.en])), [release, lang])
  if (points.length === 0) {
    return (
      <div className="container">
        <PageHeader title={t('map.title')} />
        <EmptyState title={t('map.empty')} />
      </div>
    )
  }
  const groups: MapGroup[] = release.taxonomy.groups.map((g, i) => ({
    name: lang === 'en' ? g.en || g.th : g.th || g.en,
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
  const selCi = sel ? ciText(t, sel.metrics, release.ciLevel) : null
  const pick = (id: string) => {
    update({ sel: id })
    mapRef.current?.reveal(id)
    document.getElementById('atlas-map')?.scrollIntoView({ block: 'nearest', behavior: prefersReducedMotion() ? 'auto' : 'smooth' })
  }
  return (
    <div className="container wide">
      <PageHeader title={t('map.title')} lede={t('map.lede', { n: fmtInt(release.topics.length) })} />
      <PhoneFold id="map-read-h" className="map-read" headingClass="map-read-h" heading={t('map.read.h')}>
        <Steps
          label={t('map.read.h')}
          items={[
            { title: t('map.read.1t'), body: t('map.read.1b'), art: <HillArt /> },
            { title: t('map.read.2t'), body: t('map.read.2b'), art: <SymbolArt /> },
            { title: t('map.read.3t'), body: t('map.read.3b'), art: <NearArt /> },
          ]}
        />
      </PhoneFold>
      <div className="atlas-grid">
        <figure className="atlas-fig" id="atlas-map" aria-labelledby="atlas-fig-title">
          <p className="figtitle" id="atlas-fig-title">{t('figure.n', { n: 1, title: t('map.fig', { release: release.overview.release }) })}</p>
          <p className="sr-only" id="atlas-desc">{t('map.desc')}</p>
          <TerrainMap
            ref={mapRef}
            points={points}
            groups={groups}
            terrain={terrain}
            hidden={hidden}
            layers={layers}
            selected={state.sel}
            onSelect={(id) => update({ sel: id })}
            describe={(p) => `${names.get(p.id) ?? p.id} · ${statusName(t, p.status)} · ${t('map.grid')} ${gridRef(p.x, p.y)}`}
            tipFor={(id) => {
              const tp = release.topicById.get(id)
              return tp ? <TopicTip topic={tp} ciLevel={release.ciLevel} /> : null
            }}
            names={names}
            label={t('map.aria')}
            describedBy="atlas-desc"
            controls={{ zoomIn: t('map.zoomIn'), zoomOut: t('map.zoomOut'), reset: t('map.reset'), group: t('map.zoomGroup'), hint: t('map.hint') }}
          />
          <p className="source">
            {t('source.line', { release: release.overview.release })} · {t('map.scale')}
            <SourceMore />
          </p>
        </figure>
        <aside className="atlas-side" aria-label={t('map.key.h')}>
          <section className="cart" id="atlas-selection" aria-labelledby="sel-h" aria-live="polite">
            <h2 id="sel-h" className="cart-h">{t('map.sel.h')}</h2>
            {sel ? (
              <>
                <p className="sel-name">
                  <b><TopicName topic={sel} /></b>
                  {selPoint ? <span className="g-ref">{gridRef(selPoint.x, selPoint.y)}</span> : null}
                </p>
                <p className="tp-alt" lang={otherLang}>{other(sel)}</p>
                <p className="mt-2"><StatusChip status={sel.status} label={statusName(t, sel.status)} small /></p>
                <dl className="summary compact">
                  <div><dt>{t('col.field')}</dt><dd>{groupName(release, sel.group, lang)}</dd></div>
                  <div><dt>{t('tp.share')}</dt><dd>{fmtPct(sel.metrics.share_recent, 2)}</dd></div>
                  <div><dt>{t('tp.growth')}</dt><dd>{growthText(t, sel.metrics)}{selCi ? <small>{selCi}</small> : null}</dd></div>
                </dl>
                <p className="mt-4"><Link className="btn" to={`/topics/${sel.id}`}>{t('map.sel.open')}</Link></p>
                <p className="mt-2"><button type="button" className="linkbtn" onClick={() => update({ sel: null })}>{t('map.sel.clear')}</button></p>
              </>
            ) : (
              <p className="hint">{t('map.sel.none')}</p>
            )}
          </section>
          <section className="cart" aria-labelledby="key-h">
            <h2 id="key-h" className="cart-h">{t('map.key.h')}</h2>
            <fieldset className="keyset">
              <legend>{t('map.key.statuses')}</legend>
              <div className="keylist">
                {STATUSES.map((st) => (
                  <label key={st}>
                    <input
                      type="checkbox"
                      checked={!hidden.has(st)}
                      onChange={(e) => update({ hide: e.target.checked ? state.hide.filter((s) => s !== st) : [...state.hide, st] })}
                    />
                    <StatusGlyph status={st} size={14} />
                    <span>{statusName(t, st)} {fmtInt(counts[st])}</span>
                  </label>
                ))}
              </div>
            </fieldset>
            <fieldset className="keyset">
              <legend>{t('map.key.fields')}</legend>
              <ul className="fieldkey">
                {groups.filter((g) => g.n > 0).map((g) => (
                  <li key={g.name}>
                    <i className="swatch" style={{ background: `var(--${g.color})` }} aria-hidden="true" />
                    <span>{g.name}</span>
                  </li>
                ))}
              </ul>
            </fieldset>
            <fieldset className="keyset">
              <legend>{t('map.key.layers')}</legend>
              <div className="layers">
                {LAYERS.map((ly) => (
                  <label key={ly}>
                    <input type="checkbox" checked={layers.has(ly)} onChange={(e) => update({ layers: e.target.checked ? [...state.layers, ly] : state.layers.filter((x) => x !== ly) })} />
                    <span>{t(`layer.${ly}` as const)}</span>
                  </label>
                ))}
              </div>
            </fieldset>
            <div className="keyrow">
              <svg width="46" height="22" viewBox="0 0 46 22" aria-hidden="true" focusable="false">
                {[3, 6, 9].map((r, i) => <circle key={r} cx={[6, 18, 35][i]} cy={11} r={r} fill="none" stroke="currentColor" strokeWidth="1.2" />)}
              </svg>
              <span>{t('map.key.size')}</span>
            </div>
            <div className="keyrow">
              <svg width="46" height="22" viewBox="0 0 46 22" aria-hidden="true" focusable="false">
                <path d="M2 16c8-10 18-10 26-4s12 4 16-2" fill="none" stroke="var(--map-contour)" strokeWidth="1.5" />
                <path d="M8 19c8-7 14-6 22-2s8 2 12-1" fill="none" stroke="var(--map-contour)" strokeWidth="0.9" opacity="0.6" />
              </svg>
              <span>{t('map.key.contour')}</span>
            </div>
            <div className="keyrow">
              <svg width="46" height="22" viewBox="0 0 46 22" aria-hidden="true" focusable="false">
                {[[8, 9], [16, 14], [24, 8], [31, 13], [39, 10]].map(([x, y]) => <circle key={`${x}-${y}`} cx={x} cy={y} r={2} fill="var(--map-dot)" />)}
              </svg>
              <span>{t('map.key.dot')}</span>
            </div>
          </section>
        </aside>
      </div>
      <Section id="gazetteer" title={t('map.gaz.h')} intro={t('map.gaz.intro', { level: ciPct(release.ciLevel) })}>
        <Gazetteer release={release} points={points} query={state.q} onQuery={(q) => update({ q })} onPick={pick} selected={state.sel} />
      </Section>
    </div>
  )
}
