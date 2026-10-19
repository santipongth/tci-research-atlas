import { BRAND } from './brand'

/** Header wordmark: the official logo when configured in brand.ts, else the temporary "TCI" text mark. */
export function Wordmark({ sub, lang }: { sub: string; lang: 'th' | 'en' }) {
  return (
    <span className="wm">
      {BRAND.logo ? (
        <img className="wm-logo" src={BRAND.logo.src} alt={BRAND.logo.alt[lang]} width={BRAND.logo.width} height={BRAND.logo.height} />
      ) : (
        <span className="wm-box" aria-hidden="true">{BRAND.mark}</span>
      )}
      <span className="wm-text">
        <span className="wm-name">{BRAND.name}</span>
        <span className="wm-sub">{sub}</span>
      </span>
    </span>
  )
}
