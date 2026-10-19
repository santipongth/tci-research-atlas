import { common } from './common'
import { ui } from './ui'

/** Every string file, so the parity test can detect a key defined twice. */
export const PARTS = { common, ui } as const

export const STR = { ...common, ...ui }

export type StrKey = keyof typeof STR
