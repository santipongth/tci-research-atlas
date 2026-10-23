import type { ReactNode } from 'react'
import { useI18n } from '../lib/i18n'

/** Layer 2 of the copy ruling outside a `Figure`: the method fine print of a section behind a "วิธีอ่าน" disclosure. */
export function HowNote({ children }: { children: ReactNode }) {
  const { t } = useI18n()
  return (
    <details className="how">
      <summary>{t('view.how')}</summary>
      <div>{children}</div>
    </details>
  )
}
