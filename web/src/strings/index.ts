import { common } from './common'

/** Every string file, so the parity test can detect a key defined twice. */
export const PARTS = { common } as const

export const STR = { ...common }

export type StrKey = keyof typeof STR
