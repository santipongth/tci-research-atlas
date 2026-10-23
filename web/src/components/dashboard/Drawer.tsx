import { useEffect, useId, useRef, type ReactNode } from 'react'
import { useI18n } from '../../lib/i18n'
import { Icon } from './Icon'

/**
 * A side panel on the native modal <dialog>: the browser traps focus inside, Escape closes it and focus returns to the
 * control that opened it. A click on the dimmed backdrop closes it too. `side="left"` is the phone menu; the right
 * panel holds a card's full list ("ดูทั้งหมด").
 */
export function Drawer({ open, onClose, title, side = 'right', children }: {
  open: boolean
  onClose: () => void
  title: string
  side?: 'left' | 'right'
  children: ReactNode
}) {
  const { t } = useI18n()
  const ref = useRef<HTMLDialogElement>(null)
  const titleId = useId()
  useEffect(() => {
    const d = ref.current
    if (!d || typeof d.showModal !== 'function') return
    if (open && !d.open) d.showModal()
    else if (!open && d.open) d.close()
  }, [open])
  return (
    <dialog
      ref={ref}
      className={`drawer drawer-${side}`}
      aria-labelledby={titleId}
      onClose={onClose}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div className="drawer-in">
        <div className="drawer-head">
          <h2 id={titleId}>{title}</h2>
          <button type="button" className="icon-btn" aria-label={t('dash.close')} onClick={onClose}>
            <Icon name="close" />
          </button>
        </div>
        <div className="drawer-body">{open ? children : null}</div>
      </div>
    </dialog>
  )
}
