import { STR, fmt, pct, type Lang } from '../lib/i18n'
import type { AtlasData } from '../lib/loader'

export default function StatsBand({ lang, data }: { lang: Lang; data: AtlasData }) {
  const top = data.groups[0]
  const items = [
    { n: fmt(data.totalArticles), label: STR.articles[lang] },
    { n: fmt(data.totalFields), label: data.dynamic ? (lang === 'th' ? 'หัวข้อวิจัย' : 'topics') : STR.fieldsUnit[lang] },
    { n: String(data.totalGroups), label: STR.groupsUnit[lang] },
    { n: pct(top.articles, data.totalArticles), label: `${STR.topGroupShare[lang]} — ${lang === 'th' ? top.th : top.en}` },
  ]
  return (
    <div className="grid grid-cols-2 gap-x-6 gap-y-8 border-y border-[#161611]/12 py-8 lg:grid-cols-4">
      {items.map((it, i) => (
        <div key={i} className="atlas-enter" style={{ animationDelay: `${i * 80}ms` }}>
          <div className="font-mono-data text-[34px] font-semibold leading-none tracking-tight lg:text-[44px]">
            {it.n}
          </div>
          <div className="mt-2 text-[13px] leading-snug text-[#161611]/55">{it.label}</div>
        </div>
      ))}
    </div>
  )
}
