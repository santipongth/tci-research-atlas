import { useNavigate } from 'react-router'
import { TH_PROVINCE_PATHS, TH_VIEWBOX } from '../geo/thProvinces'

/**
 * A map of Thailand for "งานวิจัยในจังหวัดของฉัน": provinces with research in the release tinted by their article
 * count (one blue, 4 steps), the chosen one in TCI blue with an orange outline, the rest a quiet ground. Pointer
 * users can click a province to open it; the page's list and select are the keyboard and screen-reader way (the map
 * itself is one labelled image).
 */
export function ProvinceLocator({ articles, current, label, size = 'md' }: {
  articles: ReadonlyMap<string, number>
  current?: string
  label: string
  size?: 'md' | 'lg'
}) {
  const navigate = useNavigate()
  const values = [...articles.values()].filter((v) => v > 0).sort((a, b) => a - b)
  const q = (p: number) => values[Math.min(values.length - 1, Math.floor(p * values.length))] ?? 0
  const cuts = [q(0.25), q(0.5), q(0.75)]
  const step = (v: number) => (v <= 0 ? 0 : 1 + cuts.filter((c) => v > c).length)
  return (
    <svg className={`plc plc-${size}`} viewBox={TH_VIEWBOX} role="img" aria-label={label}>
      {Object.entries(TH_PROVINCE_PATHS).map(([code, d]) => {
        const v = articles.get(code) ?? 0
        const on = code === current
        return (
          <path
            key={code}
            d={d}
            className={on ? 'plc-p is-on' : `plc-p plc-s${step(v)}`}
            onClick={v > 0 ? () => navigate(`/province/${code}`) : undefined}
            style={v > 0 ? { cursor: 'pointer' } : undefined}
          />
        )
      })}
      {current && TH_PROVINCE_PATHS[current] ? <path d={TH_PROVINCE_PATHS[current]} className="plc-ring" /> : null}
    </svg>
  )
}
