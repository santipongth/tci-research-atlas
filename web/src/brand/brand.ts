import nectecUrl from '../assets/brand/partners/nectec.png'
import nstdaUrl from '../assets/brand/partners/nstda.png'
import tciUrl from '../assets/brand/partners/tci.png'

/**
 * The ONE place that defines the TCI brand on the site: the TCI logo in the header and the partner logos
 * (TCI · NECTEC · NSTDA) in the footer. Files supplied by the owner on 2026-10-23 (tciai.openservice.in.th);
 * Vite fingerprints them for Pages and inlines them in the offline file. Swap a file here to update the brand.
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
  logo: { src: tciUrl, alt: { th: 'ศูนย์ดัชนีการอ้างอิงวารสารไทย (TCI)', en: 'Thai-Journal Citation Index Centre (TCI)' }, width: 227, height: 119 },
  temporary: false,
}

/** Partner logos for the footer band, in the order the owner listed them. */
export const PARTNERS: readonly BrandLogo[] = [
  { src: tciUrl, alt: { th: 'ศูนย์ดัชนีการอ้างอิงวารสารไทย (TCI)', en: 'Thai-Journal Citation Index Centre (TCI)' }, width: 227, height: 119 },
  { src: nectecUrl, alt: { th: 'ศูนย์เทคโนโลยีอิเล็กทรอนิกส์และคอมพิวเตอร์แห่งชาติ (NECTEC)', en: 'National Electronics and Computer Technology Center (NECTEC)' }, width: 287, height: 91 },
  { src: nstdaUrl, alt: { th: 'สำนักงานพัฒนาวิทยาศาสตร์และเทคโนโลยีแห่งชาติ (สวทช.)', en: 'National Science and Technology Development Agency (NSTDA)' }, width: 425, height: 139 },
]
