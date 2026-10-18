import { STR, fmt, pct, type Lang } from '../lib/i18n'
import type { AtlasData } from '../lib/loader'

interface Props {
  lang: Lang
  selected: string | null
  onSelect: (id: string | null) => void
  data: AtlasData
}

export default function GroupRanking({ lang, selected, onSelect, data }: Props) {
  const { groups: GROUPS, totalArticles } = data
  const max = GROUPS[0].articles

  const jump = (id: string) => {
    onSelect(selected === id ? null : id)
    if (selected !== id) document.getElementById('atlas')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return (
    <div>
      <div className="mb-8 max-w-2xl">
        <div className="eyebrow text-[#161611]/45">RANKING · {GROUPS.length} GROUPS</div>
        <h2 className="font-display mt-3 text-[28px] font-semibold leading-snug lg:text-[36px]">
          {lang === 'th'
            ? `${GROUPS.length} กลุ่มสาขาเรียงตามจำนวนบทความ`
            : `${GROUPS.length} field groups ranked by article volume`}
        </h2>
        <p className="mt-2 text-[14px] text-[#161611]/60">{STR.rankingLead[lang]}</p>
      </div>
      <ol className="border-t border-[#161611]/12">
        {GROUPS.map((g) => {
          const active = selected === g.id
          return (
            <li key={g.id}>
              <button
                onClick={() => jump(g.id)}
                aria-pressed={active}
                className={`group grid w-full cursor-pointer grid-cols-[2.2rem_minmax(0,1fr)_auto] items-baseline gap-x-3 border-b border-[#161611]/12 px-2 py-3 text-left transition-colors focus-visible:outline-2 focus-visible:outline-[#FF5F1F] sm:grid-cols-[2.5rem_minmax(0,1.1fr)_minmax(0,2fr)_auto] sm:gap-x-5 ${
                  active ? 'bg-[#FF5F1F]/8' : 'hover:bg-[#161611]/5'
                }`}
              >
                <span className={`font-mono-data text-[12px] ${active ? 'text-[#FF5F1F]' : 'text-[#161611]/40'}`}>
                  {String(g.rank).padStart(2, '0')}
                </span>
                <span className="min-w-0">
                  <span className="flex items-center gap-2">
                    <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: g.color }} />
                    <span className={`truncate text-[15px] leading-snug ${active ? 'font-semibold' : ''} group-hover:underline group-hover:decoration-dashed group-hover:underline-offset-4`}>
                      {lang === 'th' ? g.th : g.en}
                    </span>
                  </span>
                  <span className="mt-0.5 block truncate pl-[18px] text-[11.5px] text-[#161611]/45">
                    {lang === 'th' ? g.en : g.th} · {g.fieldCount} {data.dynamic ? (lang === 'th' ? 'หัวข้อ' : 'topics') : STR.fieldsUnit[lang]}
                  </span>
                </span>
                <span className="hidden h-1.5 self-center overflow-hidden rounded-full bg-[#161611]/8 sm:block">
                  <span
                    className="block h-full rounded-full transition-all duration-300"
                    style={{ width: `${(g.articles / max) * 100}%`, background: g.color }}
                  />
                </span>
                <span className="text-right">
                  <span className="font-mono-data block text-[15px] font-semibold">{fmt(g.articles)}</span>
                  <span className="font-mono-data block text-[11px] text-[#161611]/45">
                    {pct(g.articles, totalArticles)}
                  </span>
                </span>
              </button>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
