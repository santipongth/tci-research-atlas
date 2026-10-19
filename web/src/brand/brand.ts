/**
 * The ONE place that defines the TCI brand on the site.
 * Today: a temporary text wordmark (no TCI logo is imitated).
 * Official logo: put the file in src/brand/assets/, `import logoUrl from './assets/tci-logo.svg'`,
 * set `logo: { src: logoUrl, alt: { th: '…', en: '…' }, width: 40, height: 40 }` and `temporary: false`.
 * Vite fingerprints it for Pages and inlines it in the offline file; nothing else changes.
 */
export interface BrandLogo {
  src: string
  alt: { th: string; en: string }
  width: number
  height: number
}

export const BRAND: { name: string; mark: string; logo: BrandLogo | null; temporary: boolean } = {
  name: 'TCI Research Atlas',
  mark: 'TCI',
  logo: null,
  temporary: true,
}
