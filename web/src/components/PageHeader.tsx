import type { ReactNode } from 'react'
import { PageBar } from './dashboard/PageBar'

export interface MetaItem {
  label: string
  value: string
}

/**
 * The page h1 as the white page bar (see PageBar): the lede moves behind the (i) beside the title, release facts become
 * the one short line under it, and `children` (links, buttons) sit on the right. Every page renders exactly one.
 */
export function PageHeader({ title, titleLang, lede, meta, children }: {
  title: string
  titleLang?: string
  lede?: ReactNode
  meta?: MetaItem[]
  children?: ReactNode
}) {
  const sub = meta && meta.length ? meta.map((m) => `${m.label} ${m.value}`).join(' · ') : undefined
  return <PageBar title={title} titleLang={titleLang} sub={sub} info={lede} actions={children} />
}
