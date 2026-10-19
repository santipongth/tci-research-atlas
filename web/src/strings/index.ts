import { common } from './common'
import { emerging } from './emerging'
import { overview } from './overview'
import { ui } from './ui'

/** Every string file, so the parity test can detect a key defined twice. */
export const PARTS = { common, ui, overview, emerging } as const

export const STR = { ...common, ...ui, ...overview, ...emerging }

export type StrKey = keyof typeof STR
