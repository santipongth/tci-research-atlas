import { useId } from 'react'
import { downloadText } from '../lib/csv'
import { useI18n } from '../lib/i18n'

/** The small secondary "ดาวน์โหลด CSV" button; what the numbers in the file mean is its description (tooltip + screen readers). */
export function CsvButton({ filename, text }: { filename: string; text: () => string }) {
  const { t } = useI18n()
  const id = useId()
  return (
    <>
      <button type="button" className="btn-csv" title={t('csv.units')} aria-describedby={id} onClick={() => downloadText(filename, text())}>
        <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false">
          <path d="M8 2v8M4.5 6.5 8 10l3.5-3.5M2.5 11.5v2h11v-2" fill="none" stroke="currentColor" strokeWidth="1.8" />
        </svg>
        <span>{t('csv.download')}</span>
      </button>
      <span id={id} className="sr-only">{t('csv.units')}</span>
    </>
  )
}
