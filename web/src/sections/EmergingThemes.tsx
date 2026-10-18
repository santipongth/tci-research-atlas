import { useMemo, useState } from 'react'
import { fmt, type Lang } from '../lib/i18n'
import type { AtlasData } from '../lib/loader'
import { STATUS_STYLE } from './AtlasMap'

interface Props {
  lang: Lang
  selected: string | null
  onSelect: (id: string | null) => void
  data: AtlasData
}

const ORDER = ['EMERGING', 'HOT', 'DECLINING', 'STABLE'] as const

export default function EmergingThemes({ lang, selected, onSelect, data }: Props) {
  const topics = useMemo(
    () => data.nodes.filter((n) => n.kind === 'field' && n.status).sort((a, b) => (b.emergingScore ?? 0) - (a.emergingScore ?? 0)),
    [data],
  )
  const counts = useMemo(() => {
    const c: Record<string, number> = {}
    for (const t of topics) c[t.status!] = (c[t.status!] ?? 0) + 1
    return c
  }, [topics])

  const [filter, setFilter] = useState<string>('EMERGING')
  const shown = topics.filter((t) => t.status === filter).slice(0, 24)

  if (!topics.length) return null

  return (
    <div>
      <div className="mb-8 max-w-2xl">
        <div className="eyebrow text-[#161611]/45">
          EMERGING THEMES{data.lastCompleteYear ? ` · DATA THROUGH ${data.lastCompleteYear}` : ''}
        </div>
        <h2 className="font-display mt-3 text-[28px] font-semibold leading-snug lg:text-[36px]">
          {lang === 'th' ? 'หัวข้อที่กำลังก่อตัวและกำลังจางหาย' : 'Themes emerging and fading'}
        </h2>
        <p className="mt-2 text-[14px] text-[#161611]/60">
          {lang === 'th'
            ? 'จัดอันดับด้วย Emerging Score (0–100) ที่รวมอัตราโต ความเร่ง การระเบิดของจำนวนบทความ และความใหม่ของหัวข้อ — คลิกเพื่อดูตำแหน่งบนแผนที่'
            : 'Ranked by Emerging Score (0–100) combining growth, acceleration, publication bursts and topic novelty — click to locate on the atlas'}
        </p>
      </div>

      {/* status filter chips */}
      <div className="mb-6 flex flex-wrap gap-2">
        {ORDER.filter((s) => counts[s]).map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            aria-pressed={filter === s}
            className={`flex min-h-[36px] cursor-pointer items-center gap-2 rounded-full border px-3.5 py-1.5 text-[13px] transition-colors focus-visible:outline-2 focus-visible:outline-[#FF5F1F] ${
              filter === s ? 'border-[#161611] bg-[#161611] text-[#f5f6f2]' : 'border-[#161611]/20 text-[#161611]/70 hover:border-[#161611]/50'
            }`}
          >
            <span className="h-2 w-2 rounded-full" style={{ background: STATUS_STYLE[s].color }} />
            {STATUS_STYLE[s][lang]}
            <span className="font-mono-data text-[11.5px] opacity-70">{counts[s]}</span>
          </button>
        ))}
      </div>

      <ol className="border-t border-[#161611]/12">
        {shown.map((t, i) => {
          const active = selected === t.id
          return (
            <li key={t.id}>
              <button
                onClick={() => {
                  onSelect(active ? null : t.id)
                  if (!active) document.getElementById('atlas')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
                }}
                className={`grid w-full cursor-pointer grid-cols-[2.5rem_minmax(0,1fr)_auto] items-baseline gap-x-3 border-b border-[#161611]/12 px-2 py-3 text-left transition-colors focus-visible:outline-2 focus-visible:outline-[#FF5F1F] sm:grid-cols-[3rem_minmax(0,1.4fr)_minmax(0,2fr)_auto] ${
                  active ? 'bg-[#FF5F1F]/8' : 'hover:bg-[#161611]/5'
                }`}
              >
                <span className="font-mono-data text-[12px] text-[#161611]/40">{String(i + 1).padStart(2, '0')}</span>
                <span className="min-w-0">
                  <span className={`block truncate text-[15px] leading-snug ${active ? 'font-semibold' : ''}`}>
                    {lang === 'th' ? t.th : t.en}
                  </span>
                  <span className="mt-0.5 block truncate text-[11.5px] text-[#161611]/45">
                    {lang === 'th' ? t.en : t.th}
                    {t.burstYears ? ` · ${lang === 'th' ? 'ระเบิดช่วง' : 'burst'} ${t.burstYears}` : ''}
                  </span>
                </span>
                <span className="hidden h-1.5 self-center overflow-hidden rounded-full bg-[#161611]/8 sm:block">
                  <span className="block h-full rounded-full" style={{ width: `${t.emergingScore ?? 0}%`, background: STATUS_STYLE[t.status!].color }} />
                </span>
                <span className="text-right">
                  <span className="font-mono-data block text-[15px] font-semibold" style={{ color: STATUS_STYLE[t.status!].color }}>
                    {t.emergingScore ?? '—'}
                  </span>
                  <span className="font-mono-data block text-[11px] text-[#161611]/45">{fmt(t.articles)} {lang === 'th' ? 'เรื่อง' : 'arts'}</span>
                </span>
              </button>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
