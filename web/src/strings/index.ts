import { about } from './about'
import { atlas } from './atlas'
import { brief } from './brief'
import { common } from './common'
import { compare } from './compare'
import { data } from './data'
import { emerging } from './emerging'
import { modules } from './modules'
import { overview } from './overview'
import { topic } from './topic'
import { ui } from './ui'

/** Every string file, so the parity test can detect a key defined twice. */
export const PARTS = { common, ui, overview, emerging, topic, atlas, compare, data, about, brief, modules } as const

export const STR = { ...common, ...ui, ...overview, ...emerging, ...topic, ...atlas, ...compare, ...data, ...about, ...brief, ...modules }

export type StrKey = keyof typeof STR
