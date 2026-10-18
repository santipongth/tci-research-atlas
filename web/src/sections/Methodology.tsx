import { STR, type Lang } from '../lib/i18n'

export default function Methodology({ lang }: { lang: Lang }) {
  return (
    <div>
      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.6fr)]">
        <div>
          <div className="eyebrow text-[#161611]/45">METHOD · DATA</div>
          <h2 className="font-display mt-3 text-[28px] font-semibold leading-snug lg:text-[32px]">
            {STR.methodTitle[lang]}
          </h2>
        </div>
        <p className="max-w-[68ch] text-[15px] leading-relaxed text-[#161611]/70">{STR.methodBody[lang]}</p>
      </div>
      <footer className="mt-16 border-t border-[#161611]/12 pt-6 pb-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <span className="font-mono-data text-[12px] tracking-[0.18em] text-[#161611]/50">{STR.brand[lang]}</span>
          <span className="text-[12.5px] text-[#161611]/45">{STR.footer[lang]}</span>
        </div>
      </footer>
    </div>
  )
}
