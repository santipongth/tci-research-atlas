import type { ReactNode } from 'react'
import { useDocumentTitle } from '../lib/useDocumentTitle'

export interface MetaItem {
  label: string
  value: string
}

/** The page h1 (+ lede and civic release metadata). Every page renders exactly one. */
export function PageHeader({ title, titleLang, lede, meta, children }: { title: string; titleLang?: string; lede?: ReactNode; meta?: MetaItem[]; children?: ReactNode }) {
  useDocumentTitle(title)
  return (
    <div className="page-h">
      <h1 lang={titleLang}>{title}</h1>
      {lede ? <p className="lede">{lede}</p> : null}
      {meta && meta.length > 0 ? (
        <dl className="meta">
          {meta.map((m) => (
            <div key={m.label}>
              <dt>{m.label}</dt>
              <dd>{m.value}</dd>
            </div>
          ))}
        </dl>
      ) : null}
      {children}
    </div>
  )
}
