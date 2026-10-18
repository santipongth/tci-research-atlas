import type { Lang } from '../lib/i18n'
import { STR } from '../lib/i18n'

interface Props {
  lang: Lang
  setLang: (l: Lang) => void
}

export default function Header({ lang, setLang }: Props) {
  const nav = [
    { href: '#atlas', label: STR.navMap[lang] },
    { href: '#emerging', label: STR.navEmerging[lang] },
    { href: '#ranking', label: STR.navRanking[lang] },
    { href: '#insights', label: STR.navInsights[lang] },
    { href: '#method', label: STR.navMethod[lang] },
  ]
  return (
    <header className="sticky top-0 z-40 border-b border-[#161611]/10 bg-[#f5f6f2]/90 backdrop-blur">
      <div className="mx-auto flex max-w-[1400px] items-center justify-between gap-4 px-5 py-3">
        <a href="#top" className="group flex items-baseline gap-3">
          <span className="font-mono-data text-[13px] font-semibold tracking-[0.18em] text-[#161611]">
            {STR.brand[lang]}
          </span>
          <span className="hidden text-[13px] text-[#161611]/55 sm:inline">{STR.brandSub[lang]}</span>
        </a>
        <nav className="hidden items-center gap-6 md:flex">
          {nav.map((n) => (
            <a
              key={n.href}
              href={n.href}
              className="text-[13.5px] text-[#161611]/65 underline-offset-4 transition-colors hover:text-[#161611] hover:underline hover:decoration-dashed focus-visible:outline-2 focus-visible:outline-[#FF5F1F]"
            >
              {n.label}
            </a>
          ))}
        </nav>
        <div className="flex items-center gap-1 rounded-full border border-[#161611]/15 bg-white p-0.5" role="group" aria-label="language">
          {(['th', 'en'] as Lang[]).map((l) => (
            <button
              key={l}
              onClick={() => setLang(l)}
              aria-pressed={lang === l}
              className={`min-h-[32px] min-w-[44px] cursor-pointer rounded-full px-3 font-mono-data text-[12px] tracking-widest uppercase transition-colors focus-visible:outline-2 focus-visible:outline-[#FF5F1F] ${
                lang === l ? 'bg-[#161611] text-[#f5f6f2]' : 'text-[#161611]/60 hover:text-[#161611]'
              }`}
            >
              {l === 'th' ? 'ไทย' : 'EN'}
            </button>
          ))}
        </div>
      </div>
    </header>
  )
}
