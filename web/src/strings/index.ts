import { about } from './about'
import { common } from './common'
import { compare } from './compare'
import { data } from './data'
import { emerging } from './emerging'
import { glossary } from './glossary'
import { modules } from './modules'
import { nav } from './nav'
import { overview } from './overview'
import { topic } from './topic'
import { ui } from './ui'

/**
 * Every string file of the entry chunk, so the parity test can detect a key defined twice.
 * Lazy pages keep their strings in their own file (read with useStrings): execPages, journals, atlas, brief, changes,
 * match, methods, execViz, editorViz, openViz … — see LAZY in lib/i18n.test.ts.
 */
export const PARTS = { common, ui, nav, overview, emerging, topic, compare, data, about, modules, glossary } as const

export const STR = { ...common, ...ui, ...nav, ...overview, ...emerging, ...topic, ...compare, ...data, ...about, ...modules, ...glossary }

export type StrKey = keyof typeof STR
